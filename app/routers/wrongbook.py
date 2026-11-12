"""错题本与 AI 错误分析。"""
from __future__ import annotations

import json
import sqlite3
import uuid

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from app import db
from app.routers.session import current_user
from app.services import ai_client, events, wrongbook

router = APIRouter(tags=["wrongbook"])


class RedoIn(BaseModel):
    answers: dict[str, int] = Field(default_factory=dict)


class AnalyzeIn(BaseModel):
    ids: list[str] = Field(default_factory=list)


@router.get("/wrongbook")
def get_wrongbook(user: sqlite3.Row = Depends(current_user)):
    """按主题汇总 + 全部待清零题目（含已缓存的 AI 分析）。"""
    with db.ro() as conn:
        st = wrongbook.summary(conn, user["id"])
        items = []
        for t in st["topics"]:
            for it in wrongbook.topic_items(conn, user["id"], t["topic_id"]):
                items.append({**it, "topic_title": t["title"], "subject": t["subject"]})
        used = wrongbook.ai_used_today(conn, user["id"])
    return {
        "summary": st,
        "items": items,
        "ai": {**ai_client.config_public(), "used_today": used},
    }


@router.get("/wrongbook/{topic_id}")
def get_topic_wrongbook(topic_id: str, user: sqlite3.Row = Depends(current_user)):
    with db.ro() as conn:
        items = wrongbook.topic_items(conn, user["id"], topic_id, "open")
        cleared = wrongbook.topic_items(conn, user["id"], topic_id, "cleared")
    return {"topic_id": topic_id, "items": items, "cleared": cleared}


@router.post("/wrongbook/{topic_id}/redo")
def redo_topic(topic_id: str, body: RedoIn, user: sqlite3.Row = Depends(current_user)):
    """错题重做：答对清零；该主题全部清零时发清零奖励。"""
    with db.tx() as conn:
        fresh = conn.execute("SELECT * FROM users WHERE id=?", (user["id"],)).fetchone()
        try:
            res = wrongbook.redo(conn, fresh, topic_id, body.answers)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc))
        row = conn.execute("SELECT points FROM users WHERE id=?", (user["id"],)).fetchone()
    res["points"] = row["points"]
    return res


@router.post("/wrongbook/ai")
def analyze(body: AnalyzeIn, user: sqlite3.Row = Depends(current_user)):
    """对错题生成 AI 错误分析与改进建议（结果缓存，不重复计费）。"""
    if not ai_client.enabled():
        raise HTTPException(status_code=503, detail="AI 服务未配置（缺少 LEARN_AI_KEY）")

    ids = list(dict.fromkeys(body.ids))[:5]
    if not ids:
        raise HTTPException(status_code=400, detail="请选择要分析的错题")

    with db.ro() as conn:
        used = wrongbook.ai_used_today(conn, user["id"])
    if used + len(ids) > ai_client.DAILY_LIMIT:
        raise HTTPException(
            status_code=429,
            detail=f"今日 AI 分析次数已达上限（{ai_client.DAILY_LIMIT} 次/天）",
        )

    out = []
    with db.tx() as conn:
        for wq_id in ids:
            row = wrongbook.ai_pending(conn, user["id"], wq_id)
            if not row:
                out.append({"id": wq_id, "error": "错题不存在"})
                continue
            if row["ai_analysis"]:
                out.append({"id": wq_id, "value": json.loads(row["ai_analysis"]),
                            "cached": True})
                continue

            q = {
                "stem": row["stem"],
                "options": json.loads(row["options_json"]),
                "answer": row["answer"],
                "explain": row["explain"],
                "skill": row["skill"],
            }
            try:
                analysis = ai_client.analyze(q, row["picked"])
            except RuntimeError as exc:
                out.append({"id": wq_id, "error": str(exc)})
                continue

            wrongbook.save_ai(conn, user["id"], wq_id, analysis, ai_client.MODEL)
            # 每次真实调用（缓存未命中）计一次用量，用于日限
            events.log(conn, user["id"], f"ai:{uuid.uuid4().hex[:10]}", "ai",
                       {"wq": wq_id, "model": ai_client.MODEL})
            out.append({"id": wq_id, "value": analysis, "cached": False})

        used_after = wrongbook.ai_used_today(conn, user["id"])

    return {
        "results": out,
        "ai_used_today": used_after,
        "daily_limit": ai_client.DAILY_LIMIT,
    }
