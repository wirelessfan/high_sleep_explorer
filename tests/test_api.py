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
    """每个用例一个独立数据库，并清空进程内限流计数。"""
    dbfile = tmp_path / "test.db"
    monkeypatch.setattr(db, "DB_PATH", dbfile)
    content_loader.clear_cache()
    # 限流是进程级内存计数，用例之间会互相影响（登录限流 10 次/10 分钟）
    from app.services import ratelimit
    ratelimit.reset()
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
    """全通按「单元」计（版块 × 已开放档位），所以要逐档走完。"""
    tid = "physics-induction"
    by_id = {sec["id"]: sec for sec in content_loader.topic(tid)["sections"]}
    for sid, tier in content_loader.topic_pairs(tid):
        content = content_loader.section_tiers(by_id[sid])[tier]
        if content["type"] == "reading":
            r = client.post(f"/api/v1/topics/{tid}/sections/{sid}/read?tier={tier}",
                            json={"confirmed": True}, headers=auth_headers)
        else:
            r = client.post(f"/api/v1/topics/{tid}/sections/{sid}/submit?tier={tier}",
                            json={"answers": _all_answers(content)}, headers=auth_headers)
        assert r.status_code == 200, f"{sid}/{tier}: {r.text}"

    me = client.get("/api/v1/me", headers=auth_headers).json()
    # 每个已开放档位首杀 Boss 一次（各 1 张）+ 主题全通（2 张）
    tiers = {tier for _, tier in content_loader.topic_pairs(tid)}
    assert me["tickets"] == len(tiers) + 2


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
    """核销需家长账号：用 dad 核销，验证只能核销一次。"""
    _set_points(client, auth_headers, 200)
    r = client.post("/api/v1/achievements/redeem", json={"count": 1}, headers=auth_headers)
    code = r.json()["cards"][0]["code"]

    dad_h, _ = _login_as(client, "dad")
    v1 = client.post("/api/v1/achievements/verify", json={"code": code}, headers=dad_h)
    assert v1.status_code == 200, v1.text
    assert v1.json()["value_cny"] == 50

    v2 = client.post("/api/v1/achievements/verify", json={"code": code}, headers=dad_h)
    assert v2.status_code == 400
    assert "已经兑现" in v2.json()["detail"]


def test_achievement_verify_unknown_code(client, auth_headers):
    dad_h, _ = _login_as(client, "dad")
    r = client.post("/api/v1/achievements/verify",
                    json={"code": "AAAA-BBBB-CCCC"}, headers=dad_h)
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


# ---------- 账号登录 ----------

def _make_account(client, username, password, nickname):
    """测试用：直接在库里建一个带密码的账号。"""
    from app import auth as _auth
    with db.tx() as conn:
        uid = _auth.new_id()
        conn.execute(
            "INSERT INTO users(id, token_hash, sync_code, nickname, username, password_hash, "
            "created_at, last_seen) VALUES (?,?,?,?,?,?,?,?)",
            (uid, _auth.hash_token(_auth.new_token()),
             _auth.normalize_sync_code(_auth.new_sync_code()),
             nickname, username, _auth.hash_password(password),
             "2026-01-01T00:00:00", "2026-01-01T00:00:00"),
        )
    return uid


def test_login_success(client):
    _make_account(client, "dad", "123456", "爸爸")
    r = client.post("/api/v1/session/login", json={"username": "dad", "password": "123456"})
    assert r.status_code == 200
    d = r.json()
    assert d["username"] == "dad"
    assert d["nickname"] == "爸爸"
    assert d["has_password"] is True
    assert d["token"]


def test_login_wrong_password(client):
    _make_account(client, "mom", "123456", "妈妈")
    r = client.post("/api/v1/session/login", json={"username": "mom", "password": "bad"})
    assert r.status_code == 401
    assert "账号或密码" in r.json()["detail"]


def test_login_unknown_user_same_message(client):
    """不暴露账号是否存在。"""
    r = client.post("/api/v1/session/login", json={"username": "ghost", "password": "123456"})
    assert r.status_code == 401
    assert r.json()["detail"] == "账号或密码不正确"


def test_login_case_insensitive_username(client):
    _make_account(client, "sunny", "123456", "sunny")
    r = client.post("/api/v1/session/login", json={"username": "Sunny", "password": "123456"})
    assert r.status_code == 200
    assert r.json()["username"] == "sunny"


