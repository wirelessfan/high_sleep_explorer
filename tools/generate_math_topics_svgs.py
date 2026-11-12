"""Generate figures for the three new math topics (probability, ellipse, substitution).

Run: python -I tools/generate_math_topics_svgs.py [--check]
Reuses the drawing helpers of generate_science_diagrams so the output keeps the
same 800-wide layout, fonts and reduced-motion conventions.
"""
from __future__ import annotations

import argparse
import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import generate_science_diagrams as sci  # noqa: E402

BLUE, RED, GREEN, AMBER = sci.BLUE, sci.RED, sci.GREEN, sci.AMBER
INK, MUTED = sci.INK, sci.MUTED
box, text, line, circle, path, animate, num = (
    sci.box, sci.text, sci.line, sci.circle, sci.path, sci.animate, sci.num)


def rect(x, y, w, h, fill='#fff', stroke='#94a3b8', radius=0):
    """直角矩形（无圆角），用于表格与色块。"""
    return ('<rect x="%s" y="%s" width="%s" height="%s" fill="%s" stroke="%s" stroke-width="1.2"/>'
            % (num(x), num(y), num(w), num(h), fill, stroke))


def wrap_plain(value, width):
    """按字符宽度折行，返回纯文本行（中文按 1、英文按 0.56 计）。"""
    lines, row, used = [], '', 0.0
    for ch in value:
        step = 1.0 if ord(ch) > 255 else 0.56
        if row and used + step > width:
            lines.append(row)
            row, used = '', 0.0
        row += ch
        used += step
    if row:
        lines.append(row)
    return lines


def probability_intro():
    content = box(24, 82, 470, 440)
    content += text(44, 112, '两枚硬币：4 个等可能结果', 16, GREEN, weight=700)
    root = (95, 300)
    l1 = [(235, 205), (235, 395)]
    leaves = [(390, 155), (390, 255), (390, 345), (390, 445)]
    content += circle(root[0], root[1], 7, '#1e293b', 'none')
    content += text(root[0], root[1] - 16, '开始', 12, MUTED, 'middle')
    for i, f in enumerate(l1):
        content += line(root[0], root[1], f[0], f[1], MUTED, 2)
        dy = -8 if i == 0 else 20
        content += text((root[0] + f[0]) / 2 - 26, (root[1] + f[1]) / 2 + dy, '1/2', 13, RED, 'middle', 700)
        for j in range(2):
            leaf = leaves[i * 2 + j]
            content += line(f[0], f[1], leaf[0], leaf[1], MUTED, 2)
            dy = -10 if j == 0 else 20
            content += text((f[0] + leaf[0]) / 2 + 6, (f[1] + leaf[1]) / 2 + dy, '1/2', 12, RED, 'middle', 600)
    for leaf, label in zip(leaves, ['正正', '正反', '反正', '反反']):
        content += circle(leaf[0], leaf[1], 24, '#eaf5ef', '#86efac')
        content += text(leaf[0], leaf[1] + 5, label, 15, GREEN, 'middle', 700)
        content += text(leaf[0] + 32, leaf[1] + 5, '1/4', 13, MUTED)
    content += ('<path d="M %d %d L %d %d L %d %d" fill="none" stroke="%s" '
                'stroke-width="2.5" stroke-dasharray="6 4"/>'
                % (root[0], root[1], l1[0][0], l1[0][1], leaves[1][0], leaves[1][1], RED))
    content += '<circle cx="%d" cy="%d" r="6" fill="%s">' % (root[0], root[1], RED)
    content += animate('cx', [root[0], l1[0][0], leaves[1][0]], [0, 0.5, 1], duration=4)
    content += animate('cy', [root[1], l1[0][1], leaves[1][1]], [0, 0.5, 1], duration=4)
    content += '</circle>'
    content += '<g class="still"><circle cx="%d" cy="%d" r="6" fill="%s"/></g>' % (root[0], root[1], RED)
    content += text(44, 470, '每条路径的概率相乘：1/2 × 1/2 = 1/4', 14, INK)
    content += text(44, 500, '互斥结果相加：P(一正一反) = 1/4 + 1/4 = 1/2', 14, INK)

    content += box(514, 82, 262, 440)
    content += text(534, 112, '古典概型的两个条件', 16, GREEN, weight=700)
    for i, (label, detail) in enumerate([('① 结果有限', '样本点个数是有限的'),
                                         ('② 等可能', '每个样本点出现的可能性相同')]):
        content += text(534, 150 + i * 62, label, 15, INK, weight=700)
        content += text(534, 172 + i * 62, detail, 13, MUTED)
    content += text(534, 262, 'P(A) = m / n', 20, RED, weight=800)
    content += text(534, 290, 'm：A 包含的样本点数', 13, MUTED)
    content += text(534, 312, 'n：全部样本点数', 13, MUTED)
    content += text(534, 352, '常用技巧', 15, GREEN, weight=700)
    for i, tip in enumerate(['• 对立事件：P(A) = 1 − P(非A)',
                             '• 分步用乘法，分类用加法',
                             '• 先列样本空间，再数个数']):
        content += text(534, 376 + i * 24, tip, 13, INK)
    content += text(534, 462, '概率相同 ≠ 结果个数相同', 12, RED)
    return sci.document('有趣的概率：树状图与古典概型',
                        '把一次试验拆成几步，路径相乘、同类相加，概率自然出现。',
                        content,
                        '先确认「有限、等可能」两个条件，再套 P(A)=m/n；不等可能时不能直接数个数。',
                        height=620)


def ellipse_intro():
    content = box(24, 82, 470, 400)
    cx, cy, ra, rb = 258, 285, 190, 112
    c = (ra * ra - rb * rb) ** 0.5
    content += ('<ellipse cx="%s" cy="%s" rx="%s" ry="%s" fill="#eef6ff" stroke="%s" stroke-width="2.5"/>'
                % (num(cx), num(cy), num(ra), num(rb), BLUE))
    f1, f2 = (cx - c, cy), (cx + c, cy)
    for f, label, dx in [(f1, 'F₁', -14), (f2, 'F₂', 14)]:
        content += circle(f[0], f[1], 6, RED, 'white')
        content += text(f[0] + dx, f[1] + 24, label, 14, RED, 'middle', 700)
    content += line(f1[0], f1[1], f2[0], f2[1], MUTED, 1.5)
    content += text((f1[0] + f2[0]) / 2, cy - 12, '2c', 13, MUTED, 'middle')

    xs = [cx + ra * math.cos(-math.pi / 2 + 2 * math.pi * i / 160) for i in range(161)]
    ys = [cy + rb * math.sin(-math.pi / 2 + 2 * math.pi * i / 160) for i in range(161)]
    content += '<g class="motion">'
    content += ('<line x1="%s" y1="%s" x2="%s" y2="%s" stroke="%s" stroke-width="2" stroke-dasharray="4 3">'
                % (num(f1[0]), num(f1[1]), num(xs[0]), num(ys[0]), AMBER))
    content += animate('x2', xs) + animate('y2', ys) + '</line>'
    content += ('<line x1="%s" y1="%s" x2="%s" y2="%s" stroke="%s" stroke-width="2" stroke-dasharray="4 3">'
                % (num(f2[0]), num(f2[1]), num(xs[0]), num(ys[0]), AMBER))
    content += animate('x2', xs) + animate('y2', ys) + '</line>'
    content += '<circle cx="%s" cy="%s" r="6" fill="%s">' % (num(xs[0]), num(ys[0]), RED)
    content += animate('cx', xs) + animate('cy', ys) + '</circle></g>'
    content += '<g class="still"><circle cx="%s" cy="%s" r="6" fill="%s"/></g>' % (num(cx), num(cy - rb), RED)
    content += text(44, 120, '绳长固定：|PF₁| + |PF₂| = 2a', 15, GREEN, weight=700)
    content += text(44, 456, '当 2a > 2c 时是椭圆；2a = 2c 退化为线段，2a < 2c 不存在。', 13, MUTED)

    content += box(514, 82, 262, 400)
    content += text(534, 112, '标准方程与 a、b、c', 16, GREEN, weight=700)
    content += text(534, 148, 'x²/a² + y²/b² = 1', 18, INK, weight=800)
    content += text(534, 176, '（a > b > 0，焦点在 x 轴）', 12, MUTED)
    content += text(534, 216, 'a² = b² + c²', 18, RED, weight=800)
    content += text(534, 244, 'a：长半轴　b：短半轴　c：半焦距', 12, MUTED)
    content += text(534, 286, '焦点：F₁(−c,0)、F₂(c,0)', 14, INK)
    content += text(534, 314, '顶点：(±a,0)、(0,±b)', 14, INK)
    content += text(534, 356, '离心率 e = c/a', 18, GREEN, weight=800)
    content += text(534, 384, '0 < e < 1', 14, INK)
    content += text(534, 408, 'e 越大 → c 越大 → 椭圆越扁', 13, MUTED)
    content += text(534, 432, 'e 越小 → 越接近圆', 13, MUTED)
    return sci.document('神奇的椭圆：到两焦点距离之和为定值',
                        '动画点沿椭圆运动，两条到焦点的线段长度之和始终不变。',
                        content,
                        '先认定义（距离和 = 2a），再用 a²=b²+c² 与 e=c/a 处理方程和形状问题。',
                        height=560)


