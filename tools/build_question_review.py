"""生成本次题库审校的逐题估分与可筛选报告（标准库，无服务依赖）。

python tools/build_question_review.py --base a7239bd --date 2026-11-13
评分是公开规则的教学估计，不是学生正确率或试卷得分预测。
"""
import argparse
from collections import Counter, defaultdict
import hashlib
import html
import json
from pathlib import Path
import re
import statistics
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from tools.check_content import questions_of, section_tiers

TIER_NAMES = {"basic": "基础", "advanced": "进阶", "expert": "高级"}


def plain(value):
    return html.unescape(re.sub(r"<[^>]+>", " ", value or "")).strip()


def question_rows(data):
    for sec in data["sections"]:
        for tier, content in section_tiers(sec).items():
            for qid, q in questions_of(content):
                context = ""
                if content["type"] == "steps":
                    context = content["problems"][int(qid[1:qid.index("s")])]["stem"]
                yield sec, tier, content, qid, q, context


def estimate(topic, content, q, context, duplicate):
    """依任务特征评分；档位名称不参与难度计算。取最高匹配认知层次。"""
    stem = plain(q.get("stem", q.get("ask", "")))
    skill = q.get("skill", "")
    task = skill + " " + stem
    complexity = skill + " " + plain(context) + " " + stem
    difficulty, kind = 2, "概念辨认或直接性质判断"
    if re.search(r"计算|多少|大小|为：|等于|求导|导数|方程式|配平|概率|离心率|速率|电荷量", task):
        difficulty, kind = 3, "公式应用或一步判断"
    if re.search(r"图像|比较|守恒|功率|转化率|浓度|平均|追及|相遇|偏转|瞬时|定义域|电离|少量|过量|纸带|加速度|热量|电荷量|缺项配平|歧化|电流波形|叠加|电势能", task):
        difficulty, kind = 4, "条件辨析或短计算链"
    if re.search(r"推断|检验|等效|先后顺序|物质推断|两根.*导体棒|双杆|自感|多过程|三段式|切点|过点|切线条数|混合气体|传送带|三力平衡|反求|实根|联立|不相撞|最近距离|最小.*距离|最小.*加速度|最大速度|复指数|i\^i", complexity):
        difficulty, kind = 5, "模型选择或多条件推理"
    if re.search(r"恒成立|存在性|参数|含参|取值范围|零点个数|电容|极值点.*已知|最大.*最小|最小.*最大|板块|滑板|板长|耦合", complexity):
        difficulty, kind = 6, "边界、参数或组合模型"
    if re.search(r"分类讨论|双重|多平衡|电容.*电阻|电阻.*电容|既.*极大.*又.*极小", complexity):
        difficulty, kind = 7, "综合分类或耦合分析"
    if content["type"] == "steps":
        difficulty = max(2, difficulty - 1)
        kind += "；分步提示已降低独立求解负担"
    usefulness = 7
    use_reason = "覆盖高中复习中的常用知识与方法"
    if content["type"] == "myths" or re.search(r"易错|守恒|误差|定义域|少量|过量|临界|电离|独立|必要|充分", task):
        usefulness = 9
        use_reason = "可诊断常见误解或训练条件意识"
    elif difficulty >= 4:
        usefulness = 8
        use_reason = "适合常规模型迁移与解题训练"
    flags, advice = [], []
    if duplicate:
        usefulness = max(5, usefulness - 2)
        flags.append("同题干同选项复现")
        advice.append("用于间隔复习；独立测评时合并重复题")
    if "scholar-card" in q.get("stem", ""):
        usefulness = max(4, usefulness - 1)
        difficulty = max(1, difficulty - 1)
        flags.append("题干含解法提示")
        advice.append("教学模式保留提示，测评模式将提示移至答后")
    if topic == "math-euler" and re.search(r"e\^|欧拉|指数|i\^i", task + " " + plain(context)):
        usefulness = min(usefulness, 5)
        use_reason = "适合数学兴趣拓展，复指数、级数及复对数不属常规高中必备训练"
        flags.append("兴趣拓展")
        advice.append("作为选学，优先完成三角、导数与概率主线")
    if not advice:
        advice.append("保留作概念热身" if difficulty <= 3 else "保留，答后补写关键条件及推导过程")
    return usefulness, difficulty, use_reason, kind, flags, advice


