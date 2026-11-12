"""Build physics illustrations from shared mathematical states (stdlib only).

Run: python -I tools/generate_physics_svgs.py
SVGs remain standalone: SMIL animates geometry; CSS only selects the static
fallback for reduced motion. Layout transforms never share an animation node.
"""
from pathlib import Path
import math
import os
import xml.etree.ElementTree as ET
from html import escape

ROOT = Path(__file__).resolve().parents[1]
DEST = ROOT / 'assets' / 'notes'
TAU = math.tau
SAMPLES = 121
RED, BLUE, GREEN, GOLD, GRAY = '#dc2626', '#2563eb', '#059669', '#d97706', '#475569'
CHECKS = []


def f(v):
    return f'{v:.4f}'.rstrip('0').rstrip('.') if isinstance(v, (float, int)) else str(v)


def attrs(**kw):
    return ' '.join(k.replace('_', '-') + '="' + escape(f(v), quote=True) + '"' for k, v in kw.items() if v is not None)


def tag(name, body='', **kw):
    return f'<{name} {attrs(**kw)}>{body}</{name}>'


def text(x, y, value, color=GRAY, size=12, weight=500, anchor=None):
    return tag('text', escape(value), x=x, y=y, fill=color, font_size=max(12, size), font_weight=weight, text_anchor=anchor)


def line(x1, y1, x2, y2, color=GRAY, width=2, dash=None):
    return tag('line', x1=x1, y1=y1, x2=x2, y2=y2, stroke=color, stroke_width=width, stroke_dasharray=dash)


def path(d, color=BLUE, width=2, fill='none', **kw):
    return tag('path', d=d, stroke=color, stroke_width=width, fill=fill, **kw)


def rect(x, y, w, h, fill='#fff', stroke='#e2e8f0', radius=5):
    return tag('rect', x=x, y=y, width=w, height=h, rx=radius, fill=fill, stroke=stroke)


def circle(x, y, r, fill=RED, stroke=None):
    return tag('circle', cx=x, cy=y, r=r, fill=fill, stroke=stroke)


def poly(points, close=False):
    return 'M ' + ' L '.join(f(x) + ' ' + f(y) for x, y in points) + (' Z' if close else '')


def vector(x, y, dx, dy, color=RED, width=2):
    # A single shaft/head path makes zero vectors truly disappear.
    length = math.hypot(dx, dy)
    if length < 1e-7:
        return 'M ' + f(x) + ' ' + f(y) + ' L ' + f(x) + ' ' + f(y) + ' M ' + f(x) + ' ' + f(y) + ' L ' + f(x) + ' ' + f(y) + ' L ' + f(x) + ' ' + f(y)
    ux, uy = dx / length, dy / length
    h = min(6, length * .3)
    bx, by = x + dx - h * ux, y + dy - h * uy
    return poly([(x, y), (x + dx, y + dy)]) + ' ' + poly([(bx - h * .5 * uy, by + h * .5 * ux), (x + dx, y + dy), (bx + h * .5 * uy, by - h * .5 * ux)])


def arrow(x, y, dx, dy, color=RED, width=2):
    return path(vector(x, y, dx, dy), color, width)


def animate(name, values, duration):
    return tag('animate', attributeName=name, values=';'.join(map(f, values)), dur=f(duration) + 's', repeatCount='indefinite', calcMode='linear')


def shape(name, base, series=None, duration=4):
    base = dict(base)
    body = ''
    if series:
        for key, values in series.items():
            base[key] = values[0]
            body += animate(key.replace('_', '-'), values, duration)
    return tag(name, body, **base)


def seq_shape(name, states, build, animated, duration=4):
    data = [build(s) for s in states]
    if not animated:
        return shape(name, data[0])
    varying = {k: [d[k] for d in data] for k in data[0] if any(d[k] != data[0][k] for d in data[1:])}
    return shape(name, data[0], varying, duration)


def dynamic(states, render, duration=4):
    return '<g class="motion">' + render(states, True, duration) + '</g><g class="still">' + render([states[0]], False, duration) + '</g>'


def sample(fn):
    return [fn(i / (SAMPLES - 1)) for i in range(SAMPLES)]


def wrapped(value, width):
    lines, current, used = [], '', 0.
    for ch in value:
        size = 1.0 if ord(ch)>255 else .56
        if current and used+size>width:
            lines.append(current); current=''; used=0.
        current+=ch; used+=size
    if current: lines.append(current)
    return lines


def document(title, diagram, notes=(), intro=False, footer='', height=None):
    h = height or (260 if intro else 410)
    body = rect(0, 0, 640, h, '#fdfcf7', '#e7d8c4', 12)
    body += text(24, 28, title, '#1e293b', 15, 800)
    body += line(24, 40, 616, 40, '#e7d8c4', 1)
    if notes:
        ny = 55
        body += rect(370, ny, 246, h - ny - 48, '#fff')
        yy = ny + 22
        for value in notes:
            for part in wrapped(value,18):
                body += text(384,yy,part,size=12,weight=600)
                yy += 18
            yy += 5 if intro else 8
    body += diagram
    if footer:
        footer_lines=wrapped(footer,47)
        footer_y=h-12-len(footer_lines)*15
        body += rect(20,footer_y-13,600,len(footer_lines)*15+6,'#eff6ff','#bfdbfe')
        for i,part in enumerate(footer_lines):
            body += text(320,footer_y+i*15,part,'#1e40af',12,600,'middle')
    scale = 1.4
    return ('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 896 ' + f(h * scale) + '" width="100%" height="100%" role="img" aria-labelledby="title desc">\n'
            '<title id="title">' + escape(title) + '</title>\n'
            '<desc id="desc">' + escape(footer or title) + '。动画与静态图使用相同物理模型；减少动态效果时显示静态示意。</desc>\n'
            '<style>text{font-family:"Microsoft YaHei","PingFang SC",sans-serif}.still{display:none} '
            '@media(prefers-reduced-motion:reduce){.motion{display:none}.still{display:inline}}</style>\n<g transform="scale(1.4)">' + body + '</g>\n</svg>\n')


def save(name, content):
    ET.fromstring(content)
    target = DEST / name
    temporary = target.with_suffix('.svg.tmp')
    temporary.write_text(content.replace('><','>\n<'), encoding='utf-8', newline='\n')
    os.replace(temporary, target)


