"""盲盒：独立货币抽盒、保底、重复转券、积分换券、实物兑换。

与卡片抽卡（services/gacha.py）的关系
- 完全独立的池子与货币：盲盒券 blindbox_tickets，保底 bb_pity_sr / bb_pity_ssr；
- 但复用同一套工程范式：events 幂等、1 秒限流、概率轮盘、同批去重。

实物兑换
- 消耗 1 个角色副本（count-1，归零后行保留 = 图鉴永久解锁）；
- 复用 achievements 表产出兑现码（source='blindbox'），爸妈走现有核销接口兑现，
  因此不占成就卡「积分兑换」的每日额度统计（该统计只算 source='redeem'）。
"""
from __future__ import annotations

import json
import random
import sqlite3
import uuid
from datetime import date, datetime

from app import content_loader
from app.services import events

RARITY_ORDER = ["N", "R", "SR", "SSR"]

# 图片版本戳：换图后改这个值，浏览器会重新拉取（避免旧图缓存）
ASSET_VERSION = "2"


def _image_url(filename: str) -> str:
    return f"/assets/blindbox/{filename}?v={ASSET_VERSION}"


def _cfg() -> dict:
    return content_loader.rewards()["blindbox"]


def _wall_cfg() -> dict:
    return content_loader.rewards()["wishes"]


def _characters() -> list[dict]:
    return content_loader.blindbox_characters()["characters"]


def _pools() -> dict[str, list[dict]]:
    pools: dict[str, list[dict]] = {r: [] for r in RARITY_ORDER}
    for ch in _characters():
        pools.setdefault(ch["rarity"], []).append(ch)
    return pools


def _roll_rarity(pity_sr: int, pity_ssr: int) -> str:
    cfg = _cfg()
    if pity_ssr + 1 >= cfg["pity_ssr"]:
        return "SSR"
    if pity_sr + 1 >= cfg["pity_sr"]:
        r = random.random()
        ssr_share = cfg["rarity"]["SSR"] / (cfg["rarity"]["SSR"] + cfg["rarity"]["SR"])
        return "SSR" if r < ssr_share else "SR"
    total = sum(cfg["rarity"].values())
    roll = random.uniform(0, total)
    acc = 0.0
    for rarity in ("SSR", "SR", "R", "N"):
        acc += cfg["rarity"][rarity]
        if roll <= acc:
            return rarity
    return "N"


