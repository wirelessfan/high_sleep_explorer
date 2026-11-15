"""真实作答、逐题预设与有界奖励：使用隔离数据库，不操作生产账号。"""
from concurrent.futures import ThreadPoolExecutor
from datetime import date
import json
import uuid

import pytest
from fastapi.testclient import TestClient

from app import auth, content_loader, db
from app.main import app
from app.routers.session import _issue_session
from app.services import reflections, study_plan, wrongbook, ratelimit


@pytest.fixture()
def setup(tmp_path, monkeypatch):
    monkeypatch.setattr(db,'DB_PATH',tmp_path/'training.db')
    monkeypatch.setattr(study_plan,'today',lambda:date(2026,11,15))
    content_loader.clear_cache()
    ratelimit.reset()
    with TestClient(app) as c:
        h={}
        with db.tx() as conn:
            for name,username in [('sunny','sunny'),('student','classmate01'),('fake',None)]:
                conn.execute('INSERT INTO users(id,token_hash,sync_code,username,nickname,created_at,last_seen) VALUES(?,?,?,?,?,?,?)',
                    (name,auth.hash_token(name),name,username,'sunny','2026-11-15','2026-11-15'))
                _issue_session(conn,name,name)
                h[name]={'Authorization':'Bearer '+name}
        yield c,h
    content_loader.clear_cache()


def model(mid):
    return next(m for m in content_loader.exam_training()['models'] if m['id']==mid)


def parts(mid, suffix=''):
    m=model(mid)
    return {'concept':m['cues']+suffix,'conditions':m['conditions'], 'method':m['route']+'；'+m['counterexample']}


def attempted(c,h,mid='rope',index=0):
    q=model(mid)['questions'][index]
    r=c.post(f'/api/v1/exam-training/{mid}/answer',headers=h,json={'question_id':q['id'],'picked':q['answer']})
    assert r.status_code==200,r.text
    return r.json()['reflection']['fingerprint']


def summarize(c,h,fp,body,request_id=None):
    r=c.post('/api/v1/reflections',headers=h,json={'fingerprint':fp,'request_id':request_id or str(uuid.uuid4()),'parts':body})
    assert r.status_code==200,r.text
    return r.json()


def test_presets_are_complete_answers_balanced_and_not_leaked(setup):
    c,h=setup
    cfg=content_loader.exam_training()
    assert len(cfg['models'])==18
    answers=[]
    for m in cfg['models']:
        assert len(m['questions'])==2 and sum(x['weight'] for x in m['rubric'])==100
        r=c.get('/api/v1/exam-training/'+m['id'],headers=h['sunny']).json()
        blob=json.dumps(r)
        assert '"answer"' not in blob and '"explain"' not in blob and '"patterns"' not in blob
        assert all(q['reflection'] is None for q in r['questions'])
        for q in m['questions']:
            assert len(set(q['options']))==4 and q['explain']
            answers.append(q['answer'])
    assert [answers.count(i) for i in range(4)]==[9]*4


@pytest.mark.parametrize('mid',[m['id'] for m in content_loader.exam_training()['models']])
def test_model_preset_accepts_complete_condition_and_method(mid):
    m=model(mid)
    result=reflections.evaluate(m['questions'][0],{'criteria':m['rubric'],'contradictions':m['contradictions'],'reference':m['route']},parts(mid))
    assert result['score']>=90,(mid,result)
    nonsense={k:'我今天学会了继续努力争取进步' for k in parts(mid)}
    assert reflections.evaluate(m['questions'][0],{'criteria':m['rubric'],'contradictions':m['contradictions'],'reference':m['route']},nonsense)['score']<80


def test_synonyms_and_false_rope_conditions(setup):
    c,h=setup
    fp=attempted(c,h['sunny'])
    equivalent={'concept':'同一根轻绳，两侧拉力相等。','conditions':'绳的质量可忽略，配无摩擦的理想滑轮且绷紧。',
        'method':'分别隔离两端列牛顿第二定律，共用同一个T。有质量的绳不能直接套相等，也不代表张力等于重力。'}
    r=summarize(c,h['sunny'],fp,equivalent)
    assert r['score']==100 and r['points']==10 and r['streak']==1
    false={**equivalent,'method':'分别列F=ma。但有质量也始终相等，有摩擦也仍然相等，张力一定等于重力。'}
    r=summarize(c,h['sunny'],fp,false)
    assert r['score']<=40 and r['contradictions'] and r['points']==0


