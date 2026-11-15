"""Register the verified chat feedback and grant 50 points + 3 bonus tickets once.

Defaults to a rolled-back preview. Use --apply against the intended LEARN_DB.
"""
import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app import db
from app.services import blindbox, events, question_feedback


def record(conn):
    users = conn.execute("SELECT * FROM users WHERE lower(username)='sunny'").fetchall()
    if len(users) != 1:
        raise ValueError('Expected exactly one registered Sunny account')
    user = users[0]
    before = {'points':user['points'], 'tickets':user['blindbox_tickets']}
    body = {'topic_id':'chemistry-ionic', 'section_id':'quick', 'tier':'advanced',
            'question_id':'aq1', 'category':'incomplete',
            'detail':'Sunny 通过聊天截图反馈：题干在（0处截断。已核验是0<k<1被页面当作HTML，后半段条件丢失。'}
    q = question_feedback.resolve_question(conn, user['id'], body)
    body.update(displayed_stem=q['stem'], displayed_options=q['options'])
    report = question_feedback.submit(conn, user, body)
    review = question_feedback.moderate(conn, report['item']['id'], 'approved',
        '已核验有效并修复公共题干渲染组件，完整保留0<k<1和后续条件；原题答案B正确。',
        'maintenance:confirmed-chat-report')
    tickets = 0
    for key, count, reason in [
        ('sunny_question_feedback_bonus:2026-11-15:chemistry-ionic:aq1', 1, '有效题目反馈额外奖励'),
        ('sunny_exchange_policy_bonus:2026-11-15', 2, '采纳每日积分兑换上限调整为9张的建议'),
    ]:
        if events.log(conn, user['id'], key, 'feedback_bonus', {'tickets':count,'reason':reason}):
            blindbox.add_tickets(conn, user['id'], count)
            tickets += count
    after = conn.execute('SELECT points,blindbox_tickets FROM users WHERE id=?',(user['id'],)).fetchone()
    return {'username':user['username'], 'feedback_id':report['item']['id'],
            'credited_points':review['rewarded_now'], 'credited_tickets':tickets,
            'before':before, 'after':{'points':after['points'],'tickets':after['blindbox_tickets']}}


class PreviewRollback(Exception):
    pass


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--apply', action='store_true')
    args = parser.parse_args()
    try:
        with db.tx() as conn:
            result = record(conn)
            if not args.apply:
                raise PreviewRollback()
    except PreviewRollback:
        pass
    print(json.dumps({'applied':args.apply, **result}, ensure_ascii=False))


if __name__ == '__main__':
    main()
