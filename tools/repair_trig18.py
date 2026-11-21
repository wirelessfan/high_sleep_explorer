"""精确修复已审校的18道三角题；默认只核验，--apply才写入。"""
import argparse
import hashlib
import json
import sqlite3
from pathlib import Path

IDS = [
    'wq_eb37b7913b3f', 'wq_b5be6aa9eca9', 'wq_698fbf649511',
    'wq_00765e6c4b8a', 'wq_9a6016234cfc', 'wq_930baf7f898d',
    'wq_49b78aceeb47', 'wq_2992fa885a0b', 'wq_c6cdcdf3fdf8',
    'wq_37a91b88444c', 'wq_a08d918b7cbc', 'wq_b5a8b647536a',
    'wq_29a49f1b03bc', 'wq_a72908018d3b', 'wq_515070a4818b',
    'wq_f7d5e1aec202', 'wq_1e6a904ce4db', 'wq_a8227f3f7f90',
]
MULTI = {1: [0, 1, 3], 2: [0, 1, 3], 3: [0, 2, 3],
         4: [0, 2, 3], 5: [1, 3], 11: [1, 2, 3]}
IMAGE_OWNER = 'u_Vl5qU3dLXEZt18Ej'
IMAGE_LAYOUT = [
    ('1000009447', 0, .29), ('1000009447', .28, .52), ('1000009447', .47, .81),
    ('1000009446', 0, .71), ('1000009446', .69, 1),
    ('1000009445', 0, .43), ('1000009445', .40, .72), ('1000009445', .70, 1),
    ('1000009444', 0, .23), ('1000009444', .21, .44), ('1000009444', .42, .68),
    ('1000009444', .65, .80), ('1000009444', .78, .92), ('1000009444', .90, 1),
    ('1000009443', 0, .23), ('1000009443', .30, .62),
    ('1000009443', .59, .90), ('1000009443', .86, 1),
]


def make_images(directory):
    from PIL import Image
    directory = Path(directory)
    for n, (source, top, bottom) in enumerate(IMAGE_LAYOUT, 1):
        with Image.open(directory / f'{source}-trig18-upright.jpg') as im:
            im.crop((0, int(im.height * top), im.width, int(im.height * bottom))).save(
                directory / f'trig18-q{n:02d}-v2.jpg', quality=95)


