"""核心逻辑单测：判分、积分、抽卡、幂等、答案剥离。

运行：  python -m pytest tests -q
"""

import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from fastapi.testclient import TestClient  # noqa: E402

import app.db as db  # noqa: E402
from app import content_loader  # noqa: E402
from app.main import app  # noqa: E402
from app.services import grading  # noqa: E402


@pytest.fixture()
def client(tmp_path, monkeypatch):
    """每个用例一个独立数据库。"""
    dbfile = tmp_path / "test.db"
    monkeypatch.setattr(db, "DB_PATH", dbfile)
    content_loader.clear_cache()
    with TestClient(app) as c:
        yield c


@pytest.fixture()
def auth_headers(client):
    r = client.post("/api/v1/session")
    assert r.status_code == 200
    return {"Authorization": f"Bearer {r.json()['token']}"}


# ---------- 内容 ----------

def test_catalog_has_three_subjects(client, auth_headers):
    r = client.get("/api/v1/catalog", headers=auth_headers)
    assert r.status_code == 200
    data = r.json()
    assert len(data["subjects"]) == 3
    names = {s["name"] for s in data["subjects"]}
    assert names == {"物理", "化学", "数学"}


def test_each_topic_has_six_sections(client, auth_headers):
    cat = client.get("/api/v1/catalog", headers=auth_headers).json()
    for subj in cat["subjects"]:
        for item in subj["items"]:
            r = client.get(f"/api/v1/topics/{item['id']}", headers=auth_headers)
            assert r.status_code == 200
            assert len(r.json()["sections"]) == 6


def test_section_hides_answers(client, auth_headers):
    """前端拿到的内容里不能有 answer / explain。"""
    for tid in ("physics-induction", "chemistry-equilibrium", "math-derivative"):
        for sid in ("quick", "basic", "hard", "practice", "boss"):
            r = client.get(f"/api/v1/topics/{tid}/sections/{sid}", headers=auth_headers)
            assert r.status_code == 200
            raw = r.text
            assert '"answer"' not in raw, f"{tid}/{sid} 泄露 answer"
            assert '"explain"' not in raw, f"{tid}/{sid} 泄露 explain"


def test_answer_distribution_balanced():
    """正确答案的位置要均衡，不能集中在 A。"""
    from collections import Counter

    def qs(sec):
        t = sec["type"]
        if t in ("quiz", "boss"):
            return sec["questions"]
        if t == "levels":
            return [q for lv in sec["levels"] for q in lv["questions"]]
        if t == "myths":
            return [m["check"] for m in sec["myths"]]
        if t == "steps":
            return [s for p in sec["problems"] for s in p["steps"]]
        return []

    dist = Counter()
    for path in (ROOT / "content" / "topics").glob("*.json"):
        data = json.loads(path.read_text(encoding="utf-8"))
        for sec in data["sections"]:
            for q in qs(sec):
                dist[q["answer"]] += 1

    total = sum(dist.values())
    assert total > 0
    for idx in range(4):
        share = dist.get(idx, 0) / total
        assert share < 0.40, f"选项 {idx} 占比 {share:.0%}，过于集中"


# ---------- 判分 ----------

def test_grading_all_correct():
    sec = content_loader.topic("physics-induction")["sections"][0]
    answers = {q["id"]: q["answer"] for q in sec["questions"]}
    res = grading.grade_section(sec, answers)
    assert res["score"] == 100
    assert res["correct"] == res["total"]


def test_grading_all_wrong():
    sec = content_loader.topic("physics-induction")["sections"][0]
    answers = {q["id"]: (q["answer"] + 1) % len(q["options"]) for q in sec["questions"]}
    res = grading.grade_section(sec, answers)
    assert res["score"] == 0


def test_grading_returns_explain():
    sec = content_loader.topic("physics-induction")["sections"][0]
    answers = {sec["questions"][0]["id"]: sec["questions"][0]["answer"]}
    res = grading.grade_section(sec, answers)
    assert res["details"][0]["explain"]


# ---------- 积分 ----------

def test_section_points_awarded_once(client, auth_headers):
    sec = content_loader.topic("physics-induction")["sections"][0]
    answers = {q["id"]: q["answer"] for q in sec["questions"]}

    r1 = client.post("/api/v1/topics/physics-induction/sections/quick/submit",
                     json={"answers": answers}, headers=auth_headers)
    assert r1.status_code == 200
    first_points = r1.json()["points"]
    assert first_points == 15

    # 重做：只给复习分（3），不是再给 15
    r2 = client.post("/api/v1/topics/physics-induction/sections/quick/submit",
                     json={"answers": answers}, headers=auth_headers)
    assert r2.status_code == 200
    assert r2.json()["points"] == 3
    assert r2.json()["is_review"] is True


