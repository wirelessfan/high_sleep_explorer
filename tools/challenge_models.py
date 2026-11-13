"""中文挑战题模型。公开教材模型的独立改编；数值、设问、干扰项均重新设计。

build_challenge_bank.py 使用这些模型生成固定变式，答案与验证参数只留在离线报告。
"""
from math import sqrt, log, exp


def f(x):
    if isinstance(x, str):
        return x
    return f"{x:.6g}"


def pack(*values):
    return "；".join(f(v) for v in values)


def q(model, skill, stem, correct, wrong, explain, demands, difficulty=6, evidence=None):
    opts = [correct, *wrong]
    assert len(opts) == 4 and len(set(opts)) == 4, (model, opts)
    assert len(demands) >= 3
    return dict(model=model, skill=skill, stem=stem, options=opts, answer=0,
                explain=explain, demands=demands, difficulty=difficulty,
                evidence=evidence or {})


def kinematics(i, n):
    if i == 0:
        v=12+2*n; a=2; d=v*v/4+10+2*n; reaction=.5
        gap=d-v*reaction-v*v/(2*a)
        return q('braking-clearance','反应距离与制动临界',
          f'汽车以 {v} m/s 匀速行驶，发现前方 {f(d)} m 处的静止障碍。反应时间为 0.50 s，随后以 2 m/s² 匀减速至停，不计车长。司机不改变反应时间，为避免碰撞所需的制动加速度大小至少为多少？若仍按原方案制动，车头距障碍的最终间距为多少？（依次作答，保留三位有效数字。）',
          pack(f'{f(v*v/(2*(d-v*reaction)))} m/s²',f'{f(gap)} m'),
          [pack('2 m/s²',f'{f(d-v*v/4)} m'),pack(f'{f(v*v/(2*d))} m/s²',f'{f(gap)} m'),pack(f'{f(v*v/(d-v*reaction))} m/s²',f'{f(-gap)} m')],
          f'反应阶段走 {f(v*reaction)} m，可供制动的距离为 {f(d-v*reaction)} m。临界条件 v²=2a临(d−vτ)，故 a临={f(v*v/(2*(d-v*reaction)))} m/s²。原方案间距 d−vτ−v²/4={f(gap)} m。不能把反应距离算入制动距离。',
          ['拆分反应与制动','从不等式反求临界加速度','比较实际与临界方案'],evidence={'v':v,'d':d,'tau':reaction,'a':a})
    if i == 1:
        u=6+n; a=2; t=3+n/2; d=u*t-a*t*t/2
        # d positive and discr nonnegative; choose t before u/a
        d=u*u/(2*a)+4+n
        near=d-u*u/(2*a)
        return q('pursuit-minimum','追及与最近距离',
          f'同一直线上 A 在 B 后方 {f(d)} m。t=0 起 A 从静止以 2 m/s² 加速，B 以 {u} m/s 匀速同向行驶，均视为质点。A 追上 B 前，两者的最大间距及追上所需时间依次约为多少？',
          pack(f'{f(d+u*u/4)} m',f'{f((u+sqrt(u*u+4*d))/2)} s'),
          [pack(f'{f(d)} m',f'{f(sqrt(d))} s'),pack(f'{f(d+u*u/4)} m',f'{f(u/2)} s'),pack(f'{f(near)} m',f'{f((u+sqrt(u*u+4*d))/2)} s')],
          f'间距 D=d+ut−t²，D′=u−2t，t={f(u/2)} s 时取最大 {f(d+u*u/4)} m；追上需解 t²−ut−d=0，取正根 {f((u+sqrt(u*u+4*d))/2)} s。速度相同对应间距最大，并非追上。',
          ['建立相对位移函数','用相对速度定位极值','筛选追及方程正根'],evidence={'u':u,'d':d})
    if i == 2:
        a=2+n*.2; t=2+n*.2; u=3+n
        x=u*t+a*t*t/2; T=t+2; v=u+a*t; total=x+v*(T-t)
        return q('two-stage-inverse','分段图像反演',
          f'某质点先做加速度恒定的直线运动，随后匀速。已知初速 {u} m/s，前 {f(t)} s 位移 {f(x)} m，此后又运动 2 s，总计时段内速度始终为正。前段加速度及全程平均速度依次约为多少？',
          pack(f'{f(a)} m/s²',f'{f(total/T)} m/s'),
          [pack(f'{f(2*x/t**2)} m/s²',f'{f(total/T)} m/s'),pack(f'{f(a)} m/s²',f'{f((u+v)/2)} m/s'),pack(f'{f(a/2)} m/s²',f'{f(total/T/2)} m/s')],
          f'由 x=u t+at²/2 反求 a={f(a)} m/s²，转段速度 {f(v)} m/s。后段位移为 2v={f(2*v)} m，总位移 {f(total)} m 除以总时间 {f(T)} s 得 {f(total/T)} m/s；两段时间不同不能平均两段平均速度。',
          ['从位移反演加速度','拼接连续速度','以总路程和总时间求均速'],evidence={'u':u,'t':t,'a':a,'x':x})
    if i == 3:
        h=20+5*n; u=10+n; T=sqrt(2*h/10); x=u*T; angle=10*T/u
        return q('projectile-window','平抛落点与通行窗口',
          f'小球从高 {h} m 的平台水平抛出，目标带位于地面且距平台正下方 {f(x*.9)}～{f(x*1.1)} m。g=10 m/s²，不计阻力。要落在目标带内，水平初速的允许范围及以 {u} m/s 抛出时落地速度与水平夹角的正切依次约为多少？',
          pack(f'[{f(.9*u)}, {f(1.1*u)}] m/s',f'{f(angle)}'),
          [pack(f'[{f(.9*x)}, {f(1.1*x)}] m/s',f'{f(angle)}'),pack(f'[{f(.9*u)}, {f(1.1*u)}] m/s',f'{f(angle/2)}'),pack(f'[{f(.45*u)}, {f(.55*u)}] m/s',f'{f(1/angle)}')],
          f'竖直自由落体给 t=√(2h/g)={f(T)} s；两端水平距离除以 t，得初速区间。落地 vy=gt={f(10*T)} m/s，所以 tanθ=vy/vx={f(angle)}。位移方向的正切恰为其一半，不能混用。',
          ['分解平抛运动','由落点窗口反求速率区间','区分速度与位移方向'],evidence={'h':h,'u':u,'T':T})
    if i == 4:
        u=20+2*n; delay=1+n*.1; a=4; stop=u/a
        D=u*delay+u*u/(2*a)
        return q('delayed-braking','双车延迟刹车的安全距离',
          f'前车以 {u} m/s 行驶，在 t=0 以 4 m/s² 刹车直至停。后车同速，在 {f(delay)} s 后才以 2 m/s² 刹车直至停。两车始终在同一车道，不计车长。为不碰撞，初始车距至少应为多少？取临界允许最终恰好接触；后车停车时前车已停止。',
          f'{f(D)} m',[f'{f(u*delay)} m',f'{f(u*delay+u*u/4)} m',f'{f(u*u/8)} m'],
          f'前车停车距离 u²/8={f(u*u/8)} m，后车为 uτ+u²/4={f(u*delay+u*u/4)} m。后车速度始终不小于前车（直到两者都停），追近距离单调增加，故最大追近量就是两停车距离之差={f(D)} m。必须先证明最近状态确在最终，不能只盲目减停车距离。',
          ['分段比较两车速度','确定最危险时刻','计算相对位移临界值'],7,evidence={'u':u,'tau':delay})
    if i == 5:
        T=3+n*.2; s=5*T*T; u=2*T
        return q('vertical-meeting','竖直相遇与有效时间域',
          f'A 球从距地 {f(s)} m 高处静止释放；同一瞬间 B 球从地面以 {f(u)} m/s 竖直向上抛出。g=10 m/s²，均为质点，B 回地面即停止，A 到地面亦停止。下列结论正确的是？',
          '两球空中不能相遇；B 回地面时 A 仍在空中',
          ['两球一定在空中相遇，因相对加速度为零','两球在 B 达到最高点时相遇','B 回地面前 A 已落地'],
          f'若无地面限制，相对距离 s−ut，形式相遇时间 s/u={f(s/u)} s；B 的滞空时间 2u/g={f(u/5)} s，而 A 落地时间 √(2s/g)={f(T)} s。实际有 2u/g < T < s/u，因此形式解越过有效运动区间，空中不相遇。',
          ['建立相对运动','求两球有效运动区间','排除越界代数解'],7,evidence={'h':s,'u':u})
    if i == 6:
        dt=.1; a=2+n; first=.3+n*.02; second=first+a*dt*dt
        v=(first+second)/(2*dt)
        return q('tape-inference','纸带测量与系统误差',
          f'纸带上相邻两个连续等时区间的位移为 {f(first)} m 和 {f(second)} m，真实每段时长 0.10 s，质点匀加速。求共同端点的瞬时速度与加速度。若计时设备把每段时长误记为 0.11 s，算得的加速度是真值的多少倍？（依次作答。）',
          pack(f'{f(v)} m/s',f'{f(a)} m/s²',f'{f(100/121)} 倍'),
          [pack(f'{f(first/.1)} m/s',f'{f(a)} m/s²',f'{f(10/11)} 倍'),pack(f'{f(v)} m/s',f'{f(a)} m/s²','1.21 倍'),pack(f'{f(v/2)} m/s',f'{f(a/2)} m/s²',f'{f(100/121)} 倍')],
          f'共同端点是总时段中点，v=(s₁+s₂)/(2Δt)={f(v)} m/s；相邻差 s₂−s₁=aΔt² 得 a={a} m/s²。误用时长后的 a测/a真=(0.10/0.11)²=100/121。时间误差对加速度是平方效应。',
          ['中时刻速度识别','差分求加速度','传播时标系统误差'],evidence={'s1':first,'s2':second,'dt':dt})
    u=8+n; a=2; L=u*u/4+5
    return q('reversal-distance','反向运动与路程',
      f'质点从原点以 {u} m/s 向右出发，始终受向左的恒加速度 2 m/s²，运动至坐标 x=−{f(L)} m 时结束。求总时间及总路程，不能将经过原点视为结束。',
      pack(f'{f((u+sqrt(u*u+4*L))/2)} s',f'{f(L+u*u/2)} m'),
      [pack(f'{f((u+sqrt(u*u+4*L))/2)} s',f'{f(L)} m'),pack(f'{f(sqrt(L))} s',f'{f(L+u*u/2)} m'),pack(f'{f(u/2)} s',f'{f(u*u/4)} m')],
      f'位移方程 −L=ut−t²，取正根得时间 {f((u+sqrt(u*u+4*L))/2)} s。先右行到最右端 u²/4={f(u*u/4)} m，再左行该距离加 L，故路程 L+u²/2={f(L+u*u/2)} m。',
      ['筛选位移方程时间根','定位反向时刻','分段累计路程'],evidence={'u':u,'L':L})


