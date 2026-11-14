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
    assert len(d["options"]) >= 2
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
    assert row["user_id"] == uid
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
    assert photo["open"] == 1
    assert wb["items"][0]["source"] == "photo"


def test_photo_save_misc_subject_fallback(client, auth):
    r = client.post("/api/v1/wrongbook/photo/save", json={
        "stem": "无法判断学科的题目内容", "options": ["甲", "乙"], "picked": 0,
        "answer": 1, "subject": "biology",
    }, headers=auth)
    assert r.json()["topic_id"] == "photo-misc"
    wb = client.get("/api/v1/wrongbook", headers=auth).json()
    t = next(x for x in wb["summary"]["topics"] if x["topic_id"] == "photo-misc")
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


def test_photo_saved_question_can_be_redone(client, auth):
    """拍照题进错题本后，走正常重做流程可以清零。"""
    d = client.post("/api/v1/wrongbook/photo/save", json={
        "stem": "拍照录入的重做题", "options": ["甲", "乙", "丙"], "picked": 0,
        "answer": 2, "subject": "math",
    }, headers=auth).json()

    r = client.post("/api/v1/wrongbook/photo-math/redo",
                    json={"answers": {d["id"]: 2}}, headers=auth)
    assert r.status_code == 200
    assert r.json()["cleared"] == 1
    assert r.json()["remaining"] == 0


def test_photo_endpoints_require_auth(client):
    for path, body in (
        ("/wrongbook/photo/recognize", {"image": TINY_JPEG}),
        ("/wrongbook/photo/analyze", {"stem": "x", "options": ["a"], "picked": 0}),
        ("/wrongbook/photo/save", {"stem": "x", "options": ["a", "b"], "picked": 0}),
    ):
        assert client.post(path and f"/api/v1{path}", json=body).status_code == 401
