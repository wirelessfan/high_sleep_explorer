"""拍照错题录入（演示流程）：识别 → 三合一分析 → 入库 → 错题本分组。"""
import pytest
from starlette.testclient import TestClient

from app import content_loader, db
from app.main import app

# 1x1 像素 JPEG 的 base64，足够通过「非空」校验
TINY_JPEG = (
    "/9j/4AAQSkZJRgABAQEAYABgAAD/2wBDAAgGBgcGBQgHBwcJCQgKDBQNDAsLDBkSEw8UHRofHh0a"
    "HBwgJC4nICIsIxwcKDcpLDAxNDQ0Hyc5PTgyPC4zNDL/wAALCAABAAEBAREA/8QAFAABAAAAAAAA"
    "AAAAAAAAAAAACf/EABQQAQAAAAAAAAAAAAAAAAAAAAD/2gAIAQEAAD8AKp//2Q=="
)


@pytest.fixture()
def client(tmp_path, monkeypatch):
    dbfile = tmp_path / "test.db"
    monkeypatch.setattr(db, "DB_PATH", dbfile)
    monkeypatch.setenv("LEARN_WB_IMAGES", str(tmp_path / "images"))
    content_loader.clear_cache()
    from app.services import ratelimit
    ratelimit.reset()
    with TestClient(app) as c:
        yield c


@pytest.fixture()
def auth(client):
    r = client.post("/api/v1/session")
    assert r.status_code == 200
    return {"Authorization": f"Bearer {r.json()['token']}"}


def _stub_ai(monkeypatch):
    from app.services import ai_client
    monkeypatch.setattr(ai_client, "CHANNELS",
                        {cid: {**ch, "key": "test-key"}
                         for cid, ch in ai_client.CHANNELS.items()})
    monkeypatch.setattr(ai_client, "enabled", lambda: True)
    monkeypatch.setenv("LEARN_AI_STUB", "1")


# ---------- 识别 ----------

def test_recognize_with_stub(client, auth, monkeypatch):
    _stub_ai(monkeypatch)
    r = client.post("/api/v1/wrongbook/photo/recognize",
                    json={"image": TINY_JPEG}, headers=auth)
    assert r.status_code == 200
    d = r.json()["result"]
    assert d["stub"] is True
    assert d["stem"]
    assert len(d["questions"]) >= 2
    assert d["questions"][0]["qtype"] == "fill"
    assert d["subject"] in ("physics", "chemistry", "math")


def test_recognize_accepts_data_url(client, auth, monkeypatch):
    _stub_ai(monkeypatch)
    r = client.post("/api/v1/wrongbook/photo/recognize",
                    json={"image": "data:image/jpeg;base64," + TINY_JPEG}, headers=auth)
    assert r.status_code == 200


def test_recognize_without_ai_returns_503(client, auth, monkeypatch):
    from app.services import ai_client
    monkeypatch.setattr(ai_client, "CHANNELS",
                        {cid: {**ch, "key": ""} for cid, ch in ai_client.CHANNELS.items()})
    monkeypatch.delenv("LEARN_AI_STUB", raising=False)
    r = client.post("/api/v1/wrongbook/photo/recognize",
                    json={"image": TINY_JPEG}, headers=auth)
    assert r.status_code == 503


def test_recognize_rejects_empty_image(client, auth, monkeypatch):
    _stub_ai(monkeypatch)
    r = client.post("/api/v1/wrongbook/photo/recognize", json={"image": " "}, headers=auth)
    assert r.status_code == 422  # min_length 拦截


# ---------- 三合一分析 ----------

def test_photo_analyze_returns_three_blocks(client, auth, monkeypatch):
    _stub_ai(monkeypatch)
    r = client.post("/api/v1/wrongbook/photo/analyze", json={
        "stem": "把质量 m=2kg 的物体从高处静止释放，求 3s 内重力做的功（g 取 10 m/s²）。",
        "options": ["90 J", "180 J", "270 J", "360 J"],
        "picked": 0,
    }, headers=auth)
    assert r.status_code == 200
    d = r.json()
    assert d["errors"] == {}
    assert d["solve"]["answer_letter"] in ("A", "B", "C", "D")
    assert isinstance(d["solve"]["steps"], list) and d["solve"]["steps"]
    assert d["analyze"]["analysis"]
    assert len(d["variants"]["variants"]) == 2