def spring(animated=True):
    A, equilibrium, wall, y = 42., 220., 50., 205.
    omega = TAU / 4
    def state(u):
        phase = TAU * u
        x, v = -A * math.cos(phase), A * omega * math.sin(phase)
        ep, ek = (x / A)**2, (v / (A * omega))**2
        return dict(x=x, v=v, ep=ep, ek=ek)
    states = sample(state)
    for s in states:
        assert abs(s['ep'] + s['ek'] - 1) < 1e-12
    def coils(endpoint):
        pts = [(wall, y - 25), (wall + 10, y - 25)]
        for j in range(19):
            pts.append((wall + 15 + (endpoint - wall - 30) * j / 18, y - 25 + (7 if j % 2 else -7)))
        pts += [(endpoint - 8, y - 25), (endpoint, y - 25)]
        return poly(pts)
    diagram = line(35, y + 1, 345, y + 1, GRAY, 3) + line(wall, y - 85, wall, y + 1, GRAY, 4)
    diagram += line(equilibrium, y - 92, equilibrium, y + 10, '#94a3b8', 1, '4 3')
    diagram += text(equilibrium, y - 100, '质心平衡位置 x = 0', GRAY, 11, anchor='middle')
    diagram += text(60, 265, '水平光滑；弹簧与滑块相连', GRAY, 12)
    diagram += text(60, 287, 'F弹 = −kx；端点 v = 0', RED, 12)
    def render(ss, anim, duration):
        result = seq_shape('path', ss, lambda s: dict(d=coils(equilibrium + s['x'] - 22), fill='none', stroke=BLUE, stroke_width=2.4), anim, duration)
        result += seq_shape('rect', ss, lambda s: dict(x=equilibrium+s['x']-22, y=y-50, width=44, height=50, rx=4, fill='#fef3c7', stroke=GOLD), anim, duration)
        result += seq_shape('circle', ss, lambda s: dict(cx=equilibrium+s['x'], cy=y-25, r=3, fill=RED), anim, duration)
        result += seq_shape('path', ss, lambda s: dict(d=vector(equilibrium+s['x'], y-25, -s['x']*.8, 0), fill='none', stroke=RED, stroke_width=2), anim, duration)
        result += seq_shape('path', ss, lambda s: dict(d=vector(equilibrium+s['x'], y-65, s['v']*.75/omega, 0), fill='none', stroke=BLUE, stroke_width=2), anim, duration)
        for key, by, color in [('ek',110,RED), ('ep',180,BLUE)]:
            result += seq_shape('rect', ss, lambda s, key=key, by=by, color=color: dict(x=390, y=by, width=200*s[key], height=16, fill=color, rx=3), anim, duration)
        return result
    for by, label, color in [(110,'动能 Ek = ½mv²',RED),(180,'弹性势能 Ep = ½kx²',BLUE),(250,'总机械能 E = Ek + Ep',GREEN)]:
        diagram += text(390, by-10, label, color, 12, 700) + rect(390, by, 200, 16, '#f1f5f9')
    diagram += rect(390,250,200,16,GREEN,GREEN)
    diagram += text(390,300,'三条能量柱采用同一比例尺',GRAY,11)
    diagram += dynamic(states,render) if animated else render([states[0]],False,4)
    CHECKS.append(('spring energy and attachment', len(states)))
    return document('弹簧振子 · 位移、速度与能量同步' if animated else '弹簧系统 · 压缩状态与机械能',diagram,footer='同一相位驱动 x、v、F、Ek、Ep；Ek + Ep = E，零能量对应零柱长。')


def pendulum():
    # RK4 solves theta'' = -g/L sin(theta). One quarter orbit is reflected
    # by time reversal symmetry; energy is evaluated from the actual height.
    A, ratio, dt = math.radians(35), 9.8 / 1.2, .0005
    theta, omega, t = A, 0., 0.
    times, angles = [0.], [A]
    while theta > 0:
        def rhs(q,w): return w, -ratio*math.sin(q)
        k1=rhs(theta,omega); k2=rhs(theta+dt*k1[0]/2,omega+dt*k1[1]/2)
        k3=rhs(theta+dt*k2[0]/2,omega+dt*k2[1]/2); k4=rhs(theta+dt*k3[0],omega+dt*k3[1])
        theta += dt*(k1[0]+2*k2[0]+2*k3[0]+k4[0])/6
        omega += dt*(k1[1]+2*k2[1]+2*k3[1]+k4[1])/6
        t += dt; times.append(t); angles.append(theta)
    quarter = times[-2]+(times[-1]-times[-2])*angles[-2]/(angles[-2]-angles[-1])
    from bisect import bisect_right
    def first(q):
        tt=q*quarter; i=min(len(times)-2,max(0,bisect_right(times,tt)-1)); w=(tt-times[i])/dt
        return max(0,angles[i]*(1-w)+angles[i+1]*w)
    def state(u):
        z=min(u*4,4); quadrant=min(int(z),3); frac=z-quadrant
        q=[lambda:first(frac),lambda:-first(1-frac),lambda:-first(frac),lambda:first(1-frac)][quadrant]()
        ep=(1-math.cos(q))/(1-math.cos(A))
        return dict(q=q,x=170+105*math.sin(q),y=55+105*math.cos(q),ep=ep,ek=1-ep)
    states=sample(state)
    assert abs(states[30]['ep'])<1e-12 and abs(states[60]['ek'])<1e-12
    diagram=line(140,55,200,55,GRAY,3)+circle(170,55,3,GRAY)
    arc=[(170+105*math.sin(q),55+105*math.cos(q)) for q in [-A+2*A*j/100 for j in range(101)]]
    diagram+=path(poly(arc),'#94a3b8',1,stroke_dasharray='3 3')+text(170,185,'最低点：Ek 最大，Ep = 0',GRAY,11,anchor='middle')
    for key,by,label,color in [('ek',95,'动能 Ek',RED),('ep',150,'重力势能 Ep',BLUE)]:
        diagram+=text(390,by-8,label,color,12,700)+rect(390,by,200,14,'#f1f5f9')
    def render(ss,anim,dur):
        s=seq_shape('line',ss,lambda q:dict(x1=170,y1=55,x2=q['x'],y2=q['y'],stroke=GRAY,stroke_width=2),anim,dur)
        s+=seq_shape('circle',ss,lambda q:dict(cx=q['x'],cy=q['y'],r=10,fill=RED),anim,dur)
        for key,by,color in [('ek',95,RED),('ep',150,BLUE)]:
            s+=seq_shape('rect',ss,lambda q,key=key,by=by,color=color:dict(x=390,y=by,width=200*q[key],height=14,fill=color,rx=3),anim,dur)
        return s
    diagram+=dynamic(states,render,4*quarter)
    CHECKS.append(('pendulum extrema and energy phase',len(states)))
    return document('机械能 · 单摆与能量实时互换',diagram,intro=True,footer='按单摆方程求角度；Ep = mgL(1 − cosθ)，Ek = E − Ep（以最低点为零势能）。')


