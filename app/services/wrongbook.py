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
import re
import sqlite3
from datetime import date

from app import content_loader

# 纠错事件键前缀（与 routers/wrongbook.py 共用，按「用户 + 错题」幂等）
CORRECT_EVENT_KEY = "wrongcorrect:v1:"


def _cfg() -> dict:
    return content_loader.rewards().get("wrongbook", {})


def today_str() -> str:
    return date.today().isoformat()


def book_owner(user_id: str) -> str:
    """错题本归属：默认全家共用一本（家庭资源）；LEARN_WB_SHARED=0 时退回按账号隔离。

    注意：只用于 wrong_questions 的读写归属。AI 次数、积分、事件仍记在真实账号上。
    """
    from app import db
    return db.SHARED_WRONG_OWNER if db.wrong_book_shared() else user_id


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
        # An omitted/invalid choice is not a wrong selection. Do not let a NULL
        # picked value abort collection of subsequent genuinely wrong answers.
        qtype = q.get("qtype", "choice")
        picked_indices = d.get("picked_indices", [])
        answer_indices = q.get("answer_indices", [])
        if qtype == "multi_choice":
            options = q.get("options", [])
            if not isinstance(picked_indices, list) or not picked_indices or any(
                    type(x) is not int or not 0 <= x < len(options) for x in picked_indices
            ) or len(set(picked_indices)) != len(picked_indices):
                continue
            if not isinstance(answer_indices, list) or not answer_indices or any(
                    type(x) is not int or not 0 <= x < len(options) for x in answer_indices
            ) or len(set(answer_indices)) != len(answer_indices):
                continue
            picked = picked_indices[0]
        else:
            picked = d.get("picked")
            if type(picked) is not int or not 0 <= picked < len(q.get("options", [])):
                continue
            picked_indices = [picked]
            answer = q.get("answer")
            answer_indices = [answer] if type(answer) is int and 0 <= answer < len(q.get("options", [])) else []
        # 同题号换题后另建版本；历史快照和对应答案继续成对保存。
        snapshot = {k: q.get(k) for k in ("stem", "options", "answer", "explain")}
        if qtype == "multi_choice":
            snapshot.update(qtype=qtype, answer_indices=sorted(answer_indices))
        answer = q.get("answer", -1) if qtype == "choice" else -1
        if qtype == "multi_choice":
            answer_indices = sorted(answer_indices)
            picked_indices = sorted(picked_indices)
        fingerprint = hashlib.sha256(json.dumps(snapshot, ensure_ascii=False,
                                                sort_keys=True).encode()).hexdigest()[:16]
        rid = _row_id(user_id, topic_id, section_id, tier, qid + ":" + fingerprint)
        legacy_id = _row_id(user_id, topic_id, section_id, tier, qid)
        legacy = conn.execute("SELECT * FROM wrong_questions WHERE id=?", (legacy_id,)).fetchone()
        if legacy and (legacy["stem"], json.loads(legacy["options_json"]),
                       legacy["answer"], legacy["explain"]) == (
                           q.get("stem", ""), q.get("options", []),
                           q.get("answer"), q.get("explain", "")):
            rid = legacy_id
        existing = conn.execute(
            "SELECT id, wrong_count, status FROM wrong_questions WHERE id = ?", (rid,)
        ).fetchone()
        if existing:
            conn.execute(
                "UPDATE wrong_questions SET ai_analysis=CASE WHEN picked_indices_json=? THEN ai_analysis ELSE NULL END, "
            "ai_model=CASE WHEN picked_indices_json=? THEN ai_model ELSE NULL END, "
            "ai_at=CASE WHEN picked_indices_json=? THEN ai_at ELSE NULL END, picked=?, picked_indices_json=?, "
            "wrong_count=wrong_count+1, last_wrong_at=?, status='open', cleared_at=NULL WHERE id=?",
            (json.dumps(picked_indices), json.dumps(picked_indices), json.dumps(picked_indices), picked,
             json.dumps(picked_indices), now, rid),
            )
        else:
            conn.execute(
            "INSERT INTO wrong_questions(id, user_id, topic_id, section_id, tier, "
            "question_id, skill, stem, options_json, answer, explain, picked, qtype, "
            "answer_indices_json, picked_indices_json, created_at, last_wrong_at) "
            "VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            (rid, user_id, topic_id, section_id, tier, qid,
             d.get("skill", ""), q.get("stem", ""),
             json.dumps(q.get("options", []), ensure_ascii=False), answer,
             d.get("explain", ""), picked, qtype, json.dumps(answer_indices),
             json.dumps(picked_indices), now, now),
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
                out[f"p{pi}s{si}"] = {**st, "stem": p.get("stem", "") + "\n" + st.get("ask", ""),
                                      "explain": st.get("explain", "")}
    return out


