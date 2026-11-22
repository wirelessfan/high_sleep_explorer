"""错题纠错环节：错因 + 重做 + 订正 → 自动补偿抽奖（按用户 + 错题幂等）。"""
import json

import pytest
from starlette.testclient import TestClient

from app import content_loader, db
from app.main import app


@pytest.fixture()
def client(tmp_path, monkeypatch):
    monkeypatch.setattr(db, "DB_PATH", tmp_path / "test.db")
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


def _seed(qid, *, qtype="choice", answer=2, answer_text="", options=None, review="ready"):
    """直接插一条家庭共享错题，避开判分流程。"""
    with db.tx() as conn:
        conn.execute(
            "INSERT INTO wrong_questions(id,user_id,topic_id,section_id,tier,question_id,skill,stem, "
            "options_json,answer,picked,explain,wrong_count,status,source,created_at,last_wrong_at, "
            "subject,chapter,image_path,wrong_reason,qtype,answer_text,review_status,review_reason) "
            "VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            (qid, db.SHARED_WRONG_OWNER, "physics-force", "basic", "basic", "q-" + qid,
             "受力分析", "关于斜面上物体的重力分解，正确的是：",
             json.dumps(options if options is not None else
                        ["F₁ 是斜面给物体的下滑力", "物体受 4 个力", "合力为 mgsinθ 沿斜面向下", "分力效果可能不等于 mg"],
                        ensure_ascii=False),
             answer, 1, "重力沿斜面的分力才是合力。", 2, "open", "practice",
             "2026-11-22T09:00:00", "2026-11-22T09:00:00", "physics", "力学", "",
             "", qtype, answer_text, review, ""),
        )


def _grants(uid):
    with db.ro() as conn:
        return [tuple(r) for r in conn.execute(
            "SELECT kind,amount,used,start_day,end_day FROM relax_grant WHERE user_id=? ORDER BY kind",
            (uid,)).fetchall()]


def _me(client, auth):
    r = client.get("/api/v1/me", headers=auth)
    assert r.status_code == 200, r.text
    return r.json()["id"]


def test_correct_requires_right_answer(client, auth):
    """选择题没做对不发奖，只提示再想想。"""
    _seed("wq_correct_a")
    uid = _me(client, auth)
    r = client.post("/api/v1/wrongbook/wq_correct_a/correct", headers=auth,
                    json={"reason": "概念没弄清", "note": "关键是合力只有 mgsinθ，下次先画受力图", "redo_index": 1})
    assert r.status_code == 422, r.text
    assert _grants(uid) == []


def test_correct_grants_once_and_is_idempotent(client, auth):
    """答对 → 10 普通 + 1 实体；重复提交不再发奖。"""
    _seed("wq_correct_b")
    uid = _me(client, auth)
    payload = {"reason": "公式/定理记混", "note": "分力不是多出来的力，下次先数物体真正受几个力", "redo_index": 2}

    r = client.post("/api/v1/wrongbook/wq_correct_b/correct", headers=auth, json=payload)
    assert r.status_code == 200, r.text
    data = r.json()
    assert data["already_done"] is False
    assert data["reward"]["regular"] == 10 and data["reward"]["prize"] == 1
    assert data["reward"]["days"] == 30
    assert _grants(uid) and sorted({g[0] for g in _grants(uid)}) == ["prize", "regular"]
    assert {(g[0], g[1]) for g in _grants(uid)} == {("prize", 1), ("regular", 10)}

    r2 = client.post("/api/v1/wrongbook/wq_correct_b/correct", headers=auth, json=payload)
    assert r2.status_code == 200, r2.text
    assert r2.json()["already_done"] is True
    assert r2.json()["reward"] == {"regular": 0, "prize": 0}
    assert len(_grants(uid)) == 2, "重复提交不得叠加赠送池"

    quota = client.get("/api/v1/relax/quota", headers=auth).json()
    assert quota["granted"] >= 10 and quota["prize"]["granted"] >= 1


def test_correct_validates_note_and_transcription(client, auth):
    """订正笔记太短 / 题还没文字化，都不允许发奖。"""
    _seed("wq_correct_c")
    r = client.post("/api/v1/wrongbook/wq_correct_c/correct", headers=auth,
                    json={"reason": "粗心笔误", "note": "嗯", "redo_index": 2})
    assert r.status_code == 400

    _seed("wq_correct_d", review="needs_transcription")
    r = client.post("/api/v1/wrongbook/wq_correct_d/correct", headers=auth,
                    json={"reason": "粗心笔误", "note": "先补录文字再纠错，下次记得看清条件", "redo_index": 2})
    assert r.status_code == 409


def test_correct_open_question_only_needs_note(client, auth):
    """填空/解答题没有唯一答案，写好订正笔记即可领奖。"""
    _seed("wq_correct_e", qtype="fill", answer=-1, answer_text="3 m/s²", options=[])
    uid = _me(client, auth)
    r = client.post("/api/v1/wrongbook/wq_correct_e/correct", headers=auth,
                    json={"reason": "计算或单位出错", "note": "a=F/m=6/2=3，下次先统一单位再代数", "redo_text": "3 m/s²"})
    assert r.status_code == 200, r.text
    assert r.json()["reward"]["regular"] == 10
    assert len(_grants(uid)) == 2


def test_correct_is_per_user(client, auth):
    """同一道家庭共享错题，不同账号各纠一次各发一次奖。"""
    _seed("wq_correct_f")
    uid1 = _me(client, auth)
    auth2 = {"Authorization": "Bearer " + client.post("/api/v1/session").json()["token"]}
    uid2 = _me(client, auth2)
    assert uid1 != uid2
    payload = {"reason": "思路没找到", "note": "先画受力图再分解重力，下次按这个顺序做", "redo_index": 2}
    for a in (auth, auth2):
        r = client.post("/api/v1/wrongbook/wq_correct_f/correct", headers=a, json=payload)
        assert r.status_code == 200, r.text
        assert r.json()["already_done"] is False
    assert len(_grants(uid1)) == 2 and len(_grants(uid2)) == 2
