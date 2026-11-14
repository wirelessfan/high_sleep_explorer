"""盲盒系统 + 许愿墙：抽盒、保底、兑换、每日限额、管理员审核守卫。"""
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


@pytest.fixture()
def auth(client):
    r = client.post("/api/v1/session")
    assert r.status_code == 200
    return {"Authorization": f"Bearer {r.json()['token']}"}


def _make_account(username, password, nickname, role=None):
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


def _login(client, username, password="123456"):
    r = client.post("/api/v1/session/login", json={"username": username, "password": password})
    assert r.status_code == 200
    return {"Authorization": f"Bearer {r.json()['token']}"}


class _NoRateLimit:
    """绕过盲盒 1 秒限流（测试里连续开盒）。"""

    def __init__(self, monkeypatch):
        self.mp = monkeypatch

    def __enter__(self):
        from app.services import blindbox
        original = blindbox.draw

        def patched(conn, user, count, key):
            res = original(conn, user, count, key)
            # 把最近一条 blindbox 事件推到 2 秒前，让下一次通过限流检查。
            # 必须用与 events.now() 相同的 ISO(秒级) 格式，否则 fromisoformat 解析失败。
            from datetime import datetime, timedelta
            backdated = (datetime.now() - timedelta(seconds=2)).isoformat(timespec="seconds")
            conn.execute(
                "UPDATE events SET created_at=? "
                "WHERE id=(SELECT MAX(id) FROM events WHERE kind='blindbox')",
                (backdated,),
            )
            return res

        self.mp.setattr(blindbox, "draw", patched)
        return self

    def __exit__(self, *exc):
        return False


# ---------- 内容与初始状态 ----------

def test_blindbox_content_and_initial_state(client, auth):
    r = client.get("/api/v1/blindbox", headers=auth)
    assert r.status_code == 200
    d = r.json()

    chars = content_loader.blindbox_characters()["characters"]
    assert d["total"] == len(chars) == 8
    assert d["tickets"] == 3, "匿名新用户默认 3 张体验券"
    assert d["unlocked"] == 0
    assert d["costs"]["single"] == 1 and d["costs"]["ten"] == 9
    assert set(d["rates"]) == {"N", "R", "SR", "SSR"}

    by_rarity = {}
    for c in chars:
        by_rarity[c["rarity"]] = by_rarity.get(c["rarity"], 0) + 1
    assert by_rarity == {"N": 2, "R": 2, "SR": 2, "SSR": 2}


def test_blindbox_gallery_has_image_paths(client, auth):
    d = client.get("/api/v1/blindbox", headers=auth).json()
    for c in d["gallery"]:
        assert c["image"].startswith("/assets/blindbox/")
        assert c["image"].endswith(".svg")
        assert c["unlocked"] is False
        assert c["value_cny"] >= 0


# ---------- 抽盒 ----------

def test_draw_requires_tickets(client, auth, monkeypatch):
    # 花光 3 张券后第 4 次必须报「券不足」（全程绕过 1 秒限流，确保测的是余额而非限流）
    with _NoRateLimit(monkeypatch):
        for i in range(3):
            r = client.post("/api/v1/blindbox/draw",
                            json={"count": 1, "idempotency_key": f"k{i}"}, headers=auth)
            assert r.status_code == 200, r.text
        r = client.post("/api/v1/blindbox/draw", json={"count": 1, "idempotency_key": "k4"},
                        headers=auth)
    assert r.status_code == 400
    assert "盲盒券不足" in r.json()["detail"]


def test_draw_consumes_one_ticket(client, auth):
    r = client.post("/api/v1/blindbox/draw", json={"count": 1, "idempotency_key": "d1"},
                    headers=auth)
    assert r.status_code == 200
    d = r.json()
    assert d["cost"] == 1
    assert d["tickets_left"] == 2
    assert len(d["results"]) == 1
    item = d["results"][0]
    assert item["character_id"] and item["name"]
    assert item["rarity"] in ("N", "R", "SR", "SSR")
    assert item["image"].startswith("/assets/blindbox/")


