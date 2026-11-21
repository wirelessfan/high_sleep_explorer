"""错题本与 AI 错误分析、AI 解题、举一反三、批量导入。"""
from __future__ import annotations

import base64
import binascii
import json
import hashlib
import time
import os
import re
import sqlite3
import uuid
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import Response
from pydantic import BaseModel, Field, StrictInt

from app.services import reflections
from app import content_loader, db
from app.routers.session import current_user
from app.services import ai_client, ai_config, events, wrongbook

router = APIRouter(tags=["wrongbook"])

ASSETS_DIR = Path(__file__).resolve().parent.parent.parent / "assets"
# 错题本配图目录：默认仓库 assets/wrongbook；线上（/opt 只读）用 LEARN_WB_IMAGES 覆盖。
_IMAGES_DIR = Path(os.environ.get("LEARN_WB_IMAGES", ASSETS_DIR / "wrongbook"))
_WEB_PREFIX = "/wb-images" if os.environ.get("LEARN_WB_IMAGES") else "/assets/wrongbook"
MAX_IMAGE_B64 = 6 * 1024 * 1024   # 单张图片 base64 上限
_IMPORT_MAGIC = {
    b"\xff\xd8\xff": "jpg",
    b"\x89PNG\r\n\x1a\n": "png",
    b"RIFF": "webp",
    b"GIF8": "gif",
}


class RedoIn(BaseModel):
    answers: dict[str, StrictInt] = Field(default_factory=dict)
    multi_answers: dict[str, list[StrictInt]] = Field(default_factory=dict)
    # 填空/解答题的重做答案：题 id → 学生填的文本
    fill_answers: dict[str, str] = Field(default_factory=dict)


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
        "qtype": row["qtype"],
        "skill": row["skill"],
    }
    if with_answer:
        q["answer"] = row["answer"]
        q["answer_indices"] = json.loads(row["answer_indices_json"] or "[]")
        q["explain"] = row["explain"]
    return q


@router.get("/wrongbook")
def get_wrongbook(user: sqlite3.Row = Depends(current_user)):
    """按主题汇总 + 全部待清零题目（含已缓存的 AI 分析）。"""
    with db.ro() as conn:
        # 错题本是家庭共享的一本账：只按归属 id 读，不按当前账号隔离
        owner = wrongbook.book_owner(user["id"])
        st = wrongbook.summary(conn, owner, user["id"])
        items = []
        for t in st["topics"]:
            for it in wrongbook.topic_items(conn, owner, t["topic_id"], viewer_id=user["id"]):
                if it["status"] == "open" or it["review_status"] != "ready":
                    items.append({**it, "topic_title": t["title"], "subject": t["subject"]})
        used_by_task = wrongbook.ai_used_by_task(conn, user["id"])
        ai_state = {**ai_client.config_public(conn), "used_by_task": used_by_task,
                    "used_today": sum(used_by_task.values())}
    return {
        "summary": st,
        "items": items,
        "ai": ai_state,
    }


@router.get("/wrongbook/taxonomy")
def get_taxonomy(user: sqlite3.Row = Depends(current_user)):
    """错题本学科/章节分类体系（录入工具与前端共用）。"""
    return content_loader.wrongbook_taxonomy()


def _save_image_b64(user_id: str, raw: str) -> str:
    """base64 图片 → assets/wrongbook/<user_id>/<uuid>.<ext>，返回 web 路径。"""
    s = (raw or "").strip()
    if s.startswith("data:"):
        _, _, s = s.partition(",")
    if not s:
        raise HTTPException(status_code=400, detail="图片为空")
    if len(s) > MAX_IMAGE_B64:
        raise HTTPException(status_code=413, detail="图片过大（>4MB），请压缩后重试")
    try:
        data = base64.b64decode(s, validate=True)
    except (binascii.Error, ValueError):
        raise HTTPException(status_code=400, detail="图片 base64 解码失败")
    ext = None
    for magic, e in _IMPORT_MAGIC.items():
        if data[:len(magic)] == magic:
            ext = e
            break
    if not ext:
        raise HTTPException(status_code=400, detail="仅支持 jpg/png/webp/gif 图片")
    dir_path = _IMAGES_DIR / user_id
    dir_path.mkdir(parents=True, exist_ok=True)
    name = f"{uuid.uuid4().hex[:16]}.{ext}"
    (dir_path / name).write_bytes(data)
    return f"{_WEB_PREFIX}/{user_id}/{name}"


