"""管理员接口 + 多路 AI 通道：守卫、配置读写、任务路由、solve/variants 缓存与限额。"""
import json

import pytest
from starlette.testclient import TestClient

from app import content_loader, db
from app.main import app


@pytest.fixture()
def client(tmp_path, monkeypatch):
    dbfile = tmp_path / "test.db"
    monkeypatch.setattr(db, "DB_PATH", dbfile)
    content_loader.clear_cache()
    from app.services import ratelimit
    ratelimit.reset()
    with TestClient(app) as c:
        yield c


def _make_account(client, username, password, nickname, role=None):
    """测试用：直接在库里建一个带密码的账号（可指定角色）。"""
    from app import auth as _auth
    with db.tx() as conn:
        uid = _auth.new_id()
        conn.execute(
            "INSERT INTO users(id, token_hash, sync_code, nickname, username, "
            "password_hash, role, created_at, last_seen) VALUES (?,?,?,?,?,?,?,?,?)",
            (uid, _auth.hash_token(_auth.new_token()),
             _auth.normalize_sync_code(_auth.new_sync_code()),
             nickname, username, _auth.hash_password(password), role,
             "2026-01-01T00:00:00", "2026-01-01T00:00:00"),
        )
    return uid


def _login(client, username, password):
    r = client.post("/api/v1/session/login", json={"username": username, "password": password})
    assert r.status_code == 200
    return {"Authorization": f"Bearer {r.json()['token']}"}


@pytest.fixture()
def admin_headers(client):
    _make_account(client, "dad", "123456", "爸爸", role="admin")
    return _login(client, "dad", "123456")


@pytest.fixture()
def user_headers(client):
    _make_account(client, "sunny", "123456", "小阳")
    return _login(client, "sunny", "123456")


def _stub_ai(monkeypatch):
    """AI 客户端切 stub：视为已配置 + STUB 模式（不发起真实请求）。"""
    from app.services import ai_client
    monkeypatch.setattr(ai_client, "CHANNELS",
                        {cid: {**ch, "key": "test-key"}
                         for cid, ch in ai_client.CHANNELS.items()})
    monkeypatch.setattr(ai_client, "enabled", lambda: True)
    monkeypatch.setenv("LEARN_AI_STUB", "1")


def _fail_one_section(client, headers, topic_id="physics-induction", section="quick"):
    """故意答错一题，制造一条错题记录。"""
    data = content_loader.topic(topic_id)
    sec = next(s for s in data["sections"] if s["id"] == section)
    qs = sec["questions"]
    answers = {q["id"]: q["answer"] for q in qs}
    first = qs[0]["id"]
    answers[first] = (qs[0]["answer"] + 1) % len(qs[0]["options"])
    r = client.post(f"/api/v1/topics/{topic_id}/sections/{section}/submit",
                    json={"answers": answers}, headers=headers)
    assert r.status_code == 200
    return r.json()


# ---------- 守卫 ----------

def test_admin_requires_token(client):
    assert client.get("/api/v1/admin/ai/config").status_code == 401


def test_admin_rejects_normal_user(client, user_headers):
    r = client.get("/api/v1/admin/ai/config", headers=user_headers)
    assert r.status_code == 403


def test_admin_rejects_guest(client):
    r = client.post("/api/v1/session/guest")
    assert r.status_code == 200
    headers = {"Authorization": f"Bearer {r.json()['token']}"}
    assert client.get("/api/v1/admin/ai/config", headers=headers).status_code == 403


def test_me_payload_is_admin(client, admin_headers, user_headers):
    me_admin = client.get("/api/v1/me", headers=admin_headers).json()
    me_user = client.get("/api/v1/me", headers=user_headers).json()
    assert me_admin["is_admin"] is True
    assert me_user["is_admin"] is False


# ---------- 配置读写 ----------

def test_admin_config_defaults(client, admin_headers):
    r = client.get("/api/v1/admin/ai/config", headers=admin_headers)
    assert r.status_code == 200
    d = r.json()
    assert set(d["channels"].keys()) == {"glm", "deepseek", "gpt", "review91", "reviewugq"}
    assert set(d["routing"].keys()) == {"analyze", "solve", "variants", "recognize", "review", "photo_confirm"}
    assert d["routing"]["analyze"] == "glm"
    assert d["routing"]["solve"] == "deepseek"
    assert d["routing"]["recognize"] == "glm"
    # 管理视角有 key 状态，但永不回传密钥本体
    for cid, ch in d["channels"].items():
        assert "key_ok" in ch and "key" not in ch and "api_key" not in ch


