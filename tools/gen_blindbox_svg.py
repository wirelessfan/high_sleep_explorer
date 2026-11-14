"""生成盲盒角色 SVG（拉布布风格：尖耳、大圆眼、锯齿笑齿、毛绒边缘）。

用法：python tools/gen_blindbox_svg.py
输出：assets/blindbox/<id>.svg + box.svg

只读 content/blindbox/characters.json 的配色与配件配置，图形结构共用一套模板，
保证 8 个角色视觉风格统一（这是「一套盲盒」的关键）。
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CONTENT = ROOT / "content" / "blindbox" / "characters.json"
OUT = ROOT / "assets" / "blindbox"

# 配件分两层：BACK 在身体之前绘制（披风类），FRONT 在身体之后绘制。
# 每个配件都必须落在各自的安全区，避免与眼睛/笑齿/腮红穿模：
#   头顶区 y < 70、侧耳区 y < 92、下巴以下的肩颈区 y > 186。
BACK_ACCESSORIES = {
    "银河披风": """
      <g transform="translate(0 10)">
        <path d="M30 192 q 80 -30 160 0 q 14 30 4 52 q -84 -20 -168 0 q -10 -22 4 -52 Z"
              fill="#312e81" opacity=".38"/>
        <g fill="#e0e7ff">
          <circle cx="58" cy="206" r="2.2"/><circle cx="94" cy="220" r="1.6"/>
          <circle cx="142" cy="204" r="2.0"/><circle cx="170" cy="224" r="1.4"/>
          <circle cx="80" cy="234" r="1.4"/><circle cx="126" cy="236" r="2.4"/>
        </g>
      </g>""",
}

FRONT_ACCESSORIES = {
    "薄荷叶发夹": """
      <g transform="translate(78 66) rotate(-20)">
        <path d="M0 0 C 10 -14, 26 -16, 32 -6 C 26 6, 10 8, 0 0 Z" fill="#34d399" stroke="#059669" stroke-width="2"/>
        <path d="M0 0 L 26 -8" stroke="#059669" stroke-width="1.6" fill="none"/>
      </g>""",
    "蜜桃蝴蝶结": """
      <g transform="translate(150 70)">
        <path d="M0 0 C -16 -12, -26 -2, -14 8 C -8 12, -2 8, 0 0 Z" fill="#fb7185" stroke="#e11d48" stroke-width="2"/>
        <path d="M0 0 C 16 -12, 26 -2, 14 8 C 8 12, 2 8, 0 0 Z" fill="#fb7185" stroke="#e11d48" stroke-width="2"/>
        <circle cx="0" cy="2" r="3.4" fill="#e11d48"/>
      </g>""",
    "小云朵围巾": """
      <g transform="translate(62 194)">
        <path d="M0 0 q 12 -12 26 -3 q 8 -12 24 -3 q 16 -7 24 6 q 14 2 12 12 q -44 7 -86 0 q -4 -8 0 -12 Z"
              fill="#e0f2fe" stroke="#38bdf8" stroke-width="2"/>
      </g>""",
    "柠檬片帽子": """
      <g transform="translate(110 44)">
        <circle cx="0" cy="0" r="22" fill="#fef08a" stroke="#eab308" stroke-width="2.4"/>
        <circle cx="0" cy="0" r="15" fill="none" stroke="#facc15" stroke-width="1.6"/>
        <g stroke="#facc15" stroke-width="1.6">
          <path d="M0 -15 L0 15"/><path d="M-15 0 L15 0"/>
          <path d="M-11 -11 L11 11"/><path d="M11 -11 L-11 11"/>
        </g>
      </g>""",
    "星月小夜灯": """
      <g transform="translate(186 176)">
        <circle cx="0" cy="0" r="14" fill="#fef9c3" opacity=".7"/>
        <path d="M2 -10 a 10 10 0 1 0 0 20 a 7.5 7.5 0 1 1 0 -20 Z" fill="#a78bfa" stroke="#7c3aed" stroke-width="1.6"/>
        <path d="M-12 -12 l1.6 4 4 1.6 -4 1.6 -1.6 4 -1.6 -4 -4 -1.6 4 -1.6 Z" fill="#fde047"/>
      </g>""",
    "珊瑚小贝壳": """
      <g transform="translate(170 200)">
        <path d="M0 11 C -16 4, -14 -10, 0 -12 C 14 -10, 16 4, 0 11 Z" fill="#fdba74" stroke="#ea580c" stroke-width="2"/>
        <g stroke="#ea580c" stroke-width="1.3">
          <path d="M0 9 L -7 -8"/><path d="M0 9 L 0 -12"/><path d="M0 9 L 7 -8"/>
        </g>
      </g>""",
    "极光王冠": """
      <g transform="translate(110 38)">
        <path d="M-32 16 L -24 -10 L -11 6 L 0 -18 L 11 6 L 24 -10 L 32 16 Z"
              fill="#67e8f9" stroke="#0891b2" stroke-width="2"/>
        <circle cx="0" cy="-10" r="3" fill="#f0fdff"/>
        <circle cx="-20" cy="7" r="2" fill="#a5f3fc"/><circle cx="20" cy="7" r="2" fill="#a5f3fc"/>
      </g>""",
}


def body(color: str, accent: str) -> str:
    """共用身体：尖耳 + 毛绒头 + 大圆眼 + 锯齿笑齿。"""
    return f"""
  <defs>
    <radialGradient id="fur" cx="38%" cy="30%" r="78%">
      <stop offset="0%" stop-color="{accent}" stop-opacity=".55"/>
      <stop offset="62%" stop-color="{color}" stop-opacity=".18"/>
      <stop offset="100%" stop-color="#000000" stop-opacity=".10"/>
    </radialGradient>
    <linearGradient id="boxshade" x1="0" y1="0" x2="0" y2="1">
      <stop offset="0%" stop-color="#ffffff" stop-opacity=".7"/>
      <stop offset="100%" stop-color="#ffffff" stop-opacity="0"/>
    </linearGradient>
  </defs>

  <!-- 影子 -->
  <ellipse cx="110" cy="232" rx="52" ry="9" fill="#1f2937" opacity=".13"/>

  <!-- 耳朵 -->
  <path d="M66 92 C 46 44, 56 26, 74 34 C 90 42, 92 66, 88 84 Z"
        fill="{color}" stroke="{accent}" stroke-width="2.6" stroke-linejoin="round"/>
  <path d="M154 92 C 174 44, 164 26, 146 34 C 130 42, 128 66, 132 84 Z"
        fill="{color}" stroke="{accent}" stroke-width="2.6" stroke-linejoin="round"/>
  <path d="M70 88 C 58 58, 64 44, 76 50" fill="none" stroke="{accent}" stroke-width="2" opacity=".55"/>
  <path d="M150 88 C 162 58, 156 44, 144 50" fill="none" stroke="{accent}" stroke-width="2" opacity=".55"/>

  <!-- 头 -->
  <path d="M110 58 C 152 58, 172 88, 172 126 C 172 170, 148 200, 110 200 C 72 200, 48 170, 48 126 C 48 88, 68 58, 110 58 Z"
        fill="{color}" stroke="{accent}" stroke-width="3" stroke-linejoin="round"/>
  <path d="M110 58 C 152 58, 172 88, 172 126 C 172 170, 148 200, 110 200 C 72 200, 48 170, 48 126 C 48 88, 68 58, 110 58 Z"
        fill="url(#fur)"/>

  <!-- 毛绒边缘 -->
  <path d="M60 100 q 6 8 2 16 M160 100 q -6 8 -2 16 M52 132 q 8 6 4 14 M168 132 q -8 6 -4 14"
        fill="none" stroke="{accent}" stroke-width="2" stroke-linecap="round" opacity=".45"/>

  <!-- 眼睛 -->
  <ellipse cx="90" cy="122" rx="15" ry="17" fill="#ffffff" stroke="{accent}" stroke-width="2"/>
  <ellipse cx="130" cy="122" rx="15" ry="17" fill="#ffffff" stroke="{accent}" stroke-width="2"/>
  <circle cx="90" cy="124" r="8" fill="#1f2937"/>
  <circle cx="130" cy="124" r="8" fill="#1f2937"/>
  <circle cx="87" cy="120" r="3" fill="#ffffff"/>
  <circle cx="127" cy="120" r="3" fill="#ffffff"/>
  <circle cx="93" cy="128" r="1.6" fill="#ffffff" opacity=".8"/>
  <circle cx="133" cy="128" r="1.6" fill="#ffffff" opacity=".8"/>

  <!-- 腮红 -->
  <ellipse cx="70" cy="150" rx="10" ry="6" fill="#fb7185" opacity=".30"/>
  <ellipse cx="150" cy="150" rx="10" ry="6" fill="#fb7185" opacity=".30"/>

  <!-- 锯齿笑齿 -->
  <path d="M88 154 q 22 20 44 0 q -6 26 -22 26 q -16 0 -22 -26 Z"
        fill="#ffffff" stroke="{accent}" stroke-width="2" stroke-linejoin="round"/>
  <g stroke="{accent}" stroke-width="1.4" opacity=".8">
    <path d="M96 160 l 3 6"/><path d="M104 164 l 3 6"/>
    <path d="M112 166 l 3 6"/><path d="M120 164 l 3 6"/><path d="M128 160 l 3 6"/>
  </g>

  <!-- 小手臂 -->
  <path d="M58 176 q -14 8 -10 20 q 12 4 20 -8" fill="{color}" stroke="{accent}" stroke-width="2.4"/>
  <path d="M162 176 q 14 8 10 20 q -12 4 -20 -8" fill="{color}" stroke="{accent}" stroke-width="2.4"/>