def kinematics(newton=False):
    # Dimensionless time 0..1: kinematics v0=1,a=4; Newton v0=0,a=2.
    def state(u):
        progress=u*u if newton else (u+2*u*u)/3
        return dict(u=u,x=48+240*progress,v=u if newton else (1+4*u)/5)
    states=sample(state)
    diagram=line(30,160,345,160,GRAY,3)
    if not newton:
        for i in range(9):
            s=state(i/8); diagram+=circle(s['x']+22,160,2,RED)
        diagram+=text(45,187,'等时打点：相邻点距之差恒定',GRAY,11)
        diagram+=line(405,170,605,170)+line(405,170,405,65)
        diagram+=text(610,175,'t')+text(394,65,'v')
        diagram+=path(poly([(405,150),(585,70)]),RED,2)
        diagram+=text(445,190,'v = v₀ + at',RED,11)
    def render(ss,anim,dur):
        s=seq_shape('rect',ss,lambda q:dict(x=q['x'],y=120,width=44,height=40,rx=4,fill='#fef3c7',stroke=GOLD),anim,dur)
        if newton:
            for dx,dy,c in [(40,0,RED),(-16,0,GOLD),(0,-30,GREEN),(0,30,GRAY)]:
                s+=seq_shape('path',ss,lambda q,dx=dx,dy=dy,c=c:dict(d=vector(q['x']+22,140,dx,dy),stroke=c,fill='none',stroke_width=2),anim,dur)
        else:
            s+=seq_shape('path',ss,lambda q:dict(d=vector(q['x']+22,105,40*q['v'],0),stroke=BLUE,fill='none',stroke_width=2),anim,dur)
            s+=seq_shape('path',ss,lambda q:dict(d=poly([(405,170),(405,150),(405+180*q['u'],150-80*q['u']),(405+180*q['u'],170)],True),fill='#fde68a',fill_opacity=.55,stroke='none'),anim,dur)
            s+=seq_shape('circle',ss,lambda q:dict(cx=405+180*q['u'],cy=150-80*q['u'],r=4,fill=RED),anim,dur)
        return s
    diagram+=dynamic(states,render,3)
    if newton:
        notes=['水平方向：F − f = ma','竖直方向：N = mg','恒定合力 → 恒定加速度','x = ½at²；每轮重新释放']
        diagram+=text(45,187,'F 向右，f 向左；N 与 G 平衡',GRAY,11)
    else: notes=[]
    for q in states:
        if newton:
            assert abs(q['x']-48-240*q['u']**2)<1e-10
            assert abs(q['v']-q['u'])<1e-10
        else:
            assert abs((q['x']-48)/80-(q['u']+2*q['u']**2))<1e-10
            assert abs(q['v']*5-(1+4*q['u']))<1e-10
    CHECKS.append(('constant acceleration trajectory and velocity',len(states)))
    return document('牛顿定律 · 恒定合力与匀加速' if newton else '运动学 · 小车、纸带与 v-t 面积',diagram,notes,intro=True,footer='匀加速：v = v₀ + at；x = v₀t + ½at²。动画循环表示重新开始一次实验。')


def projectile(electric=False):
    # x=v0*t, y=.5*a*t^2, with v arrows from the same derivatives.
    startx,starty,dx,dy=(55,140,270,70) if electric else (55,100,270,150)
    states=sample(lambda u:dict(u=u,x=startx+dx*u,y=starty+dy*u*u,vx=dx,vy=2*dy*u))
    diagram=''
    if electric:
        # Uniform field exists only between plate ends; flight continues linearly outside.
        enter,leave=100,280
        startx,starty=55,135
        def state(u):
            x=55+270*u; inside=max(0,min(x-enter,leave-enter)); after=max(0,x-leave)
            c=.0012; y=135+c*inside*inside+2*c*(leave-enter)*after
            return dict(u=u,x=x,y=y,vx=270,vy=270*2*c*inside)
        states=sample(state)
        diagram+=rect(enter,90,leave-enter,8,'#fee2e2',RED)+rect(enter,220,leave-enter,8,'#dbeafe',BLUE)
        diagram+=text(190,82,'+ + + + +',RED,12,700,'middle')+text(190,245,'− − − − −',BLUE,12,700,'middle')
        for x in [125,160,200,240,265]: diagram+=arrow(x,108,0,85,GOLD,1.2)
        notes=['正电荷，忽略重力与边缘效应','板内：ax = 0，ay = qE/m','vx = v₀，vy = at','y = qUL² / (2mdv₀²)','出板后：无电场力，沿切线匀速','本图粒子不碰板，可正常飞出']
        title='电场偏转 · 板内抛物线，板外直线'
        footer='仅板间存在匀强电场；速度方向与实际轨迹相切，出板后不再继续加速。'
    else:
        diagram+=arrow(45,90,290,0,GRAY,1.5)+arrow(45,90,0,190,GRAY,1.5)
        diagram+=text(335,82,'x')+text(30,280,'y')
        notes=['只受恒定竖直重力，忽略空气阻力','x = v₀t；y = ½gt²','vx = v₀；vy = gt','合速度 v = (vx, vy)','蓝：水平分量；绿：竖直分量','红色速度箭头始终沿轨迹切线','tanθ = vy/v₀ = 2y/x','θ、α分别为速度、位移倾角']
        title='平抛运动 · 轨迹与速度矢量同步'
        footer='质点位置按二次函数采样；vx 保持水平，vy 保持竖直，v = vx + vy。'
    diagram+=path(poly([(q['x'],q['y']) for q in states]),'#94a3b8',1.5,stroke_dasharray='4 3')
    def render(ss,anim,dur):
        s=seq_shape('circle',ss,lambda q:dict(cx=q['x'],cy=q['y'],r=5,fill=RED),anim,dur)
        scale=.12
        for kind,color in [('vx',BLUE),('vy',GREEN),('v',RED)]:
            def geom(q,kind=kind,color=color):
                dx=q['vx']*scale; dy=q['vy']*scale
                # Keep the final arrowheads inside their own diagram panel.
                xx=q['x']+(dx if kind=='vy' else 0)
                return dict(d=vector(xx,q['y'],0 if kind=='vy' else dx,0 if kind=='vx' else dy),fill='none',stroke=color,stroke_width=2)
            s+=seq_shape('path',ss,geom,anim,dur)
        return s
    diagram+=dynamic(states,render,3.5)
    if electric:
        assert max(s['y'] for s in states if s['x']<=280)<215
        for q in states:
            expected_vy=270*2*.0012*max(0,min(q['x']-100,180))
            assert abs(q['vy']-expected_vy)<1e-10
            if q['x']>=280:
                assert abs(q['y']-(135+.0012*180**2+2*.0012*180*(q['x']-280)))<1e-10
    else:
        for q in states:
            assert abs(q['x']-55-270*q['u'])<1e-10
            assert abs(q['y']-100-150*q['u']**2)<1e-10
            assert abs(q['vy']-300*q['u'])<1e-10
    CHECKS.append(('electric flight clearance and derivatives' if electric else 'projectile derivative vectors',len(states)))
    return document(title,diagram,notes,footer=footer)


