"""本地工具与服务器强审核闭环，外部GPT调用用严格结构桩替代。"""
import base64
import copy
import json

import pytest
from starlette.testclient import TestClient

from app import db
from app.main import app
from app.routers import wrongbook as router
from app.services import ai_client, ratelimit, wrongbook, wrongbook_review as review

IMAGE = base64.b64encode(b"\x89PNG\r\n\x1a\n" + b"x" * 80).decode()


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setattr(db, "DB_PATH", tmp_path / "test.db")
    monkeypatch.setattr(router, "_IMAGES_DIR", tmp_path / "images")
    monkeypatch.setattr(router, "_WEB_PREFIX", "/wb-images")
    monkeypatch.setenv("LEARN_WB_IMAGES", str(tmp_path / "images"))
    monkeypatch.delenv("LEARN_AI_STUB", raising=False)
    monkeypatch.setattr(review, "review_channels", lambda: [{"id": "review91", "key": "test", "name": "测试"}])
    ratelimit.reset()
    with TestClient(app) as c:
        yield c


@pytest.fixture
def context(client):
    auth = {"Authorization": "Bearer " + client.post("/api/v1/session").json()["token"]}
    path = client.post("/api/v1/wrongbook/import/image", headers=auth, json={"image": IMAGE}).json()["path"]
    item = review.canonical({"stem": "选择所有等于2的式子", "qtype": "multi_choice", "options": ["1+1", "3-1", "2+1"],
                             "answer_indices": [0, 1], "answer": -1, "explain": "逐项计算", "derivation": "1+1=2，3-1=2，2+1=3",
                             "image_path": path, "question_no": "1"})
    return auth, item


def result(item, status="passed"):
    return {"status": status, "complete": True, "question_no": item["question_no"],
            "checks": {k: True for k in review.CHECKS}, "reasons": [] if status == "passed" else ["解析需修订"],
            "evidence": "原图第1题完整，3选项及公式和裁图逐项一致", "independent_solution": "逐项计算得AB",
            "answer_source": "AI", "item": copy.deepcopy(item)}


def stub(monkeypatch, output):
    def post(channel, model, messages, *args):
        if "仅以下题目" in messages[1]["content"][-1]["text"]:
            return json.dumps({"certain": True, "answer": -1, "answer_indices": [0, 1], "answer_text": "", "derivation": "逐项计算得AB"})
        return json.dumps(output)
    monkeypatch.setattr(ai_client, "_post", post)


def audit(client, auth, item, **extra):
    return client.post("/api/v1/wrongbook/import/review", headers=auth,
                       json={"item": item, "source_image": IMAGE, "crop_image": IMAGE, **extra})


def test_bypass_and_forged_passed_are_blocked(client, context):
    auth, item = context
    for fields in ({}, {"review_id": "forged", "approved": True, "status": "passed"}):
        response = client.post("/api/v1/wrongbook/import", headers=auth, json={"items": [{**item, **fields}]})
        assert response.status_code == 409
    with db.tx() as conn, pytest.raises(ValueError, match="真实GPT"):
        wrongbook.import_items(conn, "u_family", [item])


def test_passed_multi_import_is_idempotent_and_cache_reused(client, context, monkeypatch):
    auth, item = context
    stub(monkeypatch, result(item))
    response = audit(client, auth, item)
    assert response.status_code == 200, response.text
    item["review_id"] = response.json()["review_id"]
    assert audit(client, auth, item).json()["cached"] is True
    first = client.post("/api/v1/wrongbook/import", headers=auth, json={"items": [item]}).json()
    assert len(first["imported"]) == 1
    second = client.post("/api/v1/wrongbook/import", headers=auth, json={"items": [item]}).json()
    assert len(second["skipped"]) == 1
    with db.ro() as conn:
        row = conn.execute("SELECT * FROM wrong_questions WHERE id=?", (first["imported"][0]["id"],)).fetchone()
        assert row["qtype"] == "multi_choice"
        assert json.loads(row["answer_indices_json"]) == [0, 1]
        assert row["answer"] == -1
        assert row["wrong_count"] == 1


@pytest.mark.parametrize("key,value", [("stem", "修改题干"), ("answer_indices", [0]), ("explain", "修改解析"),
                                      ("derivation", "修改推导"), ("subject", "math"), ("chapter", "trigonometry"),
                                      ("image_path", "/wb-images/other/image.png"), ("bbox", [0, 0, 1, 1])])