class ImportImageIn(BaseModel):
    image: str = Field(min_length=32, max_length=MAX_IMAGE_B64)


@router.post("/wrongbook/import/image")
def import_image(body: ImportImageIn, user: sqlite3.Row = Depends(current_user)):
    """上传一张题目图片（base64/dataURL），存库并返回可访问路径。"""
    path = _save_image_b64(user["id"], body.image)
    return {"path": path}


class ImportItem(BaseModel):
    stem: str = Field(min_length=1, max_length=20000)
    qtype: str = Field(default="choice", max_length=16)
    answer_indices: list[StrictInt] = Field(default_factory=list, max_length=8)
    picked_indices: list[StrictInt] = Field(default_factory=list, max_length=8)
    review_status: str = Field(default="ready", max_length=32)
    review_reason: str = Field(default="", max_length=500)
    answer_text: str = Field(default="", max_length=500)
    options: list[str] = Field(default_factory=list, max_length=8)
    picked: int = Field(default=0, ge=-1, le=7)   # 填空/解答题用 -1
    answer: int = Field(default=-1, ge=-1, le=7)
    skill: str = Field(default="", max_length=64)
    explain: str = Field(default="", max_length=10000)
    subject: str = Field(default="", max_length=16)
    chapter: str = Field(default="", max_length=32)
    image_path: str = Field(default="", max_length=4000)
    wrong_reason: str = Field(default="", max_length=10000)
    derivation: str = Field(default="", max_length=20000)


class ImportIn(BaseModel):
    items: list[ImportItem] = Field(min_length=1, max_length=100)
    overwrite: bool = False


@router.post("/wrongbook/import")
def import_wrongbook(body: ImportIn, user: sqlite3.Row = Depends(current_user)):
    """批量导入错题（录入工具 / WorkBuddy 共用），同一题干自动去重。"""
    with db.tx() as conn:
        result = wrongbook.import_items(
            conn, wrongbook.book_owner(user["id"]),
            [it.model_dump() for it in body.items],
            overwrite=body.overwrite,
        )
        summary = wrongbook.summary(conn, wrongbook.book_owner(user["id"]))
    return {**result, "summary": summary,
            "note": "已加入错题本，可在「错题本」里按学科·章节重做清零。"}


@router.get("/wrongbook/{topic_id}")
def get_topic_wrongbook(topic_id: str, user: sqlite3.Row = Depends(current_user)):
    with db.ro() as conn:
        owner = wrongbook.book_owner(user["id"])
        items = wrongbook.topic_items(conn, owner, topic_id, "open", viewer_id=user["id"])
        cleared = wrongbook.topic_items(conn, owner, topic_id, "cleared", viewer_id=user["id"])
    return {"topic_id": topic_id, "items": items, "cleared": cleared}