def _taxonomy() -> dict:
    """学科/章节分类体系：{subject_id: {label, chapters:{chapter_id: label}}}。"""
    from app import content_loader
    try:
        raw = content_loader.wrongbook_taxonomy()
    except Exception:
        return {}
    out = {}
    for s in raw.get("subjects", []):
        out[s["id"]] = {
            "label": s.get("label", s["id"]),
            "chapters": {c["id"]: c.get("label", c["id"]) for c in s.get("chapters", [])},
        }
    return out


def import_topic_id(subject: str, chapter: str) -> str:
    """导入错题的 topic_id：wb-<subject>-<chapter>；空值归入 misc。"""
    return f"wb-{subject or 'misc'}-{chapter or 'misc'}"


QTYPES = ("choice", "multi_choice", "fill", "solution")


def normalize_qtype(raw, option_count: int) -> str:
    """题型归一：缺省按是否有选项推断；声称选择题却没选项时降级为填空。"""
    qtype = str(raw or "").strip().lower()
    if qtype not in QTYPES:
        qtype = "choice" if option_count >= 2 else "fill"
    if qtype == "choice" and option_count < 2:
        qtype = "fill"
    return qtype


def _norm_answer(text: str) -> str:
    """填空题的有限格式归一，不进行表达式求值或任意字符删除。"""
    s = str(text or "").strip().lower().replace("−", "-").replace("－", "-")
    s = "".join(s.split())
    for prefix in ("f(x)=", "y="):
        if s.startswith(prefix):
            s = s[len(prefix):]
            break
    s = s.replace("\\pi", "π").replace("pi", "π")
    s = s.replace("sqrt(", "√(").replace("sqrt3", "√3").replace("\\sqrt{3}", "√3")
    s = s.replace("×", "*").replace("·", "*")
    s = re.sub(r"(?<=[\d)x])\*(?=(?:sin|cos|tan|√|x|π|\())", "", s)
    return re.sub(r"√\((\d+)\)", r"√\1", s)


def answer_matches(given: str, expected: str) -> bool:
    """填空答案比对：完全一致，或命中等价写法之一（用「或」/逗号分隔的多解）。"""
    if not isinstance(given, str) or not isinstance(expected, str):
        return False
    g = _norm_answer(given)
    if not g:
        return False
    parts = [p for p in expected.split("或") if p.strip()]
    return any(g == _norm_answer(p) for p in parts)