def slope(animated=False):
    theta=math.pi/6; c,s=math.cos(theta),math.sin(theta)
    origin=(180,205)
    def world(x,y): return origin[0]+c*x+s*y,origin[1]-s*x+c*y
    left,right=world(-145,0),world(145,0)
    diagram=path(poly([left,right,(right[0],left[1])],True),GRAY,2,'#f1f5f9')
    diagram+=text(55,295,'θ = 30°；光滑斜面',GRAY,12)
    center=world(0,-20)
    if animated:
        # Revealing forces never translates or rotates their reference system.
        boxes=[(-24,-40,48,40,'#fef3c7')]
    else:
        boxes=[(-49,-40,48,40,'#fef3c7'),(-1,-40,48,40,'#dbeafe')]
    for x,y,w,h,fill in boxes:
        corners=[world(x,y),world(x+w,y),world(x+w,y+h),world(x,y+h)]
        diagram+=path(poly(corners,True),GOLD,1.6,fill)
    diagram+=circle(*center,3,RED)
    gx,gy=0,60; normal=(-s*60*c,-c*60*c); downhill=(-c*60*s,s*60*s); inward=(s*60*c,c*60*c); push=(c*48,-s*48)
    items=[(gx,gy,RED,'G = mg'),(*normal,GREEN,'N'),(*push,BLUE,'F（沿斜面向上）')]
    force_parts=[]
    for index,(dx,dy,color,label) in enumerate(items):
        elem=arrow(*center,dx,dy,color,2.3)+text(center[0]+dx+5,center[1]+dy,label,color,10.5,700)
        if animated:
            vals=['1' if i/(SAMPLES-1)>=index*.22 else '.08' for i in range(SAMPLES)]
            force_parts.append(tag('g',animate('opacity',vals,8)+elem))
        else: diagram+=elem
    # Component vectors are exactly projections of G, including signs.
    for dx,dy,label in [(*downhill,'mg sinθ'),(*inward,'mg cosθ')]:
        elem=arrow(*center,dx,dy,RED,1.2)+text(center[0]+dx-35,center[1]+dy+12,label,RED,10.5,700)
        if animated: force_parts.append(tag('g',animate('opacity',['1' if i/(SAMPLES-1)>.66 else '.08' for i in range(SAMPLES)],8)+elem))
        else: diagram+=elem
    assert abs(downhill[0]+inward[0])<.03 and abs(downhill[1]+inward[1]-60)<.04
    if animated:
        diagram+='<g class="motion">'+''.join(force_parts)+'</g><g class="still">'
        diagram+=''.join(arrow(*center,dx,dy,color) for dx,dy,color,_ in items)
        diagram+=''.join(arrow(*center,dx,dy,RED,1.2) for dx,dy in [downhill,inward])+'</g>'
    notes=['取 +x 沿斜面向上，+y 垂直向外','Gx = −mg sinθ（沿斜面向下）','Gy = −mg cosθ（压向斜面）','N = mg cosθ','沿斜面：F − mg sinθ = ma']
    if not animated: notes+=['连接体：M = m₁ + m₂','a = [F − Mg sinθ] / M','隔离 m₂：N₁₂ − m₂g sinθ = m₂a']
    else: notes+=['顺序：重力 → 支持力 → 外力','最后作分解，不把分力重复计入']
    CHECKS.append(('slope projection and contact',1))
    return document('斜面受力 · 统一坐标与分力方向',diagram,notes,footer='F 图示向上；重力沿斜面分量向下。接触面无摩擦，分力只用于计算。')


def weight(animated=False):
    # z upward = -A cos(wt): a_up/g = 0.3 cos(wt), N/mg=1+a/g.
    states=sample(lambda u:dict(y=22*math.cos(TAU*u),a=.3*math.cos(TAU*u),n=1+.3*math.cos(TAU*u)))
    diagram=line(70,65,70,295,'#cbd5e1',2,'4 3')+line(300,65,300,295,'#cbd5e1',2,'4 3')
    def render(ss,anim,dur):
        result=seq_shape('rect',ss,lambda q:dict(x=105,y=100+q['y'],width=150,height=145,rx=6,fill='#fff',stroke=GRAY,stroke_width=2),anim,dur)
        result+=seq_shape('rect',ss,lambda q:dict(x=140,y=230+q['y'],width=80,height=10,rx=2,fill='#cbd5e1'),anim,dur)
        result+=seq_shape('circle',ss,lambda q:dict(cx=180,cy=142+q['y'],r=12,fill='#fbbf24'),anim,dur)
        result+=seq_shape('path',ss,lambda q:dict(d=poly([(180,154+q['y']),(180,205+q['y']),(165,230+q['y'])])+' '+poly([(180,205+q['y']),(195,230+q['y'])]),fill='none',stroke=GRAY,stroke_width=3),anim,dur)
        for key,color in [('n',GREEN),('g',RED),('a',BLUE)]:
            def build(q,key=key,color=color):
                x=180 if key!='a' else 280; y=180+q['y']
                dy=-34*q['n'] if key=='n' else 34 if key=='g' else -80*q['a']
                return dict(d=vector(x,y,0,dy),fill='none',stroke=color,stroke_width=2.2)
            result+=seq_shape('path',ss,build,anim,dur)
        result+=seq_shape('rect',ss,lambda q:dict(x=395,y=310,width=140*q['n'],height=12,fill=GREEN,rx=2),anim,dur)
        return result
    diagram+=dynamic(states,render,4) if animated else render([states[0]],False,4)
    diagram+=text(105,320,'红 G = mg；绿 N；蓝 a',GRAY,11)
    notes=['取竖直向上为正方向','N − mg = ma','a 向上：N > mg（超重）','a 向下：N < mg（失重）','a = 0：N = mg','仅与加速度有关，与速度无关','支持力 N（同一比例尺）：']
    diagram+=rect(395,310,196,12,'none','#94a3b8')+line(535,305,535,327,GRAY,1)+text(535,340,'mg',GRAY,12,anchor='middle')
    for q in states:
        assert abs(q['n']-(1+q['a']))<1e-12
        assert q['n']>0
    assert abs(states[30]['n']-1)<1e-12 and abs(states[90]['n']-1)<1e-12
    CHECKS.append(('weight N=m(g+a)',len(states)))
    return document('超重与失重 · 运动和支持力同步',diagram,notes,footer='红绿力箭头同尺度；N = m(g+a)。蓝色 a 由电梯位置的二阶导数给出。')