def test_photo_analyze_records_usage_by_task(client, auth, monkeypatch):
    _stub_ai(monkeypatch)
    client.post("/api/v1/wrongbook/photo/analyze", json={
        "stem": "测试题题干内容足够长用于分析", "options": ["A项", "B项", "C项"], "picked": 1,
    }, headers=auth)
    from app.services import wrongbook
    with db.ro() as conn:
        used = wrongbook.ai_used_by_task(conn, _uid(client, auth))
    assert used.get("solve") == 1
    assert used.get("analyze") == 1
    assert used.get("variants") == 1


def _uid(client, headers):
    return client.get("/api/v1/me", headers=headers).json()["id"]


def test_photo_analyze_respects_task_limit(client, auth, monkeypatch):
    _stub_ai(monkeypatch)
    # 把 variants 限额压到 1，第二次应 429
    with db.tx() as conn:
        conn.execute(
            "INSERT INTO ai_config(id, config) VALUES (1, ?) "
            "ON CONFLICT(id) DO UPDATE SET config=excluded.config",
            ('{"limits":{"variants":1}}',),
        )
    body = {"stem": "限额测试题目题干内容", "options": ["A", "B", "C"], "picked": 0}
    assert client.post("/api/v1/wrongbook/photo/analyze", json=body, headers=auth).status_code == 200
    r = client.post("/api/v1/wrongbook/photo/analyze", json=body, headers=auth)
    assert r.status_code == 429
    assert "举一反三" in r.json()["detail"]


# ---------- 入库 ----------

def test_photo_save_creates_wrong_question(client, auth):
    uid = _uid(client, auth)
    r = client.post("/api/v1/wrongbook/photo/save", json={
        "stem": "一物体做匀加速直线运动，初速度为 2 m/s，加速度 3 m/s²，求 2s 末速度。",
        "options": ["6 m/s", "8 m/s", "10 m/s", "12 m/s"],
        "picked": 0,
        "answer": 1,
        "subject": "physics",
        "skill": "匀变速直线运动",
        "explain": "v = v0 + at = 2 + 3×2 = 8 m/s",
    }, headers=auth)
    assert r.status_code == 200
    d = r.json()
    assert d["id"].startswith("wq_")
    assert d["topic_id"] == "photo-physics"
    assert d["answer"] == 1

    with db.ro() as conn:
        row = conn.execute("SELECT * FROM wrong_questions WHERE id=?", (d["id"],)).fetchone()
    assert row["source"] == "photo"
    assert row["user_id"] in (uid, "u_family")
    assert row["topic_id"] == "photo-physics"
    assert row["picked"] == 0
    assert row["status"] == "open"


def test_photo_save_appears_in_wrongbook_with_friendly_title(client, auth):
    client.post("/api/v1/wrongbook/photo/save", json={
        "stem": "化学题：计算 2 mol 水的质量。",
        "options": ["18 g", "36 g", "54 g"],
        "picked": 0, "answer": 1, "subject": "chemistry",
    }, headers=auth)

    wb = client.get("/api/v1/wrongbook", headers=auth).json()
    topics = wb["summary"]["topics"]
    photo = next(t for t in topics if t["topic_id"] == "photo-chemistry")
    assert "拍照错题" in photo["title"]
    assert "化学" in photo["title"]
    assert photo["subject"] == "chemistry"
    assert photo["open"] == 0
    assert photo["pending"] == 1
    assert wb["items"][0]["source"] == "photo"
    assert wb["items"][0]["review_status"] == "needs_review"


def test_photo_save_misc_subject_fallback(client, auth):
    r = client.post("/api/v1/wrongbook/photo/save", json={
        "stem": "无法判断学科的题目内容", "options": ["甲", "乙"], "picked": 0,
        "answer": 1, "subject": "biology",
    }, headers=auth)
    assert r.json()["topic_id"] == "photo-biology"
    wb = client.get("/api/v1/wrongbook", headers=auth).json()
    t = next(x for x in wb["summary"]["topics"] if x["topic_id"] == "photo-biology")
    assert "拍照错题" in t["title"] and "理科" in t["title"]


def test_photo_save_validates_options(client, auth):
    r = client.post("/api/v1/wrongbook/photo/save", json={
        "stem": "题目", "options": ["只有一个"], "picked": 0,
    }, headers=auth)
    assert r.status_code == 400
    assert "两个选项" in r.json()["detail"]

    r2 = client.post("/api/v1/wrongbook/photo/save", json={
        "stem": "题目", "options": ["甲", "乙"], "picked": 5,
    }, headers=auth)
    assert r2.status_code in (400, 422), "所选项超界必须被拒绝"
    assert "超出范围" in r2.json()["detail"] or "参数" in str(r2.json())


