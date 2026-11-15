"""题目问题反馈：服务端核验原题，管理员审核后一次性奖励 50 分。"""
from __future__ import annotations

import hashlib
import json
import uuid
from datetime import datetime, timedelta, timezone

from app import content_loader
from app.services import events, wrongbook

REWARD = 50
CATEGORIES = {'incomplete': '题目不完整/显示异常', 'answer': '答案可能有误',
              'explanation': '解析有误/不清楚', 'diagram': '图解问题', 'other': '其他问题'}


class FeedbackError(ValueError):
    def __init__(self, message, status=400):
        super().__init__(message)
        self.status = status


def _now():
    return datetime.now(timezone(timedelta(hours=8))).isoformat(timespec='seconds')


def resolve_question(conn, user_id, body):
    if body.get('wrong_question_id'):
        row = conn.execute("SELECT * FROM wrong_questions WHERE id=? AND user_id=? AND source='practice'",
                           (body['wrong_question_id'], user_id)).fetchone()
        if not row:
            raise FeedbackError('错题记录不存在', 404)
        if (body['topic_id'], body['section_id'], body['tier'], body['question_id']) != (row['topic_id'],row['section_id'],row['tier'],row['question_id']):
            raise FeedbackError('题目定位与错题记录不一致')
        return {'stem':row['stem'], 'options':json.loads(row['options_json']),
                'answer':row['answer'], 'explain':row['explain']}
    try:
        topic = content_loader.topic(body['topic_id'])
    except content_loader.ContentError:
        raise FeedbackError('主题不存在', 404)
    section = next((s for s in topic['sections'] if s['id']==body['section_id']), None)
    if not section or body['tier'] not in content_loader.tier_ids():
        raise FeedbackError('版块或难度不存在', 404)
    content = content_loader.tier_content(section, body['tier'])
    question = wrongbook.questions_of(content).get(body['question_id']) if content else None
    if not question:
        raise FeedbackError('题目不存在', 404)
    return question


def _item(row, *, admin=False):
    data = {key:row[key] for key in ('id','topic_id','section_id','tier','question_id',
            'question_version','category','detail','status','reward_points','review_note',
            'created_at','reviewed_at')}
    snapshot = json.loads(row['snapshot_json'])
    data['question'] = snapshot if admin else {k:snapshot[k] for k in ('stem','options')}
    if admin:
        data.update(user_id=row['user_id'], nickname=row['nickname'], username=row['username'])
    return data


def submit(conn, user, body):
    if not user['username'] or user['username'].lower()=='guest':
        raise FeedbackError('请使用正式账号提交题目反馈',403)
    detail = body['detail'].strip()
    if len(detail)<5 or len(detail)>1000:
        raise FeedbackError('请用 5–1000 字描述题目问题')
    if body['category'] not in CATEGORIES:
        raise FeedbackError('反馈类型不存在')
    question = resolve_question(conn,user['id'],body)
    if body['displayed_stem']!=question.get('stem','') or body['displayed_options']!=question.get('options',[]):
        raise FeedbackError('题目已更新，请刷新后重新反馈',409)
    snapshot = {k:question.get(k) for k in ('stem','options','answer','explain')}
    raw = json.dumps(snapshot,ensure_ascii=False,sort_keys=True)
    version = hashlib.sha256(raw.encode()).hexdigest()
    values = (user['id'],body['topic_id'],body['section_id'],body['tier'],body['question_id'],version)
    previous = conn.execute('SELECT * FROM question_feedback WHERE user_id=? AND topic_id=? AND section_id=? AND tier=? AND question_id=? AND question_version=?',values).fetchone()
    if previous:
        return {'duplicate':True,'item':_item(previous),'reward':REWARD}
    now = _now()
    used = conn.execute('SELECT count(*) FROM question_feedback WHERE user_id=? AND substr(created_at,1,10)=?',(user['id'],now[:10])).fetchone()[0]
    if used>=10:
        raise FeedbackError('每天最多提交 10 道题的反馈，请明天再来',429)
    rid = 'qf_'+uuid.uuid4().hex
    conn.execute('INSERT INTO question_feedback(id,user_id,topic_id,section_id,tier,question_id,question_version,snapshot_json,category,detail,created_at) VALUES (?,?,?,?,?,?,?,?,?,?,?)',
                 (rid,*values,raw,body['category'],detail,now))
    row = conn.execute('SELECT * FROM question_feedback WHERE id=?',(rid,)).fetchone()
    return {'duplicate':False,'item':_item(row),'reward':REWARD}


def list_items(conn,user_id=None):
    admin = user_id is None
    where,args = ('',()) if admin else ('WHERE f.user_id=?',(user_id,))
    rows = conn.execute('SELECT f.*,u.nickname,u.username FROM question_feedback f JOIN users u ON u.id=f.user_id '+where+" ORDER BY CASE f.status WHEN 'pending' THEN 0 ELSE 1 END,f.created_at DESC LIMIT 200",args).fetchall()
    return {'items':[_item(r,admin=admin) for r in rows],'reward':REWARD,'categories':CATEGORIES}


def moderate(conn, report_id, status, note, reviewer):
    if status not in ('approved','rejected'):
        raise FeedbackError('审核结果只能为通过或不通过')
    note = note.strip()
    if not 2<=len(note)<=500:
        raise FeedbackError('请填写 2–500 字审核说明')
    row = conn.execute('SELECT * FROM question_feedback WHERE id=?',(report_id,)).fetchone()
    if not row:
        raise FeedbackError('反馈不存在',404)
    if row['user_id']==reviewer:
        raise FeedbackError('请由其他管理员审核自己的反馈',403)
    if row['status']!='pending':
        if row['status']!=status:
            raise FeedbackError('该反馈已审核，不能改为另一个结果',409)
        return {'item':_item(row),'rewarded_now':0}
    reward = REWARD if status=='approved' else 0
    if reward:
        if not events.log(conn,row['user_id'],f'question_feedback_reward:{report_id}',
                          'question_feedback_reward',{'feedback':report_id,'points':reward,'reviewer':reviewer}):
            raise FeedbackError('奖励记录已存在，请检查该反馈',409)
        conn.execute('UPDATE users SET points=points+? WHERE id=?',(reward,row['user_id']))
    conn.execute('UPDATE question_feedback SET status=?,reward_points=?,review_note=?,reviewed_by=?,reviewed_at=? WHERE id=?',
                 (status,reward,note,reviewer,_now(),report_id))
    row = conn.execute('SELECT * FROM question_feedback WHERE id=?',(report_id,)).fetchone()
    return {'item':_item(row),'rewarded_now':reward}
