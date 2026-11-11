"""科目与主题内容。"""
from __future__ import annotations

import sqlite3

from fastapi import APIRouter, Depends, HTTPException

from app import content_loader, db
from app.routers.session import current_user

router = APIRouter(tags=["content"])


def _section_progress(conn: sqlite3.Connection, user_id: str, topic_id: str) -> dict[str, str]:
    rows = conn.execute(
        "SELECT section_id, status FROM progress WHERE user_id=? AND topic_id=?",
        (user_id, topic_id),
    ).fetchall()
    return {r["section_id"]: r["status"] for r in rows}


@router.get("/catalog")
def get_catalog(user: sqlite3.Row = Depends(current_user)):
    cat = content_loader.catalog()
    topics = {t["id"]: t for t in cat["topics"]}

    with db.ro() as conn:
        done_counts = {}
        for row in conn.execute(
            "SELECT topic_id, COUNT(*) AS n FROM progress "
            "WHERE user_id=? AND status='done' GROUP BY topic_id",
            (user["id"],),
        ):
            done_counts[row["topic_id"]] = row["n"]

    subjects = []
    for subj in cat["subjects"]:
        items = []
        for tid in subj["topics"]:
            t = topics.get(tid)
            if not t:
                continue
            done = done_counts.get(tid, 0)
            total = len(t["sections"])
            items.append({
                "id": t["id"],
                "title": t["title"],
                "subtitle": t["subtitle"],
                "grade": t["grade"],
                "minutes": t["minutes"],
                "description": t["description"],
                "reward_card": t.get("reward_card"),
                "done": done,
                "total": total,
                "complete": done >= total,
                "percent": round(done / total * 100) if total else 0,
            })
        subjects.append({**subj, "items": items})

    return {"subjects": subjects, "sections": cat["sections"]}


@router.get("/topics/{topic_id}")
def get_topic(topic_id: str, user: sqlite3.Row = Depends(current_user)):
    try:
        data = content_loader.topic(topic_id)
        cat = content_loader.catalog()
    except content_loader.ContentError as exc:
        raise HTTPException(status_code=404, detail=str(exc))

    with db.ro() as conn:
        progress = _section_progress(conn, user["id"], topic_id)

    sections_out = []
    for sec in data["sections"]:
        meta = next((s for s in cat["sections"] if s["id"] == sec["id"]), {})
        sections_out.append({
            "id": sec["id"],
            "type": sec["type"],
            "name": meta.get("name", sec.get("name", sec["id"])),
            "icon": meta.get("icon", ""),
            "minutes": meta.get("minutes", sec.get("minutes", 0)),
            "status": progress.get(sec["id"], "open"),
            "intro": sec.get("intro", ""),
            "boss": content_loader.boss_for(topic_id, sec["id"]),
        })

    return {
        "id": data["id"],
        "subject": data["subject"],
        "title": data["title"],
        "subtitle": data["subtitle"],
        "grade": data["grade"],
        "minutes": data["minutes"],
        "description": data["description"],
        "reward_card": data.get("reward_card"),
        "sections": sections_out,
    }


@router.get("/topics/{topic_id}/sections/{section_id}")
def get_section(topic_id: str, section_id: str, user: sqlite3.Row = Depends(current_user)):
    try:
        data = content_loader.topic(topic_id)
    except content_loader.ContentError as exc:
        raise HTTPException(status_code=404, detail=str(exc))

    sec = next((s for s in data["sections"] if s["id"] == section_id), None)
    if not sec:
        raise HTTPException(status_code=404, detail="版块不存在")

    with db.ro() as conn:
        row = conn.execute(
            "SELECT status, best_score FROM progress WHERE user_id=? AND topic_id=? AND section_id=?",
            (user["id"], topic_id, section_id),
        ).fetchone()

    # 答案类字段在 strip_answers 里统一剥离
    safe = content_loader.strip_answers(sec)
    return {
        "topic_id": topic_id,
        "section": safe,
        "status": row["status"] if row else "open",
        "best_score": row["best_score"] if row else 0,
        "boss": content_loader.boss_for(topic_id, section_id),
    }


@router.get("/sections")
def section_meta():
    return content_loader.catalog()["sections"]
