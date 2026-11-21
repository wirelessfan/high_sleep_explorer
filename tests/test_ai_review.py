import json

import pytest

from app import content_loader, db
from app.main import app
from app.services import ai_client, ai_config
from starlette.testclient import TestClient


@pytest.fixture()
def client(tmp_path, monkeypatch):
    monkeypatch.setattr(db, "DB_PATH", tmp_path / "test.db")
    content_loader.clear_cache()
    with TestClient(app) as test_client:
        yield test_client


def _make_user(username, role=None):
    from app import auth
    with db.tx() as conn:
        uid = auth.new_id()
        conn.execute(
            "INSERT INTO users(id, token_hash, sync_code, nickname, username, password_hash, role, created_at, last_seen) VALUES (?,?,?,?,?,?,?,?,?)",
            (uid, auth.hash_token(auth.new_token()), auth.normalize_sync_code(auth.new_sync_code()),
             username, username, auth.hash_password("123456"), role,
             "2026-01-01T00:00:00", "2026-01-01T00:00:00"),
        )


def _headers(client, username):
    response = client.post("/api/v1/session/login", json={"username": username, "password": "123456"})
    return {"Authorization": f"Bearer {response.json()['token']}"}


@pytest.fixture()
def admin_headers(client):
    _make_user("reviewadmin", "admin")
    return _headers(client, "reviewadmin")


@pytest.fixture()
def user_headers(client):
    _make_user("reviewuser")
    return _headers(client, "reviewuser")


def test_review_config_does_not_change_legacy_routes(client, admin_headers):
    from app.services import ai_config
    with db.ro() as conn:
        cfg = ai_config.load(conn)
    assert cfg["routing"]["review"] == "review91"
    assert cfg["routing"]["analyze"] == ai_config.DEFAULT_ROUTING["analyze"]
    assert ai_client.candidates("review", cfg) == []
    monkeypatch = pytest.MonkeyPatch()
    try:
        monkeypatch.setattr(ai_client, "CHANNELS", {
            cid: {**channel, "key": "test"} for cid, channel in ai_client.CHANNELS.items()})
        legacy = [channel["id"] for channel, _ in ai_client.candidates("analyze", cfg)]
        assert legacy == ["glm", "deepseek", "gpt"]
        assert not set(legacy) & set(ai_config.REVIEW_CHANNEL_ORDER)
    finally:
        monkeypatch.undo()
    assert client.get("/api/v1/admin/ai/config", headers=admin_headers).status_code == 200


def test_review_primary_success(monkeypatch):
    monkeypatch.delenv("LEARN_AI_STUB", raising=False)
    monkeypatch.setattr(ai_client, "enabled", lambda: True)
    chs = {"review91": {"id": "review91", "key": "key", "name": "91token", "model": "gpt-6.1-sol"},
           "reviewugq": {"id": "reviewugq", "key": "key", "name": "UGQ", "model": "gpt-6.1-sol"}}
    monkeypatch.setattr(ai_client, "CHANNELS", chs)
    cfg = {"routing": {"review": "review91"}, "channels": {}, "limits": {}}
    monkeypatch.setattr(ai_client, "_load_cfg", lambda conn: cfg)
    calls = []
    payload = {"correctness": "正确", "reasoning": "2+2=4", "issues": [], "revision_suggestions": []}
    monkeypatch.setattr(ai_client, "_post", lambda ch, *args: calls.append(ch["id"]) or json.dumps(payload))
    result = ai_client.review({"stem": "2+2=?", "options": ["4", "5"], "answer": "A", "explain": "2+2=4"})
    assert result["channel"] == "review91" and calls == ["review91"]


def test_review_invalid_primary_falls_back_to_ugq(monkeypatch):
    monkeypatch.delenv("LEARN_AI_STUB", raising=False)
    monkeypatch.setattr(ai_client, "enabled", lambda: True)
    monkeypatch.setattr(ai_client, "CHANNELS", {
        "review91": {"id": "review91", "key": "key", "name": "91token", "model": "gpt-6.1-sol"},
        "reviewugq": {"id": "reviewugq", "key": "key", "name": "UGQ", "model": "gpt-6.1-sol"},
    })
    monkeypatch.setattr(ai_client, "_load_cfg", lambda conn: {
        "routing": {"review": "review91"}, "channels": {}, "limits": {}})
    calls = []
    def post(ch, *args):
        calls.append(ch["id"])
        return "{}" if ch["id"] == "review91" else json.dumps({
            "correctness": "正确", "reasoning": "计算正确", "issues": [], "revision_suggestions": []})
    monkeypatch.setattr(ai_client, "_post", post)
    result = ai_client.review({"stem": "2+2=?", "options": ["4", "5"], "answer": "A", "explain": "2+2=4"})
    assert calls == ["review91", "reviewugq"] and result["channel"] == "reviewugq"


def test_review_both_channels_fail(monkeypatch):
    monkeypatch.delenv("LEARN_AI_STUB", raising=False)
    monkeypatch.setattr(ai_client, "enabled", lambda: True)
    monkeypatch.setattr(ai_client, "CHANNELS", {
        "review91": {"id": "review91", "key": "key", "name": "91token", "model": "gpt-6.1-sol"},
        "reviewugq": {"id": "reviewugq", "key": "key", "name": "UGQ", "model": "gpt-6.1-sol"},
    })
    monkeypatch.setattr(ai_client, "_load_cfg", lambda conn: {
        "routing": {"review": "review91"}, "channels": {}, "limits": {}})
    monkeypatch.setattr(ai_client, "_post", lambda *args: "{}")
    with pytest.raises(RuntimeError):
        ai_client.review({"stem": "2+2=?", "options": ["4", "5"], "answer": "A", "explain": "2+2=4"})


def test_admin_review_guard_and_input_bounds(client, user_headers, admin_headers, monkeypatch):
    assert client.post("/api/v1/admin/ai/review", json={}, headers=user_headers).status_code == 403
    too_long = {"stem": "x" * 4001, "options": ["4", "5"], "answer": "A", "explain": "e"}
    assert client.post("/api/v1/admin/ai/review", json=too_long, headers=admin_headers).status_code == 422
    monkeypatch.setattr(ai_client, "review", lambda q: {"correctness": "正确", "channel": "review91", "model": "gpt-6.1-sol"})
    body = {"stem": "2+2=?", "options": ["4", "5"], "answer": "A", "explain": "2+2=4"}
    response = client.post("/api/v1/admin/ai/review", json=body, headers=admin_headers)
    assert response.status_code == 200 and response.json()["channel"] == "review91"