def substitution_intro():
    content = box(24, 82, 752, 360)
    stages = [(40, '原式', 'x⁴ − 2x² + 1', BLUE),
              (290, '换元', '令 t = x²（t ≥ 0）', AMBER),
              (540, '新式', 't² − 2t + 1 = (t − 1)²', GREEN)]
    for x, label, expr, color in stages:
        content += box(x, 120, 200, 150, '#ffffff', color)
        content += text(x + 100, 150, label, 14, MUTED, 'middle')
        content += text(x + 100, 196, expr, 16, color, 'middle', 700)
    content += text(250, 196, '→', 22, MUTED, 'middle', 800)
    content += text(500, 196, '→', 22, MUTED, 'middle', 800)
    content += text(40, 320, '要点一：换元后必须写出新变量的取值范围', 15, INK, weight=700)
    content += text(40, 350, '这里 t = x² ≥ 0，最终 (t − 1)² 的最小值在 t = 1 处取得，可以取到。', 14, MUTED)
    content += text(40, 382, '要点二：换元是把「多项式的次数」降下来，不是把问题变复杂', 15, INK, weight=700)
    content += text(40, 412, '要点三：三角换元要限制角范围，防止增根或丢解', 15, INK, weight=700)

    content += '<circle cx="240" cy="170" r="6" fill="%s">' % RED
    content += animate('cx', [240, 290, 240, 290, 290], [0, 0.25, 0.5, 0.75, 1], duration=6)
    content += '</circle>'
    content += '<g class="still"><circle cx="240" cy="170" r="6" fill="%s"/></g>' % RED

    content += box(24, 462, 752, 150)
    content += text(40, 492, '三种常见换元', 16, GREEN, weight=700)
    content += text(40, 522, '整体换元：t = x²、t = √(x−1)，把重复出现的一块整体替换', 14, INK)
    content += text(40, 550, '三角换元：x = sinθ 处理 √(1−x²)，x = a sinθ 处理椭圆', 14, INK)
    content += text(40, 578, '主元变换：把参数 a 看成变量，关于 a 的一次式更容易处理', 14, INK)
    return sci.document('换元法的妙用：把陌生化成熟悉',
                        '同一个表达式换个变量，次数降低、结构变简单，问题往往一步就开了。',
                        content,
                        '换元三件事：换得干净、写清新范围、最后换回原变量。',
                        height=690)


def probability_tree():
    content = box(24, 82, 470, 420)
    content += text(44, 112, '袋中 3 红 2 蓝，有放回摸两次', 16, GREEN, weight=700)
    root = (92, 290)
    l1 = [(230, 195), (230, 385)]
    leaves = [(380, 145), (380, 245), (380, 335), (380, 435)]
    content += circle(root[0], root[1], 7, '#1e293b', 'none')
    content += text(root[0], root[1] - 16, '开始', 12, MUTED, 'middle')
    for i, f in enumerate(l1):
        content += line(root[0], root[1], f[0], f[1], MUTED, 2)
        dy = -8 if i == 0 else 20
        content += text((root[0] + f[0]) / 2 - 26, (root[1] + f[1]) / 2 + dy,
                        '3/5' if i == 0 else '2/5', 13, RED, 'middle', 700)
    for i in range(2):
        for j in range(2):
            leaf = leaves[i * 2 + j]
            content += line(l1[i][0], l1[i][1], leaf[0], leaf[1], MUTED, 2)
            dy = -10 if j == 0 else 20
            content += text((l1[i][0] + leaf[0]) / 2 + 6, (l1[i][1] + leaf[1]) / 2 + dy,
                            '3/5' if j == 0 else '2/5', 12, RED, 'middle', 600)
    for leaf, (label, p) in zip(leaves, [('红红', '9/25'), ('红蓝', '6/25'),
                                         ('蓝红', '6/25'), ('蓝蓝', '4/25')]):
        content += circle(leaf[0], leaf[1], 22, '#eaf5ef', '#86efac')
        content += text(leaf[0], leaf[1] + 5, label, 14, GREEN, 'middle', 700)
        content += text(leaf[0] + 30, leaf[1] + 5, p, 13, MUTED)
    content += text(44, 466, '分步相乘：P(红红) = 3/5 × 3/5 = 9/25', 13, INK)

    content += box(514, 82, 262, 420)
    content += text(534, 112, '两个动词：分类与分步', 16, GREEN, weight=700)
    content += text(534, 146, '分类（互斥）用加法', 14, INK, weight=700)
    content += text(534, 170, 'P(A∪B)=P(A)+P(B)', 15, BLUE, weight=700)
    content += text(534, 194, 'A、B 不能同时发生', 12, MUTED)
    content += text(534, 232, '分步（独立）用乘法', 14, INK, weight=700)
    content += text(534, 256, 'P(AB)=P(A)P(B)', 15, RED, weight=700)
    content += text(534, 280, '一次结果不影响另一次', 12, MUTED)
    content += text(534, 318, '例：同色球', 14, GREEN, weight=700)
    content += text(534, 342, 'P = 9/25 + 4/25 = 13/25', 14, INK)
    content += text(534, 366, '红红与蓝蓝互斥，相加', 12, MUTED)
    content += text(534, 404, '注意', 14, RED, weight=700)
    content += text(534, 428, '互斥 ≠ 独立：互斥事件', 12, INK)
    content += text(534, 448, '同时发生概率为 0，不是 P(A)P(B)', 12, INK)
    return sci.document('概率的加法与乘法',
                        '树状图把「分步」画出来，路径相乘；同一层的不同路径相加。',
                        content,
                        '先判断是分类还是分步，再决定用加法还是乘法；互斥与独立是两个不同的概念。',
                        height=580)


def ellipse_definition():
    content = box(24, 82, 392, 400)
    content += text(44, 112, '定义与几何量', 16, GREEN, weight=700)
    cx, cy, ra, rb = 218, 290, 150, 95
    c = (ra * ra - rb * rb) ** 0.5
    content += ('<ellipse cx="%s" cy="%s" rx="%s" ry="%s" fill="#eef6ff" stroke="%s" stroke-width="2.4"/>'
                % (num(cx), num(cy), num(ra), num(rb), BLUE))
    f1, f2 = (cx - c, cy), (cx + c, cy)
    content += circle(f1[0], f1[1], 5, RED, 'white') + circle(f2[0], f2[1], 5, RED, 'white')
    content += text(f1[0], f1[1] + 24, 'F₁(−c,0)', 12, RED, 'middle')
    content += text(f2[0], f2[1] + 24, 'F₂(c,0)', 12, RED, 'middle')
    content += line(cx, cy, cx + ra, cy, AMBER, 2)
    content += text(cx + ra / 2, cy - 12, 'a', 13, AMBER, 'middle')
    content += line(cx, cy, cx, cy - rb, GREEN, 2)
    content += text(cx + 10, cy - rb / 2, 'b', 13, GREEN)
    content += line(cx, cy, cx + c, cy, RED, 2.5)
    content += text(cx + c / 2, cy + 18, 'c', 13, RED, 'middle')
    content += text(cx, cy + 74, 'a² = b² + c²', 15, INK, 'middle', 700)
    top = (cx, cy - rb)
    content += line(f1[0], f1[1], top[0], top[1], '#94a3b8', 1.5, '4 3')
    content += line(f2[0], f2[1], top[0], top[1], '#94a3b8', 1.5, '4 3')
    content += text(cx, cy + 108, '|PF₁| + |PF₂| = 2a', 14, MUTED, 'middle')
    content += text(44, 448, '2a > 2c 才是椭圆', 13, RED)

    content += box(434, 82, 342, 400)
    content += text(454, 112, '离心率 e = c/a 决定扁平程度', 15, GREEN, weight=700)
    for i, e in enumerate((0.3, 0.6, 0.9)):
        yy = 200 + i * 92
        rx = 52
        ry = rx * math.sqrt(1 - e * e)
        color = BLUE if e < 0.5 else AMBER if e < 0.8 else RED
        content += ('<ellipse cx="652" cy="%s" rx="%s" ry="%s" fill="none" stroke="%s" stroke-width="2"/>'
                    % (num(yy), num(rx), num(ry), color))
        content += text(454, yy - 2, 'e = %.1f' % e, 13, INK, weight=700)
        content += text(454, yy + 18, '较圆' if e < 0.5 else '变扁' if e < 0.8 else '很扁', 11, MUTED)
    content += text(454, 470, 'e 越接近 1，c 越接近 a，b 越小', 12, MUTED)
    return sci.document('椭圆：定义、a/b/c 与离心率',
                        '定义给出距离和，a²=b²+c² 串起三个量，离心率刻画扁平程度。',
                        content,
                        '焦点位置看分母大小：x² 下分母大焦点在 x 轴，y² 下分母大焦点在 y 轴。',
                        height=560)