def test_change_password_flow(client):
    _make_account(client, "dad", "123456", "爸爸")
    login = client.post("/api/v1/session/login",
                        json={"username": "dad", "password": "123456"}).json()
    h = {"Authorization": f"Bearer {login['token']}"}

    r = client.post("/api/v1/session/password",
                    json={"old_password": "123456", "new_password": "n3wpass"}, headers=h)
    assert r.status_code == 200

    # 旧密码失效
    assert client.post("/api/v1/session/login",
                       json={"username": "dad", "password": "123456"}).status_code == 401
    # 新密码可用
    assert client.post("/api/v1/session/login",
                       json={"username": "dad", "password": "n3wpass"}).status_code == 200


def test_change_password_rejects_wrong_old(client):
    _make_account(client, "mom", "123456", "妈妈")
    login = client.post("/api/v1/session/login",
                        json={"username": "mom", "password": "123456"}).json()
    h = {"Authorization": f"Bearer {login['token']}"}
    r = client.post("/api/v1/session/password",
                    json={"old_password": "wrong", "new_password": "abcdef"}, headers=h)
    assert r.status_code == 400
    assert "原密码不正确" in r.json()["detail"]


def test_change_password_rejects_short(client):
    _make_account(client, "mom", "123456", "妈妈")
    login = client.post("/api/v1/session/login",
                        json={"username": "mom", "password": "123456"}).json()
    h = {"Authorization": f"Bearer {login['token']}"}
    r = client.post("/api/v1/session/password",
                    json={"old_password": "123456", "new_password": "123"}, headers=h)
    assert r.status_code == 422  # Pydantic min_length


def test_change_password_rejects_same(client):
    _make_account(client, "mom", "123456", "妈妈")
    login = client.post("/api/v1/session/login",
                        json={"username": "mom", "password": "123456"}).json()
    h = {"Authorization": f"Bearer {login['token']}"}
    r = client.post("/api/v1/session/password",
                    json={"old_password": "123456", "new_password": "123456"}, headers=h)
    assert r.status_code == 400


def test_list_users_no_secrets(client):
    _make_account(client, "dad", "123456", "爸爸")
    _make_account(client, "mom", "123456", "妈妈")
    r = client.get("/api/v1/session/users")
    assert r.status_code == 200
    users = r.json()["users"]
    names = {u["username"] for u in users}
    assert {"dad", "mom"} <= names
    for u in users:
        assert set(u.keys()) == {"username", "nickname"}, "不应泄露任何敏感字段"


def test_password_hash_not_plaintext(client):
    uid = _make_account(client, "dad", "123456", "爸爸")
    with db.ro() as conn:
        row = conn.execute("SELECT password_hash FROM users WHERE id=?", (uid,)).fetchone()
    assert row["password_hash"] != "123456"
    assert row["password_hash"].startswith("pbkdf2_sha256$")


# ---------- 每日随机卡与赠送 ----------

def test_daily_draw_status_initial(client, auth_headers):
    r = client.get("/api/v1/achievements/daily", headers=auth_headers)
    assert r.status_code == 200
    d = r.json()
    assert d["enabled"] is True
    assert d["left_today"] == 1
    assert [t["value_cny"] for t in d["tiers"]] == [5, 10, 20, 50]
    assert [t["weight"] for t in d["tiers"]] == [50, 30, 15, 5]
    assert d["gift_to"] == "sunny"


def test_daily_draw_once_per_day(client, auth_headers):
    r1 = client.post("/api/v1/achievements/daily/draw", headers=auth_headers)
    assert r1.status_code == 200, r1.text
    card = r1.json()["card"]
    assert card["value_cny"] in (5, 10, 20, 50)
    assert card["source"] == "daily"
    assert card["code"]

    r2 = client.post("/api/v1/achievements/daily/draw", headers=auth_headers)
    assert r2.status_code == 400
    assert "已经抽过" in r2.json()["detail"]


def test_daily_draw_is_free(client, auth_headers):
    """抽卡不消耗积分，也不占积分兑换的日额度。"""
    _set_points(client, auth_headers, 100)
    client.post("/api/v1/achievements/daily/draw", headers=auth_headers)
    me = client.get("/api/v1/me", headers=auth_headers).json()
    assert me["points"] == 100

    redeem = client.post("/api/v1/achievements/redeem", json={"count": 1}, headers=auth_headers)
    assert redeem.status_code == 200, "每日抽卡不应占用积分兑换额度"


