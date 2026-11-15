"""逐题总结：实际作答凭据、可解释的离线对照与事务内发奖。"""
from __future__ import annotations

import hashlib
import html
import json
import re
import secrets
import unicodedata

from app import content_loader
from app.services import accounts, events, study_plan


class ReflectionError(ValueError):
    def __init__(self, message, status=400):
        super().__init__(message)
        self.status = status


def plain(value: str) -> str:
    # 不能把 0<a<1、x>2 这样的数学不等式当成 HTML 标签。
    clean = re.sub(r'</?[a-z][a-z0-9-]*(?:\s+[^<>]*?)?\s*/?>', '', value or '', flags=re.I)
    return unicodedata.normalize('NFKC', html.unescape(clean)).strip()


def normalized(value: str) -> str:
    return re.sub(r'\s+', '', plain(value)).lower()


def fingerprint(question: dict) -> str:
    # 忽略位置、题号和解析编辑，同一道题换位置不能再次领总结奖励。
    value = {'stem': normalized(question['stem']), 'options': sorted(normalized(o) for o in question['options']),
             'answer': normalized(question['options'][question['answer']])}
    return hashlib.sha256(json.dumps(value, ensure_ascii=False, sort_keys=True).encode()).hexdigest()


def record_attempt(conn, user_id, question, *, source, topic_id, section_id, tier, question_id, rubric=None):
    fp = fingerprint(question)
    conn.execute('INSERT OR IGNORE INTO question_attempts VALUES(?,?,?,?,?,?,?,?,?,?)',
        (user_id, fp, source, topic_id, section_id, tier, question_id,
         json.dumps(question, ensure_ascii=False), json.dumps(rubric, ensure_ascii=False) if rubric else None, events.now()))
    return {'fingerprint': fp}


def record_bank(conn, user_id, topic_id, section_id, tier, details, questions):
    for d in details:
        q = questions.get(d['id'])
        if q and type(d.get('picked')) is int and 0 <= d['picked'] < len(q['options']):
            d['reflection'] = record_attempt(conn, user_id, q, source='bank', topic_id=topic_id,
                section_id=section_id, tier=tier, question_id=d['id'])


def _grams(value):
    value = normalized(value)
    value = re.sub(r'[\d\W_]+', '', value)
    return {value[i:i+2] for i in range(len(value)-1)} - {
        '所以','因此','得到','可以','正确','本题','结果','这个','我们','首先','然后','注意','因为'}


def _coverage(reference, text):
    rg, tg = _grams(reference), _grams(text)
    return len(rg & tg) / len(rg) if rg else 0


def _contradictions(patterns, text):
    found = []
    # 不跨句拼接“氧化剂得电子、还原剂失电子”，也不把否定错误结论判成错误。
    for clause in re.split(r'[,，、。;；!！?？]', text):
        for pattern in patterns:
            for match in re.finditer(pattern, clause, re.I):
                statement = clause[max(0, match.start()-10):match.end()]
                if not re.search(r'不能|不是|不应|不要|错误|并非|不代表|避免', statement):
                    found.append(match.group(0))
    return found