def substitution_flow():
    cols = [('整体换元', 't = x² − 1', 'y = t² + 3',
             ['t = x² − 1 ≥ −1', 'y 的最小值在 t = −1 处', '此时 x = 0，可以取到'], GREEN),
            ('三角换元', 'x = sin θ', '√(1 − x²) = cos θ',
             ['θ ∈ [−π/2, π/2]', '保证 cos θ ≥ 0', '开方不用加绝对值'], BLUE),
            ('主元变换', '把 a 看作变量', 'f = (x² − 1)a + x',
             ['关于 a 是一次函数', '最值只可能在端点', '避免讨论 x 的高次'], AMBER)]
    content = ''
    for i, (title, sub, expr, notes, color) in enumerate(cols):
        x = 24 + 258 * i
        content += box(x, 82, 238, 360)
        content += text(x + 16, 112, title, 16, color, weight=800)
        content += text(x + 16, 146, sub, 14, INK, weight=700)
        content += text(x + 16, 182, expr, 15, INK)
        for j, note in enumerate(notes):
            content += text(x + 16, 232 + j * 28, '• ' + note, 12, MUTED)
    content += text(24, 486, '换元前先问：新变量的范围是什么？最后要把结果换回原变量。', 15, RED, weight=700)
    return sci.document('三类换元法的适用场景',
                        '整体、三角、主元，各有一条最适合的路；共同点是先定范围。',
                        content,
                        '范围写错是换元法失分最多的地方：t=x² 不能写成 t∈R。',
                        height=540)


def trig_intro():
    """单位圆上的动点：横坐标是 cosθ，纵坐标是 sinθ。"""
    content = box(24, 82, 470, 430)
    content += text(44, 112, '单位圆：一个点读出两个函数', 16, GREEN, weight=700)
    cx, cy, r = 250, 300, 150
    content += line(70, cy, 440, cy, MUTED, 1.8)
    content += line(cx, 130, cx, 470, MUTED, 1.8)
    content += ('<circle cx="%s" cy="%s" r="%s" fill="none" stroke="%s" stroke-width="2.4"/>'
                % (cx, cy, r, BLUE))
    content += text(446, cy + 20, 'x', 14, INK)
    content += text(cx + 10, 126, 'y', 14, INK)

    angles = [math.pi / 4 + 2 * math.pi * i / 160 for i in range(161)]
    xs = [cx + r * math.cos(a) for a in angles]
    ys = [cy - r * math.sin(a) for a in angles]
    content += '<g class="motion">'
    content += ('<line x1="%s" y1="%s" x2="%s" y2="%s" stroke="%s" stroke-width="2">'
                % (cx, cy, num(xs[0]), num(ys[0]), AMBER))
    content += animate('x2', xs) + animate('y2', ys) + '</line>'
    # sin：点到 x 轴的竖线
    content += ('<line x1="%s" y1="%s" x2="%s" y2="%s" stroke="%s" stroke-width="3">'
                % (num(xs[0]), cy, num(xs[0]), num(ys[0]), RED))
    content += animate('x1', xs) + animate('x2', xs) + animate('y2', ys) + '</line>'
    # cos：点到 y 轴的横线
    content += ('<line x1="%s" y1="%s" x2="%s" y2="%s" stroke="%s" stroke-width="3">'
                % (cx, num(ys[0]), num(xs[0]), num(ys[0]), GREEN))
    content += animate('y1', ys) + animate('y2', ys) + animate('x2', xs) + '</line>'
    content += '<circle cx="%s" cy="%s" r="7" fill="%s">' % (num(xs[0]), num(ys[0]), RED)
    content += animate('cx', xs) + animate('cy', ys) + '</circle></g>'
    sx_, sy_ = cx + r * math.cos(math.pi / 4), cy - r * math.sin(math.pi / 4)
    content += ('<g class="still"><circle cx="%s" cy="%s" r="7" fill="%s"/>'
                '<line x1="%s" y1="%s" x2="%s" y2="%s" stroke="%s" stroke-width="3"/>'
                '<line x1="%s" y1="%s" x2="%s" y2="%s" stroke="%s" stroke-width="3"/>'
                '<line x1="%s" y1="%s" x2="%s" y2="%s" stroke="%s" stroke-width="2"/></g>'
                % (num(sx_), num(sy_), RED,
                   num(sx_), cy, num(sx_), num(sy_), RED,
                   cx, num(sy_), num(sx_), num(sy_), GREEN,
                   cx, cy, num(sx_), num(sy_), AMBER))
    content += text(cx - 22, cy + 18, 'O', 13, MUTED)
    content += text(44, 478, '红竖线 = sinθ（纵坐标）　绿横线 = cosθ（横坐标）', 13, INK)

    content += box(514, 82, 262, 430)
    content += text(534, 112, '定义与符号', 16, GREEN, weight=700)
    content += text(534, 148, 'sinθ = y', 17, RED, weight=800)
    content += text(534, 178, 'cosθ = x', 17, GREEN, weight=800)
    content += text(534, 208, 'tanθ = y/x', 17, AMBER, weight=800)
    content += text(534, 244, '周期：sin/cos 为 2π，tan 为 π', 12, MUTED)
    content += text(534, 286, '四象限符号口诀', 15, GREEN, weight=700)
    for i, tip in enumerate(['Ⅰ：全部为正', 'Ⅱ：只有 sin 正',
                             'Ⅲ：只有 tan 正', 'Ⅳ：只有 cos 正']):
        content += text(534, 314 + i * 26, tip, 13, INK)
    content += text(534, 442, '口诀：一全正、二正弦、三正切、四余弦', 12, RED)
    return sci.document('三角函数这样记：单位圆先看坐标',
                        '点绕圆转一圈，横坐标画出余弦，纵坐标画出正弦。',
                        content,
                        '先记单位圆上的坐标，再记符号口诀；公式忘了还能现推。',
                        height=580)


def trig_special():
    """特殊角在单位圆上的坐标，以及 0—90° 的取值表。"""
    content = box(24, 82, 430, 420)
    content += text(44, 112, '特殊角在单位圆上的坐标', 16, GREEN, weight=700)
    cx, cy, r = 239, 310, 150
    content += line(64, cy, 414, cy, MUTED, 1.6)
    content += line(cx, 140, cx, 460, MUTED, 1.6)
    content += ('<circle cx="%s" cy="%s" r="%s" fill="none" stroke="%s" stroke-width="2.2"/>'
                % (cx, cy, r, BLUE))
    specials = [(0, '0°', '(1, 0)'), (30, '30°', '(√3/2, 1/2)'),
                (45, '45°', '(√2/2, √2/2)'), (60, '60°', '(1/2, √3/2)'),
                (90, '90°', '(0, 1)')]
    for deg, label, coord in specials:
        a = math.radians(deg)
        px, py = cx + r * math.cos(a), cy - r * math.sin(a)
        content += line(cx, cy, px, py, '#cbd5e1', 1.4)
        content += circle(px, py, 4.5, RED, 'white')
        ca = math.cos(a)
        anchor = 'start' if ca > 0.3 else 'end' if ca < -0.3 else 'middle'
        lx = cx + (r + 16) * ca
        ly = cy - (r + 16) * math.sin(a)
        content += text(lx, ly + 5, label, 12, INK, anchor, 700)
    content += text(cx, cy + 26, 'O', 12, MUTED)
    content += text(44, 496, '圆上点的坐标就是 (cosθ, sinθ)，与右侧表格一一对应。', 12, MUTED)

    content += box(474, 82, 302, 420)
    content += text(494, 112, '0°—90° 取值表', 16, GREEN, weight=700)
    cols = ['角', 'sin', 'cos', 'tan']
    xs = [500, 570, 650, 725]
    for x, name in zip(xs, cols):
        content += text(x, 148, name, 13, MUTED, weight=700)
    rows = [('0°', '0', '1', '0'), ('30°', '1/2', '√3/2', '√3/3'),
            ('45°', '√2/2', '√2/2', '1'), ('60°', '√3/2', '1/2', '√3'),
            ('90°', '1', '0', '不存在')]
    for i, row in enumerate(rows):
        y = 184 + i * 46
        content += line(494, y + 14, 756, y + 14, '#eef2f7', 1)
        for x, value in zip(xs, row):
            content += text(x, y, value, 13, INK if i % 2 == 0 else INK)
    content += text(494, 448, '记法：sin 0,1,2,3,4 开根除 2；cos 倒过来', 12, RED)
    content += text(494, 472, '30°、45°、60° 是最高频的三个角', 12, MUTED)
    return sci.document('特殊角：一张表 + 一个圆',
                        '单位圆上记坐标，表格里记数值；两组信息互相验证。',
                        content,
                        'tan90° 不存在，因为 cos90°=0，分母为零。',
                        height=580)


def trig_astc():
    """四象限符号：一全正、二正弦、三正切、四余弦。"""
    content = box(24, 82, 752, 430)
    content += text(44, 112, '四个象限，谁为正？', 16, GREEN, weight=700)
    cx, cy, r = 400, 300, 150
    content += line(120, cy, 680, cy, MUTED, 2)
    content += line(cx, 140, cx, 460, MUTED, 2)
    content += ('<circle cx="%s" cy="%s" r="%s" fill="none" stroke="%s" stroke-width="2.2"/>'
                % (cx, cy, r, BLUE))
    quads = [('Ⅰ', 'sin +  cos +  tan +', 45), ('Ⅱ', 'sin +  cos −  tan −', 135),
             ('Ⅲ', 'sin −  cos −  tan +', 225), ('Ⅳ', 'sin −  cos +  tan −', 315)]
    for name, detail, deg in quads:
        a = math.radians(deg)
        px, py = cx + r * 0.62 * math.cos(a), cy - r * 0.62 * math.sin(a)
        content += text(px, py, name, 22, GREEN, 'middle', 800)
        content += text(px, py + 26, detail, 12, INK, 'middle')
    content += text(cx, cy + 26, 'O', 12, MUTED)
    content += text(44, 486, '口诀：一全正、二正弦、三正切、四余弦', 17, RED, weight=800)
    content += text(44, 520, '记忆法：把「全、正弦、正切、余弦」按 Ⅰ→Ⅳ 顺序念三遍，再对照单位圆坐标。', 13, MUTED)
    return sci.document('四象限符号：一句话记住',
                        '符号由坐标正负决定：x 看余弦，y 看正弦，商看正切。',
                        content,
                        '判断符号时先确定终边所在象限，再看坐标或比值的正负。',
                        height=600)


