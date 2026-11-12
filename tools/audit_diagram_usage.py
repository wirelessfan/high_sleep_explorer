"""Audit figure usage: gallery entries vs images embedded in a topic's blocks."""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def embedded_images(data):
    """images declared in summary/tier blocks (reading flow), excluding diagrams."""
    out = set()
    groups = []
    for sec in data["sections"]:
        groups.append(sec)
        for payload in (sec.get("tiers") or {}).values():
            if isinstance(payload, dict):
                groups.append({"type": sec.get("type"), **payload})
    for g in groups:
        for b in g.get("blocks", []) or []:
            for key in ("image", "diagram"):
                if b.get(key):
                    out.add(b[key])
    return out


def main() -> int:
    catalog = json.loads((ROOT / "content" / "catalog.json").read_text(encoding="utf-8"))
    for topic in catalog["topics"]:
        tid = topic["id"]
        data = json.loads((ROOT / "content" / "topics" / f"{tid}.json").read_text(encoding="utf-8"))
        hero = f"/assets/notes/intro-{tid}.svg"
        gallery = [d["src"] for d in (data.get("diagrams") or [])]
        emb = embedded_images(data)
        dup_hero = [s for s in gallery if s == hero]
        dup_emb = [s for s in gallery if s in emb]
        twins = []
        anim = {s.replace("-anim", "") for s in gallery if "-anim" in s}
        for s in gallery:
            if "-anim" not in s and s in anim:
                twins.append(s)
        unique = [s for s in gallery if s not in dup_hero and s not in dup_emb and s not in twins]
        flags = []
        if dup_hero:
            flags.append(f"hero重复:{len(dup_hero)}")
        if dup_emb:
            flags.append(f"与正文重复:{len(dup_emb)}")
        if twins:
            flags.append(f"动/静同图:{len(twins)}")
        print(f"{tid:26} 图集{len(gallery)} 独立{len(unique)} " + (" ".join(flags) if flags else "OK"))
        if dup_emb or twins:
            for s in dup_emb + twins:
                print(f"    - {s}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