def test_points_isolated_between_users(client):
    sec = content_loader.topic("physics-induction")["sections"][0]
    answers = {q["id"]: q["answer"] for q in sec["questions"]}

    tokens = []
    for _ in range(2):
        r = client.post("/api/v1/session")
        tokens.append({"Authorization": f"Bearer {r.json()['token']}"})

    for h in tokens:
        r = client.post("/api/v1/topics/physics-induction/sections/quick/submit",
                        json={"answers": answers}, headers=h)
        assert r.status_code == 200
        assert r.json()["points"] == 15, "第二个用户也应拿到首通分"


def test_reading_awards_five(client, auth_headers):
    r = client.post("/api/v1/topics/physics-induction/sections/summary/read",
                    json={"confirmed": True}, headers=auth_headers)
    assert r.status_code == 200
    assert r.json()["points"] == 5


def test_topic_complete_gives_tickets(client, auth_headers):
    data = content_loader.topic("physics-induction")
    for sec in data["sections"]:
        if sec["type"] == "reading":
            client.post("/api/v1/topics/physics-induction/sections/summary/read",
                        json={"confirmed": True}, headers=auth_headers)
            continue
        answers = _all_answers(sec)
        r = client.post(f"/api/v1/topics/physics-induction/sections/{sec['id']}/submit",
                        json={"answers": answers}, headers=auth_headers)
        assert r.status_code == 200

    me = client.get("/api/v1/me", headers=auth_headers).json()
    # boss_first(1) + topic_complete(2) = 3
    assert me["tickets"] == 3


# ---------- 签到 ----------

def test_checkin_idempotent(client, auth_headers):
    r1 = client.post("/api/v1/checkin", headers=auth_headers)
    assert r1.status_code == 200
    assert r1.json()["points"] == 10

    r2 = client.post("/api/v1/checkin", headers=auth_headers)
    assert r2.status_code == 200
    assert r2.json()["already"] is True

    me = client.get("/api/v1/me", headers=auth_headers).json()
    assert me["points"] == 10


# ---------- 抽卡 ----------

def _fill_tickets(client, headers, n=50):
    """测试用：直接改库发卡包。"""
    with db.tx() as conn:
        uid = conn.execute(
            "SELECT id FROM users WHERE token_hash = ?",
            (__import__("app.auth", fromlist=["x"]).hash_token(
                headers["Authorization"][7:]),),
        ).fetchone()["id"]
        conn.execute("UPDATE users SET tickets = ? WHERE id = ?", (n, uid))
    return uid


def test_draw_requires_tickets(client, auth_headers):
    r = client.post("/api/v1/cards/draw", json={"count": 1, "idempotency_key": "a"},
                    headers=auth_headers)
    assert r.status_code == 400
    assert "卡包不足" in r.json()["detail"]


def test_draw_consumes_tickets_and_returns_card(client, auth_headers):
    _fill_tickets(client, auth_headers, 10)
    r = client.post("/api/v1/cards/draw", json={"count": 1, "idempotency_key": "k1"},
                    headers=auth_headers)
    assert r.status_code == 200
    data = r.json()
    assert len(data["results"]) == 1
    assert data["cost"] == 1
    assert data["tickets_left"] == 9
    assert data["results"][0]["card_id"]


def test_draw_ten_costs_nine(client, auth_headers):
    _fill_tickets(client, auth_headers, 20)
    r = client.post("/api/v1/cards/draw", json={"count": 10, "idempotency_key": "k10"},
                    headers=auth_headers)
    assert r.status_code == 200
    data = r.json()
    assert len(data["results"]) == 10
    assert data["cost"] == 9
    assert data["tickets_left"] == 11


def test_draw_idempotent(client, auth_headers):
    _fill_tickets(client, auth_headers, 10)
    r1 = client.post("/api/v1/cards/draw", json={"count": 1, "idempotency_key": "same"},
                     headers=auth_headers)
    assert r1.status_code == 200
    left1 = r1.json()["tickets_left"]

    r2 = client.post("/api/v1/cards/draw", json={"count": 1, "idempotency_key": "same"},
                     headers=auth_headers)
    assert r2.status_code == 200
    assert r2.json()["replayed"] is True
    assert r2.json()["tickets_left"] == left1, "重放不应重复扣券"