def import_items(conn: sqlite3.Connection, user_id: str, items: list[dict],
                 overwrite: bool = False, review_user_id: str | None = None) -> dict:
    """批量导入错题（录入工具/WorkBuddy 均走这里），返回导入结果明细。

    item 字段：stem(必填)、options、picked、answer、skill、explain、
    subject、chapter、image_path、wrong_reason、derivation。
    同一 (user, topic, stem指纹) 已存在时：overwrite=True 更新，否则跳过去重。
    """
    from app.services import wrongbook_review
    for item in items:
        wrongbook_review.require_receipt(conn, review_user_id or user_id, item)
    tax = _taxonomy()
    valid_subjects = set(tax) | {""}
    now = today_str()
    out = {"imported": [], "skipped": [], "updated": []}
    for i, it in enumerate(items):
        stem = str(it.get("stem", "")).strip()
        if not stem:
            out["skipped"].append({"index": i, "reason": "题干为空"})
            continue
        options = [str(o).strip() for o in (it.get("options") or []) if str(o).strip()]
        qtype = normalize_qtype(it.get("qtype"), len(options))
        if qtype not in ("choice", "multi_choice"):
            options = []
        elif len(options) < 2:
            out["skipped"].append({"index": i, "reason": "选择题选项不足两个"})
            continue
        answer_text = str(it.get("answer_text", "")).strip()[:500] if qtype not in ("choice", "multi_choice") else ""
        review_status = str(it.get("review_status", "ready"))
        review_reason = str(it.get("review_reason", "")).strip()[:500]
        if review_status not in ("ready", "needs_review", "needs_transcription"):
            review_status = "needs_review"
        answer_indices = it.get("answer_indices")
        if qtype == "choice":
            answer = it.get("answer")
            answer_indices = [answer] if type(answer) is int and 0 <= answer < len(options) else []
            answer = answer_indices[0] if answer_indices else -1
        elif qtype == "multi_choice":
            answer = -1
            if not isinstance(answer_indices, list) or any(type(x) is not int or not 0 <= x < len(options) for x in answer_indices) or len(set(answer_indices)) != len(answer_indices) or not answer_indices:
                answer_indices = []
        else:
            answer = -1
            answer_indices = []
        picked_indices = it.get("picked_indices", [])
        if not isinstance(picked_indices, list) or any(type(x) is not int or not 0 <= x < len(options) for x in picked_indices) or len(set(picked_indices)) != len(picked_indices):
            picked_indices = []
        picked = it.get("picked", -1)
        if qtype in ("choice", "multi_choice"):
            if type(picked) is not int or not 0 <= picked < len(options):
                picked = picked_indices[0] if picked_indices else -1
        else:
            picked = -1
        if qtype in ("choice", "multi_choice") and not answer_indices:
            review_status = "needs_transcription"
            review_reason = review_reason or "缺少可核验的标准答案"
        if qtype in ("choice", "multi_choice") and not picked_indices and picked >= 0:
            picked_indices = [picked]
        subject = str(it.get("subject", "")).strip()
        if subject not in valid_subjects:
            subject = ""
        chapters = tax.get(subject, {}).get("chapters", {})
        chapter = str(it.get("chapter", "")).strip()
        if chapter not in chapters:
            chapter = ""
        topic_id = import_topic_id(subject, chapter)
        # 去重键：用户 + 主题 + 题干指纹（题干相同视为同一题）
        fp = hashlib.sha256(stem.encode("utf-8")).hexdigest()[:16]
        rid = "wq_" + hashlib.sha1(f"{user_id}|{topic_id}|import|{fp}".encode()).hexdigest()[:12]
        existing = conn.execute(
            "SELECT id, review_status FROM wrong_questions WHERE id=? OR "
            "(user_id=? AND topic_id=? AND question_id=?)",
            (rid, user_id, topic_id, fp),
        ).fetchone()
        if existing:
            if not overwrite or existing["review_status"] != "ready":
                out["skipped"].append({"index": i, "reason": "已存在相同题目或等待管理员核验", "id": existing["id"]})
                continue
            rid = existing["id"]
            conn.execute(
                "UPDATE wrong_questions SET stem=?, options_json=?, picked=?, answer=?, "
                "skill=?, explain=?, subject=?, chapter=?, image_path=?, "
                "wrong_reason=?, derivation=?, qtype=?, answer_text=?, answer_indices_json=?, "
                "picked_indices_json=?, review_status=?, review_reason=?, content_version=content_version+1, "
                "ai_analysis=NULL, ai_model=NULL, ai_at=NULL, ai_solve=NULL, variants=NULL, "
                "wrong_count=wrong_count+1, last_wrong_at=?, status='open', cleared_at=NULL WHERE id=?",
                (stem, json.dumps(options, ensure_ascii=False), picked, answer,
                 str(it.get("skill", "")), str(it.get("explain", "")),
                 subject, chapter, str(it.get("image_path", "")),
                 str(it.get("wrong_reason", "")), str(it.get("derivation", "")),
                 qtype, answer_text, json.dumps(answer_indices), json.dumps(picked_indices),
                 review_status, review_reason, now, rid),
            )
            out["updated"].append({"index": i, "id": rid, "topic_id": topic_id})
            continue
        conn.execute(
            "INSERT INTO wrong_questions(id, user_id, topic_id, section_id, tier, "
            "question_id, skill, stem, options_json, answer, explain, picked, "
            "source, subject, chapter, image_path, wrong_reason, derivation, "
            "qtype, answer_text, answer_indices_json, picked_indices_json, review_status, review_reason, "
            "created_at, last_wrong_at) "
            "VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            (rid, user_id, topic_id, "import", "import", fp,
             str(it.get("skill", "")), stem,
             json.dumps(options, ensure_ascii=False), answer,
             str(it.get("explain", "")), picked, "import",
             subject, chapter, str(it.get("image_path", "")),
             str(it.get("wrong_reason", "")), str(it.get("derivation", "")),
             qtype, answer_text, json.dumps(answer_indices), json.dumps(picked_indices),
             review_status, review_reason, now, now),
        )
        out["imported"].append({"index": i, "id": rid, "topic_id": topic_id})
    return out