@router.post("/wrongbook/{topic_id}/redo")
def redo_topic(topic_id: str, body: RedoIn, user: sqlite3.Row = Depends(current_user)):
    """错题重做：答对清零；该主题全部清零时发清零奖励。"""
    with db.tx() as conn:
        fresh = conn.execute("SELECT * FROM users WHERE id=?", (user["id"],)).fetchone()
        try:
            res = wrongbook.redo(conn, fresh, topic_id, body.answers, body.fill_answers, body.multi_answers)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc))
        for result in res['results']:
            if result.get('skipped') or type(result.get('picked')) is not int:
                continue
            original = conn.execute("SELECT * FROM wrong_questions WHERE id=? AND user_id=? AND source='practice'",
                                    (result['id'], wrongbook.book_owner(user['id']))).fetchone()
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
    """Reserve atomically, call outside transactions, then publish only a current result.

    错题行在家庭共享账本里（owner），AI 次数配额与事件仍记在当前账号（user_id）上。
    """
    import time
    column = {"analyze": "ai_analysis", "solve": "ai_solve", "variants": "variants"}[task]
    reservation = uuid.uuid4().hex
    owner = wrongbook.book_owner(user_id)
    with db.tx() as conn:
        row = conn.execute("SELECT * FROM wrong_questions WHERE id=? AND ((user_id=? AND source<>'photo') OR (user_id=? AND source='photo'))",
                           (wq_id, owner, user_id)).fetchone()
        if not row:
            return {"id": wq_id, "error": "错题不存在"}
        if row["review_status"] != "ready":
            return {"id": wq_id, "error": row["review_reason"] or "题目待审核，暂不能进行 AI 分析"}
        owner = row["user_id"]
        if task == "analyze" and (row["review_status"] != "ready" or
                                  row["qtype"] == "multi_choice" and not json.loads(row["answer_indices_json"] or "[]") or
                                  row["qtype"] != "multi_choice" and (row["answer"] < 0 or row["picked"] < 0)):
            return {"id": wq_id, "error": "尚无标准答案或作答，不能分析错因"}
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
            picked = json.loads(original["picked_indices_json"] or "[]") if original["qtype"] == "multi_choice" else original["picked"]
            value = ai_client.analyze(q, picked)
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
            fresh = wrongbook.ai_pending(conn, owner, wq_id)
            if not fresh or fresh["content_version"] != original["content_version"] or (task == "analyze" and (
                    fresh["picked"] != original["picked"] or fresh["picked_indices_json"] != original["picked_indices_json"])):
                return {"id": wq_id, "error": "错题内容或选项已更新，请重新分析"}
            conn.execute(f"UPDATE wrong_questions SET {column}=? WHERE id=? AND user_id=?",
                         (json.dumps(value, ensure_ascii=False), wq_id, owner))
            if task == "analyze":
                conn.execute("UPDATE wrong_questions SET ai_model=?, ai_at=? WHERE id=? AND user_id=?",
                             (value.get("model", ""), wrongbook.today_str(), wq_id, owner))
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


# ---------------------------------------------------------------- 拍照录入

class PhotoIn(BaseModel):
    image: str = Field(min_length=32, max_length=MAX_IMAGE_B64)
    retry: bool = False
    subject: str = Field(default="", max_length=16)
    chapter: str = Field(default="", max_length=32)
    skill: str = Field(default="", max_length=64)
    shared_readonly: bool = False


class PhotoAnalyzeIn(BaseModel):
    stem: str = Field(min_length=1, max_length=20000)
    options: list[str] = Field(default_factory=list, max_length=8)
    picked: int = Field(default=-1, ge=-1, le=7)
    answer_indices: list[StrictInt] = Field(default_factory=list, max_length=8)
    picked_indices: list[StrictInt] = Field(default_factory=list, max_length=8)
    qtype: str = Field(default="choice", max_length=16)
    skill: str = Field(default="", max_length=64)


class PhotoSaveIn(BaseModel):
    stem: str = Field(min_length=1, max_length=20000)
    qtype: str = Field(default="choice", max_length=16)
    answer_text: str = Field(default="", max_length=500)
    options: list[str] = Field(default_factory=list, max_length=8)
    picked: int = Field(default=-1, ge=-1, le=7)
    answer: int = Field(default=-1, ge=-1, le=7)
    subject: str = Field(default="", max_length=16)
    skill: str = Field(default="", max_length=64)
    explain: str = Field(default="", max_length=1000)
    question_no: str = Field(default="", max_length=32)
    image_path: str = Field(default="", max_length=4000)
    job_id: str = Field(default="", max_length=64)
    item_index: int = Field(default=-1, ge=-1, le=19)


class PhotoSaveBatchIn(BaseModel):
    items: list[PhotoSaveIn] = Field(min_length=1, max_length=20)


def _owned_image_path(user_id: str, path: str) -> str:
    """只接受本次识图接口返回的当前用户图片路径，禁止借路径读写他人资源。"""
    value = (path or "").strip()
    prefix = f"{_WEB_PREFIX}/{user_id}/"
    if not value:
        return ""
    if not value.startswith(prefix) or not value[len(prefix):] or "/" in value[len(prefix):] or ".." in value:
        raise HTTPException(status_code=400, detail="图片来源无效，请重新识别")
    return value


