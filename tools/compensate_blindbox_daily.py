"""2026-11-15 Sunny 每日盲盒缺失补偿。默认只预览，--apply 幂等发放。

LEARN_DB=/var/lib/learning-highschool/app.db .venv/bin/python tools/compensate_blindbox_daily.py --apply
"""
import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app import db
from app.services import blindbox, events

INCIDENT_DAY = '2026-11-15'
BONUS_TICKETS = 3


def compensate(conn, *, apply=False):
    user = conn.execute("SELECT * FROM users WHERE lower(username)='sunny'").fetchone()
    if not user:
        raise ValueError('Sunny account not found')
    uid = user['id']
    key = f'bbox_daily_compensation:{INCIDENT_DAY}'
    previous = events.find(conn, uid, key, 'bbox_compensation')
    if previous:
        return {'replayed': True, **json.loads(previous['payload'])}
    exchanges = conn.execute("SELECT payload FROM events WHERE user_id=? AND kind='bbox_exchange' AND substr(created_at,1,10)=?", (uid, INCIDENT_DAY)).fetchall()
    refund = sum(int(json.loads(row['payload'])['points']) for row in exchanges)
    payload = {'incident_date': INCIDENT_DAY, 'bonus_tickets': BONUS_TICKETS,
               'points_refund': refund, 'reason': '每日三张盲盒券未实现；额外补偿并退回当日换券积分'}
    if not apply:
        return {'dry_run': True, 'tickets_before': user['blindbox_tickets'], 'points_before': user['points'], **payload}
    daily = blindbox.grant_daily_tickets(conn, uid)
    payload['daily_tickets_credited'] = daily['credited_now']
    payload['tickets_before'] = user['blindbox_tickets']
    payload['points_before'] = user['points']
    if not events.log(conn, uid, key, 'bbox_compensation', payload):
        raise RuntimeError('Compensation already processed')
    conn.execute('UPDATE users SET blindbox_tickets=blindbox_tickets+?,points=points+? WHERE id=?', (BONUS_TICKETS, refund, uid))
    after = conn.execute('SELECT blindbox_tickets,points FROM users WHERE id=?', (uid,)).fetchone()
    return {'replayed': False, 'tickets_after': after['blindbox_tickets'], 'points_after': after['points'], **payload}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--apply', action='store_true')
    args = parser.parse_args()
    # Transaction and event key make retries safe. Never resets a balance or draws for Sunny.
    with db.tx() as conn:
        result = compensate(conn, apply=args.apply)
    print(json.dumps(result, ensure_ascii=False))


if __name__ == '__main__':
    main()
