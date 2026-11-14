"""Generate the log diagrams from mathematical coordinates; no hand-fitted curves."""
from pathlib import Path
import math

ROOT = Path(__file__).resolve().parents[1] / 'assets' / 'notes'


def curve(fn, lo, hi, ox, oy, sx, sy, count=321, log_spacing=False):
    points = []
    for i in range(count):
        t = i / (count - 1)
        x = math.exp(math.log(lo) + t * math.log(hi / lo)) if log_spacing else lo + t * (hi - lo)
        points.append((ox + sx*x, oy - sy*fn(x)))
    return ' '.join(('M' if i == 0 else 'L') + f'{x:.3f} {y:.3f}' for i, (x, y) in enumerate(points))


def path(data, color, ident, fn, mapping, extra=''):
    return (f'<path id="{ident}" data-function="{fn}" data-mapping="{mapping}" d="{data}" '
            f'fill="none" stroke="{color}" stroke-width="3" {extra}/>')


def text(x, y, value, color='#50647a', size=13, extra=''):
    return f'<text x="{x}" y="{y}" fill="{color}" font-size="{size}" {extra}>{value}</text>'


def line(x1, y1, x2, y2, extra=''):
    return f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" stroke="#94a3b8" stroke-width="1.4" {extra}/>'


def dot(x, y, label, color='#0d9488', dx=8, dy=-8):
    return f'<circle cx="{x}" cy="{y}" r="4.5" fill="{color}"/>' + text(x+dx, y+dy, label, color, 12)


def intro():
    p = ROOT / 'intro-math-log.svg'
    s = p.read_text(encoding='utf-8')
    a = s.index('      /*'); b = s.index('    </style>', a)
    styles = '      /* Each held frame is an exact (2^n,n) point; both coordinates change together. */\n'
    for i in range(5):
        styles += f'      .tick{i+1} {{ animation: lit{i} 10s steps(1,end) infinite; }}\n'
        styles += f'      @keyframes lit{i} {{ ' + ' '.join(f'{j*20}% {{ opacity: {"1" if j == i else ".18"}; }}' for j in range(5)) + ' }\n'
    s = s[:a] + styles + s[b:]
    a = s.index('  <!-- 坐标轴') if '  <!-- 坐标轴' in s else s.index('  <!-- Linear coordinates:')
    b = s.index('  <!-- ============ 下半', a)
    body = '''  <!-- 坐标轴：origin=(110,360), sx=36, sy=46. -->
  <defs><clipPath id="introPlotClip"><rect x="111" y="134" width="653" height="260"/></clipPath></defs>
'''
    body += line(110,360,765,360,'marker-end="url(#lgIArrow)"') + line(110,392,110,130,'marker-end="url(#lgIArrow)"')
    body += text(760,383,'x') + text(94,135,'y') + text(97,379,'O')
    for x in [1,2,4,8,16]:
        px = 110 + 36*x
        body += line(px,355,px,365) + text(px,384,str(x),extra='text-anchor="middle"')
    for y in [1,2,3,4]:
        py = 360 - 46*y
        body += line(105,py,115,py) + text(100,py+5,str(y),extra='text-anchor="end"')
    data = curve(math.log2,.6,18,110,360,36,46, log_spacing=True)
    body += path(data,'#2563eb','intro-log-curve','log2','110 360 36 46','clip-path="url(#introPlotClip)"')
    body += text(590,158,'y = log₂x','#1d4ed8',15,'font-weight="700"')
    for n in range(5):
        body += dot(110+36*2**n,360-46*n,f'({2**n}, {n})')
    body += '''<g class="motion"><circle id="intro-moving-point" cx="146" cy="360" r="8" fill="#f59e0b" stroke="#fff" stroke-width="2">
      <animate attributeName="cx" values="146;182;254;398;686;146" keyTimes="0;.2;.4;.6;.8;1" calcMode="discrete" dur="10s" repeatCount="indefinite"/>
      <animate attributeName="cy" values="360;314;268;222;176;360" keyTimes="0;.2;.4;.6;.8;1" calcMode="discrete" dur="10s" repeatCount="indefinite"/>
    </circle></g>
    <circle class="still" cx="398" cy="222" r="8" fill="#f59e0b" stroke="#fff" stroke-width="2"/>
'''
    body += text(44,404,'x 每乘 2，y 就加 1；横轴使用线性刻度，1→2→4→8→16 的间距逐次翻倍。',size=12)
    s = s[:a] + body + '\n\n' + s[b:]
    # Below, equal-size cards count the stages; they are not x-axis tick marks.
    s = s.replace('把 1 不断乘 2，得到 2、4、8、16；对数就是记录你乘了几次。',
                  '每格代表一次翻倍（不是 x 轴刻度）；橙点与当前卡片同步，每次停留 2 秒。')
    return s


