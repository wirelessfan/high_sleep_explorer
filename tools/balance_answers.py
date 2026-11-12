"""平衡选择题正确答案的位置分布。

原始内容里正确答案大量集中在 A，学生可以靠猜。这个脚本把每道题的
正确选项轮换到 A/B/C/D，使分布接近均匀。可重复运行，结果确定。

两个要点：
1. 基础档的高阶档（sec["tiers"]）也要一起平衡，否则进阶 / 高级题的答案全在 A。
2. 解析里常用「第二项漏了 Ca²⁺」这类位置指代，选项一旦换位就会指错。
   所以换位的同时把解析中的「第 X 项 / 第 X 个选项」重编号到新位置。
   注意：解析里不要写「选 A」这类字母引用——字母会随换位改变，无法自动修正。

用法：
    python tools/balance_answers.py [--dry-run]
"""

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CONTENT = ROOT / "content"
LETTERS = "ABCD"
CN = "一二三四五"
ORDINAL = re.compile(r"第([一二三四五])(项|个选项|个)")


def questions_of(sec):
    """返回 [(holder_dict, question_dict), ...]，holder 是直接持有 answer 的对象。"""
    t = sec.get("type")
    out = []
    if t in ("quiz", "boss"):
        out += [(q, q) for q in sec.get("questions", [])]
    elif t == "levels":
        for lv in sec.get("levels", []):
            out += [(q, q) for q in lv.get("questions", [])]
    elif t == "myths":
        for m in sec.get("myths", []):
            out.append((m["check"], m["check"]))
    elif t == "steps":
        for p in sec.get("problems", []):
            for s in p.get("steps", []):
                out.append((s, s))
    return out


def all_questions(data):
    """顶层（基础档）+ 各高阶档的全部题目。"""
    for sec in data["sections"]:
        yield from questions_of(sec)
        for payload in (sec.get("tiers") or {}).values():
            for key in ("questions", "levels", "blocks", "myths", "problems", "videos"):
                if key not in payload:
                    continue
                sub = {"type": sec.get("type")}
                if key == "questions":
                    sub["questions"] = payload[key]
                elif key == "levels":
                    sub["levels"] = payload[key]
                elif key == "myths":
                    sub["myths"] = payload[key]
                elif key == "problems":
                    sub["problems"] = payload[key]
                else:
                    continue
                yield from questions_of(sub)


def renumber(explain, old_to_new):
    """把解析里的「第 X 项」从旧位置改写为新位置。"""
    if not explain:
        return explain

    def repl(m):
        idx = CN.index(m.group(1))
        if idx not in old_to_new:
            return m.group(0)
        return f"第{CN[old_to_new[idx]]}{m.group(2)}"

    return ORDINAL.sub(repl, explain)


def balance(dry_run=False):
    files = sorted((CONTENT / "topics").glob("*.json"))
    counter = 0
    moved = 0
    renum = 0

    for path in files:
        data = json.loads(path.read_text(encoding="utf-8"))
        for _holder, q in all_questions(data):
            opts = q.get("options") or []
            if len(opts) < 2:
                continue
            n = len(opts)
            ans = q["answer"]
            target = counter % n
            counter += 1

            if ans != target:
                # 记录「旧下标 -> 新下标」，用于同步改解析里的位置指代
                order = list(range(n))
                order[ans], order[target] = order[target], order[ans]
                old_to_new = {old: new for new, old in enumerate(order)}
                q["options"] = [opts[old] for old in order]
                q["answer"] = target
                moved += 1

                for key in ("explain",):
                    if key in q:
                        before = q[key]
                        q[key] = renumber(before, old_to_new)
                        if q[key] != before:
                            renum += 1

        if not dry_run:
            path.write_text(
                json.dumps(data, ensure_ascii=False, indent=2) + "\n",
                encoding="utf-8",
            )

    return counter, moved, renum


def distribution():
    total = 0
    dist = {}
    for path in sorted((CONTENT / "topics").glob("*.json")):
        data = json.loads(path.read_text(encoding="utf-8"))
        for _h, q in all_questions(data):
            if len(q.get("options") or []) < 2:
                continue
            dist[q["answer"]] = dist.get(q["answer"], 0) + 1
            total += 1
    return total, dist


def main():
    dry = "--dry-run" in sys.argv
    total, moved, renum = balance(dry_run=dry)
    if dry:
        print(f"[dry-run] 共 {total} 题，其中 {moved} 题需要换位，{renum} 条解析需要重编号")
    else:
        print(f"处理 {total} 题，调整 {moved} 题，重编号解析 {renum} 条")

    n, dist = distribution()
    for k in sorted(dist):
        print(f"  {LETTERS[k]}: {dist[k]} ({dist[k] / n * 100:.1f}%)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