def newton(i,n):
    m=1+n*.25; M=2+n*.5; mu=.2; g=10
    if i==0:
        F=(M+m)*3; t=2+n*.1; aA=2; aB=(F-2*m)/M; slip=.5*(aB-aA)*t*t
        return q('block-board-slip','板块滑动与最小板长',
          f'小块质量 {f(m)} kg，长板质量 {f(M)} kg，地面光滑。两者静止，小块初始位置距板左端有一段余量，块板动摩擦因数 0.20，最大静摩擦等于滑动摩擦，g=10 m/s²。向右拉板的恒力为 {f(F)} N，持续 {f(t)} s。为使块在此期间不从板的左端滑落，该余量至少多少？块与板加速度依次为多少？忽略块尺寸，允许末时刻恰到边缘。',
          pack(f'{f(slip)} m','2 m/s²',f'{f(aB)} m/s²'),
          [pack(f'{f(.5*aB*t*t)} m','2 m/s²',f'{f(aB)} m/s²'),pack('0 m','3 m/s²','3 m/s²'),pack(f'{f(2*slip)} m','2 m/s²',f'{f(aB)} m/s²')],
          f'若共速需 a=F/(M+m)=3>μg=2，不成立。滑动时小块 a₁=2，板 a₂=(F−μmg)/M={f(aB)} m/s²。块相对板向左，所需余量为 (a₂−a₁)t²/2={f(slip)} m。题目中的“左端”指初始参考端，余量由相对位移确定。',
          ['先验证无滑动假设','整体与隔离切换','用相对位移求边界'],7,evidence={'m':m,'M':M,'F':F,'t':t})
    if i==1:
        # pulling block at angle, 3-4-5 triangle
        F=5*m; N=10*m-.6*F; a=(.8*F-.2*N)/m
        return q('oblique-pull','斜拉与接触约束',
          f'质量 {f(m)} kg 的物块沿水平地面向右滑动，动摩擦因数 0.20。以大小 {f(F)} N、斜向右上方的恒力拉它，拉力方向 sinθ=0.60、cosθ=0.80，g=10 m/s²。求此时加速度，以及保持相同拉力方向时使支持力刚好为零的拉力大小。',
          pack(f'{f(a)} m/s²',f'{f(10*m/.6)} N'),
          [pack(f'{f((F-.2*10*m)/m)} m/s²',f'{f(10*m)} N'),pack(f'{f(a)} m/s²',f'{f(10*m/.8)} N'),pack(f'{f((.8*F-.2*10*m)/m)} m/s²',f'{f(10*m/.6)} N')],
          f'竖直平衡 N=mg−Fsinθ={f(N)} N，摩擦为 μN，不是 μmg。水平方向 ma=Fcosθ−μN，得 a={f(a)} m/s²。接触临界 N=0，F临=mg/sinθ={f(10*m/.6)} N；更大拉力时需改用离地模型。',
          ['分解斜拉力','将支持力代入摩擦','识别模型失效边界'],evidence={'m':m,'F':F,'a':a})
    if i==2:
        mb=2*m; a=(mb*10-m*5-.2*m*10*.8)/(mb+m); T=mb*(10-a)
        return q('incline-connection','粗糙斜面连接体',
          f'质量 {f(m)} kg 的 A 在固定斜面上，sinθ=0.60、cosθ=0.80，动摩擦因数 0.25；A 由轻绳跨理想定滑轮连接悬挂的 B，B 质量为 {f(mb)} kg。释放后 B 下行，g=10 m/s²。求加速度与绳张力，并判断把 B 质量逐渐减小时维持 A 向上匀速所需的 B 质量。',
          pack('4 m/s²',f'{f(12*m)} N',f'{f(.8*m)} kg'),
          [pack('6 m/s²',f'{f(8*m)} N',f'{f(.6*m)} kg'),pack('4 m/s²',f'{f(20*m)} N',f'{f(.8*m)} kg'),pack('4 m/s²',f'{f(12*m)} N',f'{f(.4*m)} kg')],
          f'A 向上时阻力为 mg(sinθ+μcosθ)=8m N。整体方程 20m−8m=3ma 得 a=4 m/s²；隔离 B，T=2m(10−4)=12m N。匀速临界由 m_Bg=8m 得 m_B=0.8m；不能在 A 向上时把摩擦也画向上。',
          ['判断摩擦方向','连接体联立求张力','反推匀速质量阈值'],evidence={'m':m})
    if i==3:
        a=2+n*.2; mass=50+5*n; T=3; dy=.5*a*T*T; work=mass*(10+a)*dy
        return q('elevator-inverse','电梯读数反演与功',
          f'质量 {mass} kg 的人站在电梯地板上，从静止开始 3 s 内体重计恒示 {f(mass*(10+a))} N，且电梯上升。g=10 m/s²。求这 3 s 上升高度与地板支持力对人做的功；随后若电梯以同样加速度大小减速上升，体重计示数是多少？',
          pack(f'{f(dy)} m',f'{f(work)} J',f'{f(mass*(10-a))} N'),
          [pack(f'{f(dy)} m',f'{f(mass*10*dy)} J',f'{f(mass*(10+a))} N'),pack(f'{f(2*dy)} m',f'{f(work)} J',f'{f(mass*(10-a))} N'),pack(f'{f(dy)} m',f'{f(mass*a*dy)} J',f'{f(mass*(10-a))} N')],
          f'N−mg=ma，a={f(a)} m/s²。高度 at²/2={f(dy)} m，支持力功 N h={f(work)} J，不能混为合力功。减速上升时加速度向下，N′=m(g−a)={f(mass*(10-a))} N。',
          ['由视重反求加速度','联合运动学与功','区分速度方向和加速度方向'],evidence={'m':mass,'a':a})
    if i==4:
        ma=m; mb=2*m; k=100; x=mb*10/k; aa=30
        return q('spring-cut','弹簧瞬时与后续运动辨析',
          f'质量 {f(ma)} kg 的 A 由上方细绳悬挂，A 下方用劲度系数 100 N/m 的轻弹簧悬挂质量 {f(mb)} kg 的 B，静止时剪断上方细绳。g=10 m/s²。求剪断瞬间 A、B 加速度（向下为正），以及弹簧初始伸长量。下列哪组正确？',
          pack('30 m/s²','0 m/s²',f'{f(x)} m'),
          [pack('10 m/s²','10 m/s²',f'{f(x)} m'),pack('30 m/s²','10 m/s²',f'{f(x)} m'),pack('−10 m/s²','0 m/s²',f'{f(x/2)} m')],
          f'剪断瞬间弹簧形变不变，弹力仍为 m_Bg=20m N；A 的合力为 30m N，所以 a_A=30，B 仍受平衡力，a_B=0。胡克定律 x=m_Bg/k={f(x)} m。上述加速度只在瞬间成立，不能把它们当成整个下落过程的恒定值。',
          ['用静力平衡确定初始弹力','冻结形变后分别隔离','限定瞬时结论的适用域'],evidence={'m':m,'k':100})
    if i==5:
        v=4+n; acc=2; L=v*v/4+2; time=v/2+2/v; heat=.5*m*v*v
        return q('belt-time-heat','传送带转段与相对热量',
          f'水平传送带以 {v} m/s 匀速向右运动，长度 {f(L)} m。质量 {f(m)} kg 的小块从静止轻放左端，μ=0.20，g=10 m/s²。求到达右端时间与整个滑动过程的摩擦生热；共速后带速不变。',
          pack(f'{f(time)} s',f'{f(heat)} J'),
          [pack(f'{f(L/v)} s',f'{f(heat)} J'),pack(f'{f(time)} s',f'{f(2*heat)} J'),pack(f'{f(v/2)} s','0 J')],
          f'加速至带速所需 t₁=v/(μg)={f(v/2)} s，块位移 x₁=v²/(2μg)={f(v*v/4)} m，余下 2 m 匀速。相对滑程 vt₁−x₁=x₁，Q=μmgx₁=mv²/2={f(heat)} J，不等于电机对传送带做的总功。',
          ['判定是否提前共速','拼接运动时间','按相对位移求耗散'],7,evidence={'m':m,'v':v,'L':L})
    if i==6:
        F=(m+M)*2; fneed=m*2; limit=.3*10*(m+M)
        return q('stack-static-bound','叠放体静摩擦与拉力区间',
          f'质量 {f(m)} kg 的 A 叠在质量 {f(M)} kg 的 B 上，B 所在地面光滑，A、B 最大静摩擦力为 0.30m_Ag。仅向右拉 B，g=10 m/s²。拉力为 {f(F)} N 时 A 受何方向、多大摩擦力？若要求 A 不相对 B 滑动，拉力最大多少？',
          pack(f'向右 {f(fneed)} N',f'{f(limit)} N'),
          [pack(f'向左 {f(fneed)} N',f'{f(limit)} N'),pack(f'向右 {f(.3*m*10)} N',f'{f(.3*m*10)} N'),pack('无摩擦力',f'{f(limit)} N')],
          f'整体 a=F/(M+m)=2，小块靠向右静摩擦获得加速度，f=ma={f(fneed)} N，小于上限。临界 a=3，故 Fmax=3(M+m)={f(limit)} N。最大静摩擦只在临界取满，平时按所需加速度调节。',
          ['整体求加速度','隔离确定静摩擦','求无滑动外力边界'],evidence={'m':m,'M':M,'F':F})
    R=1+n*.2; v=sqrt(5*10*R); Tb=6*m*10
    return q('vertical-circle-bound','绳模型向心力与能量',
          f'质量 {f(m)} kg 的小球由长 {f(R)} m 的轻绳系住，在竖直面内运动，不计阻力。若恰能完成整周，最低点所需最小速度和该处张力依次是多少？g=10 m/s²。',
          pack(f'{f(v)} m/s',f'{f(Tb)} N'),
          [pack(f'{f(sqrt(10*R))} m/s',f'{f(2*m*10)} N'),pack(f'{f(sqrt(4*10*R))} m/s',f'{f(5*m*10)} N'),pack(f'{f(v)} m/s',f'{f(5*m*10)} N')],
          f'绳不能推，最高点临界 T顶=0，v顶²=gR；由最低到最高上升2R，能量守恒给 v底²=v顶²+4gR=5gR。最低点 T底−mg=mv底²/R，故 T底=6mg={f(Tb)} N。',
          ['识别绳的单向约束','上下端能量联立','正确写最低点向心方程'],evidence={'m':m,'R':R})


def energy(i,n):
    m=1+n*.2; g=10
    if i==0:
        h=4+n; L=5+n; mu=.2; v=sqrt(2*g*(h-mu*L)); stop=h/mu
        return q('rough-track-budget','多段轨道能量预算',
          f'质量 {f(m)} kg 的物块从高 {h} m 处静止滑下光滑轨道，进入长 {L} m、μ=0.20 的水平粗糙段，再进入光滑上坡。g=10 m/s²，各段平滑连接。求刚过粗糙段速度、上坡最高高度（以水平段为零），以及恰使物块到达粗糙段末端的最大粗糙段长度。',
          pack(f'{f(v)} m/s',f'{f(h-.2*L)} m',f'{f(stop)} m'),
          [pack(f'{f(sqrt(2*g*h))} m/s',f'{h} m',f'{f(stop)} m'),pack(f'{f(v)} m/s',f'{f(h-.2*L)} m',f'{f(h*.2)} m'),pack(f'{f(v)} m/s',f'{f(.2*L)} m',f'{f(stop)} m')],
          f'粗糙段后动能 mg(h−μL)>0，速度 √[2g(h−μL)]={f(v)} m/s；后续光滑上坡把它转为势能，h′=h−μL={f(h-.2*L)} m。临界长度 L临=h/μ={f(stop)} m。',
          ['列多段能量收支','验证穿越条件','由临界反求路径长度'],evidence={'m':m,'h':h,'L':L,'mu':.2})
    if i==1:
        k=200; x=.2+n*.02; W=.5*k*x*x; d=2+n*.1; mu=.1; v=sqrt(2*(W-mu*m*10*d)/m)
        return q('spring-loss','弹簧释放与粗糙段临界',
          f'质量 {f(m)} kg 的物块在光滑水平区被劲度系数 200 N/m 的弹簧压缩 {f(x)} m，释放后离开恢复原长的弹簧，再进入长 {f(d)} m、μ=0.10 的粗糙区。g=10 m/s²。求离开粗糙区的速率及恰能穿越该区的最小弹簧压缩量。',
          pack(f'{f(v)} m/s',f'{f(sqrt(2*.1*m*10*d/k))} m'),
          [pack(f'{f(sqrt(k*x*x/m))} m/s',f'{f(sqrt(2*.1*m*10*d/k))} m'),pack(f'{f(v)} m/s',f'{f(.1*m*10*d/k)} m'),pack('不能穿越','压缩量越小越容易穿越')],
          f'弹性势能 {f(W)} J，粗糙段消耗 μmgd={f(mu*m*10*d)} J，仍有正动能，v={f(v)} m/s。临界 ½kx临²=μmgd，x临={f(sqrt(2*mu*m*10*d/k))} m。不能漏掉弹性势能的1/2。',
          ['计算弹性势能','扣除路径耗散并检验符号','反求临界初始形变'],evidence={'m':m,'k':k,'x':x,'d':d,'mu':mu})
    if i==2:
        P=600+100*n; resist=20+2*n; v=P/resist; acc=(P/(v/2)-resist)/m
        return q('constant-power','恒功率变加速与终速',
          f'质量 {f(m)} kg 的小车在水平路上以恒功率 {P} W 牵引，阻力恒为 {resist} N，讨论速度已大于零的阶段。求最终稳定速度，以及速度为稳定速度一半时的加速度；此阶段小车的加速度如何变化？',
          pack(f'{f(v)} m/s',f'{f(acc)} m/s²','随速度增大而减小'),
          [pack(f'{f(v)} m/s',f'{f(acc/2)} m/s²','保持恒定'),pack(f'{f(v/2)} m/s',f'{f(acc)} m/s²','随速度增大而增大'),pack(f'{f(v)} m/s','0 m/s²','一直为零')],
          f'牵引力 F=P/v，ma=P/v−f。终速由 F=f 得 vmax=P/f={f(v)} m/s；在 vmax/2 时牵引力为2f，a=f/m={f(acc)} m/s²。随速率上升，P/v下降，加速度递减；不能套匀加速公式。',
          ['联立功率与牛顿定律','比较瞬态与稳态','识别非匀加速模型'],evidence={'m':m,'P':P,'resist':resist})
    if i==3:
        M=3*m; u=8+n; vf=u/4; loss=.5*m*u*u-.5*(m+M)*vf*vf; h=vf*vf/20
        return q('inelastic-pendulum','碰撞与上升分阶段守恒',
          f'质量 {f(m)} kg 的弹丸以 {u} m/s 水平射入质量 {f(M)} kg 的静止悬挂木块并留在其中。碰撞极短，随后整体无损上升。g=10 m/s²。求上升高度及碰撞中损失的机械能。',
          pack(f'{f(h)} m',f'{f(loss)} J'),
          [pack(f'{f(u*u/20)} m','0 J'),pack(f'{f(h)} m',f'{f(.5*(m+M)*vf*vf)} J'),pack(f'{f(2*h)} m',f'{f(loss)} J')],
          f'碰撞阶段水平方向动量守恒，v=mu/(m+M)=u/4={f(vf)} m/s，机械能不守恒，损失 {f(loss)} J。碰撞后上升阶段机械能守恒，h=v²/(2g)={f(h)} m。不能跨越碰撞全程使用机械能守恒。',
          ['划分冲击与上升阶段','选择不同守恒量','核算不可逆损失'],7,evidence={'m':m,'M':M,'u':u})
    if i==4:
        F=8+n; d=3+n*.2; mu=.2; cost=mu*m*10*d; work=F*d; v=sqrt(2*(work-cost)/m)
        return q('work-angle-budget','斜向力功与法向约束',
          f'质量 {f(m)} kg 的物块沿水平面从静止向右移动 {f(d)} m，水平向右拉力大小随位移按 F(x)={F}+2x（N，x以m计）变化，动摩擦因数 0.20，g=10 m/s²。求末速度及此过程平均拉力；可将 F-x 图像面积看作做功。',
          pack(f'{f(sqrt(2*((F*d+d*d)-cost)/m))} m/s',f'{f(F+d)} N'),
          [pack(f'{f(sqrt(2*((F*d+d*d)-cost)/m))} m/s',f'{f(F+2*d)} N'),pack(f'{f(sqrt(2*(F*d+d*d)/m))} m/s',f'{f(F+d)} N'),pack(f'{f(v)} m/s',f'{F} N')],
          f'拉力功等于梯形面积 W=[F(0)+F(d)]d/2={f(F*d+d*d)} J，平均拉力 W/d={f(F+d)} N。摩擦功 −μmgd={f(-cost)} J，动能定理给 v={f(sqrt(2*(F*d+d*d-cost)/m))} m/s。不能用末拉力乘全程位移。',
          ['从变力图像求功','区分平均力与末力','将耗散纳入动能定理'],evidence={'m':m,'F0':F,'d':d})
    if i==5:
        R=1+n*.2; mu=.2; L=2+n*.2; h=2.5*R+mu*L
        return q('loop-release-height','粗糙入口与圆轨道临界',
          f'小滑块自高度 h 静止下滑，先经长 {f(L)} m、μ=0.20 的水平粗糙段，再进入半径 {f(R)} m 的光滑竖直圆轨道内侧。除水平段外无摩擦，不计尺寸，g=10 m/s²。要不脱轨完成整周，h 的最小值及此时圆轨道最低点支持力与重力之比为多少？',
          pack(f'{f(h)} m','6'),
          [pack(f'{f(2*R+.2*L)} m','5'),pack(f'{f(2.5*R)} m','6'),pack(f'{f(h)} m','5')],
          f'最高点 N=0 给 v顶²=gR。入口最低点须有动能 ½m(5gR)，加上粗糙损耗 μmgL，得到 hmin=2.5R+μL={f(h)} m。最低点 N−mg=m·5gR/R，所以 N/(mg)=6。',
          ['判最高点单侧接触临界','跨多过程列能量','复核最低点约束力'],7,evidence={'R':R,'L':L,'mu':mu})
    if i==6:
        h=10+n; flow=2+n*.2; eta=.8; P=flow*10*h*eta; v=2; kinetic=flow*v*v/2
        return q('hydro-efficiency','流水功率与效率边界',
          f'微型水电装置每秒通过 {f(flow)} kg 水，进水口比出水口高 {h} m，入水速度可忽略，出水速度 2 m/s。g=10 m/s²。装置把水流损失的机械能以 80% 效率变为电能。求电功率；若误把全部重力势能变化作为可转换机械能，将高估多少瓦？',
          pack(f'{f(.8*(flow*10*h-kinetic))} W',f'{f(.8*kinetic)} W'),
          [pack(f'{f(P)} W','0 W'),pack(f'{f(flow*10*h-kinetic)} W',f'{f(kinetic)} W'),pack(f'{f(.8*(flow*10*h-kinetic))} W',f'{f(kinetic)} W')],
          f'单位时间损失的机械能为 ṁgh−½ṁv出²={f(flow*10*h-kinetic)} W；乘0.8得电功率 {f(.8*(flow*10*h-kinetic))} W。忽略出水动能会高估0.8×½ṁv出²={f(.8*kinetic)} W。效率要作用于实际可转移能量。',
          ['把连续流量转为单位时间能量','保留出水动能','在正确能量基数上应用效率'],evidence={'flow':flow,'h':h,'v':2,'eta':.8})
    k=100; x=.2+n*.02; mu=.2; d=k*x*x/(2*mu*m*10)
    return q('spring-return','往返摩擦与最终停止',
          f'质量 {f(m)} kg 的物块从水平粗糙轨道上某点以初速 v 向右运动，前方是一段光滑区，光滑区末端固定劲度系数100 N/m的弹簧。物块到达光滑区时恰具有把弹簧压缩 {f(x)} m 的动能。弹簧将其反弹后，物块回到粗糙区继续向左，μ=0.20、g=10 m/s²。求它自重返粗糙区边界起到停止的距离；如果去程粗糙段长2 m，求最初动能。',
          pack(f'{f(d)} m',f'{f(.5*k*x*x+.2*m*10*2)} J'),
          [pack(f'{f(d/2)} m',f'{f(.5*k*x*x+.2*m*10*2)} J'),pack(f'{f(d)} m',f'{f(.5*k*x*x)} J'),pack(f'{f(2*d)} m',f'{f(k*x*x+.2*m*10*2)} J')],
          f'光滑压缩与反弹无损，返程边界动能仍为 ½kx²={f(.5*k*x*x)} J，停距 d=½kx²/(μmg)={f(d)} m。最初动能还需补上去程摩擦损失 μmg·2，故为 {f(.5*k*x*x+.2*m*10*2)} J。',
          ['分清有损与无损区','处理往返能量','从末状态反推初始能量'],evidence={'m':m,'k':k,'x':x,'mu':mu})


