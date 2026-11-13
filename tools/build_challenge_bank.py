"""生成固定挑战变式、逐题审校清单与来源索引。基础档不参与生成。

python tools/build_challenge_bank.py
仅重放内容模型，不下载资料，不依赖第三方包。公开来源获取证据见content/challenge_sources.json。
"""
from collections import Counter
from copy import deepcopy
import hashlib
import html
import json
from pathlib import Path
import random
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from tools.challenge_models import BUILDERS
from tools.check_content import questions_of, section_tiers

REVISION = 'challenge-2026-11-13'
METHODS = {
    'physics-kinematics': '分段运动先找时间域；刹车公式只用到停车时刻，不能让车辆自动倒车。相对距离D的极值要用相对速度D′=0定位，再与各转段端点比较。纸带相邻位移差为aΔt²；时间标定误差要按平方传播。',
    'physics-newton': '先假设共速，算出所需静摩擦并与上限比较，超限后分别列ma。板长、余量由相对位移判断。弹簧形变在剪断其他连接的瞬间保持；绳模型圆周最高点要求张力非负，之后才联立能量。',
    'physics-energy': '按过程分别选择守恒量：碰撞先用动量，上升再用机械能；粗糙段用功能关系。摩擦生热用相对滑程。变力功可用F-x图像面积；恒功率阶段牵引力P/v随速率改变，不能当匀加速。',
    'physics-electric': '先判断电容器断电（Q固定）或接电（U固定）。储能可写Q²/(2C)或CU²/2，变形时要把电源功UΔQ和外力功一同记账。粒子偏转先用qU=mv²/2求入射速度；零场点按矢量方向分区，零势点按标量代数和求。',
    'physics-induction': '动生感应由E=BLv、I=E/R、F=BIL串联。无外力磁阻尼不是匀减速，累加mΔv=−BLIΔt可求通过电荷，再用q=ΔΦ/R求位移。热量按动能损失或I²R累计，反向电流电荷可相消而热量不相消。',
    'chemistry-equilibrium': '三段式先守恒再代入K；Q描述当前组成，K由温度决定。扰动瞬间先算Q，不能把它当作新平衡。恒容加惰性气体不改变参与者浓度，恒压加入会稀释。异相体系先检查固体库存能否支撑Q=K。',
    'chemistry-mole': '结晶水进入称量摩尔质量，但离子计数仍按溶质化学式。取样带走溶质，单纯加水不带走；多次操作分别记n、V。混合物反推要有两个独立观测，限量试剂比较n/计量系数。分样滴定最后按总体积与样品体积的比放大。',
    'chemistry-redox': '先区分每个价态来源，再用电子得失相等；歧化中得电子与失电子只是同一转移的两端，不重复相加。硝酸既作氧化剂也提供成盐阴离子。多步滴定用中间产物串联，误差百分比以真值为分母。',
    'chemistry-periodic': '从离子电子数恢复原子序数时要补回失去的电子或扣掉得到的电子。等电子离子核电荷越大半径越小。逐级电离能大跃升可定位价电子数。位、构、性推断后再写反应，注意铝两性、过氧化物价态和共价网络的结构例外。',
    'chemistry-ionic': '混合先改浓度，再算Q与Ksp。加碱沉铝、加酸碳酸根等按当量分段，不能一式算全程。弱电解质保留分子形式；旁观离子仍进入电荷守恒。选择性沉淀要比较起沉所需浓度并核算残余量，不能只看沉淀先后。',
    'math-derivative': '先写定义域和工艺可行域，再求驻点与导数符号。全局最值要比较端点、极限及驻点；导数在孤立一点为零不代表函数不严格单调。数根要结合每个单调区间值域；过外点切线另设切点，不将外点横坐标直接代入导数。',
}


def digest(data):
    return hashlib.sha256(json.dumps(data, ensure_ascii=False, sort_keys=True).encode()).hexdigest()


