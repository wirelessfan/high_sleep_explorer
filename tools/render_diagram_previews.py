"""Render deterministic SVG frames for illustration review (requires resvg-py)."""
from __future__ import annotations

import argparse
from pathlib import Path
import xml.etree.ElementTree as ET


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path)
    parser.add_argument("destination", type=Path)
    args = parser.parse_args()
    import resvg_py

    args.destination.mkdir(parents=True, exist_ok=True)
    sources = sorted(args.source.rglob("*.svg"))
    for path in sources:
        ET.parse(path)
        target = args.destination / path.relative_to(args.source).with_suffix(".png")
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(resvg_py.svg_to_bytes(
            svg_path=str(path.resolve()), width=960,
            font_family="Microsoft YaHei", sans_serif_family="Microsoft YaHei",
        ))
    print(f"Rendered {len(sources)} SVG previews to {args.destination}")


if __name__ == "__main__":
    main()
