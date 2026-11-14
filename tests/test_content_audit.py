"""题库检查器与全题库作答回归；使用临时数据库。"""
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from fastapi.testclient import TestClient
from app import content_loader, db
from app.main import app
from app.services import ratelimit
from tools.check_content import questions_of, validate_questions


def test_validator_checks_first_question_and_rejects_boolean_answer():
    content = {"type": "quiz", "questions": [
        {"id": "first", "options": ["same", "same"], "answer": True, "explain": ""},
        {"id": "last", "options": ["a", "b"], "answer": 0, "explain": "ok", "skill": "s"},
    ]}
    errors, warnings = validate_questions(content, "test")
    assert len(errors) == 3
    assert all("/first:" in e for e in errors)
    assert len(warnings) == 1
    assert validate_questions({"type": "reading", "blocks": [{"p": "text"}]}, "read") == ([], [])


def test_every_open_unit_grades_correct_and_wrong_answers(tmp_path, monkeypatch):
    monkeypatch.setattr(db, "DB_PATH", tmp_path / "audit.db")
    content_loader.clear_cache()
    ratelimit.reset()
    count = read_count = units = 0
    with TestClient(app) as client:
        token = client.post("/api/v1/session").json()["token"]
        headers = {"Authorization": f"Bearer {token}"}
        for item in content_loader.catalog()["topics"]:
            data = content_loader.topic(item["id"])
            for section in data["sections"]:
                for tier, content in content_loader.section_tiers(section).items():
                    base = f"/api/v1/topics/{data['id']}/sections/{section['id']}"
                    params = {"tier": tier}
                    public = client.get(base, params=params, headers=headers)
                    assert public.status_code == 200, (base, tier, public.text)
                    assert '"answer"' not in public.text and '"explain"' not in public.text
                    assert content_loader.count_questions(content) == len(questions_of(content))
                    if content["type"] == "reading":
                        r = client.post(base + "/read", params=params, headers=headers, json={"confirmed": True})
                        assert r.status_code == 200 and r.json()["ok"], (base, tier, r.text)
                        read_count += 1
                        continue
                    questions = questions_of(content)
                    for correct in (False, True):
                        answers = {qid: q["answer"] if correct else (q["answer"] + 1) % len(q["options"])
                                   for qid, q in questions}
                        r = client.post(base + "/submit", params=params, headers=headers, json={"answers": answers})
                        assert r.status_code == 200, (base, tier, r.text)
                        result = r.json()
                        assert result["total"] == len(questions)
                        assert result["score"] == (100 if correct else 0), (base, tier, result)
                        # 分步练习按「答完」判完成，其他题型按正确率判通过。
                        assert result["passed"] is (correct or content["type"] == "steps")
                        assert len(result["details"]) == len(questions)
                    count += len(questions)
                    units += 1
        assert (count, units, read_count) == (985, 205, 41)


def test_challenge_models_have_unique_independently_verified_answers():
    from tools.verify_challenge_bank import verify
    report = verify()
    assert (report["count"], report["models"]) == (476, 88)


def test_wrongbook_keeps_changed_questions_separate_and_steps_have_context(tmp_path, monkeypatch):
    from app.services import wrongbook
    monkeypatch.setattr(db, "DB_PATH", tmp_path / "versions.db")
    db.init_db()
    with db.tx() as conn:
        conn.execute("INSERT INTO users(id,token_hash,sync_code,created_at,last_seen) VALUES (?,?,?,?,?)",
                     ("version-user", "hash", "sync", "2026-11-13", "2026-11-13"))
        original={"stem":"旧题", "options":["A","B"], "answer":0, "explain":"旧解析"}
        revised={"stem":"新题", "options":["C","D"], "answer":1, "explain":"新解析"}
        for question in (original, revised, revised):
            details=[dict(id="q1",correct=False,picked=1-question['answer'],
                          answer=question['answer'],explain=question['explain'])]
            wrongbook.record_wrong(conn,"version-user","topic","quick","expert",details,{"q1":question})
        rows=conn.execute("SELECT * FROM wrong_questions ORDER BY stem").fetchall()
        assert len(rows)==2
        pairs={r['stem']:(r['answer'],r['wrong_count']) for r in rows}
        assert pairs=={"旧题":(0,1),"新题":(1,2)}
    content={"type":"steps","problems":[{"stem":"父题给定长度5米", "steps":[{"ask":"求时间", "options":["1s","2s"],"answer":0}]}]}
    assert wrongbook.questions_of(content)['p0s0']['stem']=="父题给定长度5米\n求时间"

def test_every_topic_has_intro_guide_svg():
    """主题页顶部「动态引导」缩略图按约定读 /assets/notes/intro-<id>.svg。

    缺这张图会显示成破图（前端不报错，只在页面上露出裂开的图标），
    所以必须在内容自检阶段就拦住。
    """
    import json
    from pathlib import Path

    root = Path(__file__).resolve().parent.parent
    catalog = json.loads((root / "content" / "catalog.json").read_text(encoding="utf-8"))
    missing = []
    for t in catalog["topics"]:
        svg = root / "assets" / "notes" / f"intro-{t['id']}.svg"
        if not svg.exists() or svg.stat().st_size < 1000:
            missing.append(t["id"])
    assert not missing, f"以下主题缺少动态引导图 intro-<id>.svg: {missing}"


def test_topic_diagrams_all_exist():
    """主题里声明的 diagrams 图片必须真实存在。"""
    import json
    from pathlib import Path

    root = Path(__file__).resolve().parent.parent
    catalog = json.loads((root / "content" / "catalog.json").read_text(encoding="utf-8"))
    missing = []
    for t in catalog["topics"]:
        data = json.loads((root / "content" / "topics" / f"{t['id']}.json").read_text(encoding="utf-8"))
        for d in data.get("diagrams") or []:
            rel = d["src"].lstrip("/")
            if not (root / rel).exists():
                missing.append(f"{t['id']}: {d['src']}")
    assert not missing, f"图解文件缺失: {missing}"