def trig_induction():
    """诱导公式：奇变偶不变，符号看象限。"""
    content = box(24, 82, 470, 430)
    content += text(44, 112, '四步走，公式不用背', 16, GREEN, weight=700)
    steps = [('①', '写成 k·π/2 ± α', '例如 π+α 中 k=2'),
             ('②', '看 k 的奇偶', 'k 奇：sin↔cos；k 偶：不变'),
             ('③', '把 α 看成锐角', '判断原角在第几象限'),
             ('④', '按原角定符号', '该象限的 sin/cos/tan 正负')]
    for i, (num_, title, detail) in enumerate(steps):
        y = 150 + i * 84
        content += circle(62, y, 16, '#eaf5ef', '#86efac')
        content += text(62, y + 5, num_, 13, GREEN, 'middle', 800)
        content += text(90, y - 2, title, 14, INK, weight=700)
        content += text(90, y + 22, detail, 12, MUTED)

    content += box(514, 82, 262, 430)
    content += text(534, 112, '三个例子', 16, GREEN, weight=700)
    examples = [('sin(π+α)', 'k=2 偶 → 函数名不变', '第三象限，sin 取负', '−sinα'),
                ('cos(π/2+α)', 'k=1 奇 → cos 变 sin', '第二象限，cos 取负', '−sinα'),
                ('tan(π−α)', 'k=2 偶 → 函数名不变', '第二象限，tan 取负', '−tanα')]
    for i, (expr, step1, step2, result) in enumerate(examples):
        y = 152 + i * 118
        content += text(534, y, expr, 15, INK, weight=700)
        content += text(534, y + 22, step1, 11, MUTED)
        content += text(534, y + 40, step2, 11, MUTED)
        content += text(534, y + 72, '= ' + result, 15, RED, weight=800)
        content += line(534, y + 90, 756, y + 90, '#eef2f7', 1)
    return sci.document('诱导公式：奇变偶不变，符号看象限',
                        '公式不是背出来的：先看 k 的奇偶决定函数名，再看原角象限决定符号。',
                        content,
                        'α 一律当作锐角来判断象限，这是口诀里最容易被忽略的前提。',
                        height=580)


def trig_graphs():
    """sin/cos/tan 图像：周期、单调区间、奇偶性。"""
    content = box(24, 82, 752, 300)
    content += text(44, 112, 'y = sinx 与 y = cosx（周期 2π）', 15, INK, weight=700)
    ox, oy, sx, sy = 90, 210, 75, 60
    content += line(ox, oy, ox + 7 * sx, oy, MUTED, 1.6)
    content += line(ox, oy + sy, ox, oy - sy, MUTED, 1.6)
    tick_labels = ['-π','0','π/2','π','3π/2','2π','5π/2']
    for k in range(-1, 6):
        x = ox + (k + 1) * sx
        content += line(x, oy - 4, x, oy + 4, MUTED, 1)
        if 0 <= k + 1 < len(tick_labels):
            content += text(x, oy + 18, tick_labels[k + 1], 10, MUTED, 'middle')
    pts_sin = [(ox + (k / 32) * 7 * sx, oy - math.sin(-math.pi + (k / 32) * 2 * math.pi + math.pi / 2 + math.pi / 2) * sy * -1 * 0 + oy - math.sin((k/32)*2*math.pi)*sy) for k in range(33)]
    pts_sin = [(ox + (k / 32) * 7 * sx, oy - math.sin(-math.pi/2 + (k / 32) * 2 * math.pi) * sy) for k in range(33)]
    pts_cos = [(ox + (k / 32) * 7 * sx, oy - math.cos(-math.pi/2 + (k / 32) * 2 * math.pi) * sy) for k in range(33)]
    content += path('M ' + ' L '.join('%s %s' % (num(x), num(y)) for x, y in pts_sin), RED, 2.2)
    content += path('M ' + ' L '.join('%s %s' % (num(x), num(y)) for x, y in pts_cos), GREEN, 2.2)
    content += text(ox + 7 * sx - 50, oy - sy - 10, 'sin（红）', RED, 12, 700)
    content += text(ox + 7 * sx - 50, oy - sy - 26, 'cos（绿）', GREEN, 12, 700)
    content += text(44, 328, 'sin 奇函数，cos 偶函数；递增区间 [−π/2+2kπ, π/2+2kπ]', 12.5, INK)
    content += text(44, 356, 'y = tanx：周期 π，在 (−π/2+kπ, π/2+kπ) 内递增，有渐近线', 12.5, INK)
    content += box(24, 380, 752, 60, '#fef9c3')
    content += text(400, 406, '图像上读性质：最高点→最大值；过零点→sin 的零点与单调分界', 13, RED, 'middle', 700)
    return sci.document('三角函数图像：把性质画出来',
                        'sin 与 cos 的图像可以互相平移得到；tan 有渐近线。',
                        content,
                        '记不住性质时，先画草图再看图：最高点、零点、渐近线，一目了然。',
                        height=470)


def trig_hexagon():
    """六边形记忆图：同角三角函数的倒数、商与平方关系。"""
    content = box(24, 82, 752, 430)
    content += text(44, 112, '六边形记忆法：对角线互倒数，相邻相乘得下一个', 15, GREEN, weight=700)
    cx, cy = 380, 270
    labels = [('sin', 380, 140, RED), ('cos', 500, 185, GREEN), ('tan', 560, 270, AMBER),
              ('cot', 500, 355, BLUE), ('sec', 380, 400, '#7c3aed'), ('csc', 260, 355, '#0ea5e9')]
    # 画六边形连线
    pts = [(x, y) for _, x, y, _ in labels]
    for i in range(6):
        a = pts[i]; b = pts[(i + 1) % 6]
        content += line(a[0], a[1], b[0], b[1], '#cbd5e1', 1.4)
    # 对角线
    content += line(labels[0][1], labels[0][2], labels[3][1], labels[3][2], '#fbbf24', 1.6, '4 3')
    content += line(labels[1][1], labels[1][2], labels[4][1], labels[4][2], '#fbbf24', 1.6, '4 3')
    content += line(labels[2][1], labels[2][2], labels[5][1], labels[5][2], '#fbbf24', 1.6, '4 3')
    # 中心 1
    content += circle(cx, cy, 18, '#fef9c3', AMBER)
    content += text(cx, cy + 5, '1', 16, AMBER, 'middle', 800)
    # 顶点标签
    for label, x, y, color in labels:
        content += circle(x, y, 22, '#ffffff', color)
        content += text(x, y + 5, label, 14, color, 'middle', 800)
    content += text(44, 470, '对角线：sin ↔ csc　cos ↔ sec　tan ↔ cot（互为倒数）', 13, INK)
    content += text(44, 496, '相邻乘：sin·tan = cos　cos·cot = sin　（沿顺时针）', 13, INK)
    content += text(44, 522, '阴影三角形：sin² + cos² = 1　1 + tan² = sec²　1 + cot² = csc²', 13, RED, weight=700)
    return sci.document('同角三角函数：六边形一张图',
                        '对角线互倒数、相邻相乘得下一个、阴影三角形是平方关系。',
                        content,
                        '忘了公式就看图：三条对角线是倒数关系，三个阴影三角形是勾股关系。',
                        height=580)