def test_daily_draw_distribution():
    """权重抽样必须落在预期区间内。"""
    from app.services import achievements as achv
    tiers = [{"value_cny": 5, "weight": 50}, {"value_cny": 10, "weight": 30},
             {"value_cny": 20, "weight": 15}, {"value_cny": 50, "weight": 5}]
    counts = {5: 0, 10: 0, 20: 0, 50: 0}
    N = 20000
    for _ in range(N):
        counts[achv._roll_value(tiers)] += 1
    for v, expected in ((5, 50), (10, 30), (20, 15), (50, 5)):
        pct = counts[v] / N * 100
        assert abs(pct - expected) < 3.5, f"{v}元 {pct:.1f}% 偏离 {expected}%"


def test_gift_card_to_sunny(client, auth_headers):
    from app import auth as _auth
    # 建 sunny 账号作为接收方
    with db.tx() as conn:
        conn.execute(
            "INSERT INTO users(id, token_hash, sync_code, nickname, username, password_hash, "
            "created_at, last_seen) VALUES (?,?,?,?,?,?,?,?)",
            ("u_sunny_test", _auth.hash_token(_auth.new_token()),
             _auth.normalize_sync_code(_auth.new_sync_code()),
             "sunny", "sunny", _auth.hash_password("123456"), "2026-01-01T00:00:00", "2026-01-01T00:00:00"),
        )

    draw = client.post("/api/v1/achievements/daily/draw", headers=auth_headers)
    card = draw.json()["card"]

    r = client.post("/api/v1/achievements/gift",
                    json={"card_id": card["id"], "to_username": "sunny"},
                    headers=auth_headers)
    assert r.status_code == 200, r.text
    assert r.json()["to_username"] == "sunny"
    assert r.json()["value_cny"] == card["value_cny"]

    # 原主人不再拥有
    r2 = client.post("/api/v1/achievements/gift",
                     json={"card_id": card["id"], "to_username": "sunny"},
                     headers=auth_headers)
    assert r2.status_code == 400


def test_gift_unknown_target(client, auth_headers):
    draw = client.post("/api/v1/achievements/daily/draw", headers=auth_headers)
    card = draw.json()["card"]
    r = client.post("/api/v1/achievements/gift",
                    json={"card_id": card["id"], "to_username": "nobody"},
                    headers=auth_headers)
    assert r.status_code == 400
    assert "不存在" in r.json()["detail"]


def test_gift_to_self_rejected(client, auth_headers):
    me = client.get("/api/v1/me", headers=auth_headers).json()
    # 匿名测试用户没有 username，先给它一个
    with db.tx() as conn:
        conn.execute("UPDATE users SET username='self_test' WHERE id=?", (me["id"],))
    draw = client.post("/api/v1/achievements/daily/draw", headers=auth_headers)
    card = draw.json()["card"]
    r = client.post("/api/v1/achievements/gift",
                    json={"card_id": card["id"], "to_username": "self_test"},
                    headers=auth_headers)
    assert r.status_code == 400
    assert "自己" in r.json()["detail"]


def test_received_cards_lists_gifts(client):
    from app import auth as _auth
    # 两个账号：giver 抽卡送 sunny
    giver = client.post("/api/v1/session").json()
    gh = {"Authorization": f"Bearer {giver['token']}"}
    with db.tx() as conn:
        conn.execute(
            "INSERT OR IGNORE INTO users(id, token_hash, sync_code, nickname, username, "
            "password_hash, created_at, last_seen) VALUES (?,?,?,?,?,?,?,?)",
            ("u_recv_sunny", _auth.hash_token(_auth.new_token()),
             _auth.normalize_sync_code(_auth.new_sync_code()),
             "sunny", "sunny", _auth.hash_password("123456"), "2026-01-01T00:00:00", "2026-01-01T00:00:00"),
        )
        conn.execute("UPDATE users SET username='giver' WHERE id=?", (giver["id"],))

    card = client.post("/api/v1/achievements/daily/draw", headers=gh).json()["card"]
    client.post("/api/v1/achievements/gift",
                json={"card_id": card["id"], "to_username": "sunny"}, headers=gh)

    # 以 sunny 身份查看（直接签发令牌）
    token = _auth.new_token()
    with db.tx() as conn:
        conn.execute("UPDATE users SET token_hash=? WHERE id='u_recv_sunny'",
                     (_auth.hash_token(token),))
    sh = {"Authorization": f"Bearer {token}"}

    r = client.get("/api/v1/achievements/received", headers=sh)
    assert r.status_code == 200
    d = r.json()
    assert d["total"] == 1
    assert d["cards"][0]["from_username"] == "giver"
    assert d["cards"][0]["value_cny"] == card["value_cny"]


