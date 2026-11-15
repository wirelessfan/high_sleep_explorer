"""为 36 道发现小题生成可重放、无脚本的 SVG 情境图；--check 验证产物。"""
from __future__ import annotations

import argparse
import hashlib
from html import escape
import json
import math
from pathlib import Path
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'web/diagrams/discoveries'
INK, GREEN, BLUE, ORANGE = '#30483f', '#28866b', '#3977ae', '#b96829'


def text(x, y, value, color=INK, size=18, anchor='middle'):
    return f'<text x="{x}" y="{y}" fill="{color}" font-size="{size}" text-anchor="{anchor}">{escape(str(value))}</text>'


def line(x1, y1, x2, y2, color=INK, width=3, dashed=False):
    return f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" stroke="{color}" stroke-width="{width}"'+(' stroke-dasharray="7 6"' if dashed else '')+'/>'


def arrow(x1, y1, x2, y2, color=GREEN):
    return line(x1,y1,x2,y2,color)+f'<path d="M -10 -5 L 0 0 L -10 5" transform="translate({x2} {y2}) rotate({math.degrees(math.atan2(y2-y1,x2-x1))})" fill="none" stroke="{color}" stroke-width="3"/>'


def box(x,y,w,h,label='',fill='#e2f1e9'):
    return f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="12" fill="{fill}" stroke="#a1beb0" stroke-width="2"/>'+ (text(x+w/2,y+h/2+6,label) if label else '')


def circle(x,y,r,color='#e2f1e9',stroke=GREEN):
    return f'<circle cx="{x}" cy="{y}" r="{r}" fill="{color}" stroke="{stroke}" stroke-width="2"/>'


def path(d,color=GREEN,width=3,fill='none'):
    return f'<path d="{d}" fill="{fill}" stroke="{color}" stroke-width="{width}" stroke-linejoin="round"/>'


def beaker(x,y,label,fill='#dceefa',unknown=False):
    liquid=(text(x+45,y+70,'V = ?',BLUE,size=23) if unknown else f'<rect x="{x+3}" y="{y+42}" width="84" height="66" rx="8" fill="{fill}"/>')
    return path(f'M {x} {y} V {y+100} Q {x} {y+112} {x+12} {y+112} H {x+78} Q {x+90} {y+112} {x+90} {y+100} V {y}',BLUE)+liquid+text(x+45,y+145,label,size=16)


def rope_release_diagram():
    return (line(130,65,430,65)+line(280,65,280,84)+circle(280,130,46,'#fff')+
        path('M 230 210 V 130 A 50 50 0 0 1 330 130 V 230',ORANGE,5)+
        box(190,210,80,52,'2 kg')+box(290,230,80,52,'3 kg')+
        arrow(230,210,230,155)+text(207,171,'T',GREEN)+
        arrow(330,230,330,175)+text(351,190,'T',GREEN)+
        arrow(230,262,230,307,ORANGE)+text(184,298,'20 N',ORANGE)+
        arrow(330,282,330,327,ORANGE)+text(373,317,'30 N',ORANGE)+
        arrow(145,254,145,195,BLUE)+text(101,217,'加速度',BLUE,size=16)+text(101,241,'向上',BLUE,size=16)+
        arrow(420,220,420,279,BLUE)+text(486,242,'加速度',BLUE,size=16)+text(486,266,'向下',BLUE,size=16)+
        text(488,112,'同一根轻绳',size=17)+text(488,140,'理想定滑轮',size=17)+
        text(320,349,'张力相等 ≠ 各自受力平衡',size=18))


