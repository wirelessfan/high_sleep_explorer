"""Seven-day sessions: independent devices, expiry, revocation, and legacy migration."""
import time

import pytest
from starlette.testclient import TestClient

from app import auth, db
from app.main import app
from app.services import ratelimit


@pytest.fixture()
def client(tmp_path, monkeypatch):
    monkeypatch.setattr(db, 'DB_PATH', tmp_path / 'sessions.db')
    ratelimit.reset()
    with TestClient(app) as client:
        with db.tx() as conn:
            conn.execute('INSERT INTO users(id,token_hash,sync_code,username,password_hash,created_at,last_seen) '
                         'VALUES(?,?,?,?,?,?,?)',
                         ('test-sunny', auth.hash_token('unissued-token'), auth.normalize_sync_code(auth.new_sync_code()), 'sunny',
                          auth.hash_password('test-password'), '2026-11-14', '2026-11-14'))
        yield client


def login(client):
    response = client.post('/api/v1/session/login', json={'username': 'sunny', 'password': 'test-password'})
    assert response.status_code == 200
    data = response.json()
    return {'Authorization': 'Bearer ' + data['token']}, data


def test_devices_keep_separate_seven_day_logins(client):
    start = time.time()
    first, data1 = login(client)
    second, data2 = login(client)
    for headers, data in [(first, data1), (second, data2)]:
        assert start + 7*86400 <= data['session_expires_at'] <= time.time() + 7*86400
        response = client.get('/api/v1/me', headers=headers)
        assert response.status_code == 200
        assert response.json()['session_expires_at'] == data['session_expires_at']
    assert data1['token'] != data2['token']
    with db.ro() as conn:
        assert conn.execute('SELECT count(*) FROM sessions WHERE user_id=?', ('test-sunny',)).fetchone()[0] == 2


def test_deadline_is_fixed_and_expiry_enforced(client, monkeypatch):
    from app.routers import session
    headers, data = login(client)
    monkeypatch.setattr(session.time, 'time', lambda: data['session_expires_at'] - 1)
    assert client.get('/api/v1/me', headers=headers).status_code == 200
    monkeypatch.setattr(session.time, 'time', lambda: data['session_expires_at'])
    assert client.get('/api/v1/me', headers=headers).status_code == 401
    assert client.post('/api/v1/checkin', headers=headers).status_code == 401


def test_logout_revokes_only_this_device_and_survives_restart(client):
    first, _ = login(client)
    second, _ = login(client)
    assert client.post('/api/v1/session/logout', headers=first).status_code == 200
    db.init_db()
    assert client.get('/api/v1/me', headers=first).status_code == 401
    assert client.get('/api/v1/me', headers=second).status_code == 200


def test_password_change_revokes_other_devices(client):
    first, _ = login(client)
    second, _ = login(client)
    response = client.post('/api/v1/session/password', headers=second,
                           json={'old_password': 'test-password', 'new_password': 'changed-password'})
    assert response.status_code == 200
    assert client.get('/api/v1/me', headers=first).status_code == 401
    assert client.get('/api/v1/me', headers=second).status_code == 200


def test_adoption_and_guest_sessions_dont_invalidate_other_devices(client):
    first, data = login(client)
    adopted = client.post('/api/v1/session/adopt', json={'sync_code': data['sync_code']}).json()
    assert client.get('/api/v1/me', headers=first).status_code == 200
    assert client.get('/api/v1/me', headers={'Authorization': 'Bearer '+adopted['token']}).status_code == 200
    guest1 = client.post('/api/v1/session/guest').json()
    guest2 = client.post('/api/v1/session/guest').json()
    for guest in [guest1, guest2]:
        assert client.get('/api/v1/me', headers={'Authorization': 'Bearer '+guest['token']}).status_code == 200


def test_v9_migration_preserves_tokens_without_renewing_on_restart(client):
    with db.tx() as conn:
        conn.execute('UPDATE schema_version SET version=9')
        conn.execute('DELETE FROM sessions')
    before = time.time()
    db.init_db()
    with db.ro() as conn:
        saved = conn.execute('SELECT * FROM sessions WHERE user_id=?', ('test-sunny',)).fetchone()
    assert saved['expires_at'] >= before + 7*86400
    headers = {'Authorization': 'Bearer unissued-token'}
    assert client.get('/api/v1/me', headers=headers).status_code == 200
    db.init_db()
    with db.ro() as conn:
        again = conn.execute('SELECT * FROM sessions WHERE user_id=?', ('test-sunny',)).fetchone()
    assert again['expires_at'] == saved['expires_at']
    client.post('/api/v1/session/logout', headers=headers)
    db.init_db()
    assert client.get('/api/v1/me', headers=headers).status_code == 401
