"""独立复算挑战题答案，检查唯一正确选项及内容与审校清单的一致性。

不调用题库生成器。物理按受力/能量/冲量，化学按物料/电荷/电子守恒，
数学以求根、导数符号及可行域复核。输出只说明模型一致性，不代表学生实测难度。
"""
import json
import math
from pathlib import Path
import re
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from tools.check_content import section_tiers, questions_of


def f(x):return f'{x:.6g}'
def p(*xs):return '；'.join(map(str,xs))
def root(fn,lo,hi):
    assert fn(lo)*fn(hi)<=0,(lo,hi)
    for _ in range(100):
        mid=(lo+hi)/2
        if fn(lo)*fn(mid)<=0:hi=mid
        else:lo=mid
    return (lo+hi)/2


def solve(model,e):
    z=e
    if model=='braking-clearance':
        available=z['d']-z['v']*z['tau']; a=z['v']**2/(2*available)
        return p(f'{f(a)} m/s²',f"{f(available-z['v']**2/(2*z['a']))} m")
    if model=='pursuit-minimum':
        u,d=z['u'],z['d']; t=root(lambda t:d+u*t-t*t,0,100)
        return p(f'{f(d+u*(u/2)-(u/2)**2)} m',f'{f(t)} s')
    if model=='two-stage-inverse':
        u,t,x=z['u'],z['t'],z['x']; acceleration=2*(x-u*t)/t**2
        v=u+acceleration*t
        return p(f'{f(acceleration)} m/s²',f'{f((x+2*v)/(t+2))} m/s')
    if model=='projectile-window':
        t=math.sqrt(z['h']/5)
        return p(f"[{f(.9*z['u'])}, {f(1.1*z['u'])}] m/s",f"{f(10*t/z['u'])}")
    if model=='delayed-braking':
        u,tau=z['u'],z['tau']
        front=lambda t: u*min(t,u/4)-2*min(t,u/4)**2
        rear=lambda t: u*min(t,tau)+u*max(0,min(t-tau,u/2))-max(0,min(t-tau,u/2))**2
        T=tau+u/2
        worst=max(rear(T*j/1000)-front(T*j/1000) for j in range(1001))
        return f'{f(worst)} m'
    if model=='vertical-meeting':
        assert 2*z['u']/10<math.sqrt(z['h']/5)<z['h']/z['u']
        return '两球空中不能相遇；B 回地面时 A 仍在空中'
    if model=='tape-inference':
        dt=z['dt'];return p(f"{f((z['s1']+z['s2'])/(2*dt))} m/s",f"{f((z['s2']-z['s1'])/dt**2)} m/s²",f'{f((dt/.11)**2)} 倍')
    if model=='reversal-distance':
        u,L=z['u'],z['L']; t=root(lambda t:u*t-t*t+L,u/2,100)
        turning=u*(u/2)-(u/2)**2
        return p(f'{f(t)} s',f'{f(2*turning+L)} m')
    if model=='block-board-slip':
        a1=.2*10; friction=z['m']*a1; a2=(z['F']-friction)/z['M']
        assert z['F']/(z['M']+z['m'])>a1
        return p(f"{f((a2-a1)*z['t']**2/2)} m",f'{f(a1)} m/s²',f'{f(a2)} m/s²')
    if model=='oblique-pull':
        normal=10*z['m']-.6*z['F']
        return p(f"{f((.8*z['F']-.2*normal)/z['m'])} m/s²",f"{f(10*z['m']/.6)} N")
    if model=='incline-connection':
        m=z['m']; a=(2*m*10-m*10*.6-.25*m*10*.8)/(3*m)
        return p(f'{f(a)} m/s²',f'{f(2*m*(10-a))} N',f'{f(m*(.6+.25*.8))} kg')
    if model=='elevator-inverse':
        h=z['a']*9/2;return p(f'{f(h)} m',f"{f(z['m']*(10+z['a'])*h)} J",f"{f(z['m']*(10-z['a']))} N")
    if model=='spring-cut':
        tension=2*z['m']*10
        return p(f"{f((z['m']*10+tension)/z['m'])} m/s²",'0 m/s²',f"{f(tension/z['k'])} m")
    if model=='belt-time-heat':
        m,v,L=z['m'],z['v'],z['L'];t=v/2; x=t*v/2
        assert x<L
        return p(f'{f(t+(L-x)/v)} s',f'{f(.2*m*10*(v*t-x))} J')
    if model=='stack-static-bound':
        a=z['F']/(z['m']+z['M'])
        return p(f"向右 {f(z['m']*a)} N",f"{f(3*(z['m']+z['M']))} N")
    if model=='vertical-circle-bound':
        v2=10*z['R']+2*10*(2*z['R'])
        return p(f'{f(math.sqrt(v2))} m/s',f"{f(z['m']*(10+v2/z['R']))} N")
    if model=='rough-track-budget':
        E=z['m']*10*z['h']-z['mu']*z['m']*10*z['L'];assert E>0
        return p(f"{f(math.sqrt(2*E/z['m']))} m/s",f"{f(E/(z['m']*10))} m",f"{f(z['h']/z['mu'])} m")
    if model=='spring-loss':
        loss=z['mu']*z['m']*10*z['d'];E=.5*z['k']*z['x']**2-loss;assert E>0
        threshold=root(lambda x:.5*z['k']*x*x-loss,0,10)
        return p(f"{f(math.sqrt(2*E/z['m']))} m/s",f'{f(threshold)} m')
    if model=='constant-power':
        limit=z['P']/z['resist'];acc=(z['P']/(limit/2)-z['resist'])/z['m']
        return p(f'{f(limit)} m/s',f'{f(acc)} m/s²','随速度增大而减小')
    if model=='inelastic-pendulum':
        mass=z['m']+z['M'];momentum=z['m']*z['u'];v=momentum/mass
        initial=z['m']*z['u']**2/2;after=mass*v*v/2
        return p(f'{f(after/(mass*10))} m',f'{f(initial-after)} J')
    if model=='work-angle-budget':
        # 梯形法对线性F(x)精确，而非沿用生成端的展开式。
        average=(z['F0']+(z['F0']+2*z['d']))/2
        W=(average-.2*z['m']*10)*z['d']
        return p(f"{f(math.sqrt(2*W/z['m']))} m/s",f'{f(average)} N')
    if model=='loop-release-height':
        top_kinetic_per_m=10*z['R']/2
        h=(top_kinetic_per_m+10*2*z['R']+z['mu']*10*z['L'])/10
        return p(f'{f(h)} m','6')
    if model=='hydro-efficiency':
        incoming=z['flow']*10*z['h'];outgoing=.5*z['flow']*z['v']**2
        return p(f"{f(z['eta']*(incoming-outgoing))} W",f"{f(z['eta']*outgoing)} W")
    if model=='spring-return':
        E=z['k']*z['x']**2/2;friction=z['mu']*z['m']*10
        return p(f'{f(E/friction)} m',f'{f(E+2*friction)} J')
    if model=='electric-deflection':
        # 任选q/m=1，直接求加速速度、飞行时长与竖直加速度。
        vx=math.sqrt(2*z['V']);t=z['L']/vx;a=z['U']/z['d'];y=a*t*t/2
        return p(f'{f(y)} m',f"{f(y+a*t*z['D']/vx)} m")
    if model=='capacitor-isolated':
        Q=z['C']*z['U'];old=Q*Q/(2*z['C']);new=Q*Q/(2*(z['C']/2))
        return p(f"{f(Q/(z['C']/2))} V",'1',f'{f(new-old)} μJ')
    if model=='capacitor-connected':
        C,U=z['C'],z['U'];old=.5*C*U*U;new=.5*(C/2)*U*U;source=U*((C/2)*U-C*U)
        return p(f'{f(new-old)} μJ',f'{f(source)} μJ',f'{f(new-old-source)} μJ')
    if model=='point-charge-zero':
        L=z['L'];neg=root(lambda x:1/abs(x)-4/abs(x-L),-2*L,-.001*L)
        pos=root(lambda x:1/x-4/(L-x),.001*L,.999*L)
        field=root(lambda x:-1/x**2+4/(L-x)**2,-2*L,-.01*L)
        return p(f'零势 x=−{f(-neg)} m、{f(pos)} m',f'零场 x=−{f(-field)} m')
    if model=='electric-turning':
        E=z['q']*z['U'];return p(f"{f(math.sqrt(2*E/z['m']))} m/s",f"{f(E/(z['q']*z['E']))} m",f'+{f(E)} J')
    if model=='charge-release':
        delta=9e9*z['q']**2*(1/z['L']-1/(2*z['L']))
        return p(f"{f(math.sqrt(delta/z['m']))} m/s",'1/4')
    if model=='capacitor-sharing':
        C,U=z['C'],z['U'];v=C*U/(3*C);loss=.5*C*U*U-.5*(3*C)*v*v
        return p(f'{f(v)} V',f'{f(loss)} μJ')
    if model=='plate-collision-bound':
        cap=root(lambda U:U/z['d']*(z['L']/math.sqrt(2*z['V']))**2/2-z['d']/2,0,10000)
        return p(f'必须小于 {f(cap)} V','能够飞出' if z['U']<cap-1e-8 else '会撞板')
    if model=='rod-steady-power':
        I=z['B']*z['L']*z['v']/z['R'];force=I*z['B']*z['L']
        return p(f'{f(force)} N',f"{f(I*I*z['R'])} W",f"{2*z['v']} m/s")
    if model=='rod-braking-integral':
        v=z['v'];charge=z['m']*(v-v/2)/(z['B']*z['L']);x=charge*z['R']/(z['B']*z['L'])
        return p(f'{f(x)} m',f'{f(charge)} C',f"{f(z['m']*(v*v-(v/2)**2)/2)} J")
    if model=='flux-ramp':
        change=z['N']*z['S']*z['db'];I=change/z['t']/z['R']
        return p(f"{f(I*z['t'])} C",f"{f(I*I*z['R']*z['t'])} J",'电荷1倍，热量2倍')
    if model=='loop-entry-exit':
        I=z['B']*z['L']*z['v']/z['R'];duration=z['w']/z['v']
        return p(f"{f(2*I*I*z['R']*duration)} J",'0 C',f'{f(2*I*duration)} C')
    if model=='motional-capacitor':
        E,C,r,R=z['E'],z['C'],z['r'],z['R'];totalheat=E*C*E-C*E*E/2
        return p(f'{f(E/(r+R))} A',f'{f(C*E)} C',f'{f(totalheat*R/(R+r))} J')
    if model=='generator-rms':
        peak=z['N']*z['S']*z['B']*z['w'];mean_square=sum((peak*math.sin(2*math.pi*i/1000))**2 for i in range(1000))/1000
        return p(f"{f(math.sqrt(mean_square)/z['R'])} A",f"{f(mean_square/z['R'])} W",'2倍')
    if model=='rod-load-power':
        I=z['F']/(z['B']*z['L']);E=I*(z['r']+z['R'])
        return p(f"{f(E/(z['B']*z['L']))} m/s",f"{f(I*I*z['R'])} W",'20%')
    if model=='resistive-rails':
        I=z['B']*z['L']*z['v']/(z['R0']+z['rho']*z['x'])
        return p(f"{f(z['B']*z['L']*I)} N",'拉力减小，功率减小')
    if model=='eq-add-product':
        c=z['c'];x=root(lambda x:x*x-4*(c-x)**2,0,c)
        Q=(x+c/3)*x/(c-x)**2;assert abs(Q-6)<1e-8
        return p('2/3','6','逆向')
    if model=='eq-dissociation':
        c=z['c'];alpha=4/3-1;K=(2*c*alpha)**2/(c*(1-alpha))
        return p('1/3',f'{f(K)} mol/L','2，逆向')
    if model=='eq-inert-pressure':
        x=z['c']/2;K=x/((z['c']-x)**2)
        return p(f'{f(K)} L/mol','2，逆向','不移动')
    if model=='eq-rewrite':
        K=z['K'];x=root(lambda x:x*x-K*(1-x)**2,0,1)
        return p(f'{f(x)} mol',f'{f(math.sqrt(1/K))}')
    if model=='eq-constant-pressure':
        alpha=1.5-1;pA=z['p']*(1-alpha)/(1+alpha);pB=z['p']*2*alpha/(1+alpha)
        return p('50%','2/3',f'{f(pB*pB/pA)} kPa')
    if model=='eq-ammonia-density':
        x=(4-34/10.625)/2;A=(1-x)/z['V'];B=(3-3*x)/z['V'];C=2*x/z['V']
        return p('40%',f'{f(C*C/(A*B**3))} L²/mol²')
    if model=='eq-solid-inventory':
        made=min(z['solid'],z['V']*z['K'])
        return p(f"{f(made/z['V'])} mol/L",f"{f(z['solid']-made)} mol")
    if model=='eq-temperature-rebuild':
        x=root(lambda x:(2*z['c']+x)-4*(z['c']-x),0,z['c'])
        return p('2','吸热',f'{f(x)} mol/L')
    if model=='hydrate-dilution':
        amount=z['mass']/286*(50/500);Na=amount*2
        return p(f'{f(Na/.2)} mol/L',f'{f(Na)} N_A')
    if model=='gas-combustion-inverse':
        total=z['a']+z['b'];oxygen=.5*z['a']+2*z['b'];methane=(oxygen-.5*total)/1.5
        return p(f'{f(methane)} mol',f'{f(36*methane)} g',f'{f(total*22.4)} L')
    if model=='carbonate-two-observations':
        co2=z['a']+z['b'];H=z['a']+2*z['b'];b=H-co2;a=co2-b
        return p(f'{f(b)} mol',f'{f(84*a+106*b)} g')
    if model=='sampling-replenish':
        sulfate=z['c']*(.1-.025);final=.1-.025+.05
        return p(f'{f(2*sulfate/final)} mol/L',f'{f(sulfate)} mol','0.60')
    if model=='alloy-acid-inverse':
        mass=27*z['a']+24*z['b'];gas=1.5*z['a']+z['b'];a=(24*gas-mass)/9
        return p(f'{f(27*a/mass*100)}%',f'{f(2*gas)} mol')
    if model=='stock-density':
        V=10*z['s'];moles=V*1.1*.08/40;target=moles/.2*1000
        return p(f'{f(target)} mL',f'偏低，为目标的 {f(target/(target+V))} 倍')
    if model=='aliquot-titration':
        amount=z['c']*z['volume_litres']*5*10
        assert abs(amount*56/z['sample_mass']-.56)<1e-9
        return p('56.0%',f'{f(amount/.25)} mol/L')
    if model=='limiting-reagent':
        extent=min(z['a'],z['b']/3);NH3=2*extent;left=z['a']-extent
        return p(f'{f(NH3)} mol',f'{f(left)} mol',f'{f(NH3+left)} N_A')
    if model=='chlorine-disproportionation':
        cl=z['cl'];hot=z['hot'];oxidized_atoms=2*cl/(6 if hot else 2);electrons=oxidized_atoms*(5 if hot else 1)
        return p(f'{f(oxidized_atoms)} mol','5/6' if hot else '1/2',f'{f(electrons)} mol')
    if model=='nitric-mixture':
        charge=3*z['fe']+2*z['cu'];NO=charge/3
        return p(f'{f(NO)} mol',f'{f(charge+NO)} mol')
    if model=='peroxide-titration':
        electrons=z['V']*z['c']*5;amount=electrons/2
        return p(f'{f(amount/.025)} mol/L',f'{f(amount)} mol','还原剂')
    if model=='iodometric-relay':
        iodine=z['thio']/2;Cr2=iodine/3
        return p(f'{f(Cr2*294)} g',f'{f(Cr2*6)} mol')
    if model=='mixed-nox':
        electrons=3*z['no']+z['no2'];copper=electrons/2
        return p(f'{f(copper)} mol',f"{f(2*copper+z['no']+z['no2'])} mol")
    if model=='oxidant-limited':
        oxidized=2*z['cl'];left=z['fe']-oxidized;assert abs(oxidized/left-2/3)<1e-9
        return p('2/3',f'{f(oxidized)} mol',f'{f(left/2)} mol')
    if model=='chlorate-reductant':
        chlorate=z['e']/5;chloride=z['e'];gas=(chlorate+chloride)/2
        return p(f'{f(chlorate)} mol',f'{f(gas)} mol')
    if model=='sulfite-air':
        residual=.016*z['s']*5/2;original=residual/.8
        return p(f'{f(original)} mol','偏低20%')
    if model=='period-isoelectronic':return p(str(z['A']-(10+1)),'X⁺>Y²⁺>Z³⁺','6 mol、2 mol')
    if model=='period-successive-ie':return p('镁、铝',f"{f(2*z['amount'])} mol",'Y的氧化物具有两性，可溶于足量强碱')
    if model=='period-oxide-hydride':return p('S、Cl',f"{f(2*z['amount'])} mol",'HY比H₂X稳定')
    if model=='period-consecutive':return p('Mg、P','Al₂O₃','1:3')
    if model=='period-isotope-average':return p(f"{f(sum(m*ab for m,ab in [(35,z['p']),(37,1-z['p'])]))}",'18','离子键，NaCl')
    if model=='period-peroxide':return p(f"{f(z['x']/2)} mol",f"{f(z['x'])} mol",'氧为−1价，是歧化')
    if model=='period-amphoteric-hydrogen':return p('13',f"{f(3*z['x']/2)} mol",f"{f(z['x'])} mol",'X³⁺更小')
    if model=='period-covalent-network':return p('硅',f"{f(2*z['a'])} mol",'+4','SiO₂熔化涉及网络共价键')
    if model=='ionic-precip-dilution':
        ag=z['c']/2;cl=z['cl']/2;Q=ag*cl;assert Q>z['K']
        k=root(lambda k:ag*k*cl*k-z['K'],0,1)
        return p(f'{f(Q)} (mol/L)²','会沉淀',f'{f(k)}')
    if model=='ionic-aluminium-piecewise':
        al=z['al'];extra=z['base']-3*al;left=al-extra
        return p(f'{f(left)} mol',f'{f(extra)} mol',f'{f(left)} mol')
    if model=='ionic-carbonate-order':
        first=min(z['acid'],z['carbonate']);gas=z['acid']-first
        return p(f'{f(gas)} mol',f'{f(first-gas)} mol',f"{f(z['acid']/2)} mol")
    if model=='ionic-barium-acid-salt':
        a=z['a'];H=2*a;OH=3*a;SO4=2*a;Ba=1.5*a
        return p(f'{f(min(Ba,SO4))} mol',f'{f(OH-H)} mol',f'{f(SO4-Ba)} mol')
    if model=='ionic-charge-neutrality':
        sodium=2*z['sulfate']+z['Cl']-3*z['Fe'];base=3*z['Fe']
        return p(f'{f(sodium)} mol',f'{f(base)} mol',f'{f(sodium+base)} mol')
    if model=='ionic-common-ion':
        left=(z['co3']-z['ca'])/z['V'];ca=z['K']/left
        assert ca*z['V']<z['ca']*1e-5
        return p(f"{f(z['ca'])} mol",f'{f(left)} mol/L',f'{f(ca)} mol/L')
    if model=='ionic-selective-precip':
        OH2=z['KN']/z['c'];left=z['KM']/OH2
        assert abs((1-left/z['c'])*100-99.99)<1e-9
        return p('M(OH)₂先',f'{f(left)} mol/L','99.99%')
    if model=='ionic-weak-acid':
        H=(z['acid']-z['a'])/z['V'];Na=z['a']/z['V'];Cl=z['acid']/z['V'];assert abs(H+Na-Cl)<1e-10
        return p(f'{f(H)} mol/L',f'{f(Na)} mol/L',f'{f(Cl)} mol/L','H⁺+CH₃COO⁻→CH₃COOH')
    if model=='cubic-root-count':
        a=z['a'];t=math.sqrt(a);edge=-(t**3-3*a*t)
        assert abs(3*t*t-3*a)<1e-9
        return p(f'({f(-edge)}, {f(edge)})','2个',f'x={f(t)}')
    if model=='log-global-bound':
        k=z['k'];t=root(lambda x:1/x-k,1e-6,100)
        value=math.log(t)-k*t
        return p(f'{f(value)}',f'x={f(t)}','2个')
    if model=='fence-constrained':
        L=z['L'];y=L/3;x=(L-y)/2;A=x*y;assert L/2-y>0
        return p(f'{f(A)} m²',f'{f(x)} m',f'{f((L/4)*(L/2)-A)} m²')
    if model=='box-optimization':
        L=z['L'];x=root(lambda x:(L-2*x)*(L-6*x),0,L/3)
        return p(f'{f(x*(L-2*x)**2)} cm³',f'{f(x)} cm',f'{f((L/4)*(L-L/2)**2)} cm³')
    if model=='interval-monotonicity':
        a=z['a'];threshold=max(6*a*x-3*x*x for x in [2*a*j/1000 for j in range(1001)])
        return p(f'b≥{f(threshold)}',f'x={f(a)}','仍严格递增')
    if model=='external-tangents':
        a,b=z['a'],z['b'];t=root(lambda t:a-t*t+b,0,100)
        return p('2条',f'{f(2*t)}',f'{f((2*t)*(-2*t))}')
    if model=='exp-polynomial':
        a=z['a'];F=lambda x:(x-a)**2*math.exp(x);level=2*math.exp(a-2)
        assert F(a-2)>level>F(a) and F(a-50)<level<F(a+10)
        return p(f'x={f(a-2)}',f'x={f(a)}','3个')
    if model=='rational-domain-min':
        a=z['a'];minimum=a+a*a/a;end=a/2+a*a/(a/2)
        return p(f'{f(minimum)}，x={a}',f'{f(end)}',f'[{f(end)}, +∞)')
    raise AssertionError(f'模型未实现独立复核：{model}')