def inverse():
    s = '''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 800 580" width="100%" role="img" aria-labelledby="logInvTitle logInvDesc">
<title id="logInvTitle">指数与对数：互换横纵坐标</title>
<desc id="logInvDesc">两个独立线性坐标系分别画 y=2^x 与 y=log₂x。左侧 (n,2^n) 对应右侧 (2^n,n)。在同一等比例坐标系中，两条曲线关于 y=x 对称。</desc>
<style>text{font-family:'Microsoft YaHei','PingFang SC',sans-serif}.still{display:none}@media(prefers-reduced-motion:reduce){.motion{display:none}.still{display:inline}}</style>
<defs><clipPath id="expClip"><rect x="55" y="145" width="300" height="350"/></clipPath><clipPath id="logClip"><rect x="461" y="145" width="290" height="350"/></clipPath></defs>
<rect width="800" height="580" rx="14" fill="#f7f9fd"/>
<rect x="24" y="82" width="360" height="470" rx="10" fill="#fff" stroke="#c7d2e8"/>
<rect x="416" y="82" width="360" height="470" rx="10" fill="#fff" stroke="#c7d2e8"/>
'''
    s += text(30,38,'指数与对数：同一个关系的两种写法','#1e3a8a',23,'font-weight="800"')
    s += text(30,64,'2³ = 8  ⟺  log₂8 = 3：交换输入与输出，也就是交换横坐标与纵坐标。',size=14)
    s += text(44,112,'① y = 2ˣ：增长越来越快','#1d4ed8',16,'font-weight="700"')
    s += text(436,112,'② y = log₂x：增长越来越慢','#0f766e',16,'font-weight="700"')
    # Each panel has its own clearly labelled linear axes. No false screen reflection.
    s += line(55,450,350,450)+line(100,490,100,145)+text(345,473,'x')+text(82,149,'y')+text(84,467,'O')
    for x in [1,2,3]:
        s += line(100+60*x,446,100+60*x,454)+text(100+60*x,471,str(x),extra='text-anchor="middle"')
    for y in [1,2,4,8]:
        s += line(96,450-32*y,104,450-32*y)+text(91,455-32*y,str(y),extra='text-anchor="end"')
    s += path(curve(lambda x:2**x,-.7,3.2,100,450,60,32),'#2563eb','inverse-exp-curve','exp2','100 450 60 32','clip-path="url(#expClip)"')
    s += line(460,390,750,390)+line(460,490,460,145)+text(744,414,'x')+text(443,149,'y')+text(444,407,'O')
    for x in [1,2,4,8]:
        s += line(460+32*x,386,460+32*x,394)+text(460+32*x,412,str(x),extra='text-anchor="middle"')
    for y in [-1,1,2,3]:
        s += line(456,390-60*y,464,390-60*y)+text(451,395-60*y,str(y),extra='text-anchor="end"')
    s += path(curve(math.log2,.32,9,460,390,32,60,log_spacing=True),'#0d9488','inverse-log-curve','log2','460 390 32 60','clip-path="url(#logClip)"')
    for n in range(4):
        s += dot(100+60*n,450-32*2**n,f'({n},{2**n})','#2563eb')
        s += dot(460+32*2**n,390-60*n,f'({2**n},{n})',dx=-31 if n == 3 else 7)
    # Simultaneous discrete frames: exactly corresponding inverse points.
    for cx,cy,xs,ys,color in [(100,418,'100;160;220;280;100','418;386;322;194;418','#f59e0b'),
                              (492,390,'492;524;588;716;492','390;330;270;210;390','#f59e0b')]:
        s += f'<g class="motion"><circle cx="{cx}" cy="{cy}" r="7" fill="{color}" stroke="#fff" stroke-width="2">'
        for attr,values in [('cx',xs),('cy',ys)]:
            s += f'<animate attributeName="{attr}" values="{values}" keyTimes="0;.25;.5;.75;1" calcMode="discrete" dur="8s" repeatCount="indefinite"/>'
        s += '</circle></g>'
    s += text(44,520,'定义域 x∈R · 值域 y&gt;0 · 过 (0,1)',size=12)
    s += text(436,520,'定义域 x&gt;0 · 值域 y∈R · 过 (1,0)',size=12)
    s += text(30,568,'两图采用不同单位长度展示；在同一等比例坐标系中，反函数图像才关于 y=x 对称。','#0f766e',12)
    return s+'</svg>\n'