def _photo_item_values(user_id: str, item: PhotoSaveIn) -> tuple:
    if not item.stem.strip():
        raise HTTPException(status_code=400, detail="题干不能为空")
    options = [o.strip() for o in item.options if o.strip()]
    qtype = wrongbook.normalize_qtype(item.qtype, len(options))
    if qtype in ("choice", "multi_choice"):
        if len(options) < 2:
            raise HTTPException(status_code=400, detail="选择题至少需要两个选项")
        if not -1 <= item.picked < len(options):
            raise HTTPException(status_code=400, detail="所选项超出范围")
        answer_text = ""
    else:
        # 填空题/解答题不编造选项；正确答案文本用于重做判分
        options = []
        answer_text = item.answer_text.strip()
        # 转录确认并非答案正确性确认，允许答案留空，不能为录入而编造答案。
    answer = item.answer if qtype == "choice" and 0 <= item.answer < len(options) else -1
    subject = item.subject if item.subject in ("physics", "chemistry", "math", "biology", "geography", "cross") else ""
    topic_id = f"photo-{subject or 'misc'}"
    image_path = _owned_image_path(user_id, item.image_path)
    return options, topic_id, answer, image_path, qtype, answer_text


def _clean_b64(raw: str) -> str:
    """接受 data URL 或裸 base64，只保留载荷部分。"""
    s = (raw or "").strip()
    if s.startswith("data:"):
        _, _, s = s.partition(",")
    return s


def _photo_quota(conn: sqlite3.Connection, user_id: str, task: str) -> None:
    """拍照流程的轻量限额检查（不占用 ai_requests 租约：单次请求内串行调用）。"""
    cfg = ai_config.load(conn)
    if not ai_client.enabled() or not ai_client.candidates(task, cfg, vision_only=task in ("recognize", "photo_confirm")):
        raise HTTPException(status_code=503, detail="AI 服务未配置可用通道，请联系管理员")
    used = wrongbook.ai_used_by_task(conn, user_id).get(task, 0)
    limit = cfg["limits"][task]
    if used >= limit:
        raise HTTPException(
            status_code=429,
            detail=f"今日「{ai_config.TASK_LABELS[task]}」次数已达上限（{limit} 次/天）",
        )


@router.get("/wrongbook/photo/jobs")
def photo_jobs(user: sqlite3.Row = Depends(current_user)):
    with db.ro() as conn:
        rows = conn.execute("SELECT id, state, result_json FROM photo_jobs WHERE user_id=? ORDER BY rowid DESC LIMIT 30",
                            (user["id"],)).fetchall()
    return {"jobs": [{"job_id": r["id"], "state": r["state"], "result": json.loads(r["result_json"])} for r in rows]}


@router.get("/wrongbook/photo/image/{job_id}")
def photo_image(job_id: str, user: sqlite3.Row = Depends(current_user)):
    with db.ro() as conn:
        row = conn.execute(
            "SELECT image_b64 FROM photo_jobs WHERE id=? AND (user_id=? OR "
            "(json_extract(result_json,'$.metadata.shared_readonly')=1 AND EXISTS "
            "(SELECT 1 FROM wrong_questions WHERE source='photo' AND user_id=photo_jobs.user_id "
            "AND image_path='/api/v1/wrongbook/photo/image/' || photo_jobs.id)))",
            (job_id, user["id"]),
        ).fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="图片不存在")
    image = row["image_b64"]
    mime = image.split(";", 1)[0].removeprefix("data:")
    return Response(base64.b64decode(_clean_b64(image)), media_type=mime, headers={"Cache-Control": "no-store"})


@router.post("/wrongbook/photo/retry/{job_id}")
def photo_retry(job_id: str, user: sqlite3.Row = Depends(current_user)):
    with db.ro() as conn:
        row = conn.execute("SELECT image_b64 FROM photo_jobs WHERE id=? AND user_id=?", (job_id, user["id"])).fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="识图任务不存在")
    return photo_recognize(PhotoIn(image=row["image_b64"], retry=True), user)


