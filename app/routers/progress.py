"""作答提交、判分、进度、薄弱点。"""
from __future__ import annotations

import sqlite3
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from app import content_loader, db
from app.routers.session import current_user
from app.services import grading, gacha, scoring, wrongbook, study_plan

router = APIRouter(tags=["progress"])


class SubmitIn(BaseModel):
    answers: dict[str, int] = Field(default_factory=dict)


class ReadIn(BaseModel):
    confirmed: bool = True


def _now() -> str:
    return datetime.now().isoformat(timespec="seconds")


@router.post("/topics/{topic_id}/sections/{section_id}/submit")
def submit(topic_id: str, section_id: str, body: SubmitIn, tier: str = "basic",
           user: sqlite3.Row = Depends(current_user)):
    try:
        data = content_loader.topic(topic_id)
    except content_loader.ContentError as exc:
        raise HTTPException(status_code=404, detail=str(exc))

    sec = next((s for s in data["sections"] if s["id"] == section_id), None)
    if not sec:
        raise HTTPException(status_code=404, detail="版块不存在")
    if sec["type"] == "reading":
        raise HTTPException(status_code=400, detail="该版块请用 /read 接口")
    content = content_loader.tier_content(sec, tier)
    if content is None:
        raise HTTPException(status_code=400, detail="该难度档位尚未开放")
    if tier not in content_loader.tier_ids():
        raise HTTPException(status_code=400, detail="难度档位不存在")
    # 空提交既不该判分，也不该触发答案/解析下发。
    # 注意：levels 是逐关提交的，这里只要求「非空」，全量校验由各版块渲染器保证。
    if not body.answers:
        raise HTTPException(status_code=400, detail="请先作答后再提交")

    result = grading.grade_section(content, body.answers)
    passed = _is_passed(sec, result)

    with db.tx() as conn:
        prev = conn.execute(
            "SELECT * FROM progress WHERE user_id=? AND topic_id=? AND section_id=? AND tier=?",
            (user["id"], topic_id, section_id, tier),
        ).fetchone()
        is_review = bool(prev and prev["status"] == "done")
        best = max(result["score"], prev["best_score"] if prev else 0)

        if is_review:
            conn.execute(
                "UPDATE progress SET attempts = attempts + 1, best_score = ?, updated_at=? "
                "WHERE user_id=? AND topic_id=? AND section_id=? AND tier=?",
                (best, _now(), user["id"], topic_id, section_id, tier),
            )
        else:
            conn.execute(
                "INSERT INTO progress(user_id, topic_id, section_id, tier, status, best_score, "
                "attempts, awarded, updated_at) VALUES (?,?,?,?,?,?,1,0,?) "
                "ON CONFLICT(user_id, topic_id, section_id, tier) DO UPDATE SET "
                "attempts = attempts + 1, best_score = ?, updated_at = ?",
                (user["id"], topic_id, section_id, tier, "open", result["score"], _now(),
                 best, _now()),
            )

        award = scoring.award_section(conn, user["id"], topic_id, section_id,
                                      result["score"], passed and not is_review, is_review,
                                      tier=tier)

        if passed and not is_review:
            conn.execute(
                "UPDATE progress SET status='done', awarded=1, updated_at=? "
                "WHERE user_id=? AND topic_id=? AND section_id=? AND tier=?",
                (_now(), user["id"], topic_id, section_id, tier),
            )

        section_ids = [s["id"] for s in data["sections"]]
        topic_reward = scoring.topic_complete(conn, user["id"], topic_id, section_ids)
        if sec["type"] == "boss" and passed and not is_review:
            boss_tickets = scoring.boss_reward(conn, user["id"], topic_id, section_id, passed,
                                               tier=tier)
            if boss_tickets:
                topic_reward = {**topic_reward, "tickets": topic_reward["tickets"] + boss_tickets}
        row = conn.execute("SELECT * FROM users WHERE id=?", (user["id"],)).fetchone()

        unlocked = _next_unit(data, topic_id, section_id, tier, user)

        # 答错的题写入错题本（重复答错累加次数；正常重做版块不清错，
        # 清零只能走错题本的重做流程，保证清零奖励不被刷）
        wrongbook.record_wrong(conn, user["id"], topic_id, section_id, tier,
                               grading.flatten_details(result),
                               wrongbook.questions_of(content))

    # levels 类型把明细嵌在 levels[].details 里，统一摊平供错题本与薄弱点统计使用
    details = grading.flatten_details(result)
    skills = grading.weak_skills(details)

    return {
        "passed": passed,
        "score": result["score"],
        "correct": result["correct"],
        "total": result["total"],
        "details": details,
        "levels": result.get("levels"),
        "weak_skills": skills,
        "points": award["points"],
        "points_reason": award["reason"],
        "study_reward": award['reward'],
        "total_tickets": row['tickets'],
        "total_points": row["points"],
        "is_review": is_review,
        "next_section": unlocked[0] if unlocked else None,
        "next_tier": unlocked[1] if unlocked else None,
        "tier": tier,
        "topic_reward": topic_reward,
    }


