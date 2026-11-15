"""Report validation, visibility, terminal review and exactly-once 50 point awards."""
import json
from concurrent.futures import ThreadPoolExecutor

import pytest
from starlette.testclient import TestClient

from app import auth, content_loader, db
from app.main import app
from app.routers.session import _issue_session
from app.services import question_feedback as service, ratelimit, wrongbook


def test_chat_rewards_once_and_atomic(setup):
    from tools.record_sunny_feedback_rewards import record
    with db.tx() as conn:
        first=record(conn)
    assert (first['credited_points'],first['credited_tickets'])==(50,3)
    with db.tx() as conn:
        second=record(conn)
    assert (second['credited_points'],second['credited_tickets'])==(0,0)
    assert second['after']==first['after']
    assert points('other')==0
    with db.ro() as conn:
        assert conn.execute("SELECT blindbox_tickets FROM users WHERE id='other'").fetchone()[0]==3


def test_chat_rewards_roll_back_together(setup,monkeypatch):
    from tools.record_sunny_feedback_rewards import record
    from app.services import blindbox
    def fail(*args):
        raise RuntimeError('simulated write failure')
    monkeypatch.setattr(blindbox,'add_tickets',fail)
    with pytest.raises(RuntimeError),db.tx() as conn:
        record(conn)
    assert points()==0
    with db.ro() as conn:
        assert conn.execute('SELECT count(*) FROM question_feedback').fetchone()[0]==0
        assert conn.execute("SELECT count(*) FROM events WHERE kind IN ('feedback_bonus','question_feedback_reward')").fetchone()[0]==0


@pytest.fixture()
def setup(tmp_path,monkeypatch):
    monkeypatch.setattr(db,'DB_PATH',tmp_path/'feedback.db')
    ratelimit.reset()
    with TestClient(app) as client:
        headers={}
        with db.tx() as conn:
            for name,role in [('sunny',None),('other',None),('dad','admin'),('mom','admin'),('guest',None)]:
                conn.execute('INSERT INTO users(id,token_hash,sync_code,username,nickname,role,created_at,last_seen) VALUES(?,?,?,?,?,?,?,?)',
                             (name,auth.hash_token(name),name,name,name,role,'2026-01-01','2026-01-01'))
                _issue_session(conn,name,name)
                headers[name]={'Authorization':'Bearer '+name}
        q=content_loader.topic('chemistry-ionic')['sections'][0]['tiers']['advanced']['questions'][0]
        body={'topic_id':'chemistry-ionic','section_id':'quick','tier':'advanced','question_id':q['id'],
              'category':'incomplete','detail':'题干显示在不等式处截断了', 'displayed_stem':q['stem'],'displayed_options':q['options']}
        yield client,headers,body


def post(setup,name='sunny',**changes):
    c,h,body=setup
    r=c.post('/api/v1/question-feedback',headers=h[name],json={**body,**changes})
    assert r.status_code==200,r.text
    return r.json()


def points(name='sunny'):
    with db.ro() as conn:
        return conn.execute('SELECT points FROM users WHERE id=?',(name,)).fetchone()[0]


def test_report_pending_no_reward_hides_answer_and_is_private(setup):
    c,h,_=setup
    r=post(setup)
    assert r['item']['status']=='pending' and r['item']['reward_points']==0
    assert set(r['item']['question'])=={'stem','options'}
    assert points()==0
    assert len(c.get('/api/v1/question-feedback',headers=h['sunny']).json()['items'])==1
    assert c.get('/api/v1/question-feedback',headers=h['other']).json()['items']==[]
    item=c.get('/api/v1/admin/question-feedback',headers=h['dad']).json()['items'][0]
    assert item['question']['answer']==1 and item['question']['explain']


def test_approval_credits_owner_once_and_terminal_state_is_immutable(setup):
    c,h,_=setup
    rid=post(setup)['item']['id']
    url='/api/v1/admin/question-feedback/'+rid
    for admin,expected in [('dad',50),('mom',0),('dad',0)]:
        r=c.patch(url,headers=h[admin],json={'status':'approved','note':'已核验并修复显示问题'})
        assert r.status_code==200 and r.json()['rewarded_now']==expected
    assert points()==50 and points('dad')==0 and points('other')==0
    assert c.patch(url,headers=h['dad'],json={'status':'rejected','note':'改判'}).status_code==409
    with db.ro() as conn:
        assert conn.execute("SELECT count(*) FROM events WHERE kind='question_feedback_reward'").fetchone()[0]==1


def test_rejection_has_explanation_no_points_and_no_later_approval(setup):
    c,h,_=setup
    rid=post(setup)['item']['id'];url='/api/v1/admin/question-feedback/'+rid
    r=c.patch(url,headers=h['dad'],json={'status':'rejected','note':'经核算原答案正确'})
    assert r.status_code==200 and r.json()['rewarded_now']==0 and points()==0
    assert c.patch(url,headers=h['dad'],json={'status':'approved','note':'再次通过'}).status_code==409
    mine=c.get('/api/v1/question-feedback',headers=h['sunny']).json()['items'][0]
    assert mine['review_note']=='经核算原答案正确'