def evaluate(question, rubric, parts):
    text = normalized('。'.join(parts.values()))
    if rubric:
        checks = [{'label': c['label'], 'matched': any(re.search(p, text, re.I) for p in c['patterns']),
                   'weight': c['weight']} for c in rubric['criteria']]
        score = sum(c['weight'] for c in checks if c['matched'])
        contradictions = _contradictions(rubric.get('contradictions', []), text)
        mode = 'preset_rules'
        reference = rubric['reference']
    else:
        # 存量题逐题使用实际解析作对照。仅报告字面要点覆盖，不冒充在线语义判卷。
        reference = plain(question.get('explain', ''))
        sentences = [x.strip() for x in re.split(r'[。；\n]', reference) if len(x.strip()) >= 5]
        skill = question.get('skill') or (sentences[0] if sentences else reference)
        method = max(sentences, key=len) if sentences else reference
        boundary = next((s for s in reversed(sentences) if re.search(r'条件|注意|不能|先|仅|时|正|负|范围|守恒|所以', s)), method)
        checks = []
        for label, ref, weight in [('考点识别', skill, 20), ('关键推理', method, 40), ('条件与复核', boundary, 40)]:
            fraction = min(1.0, _coverage(ref, text) / .42)
            checks.append({'label': label, 'matched': fraction >= 1, 'weight': weight,
                           'earned': round(weight * fraction)})
        score = sum(c['earned'] for c in checks)
        contradictions = _contradictions([
            r'不(?:用|需|必|需要).*?(?:定义域|真数为正|检查底数)',
            r'氧化剂.*?失电子', r'还原剂.*?得电子', r'失重.*?重力(?:为零|消失)',
            r'静摩擦(?:总是|一定|始终).*?μ', r'任何(?:状态|物态).*?22\.4',
        ], text)
        mode = 'explanation_overlap'
    if contradictions:
        score = min(score, 40)
    # 三部分都需有实质文字；只有数字、提示词或泛泛夸奖不能获奖。
    substantive = all(len(_grams(value)) >= 3 for value in parts.values())
    if not substantive:
        score = min(score, 40)
    return {'score': score, 'mode': mode, 'checks': checks, 'contradictions': contradictions,
            'reference': reference, 'note': '预设考点规则对照' if rubric else '本题解析要点的字面对照；不能代替语义判卷，改用同义说法可能低估匹配度。',
            'advice': '发现与适用条件冲突的表述，请先修正。' if contradictions else
                      '把遗漏的条件或推理补进自己的总结，再试一次。' if score < 80 else '已覆盖主要要点，换一道题试着独立识别。'}


def _eligible(user):
    return user['account_status'] == 'active' and accounts.kind(user) != 'guest'


def _state(conn, user_id, day):
    conn.execute('INSERT INTO reflection_state(user_id,day) VALUES(?,?) ON CONFLICT(user_id) DO UPDATE SET '
        'streak=CASE WHEN day=excluded.day THEN streak ELSE 0 END, '
        'drops=CASE WHEN day=excluded.day THEN drops ELSE 0 END, day=excluded.day', (user_id, day))
    return conn.execute('SELECT * FROM reflection_state WHERE user_id=?', (user_id,)).fetchone()