@router.post("/wrongbook/photo/recognize")
def photo_recognize(body: PhotoIn, user: sqlite3.Row = Depends(current_user)):
    """服务器独占审核与自动保存；同账号同图片稳定幂等，失败保留供恢复。"""
    image = _clean_b64(body.image)
    try:
        data = base64.b64decode(image, validate=True)
    except (ValueError, binascii.Error):
        raise HTTPException(status_code=400, detail="图片 base64 无效")
    ext = next((ext for magic, ext in _IMPORT_MAGIC.items() if data.startswith(magic)), None)
    if not ext:
        raise HTTPException(status_code=400, detail="图片格式无效")
    mime = "jpeg" if ext == "jpg" else ext
    image_url = f"data:image/{mime};base64,{image}"
    digest = hashlib.sha256(data).hexdigest()
    metadata = {"subject": body.subject, "chapter": body.chapter, "skill": body.skill,
                "shared_readonly": body.shared_readonly}
    if body.subject or body.chapter:
        tax = wrongbook._taxonomy()
        if body.subject not in tax or body.chapter and body.chapter not in tax[body.subject]["chapters"]:
            raise HTTPException(status_code=400, detail="学科或章节分类无效")
    lease = uuid.uuid4().hex
    with db.tx() as conn:
        row = conn.execute("SELECT * FROM photo_jobs WHERE user_id=? AND image_hash=?", (user["id"], digest)).fetchone()
        if row and row["lease_until"] > time.time():
            raise HTTPException(status_code=409, detail="正在识图确认，请稍后恢复任务")
        if row and (row["state"] in ("saved", "manual_review") or not body.retry):
            cached = json.loads(row["result_json"])
            cached.update(job_id=row["id"], state=row["state"])
            return {"result": cached}
        job_id = row["id"] if row else "photo_" + uuid.uuid4().hex
        if not row:
            _photo_quota(conn, user["id"], "recognize")
            held = conn.execute("SELECT COUNT(*) FROM photo_jobs WHERE user_id=? AND lease_until>?",
                                (user["id"], time.time())).fetchone()[0]
            if held + wrongbook.ai_used_by_task(conn, user["id"]).get("recognize", 0) >= ai_config.load(conn)["limits"]["recognize"]:
                raise HTTPException(status_code=429, detail="今日识图任务次数已达上限")
            conn.execute("INSERT INTO photo_jobs(id,user_id,image_hash,image_b64,created_at,result_json) VALUES(?,?,?,?,?,?)",
                         (job_id, user["id"], digest, image_url, wrongbook.today_str(),
                          json.dumps({"metadata": metadata}, ensure_ascii=False)))
        else:
            metadata = json.loads(row["result_json"]).get("metadata", metadata)
        conn.execute("UPDATE photo_jobs SET state='processing',lease=?,lease_until=? WHERE id=?",
                     (lease, time.time() + 900, job_id))
        original = json.loads(row["original_json"]) if row and row["original_json"] else None
        review = json.loads(row["review_json"]) if row and row["review_json"] else None
    result = {"job_id": job_id, "state": "pending", "questions": [], "warnings": [], "metadata": metadata}
    try:
        if original is None:
            original = ai_client.recognize(image_url)
            with db.tx() as conn:
                if conn.execute("SELECT lease FROM photo_jobs WHERE id=?", (job_id,)).fetchone()["lease"] != lease:
                    raise RuntimeError("识图任务已过期，请恢复任务")
                conn.execute("UPDATE photo_jobs SET original_json=? WHERE id=?", (json.dumps(original, ensure_ascii=False), job_id))
                events.log(conn, user["id"], f"ai:{job_id}:recognize", "ai",
                           {"task": "recognize", "channel": original.get("channel"), "model": original.get("model")})
        result.update(original)
        result["original"] = original
        result["image_path"] = f"/api/v1/wrongbook/photo/image/{job_id}"
        if review is None or review.get("status") == "pending":
            with db.ro() as conn:
                _photo_quota(conn, user["id"], "photo_confirm")
            review = ai_client.confirm_photo(image_url, original)
        result["review"] = review
        result["questions"] = review["questions"]
        result["state"] = {"passed": "verified", "revised": "manual_review", "pending": "pending"}[review["status"]]
        with db.tx() as conn:
            active = conn.execute("SELECT lease FROM photo_jobs WHERE id=?", (job_id,)).fetchone()
            if active["lease"] != lease:
                raise RuntimeError("确认任务已过期，请恢复任务")
            conn.execute("UPDATE photo_jobs SET review_json=?,result_json=?,state=? WHERE id=?",
                         (json.dumps(review, ensure_ascii=False), json.dumps(result, ensure_ascii=False), result["state"], job_id))
            events.log(conn, user["id"], f"ai:{job_id}:photo_confirm", "ai",
                       {"task": "photo_confirm", "channel": review.get("channel"), "model": review.get("model")})
        if review["status"] == "passed":
            items = [PhotoSaveIn(**{**q, "job_id": job_id, "item_index": i, "image_path": result["image_path"]})
                     for i, q in enumerate(review["questions"])]
            result["save_results"] = _photo_save_items(items, user, automatic=True)
            result["state"] = "saved"
            result["save_mode"] = "automatic"
    except (RuntimeError, HTTPException, sqlite3.Error) as exc:
        result["state"] = "pending"
        result["error"] = str(exc.detail) if isinstance(exc, HTTPException) else (
            "保存失败，数据已回滚，可重试" if isinstance(exc, sqlite3.Error) else str(exc))
    finally:
        with db.tx() as conn:
            conn.execute("UPDATE photo_jobs SET result_json=?,state=?,lease=NULL,lease_until=0 WHERE id=? AND lease=?",
                         (json.dumps(result, ensure_ascii=False), result["state"], job_id, lease))
    return {"result": result}


