"""休闲广场每日额度：防沉迷限额、积分奖励、服务端权威计数。"""
from datetime import date, timedelta

import pytest
from starlette.testclient import TestClient

from app import db
from app.main import app
from app.routers import relax


@pytest.fixture()
def account(tmp_path, monkeypatch):
    monkeypatch.setattr(db, 'DB_PATH', tmp_path / 'quota.db')
    monkeypatch.setattr(relax, '_today', lambda: '2026-11-18')  # 周三 → 平日 10 次
    db.init_db()
    with TestClient(app) as client:
        data = client.post('/api/v1/session').json()
        yield client, data, {'Authorization': 'Bearer ' + data['token']}


def test_base_quota_by_day_type():
    assert relax.day_type('2026-11-18') == 'weekday'   # 周三
    assert relax.day_type('2026-11-19') == 'weekday'   # 周四（回归平日）
    assert relax.day_type('2026-11-21') == 'crazy-saturday'  # 疯狂星期六
    assert relax.day_type('2026-11-22') == 'weekend'   # 周日
    assert relax.day_type('2026-10-01') == 'holiday'   # 国庆
    assert relax.day_type('2026-10-10') == 'weekday'   # 调休上班的周六
    assert relax.base_limit('2026-11-18') == 10
    assert relax.base_limit('2026-11-19') == 10
    assert relax.base_limit('2026-11-21') == 20
    assert relax.base_limit('2026-11-22') == 20


def test_weekday_base_is_ten_without_points(account):
    client, _, headers = account
    q = client.get('/api/v1/relax/quota', headers=headers).json()
    assert q['base'] == 10
    assert q['bonus'] == 0
    assert q['total'] == 10
    assert q['used'] == 0
    assert q['remaining'] == 10


def test_points_grant_bonus_without_deducting_points(account):
    client, data, headers = account
    with db.tx() as conn:
        conn.execute("INSERT INTO checkins(user_id,day,points,streak) VALUES(?,?,?,?)",
                     (data['id'], '2026-11-18', 25, 1))
        conn.execute("UPDATE users SET points=points+25 WHERE id=?", (data['id'],))
    q = client.get('/api/v1/relax/quota', headers=headers).json()
    assert q['earned_points'] == 25
    assert q['bonus'] == 2
    assert q['total'] == 12
    assert q['next_bonus_in'] == 5


def test_consumption_is_limited_and_idempotent(account):
    client, _, headers = account
    # 平日 10 次：十连正好用满，允许
    r = client.post('/api/v1/relax/quota/consume', headers=headers,
                    json={'count': 10, 'idempotency_key': 'ten'})
    assert r.status_code == 200, r.text
    q = client.get('/api/v1/relax/quota', headers=headers).json()
    assert q['used'] == 10 and q['remaining'] == 0

    # 用完后再抽被拒
    r = client.post('/api/v1/relax/quota/consume', headers=headers,
                    json={'count': 1, 'idempotency_key': 'over'})
    assert r.status_code == 409
    assert r.json()['detail']['quota']['remaining'] == 0

    # 重复提交已成功的 key：返回当前额度，不重复扣（used 仍为 10）
    r = client.post('/api/v1/relax/quota/consume', headers=headers,
                    json={'count': 1, 'idempotency_key': 'ten'})
    assert r.status_code == 200
    assert r.json()['used'] == 10


def test_prize_free_on_mon_wed_fri_sun_only(account):
    # 2026-11-20 是周五
    for day, free in (
        ('2026-11-16', 1),  # 周一
        ('2026-11-17', 0),  # 周二
        ('2026-11-18', 1),  # 周三
        ('2026-11-19', 0),  # 周四
        ('2026-11-20', 1),  # 周五
        ('2026-11-21', 0),  # 周六
        ('2026-11-22', 1),  # 周日
    ):
        with db.ro() as conn:
            p = relax.prize_quota_for(conn, 'u', day)
        assert p['free'] == free, day