def graph():
    p = ROOT / 'math-log-graph.svg'
    s = p.read_text(encoding='utf-8')
    s = s.replace('；动画让底数从 2 连续变化到 10，展示曲线如何越来越平缓。', '；各曲线按同一线性坐标映射计算，定点位于 (1,0)。')
    s = s.replace('四条曲线都过 (1,0)：底数越大越平缓，底数小于 1 就翻到下方。',
                  '四条曲线都过 (1,0)；底数互为倒数时关于 x 轴对称，x&lt;1 的部分也要看。')
    a = s.index('  <!-- 坐标轴 -->') if '  <!-- 坐标轴 -->' in s else s.index('<defs><clipPath id="logFamilyClip"')
    b = s.index('  <!-- 图例 -->',a)
    body = '  <!-- 坐标轴 -->\n<defs><clipPath id="logFamilyClip"><rect x="131" y="230" width="339" height="268"/></clipPath></defs>'
    body += line(70,360,470,360,'marker-end="url(#lg2Arrow)"') + line(130,500,130,120,'marker-end="url(#lg2Arrow)"')
    body += text(460,382,'x')+text(110,126,'y')+text(113,380,'O')
    for x in [1,2,4,6,8]:
        body += line(130+40*x,356,130+40*x,364)+text(130+40*x,382,str(x),extra='text-anchor="middle"')
    for y in [-3,-2,-1,1,2,3]:
        body += line(126,360-36*y,134,360-36*y)+text(120,365-36*y,str(y),extra='text-anchor="end"')
    for base,color,dash,ident in [(2,'#2563eb',False,'log-base-2'),(10,'#7c3aed',True,'log-base-10'),(.5,'#dc2626',False,'log-base-half'),(.1,'#ea580c',True,'log-base-tenth')]:
        body += path(curve(lambda x:math.log(x,base),.03,8.5,130,360,40,36,log_spacing=True),color,ident,'log:'+str(base),'130 360 40 36',
                     'clip-path="url(#logFamilyClip)"'+(' stroke-dasharray="7 4"' if dash else ''))
    body += '<circle id="log-common-point" cx="170" cy="360" r="6" fill="#f59e0b" stroke="#fff" stroke-width="2" class="pulse"/>'
    body += text(180,404,'(1,0) 四条曲线共同交点','#b45309',12,'font-weight="700"')
    return s[:a]+body+'\n'+s[b:]


def main():
    for name, build in [('intro-math-log.svg', intro), ('math-log-inverse.svg', inverse), ('math-log-graph.svg', graph)]:
        (ROOT/name).write_text(build().replace('><', '>\n<'), encoding='utf-8', newline='\n')
        print('Updated', name)


if __name__ == '__main__':
    main()