def test_critical_field_edit_invalidates_receipt(client, context, monkeypatch, key, value):
    auth, item = context
    stub(monkeypatch, result(item))
    item["review_id"] = audit(client, auth, item).json()["review_id"]
    item[key] = value
    assert client.post("/api/v1/wrongbook/import", headers=auth, json={"items": [item]}).status_code == 409


def test_same_image_path_changed_bytes_invalidates_receipt(client, context, monkeypatch):
    auth, item = context
    stub(monkeypatch, result(item))
    item["review_id"] = audit(client, auth, item).json()["review_id"]
    owner, name = item["image_path"].split("/")[-2:]
    (router._IMAGES_DIR / owner / name).write_bytes(b"changed")
    assert client.post("/api/v1/wrongbook/import", headers=auth, json={"items": [item]}).status_code == 409


@pytest.mark.parametrize("damage", ["missing-check", "incomplete", "changed-passed", "missing-options", "missing-answer", "missing-proof", "bad-json", "timeout", "uncertain-solve"])
def test_fail_closed_on_bad_or_incomplete_gpt(client, context, monkeypatch, damage):
    auth, item = context
    if damage == "missing-options": item["options"] = []
    if damage == "missing-answer": item["answer_indices"] = []
    output = result(item)
    if damage == "missing-check": del output["checks"]["formulas"]
    if damage == "incomplete": output["complete"] = False
    if damage == "changed-passed": output["item"]["stem"] = "偷偷修订"
    if damage == "missing-proof": output["independent_solution"] = ""
    stub(monkeypatch, output)
    if damage == "bad-json": monkeypatch.setattr(ai_client, "_post", lambda *a: "{broken")
    if damage == "timeout":
        def fail(*a): raise RuntimeError("AI响应超时")
        monkeypatch.setattr(ai_client, "_post", fail)
    if damage == "uncertain-solve":
        monkeypatch.setattr(ai_client, "_post", lambda *a: json.dumps({"certain": False, "answer": -1, "answer_indices": [], "answer_text": "", "derivation": "无法解题"}) if "仅以下题目" in a[2][1]["content"][-1]["text"] else json.dumps(output))
    response = audit(client, auth, item)
    assert response.status_code == 503, response.text
    assert client.post("/api/v1/wrongbook/import", headers=auth, json={"items": [item]}).status_code == 409


def test_missing_images_cannot_review(client, context):
    auth, item = context
    assert client.post("/api/v1/wrongbook/import/review", headers=auth, json={"item": item}).status_code == 422
    assert audit(client, auth, {**item, "image_path": ""}).status_code == 400


def test_revision_requires_human_confirmation_and_final_gpt(client, context, monkeypatch):
    auth, item = context
    output = result(item, "revised")
    output["item"]["explain"] = "AI修订：逐项计算得AB"
    stub(monkeypatch, output)
    response = audit(client, auth, item).json()
    parent = response["review_id"]
    proposed = output["item"]
    assert client.post("/api/v1/wrongbook/import", headers=auth, json={"items": [{**proposed, "review_id": parent}]}).status_code == 409
    assert audit(client, auth, proposed).status_code == 409
    assert audit(client, auth, proposed, parent_review_id=parent).status_code == 409
    stub(monkeypatch, result(proposed))
    response = audit(client, auth, proposed, parent_review_id=parent, confirm_revision=True)
    assert response.status_code == 200, response.text
    assert response.json()["review"]["status"] == "passed"
    proposed["review_id"] = response.json()["review_id"]
    assert client.post("/api/v1/wrongbook/import", headers=auth, json={"items": [proposed]}).status_code == 200


def test_old_photo_manual_save_is_pending_not_ready(client, context):
    auth, item = context
    response = client.post("/api/v1/wrongbook/photo/save", headers=auth,
                           json={"stem": "人工未审核题", "qtype": "fill", "answer_text": "2"})
    assert response.status_code == 200
    with db.ro() as conn:
        row = conn.execute("SELECT review_status FROM wrong_questions WHERE id=?", (response.json()["id"],)).fetchone()
        assert row[0] == "needs_review"


def test_local_import_endpoint_does_not_proxy_unreviewed_items(monkeypatch):
    from tools.wrongbook_tool import server
    monkeypatch.setattr(server, "load_config", lambda: {})
    with TestClient(server.app) as c:
        assert c.post("/api/import", json={"items": [{"stem": "未审核"}]}).status_code == 409
        assert c.get("/api/state").json()["review_version"] == review.VERSION