"""


BOX = """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 220 270" width="220" height="270" role="img" aria-label="盲盒">
  <defs>
    <linearGradient id="bg" x1="0" y1="0" x2="1" y2="1">
      <stop offset="0%" stop-color="#fde68a"/><stop offset="55%" stop-color="#fbbf24"/><stop offset="100%" stop-color="#f59e0b"/>
    </linearGradient>
    <linearGradient id="lid" x1="0" y1="0" x2="0" y2="1">
      <stop offset="0%" stop-color="#fffbeb"/><stop offset="100%" stop-color="#fcd34d"/>
    </linearGradient>
    <linearGradient id="ribbon" x1="0" y1="0" x2="1" y2="0">
      <stop offset="0%" stop-color="#fef3c7"/><stop offset="50%" stop-color="#fffdf5"/><stop offset="100%" stop-color="#fde68a"/>
    </linearGradient>
  </defs>

  <ellipse cx="110" cy="238" rx="66" ry="11" fill="#1f2937" opacity=".15"/>

  <!-- 盒身 -->
  <rect x="38" y="102" width="144" height="126" rx="14" fill="url(#bg)" stroke="#b45309" stroke-width="3"/>
  <!-- 竖向丝带 -->
  <rect x="98" y="102" width="24" height="126" fill="url(#ribbon)" opacity=".9"/>
  <!-- 盒身明暗 -->
  <rect x="40" y="104" width="140" height="26" rx="12" fill="#ffffff" opacity=".22"/>

  <!-- 盒盖（独立分层，压在盒身上沿） -->
  <rect x="28" y="78" width="164" height="34" rx="10" fill="url(#lid)" stroke="#b45309" stroke-width="3"/>
  <rect x="28" y="104" width="164" height="8" rx="4" fill="#d97706" opacity=".35"/>
  <!-- 盖上的横向丝带 -->
  <rect x="98" y="78" width="24" height="34" fill="url(#ribbon)" opacity=".95"/>

  <!-- 蝴蝶结 -->
  <g transform="translate(110 64)">
    <path d="M0 6 C -26 -14, -44 0, -26 16 C -16 24, -4 18, 0 6 Z" fill="#fbbf24" stroke="#b45309" stroke-width="2.4"/>
    <path d="M0 6 C 26 -14, 44 0, 26 16 C 16 24, 4 18, 0 6 Z" fill="#fbbf24" stroke="#b45309" stroke-width="2.4"/>
    <circle cx="0" cy="8" r="6" fill="#92400e"/>
  </g>

  <!-- 盒身标签 -->
  <g fill="#92400e" font-family="system-ui,-apple-system,'Segoe UI',sans-serif" text-anchor="middle">
    <text x="110" y="158" font-size="14" font-weight="800">LUCKY</text>
    <text x="110" y="178" font-size="14" font-weight="800">BOX</text>
  </g>
  <circle cx="66" cy="204" r="7" fill="#fef3c7" stroke="#b45309" stroke-width="2"/>
  <circle cx="154" cy="204" r="7" fill="#fef3c7" stroke="#b45309" stroke-width="2"/>
