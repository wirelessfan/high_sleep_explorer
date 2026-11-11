"""平衡选择题正确答案的位置分布。

原始内容里正确答案大量集中在 A，学生可以靠猜。这个脚本把每道题的
正确选项轮换到 A/B/C/D，使分布接近均匀。可重复运行，结果确定。

用法：
    python tools/balance_answers.py [--dry-run]
"""

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CONTENT = ROOT / "content"
LETTERS = "ABCD"


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


def balance():
    files = sorted((CONTENT / "topics").glob("*.json"))
    counter = 0
    changed = 0
    report = []

    for path in files:
        data = json.loads(path.read_text(encoding="utf-8"))
        for sec in data["sections"]:
            for _holder, q in questions_of(sec):
                opts = q.get("options") or []
                if len(opts) < 2:
                    continue
                n = len(opts)
                ans = q["answer"]
                target = counter % n

                if ans != target:
                    opts[ans], opts[target] = opts[target], opts[ans]
                    q["options"] = opts
                    q["answer"] = target
                    changed += 1

                report.append((path.name, q.get("id", "?"), LETTERS[target]))
                counter += 1

        path.write_text(
            json.dumps(data, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )

    return counter, changed, report


def main():
    dry = "--dry-run" in sys.argv
    if dry:
        # 只统计，不写文件
        total = 0
        dist = {}
        for path in sorted((CONTENT / "topics").glob("*.json")):
            data = json.loads(path.read_text(encoding="utf-8"))
            for sec in data["sections"]:
                for _h, q in questions_of(sec):
                    if len(q.get("options") or []) < 2:
                        continue
                    dist[q["answer"]] = dist.get(q["answer"], 0) + 1
                    total += 1
        print(f"题目总数 {total}")
        for k in sorted(dist):
            print(f"  {LETTERS[k]}: {dist[k]} ({dist[k]/total*100:.1f}%)")
        return 0

    total, changed, _ = balance()
    print(f"处理 {total} 题，调整 {changed} 题")

    # 复核
    dist = {}
    for path in sorted((CONTENT / "topics").glob("*.json")):
        data = json.loads(path.read_text(encoding="utf-8"))
        for sec in data["sections"]:
            for _h, q in questions_of(sec):
                if len(q.get("options") or []) < 2:
                    continue
                dist[q["answer"]] = dist.get(q["answer"], 0) + 1
    for k in sorted(dist):
        print(f"  {LETTERS[k]}: {dist[k]} ({dist[k]/total*100:.1f}%)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
