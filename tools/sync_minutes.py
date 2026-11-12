"""把主题时长同步为「已开放单元逐段累加」的真实值。

`content/topics/*.json` 顶层的 `minutes` 与 `content/catalog.json` 里主题的
`minutes` 都是展示用的缓存值，真正口径是 `content_loader.topic_minutes()`
（按已开放单元累加）。每次补档、加版块之后跑一次本脚本即可，幂等。

用法：
    python tools/sync_minutes.py [--dry-run]
"""

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app import content_loader  # noqa: E402

TOPICS = ROOT / "content" / "topics"
CATALOG = ROOT / "content" / "catalog.json"


def main():
    dry = "--dry-run" in sys.argv
    content_loader.clear_cache()

    changed = []
    for path in sorted(TOPICS.glob("*.json")):
        data = json.loads(path.read_text(encoding="utf-8"))
        tid = data["id"]
        real = content_loader.topic_minutes(tid)
        if data.get("minutes") == real:
            continue
        changed.append((tid, data.get("minutes"), real))
        data["minutes"] = real
        if not dry:
            path.write_text(
                json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
            )

    catalog = json.loads(CATALOG.read_text(encoding="utf-8"))
    cat_changed = 0
    for meta in catalog["topics"]:
        tid = meta["id"]
        real = content_loader.topic_minutes(tid)
        if meta.get("minutes") == real:
            continue
        cat_changed += 1
        if not dry:
            meta["minutes"] = real
    if not dry and cat_changed:
        CATALOG.write_text(
            json.dumps(catalog, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )

    tag = "[dry-run] " if dry else ""
    print(f"{tag}主题文件更新 {len(changed)} 个，catalog 更新 {cat_changed} 条")
    for tid, old, new in changed:
        print(f"  {tid}: {old} -> {new} 分钟")
    return 0


if __name__ == "__main__":
    sys.exit(main())