def electric(i,n):
    if i==0:
        U=100+20*n; d=.02; L=.04; V=1e6; y=U*L*L/(4*V*d); D=.06; screen=y+U*L*D/(2*V*d)
        return q('electric-deflection','加速偏转与屏幕位移',
          f'带正电粒子从静止经 {f(V)} V 电压加速后，沿中线水平进入平行板，板长0.04 m、板距0.02 m、板间电压 {U} V；离板后再水平前进0.06 m到荧光屏。不计重力和边缘场。求粒子离板偏移量与屏上偏移量的大小，保留三位有效数字。',
          pack(f'{f(y)} m',f'{f(screen)} m'),
          [pack(f'{f(2*y)} m',f'{f(2*screen)} m'),pack(f'{f(y)} m',f'{f(y)} m'),pack(f'{f(y)} m',f'{f(screen-y)} m')],
          f'先由 qV=½mv₀²，偏转区 ay=qU/(md)、t=L/v₀。离板 y=½ayt²=UL²/(4Vd)={f(y)} m；出板斜率 vy/v₀=UL/(2Vd)，漂移再增 UL D/(2Vd)，屏偏移={f(screen)} m。最大偏移在离板时仍小于半板距，未撞板。',
          ['消去未知荷质比','联合加速和类平抛','拼接出板后的匀速漂移'],7,evidence={'U':U,'V':V,'L':L,'d':d,'D':D})
    if i==1:
        C=2+n; U=12; ratio=2; Q=C*U; energy=C*U*U/2
        return q('capacitor-isolated','断电电容器与外力功',
          f'真空平行板电容器电容 {C} μF，充至12 V后断开电源。保持两板面积不变，将板距缓慢增至原来的2倍，忽略边缘效应和漏电。求最后电压、场强与原场强之比、外力做功。',
          pack('24 V','1',f'{f(energy)} μJ'),
          [pack('12 V','0.5',f'{f(-energy/2)} μJ'),pack('24 V','2',f'{f(energy)} μJ'),pack('6 V','0.5',f'{f(-energy/2)} μJ')],
          f'断电后Q不变，C′=C/2，U′=Q/C′=24 V。E′=U′/(2d)=E，场强不变。储能 Q²/(2C)翻倍，外力正功等于储能增量，W=½CU²={f(energy)} μJ；此时没有电源做功。',
          ['选择电荷守恒约束','联合几何电容与场强','区分外力功和电源功'],evidence={'C':C,'U':U})
    if i==2:
        C=2+n; U=10; old=.5*C*U*U; new=old/2
        return q('capacitor-connected','恒压电容器能量账',
          f'电容 {C} μF 的平行板电容器始终接在10 V理想电源上。缓慢把板距增至两倍，忽略损失。求电容器储能变化 ΔE、此过程中电源对电容器做功 W源、外力做功 W外（按该顺序，正表示能量输入电容器）。',
          pack(f'{f(-new)} μJ',f'{f(-2*new)} μJ',f'{f(new)} μJ'),
          [pack(f'{f(new)} μJ','0 μJ',f'{f(new)} μJ'),pack(f'{f(-new)} μJ',f'{f(-new)} μJ','0 μJ'),pack(f'{f(-new)} μJ',f'{f(2*new)} μJ',f'{f(-3*new)} μJ')],
          f'C减半、U不变，ΔE=−¼CU²={f(-new)} μJ；ΔQ=−CU/2，电源功UΔQ=−CU²/2={f(-2*new)} μJ。由ΔE=W源+W外，外力功为 {f(new)} μJ，电源吸收能量多于储能减少量。',
          ['恒压下计算电荷转移','求电源能量交换','用完整能量账反求机械功'],7,evidence={'C':C,'U':U})
    if i==3:
        r=1+n*.2
        return q('point-charge-zero','零场点与零势点的区别',
          f'真空中x轴上固定电荷 +Q 位于x=0，−4Q位于x={f(r)} m，取无穷远电势为零。沿x轴所有有限零电势点的坐标和唯一零电场点坐标依次为多少？Q>0。',
          pack(f'零势 x=−{f(r/3)} m、{f(r/5)} m',f'零场 x=−{f(r)} m'),
          [pack(f'零势 x={f(r/3)} m',f'零场 x={f(r/3)} m'),pack(f'零势 x=−{f(r)} m',f'零场 x={f(r/5)} m'),pack(f'零势 x=−{f(r/3)} m、{f(r/5)} m',f'零场 x={f(r/3)} m')],
          f'零势解 1/|x|=4/|x−L|，分区得x=−L/3、L/5。异号电荷间场方向相同不可能抵消；只在小电荷外侧，令1/x²=4/(L−x)²且x<0，得x=−L。零势与零场分别是标量和矢量条件。',
          ['按区间处理绝对值','区分势与场的叠加','排除方向不符的代数根'],7,evidence={'L':r})
    if i==4:
        U=80+10*n; qv=2e-6; mass=1e-5; E=1000; v=sqrt(2*qv*U/mass); x=U/E
        return q('electric-turning','电场减速转向与电势能',
          f'质量1.0×10⁻⁵ kg、正电荷2.0×10⁻⁶ C的粒子，从静止经 {U} V电压加速后，逆着1000 V/m的匀强电场射入足够长区域，不计重力。求入场速度、转向距离，以及从入场到转向电势能变化。',
          pack(f'{f(v)} m/s',f'{f(x)} m',f'+{f(qv*U)} J'),
          [pack(f'{f(v)} m/s',f'{f(2*x)} m',f'−{f(qv*U)} J'),pack(f'{f(v/sqrt(2))} m/s',f'{f(x)} m',f'+{f(qv*U)} J'),pack(f'{f(v)} m/s',f'{f(x)} m','0 J')],
          f'加速qU=½mv²得v={f(v)} m/s。逆场运动受到反向力，qEx=qU，x=U/E={f(x)} m。场力做负功，电势能增加qU={f(qv*U)} J；速度瞬间为零但电场力不为零，随后反向。',
          ['电势差转化初动能','由功反求转向点','判断电势能符号与后续运动'],evidence={'U':U,'q':qv,'m':mass,'E':E})
    if i==5:
        qv=1e-6*(n+1); L=.2; m=.002; k=9e9; v=sqrt(k*qv*qv/(2*m*L))
        return q('charge-release','双粒子释放与相对距离',
          f'两个质量均为0.002 kg、带电量均为 +{f(qv)} C 的质点，初始相距0.20 m，由静止释放，只受相互库仑力，k=9.0×10⁹ N·m²/C²。相距0.40 m时每个质点的速率及其中一个质点所受库仑力与初始力之比是多少？',
          pack(f'{f(v)} m/s','1/4'),
          [pack(f'{f(sqrt(2)*v)} m/s','1/4'),pack(f'{f(v)} m/s','1/2'),pack(f'{f(v/2)} m/s','1/4')],
          f'对称性与动量守恒给二者速率相等。电势能减少 kq²(1/L−1/(2L))=kq²/(2L)，总动能为mv²，故v=√[kq²/(2mL)]。代入为 {f(v)} m/s。库仑力按距离平方反比减为1/4。',
          ['由对称确定动能分配','用电势能差代替恒力功','平方反比比较末力'],evidence={'q':qv,'L':L,'m':m})
    if i==6:
        C=2+n; U=10; C2=2*C; uf=U/3; loss=.5*C*U*U-.5*3*C*uf*uf
        return q('capacitor-sharing','电容器并联共享与能量损耗',
          f'电容为 {C} μF 的电容器充至10 V后断电，与未带电、容量为 {2*C} μF 的电容器按同极性并联，连接导线有很小电阻，最终稳定。求最终电压和总电场能损失；不把导线电阻设成严格零。',
          pack(f'{f(uf)} V',f'{f(loss)} μJ'),
          [pack('5 V','0 μJ'),pack(f'{f(uf)} V','0 μJ'),pack(f'{f(2*U/3)} V',f'{f(loss/2)} μJ')],
          f'总电荷CU守恒，并联后总电容3C，U末=U/3={f(uf)} V。初能½CU²，末能½·3C(U/3)²=初能/3，损失={f(loss)} μJ，通过暂态电流耗散，不能同时假设电场能守恒。',
          ['电荷守恒与等势条件','比较两状态总储能','解释暂态耗散的去向'],7,evidence={'C':C,'U':U})
    U=100+20*n; d=.02; L=.1; V=2000; ymax=U*L*L/(4*V*d); crit=2*V*d*d/(L*L)
    return q('plate-collision-bound','偏转板碰撞边界',
          f'带电粒子从静止经2000 V加速，沿中线水平进入长0.10 m、间距0.020 m的平行偏转板，偏转电压 {U} V。忽略重力边缘场。求不撞板允许的偏转电压上限，并判断当前粒子能否从板末端飞出（触板即算撞）。',
          pack(f'必须小于 {f(crit)} V','能够飞出' if U<crit else '会撞板'),
          [pack(f'必须小于 {f(2*crit)} V','能够飞出'),pack(f'必须小于 {f(crit/2)} V','会撞板'),pack(f'必须小于 {f(crit)} V','会撞板' if U<crit else '能够飞出')],
          f'y末=UL²/(4V加d)，必须严格小于d/2，因此U<2V加d²/L²={f(crit)} V。当前若按未撞板轨迹算末偏移为{f(ymax)} m，与半板距0.010 m比较；若超限，公式预测的末位置仅用于判断，实际早已触板。',
          ['消去荷质比建立偏移','把几何约束转成电压界','区分临界等号与严格通行'],evidence={'U':U,'d':d,'L':L,'V':V})