def test_daily_draw_does_not_consume_redeem_quota(client, auth_headers):
    """回归：每日抽卡不得占用积分兑换的日额度。"""
    _set_points(client, auth_headers, 500)
    client.post("/api/v1/achievements/daily/draw", headers=auth_headers)

    st = client.get("/api/v1/achievements", headers=auth_headers).json()["stats"]
    assert st["today_count"] == 0, "抽卡不应计入兑换次数"
    assert st["today_left"] == 2, "抽卡后仍应有完整的 2 次兑换额度"

    # 两次兑换都应成功
    for i in range(2):
        r = client.post("/api/v1/achievements/redeem", json={"count": 1}, headers=auth_headers)
        assert r.status_code == 200, f"第 {i+1} 次兑换应成功: {r.text}"

    st2 = client.get("/api/v1/achievements", headers=auth_headers).json()["stats"]
    assert st2["today_count"] == 2
    assert st2["total_count"] == 3, "累计应包含抽卡 + 两张兑换"


def test_gifting_does_not_reset_daily_quota(client, auth_headers):
    """回归：抽完立刻送人，不能因此再抽一次。"""
    from app import auth as _auth
    with db.tx() as conn:
        conn.execute(
            "INSERT OR IGNORE INTO users(id, token_hash, sync_code, nickname, username, "
            "password_hash, created_at, last_seen) VALUES (?,?,?,?,?,?,?,?)",
            ("u_sunny_q", _auth.hash_token(_auth.new_token()),
             _auth.normalize_sync_code(_auth.new_sync_code()),
             "sunny", "sunny", _auth.hash_password("123456"),
             "2026-01-01T00:00:00", "2026-01-01T00:00:00"),
        )

    card = client.post("/api/v1/achievements/daily/draw", headers=auth_headers).json()["card"]
    client.post("/api/v1/achievements/gift",
                json={"card_id": card["id"], "to_username": "sunny"}, headers=auth_headers)

    # 状态必须仍显示今天已抽
    st = client.get("/api/v1/achievements/daily", headers=auth_headers).json()
    assert st["left_today"] == 0, "赠出后不应恢复抽卡次数"

    r = client.post("/api/v1/achievements/daily/draw", headers=auth_headers)
    assert r.status_code == 400, "赠送不应绕过每日一次限制"


# ---------- 核销权限 ----------

def _login_as(client, username, password="123456"):
    """建账号并登录，返回 (headers, me)。"""
    from app import auth as _auth
    with db.tx() as conn:
        exists = conn.execute("SELECT id FROM users WHERE username=?", (username,)).fetchone()
        if not exists:
            conn.execute(
                "INSERT INTO users(id, token_hash, sync_code, nickname, username, password_hash, "
                "created_at, last_seen) VALUES (?,?,?,?,?,?,?,?)",
                (_auth.new_id(), _auth.hash_token(_auth.new_token()),
                 _auth.normalize_sync_code(_auth.new_sync_code()),
                 username, username, _auth.hash_password(password),
                 "2026-01-01T00:00:00", "2026-01-01T00:00:00"),
            )
    r = client.post("/api/v1/session/login", json={"username": username, "password": password})
    assert r.status_code == 200, r.text
    d = r.json()
    return {"Authorization": f"Bearer {d['token']}"}, d


def _issue_card(client, headers):
    """用每日抽卡拿一张卡，返回卡对象。"""
    r = client.post("/api/v1/achievements/daily/draw", headers=headers)
    assert r.status_code == 200, r.text
    return r.json()["card"]


def test_sunny_cannot_verify(client):
    """sunny 自己不能核销。"""
    sunny_h, _ = _login_as(client, "sunny")
    card = _issue_card(client, sunny_h)

    r = client.post("/api/v1/achievements/verify", json={"code": card["code"]}, headers=sunny_h)
    assert r.status_code == 403
    assert "只有家长" in r.json()["detail"]

    # 卡仍然是待兑现状态
    lst = client.get("/api/v1/achievements", headers=sunny_h).json()
    statuses = [c["status"] for c in lst["cards"] + lst["gifted_cards"]]
    assert "issued" in statuses


def test_dad_can_verify(client):
    dad_h, dad = _login_as(client, "dad")
    sunny_h, _ = _login_as(client, "sunny")
    card = _issue_card(client, sunny_h)

    r = client.post("/api/v1/achievements/verify", json={"code": card["code"]}, headers=dad_h)
    assert r.status_code == 200, r.text
    d = r.json()
    assert d["value_cny"] == card["value_cny"]
    assert d["redeemed_by"] == "dad"