def test_admin_config_roundtrip(client, admin_headers):
    r = client.put("/api/v1/admin/ai/config",
                   json={"routing": {"analyze": "gpt"},
                         "limits": {"solve": 3},
                         "channels": {"glm": {"enabled": False}}},
                   headers=admin_headers)
    assert r.status_code == 200
    d = r.json()
    assert d["routing"]["analyze"] == "gpt"
    assert d["limits"]["solve"] == 3
    assert d["channels"]["glm"]["enabled"] is False
    assert d["updated_by"] and d["updated_at"]

    # 重开一次仍持久（走库）
    r2 = client.get("/api/v1/admin/ai/config", headers=admin_headers)
    assert r2.json()["routing"]["analyze"] == "gpt"


def test_admin_config_validation(client, admin_headers):
    r = client.put("/api/v1/admin/ai/config",
                   json={"routing": {"analyze": "nope"}}, headers=admin_headers)
    assert r.status_code == 400
    r = client.put("/api/v1/admin/ai/config",
                   json={"limits": {"bad_task": 5}}, headers=admin_headers)
    assert r.status_code == 400
    r = client.put("/api/v1/admin/ai/config",
                   json={"limits": {"solve": 0}}, headers=admin_headers)
    assert r.status_code == 400
    r = client.put("/api/v1/admin/ai/config", json={}, headers=admin_headers)
    assert r.status_code == 400, "空 patch 视为误操作"


def test_admin_reset(client, admin_headers):
    client.put("/api/v1/admin/ai/config",
               json={"routing": {"solve": "gpt"}}, headers=admin_headers)
    r = client.post("/api/v1/admin/ai/reset", headers=admin_headers)
    assert r.status_code == 200
    assert r.json()["routing"]["solve"] == "deepseek"


def test_admin_users_list(client, admin_headers):
    r = client.get("/api/v1/admin/users", headers=admin_headers)
    assert r.status_code == 200
    users = r.json()["users"]
    assert any(u["username"] == "dad" and u["is_admin"] for u in users)


# ---------- 连通性测试与用量 ----------

def test_admin_ai_test_stub(client, admin_headers, monkeypatch):
    _stub_ai(monkeypatch)
    r = client.post("/api/v1/admin/ai/test", json={"task": "analyze"},
                    headers=admin_headers)
    assert r.status_code == 200
    d = r.json()
    assert d["ok"] is True and d["channel"] == "stub"
    r = client.post("/api/v1/admin/ai/test", json={"task": "nope"},
                    headers=admin_headers)
    assert r.status_code == 400


def test_admin_usage_after_analyze(client, admin_headers, monkeypatch):
    _stub_ai(monkeypatch)
    from app.services import ai_client
    monkeypatch.setattr(ai_client, "analyze", ai_client.analyze_stub)

    _fail_one_section(client, admin_headers)
    wb = client.get("/api/v1/wrongbook", headers=admin_headers).json()
    wq_id = wb["items"][0]["id"]
    r = client.post("/api/v1/wrongbook/ai", json={"ids": [wq_id]}, headers=admin_headers)
    assert r.status_code == 200

    u = client.get("/api/v1/admin/ai/usage?days=1", headers=admin_headers).json()
    assert u["total"] >= 1
    assert any(row["task"] == "analyze" and row["channel"] == "stub"
               for row in u["rows"])


# ---------- 任务路由真正生效 ----------

def test_routing_uses_configured_channel(client, admin_headers, monkeypatch):
    """把错因分析路由到 gpt 通道后，真实调用应带上 gpt 通道标记。"""
    _stub_ai(monkeypatch)
    monkeypatch.delenv("LEARN_AI_STUB", raising=False)  # 真实调用路径（不短路到 stub）
    from app.services import ai_client

    captured = {}

    def fake_chat(task, system, user_msg, *, conn=None, **kw):
        from app.services import ai_config
        cfg = ai_client._load_cfg(conn)
        cands = ai_client.candidates(task, cfg)
        captured["primary"] = cands[0][0]["id"]
        return {"text": json.dumps({"analysis": "test analysis", "suggestions": ["review the units"]}), "channel": cands[0][0]["id"],
                "model": cands[0][1]}

    monkeypatch.setattr(ai_client, "chat", fake_chat)
    client.put("/api/v1/admin/ai/config",
               json={"routing": {"analyze": "gpt"}}, headers=admin_headers)

    _fail_one_section(client, admin_headers)
    wb = client.get("/api/v1/wrongbook", headers=admin_headers).json()
    wq_id = wb["items"][0]["id"]
    r = client.post("/api/v1/wrongbook/ai", json={"ids": [wq_id]}, headers=admin_headers)
    assert r.status_code == 200
    assert captured["primary"] == "gpt"


