"""休闲广场每日抽奖额度：防沉迷限额 + 当日积分奖励次数。

规则：
- 平日（周一/二/三/四/五）每天 10 次；疯狂星期六、周日、法定节假日每天 20 次。
- 当日学习获得的积分，每 10 分额外奖励 1 次（积分照常累积，不扣除）。
- 实体奖机会独立计数：周一/三/五/日免费 1 次；当日获得积分达到 100 再额外 1 次。
- 管理员赠送的额外次数记为跨天「赠送池」（relax_grant）：7 天内有效、总量固定、
  用完即止，不会每天刷新；消耗顺序为先当日基础额度、再赠送池（先到期先用）。
- 每日额度按用户 + 自然日记录在 relax_daily_quota / relax_prize_quota，服务端权威计数，
  清缓存无法绕过。
"""
from __future__ import annotations

import json
import sqlite3
import uuid
from datetime import date, datetime, timedelta, datetime
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from app import db
from app.routers.session import current_user, require_admin
from app.services import events

router = APIRouter(tags=["relax"])

# 2026 年国务院放假安排：只列放假日期；调休上班的周末不算节假日。
_HOLIDAYS_2026 = set()
for _a, _b in (
    ("2026-01-01", "2026-01-03"),  # 元旦
    ("2026-02-15", "2026-02-23"),  # 春节
    ("2026-04-04", "2026-04-06"),  # 清明
    ("2026-05-01", "2026-05-05"),  # 劳动节
    ("2026-06-19", "2026-06-21"),  # 端午
    ("2026-09-25", "2026-09-27"),  # 中秋
    ("2026-10-01", "2026-10-07"),  # 国庆
):
    _d = date.fromisoformat(_a)
    _end = date.fromisoformat(_b)
    while _d <= _end:
        _HOLIDAYS_2026.add(_d.isoformat())
        _d = date.fromordinal(_d.toordinal() + 1)

# 调休上班日：这些周末按平日额度计算。
_MAKEUP_WORKDAYS_2026 = {
    "2026-01-04", "2026-02-14", "2026-02-28",
    "2026-05-09", "2026-09-20", "2026-10-10",
}

BASE_WEEKDAY = 10
BASE_LUCKY = 20
POINTS_PER_DRAW = 10
BONUS_CAP = 20  # 防沉迷：积分奖励次数设上限，避免每天刷出过多机会

# 实体奖免费机会：周一三五/日各 1 次（Python weekday: 周一=0 … 周日=6）。
PRIZE_FREE_WEEKDAYS = {0, 2, 4, 6}
PRIZE_FREE_LABEL = '周一/三/五/日'
PRIZE_POINTS_THRESHOLD = 100  # 当日新获得积分达到该值，额外 +1 次实体奖机会
GRANT_DAYS = 7  # 管理员赠送次数有效期（自然日，含赠送当天）


def _today() -> str:
    return date.today().isoformat()


def day_type(day: str) -> Literal["weekday", "crazy-saturday", "weekend", "holiday"]:
    d = date.fromisoformat(day)
    iso = d.isoformat()
    if iso in _HOLIDAYS_2026:
        return "holiday"
    if iso not in _MAKEUP_WORKDAYS_2026 and d.weekday() >= 5:
        # 周六是「疯狂星期六」，周日仍是周末；两者额度相同，只是标签不同。
        return "crazy-saturday" if d.weekday() == 5 else "weekend"
    return "weekday"


def base_limit(day: str) -> int:
    return BASE_LUCKY if day_type(day) != "weekday" else BASE_WEEKDAY


# 只有这些事件类型代表「当日新获得积分」；盲盒兑换/补偿等不重复计入。
_EARN_EVENT_KINDS = ("first", "review", "set", "question_feedback_reward", "reflection_reward",
                     "wrongbook_clear")


