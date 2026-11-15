"""为 36 道发现小题生成可重放、无脚本的 SVG 情境图；--check 验证产物。"""
from __future__ import annotations

import argparse
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


def axes(x=110,y=250,w=410,h=160,xlabel='x',ylabel='y'):
    return arrow(x,y,x+w,y,INK)+arrow(x,y+35,x,y-h,INK)+text(x+w+15,y+7,xlabel)+text(x-5,y-h-12,ylabel)+text(x-16,y+22,'O',size=15)


def car(x,y,label,color=BLUE):
    return box(x,y,100,38,'',fill='#e5f0f9' if color==BLUE else '#f9eadb')+path(f'M {x+17} {y} L {x+32} {y-24} H {x+69} L {x+87} {y}',color)+circle(x+24,y+40,9,'#fff',color)+circle(x+78,y+40,9,'#fff',color)+text(x+50,y+80,label,size=17)


def beaker(x,y,label,fill='#dceefa',unknown=False):
    liquid=(text(x+45,y+70,'V = ?',BLUE,size=23) if unknown else f'<rect x="{x+3}" y="{y+42}" width="84" height="66" rx="8" fill="{fill}"/>')
    return path(f'M {x} {y} V {y+100} Q {x} {y+112} {x+12} {y+112} H {x+78} Q {x+90} {y+112} {x+90} {y+100} V {y}',BLUE)+liquid+text(x+45,y+145,label,size=16)