def test_prize_points_threshold_grants_extra(account):
    client, data, headers = account
    with db.tx() as conn:
        conn.execute("INSERT INTO checkins(user_id,day,points,streak) VALUES(?,?,?,?)",
                     (data['id'], '2026-11-18', 99, 1))
    p = client.get('/api/v1/relax/quota', headers=headers).json()['prize']
    assert p['earned_points'] == 99
    assert p['points_bonus'] == 0
    assert p['next_in'] == 1
    assert p['total'] == 1 and p['remaining'] == 1

    with db.tx() as conn:
        conn.execute("UPDATE checkins SET points=100 WHERE user_id=? AND day=?",
                     (data['id'], '2026-11-18'))
    p = client.get('/api/v1/relax/quota', headers=headers).json()['prize']
    assert p['points_bonus'] == 1
    assert p['next_in'] == 0
    assert p['total'] == 2 and p['remaining'] == 2


def test_wrongbook_clear_counts_toward_quota(account):
    """清空错题 +20 分计入抽奖额度：最辛苦的学习行为不能白做。"""
    client, data, headers = account
    with db.tx() as conn:
        conn.execute(
            "INSERT INTO events(user_id,key,kind,payload,created_at) VALUES(?,?,?,?,?)",
            (data['id'], 'wrongbook_clear:physics-kinematics:2026-11-18',
             'wrongbook_clear', '{"topic":"physics-kinematics","points":20}', '2026-11-18'),
        )
    q = client.get('/api/v1/relax/quota', headers=headers).json()
    assert q['earned_points'] == 20
    assert q['bonus'] == 2
    assert q['next_bonus_in'] == 10


def test_prize_consumption_limited_and_idempotent(account):
    client, _, headers = account
    r = client.post('/api/v1/relax/prize/consume', headers=headers,
                    json={'idempotency_key': 'p0'})
    assert r.status_code == 200, r.text
    assert r.json()['prize']['used'] == 1
    assert r.json()['prize']['remaining'] == 0

    # 重复使用同一 key 不重复扣
    r = client.post('/api/v1/relax/prize/consume', headers=headers,
                    json={'idempotency_key': 'p0'})
    assert r.status_code == 200
    assert r.json()['prize']['used'] == 1

    # 用完后再抽被拒，普通抽卡额度不受影响
    r = client.post('/api/v1/relax/prize/consume', headers=headers,
                    json={'idempotency_key': 'p1'})
    assert r.status_code == 409
    q = r.json()['detail']['quota']
    assert q['prize']['remaining'] == 0
    assert q['remaining'] == 10


def _make_admin(client):
    from app import auth as a
    with db.tx() as conn:
        uid = a.new_id()
        conn.execute(
            "INSERT INTO users(id, token_hash, sync_code, nickname, username, "
            "password_hash, role, created_at, last_seen) VALUES (?,?,?,?,?,?,?,?,?)",
            (uid, a.hash_token(a.new_token()), a.normalize_sync_code(a.new_sync_code()),
             '管理员', 'dad', a.hash_password('123456'), 'admin',
             '2026-01-01T00:00:00', '2026-01-01T00:00:00'),
        )
    r = client.post('/api/v1/session/login', json={'username': 'dad', 'password': '123456'})
    assert r.status_code == 200
    return {'Authorization': 'Bearer ' + r.json()['token']}


def _grant(conn, uid, kind, amount, start, days=7):
    end = (date.fromisoformat(start) + timedelta(days=days - 1)).isoformat()
    conn.execute(
        "INSERT INTO relax_grant(user_id,kind,amount,used,start_day,end_day,created_at) "
        "VALUES(?,?,?,0,?,?,?)",
        (uid, kind, amount, start, end, '2026-01-01T00:00:00'),
    )


def test_granted_counts_toward_total(account):
    client, data, headers = account
    with db.tx() as conn:
        _grant(conn, data['id'], 'regular', 20, '2026-11-18')
        _grant(conn, data['id'], 'prize', 2, '2026-11-18')
    q = client.get('/api/v1/relax/quota', headers=headers).json()
    assert q['granted'] == 20 and q['grant_end'] == '2026-11-24'
    assert q['base'] == 10 and q['total'] == 30 and q['remaining'] == 30
    assert q['prize']['granted'] == 2
    assert q['prize']['total'] == 3 and q['prize']['remaining'] == 3


