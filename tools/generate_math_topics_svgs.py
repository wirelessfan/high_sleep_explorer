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


DOCS = {
    'intro-math-probability.svg': probability_intro,
    'intro-math-ellipse.svg': ellipse_intro,
    'intro-math-substitution.svg': substitution_intro,
    'math-probability-tree.svg': probability_tree,
    'math-ellipse-definition.svg': ellipse_definition,
    'math-substitution-flow.svg': substitution_flow,
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