def diagram(mid, n):
    if mid=='rope':
        if n==1:
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
        return (line(240,65,400,65)+path('M 320 65 V 215',ORANGE,12)+
            box(272,215,96,65,'2 kg')+text(445,145,'绳本身有质量：1 kg',size=17)+
            arrow(260,115,260,72)+text(211,104,'T上')+arrow(260,185,260,226)+text(205,211,'T下')+
            text(340,305,'把绳子也当作一个研究对象',size=17))
    if mid=='pulley':
        return (line(140,65,350,65)+path('M 200 65 V 200 A 40 40 0 0 0 280 200 V 94',ORANGE,5)+
            circle(240,200,32,'#fff')+line(240,231,240,255)+box(200,255,80,45,f'{4 if n==1 else 6} kg')+
            arrow(172,192,172,135)+text(151,144,'T')+arrow(308,192,308,135)+text(330,144,'T')+
            arrow(280,100,280,75)+text(420,100,'自由端向上拉',size=17)+
            arrow(390,265,390,212)+text(487,245,'匀速上升' if n==1 else 'a = 2 m/s² ↑',size=18))
    if mid=='friction':
        return (line(90,265,550,265)+box(250,180 if n==1 else 165,130,85,'2 kg')+
            (arrow(130,207,242,207,BLUE)+text(171,181,'推力 6 N',BLUE,size=17)+arrow(375,248,300,248,ORANGE)+text(447,243,'摩擦力？',ORANGE,size=17)+text(320,298,'箱子没有滑动',size=17) if n==1 else
             box(150,250,350,26,'',fill='#f8e6cd')+arrow(410,220,535,220,BLUE)+text(473,193,'板向右加速',BLUE,size=17)+text(320,310,'留意物块和板是否一起运动',size=17)))
    if mid=='system':
        return (line(80,280,560,280)+
            (box(235,190,85,90,'A 2 kg')+box(320,190,120,90,'B 3 kg')+arrow(110,228,228,228,BLUE)+text(166,202,'10 N',BLUE)+
             path('M 220 170 V 145 H 455 V 170',GREEN)+text(337,125,'先看作一个整体',GREEN) if n==1 else
             box(220,230,220,50,'B 3 kg')+box(270,160,120,70,'A 2 kg')+arrow(448,255,550,255,BLUE)+text(505,226,'只拉 B',BLUE)+text(315,125,'层间可能发生相对滑动',size=17)))
    if mid=='elevator':
        return (box(180,70,280,230,'',fill='#f5f8f4')+box(275,258,90,20,'',fill='#d6e6dd')+
            circle(320,145,17,'#f9e3ca',ORANGE)+line(320,163,320,218)+line(320,180,290,200)+line(320,180,350,200)+line(320,218,299,255)+line(320,218,341,255)+
            arrow(130,215 if n==1 else 115,130,115 if n==1 else 215,BLUE)+text(83,170,'v',BLUE)+
            arrow(510,115 if n==1 else 215,510,215 if n==1 else 115,ORANGE)+text(554,170,'a',ORANGE)+
            text(320,105,'50 kg' if n==1 else '60 kg')+text(320,326,'示数看加速度，别只看运动方向',size=17))
    if mid=='brake':
        if n==1:
            return (car(110,175,'正在行驶')+car(430,175,'停下来以后',ORANGE)+line(85,222,555,222)+
                arrow(220,145,350,145,BLUE)+text(282,122,'v₀ = 20 m/s',BLUE)+arrow(350,195,250,195,ORANGE)+text(305,183,'a = −5 m/s²',ORANGE,size=17)+
                text(320,307,'先想想：车会一直减速“倒着走”吗？',size=17))
        return (car(105,165,'后车：20 m/s')+car(435,165,'前车：10 m/s',ORANGE)+line(75,215,565,215)+
            line(215,250,435,250,INK,2,True)+text(325,279,'起初相隔多远才不会碰到？',size=17)+
            text(168,103,'先反应 1 s，再刹车',BLUE,size=17)+text(480,103,'立即刹车',ORANGE,size=17)+
            text(320,320,'两辆车分别分段，再比较相对位置',size=17))
    if mid=='vt':
        # 坐标采用相同的真实映射；函数线、零点和填充区域共用这些坐标。
        origin_y=190
        xs=lambda t:120+100*t
        ys=lambda v:origin_y-25*v
        pts=[(0,4),(2,0),(4,-4)] if n==1 else [(0,-2),(1,0),(3,4)]
        s=arrow(105,origin_y,555,origin_y,INK)+arrow(120,305,120,65,INK)+text(576,198,'t / s',size=15)+text(200,72,'v / (m/s)',size=15)
        for t,v in pts:
            s+=line(xs(t),origin_y,xs(t),ys(v),INK,1,True)+circle(xs(t),ys(v),4,'#fff',BLUE)
            s+=text(xs(t),origin_y+23,t,size=15)
            if v:s+=text(96,ys(v)+5,v,size=15)
        a,b,c=pts
        s+=path(f'M {xs(a[0])} {origin_y} L {xs(a[0])} {ys(a[1])} L {xs(b[0])} {origin_y} Z',GREEN,1,'#d9efe4')
        s+=path(f'M {xs(b[0])} {origin_y} L {xs(c[0])} {ys(c[1])} L {xs(c[0])} {origin_y} Z',ORANGE,1,'#fae6d0')
        s+=path('M '+' L '.join(f'{xs(t)} {ys(v)}' for t,v in pts),BLUE,4)
        return s+text(335,331,'轴上、轴下的面积，分别代表什么？',size=17)
    if mid=='log-domain':
        return (box(75,105,490,90,'',fill='#eef4fa')+text(320,160,'y = log₍ₐ₋₁₎(x − 2)' if n==1 else 'log₂(x − 1) + log₂(3 − x)',BLUE,size=26)+
            line(200,205,200,235,GREEN)+line(440,205,440,235,ORANGE)+
            box(85,235,225,65,'底数：合法的通行证')+box(330,235,225,65,'真数：正数才能进入',fill='#faeddf'))
    if mid=='log-base':
        s=axes(y=240,h=140)
        # y=log_(1/2)(x)，统一原点与单位：x=1 对应 200，y=0 对应 240。
        pts=[(110+90*x,240-30*(math.log(x)/math.log(.5))) for x in [.25+i*.0375 for i in range(101)]]
        s+=path('M '+' L '.join(f'{x:.2f} {y:.2f}' for x,y in pts),BLUE,4)+circle(200,240,4,'#fff',BLUE)+text(200,266,'1',size=15)
        return s+text(395,94,'0 < a < 1',BLUE)+text(402,124,'从左往右看，会怎样？',size=17)+text(320,325,'先看曲线的方向，再比较两个真数',size=17)
    if mid=='log-change':
        return (box(55,125,205,95,'log₂ 3' if n==1 else '2ˣ = 6',fill='#e5f0f9')+box(380,125,205,95,'log₆ 4' if n==1 else '3ʸ = 6',fill='#faeddf')+
            arrow(270,170,368,170)+text(320,140,'搭座桥',size=16)+text(320,268,'不同的底数，也能用同一种语言表达',size=18)+text(320,305,'试着用换底公式连接左右两边',size=17))
    if mid=='log-fixed':
        # 一般函数族 y=log_a(x)，不画本题平移后的答案位置。
        s=axes(y=225,h=135)
        for base,color in [(2,BLUE),(4,GREEN),(.5,ORANGE)]:
            pts=[(110+95*x,225-36*math.log(x,base)) for x in [.25+i*.0375 for i in range(101)]]
            s+=path('M '+' L '.join(f'{x:.2f} {y:.2f}' for x,y in pts),color,3)
        return s+circle(205,225,6,'#fff',INK)+text(205,253,'1',size=15)+text(425,94,'先看 y = logₐ x',size=19)+text(320,327,'底数改变时，哪个点始终不动？',size=17)
    if mid=='trig-sign':
        s=arrow(130,210,510,210,INK)+arrow(320,310,320,65,INK)+circle(320,210,105,'none','#a5bbb1')
        theta=math.radians(143.13 if n==1 else 35)
        x,y=320+105*math.cos(theta),210-105*math.sin(theta)
        s+=line(320,210,round(x,2),round(y,2),BLUE)+circle(round(x,2),round(y,2),5,'#fff',BLUE)
        s+=text(518,218,'x',size=16)+text(333,65,'y',size=16)+text(302,233,'O',size=15)
        return s+text(440,105,'第二象限' if n==1 else 'α 是锐角',size=18)+text(320,341,'先判断正负，再整理恒等式',size=17)
    if mid=='gas-volume':
        if n==1:
            return (beaker(120,120,'水：先看物态')+box(375,115,135,125,'',fill='#edf4fa')+
                ''.join(circle(x,y,6,'#dfedf7',BLUE) for x,y in [(400,138),(480,155),(435,181),(405,210),(481,214),(463,133)])+
                text(443,265,'氧气：气态',size=16)+text(320,92,'同样是 22.4 L，能一概而论吗？',size=19)+text(320,315,'温度、压强、物态，一个也别漏',size=18))
        return (box(85,95,470,190,'',fill='#f4f8fb')+
            ''.join(circle(x+dx,y,12,'#e2eff8',BLUE) for x,y in [(180,155)] for dx in [-13,13])+
            ''.join(circle(x+dx,y+dy,12,'#e4f0e8',GREEN) for x,y in [(300,145),(450,145),(205,230)] for dx,dy in [(-15,6),(0,-12),(15,6)])+
            text(320,320,'每个 O₂ 与每个 O₃，分别带来几个氧原子？',size=17))
    if mid=='concentration':
        return (beaker(100,130,'100 mL 水' if n==1 else '100 mL NaCl 溶液')+arrow(215,185,325,185)+beaker(385,130,'溶解后的溶液' if n==1 else '混合后的溶液',unknown=n==1)+
            text(320,94,'加入 NaCl' if n==1 else '再加入 200 mL CaCl₂ 溶液',size=18)+text(320,321,'浓度里的 V，要找最终溶液的体积',size=18))
    if mid=='limiting':
        return (box(70,100,210,100,'Al + HCl' if n==1 else 'Mg + Al',fill='#e5f0f9')+box(360,100,210,100,'谁先用完？' if n==1 else 'HCl 够不够？',fill='#faeddf')+
            arrow(290,150,350,150)+text(320,248,'把“原料份数”和“配方比例”放在一起看',size=18)+text(320,292,'就像配套餐：少的那一份会限制总量',size=17))
    if mid=='ionic':
        return (beaker(90,135,'CaCO₃ 固体 + 酸' if n==1 else 'NaHSO₄ 溶液')+arrow(212,185,328,185)+beaker(390,135,'反应后的烧杯' if n==1 else '加入 Ba(OH)₂')+
            (box(115,213,38,25,'',fill='#eee4d4')+circle(415,170,6,'none',BLUE)+circle(449,148,8,'none',BLUE) if n==1 else text(320,110,'沉淀与中和，可以分两条线观察',size=18))+
            text(320,323,'保留物态，再检查原子和电荷是否守恒',size=17))
    if mid=='redox':
        if n==1:
            return (box(255,80,130,60,'Cl₂：0 价',fill='#e5f0f9')+
                arrow(255,125,175,195,BLUE)+arrow(385,125,465,195,ORANGE)+
                box(80,210,180,65,'Cl⁻：−1 价',fill='#e5f0f9')+box(380,210,180,65,'ClO⁻：+1 价',fill='#faeddf')+
                arrow(370,240,270,240,ORANGE)+text(320,219,'e⁻',ORANGE,size=22)+
                text(170,302,'得电子',BLUE)+text(470,302,'失电子',ORANGE)+text(320,339,'同一种元素，也能同时扮演两个角色',size=17))
        return (box(75,120,190,105,'Cl₂：0 价' if n==1 else 'Fe²⁺',fill='#e5f0f9')+box(375,120,190,105,'Cl⁻ / ClO⁻' if n==1 else 'Cl₂',fill='#faeddf')+
            arrow(276,170,363,170,ORANGE)+text(320,145,'e⁻',ORANGE,size=22)+text(320,270,'电子从哪里来，又到哪里去？',size=19)+text(320,310,'先标化合价，再把电子的账算平',size=18))
    if mid=='periodic':
        if n==1:
            return (circle(210,190,65,'#eef4fa',BLUE)+text(210,195,'X⁺',BLUE,size=28)+circle(440,190,65,'#eef4fa',BLUE)+text(440,195,'Ne',BLUE,size=28)+
                text(325,90,'“等电子”是一条线索',size=19)+text(325,295,'电子数 → 原子序数 → 中子数',size=19))
        return (''.join(circle(x,175,45,'#eef4fa',BLUE)+text(x,182,label,BLUE,size=23) for x,label in [(110,'O²⁻'),(250,'F⁻'),(390,'Na⁺'),(530,'Mg²⁺')])+
            text(320,95,'四个粒子都有 10 个电子',size=21)+text(320,276,'图中圆圈只是符号，不代表真实半径',size=17)+text(320,310,'谁对外层电子的吸引更强？',size=18))
    raise ValueError(mid)