</svg>
"""


def render(character: dict) -> str:
    color = character["color"]
    accent = _darken(color)
    acc = character.get("accessory", "")
    back = BACK_ACCESSORIES.get(acc, "")
    front = FRONT_ACCESSORIES.get(acc, "")
    # 名字放到角色脚下并给足留白（y=254），不与身体/配件重叠
    return f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 220 270" width="220" height="270" role="img" aria-label="{character['name']}">
{back}
{body(color, accent)}
{front}
  <text x="110" y="258" text-anchor="middle" font-size="13" font-weight="700"
        font-family="system-ui,-apple-system,'Segoe UI',sans-serif" fill="{accent}">{character['name']}</text>
</svg>
"""


def _darken(hex_color: str, factor: float = 0.62) -> str:
    h = hex_color.lstrip("#")
    r, g, b = (int(h[i:i + 2], 16) for i in (0, 2, 4))
    return "#%02x%02x%02x" % (int(r * factor), int(g * factor), int(b * factor))


def main() -> int:
    data = json.loads(CONTENT.read_text(encoding="utf-8"))
    OUT.mkdir(parents=True, exist_ok=True)
    n = 0
    for ch in data["characters"]:
        (OUT / ch["image"]).write_text(render(ch), encoding="utf-8")
        n += 1
    (OUT / "box.svg").write_text(BOX, encoding="utf-8")
    print(f"generated {n} characters + box.svg -> {OUT}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