def induction(i,n):
    B=.5; L=.4; R=2; m=.1
    if i==0:
        v=4+n; F=B*B*L*L*v/R; P=F*v; I=B*L*v/R
        return q('rod-steady-power','导体棒终速与能量',
          f'水平光滑平行导轨间距0.40 m，垂直导轨向里的匀强磁场B=0.50 T，回路总电阻2.0 Ω，棒电阻忽略。以水平恒力拉棒，达到 {v} m/s 稳定速度。求该拉力、焦耳热功率；若只把总电阻加倍而拉力不变，新终速为多少？忽略自感与空气阻力。',
          pack(f'{f(F)} N',f'{f(P)} W',f'{2*v} m/s'),
          [pack(f'{f(F)} N',f'{f(P/2)} W',f'{v/2} m/s'),pack(f'{f(2*F)} N',f'{f(P)} W',f'{2*v} m/s'),pack(f'{f(F)} N',f'{f(P)} W',f'{v/2} m/s')],
          f'E=BLv，I=E/R={f(I)} A，阻力BIL=B²L²v/R={f(F)} N。稳定时外功率Fv=I²R={f(P)} W。恒力条件下v终=FR/(B²L²)，R倍增则终速倍增，并非减半。',
          ['感应电路与安培力耦合','用功率守恒复核','区分恒力与恒速的控制变量'],evidence={'B':B,'L':L,'R':R,'v':v})
    if i==1:
        v=4+n; dv=v/2; dx=m*R*dv/(B*B*L*L); heat=.5*m*(v*v-(v/2)**2); charge=m*dv/(B*L)
        return q('rod-braking-integral','磁阻尼与通过电荷量',
          f'质量0.10 kg的导体棒在光滑导轨上以 {v} m/s 进入足够大匀强磁场，B=0.50 T、棒长0.40 m，回路总电阻2.0 Ω。无外拉力，忽略自感。速度降至初速一半时，棒移动距离、通过电路的电荷量及焦耳热为多少？可对微小时段使用mΔv=−BLIΔt。',
          pack(f'{f(dx)} m',f'{f(charge)} C',f'{f(heat)} J'),
          [pack(f'{f(dx/2)} m',f'{f(charge)} C',f'{f(heat)} J'),pack(f'{f(dx)} m',f'{f(charge/2)} C',f'{f(.5*m*(v/2)**2)} J'),pack(f'{f(dx)} m',f'{f(charge)} C',f'{f(.5*m*v*v)} J')],
          f'累加动量式m(v₀−v)=BLq，q={f(charge)} C；又q=BLΔx/R，Δx=mR(v₀−v)/(B²L²)={f(dx)} m。动能损失全部为焦耳热Q=½m(v₀²−v²)={f(heat)} J。不能当作恒定阻力运动。',
          ['累加磁力冲量','将电荷与磁通变化联立','以动能差求耗散'],7,evidence={'m':m,'B':B,'L':L,'R':R,'v':v})
    if i==2:
        turns=20+n*5; area=.02; t=.5; db=.6; resistance=4; em=turns*area*db/t; Q=turns*area*db/resistance; heat=em*em/resistance*t
        return q('flux-ramp','磁通变化与非均匀速率',
          f'{turns}匝线圈每匝面积0.020 m²、总电阻4.0 Ω。垂直线圈的磁场在0.50 s内均匀增加0.60 T。求通过截面的电荷量和焦耳热。若同一磁通变化改在0.25 s内均匀完成，电荷量及焦耳热各变为几倍？忽略自感。',
          pack(f'{f(Q)} C',f'{f(heat)} J','电荷1倍，热量2倍'),
          [pack(f'{f(Q)} C',f'{f(heat)} J','电荷2倍，热量2倍'),pack(f'{f(2*Q)} C',f'{f(heat)} J','电荷1倍，热量1倍'),pack(f'{f(Q)} C',f'{f(heat/2)} J','电荷1倍，热量4倍')],
          f'E=N S ΔB/Δt={f(em)} V，q=EΔt/R=N SΔB/R={f(Q)} C；Q热=E²Δt/R={f(heat)} J。磁通变化固定时q与时长无关，而均匀变化的热量反比于时长，所以缩时一半热量翻倍。',
          ['计算磁通匝数效应','区分电荷积分与热积分','比较不同时间方案'],evidence={'N':turns,'S':area,'db':db,'t':t,'R':resistance})
    if i==3:
        v=2+n*.5; width=.6; r=3; E=B*L*v; I=E/r; time=width/v; heat=2*I*I*r*time
        return q('loop-entry-exit','线框穿越磁区与总电荷',
          f'矩形线框沿运动方向长0.60 m、宽0.40 m，总电阻3.0 Ω，以 {f(v)} m/s 匀速穿过宽度大于0.60 m的磁场条带，B=0.50 T垂直框面。由完全在外到完全穿出，求焦耳热、流过某截面的代数电荷量及电荷量绝对值的累计值。忽略自感。',
          pack(f'{f(heat)} J','0 C',f'{f(2*B*L*width/r)} C'),
          [pack(f'{f(heat)} J',f'{f(2*B*L*width/r)} C',f'{f(2*B*L*width/r)} C'),pack(f'{f(heat/2)} J','0 C',f'{f(B*L*width/r)} C'),pack('0 J','0 C','0 C')],
          f'仅进入和离开各0.60/v秒有电流，I=BLv/R={f(I)} A，两段生热相加得{f(heat)} J。进、出电流方向相反，代数电荷相消；累计绝对值2B·0.40·0.60/R={f(2*B*L*width/r)} C，不能把电荷相消误作热量也相消。',
          ['划分进出与全浸阶段','处理反向电流的代数累计','区分热量不可相消'],7,evidence={'B':B,'L':L,'w':width,'R':r,'v':v})
    if i==4:
        E=4+n; r=1; R1=3; cap=.02; initial=E/(r+R1); Q=cap*E; heat=.5*cap*E*E*R1/(r+R1)
        return q('motional-capacitor','动生电源给电容充电',
          f'导体棒在匀强磁场中受控匀速运动，等效恒定动生电动势 {E} V，棒电阻1.0 Ω，与3.0 Ω电阻和初始不带电的0.020 F电容器串联。忽略自感，速度始终保持不变。求刚开始电流、最终电荷量及充电全过程3.0 Ω电阻产生的热量。可用结论：恒压充电的总电阻热等于最终电容储能。',
          pack(f'{f(initial)} A',f'{f(Q)} C',f'{f(heat)} J'),
          [pack(f'{f(E/R1)} A',f'{f(Q)} C',f'{f(heat)} J'),pack(f'{f(initial)} A',f'{f(cap*E*.75)} C',f'{f(heat)} J'),pack(f'{f(initial)} A',f'{f(Q)} C',f'{f(2*heat)} J')],
          f'初始电容电压为零，I₀=E/(r+R)={f(initial)} A。最终电流零、电容电压E，q=CE={f(Q)} C。总电阻热为½CE²，串联同电流使热量按电阻比分配，3Ω占3/4，Q₃={f(heat)} J。稳态不能用初始分压求电容电压。',
          ['区别充电初态与稳态','应用电容电荷关系','按串联电阻比分配耗散'],7,evidence={'E':E,'r':r,'R':R1,'C':cap})
    if i==5:
        N=100+n*20; area=.01; w=20; r=5; Emax=N*.5*area*w; Irms=Emax/sqrt(2)/r; P=Emax*Emax/(2*r)
        return q('generator-rms','发电机峰值有效值与转速',
          f'{N}匝矩形线圈每匝面积0.010 m²，在0.50 T匀强磁场中以20 rad/s匀速转动，回路纯电阻5.0 Ω，线圈内阻忽略。求电流有效值、平均电功率；若转速加倍，维持转动的平均驱动力矩变为几倍？',
          pack(f'{f(Irms)} A',f'{f(P)} W','2倍'),
          [pack(f'{f(Emax/r)} A',f'{f(2*P)} W','4倍'),pack(f'{f(Irms)} A',f'{f(P)} W','4倍'),pack(f'{f(Irms/2)} A',f'{f(P/2)} W','1倍')],
          f'E峰=NBSω={f(Emax)} V，I有效=E峰/(√2R)={f(Irms)} A，平均P=E峰²/(2R)={f(P)} W。转速加倍P变4倍，平均力矩τ=P/ω只变2倍。峰值不能直接代入平均焦耳功率。',
          ['磁通导出正弦峰值','转换有效值算平均功率','将功率缩放转换为力矩缩放'],evidence={'N':N,'S':area,'B':.5,'w':w,'R':r})
    if i==6:
        F=.1+n*.02; r=.5; R=2; v=F*(r+R)/(B*B*L*L); P=F*v; useful=P*R/(r+R)
        return q('rod-load-power','磁感应稳态与负载功率',
          f'光滑导轨上的导体棒长0.40 m、棒电阻0.50 Ω，外接2.0 Ω电阻，B=0.50 T。以 {f(F)} N恒力拉棒，忽略自感，最终匀速。求终速、外电阻功率，以及输入机械功率中变成棒内热的比例。',
          pack(f'{f(v)} m/s',f'{f(useful)} W','20%'),
          [pack(f'{f(F*R/(B*B*L*L))} m/s',f'{f(P)} W','0%'),pack(f'{f(v)} m/s',f'{f(P)} W','25%'),pack(f'{f(v)} m/s',f'{f(useful/2)} W','80%')],
          f'稳态I=F/(BL)，总电动势I(R+r)=BLv，所以v={f(v)} m/s。外电阻功率I²R={f(useful)} W；棒内热占r/(R+r)=0.5/2.5=20%。机械输入等于所有电阻热之和，不能只算外负载。',
          ['力平衡与回路方程联立','区分总输入与负载输出','按内外电阻分配功率'],evidence={'B':B,'L':L,'F':F,'r':r,'R':R})
    r0=2+n*.5; rho=.5; v=2; x=4; I=B*L*v/(r0+rho*x); force=B*L*I
    return q('resistive-rails','电阻导轨与变磁阻力',
          f'导体棒长0.40 m，在B=0.50 T磁场中以2.0 m/s匀速远离闭合端。回路固定部分电阻为 {f(r0)} Ω，两根导轨单位移动距离合计增加电阻0.50 Ω/m，棒从x=0开始运动。求x=4.0 m处所需拉力；继续匀速时拉力和焦耳热功率怎样变化？',
          pack(f'{f(force)} N','拉力减小，功率减小'),
          [pack(f'{f(B*B*L*L*v/r0)} N','拉力不变，功率不变'),pack(f'{f(force)} N','拉力增大，功率增大'),pack(f'{f(force)} N','拉力减小，功率不变')],
          f'回路R(x)=R₀+0.50x，x=4时R={f(r0+2)} Ω，I=BLv/R，F=BLI={f(force)} N。匀速下电动势固定，随着R增大，F=(BL)²v/R下降，P=(BLv)²/R也下降。',
          ['建立位移相关回路电阻','联立感应电流与受力','在恒速约束下比较功率'],evidence={'B':B,'L':L,'R0':r0,'rho':rho,'v':v,'x':x})


def equilibrium(i,n):
    c=.3+n*.1
    if i==0:
        x=2*c/3; C=x; A=c-x; extra=c/3
        return q('eq-add-product','三段式与二次扰动',
          f'恒温1.0 L容器中A(g)+B(g)⇌C(g)+D(g)，K=4。初始A、B浓度均为{f(c)} mol/L，C、D均为零。达平衡后，瞬时加入C使其浓度增加{f(extra)} mol/L，体积不变。求原平衡A转化率、加C瞬间Q，并判断随后反应方向。',
          pack('2/3','6','逆向'),[pack('1/2','4','不移动'),pack('2/3','6','正向'),pack('2/3','4','不移动')],
          f'令反应进度浓度为x，K=x²/(c−x)²=4，x=2c/3，转化率2/3。加C后[C]=c，[D]=2c/3，[A]=[B]=c/3，Q=6>K，故逆向，且K不变。',
          ['三段式求原平衡','计算扰动瞬间反应商','由Q与K比较方向'],evidence={'c':c})
    if i==1:
        K=2*c/3
        return q('eq-dissociation','解离度与压缩反应商',
          f'恒温定容容器中仅充入N₂O₄，初始浓度为{f(c)} mol/L，反应N₂O₄(g)⇌2NO₂(g)。平衡压强为初始的4/3，均视为理想气体。求解离度、Kc；若瞬间把体积减半，Q与原Kc之比为多少，随后向哪边移动？',
          pack('1/3',f'{f(K)} mol/L','2，逆向'),
          [pack('2/3',f'{f(K)} mol/L','1/2，正向'),pack('1/3',f'{f(K/4)} mol/L','2，逆向'),pack('1/3',f'{f(K)} mol/L','1，不移动')],
          f'物质的量总数由n₀变n₀(1+α)，故α=1/3。Kc=(2cα)²/[c(1−α)]=2c/3={f(K)} mol/L。瞬时各浓度翻倍，Q翻为2K，故逆向。压强增大不等于K改变。',
          ['用压强反演组成','写含化学计量幂次的K','分析压缩瞬间Q缩放'],evidence={'c':c})
    if i==2:
        c=2+n*.5; K=2/c
        return q('eq-inert-pressure','惰性气体与控制条件',
          f'A(g)+B(g)⇌C(g)，初始等浓度A、B各{f(c)} mol/L，无C。定温定容达平衡时A转化率50%。求Kc。此后若恒温恒总压加入惰性气体使体积翻倍，瞬间Q/Kc与移动方向是什么？若改为恒容加入同量惰性气体，方向如何？',
          pack(f'{f(K)} L/mol','2，逆向','不移动'),
          [pack(f'{f(K)} L/mol','1/2，正向','不移动'),pack(f'{f(1/K)} L/mol','2，逆向','正向'),pack(f'{f(K)} L/mol','2，逆向','逆向')],
          f'平衡[A]=[B]=[C]=c/2，K=(c/2)/(c/2)²=2/c={f(K)} L/mol。恒压加惰性气体导致体积翻倍，各反应物浓度减半，Q′=2K，故逆向。恒容时各参与反应物的浓度不变，Q仍为K，不移动。',
          ['由转化率建立K','区分恒压稀释与恒容','计算反应商而非套压强口号'],7,evidence={'c':c})
    if i==3:
        K=4+n; c=1; x=sqrt(K)/(1+sqrt(K)); krev=1/sqrt(K)
        return q('eq-rewrite','方程式变换与平衡组成',
          f'某温度下A(g)+B(g)⇌C(g)+D(g)的K={K}。1 L中初放A、B各1 mol，C、D为零。求平衡C的物质的量，以及反应½C+½D⇌½A+½B的平衡常数（数值近似至三位有效数字）。',
          pack(f'{f(x)} mol',f'{f(krev)}'),
          [pack(f'{f(K/(1+K))} mol',f'{f(1/K)}'),pack(f'{f(x)} mol',f'{f(1/K)}'),pack(f'{f(x/2)} mol',f'{f(sqrt(K))}')],
          f'设生成x mol，x²/(1−x)²=K，取0<x<1得x=√K/(1+√K)={f(x)} mol。目标式先逆转再所有系数乘1/2，K′=K^(−1/2)={f(krev)}，不能把K直接除以2。',
          ['按化学计量列平衡式','筛选物料范围内的根','同时处理逆转与系数缩放'],evidence={'K':K})
    if i==4:
        p=90+15*n; alpha=.5; Kp=4*p/3
        return q('eq-constant-pressure','恒压解离与分压',
          f'纯A气体在恒温恒压{p} kPa下发生A(g)⇌2B(g)，达到平衡时体积为初始的1.50倍。求A的转化率、B的摩尔分数和Kp（分压以kPa代入）。',
          pack('50%','2/3',f'{f(Kp)} kPa'),
          [pack('50%','1/2',f'{f(p/2)} kPa'),pack('25%','2/3',f'{f(Kp)} kPa'),pack('50%','2/3',f'{f(1/Kp)} kPa⁻¹')],
          f'恒温恒压V比等于总物质的量比1+α，故α=0.50。n_A=0.5n₀，n_B=n₀，总1.5n₀，所以y_B=2/3，y_A=1/3。Kp=p_B²/p_A=(2p/3)²/(p/3)=4p/3。代入应为{f(4*p/3)} kPa。',
          ['从可变体积求转化率','以总物质的量算摩尔分数','用分压而非总压构造Kp'],evidence={'p':p})
    if i==5:
        V=2+n*.5; x=.4; K=(.8/V)**2/((.6/V)*(1.8/V)**3)
        return q('eq-ammonia-density','平均摩尔质量反推转化率',
          f'密闭容器初放1 mol N₂和3 mol H₂，无NH₃，仅发生N₂+3H₂⇌2NH₃。容积{f(V)} L，平衡混合气平均摩尔质量10.625 g/mol。求N₂转化率和该温度Kc；相对原子质量N=14、H=1。',
          pack('40%',f'{f(K)} L²/mol²'),
          [pack('20%',f'{f(K)} L²/mol²'),pack('40%',f'{f(K/(V*V))} L²/mol²'),pack('60%',f'{f(K)} L²/mol²')],
          f'总质量34g，平衡总量34/10.625=3.2mol，故4−2x=3.2，x=0.40mol。平衡N₂、H₂、NH₃分别0.60、1.80、0.80mol；Kc=(0.8/V)²/[(0.6/V)(1.8/V)³]={f(K)} L²/mol²，体积的净幂次为2。',
          ['总质量守恒反推总气体量','化学计量关联转化率','保留体积幂次求K'],7,evidence={'V':V})
    if i==6:
        V=2+n; K=.2; enough=n%2==0; solid=V*(.4 if enough else .1); co2=K*V if enough else solid
        return q('eq-solid-inventory','固体库存与平衡存在性',
          f'真空密闭容器体积{V} L，加入{f(solid)} mol CaCO₃(s)，加热到固定温度，仅发生CaCO₃(s)⇌CaO(s)+CO₂(g)，此温度Kc=c(CO₂)=0.20 mol/L。假设反应可以进行且气体理想。反应充分后CO₂浓度及剩余CaCO₃物质的量是多少？',
          pack(f'{f(co2/V)} mol/L',f'{f(solid-co2)} mol'),
          [pack('0.20 mol/L',f'{f(solid)} mol'),pack(f'{f(solid/V)} mol/L',f'{f(solid)} mol'),pack('0 mol/L','0 mol')],
          f'若两种固体共存，要生成0.20V={f(.2*V)} mol CO₂。先与初始CaCO₃库存{f(solid)} mol比较；实际可生成量取两者较小值{f(co2)} mol，故气体浓度{f(co2/V)} mol/L，剩余固体{f(solid-co2)} mol。固体耗尽时不能强行令Q=K。',
          ['识别异相K表达式','检查物料能否支撑平衡','区分耗尽终态与共存平衡'],7,evidence={'V':V,'solid':solid,'K':K})
    total=3*c; oldA=c; oldB=2*c; newB=total*4/5; add=newB-oldB
    return q('eq-temperature-rebuild','变温K与新平衡重建',
          f'定容容器中仅有A(g)⇌B(g)。低温平衡Kc=2，[A]={f(c)} mol/L；升到较高温度时Kc=4，体积不变、物质不逸出。求升温瞬间Q、反应正向的吸放热性质、达到新平衡时B增加的浓度。',
          pack('2','吸热',f'{f(add)} mol/L'),
          [pack('4','放热',f'{f(add)} mol/L'),pack('2','吸热',f'{f(2*c)} mol/L'),pack('2','放热',f'{f(add)} mol/L')],
          f'变温瞬间组成未变，Q=[B]/[A]=2；新K=4，故正向移动。K随温度上升而增大说明正向吸热。总浓度3c守恒，新[B]=4×3c/5，增加(12/5−2)c=0.4c={f(add)} mol/L。',
          ['区分瞬间Q与新温度K','从K温度趋势判断热效应','用新K和总量重建组成'],evidence={'c':c})


