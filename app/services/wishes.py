"""许愿墙：用户提改进意见，每条 +1 盲盒券（每人每天限 3 条）。

设计要点
- 奖励与提交在同一事务内：先 INSERT wishes，再发券，最后写幂等事件；
- 每日条数按 wishes 表当天计数（不靠事件，便于管理员删除后重新计数）；
- 同人同内容去重（规范化空白），避免粘贴刷券。
"""
from __future__ import annotations

import sqlite3
import uuid
from datetime import date, datetime

from app import content_loader
from app.services import blindbox, events


def _cfg() -> dict:
    return content_loader.rewards()["wishes"]


def _now() -> str:
    return datetime.now().isoformat(timespec="seconds")


def _today() -> str:
    return date.today().isoformat()


def _norm(text: str) -> str:
    return " ".join((text or "").split())


def today_count(conn: sqlite3.Connection, user_id: str) -> int:
    return conn.execute(
        "SELECT COUNT(*) AS n FROM wishes WHERE user_id=? AND substr(created_at,1,10)=?",
        (user_id, _today()),
    ).fetchone()["n"]


def submit(conn: sqlite3.Connection, user: sqlite3.Row, content: str) -> dict:
    cfg = _cfg()
    text = _norm(content)
    if len(text) < int(cfg.get("min_len", 5)):
        raise ValueError(f"意见太短了，至少 {cfg.get('min_len', 5)} 个字")
    if len(text) > int(cfg.get("max_len", 300)):
        raise ValueError(f"意见太长了，最多 {cfg.get('max_len', 300)} 个字")

    per_day = int(cfg.get("per_day", 3))
    used = today_count(conn, user["id"])
    if used >= per_day:
        raise ValueError(f"今天已经提了 {per_day} 条啦，明天再来许愿吧")

    dup = conn.execute(
        "SELECT 1 FROM wishes WHERE user_id=? AND content=? LIMIT 1",
        (user["id"], text),
    ).fetchone()
    if dup:
        raise ValueError("这条意见你已经提过了")

    wish_id = "w_" + uuid.uuid4().hex[:12]
    conn.execute(
        "INSERT INTO wishes(id, user_id, content, status, created_at) VALUES (?,?,?,?,?)",
        (wish_id, user["id"], text, "open", _now()),
    )

    bonus = int(cfg.get("ticket_reward", 1))
    blindbox.add_tickets(conn, user["id"], bonus)
    events.log(conn, user["id"], f"wish:{wish_id}", "wish",
               {"wish": wish_id, "bonus": bonus})

    left = max(0, per_day - used - 1)
    return {
        "id": wish_id,
        "content": text,
        "status": "open",
        "bonus": bonus,
        "left_today": left,
        "per_day": per_day,
        "created_at": _now(),
    }


def wall(conn: sqlite3.Connection, user_id: str, limit: int = 100) -> dict:
    """公开许愿墙：昵称 + 内容 + 状态 + 官方回复。

    is_admin=True 时前端会在每条意见上直接给出「回复/改状态」入口，
    管理员不必跳到管理中心也能处理。
    """
    rows = conn.execute(
        "SELECT w.id, w.content, w.status, w.reply, w.reply_at, w.created_at, w.user_id, "
        "COALESCE(u.nickname, '匿名同学') AS nickname "
        "FROM wishes w LEFT JOIN users u ON u.id = w.user_id "
        "ORDER BY w.created_at DESC LIMIT ?",
        (max(1, min(limit, 200)),),
    ).fetchall()
    items = [{
        "id": r["id"],
        "content": r["content"],
        "status": r["status"],
        "reply": r["reply"],
        "reply_at": r["reply_at"],
        "created_at": r["created_at"],
        "nickname": r["nickname"],
        "mine": r["user_id"] == user_id,
        "user_id": r["user_id"],
    } for r in rows]

    cfg = _cfg()
    per_day = int(cfg.get("per_day", 3))
    used = today_count(conn, user_id)
    is_admin = bool(conn.execute(
        "SELECT 1 FROM users WHERE id=? AND role='admin'", (user_id,)
    ).fetchone())
    return {
        "items": items,
        "is_admin": is_admin,
        "mine_today": used,
        "left_today": max(0, per_day - used),
        "per_day": per_day,
        "ticket_reward": int(cfg.get("ticket_reward", 1)),
        "statuses": {"open": "待处理", "planned": "已采纳", "done": "已实现"},
    }


def moderate(conn: sqlite3.Connection, wish_id: str, status: str,
             reply: str | None) -> dict:
    """管理员：改状态 / 写回复。状态只会停在提交时的 open；过渡到 planned/done。"""
    if status not in ("open", "planned", "done"):
        raise ValueError("状态只能是 open / planned / done")
    row = conn.execute("SELECT id FROM wishes WHERE id=?", (wish_id,)).fetchone()
    if not row:
        raise ValueError("意见不存在")

    text = _norm(reply or "")[:300] or None
    conn.execute(
        "UPDATE wishes SET status=?, reply=?, reply_at=? WHERE id=?",
        (status, text, _now() if text else None, wish_id),
    )
    r = conn.execute(
        "SELECT id, content, status, reply, reply_at, created_at FROM wishes WHERE id=?",
        (wish_id,),
    ).fetchone()
    return {
        "id": r["id"], "content": r["content"], "status": r["status"],
        "reply": r["reply"], "reply_at": r["reply_at"], "created_at": r["created_at"],
    }


def admin_list(conn: sqlite3.Connection, limit: int = 200) -> list[dict]:
    rows = conn.execute(
        "SELECT w.id, w.content, w.status, w.reply, w.reply_at, w.created_at, w.user_id, "
        "COALESCE(u.nickname, '匿名') AS nickname, COALESCE(u.username, '') AS username "
        "FROM wishes w LEFT JOIN users u ON u.id = w.user_id "
        "ORDER BY CASE w.status WHEN 'open' THEN 0 ELSE 1 END, w.created_at DESC "
        "LIMIT ?",
        (max(1, min(limit, 500)),),
    ).fetchall()
    return [{
        "id": r["id"], "content": r["content"], "status": r["status"],
        "reply": r["reply"], "reply_at": r["reply_at"], "created_at": r["created_at"],
        "nickname": r["nickname"], "username": r["username"],
    } for r in rows]