@pytest.mark.parametrize('who,expected',[('sunny',10),('student',5),('fake',0)])
def test_identity_and_real_accounting(setup,who,expected):
    c,h=setup
    r=summarize(c,h[who],attempted(c,h[who]),parts('rope'))
    assert r['points']==expected
    assert c.get('/api/v1/me',headers=h[who]).json()['points']==expected
    assert r['streak']==(1 if expected else 0)


def test_cross_user_forgery_empty_answers_and_unauthorized_reads(setup):
    c,h=setup
    fp=attempted(c,h['sunny'])
    body={'fingerprint':fp,'request_id':str(uuid.uuid4()),'parts':parts('rope')}
    assert c.post('/api/v1/reflections',headers=h['student'],json=body).status_code==403
    assert c.get('/api/v1/exam-training').status_code==401
    assert c.post('/api/v1/exam-training/rope/answer',headers=h['sunny'],json={'question_id':'rope-1','picked':True}).status_code==422
    assert c.post('/api/v1/exam-training/rope/answer',headers=h['sunny'],json={'question_id':'fake','picked':0}).status_code==404
    assert c.post('/api/v1/reflections',headers=h['sunny'],json={**body,'parts':{'concept':'    ','conditions':'    ','method':'    '}}).status_code==400
    assert c.get('/api/v1/exam-training/rope',headers=h['student']).json()['questions'][0]['reflection'] is None


def test_high_streak_weighted_reward_and_replays(setup,monkeypatch):
    c,h=setup
    monkeypatch.setattr(reflections.secrets,'randbelow',lambda n:99) # card, last 15%
    for mid in ['rope','friction','brake']:
        fp=attempted(c,h['sunny'],mid)
        request_id=str(uuid.uuid4())
        r=summarize(c,h['sunny'],fp,parts(mid),request_id)
    assert r['drop']=={'kind':'tickets','amount':2,'base_amount':1}
    assert r['streak']==0 and r['drops_today']==1 and r['total_points']==30 and r['total_tickets']==2
    replay=summarize(c,h['sunny'],fp,parts('brake'),request_id)
    assert replay['replayed'] and replay['total_tickets']==2
    updated=summarize(c,h['sunny'],fp,parts('brake','本题检查停车时间。'))
    assert updated['drop'] is None and updated['points']==0 and updated['streak']==0
    conflict=c.post('/api/v1/reflections',headers=h['sunny'],json={'fingerprint':fp,'request_id':request_id,'parts':parts('brake','变化')})
    assert conflict.status_code==409


def test_concurrent_first_summary_cannot_pay_or_count_twice(setup):
    c,h=setup
    fp=attempted(c,h['sunny'])
    with ThreadPoolExecutor(max_workers=4) as pool:
        results=list(pool.map(lambda _:summarize(c,h['sunny'],fp,parts('rope')),range(4)))
    assert sum(r['points'] for r in results)==10
    assert sum(r['first_summary'] for r in results)==1
    assert all(r['streak']==1 for r in results)


def test_failed_first_attempt_resets_and_retry_does_not_rejoin_streak(setup):
    c,h=setup
    summarize(c,h['sunny'],attempted(c,h['sunny']),parts('rope'))
    fp=attempted(c,h['sunny'],'friction')
    r=summarize(c,h['sunny'],fp,dict.fromkeys(['concept','conditions','method'],'我会认真学习天天努力'))
    assert r['points']==0 and r['streak']==0
    r=summarize(c,h['sunny'],fp,parts('friction'))
    assert r['points']==10 and not r['first_summary'] and r['streak']==0


def test_daily_caps_and_beijing_day_reset(setup,monkeypatch):
    c,h=setup
    monkeypatch.setattr(reflections.secrets,'randbelow',lambda n:0)
    results=[]
    for m in content_loader.exam_training()['models']:
        results.append(summarize(c,h['sunny'],attempted(c,h['sunny'],m['id']),parts(m['id'])))
    assert sum(r['points'] for r in results)==100
    assert sum(bool(r['drop']) for r in results)==3
    assert results[-1]['drops_today']==3
    monkeypatch.setattr(study_plan,'today',lambda:date(2026,11,16))
    info=c.get('/api/v1/exam-training',headers=h['sunny']).json()
    assert info['streak']==info['drops_today']==info['base_points_today']==0
    r=summarize(c,h['sunny'],attempted(c,h['sunny'],'rope',1),parts('rope','这题是有质量的绳。'))
    assert r['points']==10