def mole(i,n):
    scale=1+n*.2
    if i==0:
        mass=28.6*scale; V=.5; portion=.05; final=.2; c=mass/286/V*portion/final
        return q('hydrate-dilution','结晶水配液与离子计数',
          f'将{f(mass)} g Na₂CO₃·10H₂O完全溶解配成500 mL溶液，取50.0 mL稀释至200 mL。M(晶体)=286 g/mol，忽略水解对Na⁺的影响。求稀释液c(Na⁺)及其中Na⁺总数相对于N_A的倍数。',
          pack(f'{f(2*c)} mol/L',f'{f(2*c*.2)} N_A'),
          [pack(f'{f(c)} mol/L',f'{f(c*.2)} N_A'),pack(f'{f(2*c*4)} mol/L',f'{f(2*c*.2)} N_A'),pack(f'{f(2*c)} mol/L',f'{f(2*c*.5)} N_A')],
          f'晶体量={f(mass/286)} mol，原液碳酸钠浓度={f(mass/286/.5)} mol/L。取样后溶质为{f(mass/286*.1)} mol，稀释不改变量；Na⁺是其2倍，c={f(2*c)} mol/L，粒子数={f(2*c*.2)} N_A。结晶水参与称量质量但不增加Na⁺。',
          ['按水合物摩尔质量计量','连续取样与稀释守恒','化学式系数转换离子数'],evidence={'mass':mass})
    if i==1:
        a=.1*scale; b=.2*scale; total=a+b; oxygen=.5*a+2*b; co2=total; h2o=2*b
        return q('gas-combustion-inverse','混合气燃烧数据反推',
          f'CO与CH₄混合气共{f(total)} mol，完全燃烧消耗O₂ {f(oxygen)} mol，产物冷却使水全部液化。求原混合气中CH₄物质的量、生成液态水质量及干燥CO₂体积（标准状况22.4 L/mol，M(H₂O)=18 g/mol）。',
          pack(f'{f(b)} mol',f'{f(18*h2o)} g',f'{f(22.4*co2)} L'),
          [pack(f'{f(a)} mol',f'{f(18*b)} g',f'{f(22.4*co2)} L'),pack(f'{f(b)} mol',f'{f(18*h2o)} g',f'{f(22.4*(co2+h2o))} L'),pack(f'{f(b)} mol',f'{f(18*b)} g',f'{f(22.4*co2/2)} L')],
          f'设CH₄为x mol，CO为n−x，耗氧½(n−x)+2x={f(oxygen)}，解得x={f(b)} mol。水为2x mol，质量{f(36*b)} g。每种含碳分子均产1个CO₂，故CO₂总量等于原混合气总量，体积{f(22.4*co2)} L；液态水不可用气体摩尔体积。',
          ['联立混合物和耗氧关系','按氢守恒计算水','处理冷却后的相态'],evidence={'a':a,'b':b})
    if i==2:
        a=.1*scale; b=.15*scale; H=a+2*b; CO2=a+b; mass=84*a+106*b
        return q('carbonate-two-observations','双观测反推碳酸盐组成',
          f'NaHCO₃和Na₂CO₃混合样品用足量盐酸完全反应，消耗H⁺共{f(H)} mol，释放CO₂ {f(CO2)} mol。求Na₂CO₃的物质的量及原样品质量。M(NaHCO₃)=84、M(Na₂CO₃)=106 g/mol，不计杂质。',
          pack(f'{f(b)} mol',f'{f(mass)} g'),
          [pack(f'{f(a)} mol',f'{f(mass)} g'),pack(f'{f(H/2)} mol',f'{f(H/2*106)} g'),pack(f'{f(b)} mol',f'{f(106*CO2)} g')],
          f'设两组分为x、y mol，则x+y=n(CO₂)，x+2y=n(H⁺)。相减得y={f(H-CO2)} mol，再得x={f(a)} mol。总质量84x+106y={f(mass)} g；不能只用放气量区分两种碳酸盐。',
          ['选择两个独立守恒观测','联立计量方程','按组分摩尔质量回算质量'],evidence={'a':a,'b':b})
    if i==3:
        c=.2*scale; v=.1; remove=.025; add=.05; new=(c*v-c*remove)/(v-remove+add); Na=2*new
        return q('sampling-replenish','取样补水与守恒对象',
          f'有100 mL {f(c)} mol/L Na₂SO₄溶液，取走25.0 mL，再向剩余液中加入50.0 mL水，体积可加。求最终c(Na⁺)、剩余SO₄²⁻物质的量，及与原液相比Na⁺浓度的比值。忽略离子缔合。',
          pack(f'{f(Na)} mol/L',f'{f(c*.075)} mol','0.60'),
          [pack(f'{f(2*c*100/150)} mol/L',f'{f(c*.1)} mol','2/3'),pack(f'{f(new)} mol/L',f'{f(c*.075)} mol','0.30'),pack(f'{f(Na)} mol/L',f'{f(c*.1)} mol','0.60')],
          f'取样同时带走溶质，剩余SO₄²⁻为0.075c={f(c*.075)} mol；补水后体积125mL。c(Na⁺)=2×0.075c/0.125=1.2c={f(Na)} mol/L，与原来2c之比0.60。不能对取样前后全体系直接套“溶质不变”。',
          ['区分取样与稀释','确定最终总体积','离子化学计量与比例分析'],evidence={'c':c})
    if i==4:
        a=.1*scale; b=.15*scale; gas=1.5*a+b; mass=27*a+24*b; H=3*a+2*b
        return q('alloy-acid-inverse','合金放氢反推组成',
          f'Al、Mg合金样品质量{f(mass)} g，与足量非氧化性酸完全反应，放H₂ {f(gas)} mol。求样品Al质量分数和消耗H⁺物质的量。M(Al)=27、M(Mg)=24 g/mol，金属均无氧化膜，不考虑其他反应。',
          pack(f'{f(27*a/mass*100)}%',f'{f(H)} mol'),
          [pack(f'{f(a/(a+b)*100)}%',f'{f(H)} mol'),pack(f'{f(27*a/mass*100)}%',f'{f(gas)} mol'),pack(f'{f(24*b/mass*100)}%',f'{f(H/2)} mol')],
          f'设Al、Mg为x、y mol，27x+24y={f(mass)}，1.5x+y={f(gas)}。解得x={f(a)}、y={f(b)} mol，Al质量分数27x/m={f(27*a/mass*100)}%。由每mol H₂耗2mol H⁺，耗酸={f(H)} mol。',
          ['由质量和电子计量联立','区分物质的量分数和质量分数','用放氢量复核酸量'],7,evidence={'a':a,'b':b})
    if i==5:
        c=.2*scale; vs=.02; cf=.1; Vf=c*vs/cf; sodium=2*cf; water=Vf-vs
        return q('stock-density','质量分数密度与定容',
          f'NaOH母液质量分数8.00%，密度1.10 g/mL。量取{f(10*scale)} mL，配成0.200 mol/L溶液，M(NaOH)=40.0 g/mol。求需定容至的总体积，以及若误把该体积当成加水体积，实际浓度相对于目标值如何变化？定容过程不要求水和母液体积严格可加；第二问仅按体积可加作误差模型。',
          pack(f'{f(110*scale)} mL',f'偏低，为目标的 {f(11/12)} 倍'),
          [pack(f'{f(100*scale)} mL','等于目标'),pack(f'{f(110*scale)} mL','偏高，为目标的12/11倍'),pack(f'{f(220*scale)} mL','偏低，为目标的1/2倍')],
          f'母液质量ρV=11s g，NaOH质量0.88s g，n=0.022s mol；需最终V=n/0.200=0.110s L。误加110s mL水则模型总体积120s mL，浓度比=110/120=11/12。定容体积是最终溶液体积。',
          ['用密度和质量分数求溶质','物质的量与定容体积互算','建立误操作体积模型'],evidence={'s':scale})
    if i==6:
        fe=.02*scale; volume=.25; aliquot=.025; perm=fe/5*aliquot/volume; cp=.02; vp=perm/cp
        return q('aliquot-titration','分样滴定与原样纯度',
          f'含Fe²⁺的样品总质量{f(2*scale)} g，全部溶解定容250 mL，取25.0 mL，用0.0200 mol/L酸性KMnO₄滴定，恰耗{f(vp*1000)} mL。离子计量MnO₄⁻+5Fe²⁺+8H⁺→Mn²⁺+5Fe³⁺+4H₂O。求原样中Fe元素质量分数及定容液c(Fe²⁺)，M(Fe)=56 g/mol。',
          pack('56.0%',f'{f(fe/.25)} mol/L'),
          [pack('5.60%',f'{f(fe/.25/10)} mol/L'),pack('11.2%',f'{f(fe/.25/5)} mol/L'),pack('56.0%',f'{f(fe/.025)} mol/L')],
          f'滴定剂物质的量为{f(perm)} mol，对应分样Fe²⁺为5倍，再乘250/25=10反推全样，n(Fe)={f(fe)} mol；质量{f(fe*56)} g，除样品质量得56.0%。定容液浓度n/0.250={f(fe/.25)} mol/L。',
          ['滴定剂化学计量换算','从分样放大到全样','分别计算纯度与浓度'],7,evidence={'sample_mass':2*scale,'c':cp,'volume_litres':vp})
    a=.1*scale; b=.2*scale; H=2*a; excess=H/2; prod=min(a,b/3)*2; remain=a-prod/2
    return q('limiting-reagent','限量试剂与粒子余量',
          f'在理想化完全反应模型中，N₂+3H₂→2NH₃。初始N₂ {f(a)} mol、H₂ {f(b)} mol，氨不分离，反应达到限量试剂耗尽后冷却。求NH₃产量、剩余N₂物质的量及剩余气体N₂与NH₃分子总数相对N_A的倍数。忽略氨液化。',
          pack(f'{f(prod)} mol',f'{f(remain)} mol',f'{f(prod+remain)} N_A'),
          [pack(f'{f(2*a)} mol','0 mol',f'{f(2*a)} N_A'),pack(f'{f(prod)} mol',f'{f(a-b)} mol',f'{f(a+b)} N_A'),pack(f'{f(prod/2)} mol',f'{f(remain)} mol',f'{f(prod/2+remain)} N_A')],
          f'比较n/系数：N₂为{f(a)}，H₂/3为{f(b/3)}，氢为限量试剂。生成氨2b/3={f(prod)} mol，余氮a−b/3={f(remain)} mol，总分子数对应{f(prod+remain)} mol。该题明确采用完全反应模型，不能把真实合成氨平衡偷偷代入。',
          ['用计量比选择限量试剂','同时核算生成物与余量','辨别模型假设与实际平衡'],evidence={'a':a,'b':b})