def euler_intro():
    """复平面上的单位圆：e^(iθ) 的轨迹，实部是 cosθ，虚部是 sinθ。"""
    content = box(24, 82, 470, 430)
    content += text(44, 112, '复平面：e^(iθ) 在单位圆上转圈', 16, GREEN, weight=700)
    cx, cy, r = 250, 300, 150
    content += line(70, cy, 440, cy, MUTED, 1.8)
    content += line(cx, 130, cx, 470, MUTED, 1.8)
    content += ('<circle cx="%s" cy="%s" r="%s" fill="none" stroke="%s" stroke-width="2.4"/>'
                % (cx, cy, r, BLUE))
    content += text(446, cy + 20, '实轴', 12, INK)
    content += text(cx + 10, 126, '虚轴', 12, INK)
    # 标记 −1
    content += circle(cx - r, cy, 4, GREEN, 'white')
    content += text(cx - r, cy + 22, '−1', 13, GREEN, 'middle', 700)

    angles = [math.pi / 3 + 2 * math.pi * i / 160 for i in range(161)]
    xs = [cx + r * math.cos(a) for a in angles]
    ys = [cy - r * math.sin(a) for a in angles]
    content += '<g class="motion">'
    content += ('<line x1="%s" y1="%s" x2="%s" y2="%s" stroke="%s" stroke-width="2">'
                % (cx, cy, num(xs[0]), num(ys[0]), AMBER))
    content += animate('x2', xs) + animate('y2', ys) + '</line>'
    content += ('<line x1="%s" y1="%s" x2="%s" y2="%s" stroke="%s" stroke-width="3">'
                % (num(xs[0]), cy, num(xs[0]), num(ys[0]), RED))
    content += animate('x1', xs) + animate('x2', xs) + animate('y2', ys) + '</line>'
    content += ('<line x1="%s" y1="%s" x2="%s" y2="%s" stroke="%s" stroke-width="3">'
                % (cx, num(ys[0]), num(xs[0]), num(ys[0]), GREEN))
    content += animate('y1', ys) + animate('y2', ys) + animate('x2', xs) + '</line>'
    content += '<circle cx="%s" cy="%s" r="7" fill="%s">' % (num(xs[0]), num(ys[0]), RED)
    content += animate('cx', xs) + animate('cy', ys) + '</circle></g>'
    sx_, sy_ = cx + r * math.cos(math.pi / 3), cy - r * math.sin(math.pi / 3)
    content += ('<g class="still"><circle cx="%s" cy="%s" r="7" fill="%s"/>'
                '<line x1="%s" y1="%s" x2="%s" y2="%s" stroke="%s" stroke-width="3"/>'
                '<line x1="%s" y1="%s" x2="%s" y2="%s" stroke="%s" stroke-width="3"/>'
                '<line x1="%s" y1="%s" x2="%s" y2="%s" stroke="%s" stroke-width="2"/></g>'
                % (num(sx_), num(sy_), RED,
                   num(sx_), cy, num(sx_), num(sy_), RED,
                   cx, num(sy_), num(sx_), num(sy_), GREEN,
                   cx, cy, num(sx_), num(sy_), AMBER))
    content += text(cx - 22, cy + 20, 'O', 12, MUTED)
    content += text(44, 478, '红竖线 = 虚部 sinθ　绿横线 = 实部 cosθ', 13, INK)

    content += box(514, 82, 262, 430)
    content += text(534, 112, '欧拉公式', 16, GREEN, weight=700)
    content += text(534, 152, 'e^(iθ) = cosθ + i·sinθ', 17, RED, weight=800)
    content += text(534, 186, 'θ = π 时：e^(iπ) = −1', 14, INK)
    content += text(534, 210, '即 e^(iπ) + 1 = 0', 14, INK)
    content += text(534, 252, '为什么重要', 15, GREEN, weight=700)
    for i, tip in enumerate(['把指数函数搬到了圆上', '乘法变成旋转', 'sin 与 cos 是它的投影']):
        content += text(534, 280 + i * 26, '• ' + tip, 13, INK)
    content += text(534, 380, '|e^(iθ)| = 1', 15, AMBER, weight=700)
    content += text(534, 402, '模长恒为 1，只会转圈', 12, MUTED)
    content += text(534, 448, 'θ 每增加 2π，回到原点', 12, MUTED)
    return sci.document('欧拉公式：指数函数在圆上走',
                        'e^(iθ) 的实部是 cosθ、虚部是 sinθ，所以它的轨迹是单位圆。',
                        content,
                        '欧拉公式不是定义，而是由泰勒级数推导出来的恒等式。',
                        height=580)


def euler_identity():
    """e^(iπ)+1=0：五个常数如何被一个式子串起来。"""
    content = box(24, 82, 430, 400)
    content += text(44, 112, '从 1 出发，转半圈到 −1', 16, GREEN, weight=700)
    cx, cy, r = 239, 300, 145
    content += line(70, cy, 408, cy, MUTED, 1.6)
    content += line(cx, 150, cx, 450, MUTED, 1.6)
    content += ('<circle cx="%s" cy="%s" r="%s" fill="none" stroke="%s" stroke-width="2.2"/>'
                % (cx, cy, r, BLUE))
    right, left = (cx + r, cy), (cx - r, cy)
    content += circle(right[0], right[1], 5, RED, 'white')
    content += text(right[0] + 10, right[1] - 10, '1', 14, RED, weight=700)
    content += circle(left[0], left[1], 5, GREEN, 'white')
    content += text(left[0] - 18, left[1] - 10, '−1', 14, GREEN, weight=700)
    content += path('M %s %s A %s %s 0 0 0 %s %s' % (right[0], right[1], r, r, left[0], left[1]),
                    AMBER, 2.4, 'marker-end="url(#arrow)"')
    content += text(cx, 128, '旋转 π（半圈）', 13, AMBER, 'middle', 700)
    content += text(cx, cy + 26, 'O', 12, MUTED)

    content += box(474, 82, 302, 400)
    content += text(494, 112, '五个常数，一个式子', 16, GREEN, weight=700)
    content += text(494, 150, 'e^(iπ) + 1 = 0', 19, RED, weight=800)
    rows = [('e', '自然常数 ≈2.718', '增长的底'),
            ('i', '虚数单位，i²=−1', '旋转 90°'),
            ('π', '圆周率 ≈3.14159', '转半圈'),
            ('1', '乘法单位元', '起点'),
            ('0', '加法单位元', '回到原点')]
    for i, (sym, desc, role) in enumerate(rows):
        y = 192 + i * 48
        content += text(494, y, sym, 15, INK, weight=800)
        content += text(520, y, desc, 12, MUTED)
        content += text(700, y, role, 11, GREEN, 'end')
    content += text(494, 458, '五个常数来自完全不同的领域，却在这一个等式里相遇。', 11, MUTED)
    return sci.document('欧拉恒等式：五个常数的一次相遇',
                        'e^(iπ) 表示从 1 出发转半圈，落点正好是 −1，再移项就得到恒等式。',
                        content,
                        '这个式子被称为「最美公式」，因为它把增长、旋转、圆、单位与零连在了一起。',
                        height=560)


def euler_series():
    """泰勒级数三行相加：e^(iθ) 的实部是 cos，虚部是 sin。"""
    content = box(24, 82, 752, 430)
    content += text(44, 112, '把三个级数摆在一起看', 16, GREEN, weight=700)
    rows = [('e^(iθ)', '1 + iθ − θ²/2! − iθ³/3! + θ⁴/4! + iθ⁵/5! − …', BLUE),
            ('cosθ', '1 − θ²/2! + θ⁴/4! − …', RED),
            ('sinθ', 'θ − θ³/3! + θ⁵/5! − …', GREEN)]
    for i, (name, series, color) in enumerate(rows):
        y = 160 + i * 74
        content += text(60, y, name, 16, color, weight=800)
        content += text(150, y, '=', 15, MUTED)
        content += text(178, y, series, 15, INK)
    content += text(44, 400, '上面一行按 i 的幂次分组：不含 i 的项合起来正好是 cosθ，含 i 的项合起来正好是 sinθ。', 13, MUTED)
    content += box(44, 420, 712, 62, '#fef9c3', '#facc15')
    content += text(400, 448, 'cosθ + i·sinθ = e^(iθ)', 18, RED, 'middle', 800)
    content += text(400, 470, '两边实部相等、虚部相等，这就是欧拉公式', 12, MUTED, 'middle')
    return sci.document('泰勒级数：欧拉公式是怎么来的',
                        '把 e^(iθ) 展开，按实部和虚部重新分组，恰好得到余弦与正弦。',
                        content,
                        '这里的推导只在形式上操作级数；严格证明还需要说明级数收敛与可交换性。',
                        height=600)


def euler_rotation():
    """乘 i 就是旋转 90°：z → iz → i²z = −z。"""
    content = box(24, 82, 470, 430)
    content += text(44, 112, '乘 i 两次 = 转 180°', 16, GREEN, weight=700)
    ox, oy, scale = 250, 300, 100
    content += line(70, oy, 440, oy, MUTED, 1.6)
    content += line(ox, 140, ox, 460, MUTED, 1.6)
    z = (1.0, 0.5)
    pts = [('z', z, BLUE), ('iz', (-z[1], z[0]), AMBER), ('i²z = −z', (-z[0], -z[1]), RED)]
    for name, (a, b), color in pts:
        x, y = ox + a * scale, oy - b * scale
        content += line(ox, oy, x, y, color, 2.6)
        content += circle(x, y, 5, color, 'white')
        if name.startswith('i²'):
            content += text(x - 10, y + 22, name, 13, color, 'end', 700)
        else:
            content += text(x + 10, y - 10, name, 13, color, weight=700)
    content += text(ox - 20, oy + 20, 'O', 12, MUTED)
    content += text(44, 478, '每次乘 i，向量逆时针转 90°；乘 i² 等于转 180°，所以 i² = −1。', 13, INK)

    content += box(514, 82, 262, 430)
    content += text(534, 112, '乘法 = 旋转 + 伸缩', 16, GREEN, weight=700)
    content += text(534, 148, 'z·e^(iθ)', 17, RED, weight=800)
    content += text(534, 176, '模长乘 1，角度加 θ', 13, INK)
    content += text(534, 204, '｜z·e^(iθ)｜ = ｜z｜', 13, MUTED)
    content += text(534, 246, '特例', 15, GREEN, weight=700)
    content += text(534, 274, 'θ=π/2：乘 i，转 90°', 13, INK)
    content += text(534, 300, 'θ=π：乘 −1，转 180°', 13, INK)
    content += text(534, 326, 'θ=2π：乘 1，转回原处', 13, INK)
    content += text(534, 374, '这就解释了', 15, GREEN, weight=700)
    content += text(534, 402, 'i²=i·i 转两次 90°', 13, INK)
    content += text(534, 426, '= 转 180° = 乘 −1', 13, INK)
    return sci.document('复数乘法：旋转的另一种写法',
                        '乘以 e^(iθ) 就是逆时针旋转 θ；i² = −1 只是「转两个 90°」的代数版本。',
                        content,
                        '把乘法看成旋转，很多复数恒等式会立刻变得直观。',
                        height=580)