# 仅显式共享的拍照任务扩展可见性，既有私有照片和家庭题库保持原规则。
SHARED_PHOTO_SQL = """(source='photo' AND EXISTS (
    SELECT 1 FROM photo_jobs pj WHERE pj.user_id=wrong_questions.user_id
    AND wrong_questions.image_path='/api/v1/wrongbook/photo/image/' || pj.id
    AND json_extract(pj.result_json, '$.metadata.shared_readonly')=1))"""


def summary(conn: sqlite3.Connection, user_id: str, viewer_id: str | None = None) -> dict:
    """按主题汇总错题；待审核题单独计数，不参与练习进度。"""
    cfg = _cfg()
    rows = conn.execute(
        "SELECT topic_id, "
        "SUM(CASE WHEN status='open' AND review_status='ready' THEN 1 ELSE 0 END) AS open_n, "
        "SUM(CASE WHEN status='open' AND review_status<>'ready' THEN 1 ELSE 0 END) AS pending_n, "
        "SUM(CASE WHEN status='cleared' AND review_status='ready' THEN 1 ELSE 0 END) AS cleared_n, "
        "MAX(last_wrong_at) AS last_at "
        f"FROM wrong_questions WHERE (user_id=? AND source<>'photo') OR (user_id=? AND source='photo') OR {SHARED_PHOTO_SQL} GROUP BY topic_id "
        "ORDER BY open_n DESC, last_at DESC",
        (user_id, viewer_id or user_id),
    ).fetchall()

    cat = {t["id"]: t for t in content_loader.catalog()["topics"]}
    topics = []
    for r in rows:
        # 拍照录入的错题没有真实主题，按 photo-<学科> 归组并给友好标题
        if r["topic_id"].startswith("photo-"):
            subj = r["topic_id"].split("-", 1)[1]
            label = {"physics": "物理", "chemistry": "化学", "math": "数学"}.get(subj, "理科")
            topics.append({
                "topic_id": r["topic_id"],
                "title": f"📷 拍照错题 · {label}",
                "subject": subj if subj in ("physics", "chemistry", "math") else "",
                "subtitle": "手机拍照导入的题目",
                "open": r["open_n"],
                "pending": r["pending_n"],
                "cleared": r["cleared_n"],
                "last_at": r["last_at"],
            })
            continue
        # 导入的错题按 wb-<学科>-<章节> 归组，用分类体系给友好标题
        if r["topic_id"].startswith("wb-"):
            parts = r["topic_id"].split("-", 2)
            subj_id = parts[1] if len(parts) > 1 else "misc"
            chapter_id = parts[2] if len(parts) > 2 else "misc"
            tax = _taxonomy()
            subj_label = tax.get(subj_id, {}).get("label", "未分类")
            chapter_label = tax.get(subj_id, {}).get("chapters", {}).get(chapter_id, "未分类")
            topics.append({
                "topic_id": r["topic_id"],
                "title": f"📥 {subj_label} · {chapter_label}",
                "subject": subj_id if subj_id != "misc" else "",
                "chapter": chapter_id if chapter_id != "misc" else "",
                "subtitle": "录入工具导入的题目",
                "open": r["open_n"],
                "pending": r["pending_n"],
                "cleared": r["cleared_n"],
                "last_at": r["last_at"],
            })
            continue
        t = cat.get(r["topic_id"], {})
        topics.append({
            "topic_id": r["topic_id"],
            "title": t.get("title", r["topic_id"]),
            "subject": t.get("subject", ""),
            "subtitle": t.get("subtitle", ""),
            "open": r["open_n"],
            "pending": r["pending_n"],
            "cleared": r["cleared_n"],
            "last_at": r["last_at"],
        })
    open_total = sum(t["open"] for t in topics)
    return {
        "topics": topics,
        "open_total": open_total,
        "pending_total": sum(t.get("pending", 0) for t in topics),
        "clear_bonus": int(cfg.get("clear_bonus", 0)),
        "total_count": sum(t["open"] + t["pending"] + t["cleared"] for t in topics),
    }


