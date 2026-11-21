/* 动量守恒 & 机械能守恒：双主题 5 场互动探索实验室 */

import { el } from '../ui.js';
import { navigate } from '../router.js';
import { mountLabBonus } from '../lab-bonus.js';
import { canvasHud, FS } from '../lab-canvas.js';

const LAB_CSS = `
.melab{display:flex;flex-direction:column;gap:12px}
.melab .me-pill{display:inline-flex;align-items:center;gap:6px;padding:5px 11px;border-radius:999px;background:#fff;border:1px solid var(--line);font-size:12px;font-weight:700;color:var(--ink-2)}
.melab .me-dot{width:8px;height:8px;border-radius:50%;background:#d6c7b2;transition:background .2s}
.melab .me-dot.done{background:#059669}
.melab .me-themes,.melab .me-tabs{display:flex;flex-wrap:wrap;gap:7px}
.melab .me-tbtn{appearance:none;border:1px solid var(--line);background:#fff;color:var(--ink-2);padding:8px 13px;border-radius:12px;font-size:12.5px;font-weight:800;cursor:pointer}
.melab .me-tbtn.active{background:#eff6ff;border-color:#2563eb;color:#2563eb}
.melab .me-tbtn.ene.active{background:#ecfdf5;border-color:#059669;color:#059669}
.melab .me-tbtn.sum.active{background:#fffbeb;border-color:#b45309;color:#b45309}
.melab .me-tab{appearance:none;border:1px solid var(--line);background:#fff;color:var(--ink-2);padding:6px 12px;border-radius:999px;font-size:12px;font-weight:700;cursor:pointer;display:inline-flex;align-items:center;gap:5px}
.melab .me-tab.active{background:#5a463a;border-color:#5a463a;color:#fffdf8}
.melab .me-tab .chk{font-size:10.5px;padding:1px 5px;border-radius:999px;background:#ecfdf5;color:#059669}
.melab .me-tab.active .chk{background:rgba(255,255,255,.22);color:#fff}
.melab .me-predict{background:#faf6ef;border:1px dashed #dfcfb7;border-radius:12px;padding:11px 12px;margin:10px 0 12px}
.melab .me-predict-q{font-size:13px;font-weight:800;margin:0 0 8px;color:var(--ink)}
.melab .me-opts{display:flex;flex-wrap:wrap;gap:7px}
.melab .me-opt{appearance:none;background:#fff;border:1px solid #dfd2be;color:var(--ink-2);padding:6px 11px;border-radius:9px;font-size:12px;font-weight:700;cursor:pointer}
.melab .me-opt.picked{background:#eff6ff;border-color:#2563eb;color:#2563eb}
.melab .me-stage{border-radius:12px;overflow:hidden;border:1px solid var(--line);background:#fcfaf5;margin-bottom:12px}
.melab .me-stage canvas{display:block;width:100%;height:auto;touch-action:none}
.melab .me-ctrl{display:flex;flex-wrap:wrap;align-items:center;gap:10px 18px;padding:10px 12px;background:#faf7f2;border-radius:12px;border:1px solid var(--line);margin-bottom:10px}
.melab .me-range{display:flex;align-items:center;gap:8px;flex:1 1 240px;min-width:220px}
.melab .me-range label{font-size:12px;font-weight:700;color:var(--ink-2);white-space:nowrap}
.melab .me-range input{flex:1;min-width:80px;cursor:pointer}
.melab .me-val{font-size:12px;font-weight:800;color:#2563eb;min-width:64px;text-align:right;white-space:nowrap;font-variant-numeric:tabular-nums}
.melab .me-tasks{display:flex;flex-wrap:wrap;gap:7px;margin-bottom:4px}
.melab .me-task{font-size:11.5px;font-weight:700;padding:4px 10px;border-radius:9px;background:#f5f0e7;color:var(--ink-3)}
.melab .me-task.done{background:#ecfdf5;color:#059669;border:1px solid #a7f3d0}
.melab .me-insight{margin-top:12px;padding:14px;border-radius:13px;background:linear-gradient(135deg,#f0fdf4 0%,#eff6ff 100%);border:1px solid #bbf7d0}
.melab .me-insight-q{font-size:15px;font-weight:900;color:var(--ink);margin:4px 0 6px;line-height:1.5}
.melab .me-insight-b{font-size:12.5px;color:var(--ink-2);margin:0 0 10px;line-height:1.65}
.melab .me-sum-grid{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:8px;margin:12px 0}
.melab .me-stat{background:#faf7f2;border:1px solid var(--line);border-radius:12px;padding:10px;text-align:center}
.melab .me-stat b{display:block;font-size:18px;color:#2563eb}
.melab .me-stat span{font-size:11px;color:var(--ink-3)}
.melab .me-recap{border:1px solid var(--line);border-radius:12px;padding:11px 13px;background:#fffdf9;margin-bottom:8px}
.melab .topbar h1{font-size:15.5px;line-height:1.35;white-space:nowrap}
.melab .topbar .sub{line-height:1.45}
.melab .hidden{display:none !important}
`;