@router.post("/topics/{topic_id}/sections/{section_id}/read")
def mark_read(topic_id: str, section_id: str, body: ReadIn, tier: str = "basic",
              user: sqlite3.Row = Depends(current_user)):
    """知识点总结版块：点「我记住了」即完成。"""
    try:
        data = content_loader.topic(topic_id)
    except content_loader.ContentError as exc:
        raise HTTPException(status_code=404, detail=str(exc))

    sec = next((s for s in data["sections"] if s["id"] == section_id), None)
    if not sec or sec["type"] != "reading":
        raise HTTPException(status_code=400, detail="该版块不支持此操作")
    if content_loader.tier_content(sec, tier) is None:
        raise HTTPException(status_code=400, detail="该难度档位尚未开放")
    if not body.confirmed:
        raise HTTPException(status_code=400, detail="请确认已阅读完总结")

    with db.tx() as conn:
        prev = conn.execute(
            "SELECT * FROM progress WHERE user_id=? AND topic_id=? AND section_id=? AND tier=?",
            (user["id"], topic_id, section_id, tier),
        ).fetchone()
        is_review = bool(prev and prev["status"] == "done")

        conn.execute(
            "INSERT INTO progress(user_id, topic_id, section_id, tier, status, best_score, "
            "attempts, awarded, updated_at) VALUES (?,?,?,?,'done',100,1,0,?) "
            "ON CONFLICT(user_id, topic_id, section_id, tier) DO UPDATE SET "
            "status='done', attempts = attempts + 1, updated_at = ?",
            (user["id"], topic_id, section_id, tier, _now(), _now()),
        )
        award = scoring.award_section(conn, user["id"], topic_id, section_id, 100,
                                      not is_review, is_review, tier=tier)
        conn.execute(
            "UPDATE progress SET awarded=1 WHERE user_id=? AND topic_id=? AND section_id=? AND tier=?",
            (user["id"], topic_id, section_id, tier),
        )

        section_ids = [s["id"] for s in data["sections"]]
        topic_reward = scoring.topic_complete(conn, user["id"], topic_id, section_ids)
        row = conn.execute("SELECT * FROM users WHERE id=?", (user["id"],)).fetchone()
        unlocked = _next_unit(data, topic_id, section_id, tier, user)

    return {
        "ok": True,
        "study_reward": award['reward'],
        "total_tickets": row['tickets'],
        "points": award["points"],
        "total_points": row["points"],
        "is_review": is_review,
        "tier": tier,
        "next_section": unlocked[0] if unlocked else None,
        "next_tier": unlocked[1] if unlocked else None,
        "topic_reward": topic_reward,
    }


@router.get("/progress")
def get_progress(user: sqlite3.Row = Depends(current_user)):
    with db.ro() as conn:
        rows = conn.execute(
            "SELECT * FROM progress WHERE user_id=? ORDER BY updated_at DESC", (user["id"],)
        ).fetchall()
    return {
        "items": [
            {
                "topic_id": r["topic_id"],
                "section_id": r["section_id"],
                "tier": r["tier"],
                "status": r["status"],
                "best_score": r["best_score"],
                "attempts": r["attempts"],
                "updated_at": r["updated_at"],
            }
            for r in rows
        ]
    }


@router.get("/stats/skills")
def skill_stats(user: sqlite3.Row = Depends(current_user)):
    """按 skill 聚合正确率，用于薄弱点提示。"""
    agg: dict[str, dict] = {}
    for t in content_loader.catalog()["topics"]:
        try:
            data = content_loader.topic(t["id"])
        except content_loader.ContentError:
            continue
        for sec in data["sections"]:
            for content in content_loader.section_tiers(sec).values():
                for q in _iter_questions(content):
                    skill = q.get("skill")
                    if not skill:
                        continue
                    agg.setdefault(skill, {"skill": skill, "total": 0, "topics": set()})
                    agg[skill]["total"] += 1
                    agg[skill]["topics"].add(t["id"])

    return {
        "skills": [
            {"skill": v["skill"], "questions": v["total"], "topics": sorted(v["topics"])}
            for v in sorted(agg.values(), key=lambda x: -x["total"])
        ]
    }


def _iter_questions(section: dict):
    t = section.get("type")
    if t in ("quiz", "boss"):
        yield from section.get("questions", [])
    elif t == "levels":
        for lv in section.get("levels", []):
            yield from lv.get("questions", [])
    elif t == "myths":
        for m in section.get("myths", []):
            yield m.get("check", {})


def _is_passed(section: dict, result: dict) -> bool:
    t = section["type"]
    if t == "levels":
        return result["all_passed"]
    if t == "quiz":
        return result["score"] >= 60
    if t == "myths":
        return result["score"] >= 66
    if t == "steps":
        # 计划里的完成判定是「完成全部步骤」；空答案 / 半途提交不能算通关。
        details = result.get("details", [])
        return bool(details) and all(d.get("picked") is not None for d in details)
    if t == "boss":
        return result["score"] >= 100
    return False


def _next_unit(data: dict, topic_id: str, current_section: str,
               current_tier: str, user=None) -> tuple[str, str] | None:
    """下一学习单元：基础的六个版块走完，再进进阶、高级。"""
    pairs = content_loader.topic_pairs(topic_id)
    plan = study_plan.profile(user)
    if plan and plan['active'] and (current_section, current_tier) in study_plan.pairs(topic_id):
        pairs = study_plan.pairs(topic_id)
    try:
        idx = pairs.index((current_section, current_tier))
    except ValueError:
        return None
    return pairs[idx + 1] if idx + 1 < len(pairs) else None
