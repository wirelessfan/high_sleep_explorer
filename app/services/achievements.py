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
    """今日/累计兑换情况。"""
    cfg = _cfg()
    today = today_str()
    row = conn.execute(
        "SELECT COUNT(*) AS n, COALESCE(SUM(value_cny),0) AS v FROM achievements "
        "WHERE user_id=? AND ymd=? AND status!='void'",
        (user_id, today),
    ).fetchone()
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
    used = conn.execute(
        "SELECT COUNT(*) AS n FROM achievements "
        "WHERE user_id=? AND ymd=? AND status!='void'",
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
        "SELECT * FROM achievements WHERE user_id=? ORDER BY created_at DESC, rowid DESC LIMIT ?",
        (user_id, limit),
    ).fetchall()
    return [
        {
            "id": r["id"],
            "code": r["code"],
            "points": r["points"],
            "value_cny": r["value_cny"],
            "status": r["status"],
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