def galileo(animated=False):
    r=8.; bottom=(155.,235.); rise=125.; run=105.
    theta=math.atan2(rise,run); st,ct=math.sin(theta),math.cos(theta)
    left=(bottom[0]-run,bottom[1]-rise); right=(bottom[0]+run,bottom[1]-rise)
    diagram=path(poly([left,bottom,right]),GRAY,2.5)
    shallow=(340,110); diagram+=path(poly([bottom,shallow]),GRAY,1.5,stroke_dasharray='4 3')
    start=(left[0]+r*st,left[1]-r*ct)
    target=(right[0]-r*st,right[1]-r*ct)
    theta2=math.atan2(125,185); ycontact=start[1]+r*math.cos(theta2)
    xcontact=bottom[0]+(235-ycontact)/math.tan(theta2)
    target2=(xcontact-r*math.sin(theta2),start[1])
    diagram+=line(35,start[1],350,start[1],GOLD,1,'4 3')+text(55,85,'相同球心高度 h',GOLD,11)
    diagram+=circle(*target,r,'#fca5a5',RED)+circle(*target2,r,'#fca5a5',RED)
    diagram+=text(265,145,'倾角越小',GRAY,11)+text(265,162,'上升路程越长',GRAY,11)
    # Constant acceleration on the straight incline: s=.5*a*t^2.
    end=(bottom[0],bottom[1]-r/ct)
    states=sample(lambda u:dict(x=start[0]+(end[0]-start[0])*u*u,y=start[1]+(end[1]-start[1])*u*u,u=u))
    def render(ss,anim,dur):
        result=seq_shape('circle',ss,lambda q:dict(cx=q['x'],cy=q['y'],r=r,fill=RED),anim,dur)
        result+=seq_shape('path',ss,lambda q:dict(d=vector(q['x'],q['y'],24*q['u']*ct,24*q['u']*st),stroke=RED,fill='none',stroke_width=2),anim,dur)
        return result
    diagram+=dynamic(states,render,2.8) if animated else render([states[0]],False,2.8)
    # The horizontal limit is a separate alternative, not a second physical track
    # through the steep ramp. Its ball is tangent to its own horizontal surface.
    diagram+=line(55,300,345,300,BLUE,2)+text(55,280,'独立情景：水平面，无阻力',BLUE,11)
    hs=sample(lambda u:dict(x=65+240*u))
    def horizontal(ss,anim,dur):
        return seq_shape('circle',ss,lambda q:dict(cx=q['x'],cy=292,r=8,fill=BLUE),anim,dur)
    diagram+=dynamic(hs,horizontal,4) if animated else horizontal([hs[0]],False,4)
    # Signed distances from circle centers to the relevant lines must be r.
    for x,y in [start,target]:
        dist=abs((rise if x<155 else -rise)*(x-155)-run*(y-235))/math.hypot(rise,run)
        assert abs(dist-r)<1e-8
    assert abs(target2[1]-start[1])<1e-10
    dist2=abs(125*(target2[0]-155)+185*(target2[1]-235))/math.hypot(125,185)
    assert abs(dist2-r)<1e-8
    for q in states:
        dist=abs(rise*(q['x']-155)-run*(q['y']-235))/math.hypot(rise,run)
        assert abs(dist-r)<1e-8
    CHECKS.append(('Galileo three ball tangencies, equal height and moving contact',len(states)+3))
    notes=['理想条件：无耗散，机械能守恒','右侧两条斜面代表不同实验','比较的是同一小球的球心高度','上升到等高处时速度为零','动画只演示左坡从静止下滑','沿斜面速度逐渐增加','水平面：合力为零，速度恒定','圆球与各自轨道保持相切']
    return document('伽利略斜面 · 等高与水平极限',diagram,notes,footer='动画循环是重新释放，不在谷底停车或瞬间反向；斜面运动与水平匀速分情景展示。')