def _earned_points(conn: sqlite3.Connection, user_id: str, day: str) -> int:
    checkin = conn.execute(
        "SELECT COALESCE(SUM(points),0) AS n FROM checkins WHERE user_id=? AND day=?",
        (user_id, day),
    ).fetchone()["n"]
    ev = conn.execute(
        "SELECT COALESCE(SUM(CAST(json_extract(payload,'$.points') AS INTEGER)),0) AS n "
        "FROM events WHERE user_id=? AND substr(created_at,1,10)=? AND kind IN (%s)"
        % ",".join("?" * len(_EARN_EVENT_KINDS)),
        (user_id, day, *_EARN_EVENT_KINDS),
    ).fetchone()["n"]
    return int(checkin) + int(ev)


def grant_pool(
    conn: sqlite3.Connection, user_id: str, kind: str, day: str,
) -> dict:
    """某类赠送池在当天的状态：有效期内、尚未用完的所有赠送记录汇总。

    赠送次数不按天刷新——它是一笔总量固定的额度，7 天内用完即止。
    """
    rows = conn.execute(
        "SELECT id, amount, used, start_day, end_day FROM relax_grant "
        "WHERE user_id=? AND kind=? AND start_day<=? AND end_day>=? AND used<amount "
        "ORDER BY end_day ASC, start_day ASC, id ASC",
        (user_id, kind, day, day),
    ).fetchall()
    total = sum(r["amount"] for r in rows)
    used = sum(r["used"] for r in rows)
    end_day = rows[0]["end_day"] if rows else None
    return {
        "total": total,
        "used": used,
        "remaining": max(0, total - used),
        "end_day": end_day,
        "rows": rows,
    }


def _consume_grant(
    conn: sqlite3.Connection, user_id: str, kind: str, day: str, count: int,
) -> None:
    """从赠送池扣减 count 次：先到期先用（FIFO by end_day），不涉及当日基础额度。"""
    left = count
    for r in grant_pool(conn, user_id, kind, day)["rows"]:
        if left <= 0:
            break
        room = r["amount"] - r["used"]
        take = min(room, left)
        conn.execute("UPDATE relax_grant SET used = used + ? WHERE id = ?", (take, r["id"]))
        left -= take


def prize_quota_for(
    conn: sqlite3.Connection, user_id: str, day: str, earned: int | None = None,
) -> dict:
    """实体奖免费机会：周一三五/日 + 当日积分达标，资格实时折算，只记录已用。"""
    d = date.fromisoformat(day)
    free = 1 if d.weekday() in PRIZE_FREE_WEEKDAYS else 0
    if earned is None:
        earned = _earned_points(conn, user_id, day)
    points_bonus = 1 if earned >= PRIZE_POINTS_THRESHOLD else 0
    day_total = free + points_bonus
    row = conn.execute(
        "SELECT used FROM relax_prize_quota WHERE user_id=? AND day=?",
        (user_id, day),
    ).fetchone()
    day_used = row["used"] if row else 0
    grant = grant_pool(conn, user_id, "prize", day)
    # 今日可抽总量 = 当日免费额度 + 赠送池剩余；先扣当日额度，再扣赠送池。
    total = day_total + grant["remaining"]
    remaining = max(0, day_total - day_used) + grant["remaining"]
    return {
        "free": free,
        "free_days": PRIZE_FREE_LABEL,
        "earned_points": earned,
        "points_threshold": PRIZE_POINTS_THRESHOLD,
        "points_bonus": points_bonus,
        "granted": grant["remaining"],
        "grant_total": grant["total"],
        "grant_used": grant["used"],
        "grant_end": grant["end_day"],
        "day_total": day_total,
        "day_used": day_used,
        "next_in": max(0, PRIZE_POINTS_THRESHOLD - earned),
        "total": total,
        "used": day_used,
        "remaining": remaining,
    }


