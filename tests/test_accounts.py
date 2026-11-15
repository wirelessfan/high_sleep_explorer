"""Identity is independent of nicknames; registration and migration preserve ownership."""
from concurrent.futures import ThreadPoolExecutor

import pytest
from starlette.testclient import TestClient

from app import auth, db
from app.main import app
from app.routers.session import _issue_session
from app.services import accounts, ratelimit


@pytest.fixture()
def setup(tmp_path,monkeypatch):
    monkeypatch.setattr(db,'DB_PATH',tmp_path/'accounts.db')
    ratelimit.reset()
    with TestClient(app) as client:
        headers={}
        with db.tx() as conn:
            for name,role in [('dad','admin'),('mom',None),('sunny',None)]:
                conn.execute('INSERT INTO users(id,token_hash,sync_code,username,nickname,password_hash,role,created_at,last_seen) VALUES(?,?,?,?,?,?,?,?,?)',
                    (name,auth.hash_token(name),name,name,name,auth.hash_password('family-password'),role,'2026-11-11','2026-11-11'))
                _issue_session(conn,name,name)
                headers[name]={'Authorization':'Bearer '+name}
        yield client,headers


def student_body(**changes):
    return {'username':'classmate01','nickname':'小明','password':'student-password',**changes}


def test_five_groups_hide_visitors_and_repeated_nicknames_from_formal_accounts(setup):
    client,h=setup
    for _ in range(3):
        guest=client.post('/api/v1/session').json()
        assert guest['nickname']=='访客' and guest['account_type']=='guest'
        with db.tx() as conn:
            conn.execute("UPDATE users SET nickname='sunny' WHERE id=?",(guest['id'],))
    data=client.get('/api/v1/admin/users',headers=h['dad']).json()
    assert [g['type'] for g in data['groups']]==['dad','mom','sunny','student','guest']
    assert data['registered_count']==3 and data['guest_count']==3 and data['historical_count']==0
    assert {u['username'] for u in data['users']}=={'dad','mom','sunny'}


def test_individual_students_login_have_separate_progress_and_not_publicly_listed(setup):
    client,h=setup
    tokens=[]
    for name in ['classmate01','classmate02']:
        created=client.post('/api/v1/admin/students',headers=h['dad'],json=student_body(username=name))
        assert created.status_code==200 and not created.json()['is_admin']
        login=client.post('/api/v1/session/login',json={'username':name.upper(),'password':'student-password','account_type':'student'})
        assert login.status_code==200 and login.json()['account_type']=='student'
        tokens.append({'Authorization':'Bearer '+login.json()['token']})
    client.post('/api/v1/checkin',headers=tokens[0])
    assert client.get('/api/v1/me',headers=tokens[0]).json()['points']==10
    assert client.get('/api/v1/me',headers=tokens[1]).json()['points']==0
    public=client.get('/api/v1/session/users').json()['users']
    assert {u['username'] for u in public}=={'dad','mom','sunny'}
    assert client.get('/api/v1/admin/users',headers=tokens[0]).status_code==403
    assert client.post('/api/v1/session/login',json={'username':'dad','password':'family-password','account_type':'student'}).status_code==401


@pytest.mark.parametrize('changes',[
    {'username':'SUNNY'},{'username':' guest '},{'username':'student'},
    {'username':'a/b'},{'username':'ab'},{'nickname':' '},{'password':' '*8},
])
def test_student_validation_does_not_create_or_modify_accounts(setup,changes):
    c,h=setup
    r=c.post('/api/v1/admin/students',headers=h['dad'],json=student_body(**changes))
    assert r.status_code in (400,422)
    with db.ro() as conn:
        assert conn.execute('SELECT count(*) FROM users').fetchone()[0]==3


def test_permission_extra_role_injection_and_duplicate_name_rejected(setup):
    c,h=setup
    for headers,expected in [({},401),(h['sunny'],403),(h['mom'],403)]:
        assert c.post('/api/v1/admin/students',headers=headers,json=student_body()).status_code==expected
    assert c.post('/api/v1/admin/students',headers=h['dad'],json=student_body(role='admin')).status_code==422
    assert c.post('/api/v1/admin/students',headers=h['dad'],json=student_body()).status_code==200
    assert c.post('/api/v1/admin/students',headers=h['dad'],json=student_body(username='CLASSMATE01')).status_code==400