def test_photo_saved_without_strong_review_cannot_be_redone(client, auth):
    """人工录入只能进入待审核区，不能绕过GPT直接重做清零。"""
    d = client.post("/api/v1/wrongbook/photo/save", json={
        "stem": "拍照录入的重做题", "options": ["甲", "乙", "丙"], "picked": 0,
        "answer": 2, "subject": "math",
    }, headers=auth).json()

    r = client.post("/api/v1/wrongbook/photo-math/redo",
                    json={"answers": {d["id"]: 2}}, headers=auth)
    assert r.status_code == 400
    with db.ro() as conn:
        row = conn.execute("SELECT status, review_status FROM wrong_questions WHERE id=?", (d["id"],)).fetchone()
    assert tuple(row) == ("open", "needs_review")


def test_photo_endpoints_require_auth(client):
    for path, body in (
        ("/wrongbook/photo/recognize", {"image": TINY_JPEG}),
        ("/wrongbook/photo/analyze", {"stem": "x", "options": ["a"], "picked": 0}),
        ("/wrongbook/photo/save", {"stem": "x", "options": ["a", "b"], "picked": 0}),
    ):
        assert client.post(path and f"/api/v1{path}", json=body).status_code == 401


def test_recognize_returns_ordered_questions_and_compat_fields(monkeypatch):
    from app.services import ai_client
    monkeypatch.setattr(ai_client, "enabled", lambda: True)
    monkeypatch.delenv("LEARN_AI_STUB", raising=False)
    monkeypatch.setattr(ai_client, "chat", lambda *args, **kwargs: {
        "text": '{"questions":[{"question_no":"1","stem":"共享材料：实验记录。求速度。",'
                 '"options":["1 m/s","2 m/s"],"subject":"physics","uncertain":[],"needs_image":false},'
                 '{"question_no":"2","stem":"若 x=2，求 x^2。","options":[],"subject":"math",'
                 '"uncertain":["指数位置"],"needs_image":true,"image_hint":"见原图"}],"warnings":[]}',
        "channel": "deepseek", "model": "deepseek-v4.1-flash",
    })
    result = ai_client.recognize(TINY_JPEG)
    assert [q["question_no"] for q in result["questions"]] == ["1", "2"]
    assert result["questions"][1]["options"] == []
    assert result["questions"][1]["needs_image"] is True
    assert "stem" not in result


def test_recognize_single_response_keeps_legacy_shape(monkeypatch):
    from app.services import ai_client
    monkeypatch.setattr(ai_client, "enabled", lambda: True)
    monkeypatch.delenv("LEARN_AI_STUB", raising=False)
    monkeypatch.setattr(ai_client, "chat", lambda *args, **kwargs: {
        "text": '{"stem":"单题","options":["甲","乙"],"subject":"math"}',
        "channel": "deepseek", "model": "deepseek-v4.1-flash",
    })
    result = ai_client.recognize(TINY_JPEG)
    assert len(result["questions"]) == 1
    assert result["stem"] == "单题"
    assert result["options"] == ["甲", "乙"]


def test_recognize_rejects_malformed_and_too_many_questions(monkeypatch):
    from app.services import ai_client
    monkeypatch.setattr(ai_client, "enabled", lambda: True)
    monkeypatch.delenv("LEARN_AI_STUB", raising=False)
    monkeypatch.setattr(ai_client, "chat", lambda *args, **kwargs: {
        "text": '{"questions":' + str([{"stem": "题", "options": []}] * 21).replace("'", '"') + '}',
        "channel": "deepseek", "model": "deepseek-v4.1-flash",
    })
    with pytest.raises(RuntimeError, match="最多 20"):
        ai_client.recognize(TINY_JPEG)

    monkeypatch.setattr(ai_client, "chat", lambda *args, **kwargs: {
        "text": '{"questions":[{"options":[]}]}',
        "channel": "deepseek", "model": "deepseek-v4.1-flash",
    })
    with pytest.raises(RuntimeError, match="缺少题干"):
        ai_client.recognize(TINY_JPEG)


