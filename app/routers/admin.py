"""管理接口：AI 策略调整、连通性测试、用量统计、账号列表（仅管理员）。

所有端点挂 require_admin 守卫；响应永不包含 API Key（key_ok 只给布尔状态）。
"""
from __future__ import annotations

import sqlite3
import uuid
from datetime import date, timedelta

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, ConfigDict, Field, StrictInt

from app import db
from app.routers.session import require_admin
from app.services import accounts, ai_client, ai_config, events, ratelimit, wishes

router = APIRouter(prefix="/admin", tags=["admin"])


class AiConfigIn(BaseModel):
    routing: dict[str, str] = Field(default_factory=dict)
    channels: dict[str, dict] = Field(default_factory=dict)
    limits: dict[str, StrictInt] = Field(default_factory=dict)


class WishModerateIn(BaseModel):
    status: str = Field(min_length=1, max_length=16)
    reply: str = Field(default="", max_length=600)


class AiTestIn(BaseModel):
    task: str = Field(min_length=1, max_length=32)


class AiReviewIn(BaseModel):
    stem: str = Field(min_length=1, max_length=4000)
    options: list[str] = Field(min_length=2, max_length=6)
    answer: str = Field(min_length=1, max_length=500)
    explain: str = Field(min_length=1, max_length=4000)


class StudentIn(BaseModel):
    model_config = ConfigDict(extra='forbid')
    username: str = Field(min_length=3,max_length=32)
    nickname: str = Field(min_length=1,max_length=20)
    password: str = Field(min_length=8,max_length=128)
    legacy_user_id: str | None = Field(default=None,max_length=100)


def _channel_admin_view(cfg: dict) -> dict:
    """通道的管理视角：策略覆盖 + 环境侧事实（密钥只给配置状态）。"""
    out = {}
    for cid in ai_config.ALL_CHANNELS:
        ch = ai_client.CHANNELS.get(cid)
        if not ch:
            continue
        over = cfg["channels"].get(cid, {})
        out[cid] = {
            "name": ch["name"],
            "enabled": bool(over.get("enabled", True)),
            "model": over.get("model") or ch["model"],   # 当前生效模型
            "model_override": over.get("model"),          # 管理员覆盖（None=用默认）
            "default_model": ch["model"],
            "base_url": ch["base_url"],
            "key_ok": bool(ch["key"]),
            "vision": bool(ch.get("vision")),
        }
    return out


def _full_config(conn: sqlite3.Connection) -> dict:
    cfg = ai_config.load(conn)
    row = conn.execute("SELECT updated_at, updated_by FROM ai_config WHERE id = 1").fetchone()
    return {
        "routing": cfg["routing"],
        "limits": cfg["limits"],
        "channels": _channel_admin_view(cfg),
        "tasks": [{"id": t, "label": ai_config.TASK_LABELS[t]} for t in ai_config.TASKS],
        "task_labels": ai_config.TASK_LABELS,
        "channel_order": list(ai_config.ALL_CHANNELS),
        "stub": ai_client._stub_on(),
        "updated_at": row["updated_at"] if row else None,
        "updated_by": row["updated_by"] if row else None,
    }


@router.get("/ai/config")
def get_ai_config(user: sqlite3.Row = Depends(require_admin)):
    with db.ro() as conn:
        return _full_config(conn)


@router.put("/ai/config")
def put_ai_config(body: AiConfigIn, user: sqlite3.Row = Depends(require_admin)):
    patch = body.model_dump(exclude_unset=True)
    with db.tx() as conn:
        try:
            ai_config.save(conn, patch, user["id"])
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc))
        return _full_config(conn)


@router.post("/ai/reset")
def reset_ai_config(user: sqlite3.Row = Depends(require_admin)):
    with db.tx() as conn:
        ai_config.reset(conn)
        return _full_config(conn)