def diagram(mid, n):
    if mid == 'rope' and n == 1:
        return rope_release_diagram()
    if mid == 'rope':
        return (text(180,80,'实际装置',size=19)+line(110,100,250,100)+line(180,100,180,210,ORANGE,12)+
            box(140,210,80,55,'2 kg')+text(180,298,'绳也有 1 kg 质量',size=17)+
            text(450,80,'只研究绳子',size=19)+box(418,140,64,75,'绳')+
            arrow(450,140,450,100)+text(522,112,'T上 ↑',GREEN)+
            arrow(435,215,435,280,ORANGE)+text(369,267,'自重 10 N',ORANGE,size=16)+
            arrow(470,215,470,250,BLUE)+text(545,235,'T下 = 20 N',BLUE,size=16)+
            text(320,336,'静止：T上 = T下 + 绳的自重',size=20))
    if mid == 'pulley':
        m = 4 if n == 1 else 6
        return (line(100,75,175,75)+path('M 140 75 V 195 A 40 40 0 0 0 220 195 V 95',ORANGE,5)+
            circle(180,195,32,'#fff')+line(180,227,180,250)+box(140,250,80,45,f'{m} kg')+
            arrow(220,110,220,70,BLUE)+text(286,87,'自由端 ↑',BLUE,size=16)+
            text(180,324,'一端固定，另一端自由',size=17)+
            text(455,80,'负载 + 轻滑轮整体',size=18)+box(402,164,106,62,'整体')+
            arrow(420,164,420,105)+text(400,125,'T',GREEN)+arrow(490,164,490,105)+text(514,125,'T',GREEN)+
            arrow(455,226,455,295,ORANGE)+text(520,280,f'mg = {m*10} N',ORANGE,size=16)+
            text(455,323,'a = 0' if n==1 else 'a = 2 m/s² ↑',BLUE,size=19)+
            text(320,350,'滑轮升高 Δh → 两段各缩短 Δh → 自由端上移 2Δh',size=16))
    if mid == 'friction':
        if n == 1:
            return (line(65,265,360,265)+box(150,175,120,90,'2 kg')+
                arrow(150,211,77,211,ORANGE)+text(83,190,'f ?',ORANGE,size=17)+
                arrow(270,211,350,211,BLUE)+text(313,190,'推力 6 N',BLUE,size=16)+
                arrow(210,175,210,105)+text(239,118,'N',GREEN)+
                arrow(210,265,210,316,ORANGE)+text(251,307,'mg',ORANGE)+
                text(480,115,'静摩擦的“本领上限”',size=17)+box(395,140,170,55,'μsN = 10 N')+
                text(480,233,'实际需要：抵住 6 N',BLUE,size=17)+text(480,272,'没滑动 ≠ 没有摩擦',size=17)+
                text(320,349,'先算需要多少，再看上限够不够',size=19))
        return (text(173,85,'只画物块水平方向的受力',size=16)+box(100,130,140,75,'2 kg')+
            box(65,205,230,23,'',fill='#f8e6cd')+arrow(240,165,310,165,ORANGE)+text(282,143,'f →',ORANGE)+
            arrow(115,266,270,266,BLUE)+text(185,297,'板向右加速',BLUE,size=17)+
            text(464,90,'假设不滑：需 f = ma',size=18)+demand_bars(360,125,[(6,'a=3：需 6 N'),(10,'a=5：需 10 N')],8)+
            text(320,346,'摩擦可向右：它阻碍的是相对滑动趋势',size=18))
    if mid == 'system':
        if n == 1:
            return (text(185,83,'先看整体：外力 10 N',size=18)+line(50,250,330,250)+
                box(115,170,75,80,'A 2kg')+box(190,170,105,80,'B 3kg')+
                arrow(45,205,108,205,BLUE)+text(75,181,'10 N',BLUE,size=16)+
                text(185,295,'a = 外力 / 总质量',size=18)+text(475,83,'再隔离 B（只画水平方向）',size=16)+
                box(431,170,95,80,'B 3kg')+arrow(353,210,423,210,ORANGE)+text(388,188,'A推B',ORANGE,size=16)+
                text(478,295,'接触力 = mB a',size=18)+text(320,345,'内力在整体方程中抵消，但并没有消失',size=18))
        return (box(80,218,220,50,'')+text(244,250,'B 3 kg')+box(130,148,120,70,'A 2 kg')+line(50,270,330,270)+
            arrow(253,182,321,182,ORANGE)+text(291,158,'A受 f →',ORANGE,size=16)+
            arrow(302,244,352,244,BLUE)+text(338,222,'F →',BLUE,size=17)+
            arrow(178,246,107,246,ORANGE)+text(141,239,'f ←',ORANGE,size=16)+
            text(181,310,'地面光滑，层间有摩擦',size=16)+
            text(465,85,'先假设共同加速',size=18)+demand_bars(365,125,[(6,'F=15：需 6 N'),(10,'F=25：需 10 N')],8)+
            text(320,349,'超过上限就会滑；共同加速度的假设随之失效',size=17))
    if mid == 'elevator':
        down = n == 1
        return (box(110,102,200,190,'',fill='#edf4fa')+circle(210,153,17,'#f9e3ca',ORANGE)+
            line(210,170,210,225)+line(210,184,184,207)+line(210,184,236,207)+line(210,225,190,260)+line(210,225,230,260)+
            box(165,262,90,16,'')+text(210,123,'50 kg' if down else '60 kg',size=17)+
            arrow(68,236 if down else 144,68,144 if down else 236,BLUE)+text(68,275,'v',BLUE)+
            arrow(345,144 if down else 236,345,236 if down else 144,BLUE)+text(345,275,'a',BLUE)+
            text(490,82,'只研究乘客',size=18)+box(453,165,74,60,'乘客')+
            arrow(490,165,490,105,GREEN)+text(550,125,'N ↑',GREEN)+
            arrow(490,225,490,295,ORANGE)+text(559,281,'mg ↓',ORANGE,size=17)+
            text(210,321,'向上减速' if down else '向下减速',BLUE,size=19)+
            text(320,349,'体重计读的是支持力 N；重力 mg 没有改变',size=18))
    if mid == 'brake':
        xs=lambda t:95+72*t
        ys=lambda v:265-7.8*v
        s=arrow(80,265,558,265,INK)+arrow(95,285,95,75,INK)+text(575,273,'t/s',size=15)+text(140,78,'v/(m/s)',size=15)
        for t in ([0,4,6] if n==1 else [0,1,5]):
            s+=text(xs(t),290,t,size=15)
        if n == 1:
            s+=path(f'M {xs(0)} 265 V {ys(20)} L {xs(4)} 265 Z',GREEN,1,'#d9efe4')
            s+=path(f'M {xs(0)} {ys(20)} L {xs(4)} 265 H {xs(6)}',BLUE,4)
            s+=text(73,ys(20)+5,'20',size=15)+text(220,241,'路程 = 三角形面积',size=17)+text(460,239,'已停住',BLUE,size=17)
            return s+text(320,335,'同一辆车：4 s 停车，随后保持 v = 0',size=18)
        s+=path(f'M {xs(0)} {ys(20)} H {xs(1)} L {xs(5)} 265 L {xs(0)} {ys(10)} Z',GREEN,1,'#d9efe4')
        s+=path(f'M {xs(0)} {ys(20)} H {xs(1)} L {xs(5)} 265',BLUE,4)+path(f'M {xs(0)} {ys(10)} L {xs(5)} 265',ORANGE,4)
        s+=text(70,ys(20)+5,'20',size=15)+text(70,ys(10)+5,'10',size=15)+text(299,103,'后车：先反应 1 s',BLUE,size=17)+text(410,218,'前车：立即刹车',ORANGE,size=17)
        return s+text(320,322,'两曲线间面积 = 后车比前车多走的距离',size=17)+text(320,347,'后车始终更快或一样快：最近时刻在两车停下时',size=16)
    if mid == 'vt':
        oy=190; xs=lambda t:120+100*t; ys=lambda v:oy-25*v
        pts=[(0,4),(2,0),(4,-4)] if n==1 else [(0,-2),(1,0),(3,4)]
        s=arrow(105,oy,555,oy,INK)+arrow(120,305,120,65,INK)+text(576,198,'t/s',size=15)+text(194,72,'v/(m/s)',size=15)
        a,b,c=pts
        for start,end,positive in [(a,b,a[1]>0),(b,c,c[1]>0)]:
            color,fill=(GREEN,'#d9efe4') if positive else (ORANGE,'#fae6d0')
            s+=path(f'M {xs(start[0])} {oy} L {xs(start[0])} {ys(start[1])} L {xs(end[0])} {ys(end[1])} L {xs(end[0])} {oy} Z',color,1,fill)
        for t,v in pts:
            s+=line(xs(t),oy,xs(t),ys(v),INK,1,True)+circle(xs(t),ys(v),4,'#fff',BLUE)+text(xs(t),oy+23,t,size=15)
            if v:s+=text(96,ys(v)+5,v,size=15)
        s+=path('M '+' L '.join(f'{xs(t)} {ys(v)}' for t,v in pts),BLUE,4)
        return s+text(345,90,'轴上 +，轴下 −',size=17)+text(320,333,'位移：带符号相加；路程：面积绝对值相加',size=18)
    if mid == 'log-domain':
        if n == 1:
            return (text(320,104,'y = log₍ₐ₋₁₎(x − 2)',BLUE,size=29)+arrow(260,125,180,170)+arrow(400,125,465,170,ORANGE)+
                box(65,185,230,100,'')+text(180,216,'完整底数是 a − 1',GREEN,size=19)+text(180,252,'a − 1 > 0 且 a − 1 ≠ 1',size=17)+
                box(340,185,230,100,'',fill='#faeddf')+text(455,216,'完整真数是 x − 2',ORANGE,size=19)+text(455,252,'x − 2 > 0',size=19)+
                text(320,335,'像过两道门：底数合法，真数为正',size=19))
        return (text(320,85,'先让两个真数都为正',size=20)+arrow(85,205,560,205,INK)+
            text(190,235,'1',size=17)+text(320,235,'2',size=17)+text(450,235,'3',size=17)+
            line(194,140,550,140,GREEN,5)+circle(190,140,5,'#fff',GREEN)+text(306,120,'x − 1 > 0',GREEN,size=18)+
            line(90,181,446,181,ORANGE,5)+circle(450,181,5,'#fff',ORANGE)+text(306,167,'3 − x > 0',ORANGE,size=18)+
            line(196,205,444,205,BLUE,6)+circle(190,205,6,'#fff',BLUE)+circle(450,205,6,'#fff',BLUE)+
            text(320,280,'交集：1 < x < 3（两端都不含）',BLUE,size=18)+text(320,329,'再看乘积：(x − 1)(3 − x) = 1 − (x − 2)²',size=19))
    if mid == 'log-base':
        ox,oy=120,205; xs=lambda u:ox+88*u; ys=lambda v:oy-45*v
        s=arrow(100,oy,555,oy,INK)+arrow(ox,290,ox,75,INK)+text(573,213,'u',size=17)+text(273,79,'示意：y = logₐ u，0 < a < 1',size=18)
        pts=[(.25+i*.04) for i in range(100)]
        s+=path('M '+' L '.join(f'{xs(u):.2f} {ys(math.log(u,.5)):.2f}' for u in pts),BLUE,4)
        for u,label in [(1,'u₁'),(3,'u₂')]:
            y=ys(math.log(u,.5)); s+=line(xs(u),oy,xs(u),y,INK,1,True)+circle(xs(u),y,5,'#fff',BLUE)+text(xs(u),oy-12,label,size=17)
        s+=text(460,160,'真数变大',BLUE,size=18)+text(460,185,'函数值变小',BLUE,size=18)
        return s+text(320,320,'u 代表整个真数，不直接当作题目的 x',size=18)+text(320,347,'先取真数为正的交集，再按递减关系反向比较',size=17)
    if mid == 'log-change':
        if n == 1:
            return (text(320,88,'把不同底数，翻译成同一种语言',size=20)+text(105,185,'log₆ 4',BLUE,size=27)+arrow(177,176,245,176)+
                text(400,150,'log₂ 4',BLUE,size=29)+line(290,175,515,175)+text(400,215,'log₂ 6',BLUE,size=29)+
                text(400,267,'6 = 2 × 3',ORANGE,size=21)+text(320,328,'分子看 4 = 2²；分母用乘积的对数法则',size=19))
        return (box(60,95,215,65,'2ˣ = 6')+box(365,95,215,65,'3ʸ = 6',fill='#faeddf')+
            arrow(168,169,168,202)+arrow(473,169,473,202,ORANGE)+
            text(168,240,'1/x = log₆ 2',BLUE,size=23)+text(473,240,'1/y = log₆ 3',ORANGE,size=23)+
            path('M 168 261 V 281 H 473 V 261',GREEN)+text(320,327,'同底相加：log₆ 2 + log₆ 3 = log₆(2 × 3)',size=20))
    if mid == 'log-fixed':
        # Curves, axes, asymptote, and fixed point share one mathematical mapping.
        boundary,fx,fy=(2,3,3) if n==1 else (.5,1,-2)
        xs=lambda x:90+100*x
        ys=lambda y:(260-26*y) if n==1 else (150-34*y)
        yzero=ys(0)
        s=arrow(75,yzero,565,yzero,INK)+arrow(90,300,90,112,INK)+text(583,yzero+6,'x',size=17)+text(78,110,'y',size=17)
        s+=line(xs(boundary),125,xs(boundary),300,ORANGE,2,True)+text(xs(boundary),321,'x = 2' if n==1 else 'x = 1/2',ORANGE,size=16)
        for base,color in [(2,BLUE),(4,GREEN),(.5,ORANGE)]:
            points=[]
            for i in range(301):
                x=boundary+.025+i*(4.6-boundary-.025)/300
                y=math.log(x-2,base)+3 if n==1 else math.log(2*x-1,base)-2
                if 125<=ys(y)<=300: points.append((xs(x),ys(y)))
            s+=path('M '+' L '.join(f'{x:.2f} {y:.2f}' for x,y in points),color,3)
        s+=line(xs(fx),yzero,xs(fx),ys(fy),INK,1,True)+line(90,ys(fy),xs(fx),ys(fy),INK,1,True)
        s+=circle(xs(fx),ys(fy),5,INK,INK)+text(xs(fx),yzero+21,fx,size=16)+text(71,ys(fy)+5,fy,size=16)
        if n==1:
            s+=text(xs(fx)+55,ys(fy)+40,f'({fx}, {fy})',size=19)
        else:
            s+=line(xs(fx)+10,ys(fy)+5,410,226,INK,1,True)+text(475,230,f'({fx}, {fy})',size=19)
        s+=text(400,73,'本题函数族',size=17)+text(400,101,'y = logₐ(x − 2) + 3' if n==1 else 'y = logₐ(2x − 1) − 2',size=18)
        return s+text(320,348,'令整个真数 = 1：对数项为 0，剩下的就是定点',size=18)
    if mid == 'trig-sign':
        ox,oy,r=300,195,105
        s=arrow(150,oy,475,oy,INK)+arrow(ox,310,ox,65,INK)+circle(ox,oy,r,'none','#a5bbb1')+text(490,203,'x',size=16)+text(313,66,'y',size=16)
        if n == 1:
            x,y=ox-r*.8,oy-r*.6
            s+=line(ox,oy,x,y,BLUE)+line(x,y,x,oy,ORANGE,2,True)+line(x,y,ox,y,GREEN,2,True)+circle(x,y,5,'#fff',BLUE)
            return s+text(156,113,'第二象限',size=19)+text(166,151,'y = 3/5 > 0',GREEN,size=17)+text(199,222,'x < 0',ORANGE,size=18)+text(320,338,'单位圆：横坐标是 cos，纵坐标是 sin',size=19)
        for deg,color,label,lx,ly in [(35,BLUE,'α（锐角）',470,139),(125,GREEN,'β = π/2 + α',166,89),(215,ORANGE,'γ = π + α',151,283)]:
            a=math.radians(deg); x,y=ox+r*math.cos(a),oy-r*math.sin(a)
            s+=line(ox,oy,round(x,2),round(y,2),color)+circle(round(x,2),round(y,2),5,'#fff',color)+text(lx,ly,label,color,size=17)
        return s+text(470,252,'sinβ > 0',GREEN,size=18)+text(470,283,'cosγ < 0',ORANGE,size=18)+text(320,341,'角度仅作示意；先判符号，再用诱导公式',size=18)
    if mid == 'gas-volume':
        if n == 1:
            return (beaker(120,120,'水：不是气态')+box(375,115,135,125,'',fill='#edf4fa')+
                ''.join(circle(x,y,6,'#dfedf7',BLUE) for x,y in [(400,138),(480,155),(435,181),(405,210),(481,214),(463,133)])+
                text(443,265,'氧气：气态',size=16)+text(320,85,'同样是 22.4 L，能一概而论吗？',size=19)+text(320,320,'22.4 L/mol 的门票：标准状况 + 气体',size=19))
        s=box(75,100,490,175,'',fill='#f4f8fb')
        s+=''.join(circle(155+dx,160,12,'#dfedf7',BLUE) for dx in [-13,13])+text(155,235,'O₂ × 1',BLUE,size=18)
        for x,y in [(285,155),(415,155),(490,220)]:
            s+=''.join(circle(x+dx,y+dy,12,'#e4f0e8',GREEN) for dx,dy in [(-15,6),(0,-12),(15,6)])
        return s+text(355,245,'O₃ × 3',GREEN,size=18)+text(320,84,'相同温压：体积比 = 分子数比',size=20)+text(320,310,'这里只表示 1 : 3 的比例，不是实际只有 4 个分子',size=17)+text(320,341,'一个 O₂ 有 2 个氧原子；一个 O₃ 有 3 个',size=18)
    if mid == 'concentration':
        if n == 1:
            return (beaker(100,130,'100 mL 水')+arrow(215,185,325,185)+beaker(385,130,'溶解后的溶液',unknown=True)+
                text(320,94,'加入 0.1 mol NaCl',size=20)+text(320,327,'加到 100 mL 水里 ≠ 定容至 100 mL',size=20))
        return (beaker(85,100,'NaCl：0.1 mol')+beaker(465,100,'CaCl₂：0.1 mol')+
            text(130,80,'100 mL × 1 mol/L',size=16)+text(510,80,'200 mL × 0.5 mol/L',size=16)+
            arrow(188,180,265,230)+arrow(452,180,375,230)+box(210,242,220,60,'最终溶液 0.3 L')+
            text(320,130,'各贡献多少 Cl⁻？',size=18)+text(320,177,'1 倍 + 2 倍',BLUE,size=23)+text(320,337,'先数离子，再除最终体积；本题已知体积可加',size=18))
    if mid == 'limiting':
        if n == 1:
            return (text(320,88,'配方：2 Al + 6 HCl → 2 AlCl₃ + 3 H₂',size=22)+
                box(70,120,220,105,'')+text(180,157,'Al：0.1 ÷ 2',BLUE,size=22)+text(180,195,'可供 0.05 份反应',size=17)+
                box(350,120,220,105,'',fill='#faeddf')+text(460,157,'HCl：0.2 ÷ 6',ORANGE,size=22)+text(460,195,'只能供约 0.033 份',size=17)+
                line(85,261,285,261,BLUE,14)+line(355,261,488.3,261,ORANGE,14)+text(320,327,'统一成“配方份数”再比；谁先用完，谁限量',size=19))
        return (box(65,100,220,75,'Mg 需 HCl 0.2 mol')+box(355,100,220,75,'Al 需 HCl 0.3 mol',fill='#faeddf')+
            arrow(180,183,270,218)+arrow(460,183,370,218,ORANGE)+text(320,255,'全部反应需 0.5 mol，实际只有 0.4 mol',size=21)+
            text(320,300,'总产氢量：用 2 H⁺ → H₂ 计量',BLUE,size=20)+text(320,341,'知道酸用完，不等于知道哪种金属先用完',size=18))
    if mid == 'ionic':
        if n == 1:
            return (beaker(90,123,'固体保留化学式')+box(110,201,50,28,'',fill='#eee4d4')+text(310,95,'CaCO₃(s) + 2H⁺',BLUE,size=24)+
                arrow(315,125,315,175)+text(420,218,'Ca²⁺ + CO₂↑ + H₂O',size=23)+circle(400,159,8,'none',BLUE)+circle(430,136,6,'none',BLUE)+
                text(415,269,'Cl⁻ 是旁观离子，可约去',size=18)+text(320,332,'核对：两侧净电荷都是 +2；各元素原子数相等',size=18))
        return (text(320,84,'一杯溶液，两本计量账',size=22)+box(50,112,540,85,'')+
            text(320,145,'沉淀线：Ba²⁺ 0.075 mol + SO₄²⁻ 0.1 mol',BLUE,size=19)+text(320,177,'按 1 : 1 配对 → BaSO₄↓',size=18)+
            box(50,217,540,85,'',fill='#faeddf')+text(320,250,'中和线：H⁺ 0.1 mol + OH⁻ 0.15 mol',ORANGE,size=20)+text(320,282,'按 1 : 1 配对 → H₂O，留意剩余 OH⁻',size=18)+text(320,342,'先拆出实际离子量；沉淀与中和分别检查限量',size=18))
    if mid == 'redox':
        if n == 1:
            return (text(320,83,'1 mol Cl₂ = 2 mol Cl 原子（按化合价记账）',size=20)+
                box(65,125,210,100,'')+text(170,161,'1 mol Cl：0 → −1',BLUE,size=20)+text(170,197,'得 1 mol 电子',size=19)+
                box(365,125,210,100,'',fill='#faeddf')+text(470,161,'1 mol Cl：0 → +1',ORANGE,size=20)+text(470,197,'失 1 mol 电子',size=19)+
                arrow(360,255,280,255,ORANGE)+text(320,292,'同一笔转移：不把得与失相加',size=20)+text(320,337,'这是电子守恒账本，不表示微观反应路径',size=18))
        return (box(60,105,220,105,'')+text(170,141,'Fe²⁺ → Fe³⁺ + e⁻',BLUE,size=21)+text(170,183,'每 mol 失 1 mol 电子',size=17)+
            box(360,105,220,105,'',fill='#faeddf')+text(470,141,'Cl₂ + 2e⁻ → 2Cl⁻',ORANGE,size=21)+text(470,183,'每 mol 得 2 mol 电子',size=17)+
            arrow(280,239,360,239,ORANGE)+text(320,284,'0.03 mol Cl₂ 只接收 0.06 mol 电子',size=21)+text(320,335,'电子账配平后，再算 Fe³⁺ 生成量与 Fe²⁺ 剩余量',size=18))
    if mid == 'periodic':
        if n == 1:
            return (circle(170,171,65,'#eef4fa',BLUE)+text(170,165,'X⁺：10 e⁻',BLUE,size=23)+text(170,198,'和 Ne 等电子',size=17)+
                arrow(245,171,335,171)+box(355,118,215,105,'')+text(462,155,'原子比 X⁺ 多 1 e⁻',size=18)+text(462,194,'Z = 10 + 1',BLUE,size=23)+
                text(320,281,'质量数 A = 质子数 Z + 中子数 N',size=21)+text(320,332,'失去电子改变电荷，不改变原子核',size=19))
        s=text(320,85,'前提：四种离子都是 10 个电子',size=21)
        for x,r,label,z in [(110,59,'O²⁻',8),(250,51,'F⁻',9),(390,41,'Na⁺',11),(530,34,'Mg²⁺',12)]:
            s+=circle(x,180,r,'#eef4fa',BLUE)+text(x,187,label,BLUE,size=23)+text(x,267,f'Z = {z}',size=19)
        return s+arrow(110,294,530,294,ORANGE)+text(320,324,'核电荷增大 → 对同数电子吸引增强 → 半径减小',size=17)+text(320,350,'圆的大小只示意趋势，不是等比例的真实半径',size=16)
    raise ValueError(mid)


