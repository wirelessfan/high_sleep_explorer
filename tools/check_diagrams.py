"""Check SVG structure, animation timing, references, and 可视化方针 coverage.

Default mode reports coverage as warnings; `--strict` turns a missing or
too-thin figure gallery into an error so CI/deploy can gate on it.
"""
from __future__ import annotations

import argparse
import json
import re
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SVG = "{http://www.w3.org/2000/svg}"
MIN_GALLERY_PAGES = 2


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--strict", action="store_true",
                        help="把图集覆盖不足视为错误（用于新主题验收）")
    args = parser.parse_args()

    errors: list[str] = []
    warnings: list[str] = []
    files = sorted((ROOT / "assets" / "notes").glob("*.svg"))
    for path in files:
        try:
            root = ET.parse(path).getroot()
        except ET.ParseError as exc:
            errors.append(f"{path.name}: {exc}")
            continue
        ids = [el.get("id") for el in root.iter() if el.get("id")]
        if len(ids) != len(set(ids)):
            errors.append(f"{path.name}: duplicate element id")
        for el in root.iter():
            for value in el.attrib.values():
                for ref in re.findall(r"url\(#([^)]*)\)", value):
                    if ref not in ids:
                        errors.append(f"{path.name}: missing reference #{ref}")
            if el.tag in (SVG + "animate", SVG + "animateTransform"):
                values, times = el.get("values"), el.get("keyTimes")
                if values and times and len(values.split(";")) != len(times.split(";")):
                    errors.append(f"{path.name}: animation values/keyTimes mismatch")
                if times:
                    nums = list(map(float, times.split(";")))
                    if nums[0] != 0 or nums[-1] != 1 or any(a > b for a, b in zip(nums, nums[1:])):
                        errors.append(f"{path.name}: invalid animation keyTimes")
        styles = "\n".join(el.text or "" for el in root.iter(SVG + "style"))
        if "background-color:" in styles or "border-color:" in styles:
            errors.append(f"{path.name}: HTML background/border animation used in SVG")

    catalog = json.loads((ROOT / "content" / "catalog.json").read_text(encoding="utf-8"))
    coverage: list[tuple[str, int]] = []
    for topic in catalog["topics"]:
        topic_id = topic["id"]
        data_path = ROOT / "content" / "topics" / f"{topic_id}.json"
        content = data_path.read_text(encoding="utf-8")
        try:
            data = json.loads(content)
        except json.JSONDecodeError as exc:
            errors.append(f"{data_path.name}: {exc}")
            continue

        for asset in set(re.findall(r"/assets/notes/[^\s\"<>\\]+\.svg", content)):
            if not (ROOT / asset.lstrip("/")).is_file():
                errors.append(f"{data_path.name}: missing {asset}")

        intro = ROOT / "assets" / "notes" / f"intro-{topic_id}.svg"
        if not intro.is_file():
            errors.append(f"{topic_id}: missing intro animation")

        pages = data.get("diagrams") or []
        if not isinstance(pages, list):
            errors.append(f"{topic_id}: diagrams 必须是数组")
            pages = []
        seen: set[str] = set()
        for index, page in enumerate(pages):
            if not isinstance(page, dict):
                errors.append(f"{topic_id}: diagrams[{index}] 必须是对象")
                continue
            src = page.get("src")
            if not src:
                errors.append(f"{topic_id}: diagrams[{index}] 缺少 src")
                continue
            if src in seen:
                errors.append(f"{topic_id}: diagrams 重复引用 {src}")
            seen.add(src)
            if not (ROOT / src.lstrip("/")).is_file():
                errors.append(f"{topic_id}: diagrams 引用缺失 {src}")
            for field in ("title", "caption"):
                if not str(page.get(field) or "").strip():
                    errors.append(f"{topic_id}: diagrams[{index}] 缺少 {field}")

        coverage.append((topic_id, len(pages)))
        if len(pages) < MIN_GALLERY_PAGES:
            message = f"{topic_id}: 图解补充仅 {len(pages)} 页（方针要求 ≥{MIN_GALLERY_PAGES}）"
            (errors if args.strict else warnings).append(message)

    for error in errors:
        print("ERROR", error)
    for warning in warnings:
        print("WARN ", warning)
    print(f"Checked {len(files)} diagrams and {len(catalog['topics'])} topic intros; "
          f"{len(errors)} errors, {len(warnings)} warnings")
    print("图集覆盖：")
    for topic_id, count in coverage:
        print(f"  {topic_id:26} {count} 页")
    return bool(errors)


if __name__ == "__main__":
    raise SystemExit(main())