def test_legacy_migration_preserves_data_sessions_and_does_not_guess_sunny_owner(setup):
    c,h=setup
    old=c.post('/api/v1/session').json()
    oh={'Authorization':'Bearer '+old['token']}
    with db.tx() as conn:
        conn.execute("UPDATE users SET nickname='sunny',points=71,blindbox_tickets=8 WHERE id=?",(old['id'],))
        conn.execute('UPDATE schema_version SET version=11')
        before=tuple(conn.execute('SELECT * FROM users WHERE id=?',(old['id'],)).fetchone())
        session=tuple(conn.execute('SELECT * FROM sessions WHERE user_id=?',(old['id'],)).fetchone())
    db.init_db();db.init_db()
    with db.ro() as conn:
        after=tuple(conn.execute('SELECT * FROM users WHERE id=?',(old['id'],)).fetchone())
        cols=[r['name'] for r in conn.execute('PRAGMA table_info(users)')]
        assert all(a==b for i,(a,b) in enumerate(zip(before,after)) if cols[i]!='account_status')
        assert tuple(conn.execute('SELECT * FROM sessions WHERE user_id=?',(old['id'],)).fetchone())==session
    assert c.get('/api/v1/me',headers=oh).json()['is_historical']
    data=c.get('/api/v1/admin/users',headers=h['dad']).json()
    assert data['registered_count']==3 and data['historical_count']==1
    assert data['historical_users'][0]['id']==old['id']
    new=c.post('/api/v1/session').json()
    db.init_db()
    assert not c.get('/api/v1/me',headers={'Authorization':'Bearer '+new['token']}).json()['is_historical']


def test_confirmed_legacy_registration_keeps_user_id_rewards_and_learning_records(setup):
    c,h=setup
    old=c.post('/api/v1/session').json()
    with db.tx() as conn:
        conn.execute("UPDATE users SET account_status='historical',points=71,blindbox_tickets=8 WHERE id=?",(old['id'],))
        conn.execute("INSERT INTO progress(user_id,topic_id,section_id,status,updated_at) VALUES(?,'math-log','quick','done','2026-11-15')",(old['id'],))
    r=c.post('/api/v1/admin/students',headers=h['dad'],json=student_body(legacy_user_id=old['id']))
    assert r.status_code==200 and r.json()['id']==old['id']
    assert c.get('/api/v1/me',headers={'Authorization':'Bearer '+old['token']}).status_code==401
    assert c.post('/api/v1/session/adopt',json={'sync_code':old['sync_code']}).status_code==404
    login=c.post('/api/v1/session/login',json={'username':'classmate01','password':'student-password'}).json()
    assert login['points']==71 and login['account_type']=='student'
    with db.ro() as conn:
        assert conn.execute('SELECT blindbox_tickets FROM users WHERE id=?',(old['id'],)).fetchone()[0]==8
        assert conn.execute('SELECT count(*) FROM progress WHERE user_id=?',(old['id'],)).fetchone()[0]==1
    assert c.post('/api/v1/admin/students',headers=h['dad'],json=student_body(username='classmate02',legacy_user_id=old['id'])).status_code==400
    assert c.get('/api/v1/me',headers=h['sunny']).json()['points']==0


def test_cannot_claim_family_or_current_guest_record(setup):
    c,h=setup
    guest=c.post('/api/v1/session/guest').json()
    for uid in ['dad','sunny',guest['id'],'missing']:
        assert c.post('/api/v1/admin/students',headers=h['dad'],json=student_body(legacy_user_id=uid)).status_code==400


def test_concurrent_registration_uses_one_identity(setup):
    def attempt(_):
        try:
            with db.tx() as conn:
                accounts.create_student(conn,'classmate01','小明','student-password','dad')
            return True
        except ValueError:
            return False
    with ThreadPoolExecutor(max_workers=2) as pool:
        assert sum(pool.map(attempt,range(2)))==1


def test_seed_is_idempotent_preserving_passwords_and_sessions(setup):
    from tools.seed_users import upsert_user
    c,h=setup
    with db.tx() as conn:
        before=tuple(conn.execute("SELECT * FROM users WHERE id='dad'").fetchone())
        uid,_=upsert_user(conn,'dad',None,'新昵称')
        assert uid=='dad'
        assert tuple(conn.execute("SELECT * FROM users WHERE id='dad'").fetchone())==before
    assert c.get('/api/v1/me',headers=h['dad']).status_code==200


def test_visitors_are_isolated_and_cannot_gift_or_cash_demo_rewards(setup):
    c,h=setup
    first=c.post('/api/v1/session/guest').json()
    second=c.post('/api/v1/session/guest').json()
    assert first['id']!=second['id'] and first['is_guest'] and second['is_guest']
    fh={'Authorization':'Bearer '+first['token']};sh={'Authorization':'Bearer '+second['token']}
    c.post('/api/v1/checkin',headers=fh)
    assert c.get('/api/v1/me',headers=sh).json()['points']==260
    card=c.post('/api/v1/achievements/daily/draw',headers=fh).json()['card']
    assert not c.get('/api/v1/achievements/daily',headers=fh).json()['gift_target_exists']
    assert c.post('/api/v1/achievements/gift',headers=fh,json={'card_id':card['id'],'to_username':'sunny'}).status_code==400
    assert c.post('/api/v1/achievements/verify',headers=h['dad'],json={'code':card['code']}).status_code==400
    assert c.post('/api/v1/admin/students',headers=fh,json=student_body()).status_code==403
    assert c.post('/api/v1/session/password',headers=fh,json={'old_password':'unused','new_password':'new-password'}).status_code==403