def patches(rows):
    out = []
    for n, row in enumerate(rows, 1):
        p = {'id': row['id'], 'review_status': 'ready', 'review_reason': '',
             'image_path': f'/wb-images/{IMAGE_OWNER}/trig18-q{n:02d}-v2.jpg'}
        if n in MULTI:
            p.update(qtype='multi_choice', answer=-1,
                     answer_indices_json=json.dumps(MULTI[n]), answer_text='')
        elif n not in (15, 18):
            p['answer_indices_json'] = json.dumps([row['answer']] if row['qtype'] == 'choice' else [])
        if n == 1:
            p['explain'] = '由中心对称点得φ=π/3。A、B、D正确，C的实际最小值为-1。原图D末尾局部截断，按完整变换关系校核。'
        elif n == 2:
            p['derivation'] = ('相邻异向零点间距为1，T=2，ω=π，故f(x)=cos(πx+π/6)。\n'
                               'f(x+1/3)=-sinπx为奇函数；f(x+5/6)=-cosπx为偶函数。\n'
                               'f(-2022/5)=cos(7π/30)，f(2025/4)=cos(5π/12)，前者较大，C错误。\n'
                               'sin(πx+2π/3)=cos(πx+π/6)，D正确，选ABD。')
            p['explain'] = '周期为2，f(x)=cos(πx+π/6)，正确选项为A、B、D；C两端化简为cos(7π/30)与cos(5π/12)。'
        elif n == 3:
            opts = json.loads(row['options_json'])
            opts[3] = '∀x∈(π/2,5π/6]，f(x)∈[-1/2,-1/4]'
            p['options_json'] = json.dumps(opts, ensure_ascii=False)
            p['derivation'] = ('f(x)=1/2 sin(2x+π/6)，故A正确。\n'
                               '对称轴为x=π/6+kπ/2，不含-π/12，B错误。\n'
                               'x∈[5π/3,13π/6]时，相位∈[3π,4π]，函数递增，C正确。\n'
                               'x∈(π/2,5π/6]时，相位∈(2π/3,4π/3]，值域为[-1/2,-1/4]，D正确。')
            p['explain'] = '正确选项为A、C、D；D的原题自变量右端点为闭区间，已恢复。'
        elif n == 4:
            p['derivation'] = ('向左平移π/4得g(x)=2sin(2x+5π/6)，不能写成2cos2x。\n'
                               '在[π/6,π/3]上，f和g均递减，A正确。\n'
                               'g的对称轴为x=-π/6+kπ/2，B错误。\n'
                               'h(x)=tan(2x+π/3)，h(π/12+t)=-cot2t，为t的奇函数，C正确。\n'
                               'f(π/2)=-√3，g(3x/2-π/6)=2cos3x；[0,2π]内方程2cos3x=-√3有6解，D正确。')
            p['explain'] = '正确选项为A、C、D。平移后g(x)=2sin(2x+5π/6)，h的对称中心可位于其图象外。'
        elif n == 5:
            p['derivation'] = ('和差化积得f(x)=cos(2x+π/3)。\n'
                               'f(x-π/3)=cos(2x-π/3)，不是偶函数，A错误。\n'
                               '在x=π/3处相位为π，故该直线是对称轴，B正确。\n'
                               '最小值为-1，不是-√3，C错误。\n'
                               'x∈(π/12,π/3)时相位∈(π/2,π)，函数递减，D正确。')
            p['explain'] = 'f(x)=cos(2x+π/3)，正确选项为B、D。'
        elif n == 15:
            p.update(answer=-1, answer_indices_json='[]', answer_text='',
                     review_status='needs_transcription',
                     review_reason='原图上半题缺失，未给出f(x)的定义；仅凭对称关系不能确定零点数。请补完整原题。',
                     explain='暂停判分：原图缺函数定义，不能确定零点个数。',
                     derivation='已知关系只说明图象关于x=π/6对称，无法单独确定[-π,2π]内的零点个数。原先答案4及对应计数无依据，已撤销。')
        elif n == 16:
            p.update(stem='将函数 f(x)=2tan(ωx+π/6)（ω>0）的图象向左平移π/3个单位，得到函数g(x)的图象。若g(x)为奇函数，则ω的最小值是（ ）',
                     options_json=json.dumps(['1/2', '1', '2', '5/2']), answer=1,
                     answer_indices_json='[1]', skill='正切函数的平移与奇偶性',
                     explain='正确答案B：平移相位为ωπ/3+π/6。正切图象为奇函数要求此相位为kπ/2，最小正ω为1。',
                     derivation='g(x)=2tan(ωx+ωπ/3+π/6)。\n奇函数要求ωπ/3+π/6=kπ/2，k∈Z。\n解得ω=(3k-1)/2，由ω>0知k≥1，最小值为1，选B。')
        elif n == 17:
            p.update(stem='函数 f(x)=2cos(ωx+π/3)，其中ω>0。若对于∀x∈(π/3,2π/3)，都有|f(x)|<2恒成立，则ω的取值不可能是（ ）',
                     options_json=json.dumps(['1/2', '1', '3/2', '2']), answer=2,
                     answer_indices_json='[2]', skill='三角函数严格不等式与参数范围',
                     explain='正确答案C：ω=3/2时，相位区间为(5π/6,4π/3)，包含π，出现|f(x)|=2。注意原题没有平移，且x区间两端均开。',
                     derivation='|f(x)|<2等价于相位ωx+π/3不等于kπ。\nA：相位∈(π/2,2π/3)，成立。\nB：相位∈(2π/3,π)，端点π不取，成立。\nC：相位∈(5π/6,4π/3)，包含π，不成立。\nD：相位∈(π,5π/3)，端点π不取，成立。故选C。')
        elif n == 18:
            p.update(stem='已知关于x的方程 (√3/3)(sinωx−1)=cosωx 在(0,π)内恰有2个不同的实数根，求ω的取值范围（原图选项缺失）。',
                     options_json='[]', answer=-1, answer_indices_json='[]', answer_text='',
                     review_status='needs_transcription',
                     review_reason='原图选项整行截断，无法恢复原选择题；计算范围为7/6<ω≤5/2，仅供核对，补齐选项前暂停判分。',
                     explain='已纠正计算：7/6<ω≤5/2。原选择题选项缺失，暂不设判分答案。',
                     derivation='令t=ωx>0，原方程化为sin t-√3 cos t=1，即2sin(t-π/3)=1。\n解为t=π/2+2kπ或t=7π/6+2kπ；正根依次为π/2、7π/6、5π/2。\n因x∈(0,π)，对应t∈(0,ωπ)。恰有2根要求7π/6<ωπ≤5π/2。\n故7/6<ω≤5/2；右端点可取，因为t=ωπ不在开区间内。')
        out.append(p)
    return out