def redox(i,n):
    s=1+n*.2
    if i==0:
        cl=.3*s; hot=n%2==0; electron=(5/6 if hot else .5)*cl; oxy=cl/3 if hot else cl
        return q('chlorine-disproportionation','歧化反应电子去向',
          f'{f(cl)} mol Cl₂恰与足量NaOH反应。'+('热浓碱中仅生成NaCl、NaClO₃和水。' if hot else '冷稀碱中仅生成NaCl、NaClO和水。')+'求氧化产物的物质的量、被还原的氯原子占全部氯原子的比例、转移电子物质的量。',
          pack(f'{f(oxy)} mol','5/6' if hot else '1/2',f'{f(electron*2 if hot else electron*2)} mol'),
          [pack(f'{f(oxy)} mol','1/6' if hot else '1',f'{f(cl)} mol'),pack(f'{f(cl)} mol','1/2' if hot else '1/4',f'{f(cl/2)} mol'),pack(f'{f(oxy/2)} mol','5/6' if hot else '1/2',f'{f(cl*2)} mol')],
          ('热碱中3Cl₂+6OH⁻→5Cl⁻+ClO₃⁻+3H₂O，氧化产物为n(Cl₂)/3，被还原氯占5/6，每3mol Cl₂转移5mol电子。' if hot else '冷碱中Cl₂+2OH⁻→Cl⁻+ClO⁻+H₂O，氧化产物与Cl₂等物质的量，被还原氯占1/2，每mol Cl₂转移1mol电子。')+f'本题电子转移为{f(cl*5/3 if hot else cl)} mol，不能把两个方向的得失电子数相加。',
          ['配平歧化分支','按原子去向计算比例','避免得失电子重复计数'],evidence={'cl':cl,'hot':hot})
    if i==1:
        fe=.05*s; cu=.025*s; e=3*fe+2*cu; nitrate=e/3; acid=4*e/3
        return q('nitric-mixture','混合金属硝酸耗量',
          f'Fe {f(fe)} mol与Cu {f(cu)} mol完全溶于足量稀硝酸，铁全部为Fe³⁺，唯一还原气体为NO。求NO产量及HNO₃理论消耗量（包括作为氧化剂和成盐部分），不计溶解气体。',
          pack(f'{f(nitrate)} mol',f'{f(acid)} mol'),
          [pack(f'{f(nitrate)} mol',f'{f(nitrate)} mol'),pack(f'{f(e)} mol',f'{f(acid)} mol'),pack(f'{f(nitrate)} mol',f'{f(e)} mol')],
          f'金属放电子3nFe+2nCu={f(e)} mol，每mol NO由N(+5)得3e，故nNO={f(nitrate)}。成盐NO₃⁻需3nFe+2nCu={f(e)} mol，再加被还原硝酸{f(nitrate)} mol，总耗酸{f(acid)} mol。',
          ['电子守恒反推气体','区分硝酸双重用途','用电荷平衡计成盐阴离子'],7,evidence={'fe':fe,'cu':cu})
    if i==2:
        V=.02; c=.02*s; peroxide=2.5*V*c; gas=2*peroxide # reaction perm + peroxide -> 5O2 for 2perm, peroxide 5 ->5O2 actually gas=peroxide
        return q('peroxide-titration','过氧化氢双重身份与滴定',
          f'酸性溶液中用{f(c)} mol/L KMnO₄滴定含H₂O₂的25.0 mL样品，恰耗20.0 mL。反应产物Mn²⁺、O₂和水，H₂O₂中O为−1价。求原样品c(H₂O₂)、生成O₂物质的量；该反应中H₂O₂作何角色？',
          pack(f'{f(peroxide/.025)} mol/L',f'{f(peroxide)} mol','还原剂'),
          [pack(f'{f(peroxide/.025)} mol/L',f'{f(peroxide/2)} mol','氧化剂'),pack(f'{f(V*c/.025)} mol/L',f'{f(V*c)} mol','还原剂'),pack(f'{f(peroxide/.025)} mol/L',f'{f(peroxide)} mol','氧化剂')],
          f'Mn从+7到+2每个得5e，H₂O₂氧从−1到0每分子失2e，所以nH₂O₂/nMnO₄⁻=5/2。H₂O₂量为{f(peroxide)} mol，浓度{f(peroxide/.025)} mol/L，每mol H₂O₂形成1mol O₂，H₂O₂被氧化作还原剂。',
          ['由价态推化学计量','滴定数据反求浓度','辨别非常见还原剂身份'],evidence={'c':c,'V':V})
    if i==3:
        iod=.01*s; thio=2*iod; chromium=iod/3; mass=chromium*294
        return q('iodometric-relay','碘量法两段电子接力',
          f'重铬酸钾样品在酸中与过量I⁻反应，使Cr₂O₇²⁻变为2Cr³⁺，产生的I₂再用{f(thio)} mol S₂O₃²⁻恰好滴定，第二步I₂+2S₂O₃²⁻→2I⁻+S₄O₆²⁻。求样品中K₂Cr₂O₇质量及第一步转移电子量。M(K₂Cr₂O₇)=294 g/mol。',
          pack(f'{f(mass)} g',f'{f(thio)} mol'),
          [pack(f'{f(mass*3)} g',f'{f(thio/2)} mol'),pack(f'{f(mass)} g',f'{f(thio*2)} mol'),pack(f'{f(mass/2)} g',f'{f(thio)} mol')],
          f'每mol Cr₂O₇²⁻中2个Cr各得3e，总6e，对应3mol I₂。第二步每mol I₂耗2mol硫代硫酸根，所以nCr₂O₇²⁻=nS₂O₃²⁻/6={f(chromium)} mol，质量{f(mass)} g；首步电子量6nCr₂O₇²⁻={f(thio)} mol。',
          ['跨两反应串联计量','按两个Cr计电子','由终点量反推起始物质量'],7,evidence={'thio':thio})
    if i==4:
        moles=.06*s; no=.02*s; no2=.04*s; e=3*no+no2; Cu=e/2; acid=2*Cu+no+no2
        return q('mixed-nox','混合氮氧化物与耗酸',
          f'Cu与足量硝酸反应，收集干燥气体NO {f(no)} mol、NO₂ {f(no2)} mol，铜全转为Cu²⁺，气体无其他组分。求溶解Cu物质的量和HNO₃总消耗量。',
          pack(f'{f(Cu)} mol',f'{f(acid)} mol'),
          [pack(f'{f((no+no2)/2)} mol',f'{f(no+no2)} mol'),pack(f'{f(Cu)} mol',f'{f(no+no2)} mol'),pack(f'{f(e)} mol',f'{f(acid)} mol')],
          f'NO中N得3e，NO₂中N得1e，得电子总量3nNO+nNO₂={f(e)} mol，所以铜量为一半{f(Cu)} mol。被还原硝酸为nNO+nNO₂，成盐再需2nCu，总耗酸={f(acid)} mol。',
          ['区分不同气体的得电子数','由电子守恒求金属','综合氮原子去向核酸量'],evidence={'no':no,'no2':no2})
    if i==5:
        fe=.1*s; ferric=.04*s; e=ferric; cl=e/2; remain=fe-ferric
        return q('oxidant-limited','氧化剂限量与铁价态分配',
          f'溶液含Fe²⁺ {f(fe)} mol，通入Cl₂ {f(cl)} mol并完全反应，Cl₂仅把Fe²⁺氧化为Fe³⁺，无其他反应。求反应后Fe³⁺/Fe²⁺物质的量比及转移电子物质的量；再使剩余Fe²⁺全部氧化需补多少Cl₂？',
          pack('2/3',f'{f(e)} mol',f'{f(remain/2)} mol'),
          [pack('1/3',f'{f(cl)} mol',f'{f(remain)} mol'),pack('2/3',f'{f(2*e)} mol',f'{f(remain/2)} mol'),pack('3/2',f'{f(e)} mol',f'{f(remain/2)} mol')],
          f'Cl₂+2Fe²⁺→2Cl⁻+2Fe³⁺，产生Fe³⁺=2nCl₂={f(ferric)} mol，余Fe²⁺={f(remain)} mol，比例2/3。电子量为{f(e)} mol，补Cl₂需余Fe²⁺的一半{f(remain/2)} mol。',
          ['限量氧化剂决定转化量','计算反应后两价态比','反求补充氧化剂需求'],evidence={'fe':fe,'cl':cl})
    if i==6:
        electrons=.12*s; chlorate=electrons/6; chloride=chlorate*5
        return q('chlorate-reductant','不同价氯的电子配比',
          f'酸性条件下KClO₃与过量盐酸反应，ClO₃⁻和Cl⁻中的氯最终均变为Cl₂；实际转移电子{f(electrons)} mol。求消耗KClO₃物质的量与生成Cl₂物质的量，不能把同种元素在反应物中的两个来源合并成平均价态。',
          pack(f'{f(electrons/5)} mol',f'{f(3*electrons/5)} mol'),
          [pack(f'{f(electrons/6)} mol',f'{f(electrons/2)} mol'),pack(f'{f(electrons/5)} mol',f'{f(electrons/5)} mol'),pack(f'{f(electrons/10)} mol',f'{f(3*electrons/10)} mol')],
          f'ClO₃⁻中Cl从+5到0，每mol得5mol电子，故nKClO₃=n(e)/5={f(electrons/5)} mol；每个氯酸根需5个Cl⁻提供电子，总6个Cl原子产3Cl₂。反应ClO₃⁻+6H⁺+5Cl⁻→3Cl₂+3H₂O，nCl₂=3n(e)/5={f(3*electrons/5)} mol。',
          ['分离同元素的不同价态来源','先按电子数配原子比','再用原子守恒求气体'],evidence={'e':electrons})
    e=.1*s; sulfur=e/6
    return q('sulfite-air','亚硫酸盐氧化与滴定偏差',
          f'样品含Na₂SO₃，测定前已有20%的SO₃²⁻被空气氧化为SO₄²⁻。其余SO₃²⁻用酸性KMnO₄完全氧化为SO₄²⁻，实耗KMnO₄ {f(.016*s)} mol（Mn最终为+2价）。求原样Na₂SO₃物质的量及若忽略空气氧化，测量结果相对真值的百分偏差。',
          pack(f'{f(.05*s)} mol','偏低20%'),
          [pack(f'{f(.04*s)} mol','偏低25%'),pack(f'{f(.05*s)} mol','偏高20%'),pack(f'{f(.02*s)} mol','偏低50%')],
          f'每mol MnO₄⁻得5e，SO₃²⁻的S由+4到+6失2e，未被空气氧化部分为(5/2)nMnO₄⁻={f(.04*s)} mol。原量除以0.80得{f(.05*s)} mol。忽略预氧化只测到真值80%，相对真值偏低20%，不是以测量值为分母的25%。',
          ['电子计量推未氧化量','用残存比例反推原样','选对误差百分比的分母'],7,evidence={'s':s})