def build():
    source_data = json.loads((ROOT/'content/challenge_sources.json').read_text('utf8'))
    sources={s['id']:s for s in source_data['sources']}
    previous=json.loads((ROOT/'reports/question-review-2026-11-13.json').read_text('utf8'))
    old_rows={r['key']:r for r in previous['questions']}
    rows=[]; basics={}; files={}
    for topic,builder in BUILDERS.items():
        path=ROOT/f'content/topics/{topic}.json'
        data=json.loads(path.read_text('utf8'))
        basic_before={s['id']:section_tiers(s)['basic'] for s in data['sections']}
        basics[topic]=digest(basic_before)
        index=0
        for sec in data['sections']:
            for tier,payload in sec.get('tiers',{}).items():
                if tier not in ('advanced','expert'):continue
                full={**payload,'type':sec['type']}
                count=len(questions_of(full))
                payload['intro']=('多条件综合训练：请先列式、检查边界，再选择完整结论。' if count else '挑战题方法：模型、守恒、临界条件和结果复核。')
                payload['minutes']=max(8,count*5) if count else 10
                if sec['type']=='reading':
                    payload['blocks']=[
                        {'h':'先建模，再计算','p':'先明确对象、参考方向、反应前后状态和允许范围。公式中的条件也是题目的一部分，不满足条件时要更换模型。'},
                        {'h':'三个复核动作','p':'一查单位和符号；二查守恒、总量与不等式边界；三把结果代回原条件。含参题同时检查临界等号、端点以及形式解是否越界。'},
                        {'h':'本主题的关键模型','p':METHODS[topic]},
                        {'h':'练习方式','p':'本档题目以多步骤推理为目标。建议遮住选项，先在纸上独立求解；每道完整结论通常需要至少三项分析。实战训练的各小题为独立情境，不共用数值条件。'},
                        {'h':'公开题源与独立改编','p':'<a href="'+html.escape(sources[topic.split('-',1)[1]]['url'],quote=True)+'" target="_blank" rel="noopener noreferrer">'+html.escape(sources[topic.split('-',1)[1]]['title'])+'</a>；'+html.escape(sources[topic.split('-',1)[1]]['reference'])+'。作者：'+html.escape(sources[topic.split('-',1)[1]]['authors'])+'，OpenStax / Rice University，CC BY-NC-SA 4.0。题目独立改编情境、数值及设问，加入高中范围的临界和反推条件。'},
                    ]
                    payload['videos']=[]
                    continue
                if sec['type']=='levels':
                    for li,lv in enumerate(payload['levels']):lv['name']=f'第{li+1}关 · 多条件综合与检验'
                if sec['type']=='steps':
                    for p in payload['problems']:
                        p['stem']='综合迁移训练：以下各小题情境独立，按各题给定条件作答。请先写关键方程，再核验可行条件；上一小题的数值不用于下一小题。'
                for qid,item in questions_of(full):
                    # 全主题连续分配，避免同一模型以相同数值跨版块重复。
                    model_index=index%8; variant=index//8; index+=1
                    authored=builder(model_index,variant)
                    key=f"{topic}/{sec['id']}/{tier}/{qid}"
                    options=list(authored['options']); random.Random(key).shuffle(options)
                    correct=authored['options'][0]; answer=options.index(correct)
                    item.clear()
                    if sec['type'] in ('quiz','boss','levels'):item['id']=qid
                    item.update(skill=authored['skill'],options=options,answer=answer,
                                explain=authored['explain'],revision=REVISION,
                                source_id=topic.split('-',1)[1])
                    item['ask' if sec['type']=='steps' else 'stem']=authored['stem']
                    # 提示只给审题方法，不直接给数值或该题的答案。
                    if sec['type']=='myths':
                        m=payload['myths'][int(qid[1:])]
                        m.update(title=authored['skill'],wrong='看到关键词就直接套公式，不检查公式的条件与各阶段的约束。',
                                 why='同一题可能同时涉及不同过程或不同守恒对象；形式上算出的结果，还必须满足题设范围。',
                                 right='先列对象、条件和目标量，再将每条结论代回检验。方法提示不替代独立计算。')
                    # 评分针对任务而不是档位。7分必须有明确的耦合/分支/全域证明。
                    raw=authored['difficulty']
                    support=.25 if sec['type']=='myths' else 0
                    rating=max(6,raw-support)
                    old=old_rows.get(key,{})
                    rows.append(dict(key=key,topic=topic,section=sec['id'],tier=tier,qid=qid,
                        model=authored['model'],variant=variant,skill=authored['skill'],
                        stem=authored['stem'],options=options,answer=answer,explain=authored['explain'],
                        difficulty=rating,unassisted_difficulty=raw,support_adjustment=support,
                        usefulness=8 if topic=='chemistry-periodic' else 9,
                        demands=authored['demands'],evidence=authored['evidence'],
                        previous_difficulty=old.get('difficulty'),source_id=topic.split('-',1)[1]))
        basic_after={s['id']:section_tiers(s)['basic'] for s in data['sections']}
        assert basic_before==basic_after,topic
        path.write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n','utf8',newline='\n')
        files[topic]=hashlib.sha256(path.read_bytes()).hexdigest()
    stats={t:dict(count=len(rs),models=len({r['model'] for r in rs}),
          difficulty=round(sum(r['difficulty'] for r in rs)/len(rs),2),
          usefulness=round(sum(r['usefulness'] for r in rs)/len(rs),2))
           for t in BUILDERS for rs in [[r for r in rows if r['topic']==t]]}
    report=dict(revision=REVISION,scope='仅替换已有进阶、高级；基础档保留上一轮校正结果',
        methodology='教学任务估计，非学生实测。6分：至少三项相互关联的分析；7分：另需耦合模型、分段/分类、全域证明或边界排除。难点剖析有方法提示，7分题扣0.25；实战小题为独立完整情境，无逐式提示。',
        limitations='固定数值变式不等于独立模型数。88个模型共476道变式；定量验证不替代真实学生试做，尚无正确率/作答时间标定。',
        count=len(rows),models=len({r['model'] for r in rows}),topics=stats,
        preserved_basic_sha256=basics,content_sha256=files,questions=rows)
    out=ROOT/'reports/challenge-upgrade-2026-11-13'
    out.with_suffix('.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n','utf8')
    table='\n'.join(f"| {t} | {v['count']} | {v['models']} | {v['difficulty']} | {v['usefulness']} |" for t,v in stats.items())
    md=f'''# 题库挑战升级 · 2026-11-13

保留431道基础题，替换476道进阶/高级计分题，来自88个独立模型的固定变式。全库仍为907题。

{report['methodology']}

{report['limitations']}

| 主题 | 升级题数 | 模型数 | 难度/10 | 实用性/10 |
|---|---:|---:|---:|---:|
{table}

具体题干、答案、推理负担、验证参数、旧评分及来源标识见同名JSON；来源见[公开题源](../content/challenge_sources.json)。
基础档哈希以本次升级前已经校正的内容为基准；此前纠错记录保留于question-review-2026-11-13报告。

旧学习进度及奖励不重置。错题本按内容指纹保留版本，新旧题不会混用答案；分步题快照补齐父题情境。
'''
    out.with_suffix('.md').write_text(md,'utf8')
    trs=[]
    for r in rows:
        esc=lambda x:html.escape(str(x))
        trs.append('<tr>'+''.join(f'<td>{esc(v)}</td>' for v in [r['topic'],r['tier'],r['qid'],r['model'],r['difficulty'],r['usefulness'],r['stem'],' / '.join(r['demands']),r['options'][r['answer']],r['explain']])+'</tr>')
    out.with_suffix('.html').write_text('''<!doctype html><meta charset="utf-8"><title>挑战题升级审校</title><style>body{font:15px system-ui;margin:24px;color:#243247}table{border-collapse:collapse}td,th{padding:12px;border:1px solid #ddd;vertical-align:top;min-width:80px}td:nth-child(7),td:last-child{min-width:360px}input{padding:12px;width:70%;margin:16px}thead{background:#edf3fb}th{position:sticky;top:0;background:#edf3fb}</style><h1>挑战题升级：476题 / 88个模型</h1><p>目标难度6–7/10；仅为教学估计，尚无学生实测。431道基础热身题保留。输入主题、模型或关键词筛选。</p><input id="query" placeholder="例如 physics-newton / 临界 / 恒成立"><table><thead><tr>'''+''.join(f'<th>{x}</th>' for x in ['主题','档位','题号','模型','难度','实用性','题干','推理要求','答案','解析'])+'</tr></thead><tbody>'+''.join(trs)+'''</tbody></table><script>document.querySelector('#query').oninput=e=>{const v=e.target.value.toLowerCase();document.querySelectorAll('tbody tr').forEach(r=>r.hidden=!r.textContent.toLowerCase().includes(v))}</script>''','utf8')
    print(json.dumps({'count':len(rows),'models':report['models'],'topics':stats},ensure_ascii=False,indent=2))


if __name__=='__main__':build()