def test_draw_rate_limited(client, auth_headers):
    _fill_tickets(client, auth_headers, 10)
    r1 = client.post("/api/v1/cards/draw", json={"count": 1, "idempotency_key": "x1"},
                     headers=auth_headers)
    assert r1.status_code == 200
    r2 = client.post("/api/v1/cards/draw", json={"count": 1, "idempotency_key": "x2"},
                     headers=auth_headers)
    assert r2.status_code == 400
    assert "太快" in r2.json()["detail"]


def test_card_list_hides_nothing_but_tracks_owned(client, auth_headers):
    r = client.get("/api/v1/cards", headers=auth_headers)
    assert r.status_code == 200
    data = r.json()
    # 卡池会随内容扩充增长，不写死数字；只校验与内容文件一致
    expected = len(content_loader.cards()["cards"])
    assert len(data["cards"]) == expected
    assert data["owned_total"] == 0
    assert len(data["sets"]) == len(content_loader.rewards()["sets"])


# ---------- 同步码 ----------

def test_sync_code_adopt_transfers_account(client):
    r = client.post("/api/v1/session")
    me1 = r.json()
    h1 = {"Authorization": f"Bearer {me1['token']}"}

    client.post("/api/v1/checkin", headers=h1)

    r2 = client.post("/api/v1/session")
    h2 = {"Authorization": f"Bearer {r2.json()['token']}"}

    r3 = client.post("/api/v1/session/adopt",
                     json={"sync_code": me1["sync_code"]}, headers=h2)
    assert r3.status_code == 200
    adopted = r3.json()
    assert adopted["points"] == 10
    assert adopted["sync_code"] == me1["sync_code"]


def test_rotate_code_invalidates_old(client, auth_headers):
    me = client.get("/api/v1/me", headers=auth_headers).json()
    old = me["sync_code"]

    r = client.post("/api/v1/session/rotate-code", headers=auth_headers)
    assert r.status_code == 200
    new = r.json()["sync_code"]
    assert new != old

    r2 = client.post("/api/v1/session/adopt", json={"sync_code": old})
    assert r2.status_code == 404


def test_invalid_token_rejected(client):
    r = client.get("/api/v1/me", headers={"Authorization": "Bearer nope"})
    assert r.status_code == 401


def test_adopt_rate_limited(client):
    codes = []
    for _ in range(6):
        codes.append(client.post("/api/v1/session").json()["sync_code"])
    last = codes[-1]
    for _ in range(6):
        r = client.post("/api/v1/session/adopt", json={"sync_code": last})
    assert r.status_code == 429


# ---------- 工具 ----------

def _all_answers(sec):
    t = sec["type"]
    if t in ("quiz", "boss"):
        return {q["id"]: q["answer"] for q in sec["questions"]}
    if t == "levels":
        return {q["id"]: q["answer"] for lv in sec["levels"] for q in lv["questions"]}
    if t == "myths":
        return {f"m{i}": m["check"]["answer"] for i, m in enumerate(sec["myths"])}
    if t == "steps":
        return {f"p{pi}s{si}": st["answer"]
                for pi, p in enumerate(sec["problems"])
                for si, st in enumerate(p["steps"])}
    return {}


def test_duplicate_cards_convert_to_shards(client, auth_headers):
    """重复卡应自动转碎片，且碎片数按稀有度分级。"""
    _fill_tickets(client, auth_headers, 100)
    total_shards = 0
    dup_seen = 0
    for i in range(6):
        with db.tx() as conn:
            conn.execute(
                "UPDATE events SET created_at='2020-01-01T00:00:00' "
                "WHERE kind='draw' AND user_id=(SELECT id FROM users WHERE token_hash=?)",
                (__import__("app.auth", fromlist=["x"]).hash_token(
                    auth_headers["Authorization"][7:]),),
            )
        r = client.post("/api/v1/cards/draw",
                        json={"count": 10, "idempotency_key": f"shard{i}"},
                        headers=auth_headers)
        assert r.status_code == 200, r.text
        data = r.json()
        for x in data["results"]:
            if not x["is_new"]:
                dup_seen += 1
                assert x["shards"] > 0, "重复卡应给碎片"
        total_shards += data["shards_gained"]
    assert dup_seen > 0, "6 次十连应有重复卡（卡池仅 12 张）"
    assert total_shards > 0