def quota_for(conn: sqlite3.Connection, user_id: str, day: str | None = None) -> dict:
    day = day or _today()
    kind = day_type(day)
    base = base_limit(day)
    earned = _earned_points(conn, user_id, day)
    bonus = min(BONUS_CAP, earned // POINTS_PER_DRAW)
    day_total = base + bonus
    row = conn.execute(
        "SELECT used FROM relax_daily_quota WHERE user_id=? AND day=?",
        (user_id, day),
    ).fetchone()
    day_used = row["used"] if row else 0
    grant = grant_pool(conn, user_id, "regular", day)
    # 今日可抽总量 = 当日基础额度 + 赠送池剩余；先扣当日额度，再扣赠送池。
    total = day_total + grant["remaining"]
    remaining = max(0, day_total - day_used) + grant["remaining"]
    return {
        "date": day,
        "day_type": kind,
        "base": base,
        "earned_points": earned,
        "points_per_draw": POINTS_PER_DRAW,
        "bonus": bonus,
        "bonus_cap": BONUS_CAP,
        "day_total": day_total,
        "day_used": day_used,
        "granted": grant["remaining"],
        "grant_total": grant["total"],
        "grant_used": grant["used"],
        "grant_end": grant["end_day"],
        "next_bonus_in": POINTS_PER_DRAW - (earned % POINTS_PER_DRAW),
        "total": total,
        "used": day_used,
        "remaining": remaining,
        "prize": prize_quota_for(conn, user_id, day, earned),
    }


@router.get("/relax/quota")
def get_quota(user: sqlite3.Row = Depends(current_user)):
    with db.ro() as conn:
        return quota_for(conn, user["id"])


class ConsumeIn(BaseModel):
    count: int = Field(default=1, ge=1, le=10)
    idempotency_key: str | None = Field(default=None, max_length=80)


@router.post("/relax/quota/consume")
def consume_quota(body: ConsumeIn, user: sqlite3.Row = Depends(current_user)):
    day = _today()
    with db.tx() as conn:
        # 幂等：同一 key 重复提交不重复扣次数（例如网络重试 / 双击）。
        if body.idempotency_key:
            if not events.log(conn, user["id"], f"relax_quota:{day}:{body.idempotency_key}",
                              "relax_quota", {"count": body.count}):
                return quota_for(conn, user["id"], day)
        q = quota_for(conn, user["id"], day)
        if q["remaining"] < body.count:
            raise HTTPException(status_code=409, detail={
                "message": "今天的抽奖次数用完了，明天再来吧",
                "quota": q,
            })
        # 先消耗当日基础额度，超出部分才扣 7 天有效赠送池（先到期先用）。
        from_day = min(body.count, q["day_total"] - q["day_used"])
        from_grant = body.count - from_day
        if from_day > 0:
            conn.execute(
                "INSERT INTO relax_daily_quota(user_id, day, used) VALUES(?,?,?) "
                "ON CONFLICT(user_id,day) DO UPDATE SET used = used + excluded.used",
                (user["id"], day, from_day),
            )
        if from_grant > 0:
            _consume_grant(conn, user["id"], "regular", day, from_grant)
        return quota_for(conn, user["id"], day)


class PrizeConsumeIn(BaseModel):
    idempotency_key: str | None = Field(default=None, max_length=80)


@router.post("/relax/prize/consume")
def consume_prize_quota(body: PrizeConsumeIn, user: sqlite3.Row = Depends(current_user)):
    """消耗 1 次实体奖免费机会；与普通抽卡额度互不影响。"""
    day = _today()
    with db.tx() as conn:
        if body.idempotency_key:
            if not events.log(conn, user["id"], f"relax_prize:{day}:{body.idempotency_key}",
                              "relax_prize", {"count": 1}):
                return quota_for(conn, user["id"], day)
        q = quota_for(conn, user["id"], day)
        p = q["prize"]
        if p["remaining"] < 1:
            raise HTTPException(status_code=409, detail={
                "message": "今天的实体奖机会用完了，明天再来吧",
                "quota": q,
            })
        # 先消耗当日免费机会，超出部分才扣实体奖赠送池。
        if p["day_used"] < p["day_total"]:
            conn.execute(
                "INSERT INTO relax_prize_quota(user_id, day, used) VALUES(?,?,1) "
                "ON CONFLICT(user_id,day) DO UPDATE SET used = used + 1",
                (user["id"], day),
            )
        else:
            _consume_grant(conn, user["id"], "prize", day, 1)
        return quota_for(conn, user["id"], day)


class GrantIn(BaseModel):
    user_id: str = Field(min_length=1, max_length=100)
    day: str | None = Field(default=None, pattern=r"^\d{4}-\d{2}-\d{2}$")
    days: int = Field(default=GRANT_DAYS, ge=1, le=90)
    regular: int = Field(default=0, ge=0, le=1000)
    prize: int = Field(default=0, ge=0, le=1000)


@router.post("/relax/quota/grant")
def grant_quota(body: GrantIn, _admin: sqlite3.Row = Depends(require_admin)):
    """管理员给用户赠送次数：写入跨天赠送池，days 天内有效、用完即止（默认 7 天）。"""
    day = body.day or _today()
    end_day = (date.fromisoformat(day) + timedelta(days=body.days - 1)).isoformat()
    now = datetime.now().isoformat(timespec="seconds")
    with db.tx() as conn:
        if not conn.execute("SELECT 1 FROM users WHERE id=?", (body.user_id,)).fetchone():
            raise HTTPException(status_code=404, detail="用户不存在")
        for kind, amount in (("regular", body.regular), ("prize", body.prize)):
            if amount:
                conn.execute(
                    "INSERT INTO relax_grant(user_id,kind,amount,used,start_day,end_day,created_at) "
                    "VALUES(?,?,?,0,?,?,?)",
                    (body.user_id, kind, amount, day, end_day, now),
                )
        return quota_for(conn, body.user_id, day)


LAB_BONUS_AMOUNT = 20      # 首次进入「物理实验」板块赠送的抽奖次数
LAB_BONUS_DAYS = 30        # 赠送池有效期：30 天，够孩子慢慢用
LAB_BONUS_KEY = "lab_bonus:v1"   # 每账号一次性；改版本号可再发一次


@router.post("/relax/lab-bonus")
def claim_lab_bonus(user: sqlite3.Row = Depends(current_user)):
    """首次点开物理实验板块（简史 / 动量机械能）赠送 20 次抽奖。

    幂等：靠 events 唯一键，一次领取后重复调用只会返回 granted_now = 0，
    不会叠加；前端两个实验页都调这里，所以两个板块合计仍只发 20 次。
    """
    day = _today()
    with db.tx() as conn:
        first = events.log(conn, user["id"], LAB_BONUS_KEY, "relax_bonus",
                           {"amount": LAB_BONUS_AMOUNT, "days": LAB_BONUS_DAYS})
        if first:
            end_day = (date.fromisoformat(day) + timedelta(days=LAB_BONUS_DAYS - 1)).isoformat()
            conn.execute(
                "INSERT INTO relax_grant(user_id,kind,amount,used,start_day,end_day,created_at) "
                "VALUES(?,?,?,0,?,?,?)",
                (user["id"], "regular", LAB_BONUS_AMOUNT, day, end_day,
                 datetime.now().isoformat(timespec="seconds")),
            )
        q = quota_for(conn, user["id"], day)
        q["granted_now"] = LAB_BONUS_AMOUNT if first else 0
        q["bonus_amount"] = LAB_BONUS_AMOUNT
        return q


# ---------- 抽卡存档备份 + 实体券台账（家长核销 / 合成阶梯） ----------

# 服务端持有的实体奖品注册表：台账内容以这里为准，不信任客户端字符串。
PRIZE_REGISTRY = {
    "p-mai-dong":   {"name": "脉动饮料", "emoji": "🥤", "rarity": "N"},
    "p-an-mu-xi":   {"name": "安慕希牛奶", "emoji": "🥛", "rarity": "N"},
    "p-tang-hu-lu": {"name": "糖葫芦一串", "emoji": "🍡", "rarity": "N"},
    "p-hershey":    {"name": "好时巧克力", "emoji": "🍫", "rarity": "R"},
    "p-ferrero":    {"name": "费列罗巧克力", "emoji": "🍬", "rarity": "R"},
    "p-kao-yu":     {"name": "烤鱼套餐", "emoji": "🐟", "rarity": "SR"},
    "p-hai-di-lao": {"name": "海底捞火锅", "emoji": "🍲", "rarity": "SR"},
    "p-mystery":    {"name": "神秘心愿", "emoji": "🌟", "rarity": "SSR"},
}

# 合成阶梯：3 张 N 券换 1 张自选 R 券；2 张 R 券换 1 张自选 SR 券。
EXCHANGE_RULES = {"R": {"cost": 3, "from": "N"}, "SR": {"cost": 2, "from": "R"}}

STATE_MAX_CHARS = 200_000  # 存档上限，超限拒绝，防意外大包


class StatePut(BaseModel):
    data: str = Field(min_length=2, max_length=STATE_MAX_CHARS)


class LedgerEntry(BaseModel):
    prize_id: str = Field(min_length=1, max_length=40)
    client_key: str = Field(min_length=8, max_length=80)


class LedgerPost(BaseModel):
    entries: list[LedgerEntry] = Field(default_factory=list)


class RedeemIn(BaseModel):
    ledger_id: str = Field(min_length=1, max_length=64)


class ExchangeIn(BaseModel):
    target: Literal["R", "SR"]
    prize_id: str = Field(min_length=1, max_length=40)
    keys: list[str] = Field(default_factory=list)


def _now_iso() -> str:
    return datetime.now().isoformat(timespec="seconds")


def _ledger_row(row: sqlite3.Row) -> dict:
    prize = PRIZE_REGISTRY.get(row["prize_id"], {
        "name": "未知奖励", "emoji": "🎁", "rarity": "N"})
    return {
        "id": row["id"],
        "prize_id": row["prize_id"],
        "name": prize["name"],
        "emoji": prize["emoji"],
        "rarity": prize["rarity"],
        "status": row["status"],
        "created_at": row["created_at"],
        "redeemed_at": row["redeemed_at"],
    }


@router.get("/relax/gacha/state")
def get_gacha_state(user: sqlite3.Row = Depends(current_user)):
    with db.ro() as conn:
        row = conn.execute(
            "SELECT data, updated_at FROM relax_gacha_state WHERE user_id=?",
            (user["id"],),
        ).fetchone()
    return {"data": row["data"] if row else None,
            "updated_at": row["updated_at"] if row else None}


@router.put("/relax/gacha/state")
def put_gacha_state(body: StatePut, user: sqlite3.Row = Depends(current_user)):
    try:
        parsed = json.loads(body.data)
    except ValueError:
        raise HTTPException(status_code=422, detail="存档不是合法 JSON")
    if not isinstance(parsed, dict):
        raise HTTPException(status_code=422, detail="存档格式不对")
    with db.tx() as conn:
        conn.execute(
            "INSERT INTO relax_gacha_state(user_id, data, updated_at) VALUES(?,?,?) "
            "ON CONFLICT(user_id) DO UPDATE SET data = excluded.data, updated_at = excluded.updated_at",
            (user["id"], body.data, _now_iso()),
        )
    return {"ok": True}


@router.post("/relax/ledger")
def post_ledger(body: LedgerPost, user: sqlite3.Row = Depends(current_user)):
    """上报抽到的实体券。同一 client_key 重复上报只记一行（网络重试安全）。"""
    if len(body.entries) > 30:
        raise HTTPException(status_code=422, detail="单次上报最多 30 张券")
    added = 0
    with db.tx() as conn:
        for entry in body.entries:
            if entry.prize_id not in PRIZE_REGISTRY:
                continue  # 未知奖励不记账，避免客户端字符串污染台账
            cur = conn.execute(
                "INSERT OR IGNORE INTO relax_prize_ledger(id, user_id, prize_id, status, client_key, created_at) "
                "VALUES(?,?,?,'held',?,?)",
                (uuid.uuid4().hex, user["id"], entry.prize_id, entry.client_key, _now_iso()),
            )
            added += cur.rowcount
    return {"added": added}


@router.get("/relax/ledger")
def get_my_ledger(user: sqlite3.Row = Depends(current_user)):
    with db.ro() as conn:
        rows = conn.execute(
            "SELECT * FROM relax_prize_ledger WHERE user_id=? ORDER BY created_at DESC, id LIMIT 100",
            (user["id"],),
        ).fetchall()
    return {"items": [_ledger_row(r) for r in rows]}


@router.get("/relax/ledger/all")
def get_all_ledger(_admin: sqlite3.Row = Depends(require_admin)):
    with db.ro() as conn:
        rows = conn.execute(
            "SELECT l.*, u.nickname, u.username FROM relax_prize_ledger l "
            "LEFT JOIN users u ON u.id = l.user_id "
            "ORDER BY l.created_at DESC, l.id LIMIT 200",
        ).fetchall()
    items = []
    for r in rows:
        item = _ledger_row(r)
        item["nickname"] = r["nickname"] or ""
        item["username"] = r["username"] or ""
        items.append(item)
    return {"items": items}


@router.post("/relax/ledger/redeem")
def redeem_ledger(body: RedeemIn, admin: sqlite3.Row = Depends(require_admin)):
    """家长核销：把一张券标记为已兑现。"""
    with db.tx() as conn:
        cur = conn.execute(
            "UPDATE relax_prize_ledger SET status='redeemed', redeemed_at=?, redeemed_by=? "
            "WHERE id=? AND status='held'",
            (_now_iso(), admin["id"], body.ledger_id),
        )
        if cur.rowcount != 1:
            raise HTTPException(status_code=409, detail="这张券不存在或已核销/已合成")
    return {"ok": True}


@router.post("/relax/ledger/exchange")
def exchange_ledger(body: ExchangeIn, user: sqlite3.Row = Depends(current_user)):
    """合成阶梯：用低稀有度的券换一张自选高稀有度券。"""
    rule = EXCHANGE_RULES.get(body.target)
    target = PRIZE_REGISTRY.get(body.prize_id)
    if not rule or not target or target["rarity"] != body.target:
        raise HTTPException(status_code=422, detail="这张券不能通过合成获得")
    keys = list(dict.fromkeys(body.keys))[: rule["cost"]]
    if len(keys) < rule["cost"]:
        raise HTTPException(status_code=422, detail=f"需要选 {rule['cost']} 张券")
    placeholders = ",".join("?" * len(keys))
    with db.tx() as conn:
        rows = conn.execute(
            f"SELECT id, prize_id FROM relax_prize_ledger "
            f"WHERE user_id=? AND status='held' AND id IN ({placeholders})",
            (user["id"], *keys),
        ).fetchall()
        if len(rows) < rule["cost"]:
            raise HTTPException(status_code=409, detail="可用的券不够，可能已被核销或用过")
        if any(PRIZE_REGISTRY.get(r["prize_id"], {}).get("rarity") != rule["from"] for r in rows):
            raise HTTPException(status_code=422, detail=f"只能用 {rule['cost']} 张 {rule['from']} 级券")
        conn.execute(
            f"UPDATE relax_prize_ledger SET status='spent' "
            f"WHERE user_id=? AND id IN ({placeholders})",
            (user["id"], *keys),
        )
        new_id = uuid.uuid4().hex
        conn.execute(
            "INSERT INTO relax_prize_ledger(id, user_id, prize_id, status, client_key, created_at) "
            "VALUES(?,?,?,'held',?,?)",
            (new_id, user["id"], body.prize_id, f"exchange:{new_id}", _now_iso()),
        )
        row = conn.execute("SELECT * FROM relax_prize_ledger WHERE id=?", (new_id,)).fetchone()
    return {"item": _ledger_row(row)}
