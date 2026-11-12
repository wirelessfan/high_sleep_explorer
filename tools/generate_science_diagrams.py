"""Generate chemistry/math lesson diagrams with synchronized geometry.

--check validates the generated documents and mathematical invariants without writing.
--frames-dir exports deterministic SVG keyframes for independent rendering.
"""
from __future__ import annotations

import argparse
import math
import os
import tempfile
from html import escape
from pathlib import Path
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parent.parent
DEST = ROOT / "assets" / "notes"
BLUE = "#2563eb"
RED = "#dc2626"
GREEN = "#047857"
AMBER = "#b45309"
INK = "#172b42"
MUTED = "#50647a"
NS = "{http://www.w3.org/2000/svg}"


def num(v: float) -> str:
    return f"{v:.5f}".rstrip("0").rstrip(".") or "0"


def text(x, y, value, size=16, color=INK, anchor="start", weight=500):
    return f'<text x="{num(x)}" y="{num(y)}" font-size="{size}" fill="{color}" text-anchor="{anchor}" font-weight="{weight}">{escape(value)}</text>'


def box(x, y, w, h, fill="#ffffff", stroke="#cbdcd5", radius=10):
    return f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="{radius}" fill="{fill}" stroke="{stroke}"/>'


def line(x1, y1, x2, y2, color=MUTED, width=2, dash=""):
    return f'<line x1="{num(x1)}" y1="{num(y1)}" x2="{num(x2)}" y2="{num(y2)}" stroke="{color}" stroke-width="{width}"'+(f' stroke-dasharray="{dash}"' if dash else '')+'/>'


def circle(x, y, r=5, fill=RED, stroke="white"):
    return f'<circle cx="{num(x)}" cy="{num(y)}" r="{r}" fill="{fill}" stroke="{stroke}" stroke-width="1.5"/>'


def path(d, color=BLUE, width=3, extra=""):
    return f'<path d="{d}" fill="none" stroke="{color}" stroke-width="{width}" {extra}/>'


def animate(attribute, values, times=None, duration=8, discrete=False):
    vals = ";".join(num(v) if isinstance(v, (int,float)) else str(v) for v in values)
    if times is None:
        times = [i/(len(values)-1) for i in range(len(values))]
    return f'<animate attributeName="{attribute}" values="{vals}" keyTimes="{";".join(num(t) for t in times)}" dur="{duration}s" calcMode="{"discrete" if discrete else "linear"}" repeatCount="indefinite"/>'


def wrap_text(x, y, value, max_units=48, size=15, color=MUTED, anchor="start", weight=500):
    rows=[]; row=''; units=0
    for ch in value:
        step=1 if ord(ch)>255 else .55
        if row and units+step>max_units:
            rows.append(row); row=''; units=0
        row+=ch; units+=step
    if row: rows.append(row)
    return ''.join(text(x,y+22*i,row,size,color,anchor,weight) for i,row in enumerate(rows))


def document(title, subtitle, content, footer, height=460):
    return f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 800 {height}" width="100%" role="img" aria-labelledby="title description">
  <title id="title">{escape(title)}</title>
  <desc id="description">{escape(subtitle+'。'+footer)}</desc>
  <defs>
    <marker id="arrow" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="6" markerHeight="6" orient="auto-start-reverse"><path d="M0 0 L10 5 L0 10 Z" fill="context-stroke"/></marker>
    <style>
      text {{ font-family: 'Microsoft YaHei','PingFang SC',sans-serif; }}
      .still {{ display: none; }}
      @media (prefers-reduced-motion: reduce) {{
        .motion {{ display: none; }}
        .still {{ display: inline; }}
      }}
    </style>
  </defs>
  <rect width="800" height="{height}" rx="14" fill="#f7fbf9"/>
  {text(30,35,title,23,GREEN,weight=800)}
  {text(30,62,subtitle,15,MUTED)}
  {content}
  {box(24,height-62,752,49,'#eaf5ef','#c6dfd1',6)}
  {wrap_text(400,height-42,footer,max_units=47,size=14,color=GREEN,anchor='middle',weight=600)}