export async function renderMomentumEnergyLab(view) {
  const KEYS = ['bullet', 'billiard', 'explode', 'coaster', 'spring'];
  const state = {
    theme: 'momentum',
    lab: 'bullet',
    guesses: { bullet: null, billiard: null, explode: null, coaster: null, spring: null },
    correct: { bullet: 'momonly', billiard: '90deg', explode: 'light', coaster: 'equal', spring: 'eq' },
    done: { bullet: false, billiard: false, explode: false, coaster: false, spring: false },
    tasks: { bulMasses: new Set(), bilHead: false, bilOblique: false, expRatios: new Set(), coaNoFric: false, coaFric: false, sprRun: false, sprSlowOrK: false },
  };
  let disposed = false;
  const rafs = { bul: 0, bil: 0, exp: 0, coa: 0, spr: 0 };

  const root = el('div', { class: 'melab' });
  const styleTag = document.createElement('style');
  styleTag.textContent = LAB_CSS;
  root.appendChild(styleTag);

  const dots = KEYS.map(() => el('span', { class: 'me-dot' }));
  const progTxt = el('span', { text: '已探索 0 / 5' });
  root.appendChild(el('div', { class: 'topbar' }, [
    el('button', { class: 'back', text: '‹', onclick: () => { if (history.length > 1) history.back(); else navigate('#/subjects'); } }),
    el('div', { style: 'flex:1;min-width:0' }, [
      el('h1', { text: '动量 & 机械能守恒' }),
      el('div', { class: 'sub', text: '两大核心守恒律 · 5 场互动探索实验' }),
    ]),
    el('div', { class: 'me-pill' }, [...dots, progTxt]),
  ]));

  const body = el('div', { html: `
  <div class="me-themes">
    <button type="button" class="me-tbtn active" data-theme="momentum">💥 主题一：动量守恒（3 实验）</button>
    <button type="button" class="me-tbtn ene" data-theme="energy">⚡ 主题二：机械能守恒（2 实验）</button>
    <button type="button" class="me-tbtn sum" data-theme="summary">🏆 双主题全景总结</button>
  </div>
  <nav class="me-tabs" data-tbar="momentum">
    <button type="button" class="me-tab active" data-lab="bullet">a. 子弹射中木块 <span class="chk hidden" data-chk="bullet">✓</span></button>
    <button type="button" class="me-tab" data-lab="billiard">b. 台球的撞击 <span class="chk hidden" data-chk="billiard">✓</span></button>
    <button type="button" class="me-tab" data-lab="explode">c. 太空爆炸 <span class="chk hidden" data-chk="explode">✓</span></button>
  </nav>
  <nav class="me-tabs hidden" data-tbar="energy">
    <button type="button" class="me-tab active" data-lab="coaster">a. 势能与动能转化 <span class="chk hidden" data-chk="coaster">✓</span></button>
    <button type="button" class="me-tab" data-lab="spring">b. 弹性 + 重力 + 动能三方转化 <span class="chk hidden" data-chk="spring">✓</span></button>
  </nav>

  <section class="panel" data-pane="bullet">
    <div style="font-size:17px;font-weight:800;margin-bottom:4px">子弹射中木块：动量一分没少，动能去哪了？</div>
    <div style="font-size:12.5px;color:var(--ink-2)">调子弹速度与木块质量开火，看右侧总动量与摩擦生热账本。</div>
    <div class="me-predict">
      <div class="me-predict-q">① 先猜一猜：子弹打进光滑桌面上的静止木块并留在里面，总动量和总动能怎么变？</div>
      <div class="me-opts" data-lab="bullet">
        <button type="button" class="me-opt" data-val="both">动量和动能都守恒</button>
        <button type="button" class="me-opt" data-val="momonly">动量守恒，但大部分动能变成了热能</button>
      </div>
    </div>
    <div class="me-stage"><canvas data-cv="bullet" width="740" height="310"></canvas></div>
    <div class="me-ctrl">
      <div class="me-range"><label>子弹初速 v₀</label><input data-in="bulV" type="range" min="100" max="400" value="250" step="10"><span class="me-val" data-out="bulV">250 m/s</span></div>
      <div class="me-range"><label>木块质量 M</label><input data-in="bulM" type="range" min="0.5" max="4.0" value="1.5" step="0.5"><span class="me-val" data-out="bulM">1.5 kg</span></div>
      <button type="button" class="btn sm" data-act="bulFire">发射子弹</button>
      <button type="button" class="btn sm ghost" data-act="bulReset">重置</button>
    </div>
    <div class="me-tasks">
      <span class="me-task" data-task="bul1">○ 目标 1：发射一次观察动量守恒与生热</span>
      <span class="me-task" data-task="bul2">○ 目标 2：换一个木块质量 M 再射一次</span>
    </div>
    <div class="me-insight hidden" data-insight="bullet">
      <div style="font-size:11px;font-weight:800;color:#059669">✦ 顿悟时刻已解锁</div>
      <div class="me-insight-q">“撞在一起时，动量是最忠诚的账本，而机械能悄悄交了一笔巨额‘摩擦税’。”</div>
      <p class="me-insight-b">光滑桌面无外力，系统总动量严格守恒（<code>m v₀ = (m+M) v共</code>），但超 90% 初动能转化为内能（热）。</p>
      <div class="row-between" style="gap:8px;flex-wrap:wrap"><span style="font-size:11.5px;font-weight:700;color:#2563eb" data-guess="bullet"></span><button type="button" class="btn sm" data-jump="billiard">下一场：台球的撞击 →</button></div>
    </div>
  </section>

  <section class="panel hidden" data-pane="billiard">
    <div style="font-size:17px;font-weight:800;margin-bottom:4px">台球的撞击：等质量正碰定杆，斜碰为何永远成 90°？</div>
    <div style="font-size:12.5px;color:var(--ink-2)">先用偏心距 0 打一杆正碰看白球停住，再调大偏心距打斜碰验证 90° 分离！</div>
    <div class="me-predict">
      <div class="me-predict-q">① 先猜一猜：白球斜撞静止的同质量彩球（弹性碰撞），撞后两球速度夹角是多少？</div>
      <div class="me-opts" data-lab="billiard">
        <button type="button" class="me-opt" data-val="any">随角度变化，什么角都有</button>
        <button type="button" class="me-opt" data-val="90deg">永远刚好是 90° 直角！</button>
      </div>
    </div>
    <div class="me-stage"><canvas data-cv="billiard" width="740" height="310"></canvas></div>
    <div class="me-ctrl">
      <div class="me-range"><label>撞击偏心距</label><input data-in="bilOff" type="range" min="0" max="28" value="0" step="2"><span class="me-val" data-out="bilOff">0 (正碰)</span></div>
      <div class="me-range"><label>彩球/白球质量比</label><input data-in="bilMass" type="range" min="0.5" max="2.5" value="1.0" step="0.5"><span class="me-val" data-out="bilMass">1.0×</span></div>
      <button type="button" class="btn sm" data-act="bilShoot">出杆击球</button>
      <button type="button" class="btn sm ghost" data-act="bilReset">重置</button>
    </div>
    <div class="me-tasks">
      <span class="me-task" data-task="bil1">○ 目标 1：等质量正碰（偏心距 0）看白球原地定杆</span>
      <span class="me-task" data-task="bil2">○ 目标 2：等质量斜碰（偏心距 > 0）验证 90° 分离</span>
    </div>
    <div class="me-insight hidden" data-insight="billiard">
      <div style="font-size:11px;font-weight:800;color:#059669">✦ 顿悟时刻已解锁</div>
      <div class="me-insight-q">“动量守恒画出一个三角形，动能守恒恰好给出勾股定理——所以等质量弹性斜碰永远成 90°。”</div>
      <p class="me-insight-b">动量与动能同时守恒：等质量正碰交换速度；斜碰时 <code>v₀² = v₁² + v₂²</code> 锁死直角。</p>
      <div class="row-between" style="gap:8px;flex-wrap:wrap"><span style="font-size:11.5px;font-weight:700;color:#2563eb" data-guess="billiard"></span><button type="button" class="btn sm" data-jump="explode">下一场：太空爆炸 →</button></div>
    </div>
  </section>

  <section class="panel hidden" data-pane="explode">
    <div style="font-size:17px;font-weight:800;margin-bottom:4px">太空爆炸：碎片四散狂飙，为什么“质心”纹丝不动？</div>
    <div style="font-size:12.5px;color:var(--ink-2)">在深空无外力环境下引爆，调节质量比并盯紧金色质心十字！</div>
    <div class="me-predict">
      <div class="me-predict-q">① 先猜一猜：静止太空卫星炸成一大一小两块，哪一块分到的动能更多？</div>
      <div class="me-opts" data-lab="explode">
        <button type="button" class="me-opt" data-val="heavy">大块质量重，所以动能更大</button>
        <button type="button" class="me-opt" data-val="light">小块飞得快得多，反而是小块动能更大</button>
      </div>
    </div>
    <div class="me-stage"><canvas data-cv="explode" width="740" height="310"></canvas></div>
    <div class="me-ctrl">
      <div class="me-range"><label>右块 / 左块质量比</label><input data-in="expRatio" type="range" min="1" max="5" value="3" step="1"><span class="me-val" data-out="expRatio">1 : 3</span></div>
      <button type="button" class="btn sm" style="background:#dc2626" data-act="expBoom">💥 引爆分离！</button>
      <button type="button" class="btn sm ghost" data-act="expReset">复原</button>
    </div>
    <div class="me-tasks">
      <span class="me-task" data-task="exp1">○ 目标 1：引爆一次，观察总动量为 0 且质心不动</span>
      <span class="me-task" data-task="exp2">○ 目标 2：换一个质量比再引爆对比动能分配</span>
    </div>
    <div class="me-insight hidden" data-insight="explode">
      <div style="font-size:11px;font-weight:800;color:#059669">✦ 顿悟时刻已解锁</div>
      <div class="me-insight-q">“内力能把物体炸得粉碎，却连一毫米也挪不动系统的总质心。”</div>
      <p class="me-insight-b">两块动量等大反向（总动量恒为 0），由 <code>Eₖ = p²/(2m)</code> 可知越轻反而分到越多动能——这正是火箭高速喷射轻燃气反冲的原理。</p>
      <div class="row-between" style="gap:8px;flex-wrap:wrap"><span style="font-size:11.5px;font-weight:700;color:#2563eb" data-guess="explode"></span><button type="button" class="btn sm" data-jump="coaster">进入主题二：机械能守恒 →</button></div>
    </div>
  </section>

  <section class="panel hidden" data-pane="coaster">
    <div style="font-size:17px;font-weight:800;margin-bottom:4px">U 形轨道滑球：势能与动能互换，总高度为什么不变？</div>
    <div style="font-size:12.5px;color:var(--ink-2)">调释放高度并切换摩擦阻力，看右侧势能/动能/热能/总能四根柱子实时联动。</div>
    <div class="me-predict">
      <div class="me-predict-q">① 先猜一猜：光滑 U 形槽左边 8 米放开小球，右边轨道更缓，小球最高能爬到几米？</div>
      <div class="me-opts" data-lab="coaster">
        <button type="button" class="me-opt" data-val="lower">右边更长，肯定爬不到 8 米</button>
        <button type="button" class="me-opt" data-val="equal">不管右边多缓，照样精准爬回 8 米！</button>
      </div>
    </div>
    <div class="me-stage"><canvas data-cv="coaster" width="740" height="310"></canvas></div>
    <div class="me-ctrl">
      <div class="me-range"><label>释放高度 h</label><input data-in="coaH" type="range" min="3" max="10" value="8" step="1"><span class="me-val" data-out="coaH">8 m</span></div>
      <button type="button" class="btn sm" data-act="coaRun">释放小球</button>
      <button type="button" class="btn sm ghost" data-act="coaFric">当前：光滑无摩擦</button>
      <button type="button" class="btn sm ghost" data-act="coaReset">重置</button>
    </div>
    <div class="me-tasks">
      <span class="me-task" data-task="coa1">○ 目标 1：无摩擦释放，观察势能动能互换与等高爬升</span>
      <span class="me-task" data-task="coa2">○ 目标 2：开启摩擦阻力，观察机械能转化为热能</span>
    </div>
    <div class="me-insight hidden" data-insight="coaster">
      <div style="font-size:11px;font-weight:800;color:#059669">✦ 顿悟时刻已解锁</div>
      <div class="me-insight-q">“机械能像口袋里的两张钞票：高处全存成势能，谷底全换成动能，只要没漏税，总额一分不差。”</div>
      <p class="me-insight-b">无摩擦时 <code>mgh + ½mv² = 恒量</code>；开启摩擦后机械能减少量严格等于热能增加量，总能量永远守恒。</p>
      <div class="row-between" style="gap:8px;flex-wrap:wrap"><span style="font-size:11.5px;font-weight:700;color:#2563eb" data-guess="coaster"></span><button type="button" class="btn sm" data-jump="spring">下一场：弹簧三方转化 →</button></div>
    </div>
  </section>

  <section class="panel hidden" data-pane="spring">
    <div style="font-size:17px;font-weight:800;margin-bottom:4px">竖直弹簧落球：小球速度最大的瞬间，是刚碰到弹簧时吗？</div>
    <div style="font-size:12.5px;color:var(--ink-2)">释放小球砸向竖直弹簧，开启慢动作盯紧「重力势能 / 动能 / 弹性势能」三柱与平衡点！</div>
    <div class="me-predict">
      <div class="me-predict-q">① 先猜一猜：小球自由落到竖直弹簧上，什么时候小球速度达到最大值？</div>
      <div class="me-opts" data-lab="spring">
        <button type="button" class="me-opt" data-val="touch">刚碰到弹簧上端的那一瞬间</button>
        <button type="button" class="me-opt" data-val="eq">继续下压到弹力等于重力（kx = mg）时才最快</button>
      </div>
    </div>
    <div class="me-stage"><canvas data-cv="spring" width="740" height="320"></canvas></div>
    <div class="me-ctrl">
      <div class="me-range"><label>劲度系数 k</label><input data-in="sprK" type="range" min="30" max="110" value="60" step="10"><span class="me-val" data-out="sprK">60 N/m</span></div>
      <button type="button" class="btn sm" data-act="sprRun">释放小球</button>
      <button type="button" class="btn sm ghost" data-act="sprSlow">当前：常速播放</button>
      <button type="button" class="btn sm ghost" data-act="sprReset">重置</button>
    </div>
    <div class="me-tasks">
      <span class="me-task" data-task="spr1">○ 目标 1：释放一次观察三柱联动与速度最大点</span>
      <span class="me-task" data-task="spr2">○ 目标 2：开启慢动作或调 k 再观察一次</span>
    </div>
    <div class="me-insight hidden" data-insight="spring">
      <div style="font-size:11px;font-weight:800;color:#059669">✦ 顿悟时刻已解锁</div>
      <div class="me-insight-q">“刚碰弹簧时重力仍大于弹力，小球还在加速——真正最快的地方，是合力为零的平衡点！”</div>
      <p class="me-insight-b">全过程 <code>E重力 + E动能 + E弹性 = 恒量</code>：直到 <code>kx = mg</code> 时加速度归零、动能达到顶峰；再往下弹力大于重力开始减速。</p>
      <div class="row-between" style="gap:8px;flex-wrap:wrap"><span style="font-size:11.5px;font-weight:700;color:#2563eb" data-guess="spring"></span><button type="button" class="btn sm" data-jump="summary">查看双主题全景总结 🏆</button></div>
    </div>
  </section>

  <section class="panel hidden" data-pane="summary">
    <div style="text-align:center;margin-bottom:10px">
      <div style="font-size:18px;font-weight:900" data-sum="title">探索进行中：已完成 0 / 5 场实验</div>
      <div style="font-size:12.5px;color:var(--ink-2);margin-top:4px">完成两大守恒律全部 5 场实验，对照你的直觉押注与物理真相。</div>
    </div>
    <div class="me-sum-grid">
      <div class="me-stat"><b data-sum="done">0 / 5</b><span>已解锁实验</span></div>
      <div class="me-stat"><b data-sum="hit">0 / 5</b><span>直觉押注命中</span></div>
      <div class="me-stat"><b>2 大守恒律</b><span>动量 + 机械能</span></div>
    </div>
    <div data-sum="list"></div>
    <div class="row-between" style="margin-top:10px">
      <button type="button" class="btn sm ghost" data-act="resetAll">重新开始</button>
      <button type="button" class="btn sm" data-act="backSubjects">返回路线 →</button>
    </div>
  </section>
  ` });
  root.appendChild(body);

  const $ = (s) => body.querySelector(s);
  const $$ = (s) => [...body.querySelectorAll(s)];

  function updateGuess(lab) {
    const out = $(`[data-guess="${lab}"]`);
    if (!out) return;
    const g = state.guesses[lab];
    out.textContent = !g ? '下次可先做直觉押注再动手！' : (g === state.correct[lab] ? '🎯 直觉押注命中真相！' : '💡 实验反转了刚才的直觉！');
  }
  function setTask(name, ok, txt) {
    const t = $(`[data-task="${name}"]`);
    t.classList.toggle('done', ok);
    t.textContent = (ok ? '✓ ' : '○ ') + txt;
  }
  function updateProgress() {
    let n = 0;
    KEYS.forEach((k, i) => {
      const ok = state.done[k];
      if (ok) n++;
      dots[i].classList.toggle('done', ok);
      $(`[data-chk="${k}"]`).classList.toggle('hidden', !ok);
      $(`[data-insight="${k}"]`).classList.toggle('hidden', !ok);
      if (ok) updateGuess(k);
    });
    progTxt.textContent = `已探索 ${n} / 5`;
  }
  function showPane(lab) {
    state.lab = lab;
    state.theme = ['bullet', 'billiard', 'explode'].includes(lab) ? 'momentum' : (['coaster', 'spring'].includes(lab) ? 'energy' : 'summary');
    $$('.me-tbtn').forEach((b) => b.classList.toggle('active', b.dataset.theme === state.theme));
    $('[data-tbar="momentum"]').classList.toggle('hidden', state.theme !== 'momentum');
    $('[data-tbar="energy"]').classList.toggle('hidden', state.theme !== 'energy');
    $$('.me-tab').forEach((b) => b.classList.toggle('active', b.dataset.lab === lab));
    $$('[data-pane]').forEach((p) => p.classList.toggle('hidden', p.dataset.pane !== lab));
    if (lab === 'summary') renderSummary();
    if (lab === 'bullet') drawBullet();
    if (lab === 'billiard') drawBilliard();
    if (lab === 'explode') drawExplode();
    if (lab === 'coaster') drawCoaster();
    if (lab === 'spring') drawSpring();
  }

  $$('.me-tbtn').forEach((b) => b.addEventListener('click', () => showPane(b.dataset.theme === 'momentum' ? 'bullet' : b.dataset.theme === 'energy' ? 'coaster' : 'summary')));
  $$('.me-tab').forEach((b) => b.addEventListener('click', () => showPane(b.dataset.lab)));
  $$('[data-jump]').forEach((b) => b.addEventListener('click', () => showPane(b.dataset.jump)));
  $$('.me-opts').forEach((w) => {
    const lab = w.dataset.lab;
    w.querySelectorAll('.me-opt').forEach((btn) => btn.addEventListener('click', () => {
      state.guesses[lab] = btn.dataset.val;
      w.querySelectorAll('.me-opt').forEach((x) => x.classList.toggle('picked', x === btn));
      updateGuess(lab);
    }));
  });

  /* ---- 1a 子弹射中木块 ---- */
  const cBul = $('[data-cv="bullet"]'), ctxBu = cBul.getContext('2d');
  const bul = { m: 0.05, M: 1.5, v0: 250, phase: 'ready', bx: 75, blockX: 250, vc: 0, lastTs: 0 };
  function checkBul() {
    const t1 = state.tasks.bulMasses.size >= 1, t2 = state.tasks.bulMasses.size >= 2;
    setTask('bul1', t1, '目标 1：发射一次观察动量守恒与生热');
    setTask('bul2', t2, `目标 2：换不同木块质量再射一次（${Math.min(2, state.tasks.bulMasses.size)}/2）`);
    if (t1 && t2 && !state.done.bullet) { state.done.bullet = true; updateProgress(); }
  }
  function drawBullet() {
    const W = cBul.width, H = cBul.height;
    ctxBu.clearRect(0, 0, W, H); ctxBu.fillStyle = '#fcfaf5'; ctxBu.fillRect(0, 0, W, H);
    ctxBu.fillStyle = '#efe4d3'; ctxBu.fillRect(20, 210, 440, 12);
    const bw = 64 + bul.M * 10, bh = 54;
    ctxBu.fillStyle = bul.phase === 'embedded' ? '#d97706' : '#b45309';
    ctxBu.beginPath(); ctxBu.roundRect(bul.blockX, 210 - bh, bw, bh, 8); ctxBu.fill();
    ctxBu.fillStyle = '#2563eb'; ctxBu.beginPath(); ctxBu.roundRect(bul.bx, 180, 18, 7, 3); ctxBu.fill();
    ctxBu.fillStyle = '#fff'; ctxBu.font = FS.label; ctxBu.textAlign = 'right';
    ctxBu.fillText(`${bul.M}kg`, bul.blockX + bw - 10, 210 - bh / 2 + 7); ctxBu.textAlign = 'left';
    if (bul.phase === 'embedded') { ctxBu.fillStyle = '#dc2626'; ctxBu.font = FS.small; ctxBu.fillText('🔥 剧烈摩擦生热', Math.min(bul.blockX, 250), 132); }
    const p0 = bul.m * bul.v0, ek0 = 0.5 * bul.m * bul.v0 * bul.v0, vc = p0 / (bul.m + bul.M), ekA = 0.5 * (bul.m + bul.M) * vc * vc, heat = ek0 - ekA, hit = bul.phase === 'embedded';
    // 账本：面板保持原位置（480 起），行文字用 17px 保证「标签 + 数值」放得下
    const bx0 = 480, bxw = 242, bxr = bx0 + bxw - 14;
    ctxBu.fillStyle = '#fff'; ctxBu.strokeStyle = '#efe4d3'; ctxBu.beginPath(); ctxBu.roundRect(bx0, 18, bxw, 268, 12); ctxBu.fill(); ctxBu.stroke();
    ctxBu.fillStyle = '#2f2a26'; ctxBu.font = FS.hud; ctxBu.fillText('碰撞账本', bx0 + 16, 54);
    const bar = (y, l, vt, r, c) => {
      ctxBu.fillStyle = '#5b5049'; ctxBu.font = FS.small; ctxBu.fillText(l, bx0 + 16, y);
      ctxBu.font = FS.small; ctxBu.textAlign = 'right'; ctxBu.fillStyle = c; ctxBu.fillText(vt, bxr, y); ctxBu.textAlign = 'left';
      ctxBu.fillStyle = '#f3ece1'; ctxBu.beginPath(); ctxBu.roundRect(bx0 + 16, y + 9, bxw - 30, 13, 6); ctxBu.fill();
      ctxBu.fillStyle = c; ctxBu.beginPath(); ctxBu.roundRect(bx0 + 16, y + 9, Math.max(4, (bxw - 30) * Math.min(1, r)), 13, 6); ctxBu.fill();
    };
    bar(100, '总动量 p', `${p0.toFixed(0)}`, 1, '#2563eb');
    bar(162, '系统动能 Eₖ', `${(hit ? ekA : ek0).toFixed(0)} J`, hit ? ekA / ek0 : 1, '#059669');
    bar(224, '摩擦生热 Q', `${(hit ? heat : 0).toFixed(0)} J`, hit ? heat / ek0 : 0, '#dc2626');
    ctxBu.fillStyle = '#8c7b70'; ctxBu.font = FS.small;
    ctxBu.fillText(hit ? `v共 ${vc.toFixed(1)} m/s` : `子弹 0.05kg / v₀ ${bul.v0}`, bx0 + 16, 268);
  }
  function stepBullet(ts) {
    if (disposed) return;
    if (!bul.lastTs) bul.lastTs = ts;
    const dt = Math.min(0.05, (ts - bul.lastTs) / 1000); bul.lastTs = ts;
    if (bul.phase === 'flying') {
      bul.bx += bul.v0 * 1.45 * dt;
      if (bul.bx + 18 >= bul.blockX) { bul.bx = bul.blockX + 10; bul.phase = 'embedded'; bul.vc = (bul.m * bul.v0) / (bul.m + bul.M); state.tasks.bulMasses.add(bul.M); checkBul(); }
    } else if (bul.phase === 'embedded') {
      const dx = bul.vc * 6.5 * dt; bul.blockX += dx; bul.bx += dx;
      if (bul.blockX > 395) { drawBullet(); return; }
    }
    drawBullet(); rafs.bul = requestAnimationFrame(stepBullet);
  }
  $('[data-in="bulV"]').addEventListener('input', (e) => { bul.v0 = Number(e.target.value); $('[data-out="bulV"]').textContent = `${bul.v0} m/s`; drawBullet(); });
  $('[data-in="bulM"]').addEventListener('input', (e) => { bul.M = Number(e.target.value); $('[data-out="bulM"]').textContent = `${bul.M.toFixed(1)} kg`; drawBullet(); });
  $('[data-act="bulFire"]').addEventListener('click', () => { cancelAnimationFrame(rafs.bul); bul.bx = 75; bul.blockX = 250; bul.phase = 'flying'; bul.lastTs = 0; rafs.bul = requestAnimationFrame(stepBullet); });
  $('[data-act="bulReset"]').addEventListener('click', () => { cancelAnimationFrame(rafs.bul); bul.bx = 75; bul.blockX = 250; bul.phase = 'ready'; drawBullet(); });

  /* ---- 1b 台球撞击 ---- */
  const cBil = $('[data-cv="billiard"]'), ctxBi = cBil.getContext('2d');
  const bil = { off: 0, ratio: 1, r: 18, b1: null, b2: null, hit: false, deg: null, run: false, lastTs: 0 };
  function resetBil() { cancelAnimationFrame(rafs.bil); bil.run = false; bil.hit = false; bil.deg = null; bil.b1 = { x: 110, y: 155 - bil.off, vx: 0, vy: 0, tr: [] }; bil.b2 = { x: 340, y: 155, vx: 0, vy: 0, tr: [] }; }
  function checkBil() {
    setTask('bil1', state.tasks.bilHead, '目标 1：等质量正碰（偏心距 0）看白球原地定杆');
    setTask('bil2', state.tasks.bilOblique, '目标 2：等质量斜碰（偏心距 > 0）验证 90° 分离');
    if (state.tasks.bilHead && state.tasks.bilOblique && !state.done.billiard) { state.done.billiard = true; updateProgress(); }
  }
  function drawBilliard() {
    const W = cBil.width, H = cBil.height;
    ctxBi.clearRect(0, 0, W, H); ctxBi.fillStyle = '#0f5132'; ctxBi.fillRect(0, 0, W, H);
    ctxBi.strokeStyle = '#78350f'; ctxBi.lineWidth = 14; ctxBi.strokeRect(7, 7, W - 14, H - 14);
    if (!bil.hit) { ctxBi.strokeStyle = 'rgba(255,255,255,.35)'; ctxBi.setLineDash([6, 5]); ctxBi.lineWidth = 1.8; ctxBi.beginPath(); ctxBi.moveTo(bil.b1.x, bil.b1.y); ctxBi.lineTo(380, bil.b1.y); ctxBi.stroke(); ctxBi.setLineDash([]); }
    const tr = (pts, c) => { if (pts.length < 2) return; ctxBi.strokeStyle = c; ctxBi.lineWidth = 3; ctxBi.beginPath(); pts.forEach((p, i) => (i ? ctxBi.lineTo(p.x, p.y) : ctxBi.moveTo(p.x, p.y))); ctxBi.stroke(); };
    tr(bil.b1.tr, 'rgba(255,255,255,.75)'); tr(bil.b2.tr, 'rgba(250,204,21,.85)');
    ctxBi.fillStyle = '#fff'; ctxBi.beginPath(); ctxBi.arc(bil.b1.x, bil.b1.y, bil.r, 0, Math.PI * 2); ctxBi.fill();
    ctxBi.fillStyle = '#f8fafc'; ctxBi.font = FS.small; ctxBi.fillText('白球', bil.b1.x - 17, bil.b1.y - bil.r - 8);
    const r2 = bil.r * Math.pow(bil.ratio, 0.22);
    ctxBi.fillStyle = '#facc15'; ctxBi.beginPath(); ctxBi.arc(bil.b2.x, bil.b2.y, r2, 0, Math.PI * 2); ctxBi.fill();
    ctxBi.fillStyle = '#fde047'; ctxBi.fillText(`${bil.ratio}m`, bil.b2.x - 12, bil.b2.y - r2 - 8);
    canvasHud(ctxBi, { x: 20, y: 16, lh: 32, bg: 'rgba(15,23,42,.78)', lines: [
      { text: `偏心 ${bil.off === 0 ? '0（正碰）' : bil.off + 'px'} · 质量 1:${bil.ratio}`, font: FS.small, color: '#f8fafc' },
      { text: !bil.hit ? '点「出杆击球」看弹性碰撞' : (bil.off === 0 && bil.ratio === 1 ? '✨ 等质量正碰：定杆' : bil.deg !== null ? `📐 分离夹角 ${bil.deg.toFixed(0)}°` : '碰撞完成'), font: FS.small, color: '#fde047' },
    ] });
  }
  function stepBil(ts) {
    if (disposed) return;
    if (!bil.lastTs) bil.lastTs = ts;
    const dt = Math.min(0.04, (ts - bil.lastTs) / 1000); bil.lastTs = ts;
    const r2 = bil.r * Math.pow(bil.ratio, 0.22);
    bil.b1.x += bil.b1.vx * dt; bil.b1.y += bil.b1.vy * dt; bil.b2.x += bil.b2.vx * dt; bil.b2.y += bil.b2.vy * dt;
    bil.b1.tr.push({ x: bil.b1.x, y: bil.b1.y }); bil.b2.tr.push({ x: bil.b2.x, y: bil.b2.y });
    if (!bil.hit) {
      const dx = bil.b2.x - bil.b1.x, dy = bil.b2.y - bil.b1.y, d = Math.hypot(dx, dy);
      if (d <= bil.r + r2) {
        bil.hit = true;
        const nx = dx / d, ny = dy / d, m1 = 1, m2 = bil.ratio, vn = (bil.b1.vx - bil.b2.vx) * nx + (bil.b1.vy - bil.b2.vy) * ny, j = (2 * vn) / (1 / m1 + 1 / m2);
        bil.b1.vx -= (j / m1) * nx; bil.b1.vy -= (j / m1) * ny; bil.b2.vx += (j / m2) * nx; bil.b2.vy += (j / m2) * ny;
        const s1 = Math.hypot(bil.b1.vx, bil.b1.vy), s2 = Math.hypot(bil.b2.vx, bil.b2.vy);
        if (s1 > 2 && s2 > 2) bil.deg = Math.acos(Math.max(-1, Math.min(1, (bil.b1.vx * bil.b2.vx + bil.b1.vy * bil.b2.vy) / (s1 * s2)))) * 180 / Math.PI;
        if (bil.ratio === 1 && bil.off === 0) state.tasks.bilHead = true;
        if (bil.ratio === 1 && bil.off > 0) state.tasks.bilOblique = true;
        checkBil();
      }
    }
    drawBilliard();
    if (bil.b1.x > 730 || bil.b2.x > 730 || bil.b1.y < 15 || bil.b1.y > 295 || bil.b2.y < 15 || bil.b2.y > 295) { bil.run = false; return; }
    if (bil.run) rafs.bil = requestAnimationFrame(stepBil);
  }
  $('[data-in="bilOff"]').addEventListener('input', (e) => { bil.off = Number(e.target.value); $('[data-out="bilOff"]').textContent = bil.off === 0 ? '0 (正碰)' : `${bil.off} px`; resetBil(); drawBilliard(); });
  $('[data-in="bilMass"]').addEventListener('input', (e) => { bil.ratio = Number(e.target.value); $('[data-out="bilMass"]').textContent = `${bil.ratio.toFixed(1)}×`; resetBil(); drawBilliard(); });
  $('[data-act="bilShoot"]').addEventListener('click', () => { resetBil(); bil.b1.vx = 250; bil.run = true; bil.lastTs = 0; rafs.bil = requestAnimationFrame(stepBil); });
  $('[data-act="bilReset"]').addEventListener('click', () => { resetBil(); drawBilliard(); });

  /* ---- 1c 太空爆炸 ---- */
  const cExp = $('[data-cv="explode"]'), ctxEx = cExp.getContext('2d');
  const exp = { ratio: 3, boom: false, t: 0, x1: 370, x2: 370, v1: 0, v2: 0, lastTs: 0 };
  function checkExp() {
    const t1 = state.tasks.expRatios.size >= 1, t2 = state.tasks.expRatios.size >= 2;
    setTask('exp1', t1, '目标 1：引爆一次，观察总动量为 0 且质心不动');
    setTask('exp2', t2, `目标 2：换不同质量比再引爆（${Math.min(2, state.tasks.expRatios.size)}/2）`);
    if (t1 && t2 && !state.done.explode) { state.done.explode = true; updateProgress(); }
  }
  function drawExplode() {
    const W = cExp.width, H = cExp.height;
    ctxEx.clearRect(0, 0, W, H); ctxEx.fillStyle = '#0f172a'; ctxEx.fillRect(0, 0, W, H);
    const cy = 175, cx = 370;
    ctxEx.strokeStyle = '#facc15'; ctxEx.lineWidth = 1.8; ctxEx.setLineDash([4, 4]);
    ctxEx.beginPath(); ctxEx.moveTo(cx, 75); ctxEx.lineTo(cx, 270); ctxEx.stroke(); ctxEx.setLineDash([]);
    ctxEx.fillStyle = '#facc15'; ctxEx.font = FS.small; ctxEx.fillText('✦ 系统质心，纹丝不动', cx - 96, 62);
    if (!exp.boom) {
      ctxEx.fillStyle = '#38bdf8'; ctxEx.beginPath(); ctxEx.roundRect(cx - 38, cy - 22, 34, 44, 8); ctxEx.fill();
      ctxEx.fillStyle = '#f97316'; ctxEx.beginPath(); ctxEx.roundRect(cx - 2, cy - 26, 48, 52, 8); ctxEx.fill();
      ctxEx.fillStyle = '#fff'; ctxEx.fillText('1m', cx - 30, cy + 5); ctxEx.fillText(`${exp.ratio}m`, cx + 10, cy + 5);
    } else {
      ctxEx.fillStyle = '#38bdf8'; ctxEx.beginPath(); ctxEx.roundRect(exp.x1 - 18, cy - 20, 36, 40, 8); ctxEx.fill();
      ctxEx.fillStyle = '#fff'; ctxEx.fillText('1m', exp.x1 - 11, cy + 5);
      const w2 = 36 + exp.ratio * 6;
      ctxEx.fillStyle = '#f97316'; ctxEx.beginPath(); ctxEx.roundRect(exp.x2 - w2 / 2, cy - 24, w2, 48, 8); ctxEx.fill();
      ctxEx.fillStyle = '#fff'; ctxEx.fillText(`${exp.ratio}m`, exp.x2 - 12, cy + 5);
    }
    const ek1 = 0.5 * 120 * 120, ek2 = 0.5 * exp.ratio * (120 / exp.ratio) ** 2;
    canvasHud(ctxEx, { x: 16, y: 14, lh: 32, bg: 'rgba(15,23,42,.85)', lines: [
      { text: exp.boom ? '总动量 (-120)+(+120)=0' : '总动量 = 0', font: FS.small, color: '#e2e8f0' },
      { text: `轻块动能 ${((ek1 / (ek1 + ek2)) * 100).toFixed(0)}%`, font: FS.small, color: '#38bdf8' },
      { text: `重块动能 ${((ek2 / (ek1 + ek2)) * 100).toFixed(0)}%`, font: FS.small, color: '#fb923c' },
    ] });
  }
  function stepExp(ts) {
    if (disposed) return;
    if (!exp.lastTs) exp.lastTs = ts;
    const dt = Math.min(0.04, (ts - exp.lastTs) / 1000); exp.lastTs = ts;
    exp.t += dt; exp.x1 += exp.v1 * dt; exp.x2 += exp.v2 * dt; drawExplode();
    if (exp.x1 > 34 && exp.x2 < 700 && exp.t < 2.8) rafs.exp = requestAnimationFrame(stepExp);
  }
  $('[data-in="expRatio"]').addEventListener('input', (e) => { exp.ratio = Number(e.target.value); $('[data-out="expRatio"]').textContent = `1 : ${exp.ratio}`; cancelAnimationFrame(rafs.exp); exp.boom = false; exp.x1 = 370; exp.x2 = 370; drawExplode(); });
  $('[data-act="expBoom"]').addEventListener('click', () => { cancelAnimationFrame(rafs.exp); exp.boom = true; exp.t = 0; exp.x1 = 370; exp.x2 = 370; exp.lastTs = 0; exp.v1 = -160; exp.v2 = 160 / exp.ratio; state.tasks.expRatios.add(exp.ratio); checkExp(); rafs.exp = requestAnimationFrame(stepExp); });
  $('[data-act="expReset"]').addEventListener('click', () => { cancelAnimationFrame(rafs.exp); exp.boom = false; exp.x1 = 370; exp.x2 = 370; drawExplode(); });

  /* ---- 2a 势能与动能转化 ---- */
  const cCoa = $('[data-cv="coaster"]'), ctxCo = cCoa.getContext('2d');
  const coa = { h0: 8, fric: false, run: false, x: -0.89, vx: 0, heat: 0, maxE: 8, lastTs: 0 };
  const ty = (x) => (x < 0 ? 10 * x * x : 10 * (x / 1.35) ** 2);
  const tsSlope = (x) => (x < 0 ? 20 * x : (20 / (1.35 * 1.35)) * x);
  function resetCoa() { cancelAnimationFrame(rafs.coa); coa.run = false; coa.x = -Math.sqrt(coa.h0 / 10); coa.vx = 0; coa.heat = 0; coa.maxE = coa.h0; }
  function checkCoa() {
    setTask('coa1', state.tasks.coaNoFric, '目标 1：无摩擦释放，观察势能动能互换与等高爬升');
    setTask('coa2', state.tasks.coaFric, '目标 2：开启摩擦阻力，观察机械能转化为热能');
    if (state.tasks.coaNoFric && state.tasks.coaFric && !state.done.coaster) { state.done.coaster = true; updateProgress(); }
  }
  function drawCoaster() {
    const W = cCoa.width, H = cCoa.height;
    ctxCo.clearRect(0, 0, W, H); ctxCo.fillStyle = '#fcfaf5'; ctxCo.fillRect(0, 0, W, H);
    const mx = (x) => 220 + x * 165, my = (y) => 265 - y * 20;
    ctxCo.strokeStyle = 'rgba(37,99,235,.3)'; ctxCo.setLineDash([5, 5]); ctxCo.beginPath(); ctxCo.moveTo(40, my(coa.h0)); ctxCo.lineTo(455, my(coa.h0)); ctxCo.stroke(); ctxCo.setLineDash([]);
    ctxCo.strokeStyle = '#5a463a'; ctxCo.lineWidth = 4.5; ctxCo.beginPath();
    for (let x = -1; x <= 1.35; x += 0.03) { const px = mx(x), py = my(ty(x)); if (x === -1) ctxCo.moveTo(px, py); else ctxCo.lineTo(px, py); }
    ctxCo.stroke();
    const curH = Math.min(coa.h0, ty(coa.x)), curKe = Math.max(0, coa.maxE - curH - coa.heat);
    ctxCo.fillStyle = '#2563eb'; ctxCo.beginPath(); ctxCo.arc(mx(coa.x), my(curH) - 10, 10, 0, Math.PI * 2); ctxCo.fill();
    ctxCo.fillStyle = '#fff'; ctxCo.strokeStyle = '#efe4d3'; ctxCo.beginPath(); ctxCo.roundRect(485, 18, 236, 268, 12); ctxCo.fill(); ctxCo.stroke();
    ctxCo.fillStyle = '#2f2a26'; ctxCo.font = FS.hud; ctxCo.fillText('能量守恒', 502, 52);
    [{ x: 510, v: curH, l: '势能', c: '#2563eb' }, { x: 562, v: curKe, l: '动能', c: '#059669' }, { x: 614, v: coa.heat, l: '热能', c: '#dc2626' }, { x: 666, v: coa.maxE, l: '总能', c: '#5a463a' }].forEach((b) => {
      const bh = (b.v / 10) * 165;
      ctxCo.fillStyle = b.c; ctxCo.beginPath(); ctxCo.roundRect(b.x, 248 - bh, 32, Math.max(2, bh), 6); ctxCo.fill();
      ctxCo.fillStyle = '#5b5049'; ctxCo.font = FS.small; ctxCo.fillText(b.l, b.x - 2, 272);
    });
  }
  function stepCoa(ts) {
    if (disposed) return;
    if (!coa.lastTs) coa.lastTs = ts;
    const dt = Math.min(0.03, (ts - coa.lastTs) / 1000); coa.lastTs = ts;
    for (let s = 0; s < 4; s++) {
      const hdt = dt / 4, sl = tsSlope(coa.x);
      coa.vx += ((-sl * 1.45) / (1 + sl * sl * 0.04)) * hdt;
      if (coa.fric) { const pv = coa.vx; coa.vx *= (1 - 0.55 * hdt); coa.heat = Math.min(coa.maxE, coa.heat + Math.abs(pv * pv - coa.vx * coa.vx) * 0.38); }
      coa.x += coa.vx * hdt;
      if (ty(coa.x) > coa.maxE - coa.heat && !coa.fric) coa.vx = -coa.vx;
    }
    if (coa.x > 0.2 && !coa.fric) { state.tasks.coaNoFric = true; checkCoa(); }
    if (coa.fric && coa.heat > 0.6) { state.tasks.coaFric = true; checkCoa(); }
    drawCoaster();
    if (coa.run) rafs.coa = requestAnimationFrame(stepCoa);
  }
  $('[data-in="coaH"]').addEventListener('input', (e) => { coa.h0 = Number(e.target.value); $('[data-out="coaH"]').textContent = `${coa.h0} m`; resetCoa(); drawCoaster(); });
  $('[data-act="coaRun"]').addEventListener('click', () => { resetCoa(); coa.run = true; coa.lastTs = 0; rafs.coa = requestAnimationFrame(stepCoa); });
  $('[data-act="coaFric"]').addEventListener('click', (e) => { coa.fric = !coa.fric; e.currentTarget.textContent = coa.fric ? '当前：开启摩擦阻力' : '当前：光滑无摩擦'; resetCoa(); coa.run = true; coa.lastTs = 0; rafs.coa = requestAnimationFrame(stepCoa); });
  $('[data-act="coaReset"]').addEventListener('click', () => { resetCoa(); drawCoaster(); });

  /* ---- 2b 竖直弹簧三方转化 ---- */
  const cSpr = $('[data-cv="spring"]'), ctxSp = cSpr.getContext('2d');
  const spr = { k: 60, m: 1.5, g: 10, slow: false, y: 0.25, vy: 0, yT: 1.25, run: false, lastTs: 0 };
  function resetSpr() { cancelAnimationFrame(rafs.spr); spr.run = false; spr.y = 0.25; spr.vy = 0; }
  function checkSpr() {
    setTask('spr1', state.tasks.sprRun, '目标 1：释放一次观察三柱联动与速度最大点');
    setTask('spr2', state.tasks.sprSlowOrK, '目标 2：开启慢动作或调 k 再观察一次');
    if (state.tasks.sprRun && state.tasks.sprSlowOrK && !state.done.spring) { state.done.spring = true; updateProgress(); }
  }
  function drawSpring() {
    const W = cSpr.width, H = cSpr.height;
    ctxSp.clearRect(0, 0, W, H); ctxSp.fillStyle = '#fcfaf5'; ctxSp.fillRect(0, 0, W, H);
    const cx = 210, toPy = (ym) => 26 + ym * 105, gY = toPy(2.45), tPy = toPy(spr.yT), eqPy = toPy(spr.yT + (spr.m * spr.g) / spr.k), bPy = toPy(spr.y);
    ctxSp.fillStyle = '#d6c2a8'; ctxSp.fillRect(110, gY, 200, 10);
    ctxSp.strokeStyle = 'rgba(140,123,112,.45)'; ctxSp.setLineDash([4, 4]); ctxSp.beginPath(); ctxSp.moveTo(80, tPy); ctxSp.lineTo(350, tPy); ctxSp.stroke();
    ctxSp.fillStyle = '#8c7b70'; ctxSp.font = FS.small; ctxSp.fillText('弹簧原长', 250, tPy - 8);
    ctxSp.strokeStyle = '#059669'; ctxSp.beginPath(); ctxSp.moveTo(80, eqPy); ctxSp.lineTo(350, eqPy); ctxSp.stroke(); ctxSp.setLineDash([]);
    ctxSp.fillStyle = '#059669'; ctxSp.font = FS.small; ctxSp.fillText('kx = mg 速度最大', 250, eqPy + 20);
    const sTop = Math.max(tPy, bPy + 14), span = gY - sTop;
    ctxSp.strokeStyle = '#5a463a'; ctxSp.lineWidth = 3; ctxSp.beginPath(); ctxSp.moveTo(cx, sTop);
    for (let i = 1; i <= 9; i++) ctxSp.lineTo(cx + (i % 2 === 0 ? -18 : 18), sTop + (span * i) / 10);
    ctxSp.lineTo(cx, gY); ctxSp.stroke();
    ctxSp.fillStyle = '#2563eb'; ctxSp.beginPath(); ctxSp.arc(cx, bPy, 14, 0, Math.PI * 2); ctxSp.fill();
    ctxSp.fillStyle = '#1e3a8a'; ctxSp.font = FS.small; ctxSp.fillText('小球', cx + 20, bPy + 6);
    const comp = Math.max(0, spr.y - spr.yT), eTot = spr.m * spr.g * (2.45 - 0.25), eg = Math.max(0, spr.m * spr.g * (2.45 - spr.y)), ee = 0.5 * spr.k * comp * comp, ek = Math.max(0, eTot - eg - ee);
    ctxSp.fillStyle = '#fff'; ctxSp.strokeStyle = '#efe4d3'; ctxSp.beginPath(); ctxSp.roundRect(455, 18, 265, 276, 12); ctxSp.fill(); ctxSp.stroke();
    ctxSp.fillStyle = '#2f2a26'; ctxSp.font = FS.hud; ctxSp.fillText('机械能转化', 472, 52);
    [{ x: 478, v: eg, l: '势能', c: '#2563eb' }, { x: 540, v: ek, l: '动能', c: '#059669' }, { x: 602, v: ee, l: '弹性', c: '#d97706' }, { x: 664, v: eTot, l: '总能', c: '#5a463a' }].forEach((b) => {
      const bh = (b.v / eTot) * 165;
      ctxSp.fillStyle = b.c; ctxSp.beginPath(); ctxSp.roundRect(b.x, 250 - bh, 36, Math.max(2, bh), 6); ctxSp.fill();
      ctxSp.fillStyle = '#5b5049'; ctxSp.font = FS.small; ctxSp.fillText(b.l, b.x + 2, 274);
    });
  }
  function stepSpr(ts) {
    if (disposed) return;
    if (!spr.lastTs) spr.lastTs = ts;
    const dt = Math.min(0.03, (ts - spr.lastTs) / 1000) * (spr.slow ? 0.38 : 1); spr.lastTs = ts;
    for (let s = 0; s < 5; s++) {
      const hdt = dt / 5, comp = Math.max(0, spr.y - spr.yT);
      spr.vy += (spr.g - (spr.k * comp) / spr.m) * hdt; spr.y += spr.vy * hdt;
      if (spr.y > 2.32) { spr.y = 2.32; spr.vy = -Math.abs(spr.vy); }
    }
    if (spr.y > spr.yT + 0.15) { state.tasks.sprRun = true; checkSpr(); }
    drawSpring();
    if (spr.run) rafs.spr = requestAnimationFrame(stepSpr);
  }
  $('[data-in="sprK"]').addEventListener('input', (e) => { spr.k = Number(e.target.value); $('[data-out="sprK"]').textContent = `${spr.k} N/m`; state.tasks.sprSlowOrK = true; checkSpr(); resetSpr(); drawSpring(); });
  $('[data-act="sprRun"]').addEventListener('click', () => { resetSpr(); spr.run = true; spr.lastTs = 0; rafs.spr = requestAnimationFrame(stepSpr); });
  $('[data-act="sprSlow"]').addEventListener('click', (e) => { spr.slow = !spr.slow; e.currentTarget.textContent = spr.slow ? '当前：慢动作观察' : '当前：常速播放'; state.tasks.sprSlowOrK = true; checkSpr(); });
  $('[data-act="sprReset"]').addEventListener('click', () => { resetSpr(); drawSpring(); });

  function renderSummary() {
    const dN = KEYS.filter((k) => state.done[k]).length;
    const hN = KEYS.filter((k) => state.guesses[k] && state.guesses[k] === state.correct[k]).length;
    $('[data-sum="done"]').textContent = `${dN} / 5`;
    $('[data-sum="hit"]').textContent = `${hN} / 5`;
    $('[data-sum="title"]').textContent = dN === 5 ? '🏆 双主题探索完成！动量与机械能全景档案' : `探索进行中：已完成 ${dN} / 5 场实验`;
    const rows = [
      { k: 'bullet', t: '动量 1 · 子弹射中木块', p: '“动量是最忠诚的账本，而机械能悄悄交了一笔巨额摩擦税。”' },
      { k: 'billiard', t: '动量 2 · 台球的撞击', p: '“等质量正碰交换速度；弹性斜碰动量+动能联立锁死 90° 直角。”' },
      { k: 'explode', t: '动量 3 · 太空爆炸', p: '“内力能把物体炸得粉碎，却连一毫米也挪不动系统的总质心。”' },
      { k: 'coaster', t: '机械能 1 · 势能与动能转化', p: '“高处存势能、谷底换动能；有摩擦时转化为热能，总能量依然守恒。”' },
      { k: 'spring', t: '机械能 2 · 竖直弹簧三方转化', p: '“刚碰弹簧仍在加速，真正速度最大的是合力为零的 kx=mg 平衡点！”' },
    ];
    $('[data-sum="list"]').innerHTML = rows.map((r) => `<div class="me-recap"><div style="font-size:13.5px;font-weight:800">${state.done[r.k] ? '✅ ' : '🔒 '}${r.t}</div><div style="font-size:12.5px;color:var(--ink-2);margin-top:3px">${state.done[r.k] ? r.p : '完成对应实验探索后解锁'}</div></div>`).join('');
  }

  $('[data-act="resetAll"]').addEventListener('click', () => {
    KEYS.forEach((k) => { state.guesses[k] = null; state.done[k] = false; });
    state.tasks = { bulMasses: new Set(), bilHead: false, bilOblique: false, expRatios: new Set(), coaNoFric: false, coaFric: false, sprRun: false, sprSlowOrK: false };
    $$('.me-opt').forEach((b) => b.classList.remove('picked'));
    checkBul(); checkBil(); checkExp(); checkCoa(); checkSpr(); updateProgress(); renderSummary(); showPane('bullet');
  });
  $('[data-act="backSubjects"]').addEventListener('click', () => navigate('#/subjects'));

  view.innerHTML = '';
  view.appendChild(root);

  resetBil(); resetCoa();
  checkBul(); checkBil(); checkExp(); checkCoa(); checkSpr();
  updateProgress();
  drawBullet(); drawBilliard(); drawExplode(); drawCoaster(); drawSpring();
  mountLabBonus(root, '.me-themes');

  return () => {
    disposed = true;
    Object.values(rafs).forEach((id) => cancelAnimationFrame(id));
  };
}