def build(base, date):
    rows, topic_stats = [], []
    files = []
    seen = set()
    overrides = json.loads((ROOT / "tools/question_review_overrides.json").read_text(encoding="utf8"))
    cat = json.loads((ROOT / "content/catalog.json").read_text(encoding="utf8"))
    for item in cat["topics"]:
        path = ROOT / f"content/topics/{item['id']}.json"
        data = json.loads(path.read_text(encoding="utf8"))
        old = json.loads(subprocess.check_output(["git", "show", f"{base}:content/topics/{item['id']}.json"], cwd=ROOT, encoding="utf8"))
        previous = {f"{s['id']}/{t}/{qid}": (q, ctx) for s, t, c, qid, q, ctx in question_rows(old)}
        files.append({"path": str(path.relative_to(ROOT)).replace("\\", "/"), "sha256": hashlib.sha256(path.read_bytes()).hexdigest()})
        start = len(rows)
        for sec, tier, content, qid, q, context in question_rows(data):
            key = f"{data['id']}/{sec['id']}/{tier}/{qid}"
            signature = (data["id"], plain(q.get("stem", q.get("ask", ""))), tuple(sorted(q["options"])), plain(context))
            duplicate = signature in seen
            seen.add(signature)
            u, d, ur, dr, flags, advice = estimate(data["id"], content, q, context, duplicate)
            override = overrides.get(key)
            if override:
                d = override.get("difficulty", d)
                u = override.get("usefulness", u)
                dr = override.get("reason", dr)
                advice = [a for a in advice if a not in ("保留作概念热身", "保留，答后补写关键条件及推导过程")]
                if not advice:
                    advice.append("保留作概念热身" if d <= 3 else "保留，答后补写关键条件及推导过程")
                if override.get("repeat"):
                    flags.append("同模型近似复现")
                    u = max(5, u - 1)
                    advice.append("与" + override["repeat"] + "配合作间隔复习，独立测评可换情境")
            if tier == "expert" and d <= 3:
                flags.append("高级档偏易")
                advice.append("可移至基础或进阶，腾出高级档给无提示综合题")
            changed = previous.get(f"{sec['id']}/{tier}/{qid}") != (q, context)
            rows.append(dict(key=key, topic_id=data["id"], topic=data["title"], subject=data["subject"],
                             tier=tier, tier_name=TIER_NAMES[tier], section=sec["name"], section_id=sec["id"],
                             type=content["type"], question_id=qid, context=plain(context),
                             stem=plain(q.get("stem", q.get("ask", ""))), skill=q.get("skill", ""),
                             options=q["options"], answer_index=q["answer"], answer=q["options"][q["answer"]],
                             explanation=plain(q["explain"]), usefulness=u, difficulty=d,
                             usefulness_reason=ur, difficulty_reason=dr, flags=flags, advice=advice,
                             rating_method="逐题复核覆盖规则" if override else "任务特征规则估分",
                             revised=changed, source=files[-1]["path"]))
        group = rows[start:]
        topic_stats.append(dict(id=data["id"], title=data["title"], count=len(group),
                                revised=sum(r["revised"] for r in group),
                                usefulness=round(statistics.mean(r["usefulness"] for r in group), 2),
                                difficulty=round(statistics.mean(r["difficulty"] for r in group), 2)))
    metadata = dict(date=date, base=base, count=len(rows),
                    methodology="AI内容审阅后，以公开认知任务规则估分，并对易被关键词误判的题目单独覆盖评分（见rating_method及overrides文件）。网站档位不参与难度计算；分步题按每步计分。实用性面向高中复习，不等于生活用途。未使用学生作答数据，未经过教研专家复核；建议评分视为约±1至2分的初步估计。",
                    difficulty_rubric="1–2识记；3–4单步应用/条件辨析；5–6多条件、边界或参数；7–8综合分类与模型联动；9–10高难开放/竞赛。本批均为提示较充分的选择或分步题，规则没有判到9–10。",
                    usefulness_rubric="9–10高价值诊断与迁移；7–8常用知识和模型；5–6重复巩固或选学；1–4与当前目标联系较弱。重复题、提前透露解法及超出高中主线会降分。",
                    revised_question_units=sum(r["revised"] for r in rows),
                    usefulness=round(statistics.mean(r["usefulness"] for r in rows), 2),
                    difficulty=round(statistics.mean(r["difficulty"] for r in rows), 2),
                    flags=dict(Counter(f for r in rows for f in r["flags"])),
                    sources=files, topics=topic_stats)
    out = ROOT / "reports"
    out.mkdir(exist_ok=True)
    prefix = f"question-review-{date}"
    payload = {"metadata": metadata, "questions": rows}
    (out / f"{prefix}.json").write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf8")
    template = (ROOT / "tools/question_review_template.html").read_text(encoding="utf8")
    (out / f"{prefix}.html").write_text(template.replace("__REVIEW_DATA__", json.dumps(payload, ensure_ascii=False).replace("<", "\\u003c")), encoding="utf8")
    lines = [f"# 题库审校与评价 · {date}", "", f"已从 b394d2f 快进同步到 {base}（6个提交）。覆盖16主题、907道计分单元、228个学习单元，其中190个作答单元、38个阅读单元。", "",
             f"相对同步后的基线，{metadata['revised_question_units']}道计分单元的题目、解析或分步父题干发生修订；配套阅读、误区说明另有修订。修订条目不是错误题数，详见 changes.json。", "",
             f"规则估分均值：实用性 **{metadata['usefulness']}/10**，难度 **{metadata['difficulty']}/10**。", "", metadata["methodology"], "", metadata["difficulty_rubric"], "", metadata["usefulness_rubric"], "",
             "|主题|题数|修订计分单元|实用性/10|难度/10|", "|---|---:|---:|---:|---:|"]
    lines.extend(f"|{t['title']}|{t['count']}|{t['revised']}|{t['usefulness']}|{t['difficulty']}|" for t in topic_stats)
    lines += ["", "## 主要发现与建议", "",
              "- 适合每天短时复习，概念辨析、常见错误诊断、分步引导较实用。",
              f"- {metadata['flags'].get('高级档偏易', 0)}道高级档题被规则判为3分及以下；档位附带的70–95分宣传不能当成实测能力对应。建议按实际任务重新分层。",
              f"- 精确题干及选项匹配发现{metadata['flags'].get('同题干同选项复现', 0)}道重复；另逐题标出{metadata['flags'].get('同模型近似复现', 0)}道同模型近似复现。后者只列出已核对的例子，不是全库语义去重统计。",
              f"- {metadata['flags'].get('题干含解法提示', 0)}道题在题干中给出手卡提示；适合教学，削弱独立测评价值。",
              "- 欧拉主题适合兴趣拓展；其级数、复指数及复对数内容不宜作为普通高中掌握要求。五个新增数学主题仅有基础档。",
              "- 分步题当前以作答完整判完成，不等于掌握；建议后续区分完成与正确掌握。此轮保留现有产品规则。", "",
              "## 修订例子", "",
              "- 等质量弹簧连接体撤力后加速度改为F/(2m)；固定+4q与+q的零场点改为两电荷之间、距q为L/3。",
              "- 带电粒子加速题质量与数值统一；电子偏转题修正板距，保证不会在出射前撞板。",
              "- 液态CCl4的22.4 L所含分子数改为大于NA；去掉气体摩尔质量28题中N2/C2H4的双正确项。",
              "- 补齐概率独立性、换元角范围、椭圆非退化等条件；改正极值与导数、单调区间端点的过度概括。",
              "- 修正周期元素推断自相矛盾、平衡等效多解、离子反应条件及解析错位。",
              "- 修复内容检查器缩进导致只检查每组末题的问题；阅读单元不再算成1道题，修正页面题量虚增。", "",
              "- 修复难点剖析小测答完后提交按钮仍禁用的阻塞；阅读完成反馈改为阅读已完成，不再显示虚构的答对1/1题。", "",
              "## 验证与交付", "",
              "逐题作答接口回归覆盖907题：190单元分别全错与全对提交，并验证38阅读单元及全部228单元答案隐藏。分步题全错仍完成符合现有规则。测试使用临时数据库。", "",
              f"[逐题可筛选报告]({prefix}.html) · [完整评分数据]({prefix}.json) · [逐项修订前后]({prefix}-changes.json)", "",
              "本地修订，尚未提交、推送或部署。页面抽查与最终检查结果见 verification.md。"]
    (out / f"{prefix}.md").write_text("\n".join(lines) + "\n", encoding="utf8")
    print(json.dumps({k: v for k, v in metadata.items() if k not in ("sources", "topics")}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--base", default="a7239bd")
    parser.add_argument("--date", default="2026-11-13")
    args = parser.parse_args()
    build(args.base, args.date)