def induction(intro=False,animated=True):
    cx=150; ringy=130 if intro else 215; base=67 if intro else 125; amp=14 if intro else 24; ry=12; radius=42
    def state(u):
        phase=TAU*u; y=base+amp*math.cos(phase); vy=-amp*math.sin(phase)
        h=ringy-y
        phi=radius**2/(radius**2+h*h)**1.5
        dphi=3*radius**2*h*vy/(radius**2+h*h)**2.5
        return dict(y=y,phi=phi,i=-dphi)
    states=sample(state); imax=max(abs(q['i']) for q in states)
    for q in states: q['current']=q['i']/imax
    assert abs(states[0]['current'])<1e-12 and abs(states[60]['current'])<1e-12
    assert states[30]['current']*states[90]['current']<0
    diagram=tag('ellipse',cx=cx,cy=ringy,rx=radius,ry=ry,fill='none',stroke=GOLD,stroke_width=3)
    diagram+=text(cx,ringy+30,'线圈：固定，闭合，忽略自感',GRAY,10.5,anchor='middle')
    if not intro:
        diagram+=circle(150,300,24,'#fff',GRAY)+line(150,278,150,284,GRAY,1)+text(150,275,'0',GRAY,10,anchor='middle')
        diagram+=text(40,335,'表针示意瞬时 I，不模拟表头惯性',GRAY,10)
    def render(ss,anim,dur):
        result=''
        for dy,color in [(-22,BLUE),(0,RED)]:
            result+=seq_shape('rect',ss,lambda q,dy=dy,color=color:dict(x=cx-12,y=q['y']+dy,width=24,height=22,rx=2,fill=color),anim,dur)
        for dy,label in [(-7,'S'),(16,'N')]:
            result+=seq_shape('text',ss,lambda q,dy=dy,label=label:dict(x=cx,y=q['y']+dy,fill='#fff',font_size=13,text_anchor='middle'),anim,dur).replace('</text>',escape(label)+'</text>')
        # Looking down on the loop: positive clockwise current gives downward B.
        p=(cx+radius/math.sqrt(2),ringy+ry/math.sqrt(2))
        tangent=(-radius/math.sqrt(2),ry/math.sqrt(2)); norm=math.hypot(*tangent)
        result+=seq_shape('path',ss,lambda q:dict(d=vector(*p,tangent[0]/norm*25*q['current'],tangent[1]/norm*25*q['current']),fill='none',stroke=RED,stroke_width=2.5),anim,dur)
        if not intro:
            result+=seq_shape('line',ss,lambda q:dict(x1=150,y1=300,x2=150+18*math.sin(q['current']*.6),y2=300-18*math.cos(q['current']*.6),stroke=RED,stroke_width=2),anim,dur)
        return result
    diagram+=dynamic(states,render,4) if animated else render([states[30]],False,4)
    notes=(['磁铁运动 → 线圈磁通量变化','ε = −N dΦ/dt；I = ε/R','靠近与远离时电流方向相反','折返点速度为零，感应电流为零'] if intro else
           ['线圈法线取向下为正','Φ 由磁偶极子轴线上圆环公式求得','Φ ∝ R² / (R² + h²)^(3/2)','ε = −N dΦ/dt；I = ε/R','俯视：正电流为顺时针','靠近：Φ 增大，感应磁场向上','远离：Φ 减小，感应磁场向下','折返点：dΦ/dt = 0，I = 0'])
    for q in states:
        dt=.00001
        h=ringy-q['y']
        def flux(y): return radius**2/(radius**2+(ringy-y)**2)**1.5
        derivative_y=(flux(q['y']+dt)-flux(q['y']-dt))/(2*dt)
        phase=math.acos(max(-1,min(1,(q['y']-base)/amp)))
        # Magnitude agrees with -dPhi/dy * dy/dt on both halves.
        speed=amp*math.sin(phase)
        assert abs(abs(q['i'])-abs(derivative_y*speed))<1e-10
    CHECKS.append(('induction turnarounds, reversal and flux derivative',len(states)))
    return document('电磁感应 · 磁通变化决定电流',diagram,notes,intro=intro,footer='来拒去留适用于此闭合电阻回路；红色箭头随 I 反向，磁铁固定定位与动画分离。')


def induction_static():
    diagram=''
    for i,(label,detail,color) in enumerate([('1  原磁场','明确原磁场和回路法线方向',BLUE),('2  磁通量','判断穿过回路的磁通量变化',GOLD),('3  感应磁场','增反减同：阻碍变化',RED),('4  感应电流','右手螺旋定则确定电流方向',GREEN)]):
        yy=70+i*60; diagram+=rect(35,yy,310,48,'#fff')+text(50,yy+19,label,color,12,700)+text(50,yy+37,detail,GRAY,11)
    notes=['楞次定律阻碍的是磁通量变化','并非总是阻碍原磁场','ε = −N dΦ/dt','闭合电阻回路：I = ε/R','来拒去留：此类磁体与回路情景','增缩减扩的使用条件：','外磁场改变、回路可形变','并需具体判断磁力的方向']
    return document('楞次定律 · 判断流程与适用条件',diagram,notes,footer='“增缩减扩”不可泛用于所有磁通量变化；固定刚性线圈的面积不会因此改变。')


def two_problems(animated=False):
    diagram=rect(245,130,140,90,'#fef3c7',GOLD)+text(315,165,'共同枢纽',GOLD,14,700,'middle')+text(315,201,'加速度 a',GOLD,22,800,'middle')
    diagram+=rect(35,75,170,60,'#eff6ff','#93c5fd')+text(120,100,'已知受力',BLUE,14,700,'middle')+text(120,121,'求合外力 F合',BLUE,12,anchor='middle')
    diagram+=rect(435,75,170,60,'#f0fdf4','#86efac')+text(520,100,'已知运动',GREEN,14,700,'middle')+text(520,121,'由运动关系求 a',GREEN,12,anchor='middle')
    diagram+=arrow(205,110,42,42,BLUE)+arrow(435,110,-48,42,GREEN)
    diagram+=rect(35,255,170,55,'#f0fdf4','#86efac')+text(120,279,'求未知力',GREEN,14,700,'middle')+text(120,300,'隔离对象，F合 = ma',GREEN,11,anchor='middle')
    diagram+=rect(435,255,170,55,'#eff6ff','#93c5fd')+text(520,279,'求运动状态',BLUE,14,700,'middle')+text(520,300,'结合初始条件求 v、x',BLUE,11,anchor='middle')
    diagram+=arrow(385,205,50,55,BLUE)+arrow(245,205,-40,55,GREEN)
    if animated:
        # Opacity only: the fixed central card cannot lose its positioning.
        highlights=rect(244,129,142,92,'none',GOLD,6)
        diagram+='<g class="motion">'+tag('g',animate('opacity',[.2,1,.2],3)+highlights)+'</g>'
    return document('牛顿力学 · 两类问题的共同枢纽',diagram,footer='受力 → a → 运动；运动 → a → 受力。使用匀加速公式前先核对 a 是否恒定。')


# Electrostatics: field lines integrate Coulomb E; equipotentials solve the
# SAME scalar potential. There are no hand-drawn substitute ellipses.
def field_value(x,y,charges):
    ex=ey=potential=0.
    for q,cx,cy in charges:
        dx,dy=x-cx,y-cy; r=math.hypot(dx,dy)
        if r<1e-9: return 0.,0.,math.copysign(float('inf'),q)
        ex+=q*dx/r**3; ey+=q*dy/r**3; potential+=q/r
    return ex,ey,potential