@router.post("/wrongbook/photo/analyze")
def photo_analyze(body: PhotoAnalyzeIn, user: sqlite3.Row = Depends(current_user)):
    """拍照题分析：选择题走 解题→错因→举一反三；填空/解答题只做独立求解。

    填空题不编造选项，返回 answer_text（正确答案）+ derivation（分步推导）。
    """
    if not ai_client.enabled():
        raise HTTPException(status_code=503, detail="AI 服务未配置（缺少通道 Key）")

    raw_options = [o for o in body.options if o.strip()]
    qtype = wrongbook.normalize_qtype(body.qtype, len(raw_options))
    options = raw_options if qtype == "choice" else []
    q = {"stem": body.stem, "options": options, "skill": body.skill}

    with db.ro() as conn:
        for task in (("solve", "analyze", "variants") if qtype == "choice" else ("solve",)):
            _photo_quota(conn, user["id"], task)

    out: dict = {"qtype": qtype, "solve": None, "analyze": None, "variants": None,
                 "answer_text": "", "derivation": "", "explain": "", "errors": {}}

    if qtype != "choice":
        try:
            sol = ai_client.solve_fill(body.stem, body.skill)
            out["solve"] = sol
            out["answer_text"] = sol.get("answer_text", "")
            out["derivation"] = "\n".join(sol.get("steps") or [])
            out["explain"] = sol.get("key_point", "")
            with db.tx() as conn:
                events.log(conn, user["id"], f"ai:{uuid.uuid4().hex[:10]}", "ai",
                           {"task": "solve", "model": sol.get("model", ""),
                            "channel": sol.get("channel", ""), "photo": True, "qtype": qtype})
        except RuntimeError as exc:
            out["errors"]["solve"] = str(exc)
        return out

    try:
        out["solve"] = ai_client.solve(q)
    except RuntimeError as exc:
        out["errors"]["solve"] = str(exc)

    q_with_answer = dict(q)
    if out["solve"] and out["solve"].get("answer", -1) >= 0:
        q_with_answer["answer"] = out["solve"]["answer"]
        q_with_answer["explain"] = out["solve"].get("key_point", "")
    if out["solve"] and out["solve"].get("answer", -1) >= 0:
        try:
            out["analyze"] = ai_client.analyze(q_with_answer, body.picked)
        except RuntimeError as exc:
            out["errors"]["analyze"] = str(exc)
    else:
        out["errors"]["analyze"] = "解题未成功，不能编造标准答案进行错因分析"

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
    """单题人工录入兼容接口；标准答案可以留空，不作为 GPT 自动确认凭据。"""
    if len([o for o in body.options if o.strip()]) == 1 and body.qtype == "choice":
        raise HTTPException(status_code=400, detail="至少需要两个选项")
    result = _photo_save_items([body], user)[0]
    if result["status"] == "failed":
        raise HTTPException(status_code=400, detail=result["error"])
    return result


@router.post("/wrongbook/photo/save-batch")
def photo_save_batch(body: PhotoSaveBatchIn, user: sqlite3.Row = Depends(current_user)):
    """只保存用户明确提交的题目，逐题返回状态，失败项不影响已成功题。"""
    return {"results": _photo_save_items(body.items, user)}