def test_fallback_skips_disabled_channel(client, admin_headers, monkeypatch):
    _stub_ai(monkeypatch)
    """主通道被停用时，路由候选应跳过它落到下一个可用通道。"""
    from app.services import ai_client, ai_config

    client.put("/api/v1/admin/ai/config",
               json={"channels": {"glm": {"enabled": False}}}, headers=admin_headers)
    with db.ro() as conn:
        cfg = ai_config.load(conn)
    cands = ai_client.candidates("analyze", cfg)
    assert cands[0][0]["id"] == "deepseek", "glm 停用后 analyze 主候选应落到 deepseek"


# ---------- AI 解题 / 举一反三 ----------

def test_solve_with_stub_and_cache(client, admin_headers, monkeypatch):
    _stub_ai(monkeypatch)
    _fail_one_section(client, admin_headers)
    wb = client.get("/api/v1/wrongbook", headers=admin_headers).json()
    wq_id = wb["items"][0]["id"]

    r = client.post("/api/v1/wrongbook/ai/solve", json={"ids": [wq_id]},
                    headers=admin_headers)
    assert r.status_code == 200
    v = r.json()["results"][0]["value"]
    assert v["stub"] is True
    assert "steps" in v and "answer_letter" in v

    # 缓存出现在错题本列表里
    wb2 = client.get("/api/v1/wrongbook", headers=admin_headers).json()
    assert wb2["items"][0]["ai_solve"]["answer_letter"] == v["answer_letter"]

    # 二次请求命中缓存
    r2 = client.post("/api/v1/wrongbook/ai/solve", json={"ids": [wq_id]},
                     headers=admin_headers)
    assert r2.json()["results"][0]["cached"] is True


def test_variants_with_stub_and_cache(client, admin_headers, monkeypatch):
    _stub_ai(monkeypatch)
    _fail_one_section(client, admin_headers)
    wb = client.get("/api/v1/wrongbook", headers=admin_headers).json()
    wq_id = wb["items"][0]["id"]

    r = client.post("/api/v1/wrongbook/ai/variants", json={"id": wq_id, "n": 2},
                    headers=admin_headers)
    assert r.status_code == 200
    result = r.json()["result"]
    assert len(result["variants"]) == 2
    v0 = result["variants"][0]
    assert v0["stem"] and len(v0["options"]) >= 2 and 0 <= v0["answer"] < len(v0["options"])

    r2 = client.post("/api/v1/wrongbook/ai/variants", json={"id": wq_id, "n": 3},
                     headers=admin_headers)
    assert r2.json()["result"]["cached"] is True, "变式整组缓存，n 参数不再影响结果"


def test_solve_disabled_returns_503(client, admin_headers, monkeypatch):
    from app.services import ai_client
    monkeypatch.setattr(ai_client, "CHANNELS",
                        {cid: {**ch, "key": ""} for cid, ch in ai_client.CHANNELS.items()})
    monkeypatch.delenv("LEARN_AI_STUB", raising=False)
    _fail_one_section(client, admin_headers)
    wb = client.get("/api/v1/wrongbook", headers=admin_headers).json()
    wq_id = wb["items"][0]["id"]
    r = client.post("/api/v1/wrongbook/ai/solve", json={"ids": [wq_id]},
                    headers=admin_headers)
    assert r.status_code == 503


