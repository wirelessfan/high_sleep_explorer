"""错题本与 AI 错误分析、AI 解题、举一反三。"""
from __future__ import annotations

import json
import sqlite3
import uuid

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from app.services import reflections
from app import db
from app.routers.session import current_user
from app.services import ai_client, ai_config, events, wrongbook

router = APIRouter(tags=["wrongbook"])


class RedoIn(BaseModel):
    answers: dict[str, int] = Field(default_factory=dict)


class AnalyzeIn(BaseModel):
    ids: list[str] = Field(default_factory=list)


class VariantsIn(BaseModel):
    id: str = Field(min_length=1, max_length=64)
    n: int = Field(default=2, ge=1, le=3)


def _question_of(row: sqlite3.Row, with_answer: bool = True) -> dict:
    """错题行 → AI 客户端用的题目 dict。解题任务不给标准答案（保证独立作答）。"""
    q = {
        "stem": row["stem"],
        "options": json.loads(row["options_json"]),
        "skill": row["skill"],
    }
    if with_answer:
        q["answer"] = row["answer"]
        q["explain"] = row["explain"]
    return q


@router.get("/wrongbook")
def get_wrongbook(user: sqlite3.Row = Depends(current_user)):
    """按主题汇总 + 全部待清零题目（含已缓存的 AI 分析）。"""
    with db.ro() as conn:
        st = wrongbook.summary(conn, user["id"])
        items = []
        for t in st["topics"]:
            for it in wrongbook.topic_items(conn, user["id"], t["topic_id"]):
                items.append({**it, "topic_title": t["title"], "subject": t["subject"]})
        used_by_task = wrongbook.ai_used_by_task(conn, user["id"])
        ai_state = {**ai_client.config_public(conn), "used_by_task": used_by_task,
                    "used_today": sum(used_by_task.values())}
    return {
        "summary": st,
        "items": items,
        "ai": ai_state,
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
        for result in res['results']:
            if result.get('skipped') or type(result.get('picked')) is not int:
                continue
            original = conn.execute("SELECT * FROM wrong_questions WHERE id=? AND user_id=? AND source='practice'", (result['id'],user['id'])).fetchone()
            if original:
                question = {'stem':original['stem'],'options':json.loads(original['options_json']),
                            'answer':original['answer'],'explain':original['explain'],'skill':original['skill']}
                result['reflection'] = reflections.record_attempt(conn,user['id'],question,source='bank',
                    topic_id=original['topic_id'],section_id=original['section_id'],tier=original['tier'],question_id=original['question_id'])
        row = conn.execute("SELECT points FROM users WHERE id=?", (user["id"],)).fetchone()
    res["points"] = row["points"]
    return res


def _cached(row, column):
    return wrongbook.cached_ai(row[column])


def _run_ai(user_id: str, wq_id: str, task: str, n: int = 2) -> dict:
    """Reserve atomically, call outside transactions, then publish only a current result."""
    import time
    column = {"analyze": "ai_analysis", "solve": "ai_solve", "variants": "variants"}[task]
    reservation = uuid.uuid4().hex
    with db.tx() as conn:
        row = wrongbook.ai_pending(conn, user_id, wq_id)
        if not row:
            return {"id": wq_id, "error": "错题不存在"}
        cached = _cached(row, column)
        if cached:
            return {"id": wq_id, "value": cached, "cached": True}
        cfg = ai_config.load(conn)
        if not ai_client.enabled() or not ai_client.candidates(task, cfg):
            raise HTTPException(status_code=503, detail="AI 服务未配置可用通道，请联系管理员")
        now = time.time()
        conn.execute("DELETE FROM ai_requests WHERE expires_at < ?", (now,))
        pending = conn.execute(
            "SELECT 1 FROM ai_requests WHERE user_id=? AND wq_id=? AND task=?",
            (user_id, wq_id, task)).fetchone()
        if pending:
            return {"id": wq_id, "error": "这道题正在生成，请稍后查看"}
        used = wrongbook.ai_used_by_task(conn, user_id).get(task, 0)
        held = conn.execute(
            "SELECT COUNT(*) FROM ai_requests WHERE user_id=? AND task=? AND day=?",
            (user_id, task, wrongbook.today_str())).fetchone()[0]
        if used + held >= cfg["limits"][task]:
            raise HTTPException(status_code=429, detail=f"今日「{ai_config.TASK_LABELS[task]}」次数已达上限（{cfg['limits'][task]} 次/天）")
        conn.execute("INSERT INTO ai_requests VALUES (?,?,?,?,?,?)",
                     (reservation, user_id, wq_id, task, wrongbook.today_str(), now + 600))
        original = dict(row)

    try:
        q = _question_of(original, with_answer=task == "analyze")
        if task == "analyze":
            value = ai_client.analyze(q, original["picked"])
        elif task == "solve":
            value = ai_client.solve(q)
        else:
            value = ai_client.variants(q, n)
        with db.tx() as conn:
            # A timed-out lease must never overwrite the result of a replacement request.
            active = conn.execute("SELECT 1 FROM ai_requests WHERE id=?", (reservation,)).fetchone()
            if not active:
                return {"id": wq_id, "error": "生成请求已过期，请重试"}
            events.log(conn, user_id, f"ai:{reservation}", "ai",
                       {"wq": wq_id, "task": task, "model": value.get("model", ""),
                        "channel": value.get("channel", "")})
            fresh = wrongbook.ai_pending(conn, user_id, wq_id)
            if not fresh or (task == "analyze" and fresh["picked"] != original["picked"]):
                return {"id": wq_id, "error": "错题选项已更新，请重新分析"}
            conn.execute(f"UPDATE wrong_questions SET {column}=? WHERE id=? AND user_id=?",
                         (json.dumps(value, ensure_ascii=False), wq_id, user_id))
            if task == "analyze":
                conn.execute("UPDATE wrong_questions SET ai_model=?, ai_at=? WHERE id=? AND user_id=?",
                             (value.get("model", ""), wrongbook.today_str(), wq_id, user_id))
        return {"id": wq_id, "value": value, "cached": False}
    except RuntimeError as exc:
        return {"id": wq_id, "error": str(exc)}
    finally:
        with db.tx() as conn:
            conn.execute("DELETE FROM ai_requests WHERE id=?", (reservation,))


def _usage(user_id, task):
    with db.ro() as conn:
        return {"ai_used_today": wrongbook.ai_used_by_task(conn, user_id).get(task, 0),
                "daily_limit": ai_config.load(conn)["limits"][task]}


def _batch(body, user, task):
    ids = list(dict.fromkeys(body.ids))[:5]
    if not ids:
        raise HTTPException(status_code=400, detail="请选择错题")
    out = []
    for wq_id in ids:
        try:
            out.append(_run_ai(user["id"], wq_id, task))
        except HTTPException as exc:
            if not out:
                raise
            out.append({"id": wq_id, "error": exc.detail})
    return {"results": out, **_usage(user["id"], task)}


@router.post("/wrongbook/ai")
def analyze(body: AnalyzeIn, user: sqlite3.Row = Depends(current_user)):
    return _batch(body, user, "analyze")


@router.post("/wrongbook/ai/solve")
def solve(body: AnalyzeIn, user: sqlite3.Row = Depends(current_user)):
    return _batch(body, user, "solve")


@router.post("/wrongbook/ai/variants")
def variants(body: VariantsIn, user: sqlite3.Row = Depends(current_user)):
    result = _run_ai(user["id"], body.id, "variants", body.n)
    if "error" in result:
        status = 404 if result["error"] == "错题不存在" else 502
        raise HTTPException(status_code=status, detail=result["error"])
    return {"result": {**result["value"], "cached": result["cached"]},
            **_usage(user["id"], "variants")}


# ---------------------------------------------------------------- 拍照录入（演示流程）

MAX_IMAGE_B64 = 6 * 1024 * 1024   # 压缩后仍偏大的图片直接拒绝，避免拖垮请求体


class PhotoIn(BaseModel):
    image: str = Field(min_length=32, max_length=MAX_IMAGE_B64)


class PhotoAnalyzeIn(BaseModel):
    stem: str = Field(min_length=1, max_length=2000)
    options: list[str] = Field(default_factory=list)
    picked: int = Field(ge=0, le=5)


class PhotoSaveIn(BaseModel):
    stem: str = Field(min_length=1, max_length=2000)
    options: list[str] = Field(default_factory=list)
    picked: int = Field(ge=0, le=5)
    answer: int = Field(default=-1, ge=-1, le=5)
    subject: str = Field(default="", max_length=16)
    skill: str = Field(default="", max_length=64)
    explain: str = Field(default="", max_length=1000)


def _clean_b64(raw: str) -> str:
    """接受 data URL 或裸 base64，只保留载荷部分。"""
    s = (raw or "").strip()
    if s.startswith("data:"):
        _, _, s = s.partition(",")
    return s


def _photo_quota(conn: sqlite3.Connection, user_id: str, task: str) -> None:
    """拍照流程的轻量限额检查（不占用 ai_requests 租约：单次请求内串行调用）。"""
    cfg = ai_config.load(conn)
    if not ai_client.enabled() or not ai_client.candidates(task, cfg):
        raise HTTPException(status_code=503, detail="AI 服务未配置可用通道，请联系管理员")
    used = wrongbook.ai_used_by_task(conn, user_id).get(task, 0)
    limit = cfg["limits"][task]
    if used >= limit:
        raise HTTPException(
            status_code=429,
            detail=f"今日「{ai_config.TASK_LABELS[task]}」次数已达上限（{limit} 次/天）",
        )


@router.post("/wrongbook/photo/recognize")
def photo_recognize(body: PhotoIn, user: sqlite3.Row = Depends(current_user)):
    """拍照识别：图片 base64 → 结构化题目（只走视觉通道）。"""
    image = _clean_b64(body.image)
    if not image:
        raise HTTPException(status_code=400, detail="图片为空")

    with db.ro() as conn:
        _photo_quota(conn, user["id"], "recognize")

    try:
        result = ai_client.recognize(image)
    except RuntimeError as exc:
        raise HTTPException(status_code=502, detail=str(exc))

    with db.tx() as conn:
        events.log(conn, user["id"], f"ai:{uuid.uuid4().hex[:10]}", "ai",
                   {"task": "recognize", "model": result.get("model", ""),
                    "channel": result.get("channel", "")})
    return {"result": result}


@router.post("/wrongbook/photo/analyze")
def photo_analyze(body: PhotoAnalyzeIn, user: sqlite3.Row = Depends(current_user)):
    """拍照题三合一分析：AI 解题 → 错因分析 → 举一反三（一次请求跑完）。"""
    if not ai_client.enabled():
        raise HTTPException(status_code=503, detail="AI 服务未配置（缺少通道 Key）")

    options = [o for o in body.options if o.strip()]
    q = {"stem": body.stem, "options": options, "skill": ""}

    with db.ro() as conn:
        for task in ("solve", "analyze", "variants"):
            _photo_quota(conn, user["id"], task)

    out: dict = {"solve": None, "analyze": None, "variants": None, "errors": {}}

    try:
        out["solve"] = ai_client.solve(q)
    except RuntimeError as exc:
        out["errors"]["solve"] = str(exc)

    q_with_answer = dict(q)
    if out["solve"] and out["solve"].get("answer", -1) >= 0:
        q_with_answer["answer"] = out["solve"]["answer"]
        q_with_answer["explain"] = out["solve"].get("key_point", "")
    else:
        q_with_answer["answer"] = 0
        q_with_answer["explain"] = ""

    try:
        out["analyze"] = ai_client.analyze(q_with_answer, body.picked)
    except RuntimeError as exc:
        out["errors"]["analyze"] = str(exc)

    try:
        out["variants"] = ai_client.variants(q, 2)
    except RuntimeError as exc:
        out["errors"]["variants"] = str(exc)

    with db.tx() as conn:
        for task in ("solve", "analyze", "variants"):
            if out[task]:
                events.log(conn, user["id"], f"ai:{uuid.uuid4().hex[:10]}", "ai",
                           {"task": task, "model": out[task].get("model", ""),
                            "channel": out[task].get("channel", ""), "photo": True})

    return out


@router.post("/wrongbook/photo/save")
def photo_save(body: PhotoSaveIn, user: sqlite3.Row = Depends(current_user)):
    """把拍照题存进错题本（source='photo'，按学科归组，可直接重做清零）。"""
    options = [o for o in body.options if o.strip()]
    if len(options) < 2:
        raise HTTPException(status_code=400, detail="至少需要两个选项")
    if body.picked >= len(options):
        raise HTTPException(status_code=400, detail="所选项超出范围")

    subject = body.subject if body.subject in ("physics", "chemistry", "math") else ""
    topic_id = f"photo-{subject or 'misc'}"
    answer = body.answer if 0 <= body.answer < len(options) else 0
    wq_id = "wq_" + uuid.uuid4().hex[:12]
    now = wrongbook.today_str()

    with db.tx() as conn:
        conn.execute(
            "INSERT INTO wrong_questions(id, user_id, topic_id, section_id, tier, "
            "question_id, skill, stem, options_json, answer, explain, picked, "
            "source, created_at, last_wrong_at) "
            "VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            (wq_id, user["id"], topic_id, "photo", "photo", uuid.uuid4().hex[:12],
             body.skill or "拍照录入", body.stem,
             json.dumps(options, ensure_ascii=False), answer, body.explain,
             body.picked, "photo", now, now),
        )
        summary = wrongbook.summary(conn, user["id"])

    return {
        "id": wq_id,
        "topic_id": topic_id,
        "answer": answer,
        "summary": summary,
        "note": "已加入错题本，可在「错题本」里按主题重做清零。",
    }