def integrate(seed,charges,bounds,step=.65):
    def unit(x,y):
        ex,ey,_=field_value(x,y,charges); length=math.hypot(ex,ey)
        return (ex/length,ey/length) if length>1e-14 else (0.,0.)
    x,y=seed; points=[seed]
    for _ in range(7000):
        a=unit(x,y); b=unit(x+step*a[0]/2,y+step*a[1]/2); c=unit(x+step*b[0]/2,y+step*b[1]/2); d=unit(x+step*c[0],y+step*c[1])
        nx=x+step*(a[0]+2*b[0]+2*c[0]+d[0])/6; ny=y+step*(a[1]+2*b[1]+2*c[1]+d[1])/6
        if not(bounds[0]<=nx<=bounds[2] and bounds[1]<=ny<=bounds[3]): break
        if any(math.hypot(nx-cx,ny-cy)<12 for _,cx,cy in charges): break
        if math.hypot(nx-x,ny-y)<step*.1: break
        x,y=nx,ny; points.append((x,y))
    return points


def contour(center,level,charges,count=720):
    pts=[]
    cx,cy=center
    for j in range(count+1):
        angle=TAU*j/count; ca,sa=math.cos(angle),math.sin(angle)
        lo,hi=.1,.1
        while field_value(cx+hi*ca,cy+hi*sa,charges)[2]>level and hi<3000:
            lo=hi; hi+=.5
        if hi>=3000: raise AssertionError('unclosed equipotential')
        for _ in range(34):
            mid=(lo+hi)/2
            if field_value(cx+mid*ca,cy+mid*sa,charges)[2]>level: lo=mid
            else: hi=mid
        r=(lo+hi)/2; point=(cx+r*ca,cy+r*sa)
        assert abs(field_value(*point,charges)[2]-level)<1e-9
        pts.append(point)
    return pts


def electro_plot(charges,bounds,key,levels=True):
    x0,y0,x1,y1=bounds
    content=''
    if levels:
        positives=[(q,x,y) for q,x,y in charges if q>0]
        if len(positives)==1:
            _,cx,cy=positives[0]; sep=abs(charges[1][1]-cx)
            for level in [3/sep,5/sep,9/sep]:
                pts=contour((cx,cy),level,charges)
                content+=path(poly(pts,True),GREEN,1.2,stroke_dasharray='4 3')
                # Equal opposite charges have an exact mirror negative contour.
                mid=(charges[0][1]+charges[1][1])/2
                content+=path(poly([(2*mid-x,y) for x,y in pts],True),GREEN,1.2,stroke_dasharray='4 3')
            content+=line((charges[0][1]+charges[1][1])/2,y0,(charges[0][1]+charges[1][1])/2,y1,GREEN,1.5,'4 3')
        else:
            sep=abs(charges[1][1]-charges[0][1])
            for _,cx,cy in positives:
                for level in [8/sep,12/sep]: content+=path(poly(contour((cx,cy),level,charges),True),GREEN,1.2,stroke_dasharray='4 3')
            mid=((charges[0][1]+charges[1][1])/2,charges[0][2])
            content+=path(poly(contour(mid,2.8/sep,charges),True),GREEN,1.2,stroke_dasharray='4 3')
    for q,cx,cy in charges:
        if q<0: continue
        for j in range(16):
            angle=TAU*j/16; seed=(cx+13*math.cos(angle),cy+13*math.sin(angle))
            pts=integrate(seed,charges,bounds)
            if len(pts)<8: continue
            content+=path(poly(pts),GOLD,1.25)
            index=len(pts)//2; px,py=pts[index]; ex,ey,_=field_value(px,py,charges); norm=math.hypot(ex,ey)
            content+=arrow(px-3*ex/norm,py-3*ey/norm,6*ex/norm,6*ey/norm,GOLD,1.3)
    for q,cx,cy in charges:
        content+=circle(cx,cy,12,'#fee2e2' if q>0 else '#dbeafe',RED if q>0 else BLUE)
        content+=text(cx,cy+5,'+' if q>0 else '−',RED if q>0 else BLUE,17,800,'middle')
    clip='<defs><clipPath id="'+key+'">'+rect(x0,y0,x1-x0,y1-y0,'#fff','none',0)+'</clipPath></defs>'
    return clip+'<g clip-path="url(#'+key+')">'+content+'</g>'


def electric(intro=False,pair=False,isolated=False):
    if isolated:
        diagram=''
        for cx,q in [(170,1),(470,-1)]:
            cy=180
            for r in [35,60,90]: diagram+=tag('circle',cx=cx,cy=cy,r=r,fill='none',stroke=GREEN,stroke_width=1.2,stroke_dasharray='4 3')
            for j in range(12):
                a=TAU*j/12; ca,sa=math.cos(a),math.sin(a)
                diagram+=line(cx+14*ca,cy+14*sa,cx+108*ca,cy+108*sa,GOLD,1.5)
                diagram+=arrow(cx+(65-4*q)*ca,cy+(65-4*q)*sa,q*8*ca,q*8*sa,GOLD,1.5)
            diagram+=circle(cx,cy,13,'#fee2e2' if q>0 else '#dbeafe')+text(cx,cy+5,'+' if q>0 else '−',RED if q>0 else BLUE,18,800,'middle')
            diagram+=text(cx,315,'+Q：向外发散' if q>0 else '−Q：向内汇聚',GRAY,13,700,'middle')
        return document('孤立点电荷 · 场线与等势线',diagram,footer='两侧为独立情景。E = k|Q|/r²；φ = kQ/r；径向电场线与同心等势圆（球面）正交。')
    if pair:
        diagram=electro_plot([(1,95,175),(-1,225,175)],(30,65,310,290),'dipole-pair')
        diagram+=electro_plot([(1,415,175),(1,545,175)],(330,65,610,290),'like-pair')
        diagram+=text(170,60,'等量异种电荷',BLUE,12,700,'middle')+text(470,60,'等量同种正电荷',RED,12,700,'middle')
        diagram+=text(170,310,'中垂线 φ = 0；E 向右',GRAY,11,anchor='middle')+text(470,310,'中点 E = 0；φ > 0',GRAY,11,anchor='middle')
        return document('等量电荷对比 · 库仑场与真实等势线',diagram,footer='橙色为场线，绿色为等势线；异种电荷中点的 E 只在两电荷之间连线上最小。')
    if intro:
        charges=[(1,100,120),(-1,255,120)]; bounds=(25,48,345,190)
        notes=['电场线：从正电荷指向负电荷','沿电场线方向，电势降低','绿色曲线：φ = 常量','E = −∇φ，场线与等势线正交']
    else:
        charges=[(1,110,190),(-1,275,190)]; bounds=(25,65,350,320)
        notes=['绿色虚线由 φ = 常量求根生成','橙色场线按库仑场方程积分','φ = kQ(1/r₊ − 1/r₋)','E = −∇φ','中垂线：φ = 0，E 水平向右','两电荷之间连线上：','中点 E 最小，但 E ≠ 0','等势线与场线在交点正交']
    diagram=electro_plot(charges,bounds,'electric-field')
    CHECKS.append(('Coulomb equipotential root residual < 1e-9',720*3))
    return document('静电场 · 电场线与等势线正交',diagram,notes,intro=intro,footer='E 与 φ 来自同一组点电荷；图中曲线是数值解，不使用椭圆或涟漪替代等势线。')