def _photo_save_items(items: list[PhotoSaveIn], user: sqlite3.Row, automatic: bool = False) -> list[dict]:
    owner = user["id"]
    results = []
    with db.tx() as conn:
        for item in items:
            try:
                job = None
                if item.job_id:
                    job = conn.execute("SELECT * FROM photo_jobs WHERE id=? AND user_id=?", (item.job_id, user["id"])).fetchone()
                    if not job:
                        raise HTTPException(status_code=404, detail="识图任务不存在")
                    review = json.loads(job["review_json"] or "{}")
                    expected = "passed" if automatic else "revised"
                    if review.get("status") != expected and job["state"] != "saved":
                        raise HTTPException(status_code=409, detail="GPT 尚未完成确认，不能录入，请重试确认")
                    questions = review.get("questions", [])
                    if not 0 <= item.item_index < len(questions):
                        raise HTTPException(status_code=400, detail="题目序号无效")
                    if automatic:
                        source = questions[item.item_index]
                        item = PhotoSaveIn(**{**source, "job_id": item.job_id, "item_index": item.item_index})
                    # 人审确认针对稳定任务和题目序号，即使编辑题干也不重复生成。
                    fingerprint = hashlib.sha256(f"{item.job_id}:{item.item_index}".encode()).hexdigest()
                    image_path = f"/api/v1/wrongbook/photo/image/{item.job_id}"
                    item.image_path = ""
                else:
                    fingerprint = hashlib.sha256(json.dumps([item.stem.strip(), item.options], ensure_ascii=False).encode()).hexdigest()
                    image_path = ""
                metadata = json.loads(job["result_json"]).get("metadata", {}) if job else {}
                if metadata.get("subject"):
                    item.subject = metadata["subject"]
                if metadata.get("skill"):
                    item.skill = metadata["skill"]
                chapter = metadata.get("chapter", "")
                options, topic_id, answer, validated_image, qtype, answer_text = _photo_item_values(user["id"], item)
                if chapter:
                    topic_id = wrongbook.import_topic_id(item.subject, chapter)
                image_path = image_path or validated_image
                existing = conn.execute(
                    "SELECT id FROM wrong_questions WHERE user_id=? AND question_id=?",
                    (owner, fingerprint)).fetchone()
                if existing:
                    results.append({"question_no": item.question_no, "status": "duplicate", "id": existing["id"],
                                    "topic_id": topic_id})
                    continue
                wq_id = "wq_" + uuid.uuid4().hex[:12]
                now = wrongbook.today_str()
                conn.execute(
                    "INSERT INTO wrong_questions(id, user_id, topic_id, section_id, tier, question_id, skill, stem, "
                    "options_json, answer, explain, picked, source, image_path, subject, qtype, answer_text, "
                    "created_at, last_wrong_at, chapter) "
                    "VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                    (wq_id, owner, topic_id, "photo", "photo", fingerprint, item.skill or "拍照录入", item.stem.strip(),
                     json.dumps(options, ensure_ascii=False), answer, item.explain,
                     item.picked if qtype == "choice" else -1, "photo", image_path,
                     item.subject if item.subject in ("physics", "chemistry", "math", "biology", "geography", "cross") else "",
                     qtype, answer_text, now, now, chapter),
                )
                results.append({"question_no": item.question_no, "status": "saved", "id": wq_id,
                                "topic_id": topic_id, "answer": answer, "qtype": qtype})
            except HTTPException as exc:
                if automatic:
                    raise
                results.append({"question_no": item.question_no, "qtype": wrongbook.normalize_qtype(item.qtype, len(item.options)),
                                "status": "failed", "error": str(exc.detail)})
        for job_id in {it.job_id for it in items if it.job_id}:
            job = conn.execute("SELECT * FROM photo_jobs WHERE id=? AND user_id=?", (job_id, owner)).fetchone()
            if not job:
                continue
            document = json.loads(job["result_json"])
            questions = document.get("questions", [])
            saved = []
            for index, question in enumerate(questions):
                fp = hashlib.sha256(f"{job_id}:{index}".encode()).hexdigest()
                row = conn.execute("SELECT id FROM wrong_questions WHERE user_id=? AND question_id=?", (owner, fp)).fetchone()
                if row:
                    question["statusText"] = "已录入"
                    saved.append({"status": "saved", "id": row["id"], "question_no": question["question_no"]})
            if questions and len(saved) == len(questions):
                document.update(state="saved", save_mode="automatic" if automatic else "human", save_results=saved)
            conn.execute("UPDATE photo_jobs SET result_json=?,state=? WHERE id=? AND user_id=?",
                         (json.dumps(document, ensure_ascii=False), document.get("state", job["state"]), job_id, owner))
    return results
