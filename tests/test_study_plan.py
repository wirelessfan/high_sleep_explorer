"""Isolated Sunny term plan: real identity, calendar, scope and actual accounting."""
from datetime import date
from concurrent.futures import ThreadPoolExecutor
import json

import pytest
from fastapi.testclient import TestClient
from app import auth, content_loader, db
from app.main import app
from app.routers.session import _issue_session
from app.services import study_plan, scoring, wrongbook


@pytest.fixture()
def setup(tmp_path, monkeypatch):
    monkeypatch.setattr(db, 'DB_PATH', tmp_path/'study.db')
    monkeypatch.setattr(study_plan, 'today', lambda: date(2026,11,15))
    content_loader.clear_cache()
    with TestClient(app) as client:
        h = {}
        with db.tx() as conn:
            for name, username in [('sunny','sunny'), ('mom','mom'), ('fake',None), ('student','classmate01')]:
                conn.execute('INSERT INTO users(id,token_hash,sync_code,username,nickname,created_at,last_seen) VALUES(?,?,?,?,?,?,?)',
                    (name,auth.hash_token(name),name,username,'sunny','2026-11-15','2026-11-15'))
                _issue_session(conn,name,name)
                h[name]={'Authorization':'Bearer '+name}
        yield client,h
    content_loader.clear_cache()


def submit(client,h,topic='math-log',sid='quick',tier='basic'):
    content = content_loader.tier_content(next(s for s in content_loader.topic(topic)['sections'] if s['id']==sid), tier)
    answers={key:q['answer'] for key,q in wrongbook.questions_of(content).items()}
    r=client.post(f'/api/v1/topics/{topic}/sections/{sid}/submit?tier={tier}',headers=h,json={'answers':answers})
    assert r.status_code==200, r.text
    return r.json()


@pytest.mark.parametrize('day,active,mult,phase', [
    ('2026-11-14',False,1,None),('2026-11-15',True,2,'foundation'),
    ('2026-12-01',True,2,'improve'),('2026-12-21',True,2,'review'),
    ('2026-12-31',True,2,'review'),('2027-01-01',False,1,None)])
def test_calendar_boundaries(setup,monkeypatch,day,active,mult,phase):
    monkeypatch.setattr(study_plan,'today',lambda:date.fromisoformat(day))
    client,h=setup
    plan=client.get('/api/v1/catalog',headers=h['sunny']).json()['study_plan']
    assert plan['active']==active and plan['points_multiplier']==mult
    assert plan['phase'].get('id')==phase
    r=submit(client,h['sunny'])
    assert r['points']==15*mult


@pytest.mark.parametrize('name,mult',[('sunny',2),('mom',1),('fake',1),('student',1)])
def test_real_username_required_and_tier_stacks(setup,name,mult):
    client,h=setup
    r=submit(client,h[name],tier='advanced')
    assert r['points']==round(15*1.3)*mult
    assert client.get('/api/v1/me',headers=h[name]).json()['points']==r['points']
    assert bool(client.get('/api/v1/catalog',headers=h[name]).json()['study_plan'])==(name=='sunny')


@pytest.mark.parametrize('tid,sid,tier,mult',[
    ('physics-kinematics','quick','advanced',1), # contains projectile
    ('physics-kinematics','quick','expert',2),
    ('physics-newton','basic','expert',1), # circular motion + heat
    ('physics-newton','boss','expert',2),
    ('chemistry-ionic','quick','advanced',1), # Ksp
    ('chemistry-ionic','boss','advanced',2),
    ('chemistry-periodic','basic','advanced',1), # ionization energies
    ('chemistry-periodic','boss','advanced',2),
    ('physics-energy','quick','basic',1),
    ('math-derivative','quick','basic',1)])
def test_unit_scope_drives_actual_rewards(setup,tid,sid,tier,mult):
    client,h=setup
    r=submit(client,h['sunny'],tid,sid,tier)
    assert r['points']==round(scoring.section_points(sid)*scoring.tier_multiplier(tier))*mult
    assert r['study_reward']['points_multiplier']==mult
    if sid=='boss':
        assert r['topic_reward']['tickets']==mult
        assert r['total_tickets']==mult
        assert submit(client,h['sunny'],tid,sid,tier)['topic_reward']['tickets']==0


def test_review_cap_uses_base_units_and_legacy_events(setup):
    client,h=setup
    assert submit(client,h['sunny'])['points']==30
    with db.tx() as conn:
        scoring._log_event(conn,'sunny','legacy-review','review',{'points':2})
    earned=[submit(client,h['sunny'])['points'] for _ in range(8)]
    assert sum(earned)==36 and earned[-1]==0
    with db.ro() as conn:
        payloads=[json.loads(r[0]) for r in conn.execute("SELECT payload FROM events WHERE user_id='sunny' AND kind='review'")]
    assert sum(p.get('base_points',p['points']) for p in payloads)==20


