"""Sunny 的阶段备考与奖励范围；身份、日期和倍率均由服务端决定。"""
from __future__ import annotations

import sqlite3
from datetime import date, datetime, timedelta, timezone

from app import content_loader


def today() -> date:
    return datetime.now(timezone(timedelta(hours=8))).date()


def profile(user, day: date | None = None) -> dict | None:
    cfg = content_loader.study_plan()
    if user is None or user['username'] != cfg['username'] or user['account_status'] != 'active':
        return None
    day = day or today()
    start, exam = date.fromisoformat(cfg['start']), date.fromisoformat(cfg['exam_date'])
    phase = next((p for p in cfg['phases'] if p['start'] <= day.isoformat() <= p['end']), None)
    return {k: cfg[k] for k in ('id', 'region', 'grade', 'scope', 'exam_date', 'date_estimated', 'assumptions', 'coverage_note', 'reward_note')} | {
        'active': start <= day <= exam, 'days_left': max(0, (exam-day).days),
        'phase': phase or {'name': '自由探索', 'advice': '挑一个好奇的问题，按自己的节奏慢慢探索。'},
        'points_multiplier': cfg['points_multiplier'] if start <= day <= exam else 1,
        'tickets_multiplier': cfg['tickets_multiplier'] if start <= day <= exam else 1,
    }


def pairs(topic_id: str) -> list[tuple[str, str]]:
    mapping = content_loader.study_plan()['topics'].get(topic_id, {})
    allowed = {(sid, tier) for tier, sections in mapping.get('units', {}).items() for sid in sections}
    return [p for p in content_loader.topic_pairs(topic_id) if p in allowed]


def unit_context(user, topic_id: str, section_id: str, tier: str) -> dict | None:
    p = profile(user)
    if p is None:
        return None
    eligible = (section_id, tier) in pairs(topic_id)
    active = p['active'] and eligible
    return {'eligible': eligible, 'active': active, 'plan_id': p['id'],
            'label': '必修 1 · 轻松探索' if eligible else '拓展小站 · 有兴趣时再逛',
            'points_multiplier': p['points_multiplier'] if active else 1,
            'tickets_multiplier': p['tickets_multiplier'] if active else 1,
            'ends_on': p['exam_date']}


def reward_context(conn: sqlite3.Connection, user_id: str, topic_id: str, section_id: str, tier: str) -> dict:
    user = conn.execute('SELECT * FROM users WHERE id=?', (user_id,)).fetchone()
    return unit_context(user, topic_id, section_id, tier) or {'points_multiplier': 1, 'tickets_multiplier': 1}


def topic_context(user, topic_id: str, done: set[tuple[str, str]]) -> dict | None:
    p = profile(user)
    if p is None:
        return None
    core = pairs(topic_id)
    return {'eligible': bool(core), 'done': sum(pair in done for pair in core), 'total': len(core),
            'label': content_loader.study_plan()['topics'].get(topic_id, {}).get('label', '拓展小站 · 有兴趣时再逛'),
            'active': p['active'] and bool(core)}


def dashboard(conn: sqlite3.Connection, user) -> dict | None:
    p = profile(user)
    if p is None:
        return None
    done = {(r['topic_id'], r['section_id'], r['tier']) for r in conn.execute(
        "SELECT topic_id,section_id,tier FROM progress WHERE user_id=? AND status='done'", (user['id'],))}
    from app.services import wrongbook as _wb
    wrong = {(r['topic_id'], r['section_id'], r['tier']) for r in conn.execute(
        "SELECT DISTINCT topic_id,section_id,tier FROM wrong_questions WHERE user_id=? AND status='open' AND review_status='ready'",
        (_wb.book_owner(user['id']),))}
    cat = {t['id']: t for t in content_loader.catalog()['topics']}
    units = [(tid, sid, tier) for tid in content_loader.study_plan()['topics'] for sid, tier in pairs(tid)]
    subject_order = ['math', 'physics', 'chemistry']
    offset = today().toordinal() % 3
    subject_order = subject_order[offset:] + subject_order[:offset]
    final = p['days_left'] <= 10
    def rank(u):
        tier = ['basic', 'advanced', 'expert'].index(u[2])
        # 先回看错题；综合阶段优先进阶，考前回归基础。保留高阶难度。
        tier_rank = (tier if final or p['phase'].get('id') != 'improve' else {1:0, 0:1, 2:2}[tier])
        return (0 if u in wrong else 1 if u not in done else 2,
                subject_order.index(cat[u[0]]['subject']), tier_rank, units.index(u))
    ranked = sorted(units, key=rank)
    sections = {s['id']: s['name'] for s in content_loader.catalog()['sections']}
    recommendations = []
    for subj in subject_order:
        u = next((u for u in ranked if cat[u[0]]['subject'] == subj), None)
        if u:
            tid, sid, tier = u
            recommendations.append({'topic_id': tid, 'section_id': sid, 'tier': tier,
                'action': 'wrongbook' if u in wrong else 'section',
                'title': cat[tid]['title'], 'subject': subj, 'section_name': sections[sid],
                'tier_name': content_loader.tier_meta_of(tier)['name'],
                'reason': '和老朋友再见一面，也许会有新发现' if u in wrong else '熟悉的风景，再逛一遍也有收获' if u in done else '这里还没逛过，选一个好奇的小站'})
    return p | {'done': sum(u in done for u in units), 'total': len(units), 'recommendations': recommendations}