def test_photo_save_batch_reports_no_option_and_duplicate(client, auth):
    body = {"items": [
        {"question_no": "1", "stem": "无选项题", "qtype": "fill", "options": [], "picked": -1, "answer": -1},
        {"question_no": "2", "stem": "可保存题", "qtype": "choice", "options": ["甲", "乙"], "picked": 0, "answer": -1},
        {"question_no": "3", "stem": "可保存题", "qtype": "choice", "options": ["甲", "乙"], "picked": 0, "answer": -1},
    ]}
    r = client.post("/api/v1/wrongbook/photo/save-batch", json=body, headers=auth)
    assert r.status_code == 200
    statuses = [x["status"] for x in r.json()["results"]]
    assert statuses == ["saved", "saved", "duplicate"]
    assert r.json()["results"][0]["qtype"] == "fill"


def _pipeline(monkeypatch, status="passed"):
    from app.services import ai_client
    _stub_ai(monkeypatch)
    original = ai_client.recognize_stub()
    original.update(channel="glm", model="glm-5.3-flash", warnings=[])
    for q in original["questions"]:
        q["answer_text"] = ""
    monkeypatch.setattr(ai_client, "recognize", lambda *a, **k: original)
    def confirm(image, source, **kwargs):
        import copy
        questions = copy.deepcopy(source["questions"])
        if status == "revised":
            questions[0]["stem"] = "修订题干，原始识别有错误"
        return {"status": status, "questions": questions, "complete": status != "pending",
                "reasons": ["修复漏字"] if status == "revised" else [],
                "channel": "review91", "model": "gpt-6.1-sol"}
    monkeypatch.setattr(ai_client, "confirm_photo", confirm)
    return original


def test_gpt_pass_auto_saves_and_retry_is_idempotent(client, auth, monkeypatch):
    _pipeline(monkeypatch)
    body = {"image": TINY_JPEG, "approved": True}
    out = client.post('/api/v1/wrongbook/photo/recognize', json=body, headers=auth).json()['result']
    assert out['state'] == 'saved'
    assert len(out['save_results']) == 2
    assert len(client.get('/api/v1/wrongbook', headers=auth).json()['items']) == 2
    again = client.post('/api/v1/wrongbook/photo/recognize', json={**body, 'retry': True}, headers=auth).json()['result']
    assert again['job_id'] == out['job_id']
    with db.ro() as conn:
        rows = conn.execute('SELECT * FROM wrong_questions').fetchall()
    assert len(rows) == 2 and all(r['answer'] == -1 and r['answer_text'] == '' for r in rows)


def test_gpt_revision_keeps_original_and_requires_human(client, auth, monkeypatch):
    original = _pipeline(monkeypatch, 'revised')
    out = client.post('/api/v1/wrongbook/photo/recognize', json={'image': TINY_JPEG}, headers=auth).json()['result']
    assert out['state'] == 'manual_review' and out['original'] == original
    assert client.get('/api/v1/wrongbook', headers=auth).json()['items'] == []
    item = {**out['questions'][0], 'job_id': out['job_id'], 'item_index': 0, 'picked': -1}
    r = client.post('/api/v1/wrongbook/photo/save-batch', json={'items': [item]}, headers=auth).json()
    assert r['results'][0]['status'] == 'saved'
    item.update(stem='人工编辑后再试', subject='chemistry')
    r = client.post('/api/v1/wrongbook/photo/save-batch', json={'items': [item]}, headers=auth).json()
    assert r['results'][0]['status'] == 'duplicate'
    with db.ro() as conn:
        row = conn.execute('SELECT original_json,review_json FROM photo_jobs').fetchone()
    assert 'glm-5.3-flash' in row['original_json'] and '修复漏字' in row['review_json']


@pytest.mark.parametrize('failure', ['network', 'pending'])
def test_gpt_failure_or_uncertain_never_saves(client, auth, monkeypatch, failure):
    from app.services import ai_client
    _pipeline(monkeypatch, 'pending')
    if failure == 'network':
        def fail(*a, **k):
            raise RuntimeError('GPT 网络失败')
        monkeypatch.setattr(ai_client, 'confirm_photo', fail)
    out = client.post('/api/v1/wrongbook/photo/recognize', json={'image': TINY_JPEG, 'approved': True}, headers=auth).json()['result']
    assert out['state'] == 'pending'
    assert client.get('/api/v1/wrongbook', headers=auth).json()['items'] == []
    item = {**out['questions'][0], 'job_id': out['job_id'], 'item_index': 0, 'approved': True}
    res = client.post('/api/v1/wrongbook/photo/save-batch', json={'items': [item]}, headers=auth).json()
    assert res['results'][0]['status'] == 'failed'
    _pipeline(monkeypatch)
    out = client.post('/api/v1/wrongbook/photo/retry/'+out['job_id'], json={}, headers=auth).json()['result']
    assert out['state'] == 'saved'