def test_draw_ten_costs_nine(client, auth):
    # 先补满券（新用户 3 张不够十连）；按 token_hash 精确定位，避免并行测试串库
    from app import auth as _auth
    with db.tx() as conn:
        uid = conn.execute("SELECT id FROM users WHERE token_hash=?",
                           (_auth.hash_token(auth["Authorization"][7:]),)).fetchone()["id"]
        conn.execute("UPDATE users SET blindbox_tickets = 20 WHERE id=?", (uid,))

    r = client.post("/api/v1/blindbox/draw", json={"count": 10, "idempotency_key": "ten"},
                    headers=auth)
    assert r.status_code == 200
    d = r.json()
    assert d["cost"] == 9
    # 重复角色会返还券，故校验「扣券净值上限」而非固定余额
    assert 11 <= d["tickets_left"] <= 20
    assert len(d["results"]) == 10


def test_draw_idempotent(client, auth):
    first = client.post("/api/v1/blindbox/draw",
                        json={"count": 1, "idempotency_key": "same-key"}, headers=auth).json()
    second = client.post("/api/v1/blindbox/draw",
                         json={"count": 1, "idempotency_key": "same-key"}, headers=auth).json()
    assert second["replayed"] is True
    assert second["tickets_left"] == first["tickets_left"], "重放不再扣券"


def test_draw_rate_limited(client, auth):
    # 用全新匿名用户，避免其他用例残留的 blindbox 事件干扰 1 秒限流判定
    r0 = client.post("/api/v1/session")
    fresh = {"Authorization": f"Bearer {r0.json()['token']}"}
    first = client.post("/api/v1/blindbox/draw",
                        json={"count": 1, "idempotency_key": "r1"}, headers=fresh)
    assert first.status_code == 200, first.text
    r = client.post("/api/v1/blindbox/draw", json={"count": 1, "idempotency_key": "r2"},
                    headers=fresh)
    assert r.status_code == 400
    assert "太快" in r.json()["detail"]


def test_draw_invalid_count(client, auth):
    r = client.post("/api/v1/blindbox/draw", json={"count": 11, "idempotency_key": "x"},
                    headers=auth)
    assert r.status_code == 422, "Pydantic 层拦截 1..10"


# ---------- 保底与重复补偿 ----------

def test_pity_ssr_forces_ssr(auth, client):
    """把保底计数推到 pity_ssr-1，下一次必出 SSR。"""
    from app.services import blindbox
    cfg = content_loader.rewards()["blindbox"]
    with db.tx() as conn:
        user = conn.execute("SELECT * FROM users LIMIT 1").fetchone()
        conn.execute("UPDATE users SET bb_pity_ssr=?, bb_pity_sr=0, blindbox_tickets=10 WHERE id=?",
                     (cfg["pity_ssr"] - 1, user["id"]))
        fresh = conn.execute("SELECT * FROM users WHERE id=?", (user["id"],)).fetchone()
        res = blindbox.draw(conn, fresh, 1, "pity-test")
    assert res["replayed"] is False
    assert res["results"][0]["rarity"] == "SSR"
    assert res["pity_ssr"] == 0, "SSR 后保底清零"


def test_duplicate_returns_tickets(client, auth, monkeypatch):
    """把 8 个角色全部解锁后再开，重复项按稀有度返券。"""
    from app import auth as _auth
    with db.tx() as conn:
        uid = conn.execute("SELECT id FROM users LIMIT 1").fetchone()["id"]
        for ch in content_loader.blindbox_characters()["characters"]:
            conn.execute(
                "INSERT INTO blindbox_owned(user_id, character_id, count, first_at) VALUES (?,?,1,?)",
                (uid, ch["id"], "2026-01-01T00:00:00"),
            )
        conn.execute("UPDATE users SET blindbox_tickets=50 WHERE id=?", (uid,))

    with _NoRateLimit(monkeypatch):
        total_back = 0
        for i in range(6):
            r = client.post("/api/v1/blindbox/draw",
                            json={"count": 10, "idempotency_key": f"dup{i}"}, headers=auth)
            assert r.status_code == 200
            total_back += r.json()["tickets_back"]
    assert total_back > 0, "全收集后应持续返还盲盒券"