def submit(conn, user, fp, parts, request_id):
    cfg = content_loader.exam_training()['rewards']
    day = study_plan.today().isoformat()
    signature = hashlib.sha256(json.dumps([fp, parts], ensure_ascii=False, sort_keys=True).encode()).hexdigest()
    previous = events.find(conn, user['id'], 'reflection_request:' + request_id, 'reflection_submission')
    if previous:
        stored = json.loads(previous['payload'])
        if stored['signature'] != signature:
            raise ReflectionError('该请求编号已用于另一份总结，请重新提交', 409)
        return {**stored['response'], 'replayed': True}
    attempt = conn.execute('SELECT * FROM question_attempts WHERE user_id=? AND fingerprint=?', (user['id'], fp)).fetchone()
    if not attempt:
        raise ReflectionError('请先实际作答这道题，再总结考点', 403)
    question = json.loads(attempt['question_json'])
    rubric = json.loads(attempt['rubric_json']) if attempt['rubric_json'] else None
    result = evaluate(question, rubric, parts)
    existing = conn.execute('SELECT * FROM question_reflections WHERE user_id=? AND fingerprint=?', (user['id'], fp)).fetchone()
    first = existing is None
    state = _state(conn, user['id'], day)
    duplicate = any(normalized('。'.join(json.loads(r['summary_json']).values())) == normalized('。'.join(parts.values()))
        for r in conn.execute('SELECT summary_json FROM question_reflections WHERE user_id=? AND fingerprint<>?', (user['id'], fp)))
    eligible = _eligible(user)
    context = study_plan.reward_context(conn, user['id'], attempt['topic_id'], attempt['section_id'], attempt['tier'])
    pm, tm = context['points_multiplier'], context['tickets_multiplier']
    used = conn.execute('SELECT COALESCE(SUM(base_points),0) FROM question_reflections WHERE user_id=? AND reward_day=?', (user['id'], day)).fetchone()[0]
    matched = result['score'] >= cfg['match_threshold'] and not duplicate
    high = result['score'] >= cfg['high_threshold'] and not duplicate
    base = min(cfg['summary_points'], max(0, cfg['daily_base_cap']-used)) if eligible and matched and not (existing and existing['rewarded']) else 0
    points = base * pm
    streak, drops = state['streak'], state['drops']
    drop = None
    # 一道题只有首次总结参与连续计数，低匹配会断连；修改旧总结可补领一次分，不重复攒连击。
    if first:
        streak = streak + 1 if high and eligible else 0
        if streak >= cfg['streak_length']:
            streak = 0
            if drops < cfg['daily_drop_cap']:
                pick = secrets.randbelow(sum(item['weight'] for item in cfg['drop_pool']))
                prize = cfg['drop_pool'][-1]
                for item in cfg['drop_pool']:
                    if pick < item['weight']:
                        prize = item
                        break
                    pick -= item['weight']
                drops += 1
                amount = prize['amount'] * (pm if prize['kind']=='points' else tm)
                drop = {'kind': prize['kind'], 'amount': amount, 'base_amount': prize['amount']}
                if prize['kind']=='points':
                    conn.execute('UPDATE users SET points=points+? WHERE id=?', (amount, user['id']))
                else:
                    conn.execute('UPDATE users SET tickets=tickets+? WHERE id=?', (amount, user['id']))
                events.log(conn, user['id'], f'reflection_drop:{day}:{drops}', 'reflection_drop', {**drop, 'fingerprint': fp, 'reward': context})
    if points:
        conn.execute('UPDATE users SET points=points+? WHERE id=?', (points, user['id']))
        events.log(conn, user['id'], 'reflection_reward:'+fp, 'reflection_reward', {'points':points, 'base_points':base, 'reward':context})
    conn.execute('INSERT INTO question_reflections VALUES(?,?,?,?,?,?,?,?,?,?,?,?) ON CONFLICT(user_id,fingerprint) DO UPDATE SET '
        'summary_json=excluded.summary_json,score=excluded.score,best_score=MAX(best_score,excluded.score),feedback_json=excluded.feedback_json,'
        'rewarded=MAX(rewarded,excluded.rewarded),base_points=base_points+excluded.base_points,points=points+excluded.points,'
        'reward_day=CASE WHEN excluded.base_points>0 THEN excluded.reward_day ELSE reward_day END,updated_at=excluded.updated_at',
        (user['id'], fp, json.dumps(parts,ensure_ascii=False), result['score'], result['score'], json.dumps(result,ensure_ascii=False),
         int(base>0), base, points, day if base else None, events.now(), events.now()))
    conn.execute('UPDATE reflection_state SET streak=?,drops=? WHERE user_id=?', (streak,drops,user['id']))
    current = conn.execute('SELECT points,tickets FROM users WHERE id=?', (user['id'],)).fetchone()
    reason = ('体验或历史账号可练习总结，正式账号才能领取奖励。' if not eligible else
              '这份总结与另一题完全相同，请结合本题条件改写。' if duplicate else
              '本题总结积分已领取；修改不会重复计算连击。' if existing and existing['rewarded'] else
              '今日总结基础积分额度已用完，可继续练习。' if matched and base==0 else
              '达到80分可领总结积分；首次达到90分计入连击。')
    response = {**result, 'points':points, 'multiplier':pm, 'drop':drop, 'streak':streak,
                'drops_today':drops,'daily_drop_cap':cfg['daily_drop_cap'], 'first_summary':first,
                'duplicate':duplicate,'reward_reason':reason,'total_points':current['points'], 'total_tickets':current['tickets']}
    events.log(conn, user['id'], 'reflection_request:'+request_id, 'reflection_submission', {'signature':signature,'response':response})
    return response


def saved_context(conn, user_id, fp):
    attempt = conn.execute('SELECT fingerprint FROM question_attempts WHERE user_id=? AND fingerprint=?', (user_id,fp)).fetchone()
    if not attempt:
        return None
    row = conn.execute('SELECT * FROM question_reflections WHERE user_id=? AND fingerprint=?', (user_id,fp)).fetchone()
    return {'fingerprint':fp, 'saved': {'parts':json.loads(row['summary_json']), 'score':row['score'],
        'best_score':row['best_score'], 'rewarded':bool(row['rewarded'])} if row else None}
