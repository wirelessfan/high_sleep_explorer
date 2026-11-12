"""Check SVG structure, animation timing, references and lesson asset links."""
from __future__ import annotations

import json
import re
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SVG = "{http://www.w3.org/2000/svg}"


def main() -> int:
    errors = []
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
    for path in (ROOT / "content" / "topics").glob("*.json"):
        content = path.read_text(encoding="utf-8")
        json.loads(content)
        for asset in set(re.findall(r"/assets/notes/[^\s\"<>\\]+\.svg", content)):
            if not (ROOT / asset.lstrip("/")).is_file():
                errors.append(f"{path.name}: missing {asset}")
    catalog = json.loads((ROOT / "content" / "catalog.json").read_text(encoding="utf-8"))
    for topic in catalog["topics"]:
        if not (ROOT / "assets" / "notes" / f"intro-{topic['id']}.svg").is_file():
            errors.append(f"{topic['id']}: missing intro")
    for error in errors:
        print("ERROR", error)
    print(f"Checked {len(files)} diagrams and {len(catalog['topics'])} topic intros; {len(errors)} errors")
    return bool(errors)


if __name__ == "__main__":
    raise SystemExit(main())
