"""Daily blind-box grants use one Beijing date and remain atomic across devices."""
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone

import pytest
from starlette.testclient import TestClient

from app import db
from app.main import app
from app.services import blindbox, ratelimit


@pytest.fixture()
def account(tmp_path, monkeypatch):
    monkeypatch.setattr(db, 'DB_PATH', tmp_path/'daily.db')
    ratelimit.reset()
    with TestClient(app) as client:
        data = client.post('/api/v1/session').json()
        yield client, data, {'Authorization': 'Bearer '+data['token']}


def test_initial_three_are_first_day_quota_not_six(account):
    client, data, headers = account
    for _ in range(2):
        state = client.get('/api/v1/blindbox', headers=headers).json()
        assert state['tickets'] == 3
        assert state['daily']['tickets'] == 3
        assert state['daily']['timezone'] == 'Asia/Shanghai'
    with db.ro() as conn:
        assert conn.execute("SELECT count(*) FROM events WHERE user_id=? AND kind='bbox_daily'", (data['id'],)).fetchone()[0] == 1


def test_next_day_once_across_sessions_without_relogin(account, monkeypatch):
    client, data, first = account
    day = blindbox._today()
    with db.tx() as conn:
        conn.execute('UPDATE users SET blindbox_tickets=0 WHERE id=?', (data['id'],))
    second_token = client.post('/api/v1/session/adopt', json={'sync_code':data['sync_code']}).json()['token']
    second = {'Authorization':'Bearer '+second_token}
    from datetime import date, timedelta
    tomorrow = (date.fromisoformat(day)+timedelta(days=1)).isoformat()
    monkeypatch.setattr(blindbox, '_today', lambda:tomorrow)
    assert client.get('/api/v1/blindbox', headers=first).json()['tickets'] == 3
    assert client.get('/api/v1/blindbox', headers=second).json()['tickets'] == 3
    db.init_db()
    assert client.get('/api/v1/blindbox', headers=first).json()['tickets'] == 3


def test_direct_draw_gets_new_day_grant_and_replay_doesnt_repeat(account, monkeypatch):
    client, data, headers = account
    monkeypatch.setattr(blindbox, '_today', lambda:'2099-01-02')
    monkeypatch.setattr(blindbox, '_roll_rarity', lambda *args:'N')
    with db.tx() as conn:
        conn.execute('UPDATE users SET blindbox_tickets=0 WHERE id=?', (data['id'],))
    body = {'count':1,'idempotency_key':'new-day'}
    response = client.post('/api/v1/blindbox/draw', headers=headers, json=body)
    assert response.status_code == 200, response.text
    assert response.json()['tickets'] == 2
    assert client.post('/api/v1/blindbox/draw', headers=headers, json=body).json()['tickets'] == 2
    assert client.get('/api/v1/blindbox', headers=headers).json()['tickets'] == 2


def test_existing_users_keep_balance_and_unvisited_days_not_backfilled(account, monkeypatch):
    client, data, headers = account
    monkeypatch.setattr(blindbox, '_today', lambda:'2099-01-10')
    with db.tx() as conn:
        conn.execute('UPDATE users SET blindbox_tickets=7 WHERE id=?', (data['id'],))
    assert client.get('/api/v1/blindbox', headers=headers).json()['tickets'] == 10
    with db.ro() as conn:
        assert conn.execute("SELECT count(*) FROM events WHERE user_id=? AND kind='bbox_daily'", (data['id'],)).fetchone()[0] == 2


def test_concurrent_claims_credit_only_once(account, monkeypatch):
    _, data, _ = account
    monkeypatch.setattr(blindbox, '_today', lambda:'2099-01-03')
    def claim(_):
        with db.tx() as conn:
            return blindbox.grant_daily_tickets(conn, data['id'])['credited_now']
    with ThreadPoolExecutor(max_workers=4) as pool:
        credited = list(pool.map(claim, range(8)))
    assert sum(credited) == 3
    with db.ro() as conn:
        assert conn.execute('SELECT blindbox_tickets FROM users WHERE id=?', (data['id'],)).fetchone()[0] == 6


def test_beijing_midnight_independent_of_machine_timezone(monkeypatch):
    class Clock(datetime):
        instant = datetime(2026,11,14,15,59,59,tzinfo=timezone.utc)
        @classmethod
        def now(cls, tz=None):
            return cls.instant.astimezone(tz)
    monkeypatch.setattr(blindbox,'datetime',Clock)
    assert blindbox._today() == '2026-11-14'
    Clock.instant = datetime(2026,11,14,16,0,0,tzinfo=timezone.utc)
    assert blindbox._today() == '2026-11-15'


def test_daily_credit_and_marker_rollback_together(account, monkeypatch):
    _, data, _ = account
    monkeypatch.setattr(blindbox, '_today', lambda:'2099-01-04')
    with pytest.raises(RuntimeError):
        with db.tx() as conn:
            blindbox.grant_daily_tickets(conn,data['id'])
            raise RuntimeError('fail transaction')
    with db.tx() as conn:
        assert blindbox.grant_daily_tickets(conn,data['id'])['credited_now'] == 3
        assert conn.execute('SELECT blindbox_tickets FROM users WHERE id=?', (data['id'],)).fetchone()[0] == 6


def test_compensation_only_sunny_and_safe_to_repeat(account, monkeypatch):
    from tools.compensate_blindbox_daily import compensate, INCIDENT_DAY
    from app.services import events
    _, data, _ = account
    monkeypatch.setattr(blindbox, '_today', lambda: INCIDENT_DAY)
    with db.tx() as conn:
        conn.execute("UPDATE users SET username='sunny',points=9,blindbox_tickets=0 WHERE id=?", (data['id'],))
        conn.execute("DELETE FROM events WHERE user_id=? AND kind='bbox_daily'", (data['id'],))
        events.log(conn,data['id'],'exchange-fixture','bbox_exchange',{'points':100,'count':1})
        conn.execute("UPDATE events SET created_at=? WHERE user_id=? AND kind='bbox_exchange'", (INCIDENT_DAY+'T09:51:34',data['id']))
        preview = compensate(conn)
        assert preview['points_refund'] == 100
        assert conn.execute('SELECT blindbox_tickets FROM users WHERE id=?',(data['id'],)).fetchone()[0] == 0
        result = compensate(conn,apply=True)
        assert result['tickets_after'] == 6
        assert result['points_after'] == 109
        assert compensate(conn,apply=True)['replayed'] is True
        assert conn.execute('SELECT blindbox_tickets,points FROM users WHERE id=?',(data['id'],)).fetchone()[:] == (6,109)