def periodic(i,n):
    if i==0:
        A=23+2*n
        return q('period-isoelectronic','等电子离子与同位素联合推断',
          f'短周期元素X、Y、Z的原子序数依次递增，X⁺、Y²⁺、Z³⁺均有10个电子。X的一种核素质量数为{A}。求该X核素中子数，三离子半径从大到小顺序，以及Z最高价氧化物分别与足量强酸、强碱反应时每mol氧化物消耗的H⁺、OH⁻物质的量。',
          pack(f'{A-11}','X⁺>Y²⁺>Z³⁺','6 mol、2 mol'),
          [pack(f'{A-10}','Z³⁺>Y²⁺>X⁺','6 mol、2 mol'),pack(f'{A-11}','X⁺>Y²⁺>Z³⁺','3 mol、1 mol'),pack(f'{A-11}','X⁺>Y²⁺>Z³⁺','6 mol、6 mol')],
          f'由电子数加失电子数得Z核=11、12、13，即Na、Mg、Al。核素中子数A−11={A-11}。等电子离子核电荷越大半径越小。Al₂O₃两性，分别消耗6H⁺或2OH⁻，不能把两个Al漏成一个。',
          ['从离子电子数恢复原子','区分核素质量数和原子序数','周期趋势与两性计量交叉'],evidence={'A':A})
    if i==1:
        amount=.1*(n+1)
        return q('period-successive-ie','逐级电离能定位与反应量',
          f'第三周期元素X的前四级电离能（相对单位）依次为6、12、80、100，Y位于X右侧相邻位置。只按稳定主族价态分析，取X最高价氧化物{f(amount)} mol与足量盐酸反应。求X、Y元素名称、消耗H⁺物质的量，以及Y最高价氧化物与强碱反应的性质。',
          pack('镁、铝',f'{f(2*amount)} mol','Y的氧化物具有两性，可溶于足量强碱'),
          [pack('铝、硅',f'{f(3*amount)} mol','Y的氧化物具有两性'),pack('镁、铝',f'{f(amount)} mol','Y的氧化物只与酸反应'),pack('钠、镁',f'{f(2*amount)} mol','Y的氧化物具有两性')],
          f'第二级到第三级出现大跃升，说明X有2个较易失去的价电子，第三周期为Mg，右邻Al。MgO+2H⁺→Mg²⁺+H₂O，所以耗{f(2*amount)} mol H⁺；Al₂O₃为两性氧化物。数据是结构判断模型，不当作真实电离能精确值。',
          ['识别逐级电离能跃迁','结合周期定位相邻元素','由氧化物性质核算酸耗'],evidence={'amount':amount})
    if i==2:
        amount=.02*(n+1)
        return q('period-oxide-hydride','气态氢化物与最高价氧化物',
          f'主族元素X位于第三周期，其最高价氧化物为XO₃，气态氢化物为H₂X；相邻右侧元素为Y。将{f(amount)} mol XO₃完全溶于水，再用足量NaOH中和。求X、Y及耗NaOH物质的量，并比较两元素简单气态氢化物的稳定性。按高中常规模型，不考虑浓酸副反应。',
          pack('S、Cl',f'{f(2*amount)} mol','HY比H₂X稳定'),
          [pack('P、S',f'{f(3*amount)} mol','H₂X更稳定'),pack('S、Cl',f'{f(amount)} mol','HY更稳定'),pack('S、Cl',f'{f(2*amount)} mol','H₂X比HY稳定')],
          f'主族最高+6价、最低−2价且第三周期，X=S，右邻Cl。SO₃入水形成H₂SO₄，每mol最终消耗2mol NaOH，故为{f(2*amount)} mol。同期从S到Cl非金属性增强，简单氢化物HCl稳定性更高；不能用氢化物水溶液酸性替代稳定性判据。',
          ['联合最高价与氢化物定位','从氧化物计中和当量','区分氢化物稳定性和酸性'],evidence={'amount':amount})
    if i==3:
        amount=.03*(n+1)
        return q('period-consecutive','连续原子序数与两性溶解',
          f'四个第三周期主族元素W、X、Y、Z原子序数连续，价电子总数为14。将其中X最高价氧化物{f(amount)} mol分别投入两份足量NaOH溶液和盐酸。求W、Z名称、X氧化物化学式，以及两份中消耗OH⁻与H⁺之比。',
          pack('Mg、P','Al₂O₃','1:3'),
          [pack('Na、Si','MgO','1:2'),pack('Mg、P','Al₂O₃','1:1'),pack('Al、S','SiO₂','2:1')],
          f'设W价电子k，连续四者共4k+6=14，k=2，因此Mg、Al、Si、P。X是Al，氧化物Al₂O₃每mol与碱耗2OH⁻、与酸耗6H⁺，之比1:3，与取用量{f(amount)} mol无关。',
          ['整数约束恢复连续元素','确定氧化物化学式','结合两性反应消耗比'],evidence={'amount':amount})
    if i==4:
        A=35; abundance=.65+n*.02; avg=35*abundance+37*(1-abundance)
        return q('period-isotope-average','同位素平均量与离子电子数',
          f'元素X的两种天然同位素质量数为35和37，丰度分别{f(abundance*100)}%、{f((1-abundance)*100)}%；X⁻有18个电子。近似以质量数当相对原子质量。求X平均相对原子质量、较轻同位素的中子数，以及X与同周期Na形成化合物的键型及化学式。',
          pack(f'{f(avg)}','18','离子键，NaCl'),
          [pack('36','17','共价键，NaCl'),pack(f'{f(avg)}','18','共价键，NaCl₂'),pack(f'{f(avg)}','19','离子键，NaCl')],
          f'X⁻18电子，原子17电子，是Cl。平均Ar=35p+37(1−p)={f(avg)}，不是简单平均；轻核素中子数35−17=18。Na失1电子、Cl得1电子，形成NaCl，主要为离子键。同位素变化不改变价电子结构。',
          ['由离子电子数定元素','按丰度加权而非简单平均','连接核结构与成键类型'],evidence={'p':abundance})
    if i==5:
        x=.1*(n+1); sodium=2*x; oxygen=x
        return q('period-peroxide','过氧化物价态与制氧',
          f'第三周期元素X的单价阳离子与Ne等电子，形成化合物X₂O₂。取{f(x)} mol该物质与足量水反应，求生成气体量、转移电子量，以及其中氧的价态和该反应是否歧化。按Na₂O₂+H₂O常规模型。',
          pack(f'{f(x/2)} mol',f'{f(x)} mol','氧为−1价，是歧化'),
          [pack(f'{f(x)} mol',f'{f(2*x)} mol','氧为−2价，不是歧化'),pack(f'{f(x/2)} mol',f'{f(2*x)} mol','氧为−1价，是歧化'),pack(f'{f(x/2)} mol',f'{f(x)} mol','氧为−2价，是歧化')],
          f'X⁺10电子得X=Na。2Na₂O₂+2H₂O→4NaOH+O₂，nO₂=nNa₂O₂/2={f(x/2)} mol；过氧化物氧由−1一部分升至0、一部分降至−2，每mol Na₂O₂转移1mol电子，量为{f(x)} mol。得失电子不重复相加。',
          ['电子结构定位金属','识别过氧化物特殊价态','配平与电子计数交叉'],evidence={'x':x})
    if i==6:
        x=.02*(n+1)
        return q('period-amphoteric-hydrogen','铝结构定位与碱中放氢',
          f'第三周期金属X的最高价氧化物既溶强酸也溶强碱，X单质{f(x)} mol与足量NaOH溶液反应，按生成[Al(OH)₄]⁻模型计。求X的原子序数、H₂产量及OH⁻净消耗量，并比较X³⁺和Mg²⁺半径。',
          pack('13',f'{f(1.5*x)} mol',f'{f(x)} mol','X³⁺更小'),
          [pack('12',f'{f(x)} mol',f'{f(2*x)} mol','X³⁺更大'),pack('13',f'{f(1.5*x)} mol',f'{f(3*x)} mol','X³⁺更小'),pack('13',f'{f(.5*x)} mol',f'{f(x)} mol','X³⁺更大')],
          f'氧化物两性的第三周期金属为Al，原子序数13。2Al+2OH⁻+6H₂O→2[Al(OH)₄]⁻+3H₂，放氢1.5x={f(1.5*x)} mol，OH⁻净消耗x={f(x)} mol。Al³⁺和Mg²⁺均10电子，Al核电荷更大半径更小。',
          ['以两性定位元素','区分络合计量与氢氧化物计量','等电子半径排序'],evidence={'x':x})
    a=.05*(n+1)
    return q('period-covalent-network','硅的结构性质与碱反应',
          f'第三周期元素X原子最外层电子数是次外层的一半，其最高价氧化物是共价网络固体。取此氧化物{f(a)} mol与足量热NaOH反应，求X名称、NaOH消耗量及产物阴离子中X价态；与CO₂相比，不能直接用分子间作用力解释其熔点更高的原因是什么？',
          pack('硅',f'{f(2*a)} mol','+4','SiO₂熔化涉及网络共价键'),
          [pack('碳',f'{f(a)} mol','+2','SiO₂分子更大'),pack('硅',f'{f(2*a)} mol','0','SiO₂熔化涉及网络共价键'),pack('硅',f'{f(a)} mol','+4','SiO₂仅有分子间作用力')],
          f'第三周期次外层8电子，价层4电子，为Si。SiO₂+2OH⁻→SiO₃²⁻+H₂O，耗碱{f(2*a)} mol，Si保持+4价。SiO₂是共价网络，CO₂为分子晶体，熔点比较必须先辨晶体结构，不能以“相对分子质量”一条规则概括。',
          ['由电子层约束定位','写净离子反应并守电荷','以结构层次解释宏观性质'],evidence={'a':a})


def ionic(i,n):
    s=1+n*.2
    if i==0:
        c=.002*s; K=1e-10; V=.05; cl=.004*s; Q=c*cl/4; need=2*sqrt(K/(c*cl))
        return q('ionic-precip-dilution','混合稀释与沉淀判据',
          f'将等体积{f(c)} mol/L AgNO₃和{f(cl)} mol/L NaCl混合，体积可加。Ksp(AgCl)=1.0×10⁻¹⁰。求刚混合未沉淀瞬间Q，并判断是否沉淀；若混合前把两液浓度各降为原来的k倍（0<k<1），求刚好不出现沉淀的k上限，按Q≤Ksp不沉淀。',
          pack(f'{f(Q)} (mol/L)²','会沉淀',f'{f(sqrt(K/Q))}'),
          [pack(f'{f(c*cl)} (mol/L)²','会沉淀',f'{f(K/Q)}'),pack(f'{f(Q)} (mol/L)²','不沉淀',f'{f(sqrt(K/Q))}'),pack(f'{f(Q)} (mol/L)²','会沉淀',f'{f(K/Q)}')],
          f'等体积混合使两离子浓度各减半，Q=cAg·cCl/4={f(Q)}>Ksp，沉淀。预稀释后Q′=k²Q，要求k≤√(Ksp/Q)={f(sqrt(K/Q))}。应先处理混合体积，再做离子积比较。',
          ['混合体积稀释','离子积与溶度积判别','由平方缩放反求边界'],evidence={'c':c,'cl':cl,'K':K})
    if i==1:
        al=.01*s; base=3.5*al; precip=.5*al; dissolved=.5*al
        return q('ionic-aluminium-piecewise','铝沉淀生成再溶解',
          f'向含{f(al)} mol Al³⁺的溶液逐滴加入NaOH，OH⁻共{f(base)} mol，按Al³⁺先定量沉淀、沉淀再以Al(OH)₃+OH⁻→[Al(OH)₄]⁻定量溶解的理想分段模型。求最后Al(OH)₃量、溶液中含铝阴离子量，及从此时起恰使沉淀全溶还需OH⁻多少？',
          pack(f'{f(precip)} mol',f'{f(dissolved)} mol',f'{f(precip)} mol'),
          [pack(f'{f(al)} mol','0 mol',f'{f(al)} mol'),pack('0 mol',f'{f(al)} mol','0 mol'),pack(f'{f(precip)} mol',f'{f(dissolved)} mol',f'{f(3*precip)} mol')],
          f'先耗3nAl={f(3*al)} mol OH⁻生成全部沉淀，剩OH⁻={f(.5*al)} mol，按1:1溶掉相同物质的量，沉淀和铝酸根各{f(.5*al)} mol；余沉淀再溶需等量OH⁻。不能把加入碱的全过程只按沉淀方程算。',
          ['确定沉淀区间边界','分配过量碱的二次反应','用铝守恒复核末态'],7,evidence={'al':al,'base':base})
    if i==2:
        carbonate=.02*s; acid=1.5*carbonate; gas=acid-carbonate; remain=2*carbonate-acid
        return q('ionic-carbonate-order','碳酸根分步质子化',
          f'向含{f(carbonate)} mol CO₃²⁻的溶液缓慢滴入HCl，总H⁺为{f(acid)} mol。按先CO₃²⁻全部变HCO₃⁻、再HCO₃⁻放CO₂的定量模型，CO₂及时逸出。求CO₂量和最终HCO₃⁻量；若把同量原碳酸盐缓慢滴入始终局部足量的该酸液，最多能先放多少CO₂？',
          pack(f'{f(gas)} mol',f'{f(remain)} mol',f'{f(acid/2)} mol'),
          [pack(f'{f(acid/2)} mol',f'{f(carbonate-acid/2)} mol',f'{f(acid/2)} mol'),pack(f'{f(gas)} mol',f'{f(remain)} mol',f'{f(gas)} mol'),pack('0 mol',f'{f(carbonate)} mol',f'{f(acid)} mol')],
          f'酸滴碳酸盐先耗nCO₃²⁻的H⁺形成HCO₃⁻，剩余{f(gas)} mol H⁺才放气，余HCO₃⁻={f(remain)} mol。反向滴加时每mol初到的CO₃²⁻先用2mol H⁺完全放气，酸耗尽前可放nH⁺/2={f(acid/2)} mol；明确的是局部足量、气体及时逸出的模型。',
          ['判断滴加顺序的分段计量','追踪两次质子化','对比反向滴加的局部过量'],7,evidence={'carbonate':carbonate,'acid':acid})
    if i==3:
        amount=.01*s; base=1.5*amount; sulf=amount; water=2*amount
        return q('ionic-barium-acid-salt','复合离子反应的双约束',
          f'把含{f(2*amount)} mol NaHSO₄的溶液与含{f(1.5*amount)} mol Ba(OH)₂的溶液混合，电解质完全电离，体积可加。忽略沉淀溶解与水电离。求BaSO₄沉淀量、剩余OH⁻量、剩余SO₄²⁻量。',
          pack(f'{f(1.5*amount)} mol',f'{f(amount)} mol',f'{f(.5*amount)} mol'),
          [pack(f'{f(amount)} mol','0 mol',f'{f(amount)} mol'),pack(f'{f(1.5*amount)} mol','0 mol',f'{f(.5*amount)} mol'),pack(f'{f(2*amount)} mol',f'{f(amount)} mol','0 mol')],
          f'独立核算：H⁺=2a，OH⁻=3a，中和后剩a；SO₄²⁻=2a，Ba²⁺=1.5a，钡为沉淀限量，产1.5a，余硫酸根0.5a。不能用一个固定的“1:1完全反应”方程覆盖所有配比。a={f(amount)} mol。',
          ['电离后分开核算酸碱与沉淀','两组限量条件分别判断','用电荷及原子余量复核'],7,evidence={'a':amount})
    if i==4:
        Fe=.01*s; sulfate=.02*s; Cl=.03*s; sodium=2*sulfate+Cl-3*Fe; base=3*Fe
        return q('ionic-charge-neutrality','电中性反推与沉淀余量',
          f'某溶液仅含Fe³⁺、Na⁺、SO₄²⁻、Cl⁻，其中Fe³⁺ {f(Fe)} mol、SO₄²⁻ {f(sulfate)} mol、Cl⁻ {f(Cl)} mol。忽略水解。加入恰使Fe³⁺完全沉淀的NaOH，求原有Na⁺量、NaOH用量和沉淀后溶液Na⁺总量。',
          pack(f'{f(sodium)} mol',f'{f(base)} mol',f'{f(sodium+base)} mol'),
          [pack(f'{f(sulfate+Cl-Fe)} mol',f'{f(Fe)} mol',f'{f(sulfate+Cl)} mol'),pack(f'{f(sodium)} mol',f'{f(base)} mol',f'{f(sodium)} mol'),pack(f'{f(sodium/2)} mol',f'{f(base)} mol',f'{f(sodium/2+base)} mol')],
          f'电中性3nFe+nNa=2nSO₄+nCl，原Na⁺={f(sodium)} mol。Fe³⁺+3OH⁻→Fe(OH)₃，需碱{f(base)} mol，同时新带入等量Na⁺，末Na⁺={f(sodium+base)} mol。沉淀去除铁不等于去除所有阳离子。',
          ['用带电荷系数的电中性','按沉淀计量求加入量','追踪旁观离子的新增'],evidence={'Fe':Fe,'sulfate':sulfate,'Cl':Cl})
    if i==5:
        ca=.02*s; co3=.03*s; V=.1; precip=ca; remaining=(co3-ca)/V; K=4e-9; free=K/remaining
        return q('ionic-common-ion','过量沉淀剂与残余离子',
          f'将含Ca²⁺ {f(ca)} mol的溶液与含CO₃²⁻ {f(co3)} mol的溶液混合，总体积100 mL，Ksp(CaCO₃)=4.0×10⁻⁹。忽略水解，先按完全沉淀计量，再用平衡估残余。求沉淀量近似值、平衡c(CO₃²⁻)近似值及c(Ca²⁺)近似值。',
          pack(f'{f(precip)} mol',f'{f(remaining)} mol/L',f'{f(free)} mol/L'),
          [pack(f'{f(precip)} mol',f'{f(remaining)} mol/L',f'{f(sqrt(K))} mol/L'),pack(f'{f(co3)} mol','0 mol/L','0 mol/L'),pack(f'{f(precip)} mol',f'{f(co3/V)} mol/L',f'{f(K/(co3/V))} mol/L')],
          f'Ca²⁺为限量，沉淀约{f(ca)} mol。CO₃²⁻剩{f(co3-ca)} mol，浓度约{f(remaining)} mol/L。由Ksp=cCa·cCO₃得cCa≈{f(free)} mol/L，远小于原浓度，近似自洽。有共同离子时不能用纯水溶解度√Ksp。',
          ['混合计量扣除沉淀剂消耗','识别共同离子条件','用Ksp估计并检查近似'],evidence={'ca':ca,'co3':co3,'V':V,'K':K})
    if i==6:
        M=.01*s; a=1e-12; b=1e-8; threshold1=sqrt(a/M); threshold2=sqrt(b/M); remaining=a/threshold2**2
        return q('ionic-selective-precip','选择性沉淀与除杂率',
          f'溶液中M²⁺、N²⁺初始浓度均{f(M)} mol/L，Ksp[M(OH)₂]=1.0×10⁻¹²，Ksp[N(OH)₂]=1.0×10⁻⁸。缓慢加碱，体积变化忽略且无络合。求哪种先沉淀、N刚开始沉淀时残余c(M²⁺)，以及M²⁺的去除百分率。',
          pack('M(OH)₂先',f'{f(remaining)} mol/L','99.99%'),
          [pack('N(OH)₂先',f'{f(remaining)} mol/L','99.99%'),pack('M(OH)₂先',f'{f(sqrt(a))} mol/L','90%'),pack('M(OH)₂先',f'{f(remaining)} mol/L','99%')],
          f'起沉[OH⁻]=√(Ksp/c金属)，M的阈值更低。N起沉时[OH⁻]²=KspN/cN，残余cM=KspM·cN/KspN={f(remaining)} mol/L，为初始1/10000，去除99.99%。比较Ksp只有在化学式、初浓度一致的前提下才可直接推顺序。',
          ['从Ksp推各起沉阈值','把第二种起沉条件代回第一种','按残余比例评估分离程度'],7,evidence={'c':M,'KM':a,'KN':b})
    a=.02*s; acid=.03*s; left=acid-a; V=.1
    return q('ionic-weak-acid','弱酸钠盐过量强酸与电荷',
          f'含CH₃COONa {f(a)} mol的溶液与含HCl {f(acid)} mol的溶液混合，总体积100 mL。按H⁺与CH₃COO⁻定量生成弱酸、剩余强酸抑制弱酸电离的近似模型。求c(H⁺)近似值、c(Na⁺)、c(Cl⁻)，并选择符合过程的净离子式。',
          pack(f'{f(left/V)} mol/L',f'{f(a/V)} mol/L',f'{f(acid/V)} mol/L','H⁺+CH₃COO⁻→CH₃COOH'),
          [pack(f'{f(acid/V)} mol/L',f'{f(a/V)} mol/L',f'{f(acid/V)} mol/L','H⁺+CH₃COO⁻→CH₃COOH'),pack(f'{f(left/V)} mol/L','0 mol/L',f'{f(acid/V)} mol/L','H⁺+OH⁻→H₂O'),pack('0 mol/L',f'{f(a/V)} mol/L',f'{f(a/V)} mol/L','H⁺+CH₃COO⁻→CH₃COOH')],
          f'先消耗H⁺与乙酸根各{f(a)} mol，剩强酸{f(left)} mol，cH≈{f(left/V)} mol/L。Na⁺旁观保留，Cl⁻全部保留，两者浓度分别{f(a/V)}、{f(acid/V)} mol/L，满足cH+cNa=cCl。弱酸CH₃COOH在净离子式中保留分子形式。',
          ['判定酸过量后的余量','追踪旁观离子和总体积','以电荷守恒检查净离子模型'],evidence={'a':a,'acid':acid,'V':V})