def draw(conn: sqlite3.Connection, user: sqlite3.Row, count: int,
         idempotency_key: str) -> dict:
    """开盲盒主流程。"""
    cfg = _cfg()
    user_id = user["id"]

    if not isinstance(count, int) or isinstance(count, bool) or not 1 <= count <= 10:
        raise ValueError("开盒次数必须为 1–10")

    if idempotency_key:
        prev = events.find(conn, user_id, f"bbox:{idempotency_key}", "blindbox")
        if prev:
            return {"replayed": True, **json.loads(prev["payload"])}

    last = conn.execute(
        "SELECT created_at FROM events WHERE user_id=? AND kind='blindbox' "
        "ORDER BY id DESC LIMIT 1",
        (user_id,),
    ).fetchone()
    if last:
        try:
            elapsed = (datetime.now() - datetime.fromisoformat(last["created_at"])).total_seconds()
        except (TypeError, ValueError):
            elapsed = float("inf")
        if 0 <= elapsed < 1:
            raise ValueError("操作太快，请稍后再试")

    cost = cfg["ten_cost"] if count == 10 else cfg["single_cost"] * count
    have = user["blindbox_tickets"]
    if have < cost:
        raise ValueError(f"盲盒券不足，需要 {cost} 张，当前 {have} 张")

    pools = _pools()
    if not any(pools[r] for r in RARITY_ORDER):
        raise ValueError("盲盒角色池为空")

    pity_sr = user["bb_pity_sr"]
    pity_ssr = user["bb_pity_ssr"]
    results = []
    new_unlocks = []
    tickets_back = 0
    drawn: set[str] = set()

    for _ in range(count):
        rarity = _roll_rarity(pity_sr, pity_ssr)
        if rarity == "SSR":
            pity_sr, pity_ssr = 0, 0
        elif rarity == "SR":
            pity_sr, pity_ssr = 0, pity_ssr + 1
        else:
            pity_sr, pity_ssr = pity_sr + 1, pity_ssr + 1

        pool = pools[rarity] or pools["N"]
        fresh = [c for c in pool if c["id"] not in drawn]
        ch = random.choice(fresh or pool)
        drawn.add(ch["id"])

        row = conn.execute(
            "SELECT count FROM blindbox_owned WHERE user_id=? AND character_id=?",
            (user_id, ch["id"]),
        ).fetchone()

        is_new = row is None
        if is_new:
            conn.execute(
                "INSERT INTO blindbox_owned(user_id, character_id, count, first_at) "
                "VALUES (?,?,1,?)",
                (user_id, ch["id"], _now()),
            )
            new_unlocks.append(ch["id"])
            back = 0
        else:
            conn.execute(
                "UPDATE blindbox_owned SET count = count + 1 "
                "WHERE user_id=? AND character_id=?",
                (user_id, ch["id"]),
            )
            back = cfg["duplicate_tickets"].get(rarity, 0)
            tickets_back += back

        results.append({
            "character_id": ch["id"],
            "name": ch["name"],
            "en": ch.get("en", ""),
            "rarity": rarity,
            "color": ch.get("color", ""),
            "accessory": ch.get("accessory", ""),
            "image": _image_url(ch["image"]),
            "quote": ch.get("quote", ""),
            "is_new": is_new,
            "tickets_back": back,
        })

    tickets_left = have - cost + tickets_back
    conn.execute(
        "UPDATE users SET blindbox_tickets = ?, bb_pity_sr = ?, bb_pity_ssr = ?, "
        "last_seen = ? WHERE id = ?",
        (tickets_left, pity_sr, pity_ssr, _today(), user_id),
    )

    payload = {
        "results": results,
        "new_unlocks": new_unlocks,
        "tickets_back": tickets_back,
        "cost": cost,
        "tickets_left": tickets_left,
        "pity_sr": pity_sr,
        "pity_ssr": pity_ssr,
    }

    if idempotency_key and not events.log(
        conn, user_id, f"bbox:{idempotency_key}", "blindbox", payload
    ):
        raise ValueError("同一开盒请求已在处理中，请重试")

    return {"replayed": False, **payload}


def exchange_points(conn: sqlite3.Connection, user: sqlite3.Row, count: int = 1) -> dict:
    """积分 → 盲盒券（每日限 1 次，与卡片卡包兑换互不占用）。"""
    cfg = _cfg()
    user_id = user["id"]
    if not isinstance(count, int) or isinstance(count, bool) or not 1 <= count <= 5:
        raise ValueError("一次最多兑换 5 张")

    per = int(cfg.get("exchange_points", 100))
    limit = int(cfg.get("exchange_daily_limit", 1))
    used = conn.execute(
        "SELECT COUNT(*) AS n FROM events WHERE user_id=? AND kind='bbox_exchange' "
        "AND substr(created_at,1,10)=?",
        (user_id, _today()),
    ).fetchone()["n"]
    if used + 1 > limit:
        raise ValueError(f"今天已经兑换过盲盒券了（每天 {limit} 次）")

    cost = per * count
    if user["points"] < cost:
        raise ValueError(f"积分不足，需要 {cost} 分，当前 {user['points']} 分")

    key = f"bbox_ex:{_today()}:{used}"
    if not events.log(conn, user_id, key, "bbox_exchange",
                      {"count": count, "points": cost}):
        raise ValueError("请勿重复提交")

    conn.execute(
        "UPDATE users SET points = points - ?, blindbox_tickets = blindbox_tickets + ?, "
        "last_seen = ? WHERE id = ?",
        (cost, count, _today(), user_id),
    )
    return {
        "count": count,
        "points_spent": cost,
        "points_left": user["points"] - cost,
        "tickets_total": user["blindbox_tickets"] + count,
        "left_today": max(0, limit - used - 1),
    }