def test_mom_can_verify(client):
    mom_h, _ = _login_as(client, "mom")
    sunny_h, _ = _login_as(client, "sunny")
    card = _issue_card(client, sunny_h)

    r = client.post("/api/v1/achievements/verify", json={"code": card["code"]}, headers=mom_h)
    assert r.status_code == 200
    assert r.json()["redeemed_by"] == "mom"


def test_verify_permission_endpoint(client):
    sunny_h, _ = _login_as(client, "sunny")
    dad_h, _ = _login_as(client, "dad")

    a = client.get("/api/v1/achievements/verify-permission", headers=sunny_h).json()
    assert a["can_verify"] is False
    assert set(a["allowed"]) == {"dad", "mom"}

    b = client.get("/api/v1/achievements/verify-permission", headers=dad_h).json()
    assert b["can_verify"] is True


def test_cannot_verify_twice(client):
    dad_h, _ = _login_as(client, "dad")
    card = _issue_card(client, dad_h)

    assert client.post("/api/v1/achievements/verify",
                       json={"code": card["code"]}, headers=dad_h).status_code == 200
    r2 = client.post("/api/v1/achievements/verify",
                     json={"code": card["code"]}, headers=dad_h)
    assert r2.status_code == 400
    assert "已经兑现" in r2.json()["detail"]


# ---------- 错题本与 AI ----------

def _fail_one_section(client, headers, topic_id="physics-induction", section="quick"):
    """故意答错一题，制造一条错题记录。返回 (wrong details 数量, 详情)。"""
    data = content_loader.topic(topic_id)
    sec = next(s for s in data["sections"] if s["id"] == section)
    qs = sec["questions"]
    # 第一题故意选错
    answers = {q["id"]: q["answer"] for q in qs}
    first = qs[0]["id"]
    answers[first] = (qs[0]["answer"] + 1) % len(qs[0]["options"])
    r = client.post(f"/api/v1/topics/{topic_id}/sections/{section}/submit",
                    json={"answers": answers}, headers=headers)
    assert r.status_code == 200
    return r.json()


def test_wrong_question_recorded(client, auth_headers):
    res = _fail_one_section(client, auth_headers)
    wrongs = [d for d in res["details"] if not d["correct"]]
    assert len(wrongs) == 1

    wb = client.get("/api/v1/wrongbook", headers=auth_headers).json()
    assert wb["summary"]["open_total"] == 1
    assert wb["items"][0]["topic_id"] == "physics-induction"
    assert wb["items"][0]["stem"], "错题应带题干快照"
    assert wb["items"][0]["options"], "错题应带选项快照"
    # 快照里不能有答案字段泄露给前端选择区（answer 字段是核分用的，前端只在已提交后展示）
    assert "picked" in wb["items"][0]


def test_wrong_question_accumulates(client, auth_headers):
    """同一题再答错：wrong_count 累加，不新增行。"""
    _fail_one_section(client, auth_headers)
    res = _fail_one_section(client, auth_headers)  # 复习重做，又错同一题
    wb = client.get("/api/v1/wrongbook", headers=auth_headers).json()
    assert wb["summary"]["open_total"] == 1
    assert wb["items"][0]["wrong_count"] == 2


def test_redo_clears_and_rewards(client, auth_headers):
    """错题重做全对 → 清零 + 奖励；重复清零当天不再发奖。"""
    _fail_one_section(client, auth_headers)
    wb = client.get("/api/v1/wrongbook", headers=auth_headers).json()
    tid = wb["summary"]["topics"][0]["topic_id"]
    item = wb["items"][0]

    me0 = client.get("/api/v1/me", headers=auth_headers).json()
    r = client.post(f"/api/v1/wrongbook/{tid}/redo",
                    json={"answers": {item["id"]: item["answer"]}}, headers=auth_headers)
    assert r.status_code == 200, r.text
    d = r.json()
    assert d["cleared"] == 1
    assert d["remaining"] == 0
    assert d["bonus"] == 20

    me1 = client.get("/api/v1/me", headers=auth_headers).json()
    assert me1["points"] == me0["points"] + 20

    # 同一主题当天再清零不发奖（此时无错题，应直接 400）
    r2 = client.post(f"/api/v1/wrongbook/{tid}/redo",
                     json={"answers": {item["id"]: item["answer"]}}, headers=auth_headers)
    assert r2.status_code == 400
    assert "没有待清零" in r2.json()["detail"]


