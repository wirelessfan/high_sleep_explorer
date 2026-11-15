"""积分规则：签到、版块首通、复习、套装。"""
from __future__ import annotations

import sqlite3
from datetime import date, timedelta

from app import content_loader
from app.services import events, study_plan


def _cfg() -> dict:
    return content_loader.rewards()


def today_str() -> str:
    # 服务器已设 Asia/Shanghai，这里直接用本地日期
    return date.today().isoformat()


def yesterday_str() -> str:
    return (date.today() - timedelta(days=1)).isoformat()


def checkin(conn: sqlite3.Connection, user: sqlite3.Row) -> dict:
    """签到：返回本次得分与连签状态。已签到则幂等返回。"""
    cfg = _cfg()["checkin"]
    day = today_str()
    user_id = user["id"]

    existing = conn.execute(
        "SELECT * FROM checkins WHERE user_id = ? AND day = ?", (user_id, day)
    ).fetchone()
    if existing:
        return {
            "already": True,
            "day": day,
            "points": existing["points"],
            "streak": existing["streak"],
            "total_points": user["points"],
        }

    last = user["last_checkin"]
    if last == yesterday_str():
        streak = user["streak"] + 1
    elif last == day:
        streak = user["streak"]
    else:
        streak = 1

    bonus = min(cfg["max_bonus"], cfg["streak_step"] * (streak - 1))
    points = cfg["base"] + bonus

    conn.execute(
        "INSERT INTO checkins(user_id, day, points, streak) VALUES (?,?,?,?)",
        (user_id, day, points, streak),
    )
    conn.execute(
        "UPDATE users SET points = points + ?, streak = ?, last_checkin = ?, last_seen = ? WHERE id = ?",
        (points, streak, day, day, user_id),
    )

    tickets_awarded = 0
    tcfg = _cfg()["tickets"]
    if streak == 3:
        tickets_awarded += tcfg["streak_3"]
    elif streak == 7:
        tickets_awarded += tcfg["streak_7"]
    if tickets_awarded:
        conn.execute("UPDATE users SET tickets = tickets + ? WHERE id = ?", (tickets_awarded, user_id))

    return {
        "already": False,
        "day": day,
        "points": points,
        "base": cfg["base"],
        "bonus": bonus,
        "streak": streak,
        "tickets": tickets_awarded,
        "total_points": user["points"] + points,
    }


def section_points(section_id: str) -> int:
    return int(_cfg()["sections"].get(section_id, 0))


def tier_multiplier(tier: str) -> float:
    """档位系数：基础 1.0 / 进阶 1.3 / 高级 1.6（见 catalog.tiers）。"""
    meta = content_loader.tier_meta_of(tier) or {}
    try:
        return float(meta.get("multiplier", 1.0))
    except (TypeError, ValueError):
        return 1.0


def award_section(conn: sqlite3.Connection, user_id: str, topic_id: str, section_id: str,
                  score: int, passed: bool, is_review: bool, tier: str = "basic") -> dict:
    """版块完成发分。首通按版块分值，复习固定 +3（日上限）。

    幂等：同一次提交不会重复发分（由 events.key 唯一约束保证）。
    """
    cfg = _cfg()
    reward = study_plan.reward_context(conn, user_id, topic_id, section_id, tier)
    multiplier = reward['points_multiplier']
    base_points = 0
    row = conn.execute(
        "SELECT * FROM progress WHERE user_id=? AND topic_id=? AND section_id=? AND tier=?",
        (user_id, topic_id, section_id, tier),
    ).fetchone()

    already_awarded = bool(row and row["awarded"])
    points = 0
    reason = ""

    if is_review or already_awarded:
        # 复习：固定分，检查日上限
        used = conn.execute(
            "SELECT COALESCE(SUM(CAST(COALESCE(json_extract(payload,'$.base_points'),json_extract(payload,'$.points')) AS INTEGER)),0) AS s "
            "FROM events WHERE user_id=? AND kind='review' AND substr(created_at,1,10)=?",
            (user_id, today_str()),
        ).fetchone()["s"]
        remain = max(0, cfg["review_daily_cap"] - int(used))
        base_points = min(cfg["review_points"], remain)
        points = base_points * multiplier
        reason = "review"
        # 事件必须写成功才发分；冲突说明这次提交已经处理过。
        if points > 0 and not _log_event(
            conn, user_id, f"review:{topic_id}:{section_id}:{tier}:{today_str()}:{used}",
            "review", {"points": points, "base_points": base_points, "reward": reward, "section": section_id, "tier": tier}
        ):
            points = 0
    elif passed:
        base_points = round(section_points(section_id) * tier_multiplier(tier))
        points = base_points * multiplier
        reason = "first"
        if not _log_event(conn, user_id, f"first:{topic_id}:{section_id}:{tier}", "first",
                          {"points": points, "base_points": base_points, "reward": reward, "section": section_id, "tier": tier}):
            points = 0

    if points:
        conn.execute("UPDATE users SET points = points + ?, last_seen = ? WHERE id = ?",
                     (points, today_str(), user_id))

    return {"points": points, "reason": reason, "already_awarded": already_awarded, "reward": reward}