# ---------- 积分换券 ----------

def test_exchange_points_to_tickets(client, auth):
    with db.tx() as conn:
        conn.execute("UPDATE users SET points = 250")

    r = client.post("/api/v1/blindbox/exchange", json={"count": 1}, headers=auth)
    assert r.status_code == 200
    d = r.json()
    assert d["points_spent"] == 100
    assert d["points_left"] == 150
    assert d["tickets_total"] == 4, "原有 3 张 + 兑换 1 张"


def test_exchange_daily_limit(client, auth):
    with db.tx() as conn:
        conn.execute("UPDATE users SET points = 1000")
    assert client.post("/api/v1/blindbox/exchange", json={"count": 1}, headers=auth).status_code == 200
    r = client.post("/api/v1/blindbox/exchange", json={"count": 1}, headers=auth)
    assert r.status_code == 400
    assert "已经兑换过" in r.json()["detail"]


def test_exchange_insufficient_points(client, auth):
    r = client.post("/api/v1/blindbox/exchange", json={"count": 1}, headers=auth)
    assert r.status_code == 400
    assert "积分不足" in r.json()["detail"]


# ---------- 实物兑换 ----------

def test_redeem_requires_copy(client):
    r = client.post("/api/v1/session")
    h = {"Authorization": f"Bearer {r.json()['token']}"}
    r2 = client.post("/api/v1/blindbox/redeem", json={"character_id": "bubu-mint"}, headers=h)
    assert r2.status_code == 400
    assert "副本" in r2.json()["detail"]


def test_redeem_creates_code_and_consumes_copy(client):
    r = client.post("/api/v1/session")
    h = {"Authorization": f"Bearer {r.json()['token']}"}
    with db.tx() as conn:
        uid = conn.execute("SELECT id FROM users LIMIT 1").fetchone()["id"]
        conn.execute(
            "INSERT INTO blindbox_owned(user_id, character_id, count, first_at) VALUES (?,?,2,?)",
            (uid, "bubu-galaxy", "2026-01-01T00:00:00"),
        )

    r2 = client.post("/api/v1/blindbox/redeem", json={"character_id": "bubu-galaxy"}, headers=h)
    assert r2.status_code == 200
    d = r2.json()
    assert d["value_cny"] == 100, "SSR 面值 100"
    assert d["code"].count("-") == 2, "兑现码形如 XXXX-XXXX-XXXX"
    assert d["copies_left"] == 1

    # 图鉴仍解锁
    gal = client.get("/api/v1/blindbox", headers=h).json()["gallery"]
    target = next(g for g in gal if g["id"] == "bubu-galaxy")
    assert target["unlocked"] is True and target["count"] == 1


def test_redeem_once_per_month(client):
    r = client.post("/api/v1/session")
    h = {"Authorization": f"Bearer {r.json()['token']}"}
    with db.tx() as conn:
        uid = conn.execute("SELECT id FROM users LIMIT 1").fetchone()["id"]
        conn.execute(
            "INSERT INTO blindbox_owned(user_id, character_id, count, first_at) VALUES (?,?,3,?)",
            (uid, "bubu-mint", "2026-01-01T00:00:00"),
        )
    assert client.post("/api/v1/blindbox/redeem",
                       json={"character_id": "bubu-mint"}, headers=h).status_code == 200
    r2 = client.post("/api/v1/blindbox/redeem", json={"character_id": "bubu-mint"}, headers=h)
    assert r2.status_code == 400
    assert "本月" in r2.json()["detail"]