def test_admin_grant_endpoint(account):
    client, data, headers = account
    admin = _make_admin(client)
    # 非管理员被拒
    r = client.post('/api/v1/relax/quota/grant', headers=headers,
                    json={'user_id': data['id'], 'regular': 20, 'prize': 2})
    assert r.status_code == 403
    # 管理员赠送成功（默认 7 天）
    r = client.post('/api/v1/relax/quota/grant', headers=admin,
                    json={'user_id': data['id'], 'day': '2026-11-18', 'regular': 20, 'prize': 2})
    assert r.status_code == 200, r.text
    assert r.json()['granted'] == 20 and r.json()['total'] == 30
    assert r.json()['grant_end'] == '2026-11-24'
    assert r.json()['prize']['granted'] == 2 and r.json()['prize']['total'] == 3
    # 用户实际可用
    q = client.get('/api/v1/relax/quota', headers=headers).json()
    assert q['remaining'] == 30 and q['prize']['remaining'] == 3


def test_grant_valid_seven_days_then_expires(account):
    """赠送池 7 天内有效（含首尾），第 8 天失效，不再刷新。"""
    client, data, headers = account
    with db.tx() as conn:
        _grant(conn, data['id'], 'regular', 20, '2026-11-18', days=7)
        _grant(conn, data['id'], 'prize', 2, '2026-11-18', days=7)
    with db.ro() as conn:
        assert relax.grant_pool(conn, data['id'], 'regular', '2026-11-18')['remaining'] == 20
        assert relax.grant_pool(conn, data['id'], 'regular', '2026-11-24')['remaining'] == 20  # 末日仍有效
        assert relax.grant_pool(conn, data['id'], 'regular', '2026-11-25')['remaining'] == 0   # 第 8 天失效
        assert relax.grant_pool(conn, data['id'], 'prize', '2026-11-25')['remaining'] == 0


def test_grant_is_finite_across_days_not_refreshed(account, monkeypatch):
    """赠送池用完即止：跨天共享、不会每天重置。"""
    client, data, headers = account
    with db.tx() as conn:
        _grant(conn, data['id'], 'regular', 2, '2026-11-18')
    # 第一天（周三，基础 10）：先抽 10 次用掉当日基础，再抽 2 次扣赠送池
    assert client.post('/api/v1/relax/quota/consume', headers=headers,
                       json={'count': 10, 'idempotency_key': 'd1'}).status_code == 200
    r = client.post('/api/v1/relax/quota/consume', headers=headers,
                    json={'count': 2, 'idempotency_key': 'd2'})
    assert r.status_code == 200, r.text
    assert r.json()['granted'] == 0
    # 换到周六（疯狂星期六，基础 20）：基础额度恢复，但赠送池已耗尽，不再额外送 2 次
    monkeypatch.setattr(relax, '_today', lambda: '2026-11-21')
    q = client.get('/api/v1/relax/quota', headers=headers).json()
    assert q['base'] == 20 and q['granted'] == 0
    assert q['remaining'] == 20


def test_grant_carries_over_to_next_day(account, monkeypatch):
    """赠送池跨天保留：第一天没用完，第二天仍可继续用（不刷新、不重置）。"""
    client, data, headers = account
    with db.tx() as conn:
        _grant(conn, data['id'], 'regular', 20, '2026-11-18')
    # 第一天只抽 2 次，赠送池完全没动
    client.post('/api/v1/relax/quota/consume', headers=headers,
                json={'count': 2, 'idempotency_key': 'd1'})
    # 第二天：赠送池仍剩 20，可用 = 基础 20（疯狂星期六）+ 赠送 20
    monkeypatch.setattr(relax, '_today', lambda: '2026-11-21')
    q = client.get('/api/v1/relax/quota', headers=headers).json()
    assert q['granted'] == 20
    assert q['base'] == 20 and q['remaining'] == 40


def test_bonus_cap_prevents_unlimited_draws(account):
    client, data, headers = account
    with db.tx() as conn:
        conn.execute("INSERT INTO checkins(user_id,day,points,streak) VALUES(?,?,?,?)",
                     (data['id'], '2026-11-18', 1000, 1))
    q = client.get('/api/v1/relax/quota', headers=headers).json()
    assert q['bonus'] == relax.BONUS_CAP
    assert q['total'] == 10 + relax.BONUS_CAP


