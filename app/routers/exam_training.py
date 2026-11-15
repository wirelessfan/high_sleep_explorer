"""考点专项和逐题总结。在线 AI 关闭时明确使用本地预设对照。"""
import sqlite3

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, ConfigDict, Field, StrictInt

from app import content_loader, db
from app.routers.session import current_user
from app.services import reflections, study_plan, wrongbook, ratelimit

router = APIRouter(tags=['exam-training'])


class SummaryParts(BaseModel):
    model_config = ConfigDict(extra='forbid')
    concept: str = Field(min_length=4, max_length=200)
    conditions: str = Field(min_length=4, max_length=250)
    method: str = Field(min_length=4, max_length=450)


class SummaryIn(BaseModel):
    model_config = ConfigDict(extra='forbid')
    fingerprint: str = Field(pattern=r'^[a-f0-9]{64}$')
    request_id: str = Field(pattern=r'^[a-zA-Z0-9_-]{8,80}$')
    parts: SummaryParts


class AnswerIn(BaseModel):
    model_config = ConfigDict(extra='forbid')
    question_id: str = Field(min_length=1, max_length=80)
    picked: StrictInt = Field(ge=0, le=3)


def _model(model_id):
    item = next((m for m in content_loader.exam_training()['models'] if m['id']==model_id), None)
    if not item:
        raise HTTPException(404, '专项不存在')
    return item


@router.get('/exam-training')
def get_training(user: sqlite3.Row = Depends(current_user)):
    cfg = content_loader.exam_training()
    with db.ro() as conn:
        state = conn.execute('SELECT * FROM reflection_state WHERE user_id=?', (user['id'],)).fetchone()
        attempts = {r['fingerprint'] for r in conn.execute('SELECT fingerprint FROM question_attempts WHERE user_id=?', (user['id'],))}
        used = conn.execute('SELECT COALESCE(SUM(base_points),0) FROM question_reflections WHERE user_id=? AND reward_day=?', (user['id'],study_plan.today().isoformat())).fetchone()[0]
    current = state and state['day']==study_plan.today().isoformat()
    return {k:cfg[k] for k in ('title','scope','intro','evaluator_note','rewards')} | {
        'streak':state['streak'] if current else 0, 'drops_today':state['drops'] if current else 0,
        'base_points_today':used,
        'models':[{k:m[k] for k in ('id','subject','topic_id','title','cues')} | {
            'questions':len(m['questions']), 'attempted':sum(reflections.fingerprint(q) in attempts for q in m['questions'])}
            for m in cfg['models']]}


@router.get('/exam-training/{model_id}')
def get_model(model_id: str, user: sqlite3.Row = Depends(current_user)):
    model = _model(model_id)
    with db.ro() as conn:
        questions = []
        for q in model['questions']:
            ctx = reflections.saved_context(conn, user['id'], reflections.fingerprint(q))
            questions.append(content_loader.strip_answers(q) | {'reflection':ctx})
    return {k:model[k] for k in ('id','subject','topic_id','title','cues','conditions','route','counterexample')} | {'questions':questions}


@router.post('/exam-training/{model_id}/answer')
def answer(model_id: str, body: AnswerIn, user: sqlite3.Row = Depends(current_user)):
    model = _model(model_id)
    q = next((q for q in model['questions'] if q['id']==body.question_id), None)
    if not q:
        raise HTTPException(404, '题目不存在')
    with db.tx() as conn:
        ref = reflections.record_attempt(conn,user['id'],q,source='drill',topic_id=model['topic_id'],
            section_id='quick',tier='basic',question_id=q['id'],rubric={
                'criteria':model['rubric'],'contradictions':model['contradictions'],
                'reference':'；'.join([model['cues'],model['conditions'],model['route'],model['counterexample']])})
    return {'correct':body.picked==q['answer'],'answer':q['answer'],'explain':q['explain'],'reflection':ref}


@router.post('/reflections')
def summarize(body: SummaryIn, user: sqlite3.Row = Depends(current_user)):
    if not ratelimit.allow('reflection:'+user['id'],limit=60,window_seconds=60):
        raise HTTPException(429, '总结提交过快，请稍后再试')
    parts = {k:v.strip() for k,v in body.parts.model_dump().items()}
    if any(len(v)<4 for v in parts.values()):
        raise HTTPException(400, '请分别写出考点、条件和方法，不能只填空白')
    with db.tx() as conn:
        try:
            # 余额、身份、日期均在事务内重新读取。
            fresh = conn.execute('SELECT * FROM users WHERE id=?', (user['id'],)).fetchone()
            return reflections.submit(conn,fresh,body.fingerprint,parts,body.request_id)
        except reflections.ReflectionError as exc:
            raise HTTPException(exc.status, str(exc))


@router.get('/topics/{topic_id}/sections/{section_id}/reflections')
def section_summaries(topic_id: str, section_id: str, tier: str='basic', user: sqlite3.Row=Depends(current_user)):
    try:
        data = content_loader.topic(topic_id)
    except content_loader.ContentError:
        raise HTTPException(404, '主题不存在')
    sec = next((s for s in data['sections'] if s['id']==section_id),None)
    content = content_loader.tier_content(sec,tier) if sec else None
    if content is None:
        raise HTTPException(404, '单元不存在')
    with db.ro() as conn:
        return {'items':{qid:ctx for qid,q in wrongbook.questions_of(content).items()
            if (ctx:=reflections.saved_context(conn,user['id'],reflections.fingerprint(q)))}}