def test_photo_jobs_and_saved_questions_are_user_isolated(client, auth, monkeypatch):
    _pipeline(monkeypatch)
    out = client.post('/api/v1/wrongbook/photo/recognize', json={'image': TINY_JPEG}, headers=auth).json()['result']
    other = {'Authorization': 'Bearer '+client.post('/api/v1/session').json()['token']}
    assert client.get('/api/v1/wrongbook', headers=other).json()['items'] == []
    assert client.get('/api/v1/wrongbook/photo/jobs', headers=other).json()['jobs'] == []
    assert client.get(out['image_path'], headers=other).status_code == 404
    assert client.get(out['image_path']).status_code == 401
    assert client.get(out['image_path'], headers=auth).status_code == 200
    assert client.post('/api/v1/wrongbook/photo/retry/'+out['job_id'], json={}, headers=other).status_code == 404
    item = {**out['questions'][0], 'job_id': out['job_id'], 'item_index': 0}
    assert client.post('/api/v1/wrongbook/photo/save-batch', json={'items':[item]}, headers=other).json()['results'][0]['status'] == 'failed'
    wq = out['save_results'][0]['id']
    assert client.post('/api/v1/wrongbook/ai/solve', json={'ids':[wq]}, headers=other).json()['results'][0]['error'] == '错题不存在'
    db.init_db()
    assert client.get('/api/v1/wrongbook', headers=other).json()['items'] == []


def test_auto_partial_write_rolls_back_and_recovers(client, auth, monkeypatch):
    _pipeline(monkeypatch)
    with db.tx() as conn:
        conn.execute("CREATE TRIGGER fail_second BEFORE INSERT ON wrong_questions WHEN NEW.subject='math' BEGIN SELECT RAISE(ABORT,'测试写入失败'); END")
    out = client.post('/api/v1/wrongbook/photo/recognize', json={'image': TINY_JPEG}, headers=auth).json()['result']
    assert out['state'] == 'pending'
    with db.ro() as conn:
        assert conn.execute('SELECT COUNT(*) FROM wrong_questions').fetchone()[0] == 0
    with db.tx() as conn:
        conn.execute('DROP TRIGGER fail_second')
    out = client.post('/api/v1/wrongbook/photo/retry/'+out['job_id'], json={}, headers=auth).json()['result']
    assert out['state'] == 'saved' and len(out['save_results']) == 2


def test_gpt_confirmation_sends_image_and_falls_back_on_invalid_pass(monkeypatch):
    import copy
    import json
    from app.services import ai_client
    monkeypatch.delenv('LEARN_AI_STUB', raising=False)
    original = ai_client.recognize_stub()
    monkeypatch.setattr(ai_client, '_load_cfg', lambda conn: {'routing':{},'channels':{},'limits':{}})
    monkeypatch.setattr(ai_client, 'CHANNELS', {cid:{'id':cid,'key':'test','vision':True,'model':'gpt-6.1-sol'} for cid in ('review91','reviewugq')})
    calls=[]
    def post(ch, model, messages, *args):
        assert messages[1]['content'][0]['image_url']['url'].startswith('data:image/jpeg;base64,')
        calls.append(ch['id'])
        qs=copy.deepcopy(original['questions'])
        if ch['id']=='review91':
            qs[0]['stem']='偷改题干还称通过'
        return json.dumps({'status':'passed','complete':True,'visible_question_nos':['1','2'],'questions':qs,'reasons':[]})
    monkeypatch.setattr(ai_client,'_post',post)
    r=ai_client.confirm_photo(TINY_JPEG,original)
    assert r['status']=='passed' and calls==['review91','reviewugq']


def test_unanswered_transcription_is_not_graded_or_cleared(client, auth, monkeypatch):
    _pipeline(monkeypatch)
    out = client.post('/api/v1/wrongbook/photo/recognize', json={'image':TINY_JPEG}, headers=auth).json()['result']
    item = out['save_results'][0]
    r = client.post('/api/v1/wrongbook/'+item['topic_id']+'/redo',
                    json={'fill_answers':{item['id']:'随意作答'}},headers=auth)
    assert r.status_code == 400
    with db.ro() as conn:
        row = conn.execute('SELECT status,wrong_count,review_status FROM wrong_questions WHERE id=?', (item['id'],)).fetchone()
    assert tuple(row) == ('open', 1, 'needs_review')