def test_redo_wrong_again_accumulates(client, auth_headers):
    """重做时又错：不清零、wrong_count 继续 +1。"""
    _fail_one_section(client, auth_headers)
    wb = client.get("/api/v1/wrongbook", headers=auth_headers).json()
    tid = wb["summary"]["topics"][0]["topic_id"]
    item = wb["items"][0]

    wrong_pick = (item["answer"] + 1) % len(item["options"])
    r = client.post(f"/api/v1/wrongbook/{tid}/redo",
                    json={"answers": {item["id"]: wrong_pick}}, headers=auth_headers)
    assert r.status_code == 200
    d = r.json()
    assert d["cleared"] == 0
    assert d["re_wrong"] == 1
    assert d["bonus"] == 0

    wb2 = client.get("/api/v1/wrongbook", headers=auth_headers).json()
    assert wb2["items"][0]["wrong_count"] == 2
    assert wb2["items"][0]["picked"] == wrong_pick


def test_redo_requires_answers(client, auth_headers):
    """跳题（未答）不会清零。"""
    _fail_one_section(client, auth_headers)
    wb = client.get("/api/v1/wrongbook", headers=auth_headers).json()
    tid = wb["summary"]["topics"][0]["topic_id"]
    item = wb["items"][0]

    r = client.post(f"/api/v1/wrongbook/{tid}/redo",
                    json={"answers": {}}, headers=auth_headers)
    assert r.status_code == 200
    d = r.json()
    assert d["results"][0]["skipped"] is True
    assert d["cleared"] == 0


def test_ai_disabled_returns_503(client, auth_headers, monkeypatch):
    from app.services import ai_client
    monkeypatch.setattr(ai_client, "API_KEY", "")
    _fail_one_section(client, auth_headers)
    wb = client.get("/api/v1/wrongbook", headers=auth_headers).json()
    wq_id = wb["items"][0]["id"]
    r = client.post("/api/v1/wrongbook/ai", json={"ids": [wq_id]}, headers=auth_headers)
    assert r.status_code == 503


def test_ai_analyze_with_stub(client, auth_headers, monkeypatch):
    """无 Key 时走 stub 路径，验证缓存与结构。"""
    from app.services import ai_client
    monkeypatch.setattr(ai_client, "API_KEY", "test-key")
    monkeypatch.setattr(ai_client, "analyze", ai_client.analyze_stub)

    _fail_one_section(client, auth_headers)
    wb = client.get("/api/v1/wrongbook", headers=auth_headers).json()
    wq_id = wb["items"][0]["id"]

    r = client.post("/api/v1/wrongbook/ai", json={"ids": [wq_id]}, headers=auth_headers)
    assert r.status_code == 200
    d = r.json()
    v = d["results"][0]["value"]
    assert v["stub"] is True
    assert "analysis" in v and "suggestions" in v

    # 结果已缓存进行
    wb2 = client.get("/api/v1/wrongbook", headers=auth_headers).json()
    assert wb2["items"][0]["ai"]["analysis"] == v["analysis"]

    # 再次请求同一题：缓存命中，不再产生新事件
    r2 = client.post("/api/v1/wrongbook/ai", json={"ids": [wq_id]}, headers=auth_headers)
    assert r2.json()["results"][0]["cached"] is True


def test_ai_batch_cap_five(client, auth_headers, monkeypatch):
    from app.services import ai_client
    monkeypatch.setattr(ai_client, "API_KEY", "test-key")
    monkeypatch.setattr(ai_client, "analyze", ai_client.analyze_stub)

    r = client.post("/api/v1/wrongbook/ai",
                    json={"ids": ["wq_1", "wq_2", "wq_3", "wq_4", "wq_5", "wq_6"]},
                    headers=auth_headers)
    assert r.status_code == 200
    assert len(r.json()["results"]) == 5, "单次最多分析 5 题"


def test_wrongbook_isolated_between_users(client):
    """错题按用户隔离。"""
    _make_account(client, "dad", "123456", "爸爸")
    h1, _ = _login_as(client, "sunny")
    h2, _ = _login_as(client, "dad")
    _fail_one_section(client, h1)

    wb1 = client.get("/api/v1/wrongbook", headers=h1).json()
    wb2 = client.get("/api/v1/wrongbook", headers=h2).json()
    assert wb1["summary"]["open_total"] == 1
    assert wb2["summary"]["open_total"] == 0