def test_per_task_limit_429(client, admin_headers, monkeypatch):
    _stub_ai(monkeypatch)
    client.put("/api/v1/admin/ai/config",
               json={"limits": {"solve": 1}}, headers=admin_headers)
    _fail_one_section(client, admin_headers)
    wb = client.get("/api/v1/wrongbook", headers=admin_headers).json()
    wq_id = wb["items"][0]["id"]

    r = client.post("/api/v1/wrongbook/ai/solve", json={"ids": [wq_id]},
                    headers=admin_headers)
    assert r.status_code == 200
    r2 = client.post("/api/v1/wrongbook/ai/solve", json={"ids": ["wq_other"]},
                     headers=admin_headers)
    assert r2.status_code == 200 and "error" in r2.json()["results"][0]
    # Missing IDs do not consume quota, and cached results remain readable at the limit.
    r3 = client.post("/api/v1/wrongbook/ai/solve", json={"ids": [wq_id]}, headers=admin_headers)
    assert r3.json()["results"][0]["cached"] is True
    _fail_one_section(client, admin_headers, topic_id="physics-newton")
    other = next(it["id"] for it in client.get("/api/v1/wrongbook", headers=admin_headers).json()["items"] if it["id"] != wq_id)
    assert client.post("/api/v1/wrongbook/ai/solve", json={"ids": [other]}, headers=admin_headers).status_code == 429


def test_config_patch_preserves_routing_and_disabled_channels(client, admin_headers):
    client.put("/api/v1/admin/ai/config", json={"routing": {"solve": "gpt"},
               "channels": {"glm": {"enabled": False, "model": "custom-model"}}}, headers=admin_headers)
    result = client.put("/api/v1/admin/ai/config", json={"limits": {"analyze": 2}}, headers=admin_headers)
    assert result.status_code == 200
    cfg = result.json()
    assert cfg["routing"]["solve"] == "gpt"
    assert cfg["channels"]["glm"]["enabled"] is False
    assert cfg["channels"]["glm"]["model"] == "custom-model"
    assert client.put("/api/v1/admin/ai/config", json={"limits": {"solve": True}}, headers=admin_headers).status_code == 422
    assert client.put("/api/v1/admin/ai/config", json={"channels": {"glm": {"enabled": "false"}}}, headers=admin_headers).status_code == 400


def test_corrupt_config_uses_defaults(client):
    from app.services import ai_config
    with db.tx() as conn:
        conn.execute("INSERT INTO ai_config(id,config) VALUES(1,?)",
                     (json.dumps({"routing": [], "limits": "bad", "channels": {"glm": []}}),))
        assert ai_config.load(conn)["routing"] == ai_config.DEFAULT_ROUTING


def test_ai_call_releases_write_lock_and_blocks_duplicate(client, admin_headers, monkeypatch):
    from concurrent.futures import ThreadPoolExecutor
    from threading import Event
    from app.services import ai_client
    _stub_ai(monkeypatch)
    _fail_one_section(client, admin_headers)
    item = client.get("/api/v1/wrongbook", headers=admin_headers).json()["items"][0]
    started, release = Event(), Event()
    def slow_solve(q):
        started.set()
        assert release.wait(10)
        return ai_client.solve_stub(q)
    monkeypatch.setattr(ai_client, "solve", slow_solve)
    with ThreadPoolExecutor(max_workers=1) as pool:
        pending = pool.submit(client.post, "/api/v1/wrongbook/ai/solve", json={"ids": [item["id"]]}, headers=admin_headers)
        try:
            assert started.wait(10)
            # The AI HTTP request is active; another writer must still acquire SQLite immediately.
            import sqlite3
            with sqlite3.connect(db.DB_PATH, timeout=.2) as conn:
                conn.execute("BEGIN IMMEDIATE")
                conn.execute("UPDATE users SET nickname=nickname")
            duplicate = client.post("/api/v1/wrongbook/ai/solve", json={"ids": [item["id"]]}, headers=admin_headers)
            assert "正在生成" in duplicate.json()["results"][0]["error"]
        finally:
            release.set()
        assert pending.result().json()["results"][0]["cached"] is False
    with db.ro() as conn:
        assert conn.execute("SELECT count(*) FROM ai_requests").fetchone()[0] == 0
        assert conn.execute("SELECT count(*) FROM events WHERE kind='ai'").fetchone()[0] == 1