@router.post("/ai/test")
def test_ai(body: AiTestIn, user: sqlite3.Row = Depends(require_admin)):
    """对指定任务的当前路由做一次最小真实调用，返回通道与延迟。"""
    task = body.task
    if task not in ai_config.TASKS:
        raise HTTPException(status_code=400, detail=f"未知任务：{task}")
    if not ratelimit.allow(f"ai-test:{user['id']}", limit=5, window_seconds=60):
        raise HTTPException(status_code=429, detail="连通性测试过于频繁，请稍后再试")

    if ai_client._stub_on():
        return {"ok": True, "channel": "stub", "model": "stub", "latency_ms": 0,
                "reply": "演示模式（LEARN_AI_STUB=1），未发起真实请求"}

    import time
    start = time.monotonic()
    try:
        r = ai_client.chat(task, "你是连通性测试助手。", "收到请只回复两个字母：OK",
                           json_mode=False, max_tokens=10)
        latency = int((time.monotonic() - start) * 1000)
        return {"ok": True, "channel": r["channel"], "model": r["model"],
                "latency_ms": latency, "reply": r["text"].strip()[:40]}
    except RuntimeError as exc:
        latency = int((time.monotonic() - start) * 1000)
        return {"ok": False, "error": str(exc), "latency_ms": latency}


@router.post("/ai/review")
def review_question(body: AiReviewIn, user: sqlite3.Row = Depends(require_admin)):
    """对管理员提交的题目快照做审校建议，不写入题库。"""
    if not ratelimit.allow(f"ai-review:{user['id']}", limit=10, window_seconds=86400):
        raise HTTPException(status_code=429, detail="今日审校次数已达上限（10 次）")
    if any(not isinstance(option, str) or not option.strip() or len(option) > 500
           for option in body.options):
        raise HTTPException(status_code=422, detail="选项必须为 1–500 字文本")
    question = body.model_dump()
    question["options"] = [option.strip() for option in body.options]
    question["answer"] = body.answer.strip()
    question["stem"] = body.stem.strip()
    question["explain"] = body.explain.strip()
    try:
        result = ai_client.review(question)
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from None
    with db.tx() as conn:
        events.log(conn, user["id"], f"ai-review:{uuid.uuid4().hex}", "ai",
                   {"task": "review", "channel": result["channel"], "model": result["model"]})
    return result


@router.get("/ai/usage")
def ai_usage(days: int = 1, user: sqlite3.Row = Depends(require_admin)):
    """按通道 × 任务聚合 AI 用量（events 表，kind='ai'）。"""
    days = max(1, min(days, 30))
    cutoff = (date.today() - timedelta(days=days - 1)).isoformat()
    with db.ro() as conn:
        rows = conn.execute(
            "SELECT COALESCE(json_extract(payload,'$.channel'),'stub') AS channel, "
            "COALESCE(json_extract(payload,'$.task'),'analyze') AS task, "
            "COUNT(*) AS n "
            "FROM events WHERE kind='ai' AND substr(created_at,1,10) >= ? "
            "GROUP BY channel, task ORDER BY n DESC",
            (cutoff,),
        ).fetchall()
    return {
        "days": days,
        "rows": [{"channel": r["channel"], "task": r["task"], "count": r["n"]}
                 for r in rows],
        "total": sum(r["n"] for r in rows),
    }


@router.get("/users")
def list_users(user: sqlite3.Row = Depends(require_admin)):
    """按五类身份展示，历史临时数据独立保留。"""
    with db.ro() as conn:
        return accounts.directory(conn)


@router.post('/students')
def create_student(body: StudentIn, user: sqlite3.Row = Depends(require_admin)):
    with db.tx() as conn:
        try:
            return accounts.create_student(conn,body.username,body.nickname,body.password,user['id'],body.legacy_user_id)
        except ValueError as exc:
            raise HTTPException(status_code=400,detail=str(exc))


@router.get("/wishes")
def list_wishes(user: sqlite3.Row = Depends(require_admin)):
    """许愿墙全部意见（待处理优先）。"""
    with db.ro() as conn:
        return {"items": wishes.admin_list(conn)}


@router.patch("/wishes/{wish_id}")
def moderate_wish(wish_id: str, body: WishModerateIn,
                  user: sqlite3.Row = Depends(require_admin)):
    """管理员：改状态（open/planned/done）并写官方回复。"""
    with db.tx() as conn:
        try:
            return wishes.moderate(conn, wish_id, body.status, body.reply)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc))
