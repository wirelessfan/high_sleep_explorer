"""把 MIT 许可的 Labubu 原图按色相旋转生成一组盲盒配色变体。

原图：xiaohe0601/leafer-labubu (MIT) docs/labubu-classic.png
仅对画面中的「棕色系」像素做色相替换，保留黑色描边、白色眼睛与粉色脸部，
避免整图偏色导致角色失真。

用法：python tools/gen_labubu_variants.py
输出：assets/blindbox/labubu-<id>.png
"""
from __future__ import annotations

import colorsys
import struct
import sys
import zlib
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "tools" / "assets" / "labubu-base.png"   # 生成源，不参与线上部署
OUT = ROOT / "assets" / "blindbox"

# 8 个变体：id -> (目标色相偏移角度, 目标饱和度倍率, 目标明度倍率)
VARIANTS = {
    "classic": (0, 1.0, 1.0),       # 原版棕
    "mint": (150, 0.95, 1.18),      # 薄荷绿
    "peach": (-24, 0.95, 1.45),     # 蜜桃粉（提亮）
    "sky": (205, 0.95, 1.18),       # 天空蓝
    "lemon": (46, 1.10, 1.45),      # 柠檬黄（提亮）
    "lilac": (268, 0.85, 1.20),     # 丁香紫
    "rose": (330, 1.00, 1.05),      # 玫瑰红
    "aurora": (180, 1.00, 1.15),    # 极光青
}


def _read_png(path: Path):
    """极简 PNG 解码：只支持调色板（colortype 3）与 8bit，够用即可。"""
    raw = path.read_bytes()
    if raw[:8] != b"\x89PNG\r\n\x1a\n":
        raise ValueError("不是 PNG")
    pos = 8
    w = h = 0
    palette = b""
    trns = b""
    idat = b""
    while pos < len(raw):
        (length,) = struct.unpack(">I", raw[pos:pos + 4])
        ctype = raw[pos + 4:pos + 8]
        data = raw[pos + 8:pos + 8 + length]
        pos += 12 + length
        if ctype == b"IHDR":
            w, h, depth, color = struct.unpack(">IIBB", data[:10])
            if color != 3:
                raise ValueError(f"仅支持调色板 PNG，当前 colortype={color}")
        elif ctype == b"PLTE":
            palette = data
        elif ctype == b"tRNS":
            trns = data
        elif ctype == b"IDAT":
            idat += data
        elif ctype == b"IEND":
            break

    raw_pixels = zlib.decompress(idat)
    stride = w
    rows = []
    prev = bytearray(stride)
    i = 0
    for _ in range(h):
        f = raw_pixels[i]
        i += 1
        line = bytearray(raw_pixels[i:i + stride])
        i += stride
        if f == 1:
            for x in range(1, stride):
                line[x] = (line[x] + line[x - 1]) & 0xFF
        elif f == 2:
            for x in range(stride):
                line[x] = (line[x] + prev[x]) & 0xFF
        elif f == 3:
            for x in range(stride):
                left = line[x - 1] if x else 0
                line[x] = (line[x] + ((left + prev[x]) >> 1)) & 0xFF
        elif f == 4:
            for x in range(stride):
                a = line[x - 1] if x else 0
                b = prev[x]
                c = prev[x - 1] if x else 0
                p = a + b - c
                pa, pb, pc = abs(p - a), abs(p - b), abs(p - c)
                pr = a if (pa <= pb and pa <= pc) else (b if pb <= pc else c)
                line[x] = (line[x] + pr) & 0xFF
        rows.append(line)
        prev = line
    return w, h, palette, trns, rows


def _write_png(path: Path, w: int, h: int, rows: list[bytearray]) -> None:
    def chunk(tag: bytes, data: bytes) -> bytes:
        return (struct.pack(">I", len(data)) + tag + data +
                struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF))

    raw = b"".join(b"\x00" + bytes(r) for r in rows)
    png = (b"\x89PNG\r\n\x1a\n"
           + chunk(b"IHDR", struct.pack(">IIBBBBB", w, h, 8, 2, 0, 0, 0))
           + chunk(b"IDAT", zlib.compress(raw, 9))
           + chunk(b"IEND", b""))
    path.write_bytes(png)


def _is_body_rgb(r: int, g: int, b: int) -> bool:
    """判断是否为「棕色身体」像素：暖色、中等明度、非灰黑、非近白。"""
    h, s, v = colorsys.rgb_to_hsv(r / 255, g / 255, b / 255)
    return 0.02 <= h <= 0.11 and s >= 0.28 and 0.16 <= v <= 0.72


def _recolor(r: int, g: int, b: int, dh: float, ds: float, dv: float):
    h, s, v = colorsys.rgb_to_hsv(r / 255, g / 255, b / 255)
    h = (h + dh / 360.0) % 1.0
    s = min(1.0, s * ds)
    v = min(1.0, v * dv)
    r2, g2, b2 = colorsys.hsv_to_rgb(h, s, v)
    return int(r2 * 255), int(g2 * 255), int(b2 * 255)


def _rebuild_with_palette(src_bytes: bytes, palette: bytes) -> bytes:
    """把 PNG 的 PLTE 换成新调色板并重算所有 chunk 的 CRC，其余字节原样保留。

    这是最稳的做法：像素索引、tRNS 透明表、IDAT 压缩数据完全不动，
    仅改变索引到颜色的映射，因此不会破坏行滤波或 alpha。
    """
    def chunk(tag: bytes, data: bytes) -> bytes:
        return (struct.pack(">I", len(data)) + tag + data +
                struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF))

    out = bytearray(src_bytes[:8])
    pos = 8
    while pos < len(src_bytes):
        (length,) = struct.unpack(">I", src_bytes[pos:pos + 4])
        tag = src_bytes[pos + 4:pos + 8]
        data = src_bytes[pos + 8:pos + 8 + length]
        if tag == b"PLTE":
            data = palette
        out += chunk(tag, data)
        pos += 12 + length
        if tag == b"IEND":
            break
    return bytes(out)


def main() -> int:
    if not SRC.exists():
        print(f"缺少原图：{SRC}")
        return 1
    src_bytes = SRC.read_bytes()
    w, h, palette, trns, _rows = _read_png(SRC)
    colors = [(palette[i], palette[i + 1], palette[i + 2]) for i in range(0, len(palette), 3)]

    made = 0
    for vid, (dh, ds, dv) in VARIANTS.items():
        new_pal = bytearray()
        for (r, g, b) in colors:
            if _is_body_rgb(r, g, b):
                nr, ng, nb = _recolor(r, g, b, dh, ds, dv)
            else:
                nr, ng, nb = r, g, b
            new_pal += bytes((nr, ng, nb))

        dst = OUT / f"labubu-{vid}.png"
        dst.write_bytes(_rebuild_with_palette(src_bytes, bytes(new_pal)))
        made += 1
        print(f"  {dst.name}  ({dst.stat().st_size // 1024} KB)")
    print(f"完成：{made} 个变体（调色板替换法，保留原始 alpha 与滤波）")
    return 0


if __name__ == "__main__":
    sys.exit(main())