def test_failed_ai_releases_quota_and_changed_pick_invalidates_cache(client, admin_headers, monkeypatch):
    from app.services import ai_client
    _stub_ai(monkeypatch)
    _fail_one_section(client, admin_headers)
    item = client.get("/api/v1/wrongbook", headers=admin_headers).json()["items"][0]
    def fail(*a, **k): raise RuntimeError("network unavailable")
    monkeypatch.setattr(ai_client, "analyze", fail)
    result = client.post("/api/v1/wrongbook/ai", json={"ids": [item["id"]]}, headers=admin_headers)
    assert "error" in result.json()["results"][0]
    assert result.json()["ai_used_today"] == 0
    with db.ro() as conn:
        assert conn.execute("SELECT count(*) FROM ai_requests").fetchone()[0] == 0
    monkeypatch.setattr(ai_client, "analyze", ai_client.analyze_stub)
    client.post("/api/v1/wrongbook/ai", json={"ids": [item["id"]]}, headers=admin_headers)
    new_pick = next(i for i in range(len(item["options"])) if i not in (item["picked"], item["answer"]))
    client.post(f"/api/v1/wrongbook/{item['topic_id']}/redo", json={"answers": {item["id"]: new_pick}}, headers=admin_headers)
    fresh = client.get("/api/v1/wrongbook", headers=admin_headers).json()["items"][0]
    assert fresh["picked"] == new_pick and fresh["ai"] is None


def test_analysis_does_not_publish_for_superseded_pick(client, admin_headers, monkeypatch):
    from app.services import ai_client
    _stub_ai(monkeypatch)
    _fail_one_section(client, admin_headers)
    item = client.get("/api/v1/wrongbook", headers=admin_headers).json()["items"][0]
    def change_while_analyzing(q, picked):
        with db.tx() as conn:
            conn.execute("UPDATE wrong_questions SET picked=? WHERE id=?", ((picked+1)%len(q["options"]), item["id"]))
        return ai_client.analyze_stub(q, picked)
    monkeypatch.setattr(ai_client, "analyze", change_while_analyzing)
    result = client.post("/api/v1/wrongbook/ai", json={"ids": [item["id"]]}, headers=admin_headers)
    assert "已更新" in result.json()["results"][0]["error"]
    assert client.get("/api/v1/wrongbook", headers=admin_headers).json()["items"][0]["ai"] is None


def test_ai_requests_do_not_leak_other_users_questions(client, admin_headers, user_headers, monkeypatch):
    _stub_ai(monkeypatch)
    _fail_one_section(client, admin_headers)
    item = client.get("/api/v1/wrongbook", headers=admin_headers).json()["items"][0]
    for path in ["ai", "ai/solve"]:
        result = client.post(f"/api/v1/wrongbook/{path}", json={"ids": [item["id"]]}, headers=user_headers)
        assert result.json()["results"][0] == {"id": item["id"], "error": "错题不存在"}
        assert result.json()["ai_used_today"] == 0
    assert client.post("/api/v1/wrongbook/ai/variants", json={"id": item["id"]}, headers=user_headers).status_code == 404


def test_skipped_question_does_not_drop_later_wrong_answers(client, admin_headers):
    topic_id = "physics-induction"
    section = next(s for s in content_loader.topic(topic_id)["sections"] if s["id"] == "quick")
    first, second = section["questions"][:2]
    # Leave the first question unanswered; answer the second incorrectly.
    result = client.post(f"/api/v1/topics/{topic_id}/sections/quick/submit",
                         json={"answers": {second["id"]: (second["answer"]+1)%len(second["options"])}},
                         headers=admin_headers)
    assert result.status_code == 200
    items = client.get("/api/v1/wrongbook", headers=admin_headers).json()["items"]
    assert len(items) == 1 and items[0]["stem"] == second["stem"]


def test_concurrent_different_questions_cannot_exceed_daily_quota(client, admin_headers, monkeypatch):
    from concurrent.futures import ThreadPoolExecutor
    from threading import Event
    from app.services import ai_client
    _stub_ai(monkeypatch)
    client.put("/api/v1/admin/ai/config", json={"limits": {"solve": 1}}, headers=admin_headers)
    _fail_one_section(client, admin_headers)
    _fail_one_section(client, admin_headers, topic_id="physics-newton")
    items = client.get("/api/v1/wrongbook", headers=admin_headers).json()["items"]
    started, release = Event(), Event()
    def slow(q):
        started.set()
        assert release.wait(10)
        return ai_client.solve_stub(q)
    monkeypatch.setattr(ai_client, "solve", slow)
    with ThreadPoolExecutor(max_workers=1) as pool:
        pending = pool.submit(client.post, "/api/v1/wrongbook/ai/solve", json={"ids": [items[0]["id"]]}, headers=admin_headers)
        try:
            assert started.wait(10)
            blocked = client.post("/api/v1/wrongbook/ai/solve", json={"ids": [items[1]["id"]]}, headers=admin_headers)
            assert blocked.status_code == 429
        finally:
            release.set()
        assert pending.result().status_code == 200