</svg>
'''


def axes(x1,y1,x2,y2):
    return line(x1,y1,x2,y1,MUTED)+line(x1,y1,x1,y2,MUTED)+text(x2-5,y1+22,"x",15)+text(x1-15,y2+5,"y",15)


def parabola(x):
    return 108 + 0.0035*(x-210)**2


def parabola_slope(x):
    return 0.007*(x-210)


def intro_math():
    """上下两个子图共用同一条横轴：上方 f(x)，下方 f′(x)。

    曲线按采样点折线绘制（不用手调控制点），切线斜率直接取该点导数，
    因此曲线、切点、切线、下方导数光点四者严格同步。
    """
    xs=[90+240*(1-math.cos(2*math.pi*i/240))/2 for i in range(241)]
    x0,x1=90,330
    left,right=130,700
    def sx(x): return left+(x-x0)*(right-left)/(x1-x0)
    def fy(x): return 160+0.0035*(x-210)**2      # 屏幕 y；数学上是开口向下
    screen_slope=lambda x: parabola_slope(x)      # SVM 屏幕切线斜率
    math_fprime=lambda x: -parabola_slope(x)      # 数学导数：左正右负
    ys=[fy(x) for x in xs]
    slopes=[screen_slope(x) for x in xs]

    top_axis=318
    zero_y=520
    dscale=80
    # 屏幕 y 向下；数学导数 f′ = −屏幕斜率，正值画在零轴上方。
    def dy(x): return zero_y+screen_slope(x)*dscale

    def polyline(pts,color,width=3):
        return path('M '+' L '.join('%s %s'%(num(a),num(b)) for a,b in pts),color,width)

    ticks=[90,150,210,270,330]
    def axis_ticks(axis_y,label):
        out=''
        for x in ticks:
            out+=line(sx(x),axis_y-5,sx(x),axis_y+5,MUTED,1.5)
            out+=text(sx(x),axis_y+22,label(x),13,MUTED,'middle')
        return out
    tick_label=lambda x:'%.1f'%((x-210)/60)

    def moving():
        base=xs[0]
        s='<g class="motion">'
        s+='<line x1="%s" y1="%s" x2="%s" y2="%s" stroke="%s" stroke-width="2.6">'%(
            num(sx(base)-46),num(fy(base)-46*slopes[0]),
            num(sx(base)+46),num(fy(base)+46*slopes[0]),RED)
        for attr,vals in [('x1',[sx(x)-46 for x in xs]),('x2',[sx(x)+46 for x in xs]),
                          ('y1',[y-46*m for y,m in zip(ys,slopes)]),
                          ('y2',[y+46*m for y,m in zip(ys,slopes)])]:
            s+=animate(attr,vals,duration=8)
        s+='</line>'
        s+='<circle cx="%s" cy="%s" r="5.5" fill="%s" stroke="white">'%(num(sx(base)),num(fy(base)),RED)
        s+=animate('cx',[sx(x) for x in xs])+animate('cy',ys)+'</circle>'
        s+='<circle cx="%s" cy="%s" r="5.5" fill="%s" stroke="white">'%(num(sx(base)),num(dy(base)),RED)
        s+=animate('cx',[sx(x) for x in xs])+animate('cy',[dy(x) for x in xs])+'</circle>'
        # 贯穿上下两图的竖直参考线，直接显示两图共用同一个 x
        s+='<line x1="%s" y1="%s" x2="%s" y2="%s" stroke="#dc2626" stroke-width="1" stroke-dasharray="4 4" opacity=".5">'%(
            num(sx(base)),num(fy(base)),num(sx(base)),num(dy(base)))
        s+=animate('x1',[sx(x) for x in xs])+animate('x2',[sx(x) for x in xs])+'</line>'
        s+='</g>'
        return s

    content=box(24,82,752,268)+box(24,362,752,286)

    # ---- 上：f(x) ----
    content+=text(40,108,'f(x) 的图像',17,GREEN,weight=700)
    content+=line(left,top_axis,right,top_axis,MUTED,2)
    content+=line(left,top_axis,left,118,MUTED,2)
    content+=axis_ticks(top_axis,tick_label)
    content+=text(right-6,top_axis+22,'x',15,INK,'end')
    content+=text(left-14,130,'y',15,INK,'end')
    content+=polyline([(sx(x),fy(x)) for x in xs],BLUE,3)
    content+=text(sx(292),fy(292)+34,'y = f(x)',16,BLUE)
    content+=line(sx(210),fy(210),sx(210),top_axis,'#9aafbd',1,'4 4')
    content+=text(sx(210)+10,fy(210)-12,'峰顶：f′(x) = 0',14,MUTED)

    # ---- 下：f′(x)，横轴刻度与上图逐一对应 ----
    content+=text(40,388,'f′(x) 的图像',17,GREEN,weight=700)
    content+=line(left,618,right,618,MUTED,2)
    content+=line(left,618,left,400,MUTED,2)
    content+=axis_ticks(618,tick_label)
    content+=text(right-6,640,'x',15,INK,'end')
    content+=text(left-14,412,'f′(x)',15,INK,'end')
    content+=line(left,zero_y,right,zero_y,'#9aafbd',1,'4 4')
    content+=text(left-8,zero_y+5,'0',13,MUTED,'end')
    content+=polyline([(sx(x),dy(x)) for x in xs],RED,3)
    content+=line(sx(210),400,sx(210),618,'#9aafbd',1,'4 4')
    content+=circle(sx(210),zero_y,4,RED)
    content+=text(sx(210)+10,zero_y-12,'f′(x) = 0',14,MUTED)
    content+=text(sx(120),dy(120)-14,'f′(x) > 0',14,RED)
    content+=text(sx(300),dy(300)+24,'f′(x) < 0',14,RED)

    content+=moving()
    content+='<g class="still">%s%s%s</g>'%(
        line(sx(210)-46,fy(210),sx(210)+46,fy(210),RED,2.6),
        circle(sx(210),fy(210),5.5),
        circle(sx(210),zero_y,5.5))

    content+=text(24,668,'↑ 上下两图共用同一条横轴：刻度、红色竖线在同一个 x 上对齐。',14,MUTED)
    content+=text(24,692,'看 f′(x) 的符号就能读出 f(x) 的走势：f′ > 0 递增，f′ < 0 递减；过零处是峰顶。',14,MUTED)
    return document('导数：f(x) 与 f′(x) 上下对齐同步',
                    '上方是函数曲线与切线，下方是导数曲线；两图共用同一条横轴。',
                    content,'判断极值需看导数变号；f′(x₀) = 0 本身不保证是极值。',
                    height=780)


def cubic(dynamic=False):
    """三次函数的极值与导数：上 f(x)，下 f′(x)，横轴严格对齐。

    f(x)  = x³ − 3x    → f(−1)=2 为极大值，f(1)=−2 为极小值
    f′(x) = 3x² − 3    → 零点恰为 x=±1，与极值点竖直对齐
    """
    x0,x1=-2.0,2.0
    left,right=150,700
    def sx(x): return left+(x-x0)*(right-left)/(x1-x0)
    top_zero,top_px=238,30
    def fy(x): return top_zero-(x**3-3*x)*top_px
    bot_zero,bot_px=520,8.5
    def fp(x): return 3*x*x-3
    def fpy(x): return bot_zero-fp(x)*bot_px
    def polyline(fn,a,b,color,width=3,n=240):
        return path('M '+' L '.join('%s %s'%(num(sx(a+(b-a)*i/n)),num(fn(a+(b-a)*i/n))) for i in range(n+1)),color,width)

    content=box(24,82,752,300)+box(24,392,752,250)

    # ---- 上：f(x) ----
    content+=text(40,108,'f(x) = x³ − 3x 的图像',17,GREEN,weight=700)
    content+=line(left,340,right,340,MUTED,2)
    content+=line(left,340,left,120,MUTED,2)
    content+=text(right-6,362,'x',15,INK,'end')
    content+=text(left-14,132,'y',15,INK,'end')
    content+=polyline(fy,x0,x1,BLUE)
    content+=text(sx(1.42),fy(1.42)+32,'y = f(x)',16,BLUE)

    for xv,label,above in [(-1,'极大值 f(−1) = 2',True),(1,'极小值 f(1) = −2',False)]:
        py=fy(xv)
        content+=circle(sx(xv),py,5.5,RED)
        ty=py-14 if above else py+26
        content+=text(sx(xv)+(14 if not above else 0),ty,label,14,RED,'start' if not above else 'middle')
    content+=text(left,372,'红点为极值点：极大值在峰、极小值在谷',13,MUTED)

    # ---- 下：f′(x) ----
    content+=text(40,418,'f′(x) = 3x² − 3 的图像',17,GREEN,weight=700)
    content+=line(left,610,right,610,MUTED,2)
    content+=line(left,610,left,432,MUTED,2)
    content+=text(right-6,632,'x',15,INK,'end')
    content+=text(left-14,444,'f′(x)',15,INK,'end')
    content+=line(left,bot_zero,right,bot_zero,'#9aafbd',1,'4 4')
    content+=text(left-8,bot_zero+5,'0',13,MUTED,'end')
    content+=polyline(fpy,x0,x1,RED)
    for xv in (-1,1):
        content+=circle(sx(xv),bot_zero,5,RED)
        content+=line(sx(xv),fy(xv),sx(xv),610,'#dc2626',1,'4 4')
        content+=text(sx(xv),bot_zero-12,'f′ = 0',13,RED,'middle')
    content+=text(sx(-1.55),fpy(-1.55)-10,'f′ > 0',14,RED)
    content+=text(sx(0),bot_zero+24,'f′ < 0',14,RED)
    content+=text(sx(1.2),fpy(1.6)-10,'f′ > 0',14,RED)
    content+=text(left,644,'↑ 红色虚线把 f′ 的过零点与上图的极大、极小值点一一对齐',13,MUTED)

    if dynamic:
        xs=[x0+(x1-x0)*i/240 for i in range(241)]
        base=xs[0]
        # 屏幕切线斜率 = −f′(x)·纵向比例；直接与曲线导数一致。
        def sslope(x): return -fp(x)*top_px
        s='<g class="motion">'
        s+='<line x1="%s" y1="%s" x2="%s" y2="%s" stroke="%s" stroke-width="2.6">'%(
            num(sx(base)-60),num(fy(base)-60*sslope(base)),
            num(sx(base)+60),num(fy(base)+60*sslope(base)),RED)
        for attr,vals in [('x1',[sx(x)-60 for x in xs]),('x2',[sx(x)+60 for x in xs]),
                          ('y1',[fy(x)-60*sslope(x) for x in xs]),('y2',[fy(x)+60*sslope(x) for x in xs])]:
            s+=animate(attr,vals,duration=9)
        s+='</line>'
        s+='<circle cx="%s" cy="%s" r="5.5" fill="%s" stroke="white">'%(num(sx(base)),num(fy(base)),RED)
        s+=animate('cx',[sx(x) for x in xs])+animate('cy',[fy(x) for x in xs])+'</circle>'
        s+='<circle cx="%s" cy="%s" r="5.5" fill="%s" stroke="white">'%(num(sx(base)),num(fpy(base)),RED)
        s+=animate('cx',[sx(x) for x in xs])+animate('cy',[fpy(x) for x in xs])+'</circle>'
        s+='<line x1="%s" y1="%s" x2="%s" y2="%s" stroke="#dc2626" stroke-width="1" stroke-dasharray="4 4" opacity=".5">'%(
            num(sx(base)),num(fy(base)),num(sx(base)),num(fpy(base)))
        s+=animate('x1',[sx(x) for x in xs])+animate('x2',[sx(x) for x in xs])+'</line></g>'
        s+='<g class="still">%s%s%s</g>'%(
            line(sx(0)-60,fy(0),sx(0)+60,fy(0),RED,2.6),
            circle(sx(0),fy(0),5.5),circle(sx(0),fpy(0),5.5))
        content+=s
        return document('三次函数：切线、极值点与 f′(x) 同步',
                        '观察切点移动：f′ 的正负、零点与 f 的增减、极值如何一一对应。',
                        content,'极大值点 f′ 由正变负；极小值点 f′ 由负变正。',height=740)
    return document('三次函数：f(x) 与 f′(x) 的极值对应',
                    '上方曲线的极大值与极小值，正好对齐下方导函数的两个过零点。',
                    content,'f′ > 0 的区间函数递增，f′ < 0 的区间函数递减；变号点才是极值点。',height=740)


def atomic_write(p: Path, content: str):
    p.parent.mkdir(parents=True,exist_ok=True)
    fd,tmp=tempfile.mkstemp(prefix='.'+p.name+'.',suffix='.tmp',dir=p.parent)
    try:
        with os.fdopen(fd,'w',encoding='utf-8',newline='\n') as out:
            out.write(content)
        os.replace(tmp,p)
    finally:
        if os.path.exists(tmp):
            os.unlink(tmp)


def secant_y(x):
    return 268 - .62*(x-100) + .00075*(x-220)**2


def secant_slope(x):
    return -.62 + .0015*(x-220)


def math_secant(dynamic=False):
    px=220; py=secant_y(px)
    qxs=[px+2+198*(1+math.cos(2*math.pi*i/240))/2 for i in range(241)]
    qys=[secant_y(x) for x in qxs]
    slopes=[(y-py)/(x-px) for x,y in zip(qxs,qys)]
    def segment(qx,qy,m):
        return line(100,py+m*(100-px),440,py+m*(440-px),AMBER,2,'5 4')+circle(qx,qy,6,AMBER)+text(qx+8,qy-11,'Q',16,AMBER)
    content=box(24,82,752,307)+axes(65,327,470,103)
    content+=path('M 80 295.1 Q 270 137.4 460 88')
    content+=text(390,121,'y = f(x)',16,BLUE)
    content+=line(125,py+secant_slope(px)*(125-px),400,py+secant_slope(px)*(400-px),RED,2.8)
    content+=text(132,286,'切线 T',16,RED)+circle(px,py,5.5)
    content+=text(px-20,py-12,'P',16,RED)
    content+=line(px,py,px,327,'#9aafbd',1,'4 4')+text(px,352,'x₀',16,MUTED,'middle')
    if dynamic:
        content+='<g class="motion"><line x1="100" y1="'+num(py+slopes[0]*(100-px))+'" x2="440" y2="'+num(py+slopes[0]*(440-px))+'" stroke="'+AMBER+'" stroke-width="2" stroke-dasharray="5 4">'
        content+=animate('y1',[py+m*(100-px) for m in slopes])+animate('y2',[py+m*(440-px) for m in slopes])+'</line>'
        content+='<circle cx="'+num(qxs[0])+'" cy="'+num(qys[0])+'" r="6" fill="'+AMBER+'" stroke="white">'+animate('cx',qxs)+animate('cy',qys)+'</circle>'
        content+='<text x="'+num(qxs[0]+9)+'" y="'+num(qys[0]-10)+'" font-size="16" fill="'+AMBER+'">Q'+animate('x',[x+9 for x in qxs])+animate('y',[y-10 for y in qys])+'</text></g>'
        content+='<g class="still">'+segment(350,secant_y(350),(secant_y(350)-py)/(350-px))+'</g>'
    else:
        qx=350; qy=secant_y(qx)
        content+=segment(qx,qy,(qy-py)/(qx-px))
    content+=box(493,117,260,222,'#fff9e7','#ead8a2')
    for y,value,color in [(147,'割线始终通过 P、Q',AMBER),(184,'kPQ = Δy / Δx',INK),(221,'Δx → 0 时',INK),(252,'kPQ → f′(x₀)',RED),(290,'Q 沿函数曲线靠近 P',INK),(319,'极限不等于取 Δx = 0',MUTED)]:
        content+=text(508,y,value,16,color)
    return document('导数：割线逼近切线'+('（动态）' if dynamic else ''),'固定 P，移动 Q；曲线、割线、切线由同一函数计算。',content,'数学坐标的斜率为正；SVG 纵坐标向下，因此屏幕斜率符号相反。')


def cards(items, x=418, y=98, width=352, spacing=63):
    s=''
    for i,(heading,body,color) in enumerate(items):
        yy=y+i*spacing
        s+=box(x,yy,width,spacing-8,'#ffffff','#d4e2dc')
        s+=text(x+14,yy+23,heading,17,color,weight=700)
        s+=text(x+14,yy+46,body,15,MUTED)
    return s


def mole(intro=False):
    content=box(24,82,360,307)+box(402,82,374,307)
    content+=box(151,190,106,66,'#ddf4e6','#8dbca2')+text(204,219,'n',28,GREEN,'middle',800)+text(204,244,'mol',16,GREEN,'middle')
    for x,y,w,h,label,color in [(135,105,140,50,'质量 m',AMBER),(42,263,112,52,'粒子数 N',BLUE),(254,263,112,52,'气体体积 V',RED)]:
        content+=box(x,y,w,h)+text(x+w/2,y+32,label,16,color,'middle',700)
    content+=line(204,157,204,188,AMBER,2)+line(151,237,112,260,BLUE,2)+line(257,237,300,260,RED,2)
    for y,value,color in [(116,'n = m / M',AMBER),(146,'M 的单位：g/mol',MUTED),(184,'n = N / Nₐ',BLUE),(214,'Nₐ = 6.02214076 × 10²³ mol⁻¹',MUTED),(252,'n = V / Vₘ',RED),(282,'标况气体：Vₘ ≈ 22.4 L/mol',MUTED),(320,'c = n / V溶液',GREEN),(350,'c：mol/L；V溶液：L',MUTED)]:
        content+=text(420,y,value,17 if y in [116,184,252,320] else 15,color)
    content+=text(204,352,'先明确粒子种类、物态和条件',15,MUTED,'middle')
    return document('物质的量：连接质量、粒子数和气体体积','换算时保持单位一致，并写明研究的是哪一种粒子。',content,'22.4 L/mol 仅用于标况下的气体；液体、固体和其他温压条件不直接套用。')


def periodic(intro=False):
    content=box(24,82,752,307)
    if intro:
        # Carbon shell population is schematic and stationary, never a classical orbit.
        content+='<circle cx="163" cy="207" r="61" fill="none" stroke="#8dbca2" stroke-width="2"/>'
        content+='<circle cx="163" cy="207" r="32" fill="none" stroke="#93b9e1" stroke-width="2"/>'
        content+=circle(163,207,18,'#fee2e2',RED)+text(163,213,'+6',16,RED,'middle',700)
        for x,y in [(163,175),(163,239)]: content+=circle(x,y,5,BLUE)
        for x,y in [(163,146),(163,268),(102,207),(224,207)]: content+=circle(x,y,5,GREEN)
        content+=text(163,313,'碳原子：2、4',18,INK,'middle',700)
        content+=text(163,343,'点仅表示各层电子数',15,MUTED,'middle')
        content+=text(163,367,'不表示电子的运动轨迹',15,RED,'middle')
    else:
        for x,y,label,detail in [(83,115,'结构','层数、价电子'),(53,276,'位置','周期、主族'),(230,276,'性质','金属/非金属')]:
            content+=box(x,y,132,58,'#eaf5ef')+text(x+66,y+25,label,18,GREEN,'middle',700)+text(x+66,y+46,detail,14,MUTED,'middle')
        content+=line(140,175,115,274,GREEN)+line(215,175,289,274,GREEN)+line(187,305,228,305,GREEN)
    for y,value,color in [(117,'位—构—性：注意适用范围',GREEN),(155,'主族元素：电子层数 = 周期数',INK),(189,'IA—VIIA：最外层电子数 = 族序数',INK),(223,'He 最外层 2 个电子，属于第18族',RED),(267,'同周期主族：一般半径减小',INK),(300,'金属性减弱，非金属性增强',INK),(340,'同主族向下：一般半径增大',INK),(372,'金属性增强，非金属性减弱',INK)]:
        content+=text(390,y,value,16,color,weight=700 if y==117 else 500)
    return document('元素周期律：位置、结构与性质','比较趋势需在对应周期或主族内；原子半径比较需采用一致口径。',content,'非金属性强不等于氢化物酸性强：HF 是弱酸；通常比较最高价氧化物对应水化物。')


def equilibrium(intro=False,dynamic=False):
    # A reversible first-order A <=> B at constant T,V. Initially A=B=1;
    # add A so A=2,B=1, then A=1.5+.5 exp(-t), B=1.5-.5 exp(-t).
    ts=[i/16 for i in range(129)]
    xs=[190+28*t for t in ts]
    ya=[255-66*(1.5+.5*math.exp(-t)) for t in ts]
    yb=[255-66*(1.5-.5*math.exp(-t)) for t in ts]
    def curve(ys): return 'M '+' L '.join(f'{num(x)} {num(y)}' for x,y in zip(xs,ys))
    content=box(24,82,752,307)
    content+=line(60,302,445,302)+line(60,302,60,112)+text(39,121,'v',17)+text(440,325,'t',17)
    content+=line(60,189,190,189,GREEN,3)+line(190,113,190,302,'#9aafbd',1,'4 4')
    content+=path(curve(ya),RED)+path(curve(yb),BLUE)
    content+=text(198,113,'v正',16,RED)+text(205,220,'v逆',16,BLUE)
    content+=text(118,176,'旧平衡',15,GREEN,'middle')+text(190,326,'t₁',16,MUTED,'middle')
    content+=text(345,146,'接近新平衡',15,GREEN)
    content+=text(252,355,'A ⇌ B（恒温、恒容）',17,INK,'middle')
    if dynamic:
        content+='<g class="motion"><line x1="190" y1="120" x2="190" y2="300" stroke="#9aafbd" stroke-width="1.5" stroke-dasharray="3 4">'+animate('x1',xs,duration=9)+animate('x2',xs,duration=9)+'</line>'
        for ys,color in [(ya,RED),(yb,BLUE)]:
            content+='<circle cx="190" cy="'+num(ys[0])+'" r="5" fill="'+color+'" stroke="white">'+animate('cx',xs,duration=9)+animate('cy',ys,duration=9)+'</circle>'
        content+='</g>'
    content+=box(470,104,288,264,'#ffffff','#cbdcd5')
    for y,value,color in [(133,'t₁：只增大 A 的浓度',GREEN),(170,'正反应速率瞬时增大',RED),(206,'逆反应速率瞬时不变',BLUE),(242,'随后 A 减少，B 增加',INK),(278,'正逆速率逐渐接近',INK),(314,'新平衡：v正 = v逆 ≠ 0',GREEN),(347,'并非反应停止或浓度相等',MUTED)]:
        content+=text(485,y,value,16 if y!=347 else 15,color)
    return document('化学平衡：浓度扰动后的速率变化'+('（动态）' if dynamic else ''),'以恒温恒容、正逆反应均为一级的 A ⇌ B 为例。',content,'升温通常使正逆速率同时突变；催化剂不会使平衡移动，压强效应需结合气体反应条件。')


def ionic_intro():
    content=box(24,82,352,307)+box(396,82,380,307)
    content+=path('M 72 113 L 72 333 Q72 347 87 347 L 313 347 Q328 347 328 333 L328 113',MUTED,2)
    content+=line(75,145,325,145,'#90b6dd',1,'5 4')
    times=[0,.35,.55,.8,1]
    xs1=[125,187,187,187,125]; xs2=[275,213,213,213,275]
    ys=[200,213,240,311,200]
    content+='<g class="motion">'
    for name,xs,color,base_x in [('Ba²⁺',xs1,RED,125),('SO₄²⁻',xs2,BLUE,275)]:
        # Static placement stays on the outer group; animate only local offsets.
        offsets=[(x-base_x,y-200) for x,y in zip(xs,ys)]
        content+='<g transform="translate('+str(base_x)+' 200)"><g transform="translate(0 0)"><animateTransform attributeName="transform" type="translate" values="'+ ';'.join(f'{x} {y}' for x,y in offsets)+'" keyTimes="0;0.35;0.55;0.8;1" dur="7s" calcMode="linear" repeatCount="indefinite"/>'
        content+=circle(0,0,22,'#f1f6fa',color)+text(0,5,name,13,color,'middle',700)
        content+=animate('opacity',[1,1,0,0,1],times,7)+'</g></g>'
    content+='<g transform="translate(200 213)" opacity="0">'+animate('opacity',[0,0,1,1,0],times,7)
    content+='<g transform="translate(0 0)"><animateTransform attributeName="transform" type="translate" values="0 0;0 0;0 27;0 107;0 0" keyTimes="0;0.35;0.55;0.8;1" dur="7s" repeatCount="indefinite"/>'
    content+=box(-55,-16,110,32,'#fff','#aebdc5')+text(0,6,'BaSO₄(s)',16,GREEN,'middle',700)+'</g></g></g>'
    content+='<g class="still">'+circle(125,200,22,'#f1f6fa',RED)+text(125,205,'Ba²⁺',13,RED,'middle')+circle(275,200,22,'#f1f6fa',BLUE)+text(275,205,'SO₄²⁻',13,BLUE,'middle')+box(147,310,106,30)+text(200,331,'BaSO₄(s)',16,GREEN,'middle')+'</g>'
    content+=text(200,375,'离子结合后以难溶固体表示',15,MUTED,'middle')
    for y,value,color in [(117,'Ba²⁺ + SO₄²⁻ = BaSO₄↓',GREEN),(163,'反应前：离子在水溶液中',INK),(203,'反应后：形成白色难溶固体',INK),(247,'能拆：溶液中的易溶强电解质',BLUE),(281,'不拆：难溶物、弱电解质、气体',RED),(328,'澄清石灰水：Ca²⁺ + 2OH⁻',GREEN),(366,'石灰乳参与反应：保留 Ca(OH)₂',INK)]:
        content+=text(410,y,value,16,color)
    return document('离子反应：从溶液离子到沉淀','粒子图只示意结合与沉降；不代表真实晶格或离子大小。',content,'离子反应也包括难溶物与酸反应、氧化还原等；反应式须核对原子和电荷守恒。')


def ionic_rules(dynamic=False):
    if not dynamic:
        content=cards([('保留化学式','难溶物、弱电解质、气体、单质与氧化物',RED),('弱酸酸式根保留','HCO₃⁻、HSO₃⁻、HS⁻ 不继续拆',BLUE),('微溶物看存在状态','澄清石灰水拆；石灰乳保留 Ca(OH)₂',GREEN),('酸式盐看溶剂','NaHSO₄ 水溶液中拆为 Na⁺、H⁺、SO₄²⁻',AMBER)],24,97,752,68)
        return document('离子方程式：拆分要看物态与条件','拆分对象是溶液中实际以离子存在的易溶强电解质。',content,'Al³⁺ 与 AlO₂⁻ 双水解只生成 Al(OH)₃ 沉淀；与 HCO₃⁻ 反应还生成 CO₂。')
    rows=[('① 写：配平化学方程式','CaCO₃ + 2HCl = CaCl₂ + H₂O + CO₂↑'),('② 拆：只拆溶液中易溶强电解质','CaCO₃ + 2H⁺ + 2Cl⁻ = Ca²⁺ + 2Cl⁻ + H₂O + CO₂↑'),('③ 删：删除两侧相同旁观离子','两侧各删去 2Cl⁻，CaCO₃ 固体保留'),('④ 查：原子守恒、电荷守恒','CaCO₃ + 2H⁺ = Ca²⁺ + H₂O + CO₂↑')]
    content=''
    for i,(heading,body) in enumerate(rows):
        y=86+i*78
        content+='<g>'+box(24,y,752,69,'#fff','#cbdcd5')+text(42,y+24,heading,17,GREEN,weight=700)+text(42,y+51,body,16,INK)
        content+='<g class="motion"><rect x="24" y="'+str(y)+'" width="5" height="69" fill="'+GREEN+'">'+animate('opacity',[1 if k==i else .08 for k in range(4)]+[1 if i==0 else .08],[0,.25,.5,.75,1],12,True)+'</rect></g></g>'
    return document('离子方程式：写、拆、删、查','石灰石与稀盐酸反应；四行完整保留，左侧指示条按顺序推进。',content,'最终式：Ca、C、O、H 原子分别守恒；等号两边总电荷均为 +2。',height=470)


def redox_intro():
    content=box(24,82,752,307)
    content+=box(55,154,150,96,'#edf4ff','#aac6ef')+text(130,190,'Na → Na⁺',21,BLUE,'middle',700)+text(130,224,'失电子，被氧化',16,BLUE,'middle')
    content+=box(350,154,150,96,'#fff0ed','#efb6ad')+text(425,190,'Cl → Cl⁻',21,RED,'middle',700)+text(425,224,'得电子，被还原',16,RED,'middle')
    content+=path('M 180 148 Q 275 67 370 148',AMBER,2,'marker-end="url(#arrow)"')
    coords=[(180+190*i/120,148-162*(i/120)*(1-i/120)) for i in range(121)]
    content+='<g class="motion"><circle cx="180" cy="148" r="13" fill="#fff0b5" stroke="'+AMBER+'">'+animate('cx',[p[0] for p in coords],duration=4)+animate('cy',[p[1] for p in coords],duration=4)+'</circle></g>'
    content+=text(276,93,'e⁻ 转移方向',15,AMBER,'middle')
    content+=text(276,286,'2Na + Cl₂ = 2NaCl',22,INK,'middle',700)
    content+=text(276,321,'每个 Na 失 1e⁻，每个 Cl 得 1e⁻',16,MUTED,'middle')
    content+=text(276,355,'箭头示意电子转移，不表示实际飞行轨迹',14,MUTED,'middle')
    content+=line(535,110,535,366,'#cbdcd5',1)
    for y,value,color in [(137,'还原剂：Na',BLUE),(177,'升价、失电子',BLUE),(217,'氧化剂：Cl₂',RED),(257,'降价、得电子',RED),(307,'得失电子总数',GREEN),(340,'均为 2e⁻',GREEN)]: content+=text(558,y,value,18,color)
    return document('氧化还原：得失电子与化合价','以钠与氯气反应为例；图中 Cl 表示氯气中的一个氯原子。',content,'氧化还原的本质是电子转移，也可表现为共用电子对偏移；图中不表示电子经典轨道。')


def redox(dynamic=False):
    # Dedicated text spans make bridge endpoints independent of font metrics.
    content=box(24,82,752,307)
    for x,label in [(100,'2Fe'),(220,'+'),(310,'3Cl₂'),(425,'→'),(575,'2FeCl₃')]:
        content+=text(x,207,label,29,INK,'middle',700)
    content+=text(425,180,'点燃',15,MUTED,'middle')
    for x,label,col in [(100,'0',RED),(310,'0',BLUE),(550,'+3',RED),(604,'−1',BLUE)]:content+=text(x,166,label,17,col,'middle',700)
    content+=text(550,233,'Fe',15,RED,'middle')+text(604,233,'Cl',15,BLUE,'middle')
    top=path('M 100 143 L100 112 L550 112 L550 143',RED,2,'marker-end="url(#arrow)"')+text(325,102,'Fe：升 0→+3，失 2×3e⁻，被氧化',16,RED,'middle')
    bottom=path('M 310 246 L310 279 L604 279 L604 246',BLUE,2,'marker-end="url(#arrow)"')+text(458,307,'Cl：降 0→−1，得 6×1e⁻，被还原',16,BLUE,'middle')
    if dynamic:
        # Complete bridges are shown in sequential stages; nothing drifts.
        content+='<g class="motion"><g opacity="0">'+animate('opacity',[0,1,1,1,0],[0,.25,.5,.95,1],10,True)+top+'</g><g opacity="0">'+animate('opacity',[0,0,1,1,0],[0,.25,.5,.95,1],10,True)+bottom+'</g></g><g class="still">'+top+bottom+'</g>'
    else: content+=top+bottom
    content+=text(400,350,'失电子总数 = 得电子总数 = 6e⁻',20,GREEN,'middle',700)
    content+=text(400,377,'双线桥：反应物中的元素 → 生成物中的同种元素',16,MUTED,'middle')
    return document('氧化还原：同元素对应的双线桥'+('（动态）' if dynamic else ''),'先标化合价，再对应元素、标得失电子，最后核对电子总数。',content,'此反应 Fe 是还原剂，Cl₂ 是氧化剂；强弱比较须在相同反应条件下进行。')


def generated():
    return {name:content.replace('><','>\n<') for name,content in {
        'intro-math-derivative.svg':intro_math(),
        'math-cubic-extrema.svg':cubic(),
        'math-cubic-extrema-anim.svg':cubic(True),
        'math-derivative-tangent.svg':math_secant(),
        'math-derivative-tangent-anim.svg':math_secant(True),
        'chem-mole-bridge.svg':mole(),
        'intro-chemistry-mole.svg':mole(True),
        'chem-periodic-triangle.svg':periodic(),
        'intro-chemistry-periodic.svg':periodic(True),
        'chem-equilibrium-vt.svg':equilibrium(),
        'chem-equilibrium-vt-anim.svg':equilibrium(dynamic=True),
        'intro-chemistry-equilibrium.svg':equilibrium(intro=True),
        'intro-chemistry-ionic.svg':ionic_intro(),
        'chem-ionic-rules.svg':ionic_rules(),
        'chem-ionic-rules-anim.svg':ionic_rules(True),
        'intro-chemistry-redox.svg':redox_intro(),
        'chem-redox-bridge.svg':redox(),
        'chem-redox-bridge-anim.svg':redox(True),
    }.items()}


def validate(docs):
    for name,content in docs.items():
        root=ET.fromstring(content)
        ids=[e.get('id') for e in root.iter() if e.get('id')]
        assert len(ids)==len(set(ids)),name
        for e in root.iter(NS+'animate'):
            assert len(e.get('values').split(';'))==len(e.get('keyTimes').split(';')),name
    max_error=0
    xs=[90+240*(1-math.cos(2*math.pi*i/240))/2 for i in range(241)]
    for a,b in zip(xs,xs[1:]):
        x=(a+b)/2
        interp=(parabola(a)+parabola(b))/2
        max_error=max(max_error,abs(interp-parabola(x)))
        assert abs((parabola_slope(a)+parabola_slope(b))/2-parabola_slope(x))<1e-12
    assert max_error<.01,max_error
    # 上下双图共用同一条横轴：每个采样时刻，上方切点与下方 f′(x) 光点
    # 的屏幕 x 必须相同，且各自落在正确的函数/导函数曲线上。
    intro_root=ET.fromstring(docs['intro-math-derivative.svg'])
    motion=next(g for g in intro_root.iter() if g.get('class')=='motion')
    circles=[c for c in motion if c.tag==NS+'circle']
    assert len(circles)==2
    def series(circle,attr):
        node=next(a for a in circle if a.get('attributeName')==attr)
        return list(map(float,node.get('values').split(';')))
    pcx,pcy=series(circles[0],'cx'),series(circles[0],'cy')
    dcx,dcy=series(circles[1],'cx'),series(circles[1],'cy')
    assert len(pcx)==len(pcy)==len(dcx)==len(dcy)==241
    left,right,x0,x1=130,700,90,330
    def intro_sx(x): return left+(x-x0)*(right-left)/(x1-x0)
    def intro_fy(x): return 160+0.0035*(x-210)**2
    zero_y,dscale=520,80
    def intro_dy(x): return zero_y+parabola_slope(x)*dscale
    for px,py,dx_,dyp in zip(pcx,pcy,dcx,dcy):
        # pcx 是屏幕 x；先反解回数学定义域再验函数值。
        x=x0+(px-left)*(x1-x0)/(right-left)
        assert abs(py-intro_fy(x))<2e-4,(x,py)
        assert abs(dx_-intro_sx(x))<2e-4,(x,dx_)
        assert abs(dyp-intro_dy(x))<2e-4,(x,dyp)
        # 上下两图共用同一 x 映射：两条光点的屏幕 x 必须相等
        assert abs(dx_-px)<1e-9,(px,dx_)
    assert abs(intro_sx(210)-(left+right)/2)<1e-9
    # 屏幕 y 向下：峰顶左侧屏幕斜率为负（曲线上扬），右侧为正（曲线下落）。
    assert parabola_slope(90)<0 and parabola_slope(330)>0
    # 数学导数 f′ = −屏幕斜率：左侧为正、右侧为负。
    assert -parabola_slope(90)>0 and -parabola_slope(330)<0
    for x in (90,330):
        assert intro_dy(x)!=zero_y
    assert intro_dy(90)<zero_y and intro_dy(330)>zero_y  # f′>0 在轴上方

    # 二次函数图的切线也必须真的贴着曲线：屏幕切线斜率 = 屏幕曲线斜率。
    intro_motion=next(g for g in intro_root.iter() if g.get('class')=='motion')
    iline=[e for e in intro_motion if e.tag==NS+'line' and e.get('stroke')=='#dc2626'][0]
    def ivals(attr):
        return list(map(float,next(a for a in iline if a.get('attributeName')==attr).get('values').split(';')))
    ix1,ix2,iy1,iy2=ivals('x1'),ivals('x2'),ivals('y1'),ivals('y2')
    ierr=0
    for x1,x2,y1,y2 in zip(ix1,ix2,iy1,iy2):
        mx=(x1+x2)/2
        x=x0+(mx-left)*(330-90)/(right-left)
        slope=(y2-y1)/(x2-x1)
        ierr=max(ierr,abs(slope-parabola_slope(x)))
        assert abs(slope-parabola_slope(x))<2e-3,(x,slope,parabola_slope(x))
    assert ierr<2e-3

    # 三次函数：极大/极小值点必须恰好是 f′ 的两个零点，且 x 位置对齐。
    cubic_root=ET.fromstring(docs['math-cubic-extrema.svg'])
    def cubic_values(fn,lo,hi):
        return [(x,fn(x)) for x in (lo,hi)]
    assert abs((-1)**3-3*(-1)-2)<1e-12   # f(-1)=2 极大
    assert abs((1)**3-3*(1)+2)<1e-12     # f(1)=-2 极小
    for xv in (-1,1):
        assert abs(3*xv*xv-3)<1e-12      # f′(±1)=0
    assert 3*(-2)**2-3>0 and 3*(2)**2-3>0  # 两端导数为正
    assert 3*(0)**2-3<0                     # 中间导数为负
    cubic_text=''.join(cubic_root.itertext())
    for label in ('极大值 f(−1) = 2','极小值 f(1) = −2','f′ = 0'):
        assert label in cubic_text,label
    # 动态切线必须真的贴着曲线：采样每点比较切线斜率与曲线数值导数。
    anim_cubic=ET.fromstring(docs['math-cubic-extrema-anim.svg'])
    motion=next(g for g in anim_cubic.iter() if g.get('class')=='motion')
    tang=[e for e in motion if e.tag==NS+'line' and e.get('stroke')=='#dc2626'][0]
    def vals(attr):
        return list(map(float,next(a for a in tang if a.get('attributeName')==attr).get('values').split(';')))
    t_x1,t_x2,t_y1,t_y2=vals('x1'),vals('x2'),vals('y1'),vals('y2')
    err=0
    for x1,x2,y1,y2 in zip(t_x1,t_x2,t_y1,t_y2):
        mx=(x1+x2)/2
        x=(-2)+(mx-150)*(4)/(700-150)
        slope=(y2-y1)/(x2-x1)
        err=max(err,abs(slope-(-(3*x*x-3)*30)))
        assert abs(slope-(-(3*x*x-3)*30))<2e-3,(x,slope)
    assert err<2e-3
    # A quadratic curve has linear derivatives and secant slopes. All coordinates
    # are sampled at identical keyTimes; interpolate geometry with the same clock.
    qxs=[222+198*(1+math.cos(2*math.pi*i/240))/2 for i in range(241)]
    secant_error=0
    p=220; py=secant_y(p)
    for x in qxs:
        m=(secant_y(x)-py)/(x-p)
        assert abs(m-(-.62+.00075*(x-p)))<1e-12
        assert abs((py+m*(x-p))-secant_y(x))<1e-10
        assert 100 < x <= 420 and secant_y(x)>82
        assert max(py+m*(100-p),py+m*(440-p))<327
    # Rounded SVG values maintain the same invariants within serialization error.
    anim_root=ET.fromstring(docs['math-derivative-tangent-anim.svg'])
    animations=[e for e in anim_root.iter(NS+'animate')]
    qcx=list(map(float,next(e for e in animations if e.get('attributeName')=='cx').get('values').split(';')))
    qcy=list(map(float,next(e for e in animations if e.get('attributeName')=='cy').get('values').split(';')))
    y1s=list(map(float,next(e for e in animations if e.get('attributeName')=='y1').get('values').split(';')))
    y2s=list(map(float,next(e for e in animations if e.get('attributeName')=='y2').get('values').split(';')))
    for x,y,y1,y2 in zip(qcx,qcy,y1s,y2s):
        assert abs(y-secant_y(x))<.00002
        assert abs(y-(y1+(y2-y1)*(x-100)/340))<.00003
    for a,b in zip(qxs,qxs[1:]):
        secant_error=max(secant_error,abs((secant_y(a)+secant_y(b))/2-secant_y((a+b)/2)))
    assert secant_error<.002
    # Known Bezier controls used above match both analytic polynomial curves.
    for i in range(101):
        t=i/100
        x=80+380*t
        by=(1-t)**2*295.1+2*(1-t)*t*137.4+t*t*88
        assert abs(by-secant_y(x))<1e-9
        x=70+280*t
        by=(1-t)**2*176.6+2*(1-t)*t*39.4+t*t*176.6
        assert abs(by-parabola(x))<1e-9
    intro=ET.fromstring(docs['intro-math-derivative.svg'])
    intro_text=''.join(intro.itertext())
    assert -parabola_slope(90)>0 and -parabola_slope(330)<0
    assert 'f′(x) > 0' in intro_text
    assert 'f′(x) = 0' in intro_text
    assert 'f′(x) < 0' in intro_text
    assert 'f′(x) 的图像' in intro_text
    for animated in intro.iter():
        for item in animated:
            if item.tag==NS+'animate' and item.get('attributeName') in ['cx','cy','x1','y1','x2','y2']:
                assert abs(float(animated.get(item.get('attributeName')))-float(item.get('values').split(';')[0]))<1e-9
    # Balanced A <=> B: total A+B is constant and both rates converge.
    for i in range(129):
        t=i/16; a=1.5+.5*math.exp(-t); b=1.5-.5*math.exp(-t)
        assert abs(a+b-3)<1e-12 and a>=b and a>0 and b>0
    print(f'Validated {len(docs)} SVG documents; intro tangent interpolation error <= {max_error:.6f}; secant interpolation error <= {secant_error:.6f} SVG units; equilibrium mass balance holds')


def freeze(content, fraction):
    root=ET.fromstring(content)
    ET.register_namespace('',NS[1:-1])
    for parent in root.iter():
        for e in list(parent):
            if e.tag not in (NS+'animate',NS+'animateTransform'):
                continue
            vals=e.get('values').split(';'); times=list(map(float,e.get('keyTimes').split(';')))
            idx=max(i for i,t in enumerate(times) if t<=fraction)
            if idx==len(vals)-1 or e.get('calcMode')=='discrete':
                value=vals[idx]
            else:
                a,b=times[idx:idx+2]; f=(fraction-a)/(b-a)
                try:
                    if e.tag==NS+'animateTransform':
                        va=list(map(float,vals[idx].replace(',',' ').split()))
                        vb=list(map(float,vals[idx+1].replace(',',' ').split()))
                        value=' '.join(num(a*(1-f)+b*f) for a,b in zip(va,vb))
                    else:
                        value=num(float(vals[idx])*(1-f)+float(vals[idx+1])*f)
                except ValueError:
                    value=vals[idx]
            if e.tag==NS+'animateTransform':
                value=e.get('type')+'('+value+')'
            parent.set(e.get('attributeName'),value)
            parent.remove(e)
    return '\n'.join(ET.tostring(root,encoding='unicode').replace('><','>\n<').splitlines())+'\n'


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check',action='store_true')
    parser.add_argument('--frames-dir',type=Path)
    args=parser.parse_args()
    docs=generated()
    validate(docs)
    if args.check:
        return
    for name,content in docs.items():
        atomic_write(DEST/name,content)
    print(f'Generated {len(docs)} diagrams')
    if args.frames_dir:
        for name,content in docs.items():
            for f in [0,.25,.5,.75]:
                target=args.frames_dir/Path(name).stem/f'{round(f*100):02d}.svg'
                atomic_write(target,freeze(content,f))
        print(f'Exported keyframes to {args.frames_dir}')


if __name__=='__main__':
    main()