def test_duplicate_same_question_version_does_not_create_more_reports(setup):
    first=post(setup)
    second=post(setup,detail='换一种描述重复提交这道题',category='other')
    assert second['duplicate'] and first['item']['id']==second['item']['id']
    assert points()==0


def test_unauthorized_guest_and_normal_users_cannot_review_or_choose_rewards(setup):
    c,h,body=setup
    assert c.post('/api/v1/question-feedback',json=body).status_code==401
    assert c.post('/api/v1/question-feedback',headers=h['guest'],json=body).status_code==403
    anon=c.post('/api/v1/session').json()['token']
    assert c.post('/api/v1/question-feedback',headers={'Authorization':'Bearer '+anon},json=body).status_code==403
    for name in ['sunny','other','guest']:
        assert c.get('/api/v1/admin/question-feedback',headers=h[name]).status_code==403
        assert c.patch('/api/v1/admin/question-feedback/nonexistent',headers=h[name],json={'status':'approved','note':'通过'}).status_code==403
    assert c.post('/api/v1/question-feedback',headers=h['sunny'],json={**body,'reward_points':5000}).status_code==422


@pytest.mark.parametrize('change,expected',[
    ({'question_id':'missing'},404),({'topic_id':'../db'},404),({'section_id':'missing'},404),
    ({'displayed_stem':'伪造题目'},409),({'displayed_options':['假的A','假的B']},409),
    ({'detail':'     '},400),({'category':'fraud'},422),({'tier':'unknown'},422),
])
def test_invalid_or_stale_question_not_recorded(setup,change,expected):
    c,h,body=setup
    r=c.post('/api/v1/question-feedback',headers=h['sunny'],json={**body,**change})
    assert r.status_code==expected,r.text
    assert c.get('/api/v1/question-feedback',headers=h['sunny']).json()['items']==[]


def test_question_versions_are_independent(setup,monkeypatch):
    first=post(setup)
    original=service.resolve_question
    def revised(conn,uid,body):
        return {**original(conn,uid,body),'explain':'题目已修订的新解析'}
    monkeypatch.setattr(service,'resolve_question',revised)
    second=post(setup)
    assert not second['duplicate'] and second['item']['question_version']!=first['item']['question_version']


def test_concurrent_admins_only_award_fifty(setup):
    rid=post(setup)['item']['id']
    def approve(admin):
        with db.tx() as conn:
            return service.moderate(conn,rid,'approved','确认显示异常',admin)['rewarded_now']
    with ThreadPoolExecutor(max_workers=2) as pool:
        rewards=list(pool.map(approve,['dad','mom']))
    assert sum(rewards)==50 and points()==50


def test_reward_and_status_roll_back_together(setup):
    rid=post(setup)['item']['id']
    with pytest.raises(RuntimeError):
        with db.tx() as conn:
            service.moderate(conn,rid,'approved','确认显示异常','dad')
            raise RuntimeError('transaction interrupted')
    assert points()==0
    with db.tx() as conn:
        assert service.moderate(conn,rid,'approved','确认显示异常','dad')['rewarded_now']==50
    assert points()==50


def test_admin_cannot_approve_own_report(setup):
    c,h,_=setup
    rid=post(setup,'dad')['item']['id']
    assert c.patch('/api/v1/admin/question-feedback/'+rid,headers=h['dad'],json={'status':'approved','note':'自己通过'}).status_code==403


def test_historical_wrongbook_snapshot_can_be_reported_only_by_owner(setup):
    c,h,body=setup
    with db.tx() as conn:
        wrongbook.record_wrong(conn,'sunny','chemistry-ionic','quick','advanced',
                               [{'id':'old-q','correct':False,'picked':0}],
                               {'old-q':{'stem':'旧版完整题干0<k<1，请求上限','options':['a','b'],'answer':1,'explain':'原解析'}})
        row=conn.execute('SELECT * FROM wrong_questions').fetchone()
    b={**body,'question_id':row['question_id'],'wrong_question_id':row['id'],'displayed_stem':row['stem'],'displayed_options':json.loads(row['options_json'])}
    assert c.post('/api/v1/question-feedback',headers=h['other'],json=b).status_code==404
    r=c.post('/api/v1/question-feedback',headers=h['sunny'],json=b)
    assert r.status_code==200 and r.json()['item']['question']['stem']==row['stem']


def test_v10_upgrade_preserves_existing_session_and_records(setup):
    c,h,_=setup
    rid=post(setup)['item']['id']
    with db.tx() as conn:
        conn.execute('UPDATE schema_version SET version=10')
    db.init_db();db.init_db()
    assert c.get('/api/v1/me',headers=h['sunny']).status_code==200
    assert c.get('/api/v1/question-feedback',headers=h['sunny']).json()['items'][0]['id']==rid
    with db.ro() as conn:
        assert conn.execute('SELECT version FROM schema_version').fetchone()[0]==db.SCHEMA_VERSION