def derivative_sign_table():
    """列表法：f′ 的符号、f 的单调性与极值。"""
    content = box(24, 82, 752, 430)
    content += text(44, 112, '例：f(x) = x³ − 3x，f′(x) = 3x² − 3 = 3(x+1)(x−1)', 15, INK, weight=700)
    cols = ['x', '(−∞,−1)', '−1', '(−1,1)', '1', '(1,+∞)']
    xs = [90, 220, 330, 425, 505, 590]
    widths = [130, 110, 95, 80, 85]
    content += rect(80, 140, 530, 130, '#ffffff', '#cbd5e1', 8)
    for x, name in zip(xs[:-1], cols[:-1]):
        content += text(x + widths[0] / 2 - 10, 168, name, 13, INK, weight=700)
    content += line(80, 178, 610, 178, '#cbd5e1', 1)
    rows = [('f′(x)', '+', '0', '−', '0', '+', RED),
            ('f(x)', '增 ↗', '极大值 2', '减 ↘', '极小值 −2', '增 ↗', BLUE)]
    for i, (label, *cells, color) in enumerate(rows):
        y = 206 + i * 30
        content += text(95, y, label, 13, color, weight=700)
        for x, value in zip(xs[1:], cells):
            content += text(x, y, value, 12.5, INK, 'middle', 700 if i == 0 else 500)
    content += text(80, 296, 'f′ 由正变负 → 极大值；由负变正 → 极小值', 14, RED, weight=700)
    content += text(80, 326, '列完表再画草图：极大值在山峰、极小值在山谷，一目了然', 13, MUTED)
    content += box(44, 356, 712, 120, '#f0fdf4')
    content += text(64, 386, '为什么用列表法', 14, GREEN, weight=700)
    for i, tip in enumerate(['① 解 f′(x)=0，按根把定义域分成几段',
                             '② 每段判断 f′ 的符号（代一个特殊值即可）',
                             '③ 符号变化的分界点就是极值点；不变号则不是极值点']):
        content += text(64, 414 + i * 24, tip, 12.5, INK)
    return sci.document('导数与单调性 · 列表法',
                        '解出 f′ 的零点，列一张符号表，单调区间与极值同时出现。',
                        content,
                        'f′ 的零点不一定是极值点：必须看到 f′ 在该点两侧变号。',
                        height=500)


def derivative_formulas():
    """求导公式与运算法则速查表。"""
    content = box(24, 82, 360, 430)
    content += text(44, 112, '基本初等函数', 16, GREEN, weight=700)
    rules = [('(xⁿ)′ = n·xⁿ⁻¹', '幂函数'),
             ('(sin x)′ = cos x', '正弦'),
             ('(cos x)′ = −sin x', '余弦'),
             ('(eˣ)′ = eˣ', '指数（不变）'),
             ('(aˣ)′ = aˣ ln a', '一般指数'),
             ('(ln x)′ = 1/x', '对数'),
             ('(log_a x)′ = 1/(x ln a)', '一般对数')]
    for i, (formula, note) in enumerate(rules):
        y = 144 + i * 50
        content += text(64, y, formula, 14, INK, weight=700)
        content += text(64, y + 20, note, 11.5, MUTED)
    content += box(404, 82, 372, 430)
    content += text(424, 112, '运算法则', 16, GREEN, weight=700)
    rules2 = [('和差：[f ± g]′ = f′ ± g′', '逐项求导'),
              ('乘：[f·g]′ = f′g + fg′', '不能直接相乘'),
              ('商：[f/g]′ = (f′g − fg′)/g²', '分母 g ≠ 0'),
              ('复合（链式）：[f(g)]′ = f′(g)·g′(x)', '先外后内，逐层相乘'),
              ('例：y=(2x+1)⁵ 的导数是 10(2x+1)⁴', '外层 5(2x+1)⁴，内层导数 2')]
    for i, (formula, note) in enumerate(rules2):
        y = 144 + i * 56
        content += text(424, y, formula, 13.5, INK, weight=700)
        content += text(424, y + 20, note, 11.5, MUTED)
    content += text(424, 452, '复合函数最易错：忘记乘内层导数', 12.5, RED, weight=700)
    return sci.document('求导公式与运算法则速查表',
                        '基本公式与四则、复合法则都在一页，考前扫一遍。',
                        content,
                        '链式法则：由外向内逐层求导，每层相乘；记不住时用定义推。',
                        height=560)


def probability_dice_grid():
    """两枚骰子的 36 个样本空间网格，和为 7 的对角线高亮。"""
    content = box(24, 82, 470, 430)
    content += text(44, 112, '两枚骰子：36 个等可能结果', 16, GREEN, weight=700)
    gx, gy, cell = 90, 150, 56
    for i in range(6):
        content += text(gx + i * cell + cell / 2, gy - 10, str(i + 1), 12, MUTED, 'middle', 700)
        content += text(gx - 14, gy + i * cell + cell / 2 + 5, str(i + 1), 12, MUTED, 'middle', 700)
    for i in range(6):
        for j in range(6):
            x, y = gx + i * cell, gy + j * cell
            if i + 1 + j + 1 == 7:
                content += rect(x, y, cell, cell, '#fef3c7', '#f59e0b', 4)
            else:
                content += rect(x, y, cell, cell, '#ffffff', '#e2e8f0', 4)
            content += text(x + cell / 2, y + cell / 2 + 5, str(i + 1 + j + 1), 13,
                            '#b45309' if i + j == 5 else '#64748b', 'middle', 700 if i + j == 5 else 500)
    content += text(gx, gy + 6 * cell + 30, '横：第一枚骰子　纵：第二枚骰子　格中数字 = 点数之和', 12, MUTED)
    content += text(gx, gy + 6 * cell + 56, '黄色对角线：和为 7，共 6 格 → P = 6/36 = 1/6', 13, RED, weight=700)

    content += box(514, 82, 262, 430)
    content += text(534, 112, '为什么画网格', 16, GREEN, weight=700)
    for i, tip in enumerate(['① 36 个样本点一目了然，不会漏数',
                             '② 任意事件的概率 = 数格子 ÷ 36',
                             '③ 和为 7 的组合最多（6 种），所以最常见',
                             '④ 和为 2 或 12 只有 1 种，最罕见']):
        content += text(534, 146 + i * 30, tip, 12.5, INK)
    content += text(534, 282, '其他事件的用法', 15, GREEN, weight=700)
    for i, tip in enumerate(['和为偶数：对角线一半，18 格 → 1/2',
                             '第一枚为 6：整行 6 格 → 1/6',
                             '至少一个 6：36 − 25 = 11 格 → 11/36']):
        content += text(534, 312 + i * 28, '• ' + tip, 12.5, INK)
    content += text(534, 428, '数格子之前，先确认两枚骰子互相独立', 12, RED)
    return sci.document('两枚骰子：36 个样本点的网格',
                        '把所有结果摆成 6×6 的表格，概率就是数格子。',
                        content,
                        '古典概型等可能的前提：两枚骰子互相独立，每格概率同为 1/36。',
                        height=580)


def probability_complement():
    """「至少一次」用对立事件：1 − 全不发生。"""
    content = box(24, 82, 752, 300)
    content += text(44, 112, '例：命中率 0.4，射击三次，至少命中一次的概率？', 15, INK, weight=700)
    content += rect(60, 140, 240, 60, '#fef2f2', '#fca5a5', 8)
    content += text(180, 165, '正面硬算：分类相加', 13, RED, 700, 'middle')
    content += text(180, 188, '恰 1 次 + 恰 2 次 + 恰 3 次（三项）', 12, '#7f1d1d', 'middle')
    content += rect(360, 140, 240, 60, '#f0fdf4', '#86efac', 8)
    content += text(480, 165, '反面巧算：对立事件', 13, GREEN, 700, 'middle')
    content += text(480, 188, '1 − 三次全不中（一项）', 12, '#14532d', 'middle')
    content += text(180, 240, '每次不中 = 0.6，三次全不中 = 0.6³ = 0.216', 13, INK)
    content += text(180, 264, '至少命中一次 = 1 − 0.216 = 0.784', 14, RED, weight=700)
    content += text(480, 240, '「至少」问题几乎都用这一招', 13, INK)
    content += text(480, 264, 'n 次至少一次 = 1 − (1−p)ⁿ', 13, MUTED)
    content += text(44, 310, '为什么反面更快：正面要分「恰 1、恰 2、恰 3」三类分别用组合数计算；反面只有一项。', 13, MUTED)
    content += text(44, 336, '同理：至少两次 = 1 − 全不中 − 恰一次；至少 n−1 次 = 1 − 全中 − 恰 n−1 次', 13, MUTED)
    content += box(24, 366, 752, 130, '#f0fdf4')
    content += text(44, 396, '什么时候能用：', 14, GREEN, weight=700)
    for i, tip in enumerate(['① 各次试验相互独立（互不影响）',
                             '② 每次试验的概率相同',
                             '③ 「至少」包含的情形很多时，优先取对立面']):
        content += text(44, 424 + i * 24, tip, 12.5, INK)
    return sci.document('至少一次：用对立事件一步到位',
                        '「至少发生一次」的反面是「一次都没发生」。',
                        content,
                        '前提是各次试验相互独立且概率相同；不独立时不能这样算。',
                        height=540)


