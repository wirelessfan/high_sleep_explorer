"""独立复算发现小站的固定36题；不调用SVG或题库生成器。

数值/函数题按受力、分段运动、定义域和守恒复算；概念题列出人工核查依据。
--baseline REF 还会核对题干、选项、答案及奖励指纹未变，不访问生产数据库。
"""
import argparse
from fractions import Fraction as F
import hashlib
import json
import math
from pathlib import Path
import subprocess
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from app.services.reflections import fingerprint


def number(x):
    return f'{float(x):.6g}'


def verify(cfg):
    questions={q['id']:q for m in cfg['models'] for q in m['questions']}
    seen=set()

    def answer(qid, expected, reason):
        q=questions[qid]
        matches=[i for i,s in enumerate(q['options']) if s.replace('−','-')==expected.replace('−','-')]
        assert matches==[q['answer']],(qid,expected,q['options'],q['answer'])
        assert qid not in seen and reason
        seen.add(qid)

    # Newton's law; equal rope accelerations; length = constant.
    g=10
    a=(3-2)*g/(2+3); t=2*(g+a)
    answer('rope-1',f'分别列方程，共用 T={number(t)} N','T-2g=2a; 3g-T=3a')
    answer('rope-2',f'上端{number((1+2)*g)} N、下端{number(2*g)} N，绳有质量，不能套轻绳结论','isolate massive rope')
    answer('pulley-1',f'拉力{number(4*g/2)} N，自由端速率是物体2倍','2T=mg; end displacement=2h')
    answer('pulley-2',f'{number(6*(g+2)/2)} N、{number(2*2)} m/s²','2T-mg=ma; end acceleration=2a')
    assert 6<.5*2*g
    answer('friction-1',f'{number(6)} N，方向与推力相反','static horizontal equilibrium')
    assert 2*3<=.4*2*g<2*5
    answer('friction-2','a=3时需右向6 N可共速；a=5时需10 N超过8 N，不能保持','required m*a compared with maximum')
    a=10/(2+3)
    answer('system-1',f'{number(a)} m/s²、{number(3*a)} N','whole system acceleration, isolate B')
    assert 2*15/(2+3)<=.4*2*g<2*25/(2+3)
    answer('system-2','F=15 N可共速，F=25 N不能共速','common acceleration is only a trial assumption')
    answer('elevator-1',f'{number(50*(g-2))} N，失重','downward acceleration: mg-N=ma')
    answer('elevator-2',f'a向上，示数{number(60*(g+2))} N，重力{number(60*g)} N','downward deceleration means upward acceleration')
    stop=20/5; distance=20*stop/2
    answer('brake-1',f'{number(distance)} m，{number(stop)} s已停车，剩余时间静止','v clipped to zero after stopping')
    front=lambda t:10*min(t,5)-min(t,5)**2
    rear=lambda t:20*min(t,1)+20*max(0,min(t-1,4))-2.5*max(0,min(t-1,4))**2
    # Relative speed is positive before 5; include every segment boundary and stationary point.
    worst=max(rear(t)-front(t) for t in (0,1,5))
    assert all((20 if t<1 else max(0,25-5*t))-max(0,10-2*t)>=-1e-9 for t in [i/100 for i in range(501)])
    answer('brake-2',f'{number(worst)} m','maximum closure, strict gap greater than maximum')
    for qid,v0,acc,duration in [('vt-1',4,-2,4),('vt-2',-2,2,3)]:
        zero=-v0/acc
        displacement=v0*duration+acc*duration**2/2
        first=v0*zero+acc*zero**2/2
        length=abs(first)+abs(displacement-first)
        answer(qid,f'{number(displacement)} m、{number(length)} m','split integral of v and |v| at zero')

    # Definitions, actual function families and numerical witnesses across legal bases.
    answer('log-domain-1','a>1且a≠2，x>2','a-1>0, a-1!=1, x-2>0 (symbolic/manual condition review)')
    # Product is 1-(x-2)^2, so >=1 iff x=2; it lies in (1,3).
    assert (2-1)*(3-2)==1
    assert all((x-1)*(3-x)<1 for x in [1+i/100 for i in range(1,200) if i!=100])
    answer('log-domain-2','仅x=2','completed square: maximum 1 at vertex')
    for base in (.2,.5,.8):
        for x in [-.9+i*.01 for i in range(389) if abs(-.9+i*.01-1)>1e-8]:
            assert (math.log(x+1,base)<math.log(3-x,base))==(1<x<3)
    answer('log-base-1','1<x<3','decreasing log; x+1>3-x intersect (-1,3)')
    for x in [.51+i*.01 for i in range(449) if abs(.51+i*.01-2)>1e-8]:
        assert (math.log(2*x-1,.5)>=math.log(5-x,.5))==(.5<x<=2)
    assert math.log(3,.5)==math.log(3,.5)
    answer('log-base-2','1/2<x≤2','decreasing log; 2x-1<=5-x intersect (.5,5)')
    a=math.log(3,2)
    assert math.isclose(math.log(4,6),2/(1+a))
    answer('log-change-1','2/(1+a)','change base to 2; log2(6)=1+a')
    x,y=math.log(6,2),math.log(6,3)
    answer('log-change-2',number(1/x+1/y),'reciprocal logarithms, common base 6')
    for base in (.25,.5,2,3,4,10):
        assert math.log(3-2,base)+3==3
        assert math.log(2*1-1,base)-2==-2
    answer('log-fixed-1','(3,3)','x-2=1, y=3, domain x>2')
    answer('log-fixed-2','(1,−2)，x>1/2','2x-1=1, y=-2, domain x>.5')
    sin=F(3,5); cos=-F(4,5)
    assert sin*sin+cos*cos==1
    answer('trig-sign-1',f'{cos}、{sin/cos}','quadrant II chooses negative square root')
    for angle in [math.pi*i/200 for i in range(1,100)]:
        assert math.isclose(math.sin(math.pi/2+angle)*math.cos(math.pi+angle),-math.cos(angle)**2,abs_tol=1e-12)
    answer('trig-sign-2','−cos²α','angle addition identities and sign in quadrants II/III')

    # Stoichiometry, ions, electron and nuclear counts (rational arithmetic).
    answer('gas-volume-1','水此时通常为液态，不能用气体摩尔体积','manual: water is not gas; 0C ice/liquid detail does not affect conclusion')
    amount=F('4.48')/F('22.4'); atoms=amount*(F(1,4)*2+F(3,4)*3)
    answer('gas-volume-2',number(atoms)+'NA','same T,p: volume fraction=mole fraction')
    answer('concentration-1','不能，100 mL是水体积而非最终溶液体积','manual: missing final solution volume')
    cl=F('.1')*1+F('.2')*F('.5')*2
    answer('concentration-2',number(cl/F('.3'))+' mol/L','sum chloride amounts / additive final volume')
    extent=min(F('.1')/2,F('.2')/6)
    assert extent==F('.2')/6
    answer('limiting-1','HCl，'+number(extent*3)+' mol','min(n/coefficient)')
    needed=2*F('.1')+3*F('.1'); available=F('.4')
    assert available<needed
    # Multiple feasible allocations consume the same acid, so leftovers are not unique.
    assert 2*F('.05')+3*F('.1')==available==2*F('.1')+3*F(1,15)
    answer('limiting-2',f'酸不足，H₂为{number(available/2)} mol，但各金属剩余量不能唯一确定','H+ conservation and nonunique metal allocation')
    # Manually check solid state, spectator removal, atom and charge conservation.
    answer('ionic-1','CaCO₃(s)+2H⁺→Ca²⁺+CO₂↑+H₂O','manual: retain insoluble solid, remove spectator chloride; atom/charge balance')
    precip=min(F('.1'),F('.075')); hydroxide=2*F('.075')-F('.1')
    answer('ionic-2',f'{number(precip)} mol、{number(hydroxide)} mol','separate precipitation and neutralization limits')
    # 2 Cl atoms: one oxidation 0->+1, one reduction 0->-1, per Cl2 formula unit.
    electrons=F(2)*F(1,2)*1
    answer('redox-1',number(electrons)+' mol','count loss OR gain, do not add')
    converted=min(F('.1'),F('.03')*2)
    answer('redox-2',f'{number(converted)} mol、{number(F(".1")-converted)} mol','electron budget 2Fe2+ per Cl2')
    z=10+1; neutron=23-z
    assert z==11
    answer('periodic-1',f'Na、{neutron}','10-electron positive ion -> Z11; N=A-Z')
    particles=[('O²⁻',8,2),('F⁻',9,1),('Na⁺',11,-1),('Mg²⁺',12,-2)]
    assert all(z+excess==10 for _,z,excess in particles)
    answer('periodic-2','>'.join(name for name,z,_ in sorted(particles,key=lambda p:p[1])),'manual trend: isoelectronic simple ions, larger Z -> smaller r')
    assert seen==set(questions)
    return len(seen)


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--baseline',help='optional Git ref for identity/fingerprint comparison')
    args=parser.parse_args()
    cfg=json.loads((ROOT/'content/exam_training.json').read_text(encoding='utf-8'))
    # Input lock prevents a changed question silently using the old hardcoded calculation.
    inputs=[{k:q[k] for k in ('id','stem','options','answer')} for m in cfg['models'] for q in m['questions']]
    digest=hashlib.sha256(json.dumps(inputs,ensure_ascii=False,sort_keys=True).encode()).hexdigest()
    assert digest=='1648021ec1ea9dacbb62e25fe7bdf7f9a83d3475ac8521b12f6d5339153ea072', 'Question inputs changed; independently review and update calculations'
    count=verify(cfg)
    if args.baseline:
        old=json.loads(subprocess.check_output(['git','show',args.baseline+':content/exam_training.json'],cwd=ROOT))
        previous={q['id']:q for m in old['models'] for q in m['questions']}
        for m in cfg['models']:
            for q in m['questions']:
                assert all(q[k]==previous[q['id']][k] for k in ('stem','options','answer'))
                assert fingerprint(q)==fingerprint(previous[q['id']]),q['id']
        print('36 question identities and reward fingerprints unchanged')
    print(f'{count} discovery answers verified; concept/state assumptions also require human review')
