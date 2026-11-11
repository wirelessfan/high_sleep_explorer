"""内容自检：答案完整性、选项重复、解析非空。"""

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CONTENT = ROOT / "content"


def load(p):
    return json.loads((CONTENT / p).read_text(encoding="utf-8"))


CONTENT_KEYS = ("questions", "levels", "blocks", "videos", "myths", "problems", "egg")
TIERS = ("basic", "advanced", "expert")


def section_tiers(sec):
    """与 app.content_loader.section_tiers 同口径：顶层内容 = 基础档。"""
    out = {}
    if any(k in sec for k in CONTENT_KEYS):
        out["basic"] = {k: v for k, v in sec.items() if k != "tiers"}
    for tid, payload in (sec.get("tiers") or {}).items():
        item = {k: v for k, v in sec.items() if k not in CONTENT_KEYS and k != "tiers"}
        item.update(payload or {})
        out[tid] = item
    return out


def questions_of(sec):
    t = sec.get("type")
    if t in ("quiz", "boss"):
        return [(q["id"], q) for q in sec.get("questions", [])]
    if t == "levels":
        out = []
        for lv in sec.get("levels", []):
            out += [(q["id"], q) for q in lv.get("questions", [])]
        return out
    if t == "myths":
        return [(f"m{i}", m["check"]) for i, m in enumerate(sec.get("myths", []))]
    if t == "steps":
        out = []
        for pi, p in enumerate(sec.get("problems", [])):
            for si, s in enumerate(p.get("steps", [])):
                out.append((f"p{pi}s{si}", s))
        return out
    return []


def main():
    errors = []
    warnings = []

    catalog = load("catalog.json")
    topic_ids = [t["id"] for t in catalog["topics"]]

    for tid in topic_ids:
        data = load(f"topics/{tid}.json")
        if data.get("id") != tid:
            errors.append(f"{tid}: id 不匹配")

        sec_ids = [s["id"] for s in data["sections"]]
        expect = [s["id"] for s in catalog["sections"]]
        if sec_ids != expect:
            errors.append(f"{tid}: 版块顺序 {sec_ids} != {expect}")

        total_q = 0
        tier_counts = {t: 0 for t in TIERS}
        for sec in data["sections"]:
            tiers = section_tiers(sec)
            seen_ids = set()
            for tier_id in tiers:
                if tier_id not in TIERS:
                    errors.append(f"{tid}/{sec['id']}: 未知档位 {tier_id}")
            for tier_id, content in tiers.items():
                for qid, q in questions_of(content):
                    total_q += 1
                    tier_counts[tier_id] = tier_counts.get(tier_id, 0) + 1
                    # myths / steps 的 id 是按下标合成的（m0、p0s0），跨档位重复属正常
                    if content["type"] in ("quiz", "levels", "boss"):
                        if qid in seen_ids:
                            errors.append(f"{tid}/{sec['id']}/{tier_id}/{qid}: 同版块内题号重复")
                        seen_ids.add(qid)
                opts = q.get("options") or []
                if len(opts) < 2:
                    errors.append(f"{tid}/{sec['id']}/{tier_id}/{qid}: 选项少于 2 个")
                if len(set(opts)) != len(opts):
                    errors.append(f"{tid}/{sec['id']}/{tier_id}/{qid}: 选项重复")
                ans = q.get("answer")
                if not isinstance(ans, int) or not (0 <= ans < len(opts)):
                    errors.append(f"{tid}/{sec['id']}/{tier_id}/{qid}: answer 越界 ({ans})")
                if not (q.get("explain") or "").strip():
                    errors.append(f"{tid}/{sec['id']}/{tier_id}/{qid}: 解析为空")
                if "skill" not in q and content["type"] in ("quiz", "levels", "boss"):
                    warnings.append(f"{tid}/{sec['id']}/{tier_id}/{qid}: 缺少 skill 标签")

            for tier_id, content in tiers.items():
                if content["type"] == "reading" and not content.get("blocks"):
                    errors.append(f"{tid}/{sec['id']}/{tier_id}: 阅读版块无内容")
        print(f"  {tid}: {len(data['sections'])} 版块 / {total_q} 题 "
              f"(基础 {tier_counts['basic']} · 进阶 {tier_counts['advanced']} · 高级 {tier_counts['expert']})")

    # 卡片
    cards = load("cards/cards.json")["cards"]
    ids = [c["id"] for c in cards]
    if len(set(ids)) != len(ids):
        errors.append("卡片 id 重复")
    rewards = load("rewards.json")
    for set_id, s in rewards["sets"].items():
        for cid in s["cards"]:
            if cid not in ids:
                errors.append(f"套装 {set_id} 引用不存在的卡 {cid}")
    for c in cards:
        img = ROOT / "assets" / "cards" / c["image"]
        if not img.exists():
            errors.append(f"卡片 {c['id']} 图片缺失: {c['image']}")
        if c["rarity"] not in rewards["gacha"]["rarity"]:
            errors.append(f"卡片 {c['id']} 稀有度非法: {c['rarity']}")

    # 稀有度覆盖
    rarities = {c["rarity"] for c in cards}
    for r in rewards["gacha"]["rarity"]:
        if r not in rarities:
            warnings.append(f"稀有度 {r} 没有对应卡片")

    print(f"\n卡片: {len(cards)} 张")
    if warnings:
        print(f"\n警告 {len(warnings)}:")
        for w in warnings:
            print("  ! " + w)
    if errors:
        print(f"\n错误 {len(errors)}:")
        for e in errors:
            print("  [X] " + e)
        return 1
    print("\nOK 内容自检通过")
    return 0


if __name__ == "__main__":
    sys.exit(main())