def topic_items(conn: sqlite3.Connection, user_id: str, topic_id: str,
                status: str = "open", viewer_id: str | None = None) -> list[dict]:
    rows = conn.execute(
        f"SELECT * FROM wrong_questions WHERE ((user_id=? AND source<>'photo') OR (user_id=? AND source='photo') OR {SHARED_PHOTO_SQL}) AND topic_id=? AND ((status=? AND review_status='ready') OR (status='open' AND review_status<>'ready')) "
        "ORDER BY last_wrong_at DESC",
        (user_id, viewer_id or user_id, topic_id, status),
    ).fetchall()
    items = []
    for r in rows:
        options = json.loads(r["options_json"])
        images = [p for p in (r["image_path"].split(",") if "image_path" in r.keys() and r["image_path"] else []) if p]
        items.append({
            "id": r["id"],
            "owner_id": r["user_id"],
            "owner_name": (conn.execute("SELECT username FROM users WHERE id=?", (r["user_id"],)).fetchone() or {"username": ""})["username"],
            "can_edit": r["source"] != "photo" or r["user_id"] == (viewer_id or user_id),
            "topic_id": r["topic_id"],
            "section_id": r["section_id"],
            "question_id": r["question_id"],
            "tier": r["tier"],
            "skill": r["skill"],
            "stem": r["stem"],
            "options": options,
            "picked": r["picked"],
            "answer": r["answer"],
            "answer_indices": json.loads(r["answer_indices_json"] or "[]"),
            "picked_indices": json.loads(r["picked_indices_json"] or "[]"),
            "explain": r["explain"],
            "wrong_count": r["wrong_count"],
            "source": r["source"] if "source" in r.keys() else "practice",
            "subject": r["subject"] if "subject" in r.keys() else "",
            "chapter": r["chapter"] if "chapter" in r.keys() else "",
            "images": images,
            "qtype": r["qtype"] if "qtype" in r.keys() else "choice",
            "answer_text": r["answer_text"] if "answer_text" in r.keys() else "",
            "review_status": r["review_status"],
            "review_reason": r["review_reason"],
            "status": r["status"],
            "content_version": r["content_version"],
            "wrong_reason": r["wrong_reason"] if "wrong_reason" in r.keys() else "",
            "derivation": r["derivation"] if "derivation" in r.keys() else "",
            "corrected_at": r["corrected_at"] if "corrected_at" in r.keys() else "",
            "correct_note": r["correct_note"] if "correct_note" in r.keys() else "",
            "corrected_by_me": bool(conn.execute(
                "SELECT 1 FROM events WHERE user_id=? AND key=?",
                (viewer_id or user_id, f"{viewer_id or user_id}:{CORRECT_EVENT_KEY}{r['id']}")).fetchone()),
            "ai": cached_ai(r["ai_analysis"]),
            "ai_solve": cached_ai(r["ai_solve"]),
            "variants": cached_ai(r["variants"]),
            "last_wrong_at": r["last_wrong_at"],
        })
    return items


def cached_ai(raw) -> dict | None:
    from app.services import ai_client
    if not raw:
        return None
    try:
        value = json.loads(raw)
    except (ValueError, TypeError):
        return None
    if not isinstance(value, dict) or (value.get("stub") and not ai_client._stub_on()):
        return None
    return value