def test_blindbox_codes_visible_to_parent_verify(client):
    """实物兑换产出的码在家长核销接口里可兑现。"""
    _make_account("dad", "123456", "爸爸", role="admin")
    dad = _login(client, "dad")

    r = client.post("/api/v1/session")
    kid_token = r.json()["token"]
    kid = {"Authorization": f"Bearer {kid_token}"}
    # 按 token_hash 精确定位这个匿名用户，避免误取到 dad 那一行
    from app import auth as _auth
    with db.tx() as conn:
        uid = conn.execute("SELECT id FROM users WHERE token_hash=?",
                           (_auth.hash_token(kid_token),)).fetchone()["id"]
        conn.execute(
            "INSERT INTO blindbox_owned(user_id, character_id, count, first_at) VALUES (?,?,1,?)",
            (uid, "bubu-sky", "2026-01-01T00:00:00"),
        )
    code = client.post("/api/v1/blindbox/redeem",
                       json={"character_id": "bubu-sky"}, headers=kid).json()["code"]

    v = client.post("/api/v1/achievements/verify", json={"code": code}, headers=dad)
    assert v.status_code == 200
    assert v.json()["value_cny"] == 10, "R 级面值 10"
    assert v.json()["redeemed_by"] == "dad"


# ---------- 许愿墙 ----------

def test_wish_submit_rewards_ticket(client, auth):
    before = client.get("/api/v1/blindbox", headers=auth).json()["tickets"]
    r = client.post("/api/v1/wishes", json={"content": "希望增加化学方程式的配平练习"}, headers=auth)
    assert r.status_code == 200
    d = r.json()
    assert d["bonus"] == 1
    assert d["left_today"] == 2
    after = client.get("/api/v1/blindbox", headers=auth).json()["tickets"]
    assert after == before + 1


def test_wish_daily_limit_three(client, auth):
    for i in range(3):
        r = client.post("/api/v1/wishes", json={"content": f"第 {i} 条改进意见内容"}, headers=auth)
        assert r.status_code == 200, r.text
    r4 = client.post("/api/v1/wishes", json={"content": "第四条意见应该被拒绝"}, headers=auth)
    assert r4.status_code == 400
    assert "已经提了" in r4.json()["detail"]


def test_wish_too_short(client, auth):
    r = client.post("/api/v1/wishes", json={"content": "短"}, headers=auth)
    assert r.status_code == 400
    assert "太短" in r.json()["detail"]


def test_wish_dedup(client, auth):
    text = "希望错题本支持导出成 PDF 方便打印"
    assert client.post("/api/v1/wishes", json={"content": text}, headers=auth).status_code == 200
    r = client.post("/api/v1/wishes", json={"content": text}, headers=auth)
    assert r.status_code == 400
    assert "提过了" in r.json()["detail"]


def test_wall_lists_and_marks_mine(client, auth):
    client.post("/api/v1/wishes", json={"content": "希望首页显示本周学习时长统计"}, headers=auth)
    d = client.get("/api/v1/wishes", headers=auth).json()
    assert d["per_day"] == 3
    assert d["ticket_reward"] == 1
    assert len(d["items"]) == 1
    assert d["items"][0]["mine"] is True
    assert d["items"][0]["status"] == "open"
    assert d["left_today"] == 2


def test_admin_wish_moderation(client):
    _make_account("dad", "123456", "爸爸", role="admin")
    dad = _login(client, "dad")
    r = client.post("/api/v1/session")
    kid = {"Authorization": f"Bearer {r.json()['token']}"}
    wid = client.post("/api/v1/wishes", json={"content": "希望增加错题重做的计时器"},
                      headers=kid).json()["id"]

    lst = client.get("/api/v1/admin/wishes", headers=dad)
    assert lst.status_code == 200
    assert any(item["id"] == wid for item in lst.json()["items"])

    r2 = client.patch(f"/api/v1/admin/wishes/{wid}",
                      json={"status": "planned", "reply": "已排期，下个版本做"}, headers=dad)
    assert r2.status_code == 200
    assert r2.json()["status"] == "planned"
    assert r2.json()["reply"] == "已排期，下个版本做"

    wall = client.get("/api/v1/wishes", headers=kid).json()
    assert wall["items"][0]["reply"] == "已排期，下个版本做"