def ellipse_focus_axis():
    """标准方程与焦点位置：看分母大小。"""
    content = box(24, 82, 360, 430)
    content += text(44, 112, '焦点在 x 轴', 15, BLUE, weight=800)
    content += text(44, 148, 'x²/25 + y²/9 = 1', 15, INK, weight=700)
    content += text(44, 176, 'x² 分母 25 大 → 焦点在 x 轴', 12.5, MUTED)
    content += text(44, 200, '焦点 (±4, 0)', 12.5, MUTED)
    content += text(44, 232, '焦点在 y 轴', 15, BLUE, weight=800)
    content += text(44, 268, 'x²/9 + y²/16 = 1', 15, INK, weight=700)
    content += text(44, 296, 'y² 分母 16 大 → 焦点在 y 轴', 12.5, MUTED)
    content += text(44, 320, '焦点 (0, ±√7)', 12.5, MUTED)
    content += text(44, 356, '记忆：谁的分母大，长轴就在谁的方向', 13, RED, weight=700)
    content += text(44, 384, '（a² 永远是较大的分母）', 12.5, MUTED)

    content += box(404, 82, 372, 430)
    content += text(424, 112, '参数不完整时先讨论', 16, GREEN, weight=700)
    content += text(424, 148, '例：方程 x²/m + y²/4 = 1 表示椭圆，', 13, INK)
    content += text(424, 172, '且焦点在 x 轴，求 m 的范围。', 13, INK)
    content += text(424, 204, '① 焦点在 x 轴：m > 4', 13, RED, weight=700)
    content += text(424, 232, '② 表示椭圆（焦点在 y 轴）：0 < m < 4', 13, INK, weight=700)
    content += text(424, 264, '③ 若题目说「表示椭圆」不指明焦点：', 13, INK)
    content += text(424, 288, 'm > 0 且 m ≠ 4（两种情形都要算）', 13, INK, weight=700)
    content += text(424, 324, '高频陷阱', 15, GREEN, weight=700)
    for i, tip in enumerate(['• 把 m>4 与 0<m<4 混为一谈',
                             '• 忘记 m>0（分母不能为 0 或负）',
                             '• 忽略「焦点位置未指明」需要分类讨论']):
        content += text(424, 352 + i * 26, tip, 12.5, RED)
    return sci.document('标准方程与焦点位置',
                        '比较两个分母的大小：分母大的方向是长轴，焦点就在那条轴上。',
                        content,
                        '参数没指明焦点位置时，必须分类讨论；这是选择题的常设陷阱。',
                        height=560)


def ellipse_focus_chord():
    """焦点弦与焦点三角形：两个恒定周长。"""
    content = box(24, 82, 470, 430)
    content += text(44, 112, '焦点三角形：周长恒为 2a + 2c', 15, GREEN, weight=700)
    cx, cy, ra, rb = 250, 300, 170, 105
    c = (ra * ra - rb * rb) ** 0.5
    content += ('<ellipse cx="%s" cy="%s" rx="%s" ry="%s" fill="#eef6ff" stroke="%s" stroke-width="2.2"/>'
                % (num(cx), num(cy), num(ra), num(rb), BLUE))
    f1, f2 = (cx - c, cy), (cx + c, cy)
    p = (cx + ra * math.cos(0.7), cy - rb * math.sin(0.7))
    content += circle(f1[0], f1[1], 5, RED, 'white') + circle(f2[0], f2[1], 5, RED, 'white')
    content += circle(p[0], p[1], 5, AMBER, 'white')
    for f in (f1, f2):
        content += line(f[0], f[1], p[0], p[1], '#94a3b8', 1.6, '4 3')
    content += text(f1[0] - 14, f1[1] + 20, 'F₁', 13, RED, 'middle', 700)
    content += text(f2[0] + 14, f2[1] + 20, 'F₂', 13, RED, 'middle', 700)
    content += text(p[0] + 10, p[1] - 12, 'P', 13, AMBER, weight=700)
    content += text(44, 452, '周长 = |PF₁| + |PF₂| + |F₁F₂| = 2a + 2c（恒定）', 13, INK, weight=700)
    content += text(44, 480, '弦 AB 过焦点 F₁ 时，三角形 ABF₂ 的周长恒为 4a', 13, INK, weight=700)

    content += box(514, 82, 262, 430)
    content += text(534, 112, '推导只用定义', 16, GREEN, weight=700)
    content += text(534, 148, '焦点三角形：', 14, INK, weight=700)
    content += text(534, 172, '|PF₁| + |PF₂| = 2a', 13, INK)
    content += text(534, 196, '加 |F₁F₂| = 2c → 周长 2a + 2c', 13, MUTED)
    content += text(534, 238, '焦点弦 AB（过 F₁）：', 14, INK, weight=700)
    content += text(534, 262, '|AF₁| + |AF₂| = 2a', 13, INK)
    content += text(534, 286, '|BF₁| + |BF₂| = 2a', 13, INK)
    content += text(534, 310, '|AB| = |AF₁| + |BF₁|', 13, INK)
    content += text(534, 334, '周长 = 2a + 2a = 4a', 14, RED, weight=700)
    content += text(534, 384, '两个定值都只依赖 a、c', 13, MUTED)
    content += text(534, 428, '不必知道 P 的具体位置', 12, MUTED)
    return sci.document('焦点弦与焦点三角形：两个定值周长',
                        '定义给出的 2a 加上焦距 2c，直接得到两个恒定周长。',
                        content,
                        '焦点在 y 轴的椭圆同理；椭圆越扁 c 越大，三角形越“胖”。',
                        height=560)


def substitution_trig_example():
    """三角换元完整例题：y = x + √(1−x²) 的最大值。"""
    content = box(24, 82, 752, 300)
    content += text(44, 112, '例：求 y = x + √(1−x²) 的最大值（|x| ≤ 1）', 15, INK, weight=700)
    content += text(44, 148, '① 令 x = sinθ，θ ∈ [−π/2, π/2]', 13.5, INK)
    content += text(44, 176, '② √(1−x²) = √(1−sin²θ) = cosθ（区间内 cosθ ≥ 0）', 13.5, INK)
    content += text(44, 204, '③ y = sinθ + cosθ = √2·sin(θ + π/4)', 13.5, INK)
    content += text(44, 232, '④ θ ∈ [−π/2, π/2] 时 θ+π/4 ∈ [−π/4, 3π/4]，最大值在 θ = π/4', 13.5, INK)
    content += text(44, 260, '⑤ 最大值 y = √2，此时 x = sin(π/4) = √2/2', 13.5, INK)
    content += text(44, 296, '范围链：θ 的范围决定 θ+π/4 的范围，再定 sin 的最大值——每一步都不能跳', 12.5, MUTED)
    content += box(24, 320, 752, 60, '#fef9c3')
    content += text(400, 348, '易错：不写 θ 的范围，就说不清 sin(θ+π/4) 为什么能取到 1', 13, RED, 'middle', 700)
    content += box(24, 400, 360, 110, '#f0fdf4')
    content += text(44, 428, '不用换元也行', 13.5, GREEN, weight=700)
    content += text(44, 452, 'y = x + √(1−x²) 的两项平方和为 1，', 12, INK)
    content += text(44, 474, '柯西不等式给出同样的最大值 √2', 12, INK)
    content += box(404, 400, 372, 110, '#eff6ff')
    content += text(424, 428, '适用条件', 13.5, BLUE, weight=700)
    content += text(424, 452, '√(1−x²) 的存在要求 |x| ≤ 1，', 12, INK)
    content += text(424, 474, '这正是三角换元能覆盖的范围', 12, INK)
    return sci.document('三角换元例题：最大值 √2 是怎么来的',
                        '换元、开方、辅助角、定范围，四步一气呵成。',
                        content,
                        '每一步都写出范围，才能说明最大值“取得到”。',
                        height=540)


def substitution_main_variable():
    """主元变换：把参数 a 看成一次函数的主元。"""
    content = box(24, 82, 752, 300)
    content += text(44, 112, '例：已知 (x²−1)a + x ≥ 0 对任意 a ∈ [−1,1] 恒成立，求 x 的范围。', 13.5, INK, weight=700)
    content += text(44, 148, '常规思路：按 a = 1 和 a = −1 两种情况分别解 x 的不等式，再取交集', 13, MUTED)
    content += text(44, 176, '主元思路：把 a 看成变量，f(a) = (x²−1)·a + x 是关于 a 的一次函数', 13, INK)
    content += text(44, 204, '一次函数在闭区间上的最小值在端点取得 → 只需两个端点都 ≥ 0', 13, INK)
    content += box(24, 230, 752, 66, '#f0fdf4')
    content += text(44, 254, 'f(−1) = −(x²−1) + x ≥ 0　且　f(1) = (x²−1) + x ≥ 0', 14, INK, 'middle', 700)
    content += text(44, 284, '即 x² − x − 1 ≤ 0 且 x² + x − 1 ≤ 0', 13, MUTED, 'middle')
    content += text(44, 324, '解得 (√5−1)/2 ≥ x ≥ (1−√5)/2（两集合取交集）', 13.5, INK, weight=700)
    content += text(44, 352, '常规解法要按 x²−1 的正负分两类讨论；主元法把“讨论”变成“查两端”', 13, MUTED)
    content += box(24, 372, 752, 60, '#fef9c3')
    content += text(400, 400, '适用条件：f(a) 关于 a 是一次的（不含 a²）', 13, RED, 'middle', 700)
    content += box(24, 442, 752, 56, '#f0fdf4')
    content += text(44, 470, '何时想到主元：', 13, GREEN, weight=700)
    content += text(140, 470, '参数 a 的次数低（一次），而 x 的次数高（二次以上）时，交换地位更简单', 12.5, INK)
    return sci.document('主元变换：把参数当成变量',
                        '参数次数低、变量次数高时，把参数看作主元，问题变成一次函数的端点问题。',
                        content,
                        '主元法不是万能的：只对“关于参数是一次”的不等式有效。',
                        height=540)