def demand_bars(x, y, rows, limit):
    """Compare required friction against its ceiling; never label demand as actual force."""
    s=''
    for i,(amount,label) in enumerate(rows):
        cy=y+i*84
        s+=text(x,cy,label,BLUE,size=16,anchor='start')
        s+=line(x,cy+23,x+amount*17,cy+23,BLUE,13)
    s+=line(x+limit*17,y+7,x+limit*17,y+120,ORANGE,2,True)
    return s+text(x+84,y+153,'上限 μsN = 8 N',ORANGE,size=17)


CAPTIONS = {
    'rope-1': '绿色为相同张力T，橙色为20N和30N重力，蓝色为加速度。初速度为零不代表受力平衡。箭头不按比例。',
    'rope-2': '右图只研究绳子：上端力向上，下端拉力与绳自重向下。T下是物体对绳的力。箭头不按比例。',
    'pulley-1': '左图自由端没有固定；右图研究负载与轻滑轮整体，两股张力向上、重力向下。匀速时加速度为零。箭头不按比例。',
    'pulley-2': '两股张力共同提起整体，还要提供向上的加速度；不能把加速装置当成平衡装置。箭头不按比例。',
    'friction-1': '箱子有推力、摩擦力、支持力和重力。10N是静摩擦上限，实际摩擦由静止所需决定。箭头不按比例。',
    'friction-2': '左图仅画物块的水平受力，竖直方向支持力与重力平衡。右图是“不滑所需”的摩擦，上限8N；10N不是实际静摩擦。',
    'system-1': '整体图用外力求共同加速度；右图只画B的水平受力，用B的质量求接触力。竖直方向受力平衡，箭头不按比例。',
    'system-2': '左图强调水平力：A受层间摩擦向右，B受外拉力向右、A的摩擦向左。右图6N、10N均为“不滑假设”下的需求，超过8N假设失效。',
    'elevator-1': '蓝色v向上、a向下；右图只研究乘客，N向上、mg向下。体重计示数是N，失重时mg不变。力的箭头不按比例。',
    'elevator-2': '向下减速意味着a向上。右图乘客受N向上、mg向下；超重是N变大，不是mg变大。箭头不按比例。',
    'brake-1': '速度在4秒降至零，4到6秒保持零；绿色三角形面积是路程。停车后不能延长直线算出“倒着走”。',
    'brake-2': '蓝线为后车，橙线为前车。绿色差面积是接近量；后车全程不慢于前车，故两车都停下时接近量最大。',
    'vt-1': '横轴时间、纵轴速度。绿色轴上面积为正，橙色轴下面积为负；路程把两块面积的绝对值相加。',
    'vt-2': '轴下橙色表示负位移，轴上绿色表示正位移；t=1秒变向。线斜率为正，负速度不表示负加速度。',
    'log-domain-1': '底数是整个a−1，必须大于0且不等于1；真数是整个x−2，必须大于0。两组条件同时成立。',
    'log-domain-2': '两条真数为正的区间取交集，得到1<x<3；空心圆表示不包含端点，再在这个范围内解不等式。',
    'log-base-1': '图中u代表完整真数，画的是递减关系示意，不是题目关于x的函数图。先检查x+1和3−x为正，再反向比较。',
    'log-base-2': '图中u代表完整真数，递减函数把大小关系反向。先检查2x−1和5−x为正，注意最终端点的开闭。',
    'log-change-1': '换底时分子分母必须用同一个底数；6=2×3，把分母拆成log₂2+log₂3。',
    'log-change-2': '先把指数写成对数，再取倒数，统一为以6为底的对数相加。x、y都非零。',
    'log-fixed-1': '图中画的是本题平移后的函数族（示例底数2、4、1/2）。渐近线x=2不属于定义域；交点是(3,3)。',
    'log-fixed-2': '图中画的是本题函数族（示例底数2、4、1/2）。渐近线x=1/2不属于定义域；交点是(1,−2)。',
    'trig-sign-1': '单位圆上的点位于第二象限：纵坐标sinα为正，横坐标cosα为负。先定符号再开平方。',
    'trig-sign-2': '三条射线分别为α、π/2+α、π+α。角度只作示意；后两个角分别在第二、第三象限，乘积应为负。',
    'gas-volume-1': '标准状况还不够，还必须是气体。水不是水蒸气，不能套气体摩尔体积；氧气的分子数与原子数要区分。',
    'gas-volume-2': '蓝色双球是O₂，绿色三球是O₃。图只表达分子数1:3的比例；总物质的量算出后，再按每分子2或3个原子加权。',
    'concentration-1': '左边100mL是水的体积；右边最终溶液体积未知，不能严格把它当100mL。液面不表示确定数值。',
    'concentration-2': '两种输入分别含0.1mol盐，但每个CaCl₂贡献两个Cl⁻。本题明确体积可加，最终体积为0.3L。液面不作定量刻度。',
    'limiting-1': '条形比较的是n除以化学计量系数后的配方份数，不是直接比较原料的mol数。HCl可供的份数更少。',
    'limiting-2': '两种金属全反应共需0.5mol酸，现只有0.4mol。总氢气由酸量决定，金属各自剩余量还缺分配条件。',
    'ionic-1': '烧杯底部示意CaCO₃固体，不能拆成游离离子；反应后有CO₂气体，Cl⁻是旁观离子。粒子图不表示数量比例。',
    'ionic-2': '上面按Ba²⁺与SO₄²⁻的1:1关系算沉淀，下面按H⁺与OH⁻的1:1关系算中和。两条线各自判断限量。',
    'redox-1': '左右按化合价变化记账：1mol氯原子得电子，1mol失电子。得与失是同一笔转移的两端，不能相加；图不是反应机理。',
    'redox-2': 'Fe²⁺每mol失1mol电子，Cl₂每mol得2mol电子；先匹配电子量，再核对铁元素总量与剩余。',
    'periodic-1': 'X⁺有10个电子，所以中性X有11个电子、11个质子。质量数减质子数得到中子数，失电子不改变原子核。',
    'periodic-2': '同为10电子的前提下，Z从8增至12，半径依次减小。圆大小仅示意趋势，不是等比例实测值。',
}