# ---------- 成就卡 ----------

def _set_points(client, headers, points):
    with db.tx() as conn:
        conn.execute(
            "UPDATE users SET points=? WHERE token_hash=?",
            (points, __import__("app.auth", fromlist=["x"]).hash_token(
                headers["Authorization"][7:])),
        )


def test_achievement_stats_initial(client, auth_headers):
    r = client.get("/api/v1/achievements", headers=auth_headers)
    assert r.status_code == 200
    d = r.json()
    assert d["stats"]["points_per_card"] == 100
    assert d["stats"]["value_cny"] == 50
    assert d["stats"]["daily_limit"] == 2
    assert d["stats"]["today_left"] == 2
    assert d["cards"] == []
    assert d["can_redeem"] is False


def test_achievement_redeem_insufficient(client, auth_headers):
    _set_points(client, auth_headers, 50)
    r = client.post("/api/v1/achievements/redeem", json={"count": 1}, headers=auth_headers)
    assert r.status_code == 400
    assert "积分不足" in r.json()["detail"]


def test_achievement_redeem_success(client, auth_headers):
    _set_points(client, auth_headers, 250)
    r = client.post("/api/v1/achievements/redeem", json={"count": 1}, headers=auth_headers)
    assert r.status_code == 200, r.text
    d = r.json()
    assert d["points"] == 150
    assert d["spent"] == 100
    assert len(d["cards"]) == 1
    card = d["cards"][0]
    assert card["value_cny"] == 50
    assert card["status"] == "issued"
    assert len(card["code"]) >= 12
    assert d["stats"]["today_count"] == 1
    assert d["stats"]["today_left"] == 1


def test_achievement_daily_limit(client, auth_headers):
    """一天最多 2 张：第 3 张必须拒绝。"""
    _set_points(client, auth_headers, 1000)
    for i in range(2):
        r = client.post("/api/v1/achievements/redeem", json={"count": 1}, headers=auth_headers)
        assert r.status_code == 200, f"第 {i+1} 张应成功: {r.text}"
    r3 = client.post("/api/v1/achievements/redeem", json={"count": 1}, headers=auth_headers)
    assert r3.status_code == 400
    assert "兑满" in r3.json()["detail"]

    # 积分只被扣了 2 次
    me = client.get("/api/v1/me", headers=auth_headers).json()
    assert me["points"] == 800


def test_achievement_redeem_two_at_once(client, auth_headers):
    _set_points(client, auth_headers, 500)
    r = client.post("/api/v1/achievements/redeem", json={"count": 2}, headers=auth_headers)
    assert r.status_code == 200, r.text
    d = r.json()
    assert len(d["cards"]) == 2
    assert d["spent"] == 200
    assert d["cards"][0]["code"] != d["cards"][1]["code"]
    assert d["today_left"] == 0


def test_achievement_cannot_exceed_daily_limit_in_one_call(client, auth_headers):
    _set_points(client, auth_headers, 1000)
    r = client.post("/api/v1/achievements/redeem", json={"count": 3}, headers=auth_headers)
    assert r.status_code == 400
    assert "还能兑 2 张" in r.json()["detail"]


def test_achievement_verify_once(client, auth_headers):
    _set_points(client, auth_headers, 200)
    r = client.post("/api/v1/achievements/redeem", json={"count": 1}, headers=auth_headers)
    code = r.json()["cards"][0]["code"]

    v1 = client.post("/api/v1/achievements/verify", json={"code": code}, headers=auth_headers)
    assert v1.status_code == 200, v1.text
    assert v1.json()["value_cny"] == 50

    v2 = client.post("/api/v1/achievements/verify", json={"code": code}, headers=auth_headers)
    assert v2.status_code == 400
    assert "已经兑现" in v2.json()["detail"]


def test_achievement_verify_unknown_code(client, auth_headers):
    r = client.post("/api/v1/achievements/verify",
                    json={"code": "AAAA-BBBB-CCCC"}, headers=auth_headers)
    assert r.status_code == 400
    assert "不存在" in r.json()["detail"]


def test_achievement_codes_unique(client, auth_headers):
    """批量生成不应撞码。"""
    codes = set()
    with db.tx() as conn:
        from app.services import achievements as achv
        for _ in range(200):
            codes.add(achv._new_code(conn))
    assert len(codes) == 200