def test_admin_wish_requires_admin(client, auth):
    assert client.get("/api/v1/admin/wishes", headers=auth).status_code == 403
    r = client.patch("/api/v1/admin/wishes/w_x", json={"status": "done"}, headers=auth)
    assert r.status_code == 403


def test_admin_wish_invalid_status(client):
    _make_account("dad", "123456", "爸爸", role="admin")
    dad = _login(client, "dad")
    r = client.post("/api/v1/session")
    kid = {"Authorization": f"Bearer {r.json()['token']}"}
    wid = client.post("/api/v1/wishes", json={"content": "希望支持夜间模式"},
                      headers=kid).json()["id"]
    r2 = client.patch(f"/api/v1/admin/wishes/{wid}", json={"status": "nope"}, headers=dad)
    assert r2.status_code == 400


# ---------- 迁移 ----------

def test_v7_to_v8_migration(tmp_path, monkeypatch):
    """老库（v7）升级后应有盲盒字段与两张新表，且默认发体验券。"""
    import sqlite3
    dbfile = tmp_path / "old.db"
    conn = sqlite3.connect(dbfile)
    conn.executescript("""
    CREATE TABLE schema_version (id INTEGER PRIMARY KEY CHECK (id=1), version INTEGER NOT NULL);
    INSERT INTO schema_version(id, version) VALUES (1, 7);
    CREATE TABLE users (
        id TEXT PRIMARY KEY, token_hash TEXT NOT NULL UNIQUE, sync_code TEXT NOT NULL UNIQUE,
        nickname TEXT NOT NULL DEFAULT 'sunny', username TEXT, password_hash TEXT,
        points INTEGER NOT NULL DEFAULT 0, streak INTEGER NOT NULL DEFAULT 0, last_checkin TEXT,
        tickets INTEGER NOT NULL DEFAULT 0, shards INTEGER NOT NULL DEFAULT 0,
        pity_sr INTEGER NOT NULL DEFAULT 0, pity_ssr INTEGER NOT NULL DEFAULT 0,
        makeup_used INTEGER NOT NULL DEFAULT 0, makeup_month TEXT, role TEXT,
        created_at TEXT NOT NULL, last_seen TEXT NOT NULL);
    INSERT INTO users(id, token_hash, sync_code, created_at, last_seen)
        VALUES ('u_old','th','sc','2026-01-01','2026-01-01');
    """)
    conn.commit()
    conn.close()

    monkeypatch.setattr(db, "DB_PATH", dbfile)
    db.init_db()

    with db.ro() as c:
        cols = {r["name"] for r in c.execute("PRAGMA table_info(users)").fetchall()}
        assert {"blindbox_tickets", "bb_pity_sr", "bb_pity_ssr"} <= cols
        row = c.execute("SELECT blindbox_tickets, bb_pity_sr FROM users WHERE id='u_old'").fetchone()
        assert row["blindbox_tickets"] == 3, "老用户补 3 张体验券"
        assert row["bb_pity_sr"] == 0
        tables = {r["name"] for r in c.execute(
            "SELECT name FROM sqlite_master WHERE type='table'").fetchall()}
        assert {"blindbox_owned", "wishes"} <= tables
        assert c.execute("SELECT version FROM schema_version WHERE id=1").fetchone()["version"] == db.SCHEMA_VERSION

    # 幂等：再跑一次不报错
    db.init_db()


def test_svg_assets_exist(client):
    """盲盒 SVG 必须真实存在且可访问（前端直接引用，缺一个就是破图）。"""
    chars = content_loader.blindbox_characters()["characters"]
    assert len(chars) == 8
    for ch in chars:
        assert ch["image"].endswith(".svg")
    r = client.get(f"/assets/blindbox/{chars[0]['image']}")
    assert r.status_code == 200
    assert "svg" in r.headers.get("content-type", "")
    assert client.get("/assets/blindbox/box.svg").status_code == 200