def build(check=False):
    cfg_path=ROOT/'content/exam_training.json'
    cfg=json.loads(cfg_path.read_text(encoding='utf-8'))
    total=0
    for model in cfg['models']:
        for n,q in enumerate(model['questions'],1):
            title=model['title'].split('：')[0]+' · 情境图'
            caption=CAPTIONS[q['id']]
            alt='题目情境示意：'+q['stem']+' '+caption
            svg=(f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 640 360" role="img" aria-labelledby="title desc">'
                f'<title id="title">{escape(title)}</title><desc id="desc">{escape(alt)}</desc>'
                '<rect width="640" height="360" rx="20" fill="#f5faf7"/>'
                '<g font-family="Microsoft YaHei, PingFang SC, Noto Sans CJK SC, sans-serif">'+
                text(30,36,'一起看图找线索',GREEN,size=17,anchor='start')+diagram(model['id'],n)+'</g></svg>\n')
            tree=ET.fromstring(svg)
            assert tree.attrib['viewBox']=='0 0 640 360'
            assert all(e.tag.split('}')[-1] not in {'script','image','foreignObject','animate'} for e in tree.iter())
            target=OUT/(q['id']+'.svg')
            digest=hashlib.sha256(svg.encode('utf-8')).hexdigest()[:12]
            meta={'src':'/diagrams/discoveries/'+target.name+'?v='+digest,'title':title,'alt':alt,
                  'caption':'点图可以放大。'+caption}
            if check:
                assert target.read_text(encoding='utf-8')==svg,target
                assert q.get('diagram')==meta,q['id']
                assert 'target_seconds' not in q,q['id']
            else:
                OUT.mkdir(parents=True,exist_ok=True)
                target.write_text(svg,encoding='utf-8',newline='\n')
                q['diagram']=meta
                q.pop('target_seconds',None)
            total+=1
    if not check: cfg_path.write_text(json.dumps(cfg,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(f'{total} SVG diagrams '+('verified' if check else 'written'))


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check',action='store_true')
    build(parser.parse_args().check)