def verify_field():
    charges=[(1,110,190),(-1,275,190)]
    pts=contour((110,190),5/165,charges)
    errors=[]
    for i in range(1,len(pts)-1):
        x,y=pts[i]; tx=pts[i+1][0]-pts[i-1][0]; ty=pts[i+1][1]-pts[i-1][1]
        ex,ey,_=field_value(x,y,charges)
        cosine=abs(ex*tx+ey*ty)/math.hypot(ex,ey)/math.hypot(tx,ty)
        errors.append(math.degrees(math.asin(min(1,cosine))))
    assert max(errors)<.01, max(errors)
    CHECKS.append(('equipotential/field orthogonality max degrees',max(errors)))


def export_frames(outputs, directory):
    import re
    directory.mkdir(parents=True, exist_ok=True)
    ns = '{http://www.w3.org/2000/svg}'
    ET.register_namespace('', 'http://www.w3.org/2000/svg')
    numeric = re.compile(r'-?\d+(?:\.\d+)?(?:[eE][+-]?\d+)?')
    count = 0
    for name, content in outputs.items():
        for phase in (0, .25, .5, .75):
            root = ET.fromstring(content)
            for parent in root.iter():
                for child in list(parent):
                    if child.tag == ns + 'animate':
                        values = child.attrib['values'].split(';')
                        index = phase * (len(values) - 1)
                        lo = min(int(index), len(values)-1); hi = min(lo+1, len(values)-1)
                        mix = index-lo
                        a, b = values[lo], values[hi]
                        aa, bb = list(numeric.finditer(a)), list(numeric.finditer(b))
                        if len(aa) == len(bb) and numeric.sub('#', a) == numeric.sub('#', b):
                            it = iter(float(x.group())*(1-mix)+float(y.group())*mix for x,y in zip(aa,bb))
                            value = numeric.sub(lambda _: f(next(it)), a)
                        else: value = a
                        parent.set(child.attrib['attributeName'],value)
                        if child.tail:
                            siblings=list(parent); position=siblings.index(child)
                            if position: siblings[position-1].tail=(siblings[position-1].tail or '')+child.tail
                            else: parent.text=(parent.text or '')+child.tail
                        parent.remove(child)
                    elif child.attrib.get('class') == 'still': parent.remove(child)
                if parent.tag == ns+'style': parent.text='text{font-family:"Microsoft YaHei","PingFang SC",sans-serif}'
            out=directory/(Path(name).stem+'-t'+str(int(phase*100))+'.svg')
            out.write_text(ET.tostring(root,encoding='unicode'),encoding='utf-8',newline='\n')
            count += 1
    print('Exported static frames',count,'to',directory)


def verify_text_bounds(root, filename):
    failures=[]
    for node in root.iter():
        if not node.tag.endswith('}text'): continue
        value=''.join(node.itertext()).strip()
        # Animation descendants contain numeric values; only direct visible text counts.
        value=(node.text or '')+''.join(child.tail or '' for child in node)
        size=float(node.attrib.get('font-size',12))
        width=sum(1 if ord(ch)>255 else .56 for ch in value)*size
        x=float(node.attrib.get('x',0)); y=float(node.attrib.get('y',0))
        anchor=node.attrib.get('text-anchor','start')
        left=x-width/2 if anchor=='middle' else x-width if anchor=='end' else x
        right=left+width
        if left<0 or right>640 or y<0 or y>410:
            failures.append((value,round(left,1),round(right,1),y))
    assert not failures,(filename,failures)


def main():
    import argparse
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check', action='store_true', help='Run all physics/XML assertions without writing SVG assets')
    parser.add_argument('--frames-dir', type=Path, help='Export standalone static SVG frames at t=0, 1/4, 1/2, 3/4')
    arguments = parser.parse_args()
    targets={
        'phys-energy-spring.svg':lambda:spring(False),'phys-energy-spring-anim.svg':spring,
        'intro-physics-energy.svg':pendulum,
        'intro-physics-kinematics.svg':kinematics,'intro-physics-newton.svg':lambda:kinematics(True),
        'phys-motion-curve-anim.svg':projectile,'phys-electric-deflect-anim.svg':lambda:projectile(True),
        'phys-newton-slope.svg':slope,'phys-newton-slope-anim.svg':lambda:slope(True),
        'phys-newton-weight.svg':weight,'phys-newton-weight-anim.svg':lambda:weight(True),
        'phys-newton-galileo.svg':galileo,'phys-newton-galileo-anim.svg':lambda:galileo(True),
        'phys-induction-lenz.svg':induction_static,'phys-induction-lenz-anim.svg':induction,
        'intro-physics-induction.svg':lambda:induction(True),
        'phys-newton-two-problems.svg':two_problems,'phys-newton-two-problems-anim.svg':lambda:two_problems(True),
        'phys-electric-field.svg':electric,'phys-electric-dipole-pair.svg':lambda:electric(pair=True),
        'phys-electric-point-charges.svg':lambda:electric(isolated=True),'intro-physics-electric.svg':lambda:electric(True),
    }
    verify_field()
    # Generate and validate everything before replacing any illustration.
    outputs={name:build() for name,build in targets.items()}
    for name,content in outputs.items():
        root=ET.fromstring(content)
        assert root.attrib['viewBox'].startswith('0 0 896 ')
        assert 'prefers-reduced-motion' in content
        verify_text_bounds(root,name)
        for element in root.iter():
            if element.tag.endswith('}animate'):
                values=element.attrib['values'].split(';')
                assert len(values)>=2
        if not arguments.check:
            save(name,content)
    print(('Checked without writing' if arguments.check else 'Generated and XML-validated'),len(outputs),'SVGs')
    if arguments.frames_dir:
        export_frames(outputs,arguments.frames_dir)
    for name,value in CHECKS: print(name+':',value)


if __name__ == '__main__':
    main()