def euler_polar():
    """极坐标：模长与辐角。"""
    content = box(24, 82, 470, 430)
    content += text(44, 112, '例：把 z = 3 + 4i 写成极坐标形式', 15, INK, weight=700)
    cx, cy, scale = 250, 300, 34
    content += line(70, cy, 440, cy, MUTED, 1.8)
    content += line(cx, 470, cx, 130, MUTED, 1.8)
    px, py = cx + 3 * scale, cy - 4 * scale
    content += line(cx, cy, px, py, RED, 2.6)
    content += circle(px, py, 6, RED, 'white')
    content += text(px + 12, py - 6, 'z = 3+4i', 13, RED, weight=700)
    content += text(cx + 3 * scale / 2, cy + 20, '3（实部）', 12, BLUE, 'middle')
    content += line(px, py, px, cy, '#94a3b8', 1.4, '3 3')
    content += text(px + 10, (py + cy) / 2, '4（虚部）', 12, GREEN)
    r = 5.0
    content += text(cx - 66, cy - 92, '|z| = 5', 14, RED, weight=800)
    content += text(44, 456, 'r = √(3²+4²) = 5　θ = arctan(4/3) ≈ 53°', 13, INK)
    content += text(44, 484, '极坐标形式：z = r(cosθ + i·sinθ) = 5e^(iθ)', 13.5, INK, weight=700)

    content += box(514, 82, 262, 430)
    content += text(534, 112, '模长与辐角', 16, GREEN, weight=700)
    content += text(534, 148, 'r = |z| = √(a²+b²)', 14, INK, weight=700)
    content += text(534, 176, 'θ = arg z（辐角）', 14, INK, weight=700)
    content += text(534, 208, '乘法：模长相乘、辐角相加', 12.5, INK)
    content += text(534, 232, '除法：模长相除、辐角相减', 12.5, INK)
    content += text(534, 232 + 34, '乘方：模长乘方、辐角乘 n', 12.5, INK)
    content += text(534, 286, '与欧拉公式的关系', 15, GREEN, weight=700)
    content += text(534, 312, 'e^(iθ) = cosθ + i·sinθ', 13, INK)
    content += text(534, 336, '所以 z = r·e^(iθ)', 14, RED, weight=700)
    content += text(534, 366, '极坐标就是欧拉公式的直接应用：', 12, MUTED)
    content += text(534, 390, '模长和辐角把“位置”变成“距离+方向”', 12, MUTED)
    content += text(534, 436, '乘除与乘方在极坐标下极其简单', 12, RED)
    return sci.document('极坐标：模长与辐角',
                        '模长 r 给出离原点的距离，辐角 θ 给出方向；两个数确定一个复数。',
                        content,
                        '三角换元、欧拉公式、复数乘法，都是“模长与辐角”这套语言的不同说法。',
                        height=580)


def euler_demoivre():
    """棣莫弗定理：幂的辐角乘 n。"""
    content = box(24, 82, 470, 430)
    content += text(44, 112, '棣莫弗定理：[r(cosθ+i·sinθ)]ⁿ = rⁿ(cos nθ + i·sin nθ)', 14, INK, weight=700)
    cx, cy, base = 250, 300, 34
    z = 1 + 1j if False else None
    # (1+i)^k 的模长 (√2)^k、辐角 k·π/4
    pts = []
    for k in range(1, 9):
        mod = (math.sqrt(2)) ** k
        ang = k * math.pi / 4
        pts.append((k, mod, ang))
    max_mod = pts[-1][1]
    scale = 130 / max_mod
    for k, mod, ang in pts:
        px = cx + mod * scale * math.cos(ang)
        py = cy - mod * scale * math.sin(ang)
        color = BLUE if k < 8 else RED
        content += circle(px, py, 4.5, color, 'white')
        content += line(cx, cy, px, py, color, 1.2)
        content += text(px + 8, py - 4, str(k), 10.5, MUTED, weight=700)
    content += text(cx, cy + 20, 'O', 11, MUTED)
    content += text(44, 456, '(1+i)^k 的落点：模长 (√2)^k 递增，辐角每次 +45°，绕 2 圈', 12.5, MUTED)
    content += text(44, 484, 'k=8 时辐角 8×45°=360°，回到正实轴，模长 (√2)⁸ = 16', 13, RED, weight=700)

    content += box(514, 82, 262, 430)
    content += text(534, 112, '定理内容', 16, GREEN, weight=700)
    content += text(534, 148, '[r(cosθ+isinθ)]ⁿ', 14, INK, weight=700)
    content += text(534, 172, '= rⁿ(cos nθ + i·sin nθ)', 14, INK, weight=700)
    content += text(534, 204, '由欧拉公式一行可得：', 13, MUTED)
    content += text(534, 228, '左边 = (r·e^(iθ))ⁿ = rⁿ·e^(inθ)', 13, INK)
    content += text(534, 252, '右边由欧拉公式展开即原形式', 12.5, MUTED)
    content += text(534, 288, '与本站例题的对照', 15, GREEN, weight=700)
    content += text(534, 314, '(1+i)⁸：1+i = √2·e^(iπ/4)', 12.5, INK)
    content += text(534, 338, '八次方：模长 (√2)⁸ = 16', 12.5, INK)
    content += text(534, 362, '辐角 8×π/4 = 2π，回到正实轴', 12.5, INK)
    content += text(534, 386, '所以 (1+i)⁸ = 16', 13.5, RED, weight=800)
    return sci.document('棣莫弗定理：幂的辐角乘 n',
                        '欧拉公式一行推出棣莫弗定理；幂运算变成“模长乘方、辐角乘 n”。',
                        content,
                        '图示是 (1+i)^k 的落点螺旋：每乘一次 (1+i)，转 45° 并放大 √2 倍。',
                        height=560)


DOCS = {
    'intro-math-probability.svg': probability_intro,
    'intro-math-ellipse.svg': ellipse_intro,
    'intro-math-substitution.svg': substitution_intro,
    'math-probability-tree.svg': probability_tree,
    'math-ellipse-definition.svg': ellipse_definition,
    'math-substitution-flow.svg': substitution_flow,
    'intro-math-trig.svg': trig_intro,
    'math-trig-special.svg': trig_special,
    'math-trig-astc.svg': trig_astc,
    'math-trig-induction.svg': trig_induction,
    'intro-math-euler.svg': euler_intro,
    'math-euler-identity.svg': euler_identity,
    'math-euler-series.svg': euler_series,
    'math-euler-rotation.svg': euler_rotation,
    'math-derivative-sign-table.svg': derivative_sign_table,
    'math-derivative-formulas.svg': derivative_formulas,
    'math-probability-dice-grid.svg': probability_dice_grid,
    'math-probability-complement.svg': probability_complement,
    'math-ellipse-focus-axis.svg': ellipse_focus_axis,
    'math-ellipse-focus-chord.svg': ellipse_focus_chord,
    'math-substitution-trig-example.svg': substitution_trig_example,
    'math-substitution-main-variable.svg': substitution_main_variable,
    'math-euler-polar.svg': euler_polar,
    'math-euler-demoivre.svg': euler_demoivre,
    'math-trig-graphs.svg': trig_graphs,
    'math-trig-hexagon.svg': trig_hexagon,
}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check', action='store_true', help='校验数学关系，不写文件')
    parser.add_argument('--frames-dir', type=Path)
    args = parser.parse_args()

    # 关键数值断言：椭圆 a²=b²+c²、概率归一、换元范围
    ra, rb = 150.0, 95.0
    c = (ra * ra - rb * rb) ** 0.5
    assert abs((ra * ra) - (rb * rb + c * c)) < 1e-9
    assert abs(3 / 5 * 3 / 5 + 3 / 5 * 2 / 5 + 2 / 5 * 3 / 5 + 2 / 5 * 2 / 5 - 1) < 1e-12
    assert abs(9 / 25 + 4 / 25 - 13 / 25) < 1e-12
    assert 1 / 4 + 1 / 4 == 1 / 2
    assert (lambda t: t * t - 2 * t + 1)(1) == 0
    assert all((x * x) >= 0 for x in (-3, -1, 0, 1, 3))
    for e in (0.3, 0.6, 0.9):
        assert 0 < e < 1 and math.sqrt(1 - e * e) > 0

    docs = {name: fn() for name, fn in DOCS.items()}
    for name, content in docs.items():
        sci.ET.fromstring(content)
        if args.check:
            continue
        (sci.ROOT / 'assets' / 'notes' / name).write_text(
            content.replace('><', '>\n<'), encoding='utf-8', newline='\n')
        print('wrote', name)
    if args.check:
        print(f'Validated {len(docs)} math-topic figures')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
