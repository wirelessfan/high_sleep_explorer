"""成就卡：积分兑换 → 生成兑现码 → 核销。

设计要点
- 兑换扣分与建卡在同一事务内，日上限按 achievements.ymd 统计，天然幂等。
- 兑现码由去混淆字符集生成，全局唯一；核销是单向状态迁移 issued -> redeemed。
- 每日上限防止误操作与刷分把预算冲掉，是这套体系唯一硬约束。
"""
from __future__ import annotations

import sqlite3
import uuid
from datetime import date

from app import content_loader

_CODE_ALPHABET = "ABCDEFGHJKMNPQRSTUVWXYZ23456789"  # 去掉 0/O/1/I/L


def _cfg() -> dict:
    return content_loader.rewards()["achievement"]


def today_str() -> str:
    return date.today().isoformat()


def _new_code(conn: sqlite3.Connection, groups: int = 3, size: int = 4) -> str:
    import secrets
    for _ in range(20):
        raw = "".join(secrets.choice(_CODE_ALPHABET) for _ in range(groups * size))
        code = "-".join(raw[i:i + size] for i in range(0, len(raw), size))
        if not conn.execute("SELECT 1 FROM achievements WHERE code = ?", (code,)).fetchone():
            return code
    raise RuntimeError("无法生成唯一兑现码")


def stats(conn: sqlite3.Connection, user_id: str) -> dict:
    """积分兑换的日额度与累计。

    注意：日上限只约束「积分兑换」，每日免费抽卡与收到的赠卡都不占额度，
    所以这里必须按 source='redeem' 过滤，否则抽一次卡就少一次兑换机会。
    """
    cfg = _cfg()
    today = today_str()
    row = conn.execute(
        "SELECT COUNT(*) AS n, COALESCE(SUM(value_cny),0) AS v FROM achievements "
        "WHERE user_id=? AND ymd=? AND status!='void' AND source='redeem'",
        (user_id, today),
    ).fetchone()
    # 累计口径包含兑换、抽卡与收到的赠卡
    total = conn.execute(
        "SELECT COUNT(*) AS n, COALESCE(SUM(value_cny),0) AS v FROM achievements "
        "WHERE user_id=? AND status!='void'",
        (user_id,),
    ).fetchone()
    return {
        "points_per_card": cfg["points_per_card"],
        "value_cny": cfg["value_cny"],
        "daily_limit": cfg["daily_limit"],
        "today_count": row["n"],
        "today_value": row["v"],
        "today_left": max(0, cfg["daily_limit"] - row["n"]),
        "total_count": total["n"],
        "total_value": total["v"],
    }


def redeem_points(conn: sqlite3.Connection, user: sqlite3.Row, count: int = 1) -> dict:
    """用积分兑换成就卡，返回新生成的卡。"""
    cfg = _cfg()
    if not isinstance(count, int) or isinstance(count, bool) or not 1 <= count <= 10:
        raise ValueError("兑换张数必须为 1–10")

    today = today_str()
    # 额度只统计积分兑换；每日抽卡和赠卡不占这个额度
    used = conn.execute(
        "SELECT COUNT(*) AS n FROM achievements "
        "WHERE user_id=? AND ymd=? AND status!='void' AND source='redeem'",
        (user["id"], today),
    ).fetchone()["n"]

    left = max(0, cfg["daily_limit"] - used)
    if left <= 0:
        raise ValueError(f"今天已经兑满 {cfg['daily_limit']} 张，明天再来")
    if count > left:
        raise ValueError(f"今天还能兑 {left} 张")

    cost = cfg["points_per_card"] * count
    if user["points"] < cost:
        raise ValueError(f"积分不足，需要 {cost}，当前 {user['points']}")

    cards = []
    for _ in range(count):
        code = _new_code(conn)
        card_id = "a_" + uuid.uuid4().hex[:12]
        card = {
            "id": card_id,
            "code": code,
            "value_cny": cfg["value_cny"],
            "points": cfg["points_per_card"],
            "status": "issued",
            "created_at": today,
        }
        conn.execute(
            "INSERT INTO achievements(id, user_id, code, ymd, points, value_cny, status, created_at) "
            "VALUES (?,?,?,?,?,?, 'issued', ?)",
            (card_id, user["id"], code, today, cfg["points_per_card"], cfg["value_cny"], today),
        )
        cards.append(card)

    conn.execute("UPDATE users SET points = points - ? WHERE id = ?", (cost, user["id"]))

    return {
        "cards": cards,
        "spent": cost,
        "count": count,
        "today_left": left - count,
        "today_value": (used + count) * cfg["value_cny"],
    }