def _log_event(conn: sqlite3.Connection, user_id: str, key: str, kind: str, payload: dict) -> bool:
    """写入事件，key 冲突说明已处理过，返回 False。

    统一走 events.log：业务键会加上 user_id 前缀，避免跨用户互相挡住发奖。
    """
    return events.log(conn, user_id, key, kind, payload)


def topic_complete(conn: sqlite3.Connection, user_id: str, topic_id: str, section_ids: list[str]) -> dict:
    """检查主题是否全通，全通则发券 + 首次集卡奖励。"""
    try:
        pairs = content_loader.topic_pairs(topic_id)
    except content_loader.ContentError:
        pairs = [(sid, "basic") for sid in section_ids]
    if not pairs:  # 内容缺失时退回到调用方给的版块列表
        pairs = [(sid, "basic") for sid in section_ids]

    rows = conn.execute(
        "SELECT section_id, tier, status FROM progress WHERE user_id=? AND topic_id=?",
        (user_id, topic_id),
    ).fetchall()
    done = {(r["section_id"], r["tier"]) for r in rows if r["status"] == "done"}
    complete = all(pair in done for pair in pairs)

    awarded = {"tickets": 0, "complete": False}
    if not complete:
        return awarded

    cfg = _cfg()["tickets"]
    user = conn.execute('SELECT * FROM users WHERE id=?', (user_id,)).fetchone()
    plan = study_plan.profile(user)
    multiplier = plan['tickets_multiplier'] if plan and study_plan.pairs(topic_id) else 1
    tickets = cfg['topic_complete'] * multiplier
    if _log_event(conn, user_id, f"topic_done:{topic_id}", "topic_complete", {"tickets": tickets, "multiplier": multiplier}):
        conn.execute("UPDATE users SET tickets = tickets + ? WHERE id = ?",
                     (tickets, user_id))
        awarded = {"tickets": tickets, "complete": True}
    return awarded


def boss_reward(conn: sqlite3.Connection, user_id: str, topic_id: str, section_id: str,
                passed: bool, tier: str = "basic") -> int:
    """Boss 版块首通额外发卡包（与 50 积分分开计）。"""
    if not passed:
        return 0
    tickets = int(_cfg()["tickets"].get("boss_first", 0))
    reward = study_plan.reward_context(conn, user_id, topic_id, section_id, tier)
    tickets *= reward['tickets_multiplier']
    if tickets <= 0:
        return 0
    if _log_event(conn, user_id, f"boss:{topic_id}:{section_id}:{tier}", "boss_first",
                  {"tickets": tickets, "tier": tier, "reward": reward}):
        conn.execute("UPDATE users SET tickets = tickets + ? WHERE id = ?", (tickets, user_id))
        return tickets
    return 0


def award_set(conn: sqlite3.Connection, user_id: str, set_id: str, points: int) -> int:
    if _log_event(conn, user_id, f"set:{set_id}", "set", {"set": set_id, "points": points}):
        conn.execute("UPDATE users SET points = points + ? WHERE id = ?", (points, user_id))
        return points
    return 0