def test_active_job_rejects_competing_retry(client, auth, monkeypatch):
    import time
    _pipeline(monkeypatch, 'pending')
    out = client.post('/api/v1/wrongbook/photo/recognize',json={'image':TINY_JPEG},headers=auth).json()['result']
    with db.tx() as conn:
        conn.execute('UPDATE photo_jobs SET lease=?,lease_until=? WHERE id=?',('other-worker',time.time()+300,out['job_id']))
    r=client.post('/api/v1/wrongbook/photo/retry/'+out['job_id'],json={},headers=auth)
    assert r.status_code==409


def test_explicit_photo_sharing_preserves_owner_and_readonly(client, auth, monkeypatch):
    _pipeline(monkeypatch)
    uid = _uid(client, auth)
    body = {'image': TINY_JPEG, 'subject': 'math', 'chapter': 'functions',
            'skill': '值域', 'shared_readonly': True}
    out = client.post('/api/v1/wrongbook/photo/recognize', json=body, headers=auth).json()['result']
    assert out['state'] == 'saved'
    other = {'Authorization': 'Bearer '+client.post('/api/v1/session').json()['token']}
    shared = client.get('/api/v1/wrongbook', headers=other).json()
    assert len(shared['items']) == 2
    for item in shared['items']:
        assert item['owner_id'] == uid and item['can_edit'] is False
        assert (item['subject'], item['chapter'], item['skill']) == ('math', 'functions', '值域')
    item = shared['items'][0]
    assert client.get(out['image_path'], headers=other).status_code == 200
    assert client.get(out['image_path']).status_code == 401
    assert client.get('/api/v1/wrongbook/photo/jobs', headers=other).json()['jobs'] == []
    denied = client.post('/api/v1/wrongbook/'+item['topic_id']+'/redo',
                         json={'fill_answers': {item['id']: '1'}}, headers=other)
    assert denied.status_code == 400 and '只读' in denied.json()['detail']
    assert client.post('/api/v1/wrongbook/ai/solve', json={'ids': [item['id']]}, headers=other).json()['results'][0]['error'] == '错题不存在'
    assert client.post('/api/v1/wrongbook/photo/retry/'+out['job_id'], headers=other).status_code == 404
    db.init_db()
    with db.ro() as conn:
        assert {r['user_id'] for r in conn.execute('SELECT user_id FROM wrong_questions')} == {uid}
    again = client.post('/api/v1/wrongbook/photo/recognize', json=body, headers=auth).json()['result']
    assert again['job_id'] == out['job_id']
    assert len(client.get('/api/v1/wrongbook', headers=other).json()['items']) == 2


def test_pending_photo_keeps_classification_on_retry(client, auth, monkeypatch):
    _pipeline(monkeypatch, 'pending')
    body = {'image': TINY_JPEG, 'subject': 'math', 'chapter': 'functions',
            'skill': '值域', 'shared_readonly': True}
    out = client.post('/api/v1/wrongbook/photo/recognize', json=body, headers=auth).json()['result']
    assert out['state'] == 'pending' and out['metadata']['chapter'] == 'functions'
    with db.ro() as conn:
        row = conn.execute('SELECT * FROM photo_jobs WHERE id=?', (out['job_id'],)).fetchone()
        assert row['original_json'] and row['image_b64'] and row['user_id'] == _uid(client, auth)
    _pipeline(monkeypatch)
    out = client.post('/api/v1/wrongbook/photo/retry/'+out['job_id'], headers=auth).json()['result']
    assert out['state'] == 'saved' and out['metadata']['shared_readonly'] is True
    assert all(q['chapter'] == 'functions' for q in client.get('/api/v1/wrongbook', headers=auth).json()['items'])


@pytest.mark.parametrize('finish', ['length','content_filter',None])
def test_vision_rejects_non_stop_even_valid_json(monkeypatch, finish):
    import httpx
    from app.services import ai_client
    class Fake:
        def __init__(self, **kw): pass
        def __enter__(self): return self
        def __exit__(self,*args): pass
        def post(self,*args,**kwargs):
            return httpx.Response(200,json={'choices':[{'finish_reason':finish,'message':{'content':'{"status":"passed"}'}}]})
    monkeypatch.setattr(httpx,'Client',Fake)
    with pytest.raises(RuntimeError,match='截断'):
        ai_client._post({'base_url':'https://test.invalid','key':'test','name':'test'},'gpt-6.1-sol',[{'role':'user','content':[{'type':'image_url'}]}],True,10)