def test_repeat_template_is_saved_but_does_not_farm_streak(setup):
    c,h=setup
    text=parts('rope')
    summarize(c,h['sunny'],attempted(c,h['sunny']),text)
    fp=attempted(c,h['sunny'],'rope',1)
    r=summarize(c,h['sunny'],fp,text)
    assert r['duplicate'] and r['points']==0 and r['streak']==0
    saved=c.get('/api/v1/exam-training/rope',headers=h['sunny']).json()['questions'][1]['reflection']['saved']
    assert saved['parts']==text


def test_expired_plan_and_identical_question_moved_positions(setup,monkeypatch):
    c,h=setup
    monkeypatch.setattr(study_plan,'today',lambda:date(2027,1,1))
    r=summarize(c,h['sunny'],attempted(c,h['sunny']),parts('rope'))
    assert r['points']==5
    q=model('rope')['questions'][0]
    assert reflections.fingerprint(q)==reflections.fingerprint({**q,'id':'new-id','explain':'编辑解析不重发奖励'})
    assert reflections.plain('0<a<1，x>2')=='0<a<1,x>2'


def test_normal_questions_and_partial_levels_require_actual_selection(setup):
    c,h=setup
    content=content_loader.tier_content(content_loader.topic('math-log')['sections'][0],'basic')
    qid,q=next(iter(wrongbook.questions_of(content).items()))
    r=c.post('/api/v1/topics/math-log/sections/quick/submit',headers=h['sunny'],json={'answers':{qid:q['answer']}}).json()
    answered=[d for d in r['details'] if d.get('reflection')]
    assert len(answered)==1 and answered[0]['id']==qid
    saved=c.get('/api/v1/topics/math-log/sections/quick/reflections',headers=h['sunny']).json()['items']
    assert set(saved)=={qid}
    fp=answered[0]['reflection']['fingerprint']
    result=summarize(c,h['sunny'],fp,{'concept':'对数定义与指数的互逆关系','conditions':'底数为正而且不等于一，真数必须是正数','method':q['explain']+'。先把对数式改写成指数式，再求指数并核验。'})
    assert result['mode']=='explanation_overlap'


def test_special_question_feedback_is_server_resolved(setup):
    c,h=setup
    m=model('rope');q=m['questions'][0]
    body={'topic_id':m['topic_id'],'section_id':'drill-rope','tier':'basic','question_id':q['id'],
          'category':'other','detail':'检查这道专项的适用条件','displayed_stem':q['stem'],'displayed_options':q['options']}
    assert c.post('/api/v1/question-feedback',headers=h['sunny'],json=body).status_code==200
    assert c.post('/api/v1/question-feedback',headers=h['sunny'],json={**body,'topic_id':'math-log'}).status_code==404


def test_reordered_options_cannot_create_a_second_reward():
    q=model('rope')['questions'][0]
    answer=q['options'][q['answer']]
    reordered=list(reversed(q['options']))
    assert reflections.fingerprint(q)==reflections.fingerprint({**q,'options':reordered,'answer':reordered.index(answer)})


def test_rate_limit_and_injected_client_rewards_do_not_change_balance(setup,monkeypatch):
    c,h=setup
    fp=attempted(c,h['sunny'])
    body={'fingerprint':fp,'request_id':str(uuid.uuid4()),'parts':parts('rope')}
    assert c.post('/api/v1/reflections',headers=h['sunny'],json={**body,'points':99999}).status_code==422
    monkeypatch.setattr(ratelimit,'allow',lambda *a,**kw:False)
    assert c.post('/api/v1/reflections',headers=h['sunny'],json=body).status_code==429
    assert c.get('/api/v1/me',headers=h['sunny']).json()['points']==0


def test_wrongbook_redo_returns_summary_for_actual_practice_answer(setup):
    c,h=setup
    content=content_loader.tier_content(content_loader.topic('math-log')['sections'][0],'basic')
    qid,q=next(iter(wrongbook.questions_of(content).items()))
    c.post('/api/v1/topics/math-log/sections/quick/submit',headers=h['sunny'],json={'answers':{qid:(q['answer']+1)%4}})
    items=c.get('/api/v1/wrongbook/math-log',headers=h['sunny']).json()['items']
    item=items[0]
    r=c.post('/api/v1/wrongbook/math-log/redo',headers=h['sunny'],json={'answers':{item['id']:item['answer']}})
    assert r.status_code==200,r.text
    assert r.json()['results'][0]['reflection']['fingerprint']==reflections.fingerprint(q)
