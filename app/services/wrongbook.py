"""错题本：记录、按主题重做、清零奖励。

设计要点
- 记录：submit 判分后，把答错的题按 (user, 主题, 版块, 档位, 题目) 唯一 upsert，
  重复答错累加 wrong_count 并刷新最近选项；快照题干/选项/答案/解析，
  之后内容文件改动不影响错题重做。
- 清零：只在错题本的重做流程里清（正常重做版块不清错，防止「故意做错再重做」刷奖励）；
  一个主题的错题全部清完时发清零奖励，按 (user, 主题, 日期) 幂等，一天最多一次。
- AI：分析结果缓存在行上；同一题同一错选不重复计费。
"""
from __future__ import annotations

import hashlib
import json
import sqlite3
from datetime import date

from app import content_loader


def _cfg() -> dict:
    return content_loader.rewards().get("wrongbook", {})


def today_str() -> str:
    return date.today().isoformat()


def _row_id(user_id: str, topic_id: str, section_id: str, tier: str, question_id: str) -> str:
    raw = f"{user_id}|{topic_id}|{section_id}|{tier}|{question_id}"
    return "wq_" + hashlib.sha1(raw.encode("utf-8")).hexdigest()[:12]


def record_wrong(conn: sqlite3.Connection, user_id: str, topic_id: str,
                 section_id: str, tier: str, details: list[dict],
                 questions: dict[str, dict]) -> int:
    """把判分结果里的错题写入错题本，返回新增/更新的行数。

    questions: {question_id: {stem, options, answer, explain, skill}} —— 来自判分内容。
    """
    now = today_str()
    n = 0
    for d in details:
        if d.get("correct"):
            continue
        qid = d["id"]
        q = questions.get(qid)
        if not q:
            continue
        rid = _row_id(user_id, topic_id, section_id, tier, qid)
        existing = conn.execute(
            "SELECT id, wrong_count, status FROM wrong_questions WHERE id = ?", (rid,)
        ).fetchone()
        if existing:
            conn.execute(
                "UPDATE wrong_questions SET picked=?, wrong_count=wrong_count+1, "
                "last_wrong_at=?, status='open', cleared_at=NULL WHERE id=?",
                (d.get("picked"), now, rid),
            )
        else:
            conn.execute(
                "INSERT INTO wrong_questions(id, user_id, topic_id, section_id, tier, "
                "question_id, skill, stem, options_json, answer, explain, picked, "
                "created_at, last_wrong_at) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                (rid, user_id, topic_id, section_id, tier, qid,
                 d.get("skill", ""),
                 q.get("stem", ""),
                 json.dumps(q.get("options", []), ensure_ascii=False),
                 d.get("answer", 0),
                 d.get("explain", ""),
                 d.get("picked"),
                 now, now),
            )
        n += 1
    return n


def questions_of(content: dict) -> dict[str, dict]:
    """从判分内容里取 {question_id: 题目}，与 grading 的 id 口径一致。"""
    out: dict[str, dict] = {}
    t = content.get("type")
    if t in ("quiz", "boss"):
        for q in content.get("questions", []):
            out[q["id"]] = q
    elif t == "levels":
        for lv in content.get("levels", []):
            for q in lv.get("questions", []):
                out[q["id"]] = q
    elif t == "myths":
        for i, m in enumerate(content.get("myths", [])):
            chk = m.get("check", {})
            out[f"m{i}"] = {**chk, "stem": chk.get("stem", m.get("title", "")),
                            "explain": chk.get("explain", "")}
    elif t == "steps":
        for pi, p in enumerate(content.get("problems", [])):
            for si, st in enumerate(p.get("steps", [])):
                out[f"p{pi}s{si}"] = {**st, "stem": st.get("ask", ""),
                                      "explain": st.get("explain", "")}
    return out


def summary(conn: sqlite3.Connection, user_id: str) -> dict:
    """按主题汇总错题。"""
    cfg = _cfg()
    rows = conn.execute(
        "SELECT topic_id, "
        "SUM(CASE WHEN status='open' THEN 1 ELSE 0 END) AS open_n, "
        "SUM(CASE WHEN status='cleared' THEN 1 ELSE 0 END) AS cleared_n, "
        "MAX(last_wrong_at) AS last_at "
        "FROM wrong_questions WHERE user_id=? GROUP BY topic_id "
        "ORDER BY open_n DESC, last_at DESC",
        (user_id,),
    ).fetchall()

    cat = {t["id"]: t for t in content_loader.catalog()["topics"]}
    topics = []
    for r in rows:
        t = cat.get(r["topic_id"], {})
        topics.append({
            "topic_id": r["topic_id"],
            "title": t.get("title", r["topic_id"]),
            "subject": t.get("subject", ""),
            "subtitle": t.get("subtitle", ""),
            "open": r["open_n"],
            "cleared": r["cleared_n"],
            "last_at": r["last_at"],
        })
    open_total = sum(t["open"] for t in topics)
    return {
        "topics": topics,
        "open_total": open_total,
        "clear_bonus": int(cfg.get("clear_bonus", 0)),
        "total_count": sum(t["open"] + t["cleared"] for t in topics),
    }