def test_mixed_review_quota_and_noncore_rewards(setup):
    client,h=setup
    submit(client,h['sunny'])
    submit(client,h['sunny'],'physics-energy')
    earned=[submit(client,h['sunny'],'physics-energy')['points']]
    earned += [submit(client,h['sunny'])['points'] for _ in range(8)]
    assert sum(earned)==37 # 3 normal + 17 doubled


def test_boss_concurrent_first_reward_only_once(setup):
    client,h=setup
    with ThreadPoolExecutor(max_workers=4) as pool:
        results=list(pool.map(lambda _:submit(client,h['sunny'],sid='boss'), range(4)))
    assert sum(r['topic_reward']['tickets'] for r in results)==2
    assert sum(r['points']==100 for r in results)==1
    with db.ro() as conn:
        user=conn.execute("SELECT * FROM users WHERE id='sunny'").fetchone()
        assert user['tickets']==2 and user['points']==118 # first + three reviews


def test_topic_complete_balance_is_fresh_in_read_response(setup):
    client,h=setup
    tid='math-trig'
    with db.tx() as conn:
        for sid,tier in content_loader.topic_pairs(tid):
            if sid=='summary':continue
            conn.execute("INSERT INTO progress(user_id,topic_id,section_id,tier,status,awarded,updated_at) VALUES(?,?,?,?, 'done',1,'2026-11-15')",('sunny',tid,sid,tier))
    path=f'/api/v1/topics/{tid}/sections/summary/read'
    r=client.post(path,headers=h['sunny'],json={'confirmed':True}).json()
    assert r['topic_reward']['tickets']==4 and r['total_tickets']==4
    assert client.post(path,headers=h['sunny'],json={'confirmed':True}).json()['topic_reward']['tickets']==0


def test_recommendations_follow_progress_wrongbook_and_date_is_display_only(setup):
    client,h=setup
    plan=client.get('/api/v1/catalog',headers=h['sunny']).json()['study_plan']
    assert plan['date_estimated'] and plan['days_left']==46
    assert len(plan['recommendations'])==3
    rec=plan['recommendations'][0]
    submit(client,h['sunny'],rec['topic_id'],rec['section_id'],rec['tier'])
    updated=client.get('/api/v1/catalog',headers=h['sunny']).json()['study_plan']
    assert updated['done']==plan['done']+1 and updated['recommendations'][0]!=rec
    with db.tx() as conn:
        wrongbook.record_wrong(conn,'sunny',rec['topic_id'],rec['section_id'],rec['tier'],
            [{'id':'qtest','correct':False,'picked':1}],{'qtest':{'stem':'test','options':['a','b'],'answer':0,'explain':'test'}})
    updated=client.get('/api/v1/catalog',headers=h['sunny']).json()['study_plan']
    assert updated['recommendations'][0]['reason']=='先清理本单元错题'
    assert updated['recommendations'][0]['action']=='wrongbook'
    daily=client.get('/api/v1/daily?date=2030-01-01',headers=h['sunny']).json()
    assert daily['study_plan']['active'] and daily['study_plan']['days_left']==46
    assert daily['topic']['id']==updated['recommendations'][0]['topic_id']
    assert submit(client,h['sunny'],sid='boss')['points']==100


def test_config_units_exist_and_excluded_material_stays_out():
    cfg=content_loader.study_plan()
    for tid,info in cfg['topics'].items():
        declared={(sid,tier) for tier,sids in info['units'].items() for sid in sids}
        assert declared==set(study_plan.pairs(tid))
        assert any(tier!='basic' for _,tier in declared) or tid=='math-trig'
    for tid,info in cfg['topics'].items():
        for sid,tier in study_plan.pairs(tid):
            sec=next(s for s in content_loader.topic(tid)['sections'] if s['id']==sid)
            blob=json.dumps(content_loader.tier_content(sec,tier),ensure_ascii=False)
            assert not any(word in blob for word in ['Ksp','平抛','向心力','电离能','导数'])


def test_historical_identity_and_unrelated_rewards_do_not_get_bonus(setup):
    client,h=setup
    r=client.post('/api/v1/checkin',headers=h['sunny']).json()
    assert r['points']==10
    with db.tx() as conn:
        conn.execute("UPDATE users SET account_status='historical' WHERE id='sunny'")
    assert client.get('/api/v1/catalog',headers=h['sunny']).json()['study_plan'] is None
    assert submit(client,h['sunny'])['points']==15


def test_next_unit_skips_out_of_scope_and_daily_counts_only_core(setup):
    client,h=setup
    r=submit(client,h['sunny'],sid='basic',tier='advanced')
    assert (r['next_section'],r['next_tier'])==('hard','advanced')
    daily=client.get('/api/v1/daily',headers=h['sunny']).json()
    assert daily['topic']['total']==len(study_plan.pairs(daily['topic']['id']))


def test_display_date_cannot_reenable_expired_plan(setup,monkeypatch):
    client,h=setup
    monkeypatch.setattr(study_plan,'today',lambda:date(2027,1,1))
    daily=client.get('/api/v1/daily?date=2026-11-15',headers=h['sunny']).json()
    assert not daily['study_plan']['active']
    assert submit(client,h['sunny'],sid='boss')['topic_reward']['tickets']==1