def redo(conn: sqlite3.Connection, user: sqlite3.Row, topic_id: str,
         answers: dict[str, int], fill_answers: dict[str, str] | None = None,
         multi_answers: dict[str, list[int]] | None = None) -> dict:
    """错题重做判分：答对清零，答错继续留库并累加次数。

    选择题用 answers（题 id → 选项序号）；填空/解答题用 fill_answers（题 id → 答案文本，
    按归一化字符串比对）。错题行归属共享错题本，清零奖励记在「当前操作的人」账上。
    """
    owner = book_owner(user["id"])
    multi_answers = multi_answers or {}
    submitted = set(answers) | set(fill_answers or {}) | set(multi_answers)
    if submitted:
        placeholders = ",".join("?" for _ in submitted)
        forbidden = conn.execute(
            f"SELECT 1 FROM wrong_questions WHERE id IN ({placeholders}) AND source='photo' AND user_id<>?",
            (*submitted, user["id"]),
        ).fetchone()
        if forbidden:
            raise ValueError("共享照片只读，只有所有者可以重做或修改")
    rows = conn.execute(
        "SELECT * FROM wrong_questions WHERE ((user_id=? AND source<>'photo') OR (user_id=? AND source='photo')) AND topic_id=? AND status='open' AND review_status='ready'",
        (owner, user["id"], topic_id),
    ).fetchall()
    if not rows:
        raise ValueError("这个主题当前没有待清零的错题")

    fill_answers = fill_answers or {}
    results = []
    cleared_now = 0
    re_wrong = 0
    for r in rows:
        qtype = r["qtype"] if "qtype" in r.keys() else "choice"
        if (qtype not in ("choice", "multi_choice") and not r["answer_text"]) or (qtype == "choice" and not 0 <= r["answer"] < len(json.loads(r["options_json"]))):
            results.append({"id": r["id"], "skipped": True, "qtype": qtype, "correct": False,
                            "stem": r["stem"], "answer": r["answer"], "explain": "尚无标准答案，未判分"})
            continue
        if qtype == "multi_choice":
            if r["review_status"] != "ready":
                results.append({"id": r["id"], "skipped": True, "qtype": qtype,
                                "stem": r["stem"], "explain": r["review_reason"] or "待补录，未判分", "correct": False})
                continue
            picked_set = multi_answers.get(r["id"] )
            total = len(json.loads(r["options_json"]))
            if not isinstance(picked_set, list) or not picked_set:
                results.append({"id": r["id"], "skipped": True, "qtype": qtype,
                                "stem": r["stem"], "answer_indices": json.loads(r["answer_indices_json"] or "[]"),
                                "explain": r["explain"], "correct": False})
                continue
            if any(type(x) is not int or not 0 <= x < total for x in picked_set) or len(set(picked_set)) != len(picked_set):
                raise ValueError("多选答案选项无效")
            expected = json.loads(r["answer_indices_json"] or "[]")
            if not expected or any(type(x) is not int or not 0 <= x < total for x in expected) or len(set(expected)) != len(expected):
                results.append({"id": r["id"], "skipped": True, "qtype": qtype, "correct": False,
                                "explain": "标准答案待补录，未判分"})
                continue
            correct = set(picked_set) == set(expected)
            if correct:
                conn.execute("UPDATE wrong_questions SET status='cleared', cleared_at=?, last_wrong_at=? WHERE id=? AND status='open' AND review_status='ready'",
                             (today_str(), today_str(), r["id"]))
                cleared_now += 1
            else:
                conn.execute("UPDATE wrong_questions SET ai_analysis=CASE WHEN picked_indices_json=? THEN ai_analysis ELSE NULL END, "
                             "ai_model=CASE WHEN picked_indices_json=? THEN ai_model ELSE NULL END, "
                             "ai_at=CASE WHEN picked_indices_json=? THEN ai_at ELSE NULL END, "
                             "picked_indices_json=?, wrong_count=wrong_count+1, last_wrong_at=? WHERE id=? AND status='open' AND review_status='ready'",
                             (json.dumps(picked_set), json.dumps(picked_set), json.dumps(picked_set), json.dumps(picked_set), today_str(), r["id"]))
                re_wrong += 1
            results.append({"id": r["id"], "stem": r["stem"], "qtype": qtype,
                            "picked_indices": picked_set, "answer_indices": expected,
                            "correct": correct, "cleared": correct, "explain": r["explain"]})
            continue
        if qtype != "choice":
            given = str(fill_answers.get(r["id"], "")).strip()
            if not given:
                results.append({"id": r["id"], "skipped": True, "qtype": qtype,
                                "stem": r["stem"], "answer": r["answer"],
                                "answer_text": r["answer_text"] if "answer_text" in r.keys() else "",
                                "explain": r["explain"], "correct": False})
                continue
            correct = answer_matches(given, r["answer_text"] if "answer_text" in r.keys() else "")
            if correct:
                conn.execute(
                    "UPDATE wrong_questions SET status='cleared', cleared_at=?, last_wrong_at=? "
                    "WHERE id=? AND status='open'",
                    (today_str(), today_str(), r["id"]),
                )
                cleared_now += 1
            else:
                conn.execute(
                    "UPDATE wrong_questions SET wrong_count=wrong_count+1, last_wrong_at=? "
                    "WHERE id=? AND status='open'",
                    (today_str(), r["id"]),
                )
                re_wrong += 1
            results.append({
                "id": r["id"], "stem": r["stem"], "qtype": qtype, "picked": -1,
                "answer": -1, "answer_text": r["answer_text"] if "answer_text" in r.keys() else "",
                "given": given, "correct": correct, "cleared": correct,
                "explain": r["explain"], "skill": r["skill"],
            })
            continue
        picked = answers.get(r["id"])
        if picked is None:
            results.append({"id": r["id"], "skipped": True, "qtype": qtype,
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
                "UPDATE wrong_questions SET ai_analysis=CASE WHEN picked IS ? THEN ai_analysis ELSE NULL END, "
                "ai_model=CASE WHEN picked IS ? THEN ai_model ELSE NULL END, "
                "ai_at=CASE WHEN picked IS ? THEN ai_at ELSE NULL END, picked=?, wrong_count=wrong_count+1, "
                "last_wrong_at=? WHERE id=? AND status='open'",
                (picked, picked, picked, picked, today_str(), r["id"]),
            )
            re_wrong += 1
        results.append({
            "id": r["id"], "stem": r["stem"], "picked": picked, "qtype": qtype,
            "answer": r["answer"], "correct": correct, "cleared": correct,
            "explain": r["explain"], "skill": r["skill"],
        })

    bonus = 0
    remaining = conn.execute(
        "SELECT COUNT(*) AS n FROM wrong_questions "
        "WHERE ((user_id=? AND source<>'photo') OR (user_id=? AND source='photo')) AND topic_id=? AND status='open' AND review_status='ready'",
        (owner, user["id"], topic_id),
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


def save_solve(conn: sqlite3.Connection, user_id: str, wq_id: str, result: dict) -> None:
    """缓存 AI 独立解题结果（含实际生效通道/模型，便于排查）。"""
    conn.execute(
        "UPDATE wrong_questions SET ai_solve=? WHERE id=? AND user_id=?",
        (json.dumps(result, ensure_ascii=False), wq_id, user_id),
    )


def save_variants(conn: sqlite3.Connection, user_id: str, wq_id: str, result: dict) -> None:
    """缓存 AI 举一反三的变式题组。"""
    conn.execute(
        "UPDATE wrong_questions SET variants=? WHERE id=? AND user_id=?",
        (json.dumps(result, ensure_ascii=False), wq_id, user_id),
    )


def ai_pending(conn: sqlite3.Connection, user_id: str, wq_id: str) -> sqlite3.Row | None:
    return conn.execute(
        "SELECT * FROM wrong_questions WHERE id=? AND user_id=? AND review_status='ready'",
        (wq_id, user_id),
    ).fetchone()


def ai_used_today(conn: sqlite3.Connection, user_id: str) -> int:
    """今日全部 AI 调用次数（各任务合计）。"""
    return conn.execute(
        "SELECT COUNT(*) AS n FROM events WHERE user_id=? AND kind='ai' "
        "AND substr(created_at,1,10)=?",
        (user_id, today_str()),
    ).fetchone()["n"]


def ai_used_by_task(conn: sqlite3.Connection, user_id: str) -> dict[str, int]:
    """今日按任务拆分的 AI 用量；旧事件 payload 无 task 字段，归入 analyze。"""
    rows = conn.execute(
        "SELECT COALESCE(json_extract(payload,'$.task'),'analyze') AS task, COUNT(*) AS n "
        "FROM events WHERE user_id=? AND kind='ai' AND substr(created_at,1,10)=? "
        "GROUP BY task",
        (user_id, today_str()),
    ).fetchall()
    return {r["task"]: r["n"] for r in rows}