def list_cards(conn: sqlite3.Connection, user_id: str, limit: int = 40) -> list[dict]:
    rows = conn.execute(
        "SELECT a.*, u.nickname AS from_nickname, u.username AS from_username "
        "FROM achievements a LEFT JOIN users u ON u.id = a.gifted_from "
        "WHERE a.user_id=? ORDER BY a.created_at DESC, a.rowid DESC LIMIT ?",
        (user_id, limit),
    ).fetchall()
    keys = rows[0].keys() if rows else []
    return [
        {
            "id": r["id"],
            "code": r["code"],
            "points": r["points"],
            "value_cny": r["value_cny"],
            "status": r["status"],
            "source": r["source"] if "source" in keys else "redeem",
            "gifted_from": r["gifted_from"] if "gifted_from" in keys else None,
            "from_nickname": r["from_nickname"] if "from_nickname" in keys else None,
            "from_username": r["from_username"] if "from_username" in keys else None,
            "created_at": r["created_at"],
            "redeemed_at": r["redeemed_at"],
        }
        for r in rows
    ]


def mark_redeemed(conn: sqlite3.Connection, code: str) -> dict:
    """核销兑现码（家长/老师线下给钱后标记）。"""
    normalized = code.strip().upper().replace(" ", "")
    row = conn.execute("SELECT * FROM achievements WHERE code = ?", (normalized,)).fetchone()
    if not row:
        raise ValueError("兑现码不存在")
    if row["status"] == "redeemed":
        raise ValueError("这张卡已经兑现过了")
    if row["status"] == "void":
        raise ValueError("这张卡已作废")

    conn.execute(
        "UPDATE achievements SET status='redeemed', redeemed_at=? WHERE id=?",
        (today_str(), row["id"]),
    )
    return {
        "id": row["id"],
        "code": row["code"],
        "value_cny": row["value_cny"],
        "redeemed_at": today_str(),
    }


# ---------- 每日随机卡 ----------

def _daily_cfg() -> dict:
    return _cfg().get("daily_draw", {})


def _roll_value(tiers: list[dict]) -> int:
    """按权重抽面值。"""
    import random
    total = sum(t["weight"] for t in tiers)
    roll = random.uniform(0, total)
    acc = 0.0
    for t in tiers:
        acc += t["weight"]
        if roll <= acc:
            return int(t["value_cny"])
    return int(tiers[-1]["value_cny"])


def daily_status(conn: sqlite3.Connection, user_id: str) -> dict:
    """今天是否已抽过、可赠予对象。"""
    cfg = _daily_cfg()
    if not cfg.get("enabled"):
        return {"enabled": False}

    today = today_str()
    # 赠出的卡 user_id 已变成对方，必须把 gifted_from 也计入，
    # 否则「抽完就送人」可以绕开每日一次的限制。
    used = conn.execute(
        "SELECT COUNT(*) AS n FROM achievements "
        "WHERE ymd=? AND source='daily' AND status!='void' "
        "AND (user_id=? OR gifted_from=?)",
        (today, user_id, user_id),
    ).fetchone()["n"]

    gift_to = cfg.get("gift_to", "sunny")
    target = conn.execute(
        "SELECT id, nickname, username FROM users WHERE username = ?", (gift_to,)
    ).fetchone()

    return {
        "enabled": True,
        "per_day": int(cfg.get("per_day", 1)),
        "used_today": used,
        "left_today": max(0, int(cfg.get("per_day", 1)) - used),
        "tiers": cfg.get("tiers", []),
        "gift_to": gift_to,
        "gift_target_exists": target is not None,
        "gift_target_nickname": target["nickname"] if target else None,
    }