def derivative(i,n):
    if i==0:
        a=1+n*.5; low=-2*a**1.5; high=-low
        return q('cubic-root-count','含参三次函数零点个数',
          f'f(x)=x³−{f(3*a)}x+b，x∈R。求使f有三个不同实零点的b范围，以及在b取该范围右端点时的不同实零点个数和重根坐标。',
          pack(f'({f(low)}, {f(high)})','2个',f'x={f(sqrt(a))}'),
          [pack(f'[{f(low)}, {f(high)}]','3个',f'x={f(sqrt(a))}'),pack(f'({f(low)}, {f(high)})','2个',f'x=−{f(sqrt(a))}'),pack(f'({f(low/2)}, {f(high/2)})','1个','x=0')],
          f'f′=3(x²−a)，极大点−√a、极小点√a；极大值b+2a^(3/2)，极小值b−2a^(3/2)。要有三个不同零点，需前者>0、后者<0，因此严格区间{f(low)}<b<{f(high)}。上端点极小值恰0，x=√a为二重根，另有一单根，共2个不同根。',
          ['导数划分单调区间','把零点个数译为极值符号','分析等号时重根与不同根数'],7,evidence={'a':a})
    if i==1:
        k=1+n*.2; threshold=1+log(k); # ln x <= kx+b requires b>= -ln k-1
        bound=-1-log(k)
        return q('log-global-bound','对数恒成立与唯一等号点',
          f'对所有x>0，不等式ln x≤{f(k)}x+b恒成立。求b的最小值、取最小值时唯一等号点；若b比最小值小1，方程ln x={f(k)}x+b有几个正根？',
          pack(f'{f(bound)}',f'x={f(1/k)}','2个'),
          [pack(f'{f(-log(k))}',f'x={f(k)}','1个'),pack(f'{f(bound)}',f'x={f(1/k)}','0个'),pack(f'{f(1+log(k))}',f'x={f(k)}','2个')],
          f'令g=ln x−kx，g′=1/x−k，在x=1/k取全局最大−ln k−1={f(bound)}。恒成立需b不小于此最大值。低于最大值1的水平线与两侧严格单调且趋于−∞的曲线各交一次，共2正根。',
          ['恒成立转为全局最值','用导数及两端极限证明唯一最大','比较水平线求根数'],7,evidence={'k':k})
    if i==2:
        L=12+2*n; x=L/4; y=L/2; area=L*L/8; # add constraint y<= cap L/3 => constrained maximum x=L/3 y=L/3
        cap=L/3; xc=(L-cap)/2; Ac=xc*cap
        return q('fence-constrained','围栏优化与额外边界',
          f'长方形菜地一边靠墙，另三边围栏总长{L} m。令垂直墙的边为x，沿墙边为y。若另要求y≤{f(cap)} m，求最大面积及此时x；与没有此额外限制时最大面积相比减少多少？',
          pack(f'{f(Ac)} m²',f'{f(xc)} m',f'{f(area-Ac)} m²'),
          [pack(f'{f(area)} m²',f'{f(x)} m','0 m²'),pack(f'{f(Ac)} m²',f'{f(cap/2)} m',f'{f(area-Ac)} m²'),pack(f'{f(Ac/2)} m²',f'{f(xc)} m',f'{f(area-Ac/2)} m²')],
          f'2x+y=L，面积A(y)=y(L−y)/2，在0<y≤L/3上导数L/2−y>0，最大取边界y=L/3，x=L/3，面积L²/9={f(Ac)} m²。无约束最优y=L/2、面积L²/8，减少L²/72={f(area-Ac)} m²。驻点在可行域外必须舍弃。',
          ['从几何约束建单变量函数','先确定可行域再查驻点','比较受限与无约束最优'],evidence={'L':L})
    if i==3:
        L=12+n*3; x=L/6; vol=2*L**3/27
        return q('box-optimization','纸盒体积与有效定义域',
          f'边长{L} cm的正方形纸板，四角各剪去边长x的正方形后折成无盖盒。求最大体积及所需x；若工艺要求x≥{f(L/4)} cm，最大体积又为多少？忽略厚度。',
          pack(f'{f(vol)} cm³',f'{f(x)} cm',f'{f(L**3/16)} cm³'),
          [pack(f'{f(vol)} cm³',f'{f(L/3)} cm',f'{f(vol)} cm³'),pack(f'{f(L**3/8)} cm³',f'{f(L/4)} cm',f'{f(L**3/16)} cm³'),pack(f'{f(vol)} cm³',f'{f(x)} cm',f'{f(vol)} cm³')],
          f'V=x(L−2x)²，物理域0<x<L/2。V′=(L−2x)(L−6x)，有效驻点x=L/6，最大2L³/27={f(vol)}。工艺区间[L/4,L/2)全在下降段，最优是左端点L/4，体积L³/16={f(L**3/16)}。',
          ['由折叠几何写体积与定义域','导数符号判全局最优','额外工艺约束改变最优点'],evidence={'L':L})
    if i==4:
        a=1+n*.5; # f=x^3-3x^2+ax monotone interval require a>=3
        upper=3; minimum=3; at=1
        return q('interval-monotonicity','区间单调与参数临界',
          f'f(x)=x³−{f(3*a)}x²+bx，定义于[0,{f(2*a)}]。求f在该区间单调递增所需b的完整范围，以及取边界b时f′为零的点和函数是否仍严格递增。',
          pack(f'b≥{f(3*a*a)}',f'x={f(a)}','仍严格递增'),
          [pack(f'b>{f(3*a*a)}',f'x={f(a)}','等号时不递增'),pack(f'b≥{f(6*a*a)}','x=0','仍严格递增'),pack(f'b≤{f(3*a*a)}',f'x={f(a)}','不严格递增')],
          f'f′=3(x−a)²+b−3a²，区间含a，其最小值b−3a²。非负要求b≥3a²={f(3*a*a)}。边界时f′=3(x−a)²只在孤立一点为零，任意非退化区间上都有正导数部分，函数仍严格递增。必要性亦由a附近导数为负可证。',
          ['把单调条件化为导数恒非负','在给定区间求导数最小值','区分孤立零导数与常值区间'],7,evidence={'a':a})
    if i==5:
        a=1+n*.5; b=2+n; # y=x²+a passing P(0,-b), tangent t²=a+b
        t=sqrt(a+b); slope=2*t
        return q('external-tangents','过定点切线及切点排除',
          f'曲线y=x²+{f(a)}，求过P(0,−{b})的切线条数、两切点横坐标差及两条切线斜率之积。注意P不在曲线上，不可直接将P横坐标代入导数。',
          pack('2条',f'{f(2*t)}',f'{f(-4*(a+b))}'),
          [pack('1条','0','0'),pack('2条',f'{f(t)}',f'{f(-4*(a+b))}'),pack('2条',f'{f(2*t)}',f'{f(4*(a+b))}')],
          f'设切点横坐标t，切线y=2tx+a−t²。过P给a−t²=−b，即t=±√(a+b)。两切点横坐标相差2√(a+b)={f(2*t)}，斜率为±2√(a+b)，乘积−4(a+b)={f(-4*(a+b))}。',
          ['独立设未知切点','联立过点与切线条件','区分切点参数与定点坐标'],evidence={'a':a,'b':b})
    if i==6:
        a=1+n*.25; xmax=a; xmin=a-2; minval=4*exp(a-2)
        return q('exp-polynomial','指数多项式极值与水平交点',
          f'f(x)=(x−{f(a)})²eˣ，x∈R。求极大值点横坐标、极小值点横坐标，及方程f(x)=2e^({f(a-2)})的不同实根个数。这里“极大/极小值点”指局部极值，不是全局最大。',
          pack(f'x={f(a-2)}',f'x={f(a)}','3个'),
          [pack(f'x={f(a)}',f'x={f(a-2)}','2个'),pack(f'x={f(a-2)}',f'x={f(a)}','2个'),pack(f'x={f(a-2)}',f'x={f(a)}','1个')],
          f'f′=eˣ(x−a)(x−a+2)，符号依次+、−、+，因此a−2为极大值点，a为极小值点。极大值4e^(a−2)，极小值0；左端极限0，右端趋∞。题设水平线2e^(a−2)在0与极大值之间，三个单调区间各有一个交点。',
          ['乘积求导后判符号','区分局部极值与无界性','结合端点极限逐段数根'],7,evidence={'a':a})
    a=2+n; # x+a²/x on [1,a/2] then min endpoint a/2 = 2.5a, global2a
    cap=a/2
    return q('rational-domain-min','有理函数最值与参数可行域',
          f'f(x)=x+{a*a}/x，x>0。先求全定义域上的最小值及等号点；再把定义域限制为0<x≤{f(cap)}，求受限最小值和所有可能取值。',
          pack(f'{2*a}，x={a}',f'{f(2.5*a)}',f'[{f(2.5*a)}, +∞)'),
          [pack(f'{2*a}，x={a}',f'{2*a}',f'[{2*a}, +∞)'),pack(f'{2*a}，x={a}',f'{f(2.5*a)}',f'(0, {f(2.5*a)}]'),pack(f'{a*a+1}，x=1',f'{f(2.5*a)}',f'[{f(2.5*a)}, +∞)')],
          f'f′=1−a²/x²，先减后增，x=a取全局最小2a。受限上端a/2<a，全区间递减，最小值f(a/2)=a/2+2a=2.5a={f(2.5*a)}；x→0⁺时f→∞，值域闭于最小值、向上无界。',
          ['求导并定位驻点','剔除可行域外的等号点','由连续性与端点极限求值域'],evidence={'a':a})


BUILDERS = {
    'physics-kinematics': kinematics, 'physics-newton': newton,
    'physics-energy': energy, 'physics-electric': electric,
    'physics-induction': induction, 'chemistry-equilibrium': equilibrium,
    'chemistry-mole': mole, 'chemistry-redox': redox,
    'chemistry-periodic': periodic, 'chemistry-ionic': ionic,
    'math-derivative': derivative,
}