def test_gacha_state_roundtrip(account):
    """存档服务端备份：清缓存/换设备后可从服务端恢复。"""
    client, _, headers = account
    r = client.get('/api/v1/relax/gacha/state', headers=headers)
    assert r.status_code == 200 and r.json()['data'] is None
    r = client.put('/api/v1/relax/gacha/state', headers=headers,
                   json={'data': '{"counts":{"cotton-rabbit":1},"pityR":3}'})
    assert r.status_code == 200, r.text
    r = client.get('/api/v1/relax/gacha/state', headers=headers)
    assert r.json()['data'] == '{"counts":{"cotton-rabbit":1},"pityR":3}'
    assert r.json()['updated_at']
    # 非法 JSON 被拒
    r = client.put('/api/v1/relax/gacha/state', headers=headers, json={'data': 'not-json'})
    assert r.status_code == 422


def test_ledger_idempotent_redeem_and_exchange(account):
    """实体券台账：幂等上报、家长核销、3N→1R 合成阶梯。"""
    client, _, headers = account
    admin = _make_admin(client)
    # 非管理员看不到全员台账、不能核销
    assert client.get('/api/v1/relax/ledger/all', headers=headers).status_code == 403
    assert client.post('/api/v1/relax/ledger/redeem', headers=headers,
                       json={'ledger_id': 'x'}).status_code == 403

    entries = [
        {'prize_id': 'p-mai-dong', 'client_key': 'p:p-mai-dong:1001'},
        {'prize_id': 'p-an-mu-xi', 'client_key': 'p:p-an-mu-xi:1002'},
        {'prize_id': 'p-tang-hu-lu', 'client_key': 'p:p-tang-hu-lu:1003'},
        {'prize_id': 'p-hershey', 'client_key': 'p:p-hershey:1004'},
        {'prize_id': 'p-fake', 'client_key': 'p:p-fake:1005'},  # 未知奖励不记账
    ]
    r = client.post('/api/v1/relax/ledger', headers=headers, json={'entries': entries})
    assert r.status_code == 200 and r.json()['added'] == 4
    # 同 client_key 重传不重复记账（网络重试安全）
    r = client.post('/api/v1/relax/ledger', headers=headers, json={'entries': entries[:1]})
    assert r.json()['added'] == 0

    items = client.get('/api/v1/relax/ledger', headers=headers).json()['items']
    assert len(items) == 4
    n_ids = [i['id'] for i in items if i['rarity'] == 'N']
    assert len(n_ids) == 3

    # 合成：3 张 N 券 → 1 张自选 R 券（好时巧克力）
    r = client.post('/api/v1/relax/ledger/exchange', headers=headers,
                    json={'target': 'R', 'prize_id': 'p-hershey', 'keys': n_ids})
    assert r.status_code == 200, r.text
    assert r.json()['item']['prize_id'] == 'p-hershey'
    items = client.get('/api/v1/relax/ledger', headers=headers).json()['items']
    statuses = [i['status'] for i in items]
    assert statuses.count('spent') == 3 and statuses.count('held') == 2

    # 券数不够 / 拿 R 级券当 N 级原料 都被拒
    r = client.post('/api/v1/relax/ledger/exchange', headers=headers,
                    json={'target': 'R', 'prize_id': 'p-hershey', 'keys': n_ids})
    assert r.status_code == 409

    # 家长核销刚合成的券
    hershey = [i for i in items if i['status'] == 'held' and i['prize_id'] == 'p-hershey'][0]
    r = client.post('/api/v1/relax/ledger/redeem', headers=admin, json={'ledger_id': hershey['id']})
    assert r.status_code == 200, r.text
    items = client.get('/api/v1/relax/ledger', headers=headers).json()['items']
    assert [i['status'] for i in items if i['id'] == hershey['id']] == ['redeemed']

    # 家长台账能看到全部记录（含昵称）
    all_items = client.get('/api/v1/relax/ledger/all', headers=admin).json()['items']
    assert len(all_items) == len(items)
    assert 'nickname' in all_items[0]