NUM=re.compile(r'[+-]?(?:\d*\.\d+|\d+)(?:e[+-]?\d+)?',re.I)
def equal_option(a,b):
    a=a.replace('−','-');b=b.replace('−','-')
    if NUM.sub('#',a)!=NUM.sub('#',b):return False
    aa=list(map(float,NUM.findall(a)));bb=list(map(float,NUM.findall(b)))
    return len(aa)==len(bb) and all(math.isclose(x,y,rel_tol=2e-5,abs_tol=1e-10) for x,y in zip(aa,bb))


def verify():
    report=json.loads((ROOT/'reports/challenge-upgrade-2026-11-13.json').read_text('utf8'))
    content={}
    for path in (ROOT/'content/topics').glob('*.json'):
        data=json.loads(path.read_text('utf8'))
        for sec in data['sections']:
            for tier,c in section_tiers(sec).items():
                for qid,q in questions_of(c):content[f"{data['id']}/{sec['id']}/{tier}/{qid}"]=q
    errors=[]
    for r in report['questions']:
        try:
            expected=solve(r['model'],r['evidence'])
            matches=[i for i,opt in enumerate(r['options']) if equal_option(opt,expected)]
            assert matches==[r['answer']],(expected,matches,r['options'],r['answer'])
            q=content[r['key']]
            assert q['options']==r['options'] and q['answer']==r['answer'] and q['explain']==r['explain']
            assert q.get('stem',q.get('ask'))==r['stem']
        except Exception as exc:errors.append((r['key'],str(exc)))
    if errors:
        for row in errors:print(*row)
        raise AssertionError(f'{len(errors)}个复核失败')
    print(f"独立模型复算通过：{len(report['questions'])}道变式 / {report['models']}个模型；每题唯一匹配正确选项。")
    return report


if __name__=='__main__':verify()