def repair(db_path, image_directory, apply=False):
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    conn.execute('BEGIN IMMEDIATE' if apply else 'BEGIN')
    try:
        rows = [conn.execute('SELECT * FROM wrong_questions WHERE id=?', (rid,)).fetchone() for rid in IDS]
        assert all(rows), '18个ID必须全部存在'
        assert all(r['topic_id'] == 'wb-math-trigonometry' and r['user_id'] == 'u_family' for r in rows), '题目归属不符'
        cols = {r[1] for r in conn.execute('PRAGMA table_info(wrong_questions)')}
        assert {'answer_indices_json', 'review_status', 'content_version'} <= cols, '请先部署v23迁移'
        others_before = [tuple(r) for r in conn.execute('SELECT * FROM wrong_questions WHERE id NOT IN (' + ','.join('?' * len(IDS)) + ') ORDER BY id', IDS)]
        preserved = ['user_id', 'question_id', 'wrong_count', 'status', 'created_at', 'last_wrong_at', 'cleared_at', 'picked']
        changed = []
        for p in patches(rows):
            rid = p.pop('id')
            path = Path(image_directory) / IMAGE_OWNER / Path(p['image_path']).name
            assert path.is_file() and path.stat().st_size > 1000, f'配图缺失：{path}'
            row = next(r for r in rows if r['id'] == rid)
            delta = {k: v for k, v in p.items() if row[k] != v}
            if not delta:
                continue
            changed.append({'id': rid, 'fields': list(delta)})
            if apply:
                delta.update(ai_analysis=None, ai_model=None, ai_at=None, ai_solve=None, variants=None)
                sql = ','.join(k + '=?' for k in delta)
                cur = conn.execute('UPDATE wrong_questions SET ' + sql + ',content_version=content_version+1 WHERE id=?', [*delta.values(), rid])
                assert cur.rowcount == 1
        if apply:
            others_after = [tuple(r) for r in conn.execute('SELECT * FROM wrong_questions WHERE id NOT IN (' + ','.join('?' * len(IDS)) + ') ORDER BY id', IDS)]
            assert others_before == others_after, '不允许改动其他题目'
            for old in rows:
                new = conn.execute('SELECT * FROM wrong_questions WHERE id=?', (old['id'],)).fetchone()
                assert all(old[k] == new[k] for k in preserved), '不允许改动进度或归属'
            conn.commit()
        else:
            conn.rollback()
        print(json.dumps({'applied': apply, 'changed_count': len(changed), 'ready': 16,
                          'pending': [IDS[14], IDS[17]], 'changes': changed}, ensure_ascii=False, indent=2))
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--db')
    parser.add_argument('--images')
    parser.add_argument('--make-images')
    parser.add_argument('--apply', action='store_true')
    args = parser.parse_args()
    if args.make_images:
        make_images(args.make_images)
    else:
        assert args.db and args.images
        repair(args.db, args.images, args.apply)