def topic_items(conn: sqlite3.Connection, user_id: str, topic_id: str,
                status: str = "open") -> list[dict]:
    rows = conn.execute(
        "SELECT * FROM wrong_questions WHERE user_id=? AND topic_id=? AND status=? "
        "ORDER BY last_wrong_at DESC",
        (user_id, topic_id, status),
    ).fetchall()
    items = []
    for r in rows:
        options = json.loads(r["options_json"])
        items.append({
            "id": r["id"],
            "topic_id": r["topic_id"],
            "section_id": r["section_id"],
            "tier": r["tier"],
            "skill": r["skill"],
            "stem": r["stem"],
            "options": options,
            "picked": r["picked"],
            "answer": r["answer"],
            "explain": r["explain"],
            "wrong_count": r["wrong_count"],
            "ai": json.loads(r["ai_analysis"]) if r["ai_analysis"] else None,
            "last_wrong_at": r["last_wrong_at"],
        })
    return items


def redo(conn: sqlite3.Connection, user: sqlite3.Row, topic_id: str,
         answers: dict[str, int]) -> dict:
    """错题重做判分：答对清零，答错继续留库并累加次数。"""
    rows = conn.execute(
        "SELECT * FROM wrong_questions WHERE user_id=? AND topic_id=? AND status='open'",
        (user["id"], topic_id),
    ).fetchall()
    if not rows:
        raise ValueError("这个主题当前没有待清零的错题")

    results = []
    cleared_now = 0
    re_wrong = 0
    for r in rows:
        picked = answers.get(r["id"])
        if picked is None:
            results.append({"id": r["id"], "skipped": True,
                            "stem": r["stem"], "answer": r["answer"],
                            "explain": r["explain"], "correct": False})
            continue
        total = len(json.loads(r["options_json"]))
        correct = picked == r["answer"] and 0 <= picked < total
        if correct:
            conn.execute(
                "UPDATE wrong_questions SET status='cleared', cleared_at=?, last_wrong_at=? "
                "WHERE id=? AND status='open'",
                (today_str(), today_str(), r["id"]),
            )
            cleared_now += 1
        else:
            conn.execute(
                "UPDATE wrong_questions SET picked=?, wrong_count=wrong_count+1, "
                "last_wrong_at=? WHERE id=? AND status='open'",
                (picked, today_str(), r["id"]),
            )
            re_wrong += 1
        results.append({
            "id": r["id"], "stem": r["stem"], "picked": picked,
            "answer": r["answer"], "correct": correct, "cleared": correct,
            "explain": r["explain"], "skill": r["skill"],
        })

    bonus = 0
    remaining = conn.execute(
        "SELECT COUNT(*) AS n FROM wrong_questions "
        "WHERE user_id=? AND topic_id=? AND status='open'",
        (user["id"], topic_id),
    ).fetchone()["n"]
    if cleared_now and remaining == 0:
        bonus = _clear_bonus(conn, user["id"], topic_id)

    return {
        "results": results,
        "cleared": cleared_now,
        "re_wrong": re_wrong,
        "remaining": remaining,
        "bonus": bonus,
    }


def _clear_bonus(conn: sqlite3.Connection, user_id: str, topic_id: str) -> int:
    """清零奖励：一个主题一天最多发一次。"""
    cfg = _cfg()
    bonus = int(cfg.get("clear_bonus", 0))
    if bonus <= 0:
        return 0
    key = f"wrongbook_clear:{user_id}:{topic_id}:{today_str()}"
    cur = conn.execute(
        "INSERT OR IGNORE INTO events(user_id, key, kind, payload, created_at) "
        "VALUES (?,?,?,?,?)",
        (user_id, key, "wrongbook_clear", json.dumps({"topic": topic_id, "points": bonus},
                                                      ensure_ascii=False), today_str()),
    )
    if cur.rowcount != 1:
        return 0
    conn.execute("UPDATE users SET points = points + ? WHERE id = ?", (bonus, user_id))
    return bonus


def save_ai(conn: sqlite3.Connection, user_id: str, wq_id: str, analysis: dict,
            model: str) -> None:
    conn.execute(
        "UPDATE wrong_questions SET ai_analysis=?, ai_model=?, ai_at=? "
        "WHERE id=? AND user_id=?",
        (json.dumps(analysis, ensure_ascii=False), model, today_str(), wq_id, user_id),
    )


def ai_pending(conn: sqlite3.Connection, user_id: str, wq_id: str) -> sqlite3.Row | None:
    return conn.execute(
        "SELECT * FROM wrong_questions WHERE id=? AND user_id=?",
        (wq_id, user_id),
    ).fetchone()


def ai_used_today(conn: sqlite3.Connection, user_id: str) -> int:
    return conn.execute(
        "SELECT COUNT(*) AS n FROM events WHERE user_id=? AND kind='ai' "
        "AND substr(created_at,1,10)=?",
        (user_id, today_str()),
    ).fetchone()["n"]