def build(check=False):
    cfg_path=ROOT/'content/exam_training.json'
    cfg=json.loads(cfg_path.read_text(encoding='utf-8'))
    total=0
    for model in cfg['models']:
        for n,q in enumerate(model['questions'],1):
            title=model['title'].split('：')[0]+' · 情境图'
            alt='题目情境示意：'+q['stem']
            if q['id']=='rope-1':
                alt+=' 图中同时标出两物体向上的相同张力T、向下的20N和30N重力，以及释放后的加速度方向：2kg向上、3kg向下。张力相等不代表各自受力平衡。'
            svg=(f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 640 360" role="img" aria-labelledby="title desc">'
                f'<title id="title">{escape(title)}</title><desc id="desc">{escape(alt)}</desc>'
                '<rect width="640" height="360" rx="20" fill="#f5faf7"/>'
                '<g font-family="Microsoft YaHei, PingFang SC, Noto Sans CJK SC, sans-serif">'+
                text(30,36,'一起看图找线索',GREEN,size=17,anchor='start')+diagram(model['id'],n)+'</g></svg>\n')
            tree=ET.fromstring(svg)
            assert tree.attrib['viewBox']=='0 0 640 360'
            assert all(e.tag.split('}')[-1] not in {'script','image','foreignObject','animate'} for e in tree.iter())
            target=OUT/(q['id']+'.svg')
            meta={'src':'/diagrams/discoveries/'+target.name+('?v=2' if q['id']=='rope-1' else ''),'title':title,'alt':alt,
                  'caption':('点图可以放大。绿色为绳的张力，橙色为物体重力，蓝色为释放后的加速度方向。“由静止释放”只是初速度为零，不代表保持静止。箭头示意不按比例。' if q['id']=='rope-1' else
                             '点图可以放大。示意图不按比例；观察图中的线索，再以题干条件为准。')}
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
