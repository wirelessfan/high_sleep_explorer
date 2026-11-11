"""科目与主题内容。"""
from __future__ import annotations

import sqlite3
from datetime import date, datetime

from fastapi import APIRouter, Depends, HTTPException, Query

from app import content_loader, db
from app.routers.session import current_user

router = APIRouter(tags=["content"])


def _section_progress(conn: sqlite3.Connection, user_id: str, topic_id: str) -> dict[tuple[str, str], str]:
    """{(section_id, tier): status}"""
    rows = conn.execute(
        "SELECT section_id, tier, status FROM progress WHERE user_id=? AND topic_id=?",
        (user_id, topic_id),
    ).fetchall()
    return {(r["section_id"], r["tier"]): r["status"] for r in rows}


@router.get("/catalog")
def get_catalog(user: sqlite3.Row = Depends(current_user)):
    cat = content_loader.catalog()
    topics = {t["id"]: t for t in cat["topics"]}

    with db.ro() as conn:
        done_rows = conn.execute(
            "SELECT topic_id, section_id, tier FROM progress "
            "WHERE user_id=? AND status='done'",
            (user["id"],),
        ).fetchall()
    done_set = {(r["topic_id"], r["section_id"], r["tier"]) for r in done_rows}

    subjects = []
    for subj in cat["subjects"]:
        items = []
        for tid in subj["topics"]:
            t = topics.get(tid)
            if not t:
                continue
            pairs = content_loader.topic_pairs(tid)
            done = sum(1 for sid, tier in pairs if (tid, sid, tier) in done_set)
            total = len(pairs)
            tier_progress = {}
            for tier in content_loader.tier_ids():
                tier_pairs = [p for p in pairs if p[1] == tier]
                if not tier_pairs:
                    continue
                tier_progress[tier] = {
                    "done": sum(1 for sid, _ in tier_pairs if (tid, sid, tier) in done_set),
                    "total": len(tier_pairs),
                }
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
                "tiers": tier_progress,
            })
        subjects.append({**subj, "items": items})

    return {"subjects": subjects, "sections": cat["sections"], "tiers": content_loader.tier_meta()}


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
        tiers = content_loader.section_tier_list(sec)
        for tier in tiers:
            tier["status"] = progress.get((sec["id"], tier["id"]), "open")
        sections_out.append({
            "id": sec["id"],
            "type": sec["type"],
            "name": meta.get("name", sec.get("name", sec["id"])),
            "icon": meta.get("icon", ""),
            "minutes": meta.get("minutes", sec.get("minutes", 0)),
            # status 保留为基础档状态，兼容只认识单档的调用方
            "status": progress.get((sec["id"], "basic"), "open"),
            "intro": sec.get("intro", ""),
            "tiers": tiers,
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
        "tiers": content_loader.tier_meta(),
    }


@router.get("/topics/{topic_id}/sections/{section_id}")
def get_section(topic_id: str, section_id: str, tier: str = "basic",
                user: sqlite3.Row = Depends(current_user)):
    try:
        data = content_loader.topic(topic_id)
    except content_loader.ContentError as exc:
        raise HTTPException(status_code=404, detail=str(exc))

    sec = next((s for s in data["sections"] if s["id"] == section_id), None)
    if not sec:
        raise HTTPException(status_code=404, detail="版块不存在")

    tiers = content_loader.section_tier_list(sec)
    tier_meta = next((t for t in tiers if t["id"] == tier), None)
    if tier_meta is None:
        raise HTTPException(status_code=400, detail="难度档位不存在")

    with db.ro() as conn:
        rows = conn.execute(
            "SELECT tier, status, best_score FROM progress "
            "WHERE user_id=? AND topic_id=? AND section_id=?",
            (user["id"], topic_id, section_id),
        ).fetchall()
    by_tier = {r["tier"]: r for r in rows}
    for item in tiers:
        item["status"] = by_tier[item["id"]]["status"] if item["id"] in by_tier else "open"
    row = by_tier.get(tier)

    content = content_loader.tier_content(sec, tier)
    payload = {
        "topic_id": topic_id,
        "tier": tier_meta,
        "tiers": tiers,
        "available": content is not None,
        "section": content_loader.strip_answers(content) if content else None,
        "status": row["status"] if row else "open",
        "best_score": row["best_score"] if row else 0,
        "boss": content_loader.boss_for(topic_id, section_id),
    }
    return payload


@router.get("/sections")
def section_meta():
    return content_loader.catalog()["sections"]


_WEEKDAYS = ("周一", "周二", "周三", "周四", "周五", "周六", "周日")


def _parse_day(value: str | None):
    if not value:
        return date.today()
    try:
        return datetime.strptime(value, "%Y-%m-%d").date()
    except ValueError:
        raise HTTPException(status_code=400, detail="date 需为 YYYY-MM-DD")


@router.get("/history")
def get_history(date_str: str | None = Query(default=None, alias="date"),
                user: sqlite3.Row = Depends(current_user)):
    """历史上的今天：某月某日的科学事件；无当日条目时回退到最近一条。"""
    day = _parse_day(date_str)
    info = content_loader.history_for(day)
    entry = info["entry"]
    if not entry:
        raise HTTPException(status_code=404, detail="历史事件库为空")

    topic = None
    if entry.get("topic"):
        meta = next((t for t in content_loader.catalog()["topics"] if t["id"] == entry["topic"]), None)
        if meta:
            topic = {"id": meta["id"], "title": meta["title"], "subject": meta["subject"]}

    return {
        "date": day.isoformat(),
        "weekday": _WEEKDAYS[day.weekday()],
        "fallback": info["fallback"],
        "offset_days": info["offset"],
        "entry_date": f"{entry['month']} 月 {entry['day']} 日",
        "total": info["total"],
        "entry": {
            "year": entry.get("year"),
            "field": entry.get("field", ""),
            "person": entry.get("person", ""),
            "title": entry.get("title", ""),
            "story": entry.get("story", ""),
            "learn": entry.get("learn", ""),
        },
        "topic": topic,
    }


@router.get("/daily")
def get_daily(date_str: str | None = Query(default=None, alias="date"),
              user: sqlite3.Row = Depends(current_user)):
    """每日主题：节日特辑优先，否则按日期轮转。

    `date` 查询参数只用于调试与测试（例如 ?date=2026-11-11 查看双十一特辑）。
    """
    day = _parse_day(date_str)
    info = content_loader.daily_for(day)
    cat = content_loader.catalog()
    topic_meta = next((t for t in cat["topics"] if t["id"] == info["topic_id"]), None)
    if not topic_meta:
        raise HTTPException(status_code=404, detail="每日主题配置引用了不存在的主题")

    subject = next((s for s in cat["subjects"] if s["id"] == topic_meta["subject"]), {})
    pairs = content_loader.topic_pairs(topic_meta["id"])
    total = len(pairs)
    with db.ro() as conn:
        row = conn.execute(
            "SELECT COUNT(*) AS n FROM progress WHERE user_id=? AND topic_id=? AND status='done'",
            (user["id"], topic_meta["id"]),
        ).fetchone()
    done = row["n"] if row else 0

    special = info["special"]
    return {
        "date": day.isoformat(),
        "weekday": _WEEKDAYS[day.weekday()],
        "special": {
            "id": special["id"],
            "title": special["title"],
            "tagline": special.get("tagline", ""),
            "description": special.get("description", ""),
            "aside": special.get("aside", ""),
            "emoji": special.get("emoji", ""),
            "accent": special.get("accent", "fresh"),
            "digest": special.get("digest", []),
        } if special else None,
        "quote": info["quote"],
        "topic": {
            "id": topic_meta["id"],
            "subject": topic_meta["subject"],
            "subject_name": subject.get("name", ""),
            "title": topic_meta["title"],
            "subtitle": topic_meta["subtitle"],
            "grade": topic_meta["grade"],
            "minutes": topic_meta["minutes"],
            "description": topic_meta["description"],
            "reward_card": topic_meta.get("reward_card"),
            "done": done,
            "total": total,
            "complete": done >= total,
            "percent": round(done / total * 100) if total else 0,
        },
    }