def draw_daily(conn: sqlite3.Connection, user: sqlite3.Row) -> dict:
    """每日一次免费抽卡。"""
    cfg = _daily_cfg()
    if not cfg.get("enabled"):
        raise ValueError("每日抽卡未开放")

    per_day = int(cfg.get("per_day", 1))
    today = today_str()
    # 与 daily_status 保持同一口径：自己抽的（含已赠出的）都算用掉次数
    used = conn.execute(
        "SELECT COUNT(*) AS n FROM achievements "
        "WHERE ymd=? AND source='daily' AND status!='void' "
        "AND (user_id=? OR gifted_from=?)",
        (today, user["id"], user["id"]),
    ).fetchone()["n"]
    if used >= per_day:
        raise ValueError("今天已经抽过了，明天再来")

    value = _roll_value(cfg.get("tiers", []))
    code = _new_code(conn)
    card_id = "a_" + uuid.uuid4().hex[:12]

    conn.execute(
        "INSERT INTO achievements(id, user_id, code, ymd, points, value_cny, status, "
        "source, created_at) VALUES (?,?,?,?,0,?,'issued','daily',?)",
        (card_id, user["id"], code, today, value, today),
    )

    return {
        "card": {
            "id": card_id,
            "code": code,
            "value_cny": value,
            "status": "issued",
            "source": "daily",
            "created_at": today,
            "gifted_from": None,
        },
        "left_today": max(0, per_day - used - 1),
    }


def gift_card(conn: sqlite3.Connection, user: sqlite3.Row, card_id: str,
              to_username: str | None = None) -> dict:
    """把一张卡赠送给目标账号（默认配置里的 sunny）。

    限制：只能赠出自己名下的、未兑现的卡；不能赠给自己。
    """
    cfg = _daily_cfg()
    target_name = (to_username or cfg.get("gift_to") or "sunny").strip().lower()

    card = conn.execute(
        "SELECT * FROM achievements WHERE id=? AND user_id=?", (card_id, user["id"])
    ).fetchone()
    if not card:
        raise ValueError("卡不存在或不属于你")
    if card["status"] == "redeemed":
        raise ValueError("已兑现的卡不能赠送")
    if card["status"] == "void":
        raise ValueError("已作废的卡不能赠送")

    target = conn.execute(
        "SELECT id, nickname, username FROM users WHERE username = ?", (target_name,)
    ).fetchone()
    if not target:
        raise ValueError(f"接收账号 {target_name} 不存在")
    if target["id"] == user["id"]:
        raise ValueError("不能赠送给自己")

    conn.execute(
        "UPDATE achievements SET user_id=?, gifted_from=?, gifted_at=? WHERE id=?",
        (target["id"], user["id"], today_str(), card_id),
    )

    return {
        "card_id": card_id,
        "code": card["code"],
        "value_cny": card["value_cny"],
        "to_username": target["username"],
        "to_nickname": target["nickname"],
    }


def received_cards(conn: sqlite3.Connection, user_id: str) -> list[dict]:
    """别人赠给我的卡。"""
    rows = conn.execute(
        "SELECT a.*, u.nickname AS from_nickname, u.username AS from_username "
        "FROM achievements a LEFT JOIN users u ON u.id = a.gifted_from "
        "WHERE a.user_id = ? AND a.gifted_from IS NOT NULL "
        "ORDER BY a.gifted_at DESC, a.rowid DESC LIMIT 30",
        (user_id,),
    ).fetchall()
    return [
        {
            "id": r["id"],
            "code": r["code"],
            "value_cny": r["value_cny"],
            "status": r["status"],
            "gifted_at": r["gifted_at"],
            "from_nickname": r["from_nickname"] or "家人",
            "from_username": r["from_username"],
        }
        for r in rows
    ]