def redeem_character(conn: sqlite3.Connection, user: sqlite3.Row,
                     character_id: str) -> dict:
    """实物兑换：消耗 1 个副本，产出兑现码（复用 achievements 表与家长核销链路）。"""
    from app.services import achievements as achv

    cfg = _cfg()
    user_id = user["id"]
    ch = next((c for c in _characters() if c["id"] == character_id), None)
    if not ch:
        raise ValueError("角色不存在")

    row = conn.execute(
        "SELECT count FROM blindbox_owned WHERE user_id=? AND character_id=?",
        (user_id, character_id),
    ).fetchone()
    if not row or row["count"] <= 0:
        raise ValueError("还没有这个角色的副本，先去开出它吧")

    limit = int(cfg.get("redeem_per_month", 1))
    month = _today()[:7]
    # 每月每角色 1 次：按 events 里的角色 id 统计（不依赖 achievements 的文本字段）
    used_n = conn.execute(
        "SELECT COUNT(*) AS n FROM events WHERE user_id=? AND kind='bbox_redeem' "
        "AND json_extract(payload,'$.character')=? AND substr(created_at,1,7)=?",
        (user_id, character_id, month),
    ).fetchone()["n"]
    if used_n >= limit:
        raise ValueError(f"「{ch['name']}」本月已经兑换过了（每月 {limit} 次）")

    value = int(cfg["value_cny"].get(ch["rarity"], 0))
    code = achv._new_code(conn)
    now = _now()
    conn.execute(
        "INSERT INTO achievements(id, user_id, code, ymd, points, value_cny, status, "
        "source, created_at) VALUES (?,?,?,?,?,?,?,?,?)",
        ("a_" + uuid.uuid4().hex[:12], user_id, code, _today(), 0, value,
         "issued", "blindbox", now),
    )
    conn.execute(
        "UPDATE blindbox_owned SET count = count - 1 WHERE user_id=? AND character_id=?",
        (user_id, character_id),
    )
    if not events.log(conn, user_id, f"bbox_redeem:{character_id}:{month}",
                      "bbox_redeem", {"character": character_id, "value": value,
                                      "code": code}):
        raise ValueError("本月已经兑换过了")

    left = int(row["count"]) - 1
    return {
        "character_id": character_id,
        "name": ch["name"],
        "rarity": ch["rarity"],
        "value_cny": value,
        "code": code,
        "copies_left": left,
        "note": "把兑现码交给家长核销；同一角色每月限兑 1 次。",
    }


def owned_map(conn: sqlite3.Connection, user_id: str) -> dict[str, int]:
    rows = conn.execute(
        "SELECT character_id, count FROM blindbox_owned WHERE user_id=?", (user_id,)
    ).fetchall()
    return {r["character_id"]: r["count"] for r in rows}


def gallery(conn: sqlite3.Connection, user_id: str) -> list[dict]:
    """图鉴：全部角色 + 是否解锁 + 副本数。"""
    owned = owned_map(conn, user_id)
    out = []
    for ch in _characters():
        n = owned.get(ch["id"], 0)
        out.append({
            "id": ch["id"],
            "name": ch["name"],
            "en": ch.get("en", ""),
            "rarity": ch["rarity"],
            "color": ch.get("color", ""),
            "accessory": ch.get("accessory", ""),
            "image": _image_url(ch["image"]),
            "quote": ch.get("quote", ""),
            "story": ch.get("story", ""),
            "unlocked": ch["id"] in owned,   # count=0 也算解锁（曾拥有）
            "count": n,
            "value_cny": int(_cfg()["value_cny"].get(ch["rarity"], 0)),
        })
    order = {r: i for i, r in enumerate(RARITY_ORDER)}
    out.sort(key=lambda c: (order.get(c["rarity"], 9), c["id"]))
    return out


def add_tickets(conn: sqlite3.Connection, user_id: str, n: int) -> None:
    """发放盲盒券（许愿墙奖励等复用）。"""
    if n <= 0:
        return
    conn.execute(
        "UPDATE users SET blindbox_tickets = blindbox_tickets + ? WHERE id = ?",
        (n, user_id),
    )


def wish_bonus() -> int:
    return int(_wall_cfg().get("ticket_reward", 1))


def _now() -> str:
    return datetime.now().isoformat(timespec="seconds")


def _today() -> str:
    return date.today().isoformat()