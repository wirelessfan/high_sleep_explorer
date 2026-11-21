/* 混沌与量子脑洞：双摆混沌蝴蝶效应 + 木星引力弹弓 + 光电效应激光打电子（暗黑霓虹互动实验室） */

import { el } from '../ui.js';
import { navigate } from '../router.js';
import { mountLabBonus } from '../lab-bonus.js';

const LAB_CSS = `
.cqlab{display:flex;flex-direction:column;gap:12px}
.cqlab .cq-pill{display:inline-flex;align-items:center;gap:6px;padding:5px 11px;border-radius:999px;background:#fff;border:1px solid var(--line);font-size:12px;font-weight:700;color:var(--ink-2)}
.cqlab .cq-dot{width:8px;height:8px;border-radius:50%;background:#d6c7b2;transition:background .2s}
.cqlab .cq-dot.done{background:#059669}
.cqlab .cq-tabs{display:flex;flex-wrap:wrap;gap:7px}
.cqlab .cq-tab{appearance:none;border:1px solid var(--line);background:#fff;color:var(--ink-2);padding:7px 12px;border-radius:999px;font-size:12px;font-weight:700;cursor:pointer;display:inline-flex;align-items:center;gap:5px}
.cqlab .cq-tab.active{background:#0f172a;border-color:#f59e0b;color:#fcd34d}
.cqlab .cq-tab .chk{font-size:10.5px;padding:1px 5px;border-radius:999px;background:#ecfdf5;color:#059669}
.cqlab .cq-tab.active .chk{background:rgba(245,158,11,.24);color:#fcd34d}
.cqlab .cq-predict{background:#faf6ef;border:1px dashed #dfcfb7;border-radius:12px;padding:11px 12px;margin:10px 0 12px}
.cqlab .cq-predict-q{font-size:13px;font-weight:800;margin:0 0 8px;color:var(--ink)}
.cqlab .cq-opts{display:flex;flex-wrap:wrap;gap:7px}
.cqlab .cq-opt{appearance:none;background:#fff;border:1px solid #dfd2be;color:var(--ink-2);padding:6px 11px;border-radius:9px;font-size:12px;font-weight:700;cursor:pointer}
.cqlab .cq-opt.picked{background:#eff6ff;border-color:#2563eb;color:#2563eb}
.cqlab .cq-stage{border-radius:14px;overflow:hidden;border:1px solid #1e293b;background:#0b1120;margin-bottom:12px;box-shadow:0 8px 24px rgba(15,23,42,.18)}
.cqlab .cq-stage canvas{display:block;width:100%;height:auto;touch-action:none}
.cqlab .cq-ctrl{display:flex;flex-wrap:wrap;align-items:center;gap:10px 18px;padding:10px 12px;background:#faf7f2;border-radius:12px;border:1px solid var(--line);margin-bottom:10px}
.cqlab .cq-range{display:flex;align-items:center;gap:8px;flex:1 1 240px;min-width:220px}
.cqlab .cq-range label{font-size:12px;font-weight:700;color:var(--ink-2);white-space:nowrap}
.cqlab .cq-range input{flex:1;min-width:80px;cursor:pointer}
.cqlab .cq-val{font-size:12px;font-weight:800;color:#2563eb;min-width:68px;text-align:right;white-space:nowrap;font-variant-numeric:tabular-nums}
.cqlab .cq-tasks{display:flex;flex-wrap:wrap;gap:7px;margin-bottom:4px}
.cqlab .cq-task{font-size:11.5px;font-weight:700;padding:4px 10px;border-radius:9px;background:#f5f0e7;color:var(--ink-3)}
.cqlab .cq-task.done{background:#ecfdf5;color:#059669;border:1px solid #a7f3d0}
.cqlab .cq-insight{margin-top:12px;padding:14px;border-radius:13px;background:linear-gradient(135deg,#f0fdf4 0%,#eff6ff 100%);border:1px solid #bbf7d0}
.cqlab .cq-insight-q{font-size:15px;font-weight:900;color:var(--ink);margin:4px 0 6px;line-height:1.5}
.cqlab .cq-insight-b{font-size:12.5px;color:var(--ink-2);margin:0 0 10px;line-height:1.65}
.cqlab .cq-recap{border:1px solid var(--line);border-radius:12px;padding:11px 13px;background:#fffdf9;margin-bottom:8px}
.cqlab .hidden{display:none !important}
`;

export async function renderChaosQuantumLab(view) {
  const KEYS = ['chaos', 'slingshot', 'photo'];
  const state = {
    tab: 'chaos',
    guesses: { chaos: null, slingshot: null, photo: null },
    correct: { chaos: 'diverge', slingshot: 'planet', photo: 'freq' },
    done: { chaos: false, slingshot: false, photo: false },
    tasks: { chaRun: false, chaDiverge: false, sliShot: false, sliBoost: false, phoRed: false, phoUv: false },
  };
  let disposed = false;
  let rafId = 0;

  const root = el('div', { class: 'cqlab' });
  const styleTag = document.createElement('style');
  styleTag.textContent = LAB_CSS;
  root.appendChild(styleTag);

  const dots = KEYS.map(() => el('span', { class: 'cq-dot' }));
  const progTxt = el('span', { text: '已探索 0 / 3' });
  root.appendChild(el('div', { class: 'topbar' }, [
    el('button', { class: 'back', text: '‹', onclick: () => { if (history.length > 1) history.back(); else navigate('#/subjects'); } }),
    el('div', { style: 'flex:1;min-width:0' }, [
      el('h1', { text: '混沌与量子脑洞' }),
      el('div', { class: 'sub', text: '双摆蝴蝶效应 · 木星引力弹弓 · 光电效应打电子' }),
    ]),
    el('div', { class: 'cq-pill' }, [...dots, progTxt]),
  ]));

  const body = el('div', { html: `
  <nav class="cq-tabs">
    <button type="button" class="cq-tab active" data-tab="chaos">🦋 1. 双摆混沌 <span class="chk hidden" data-chk="chaos">✓</span></button>
    <button type="button" class="cq-tab" data-tab="slingshot">🪐 2. 木星引力弹弓 <span class="chk hidden" data-chk="slingshot">✓</span></button>
    <button type="button" class="cq-tab" data-tab="photo">⚛️ 3. 光电效应 <span class="chk hidden" data-chk="photo">✓</span></button>
    <button type="button" class="cq-tab" data-tab="summary">🏆 专题总结</button>
  </nav>

  <!-- 1: DOUBLE PENDULUM CHAOS -->
  <section class="panel" data-pane="chaos">
    <div style="font-size:17px;font-weight:800;margin-bottom:4px">双摆混沌：初始角度只差 0.01°，几秒后会发生什么？</div>
    <div style="font-size:12.5px;color:var(--ink-2)">青色和玫红两根双摆从几乎完全重合的位置同时释放——睁大眼睛看它们第 4 秒的突然决裂！</div>
    <div class="cq-predict">
      <div class="cq-predict-q">① 先猜一猜：两根完全相同的双摆，释放角度只差 0.01°，它们之后会一直贴在一起摆动吗？</div>
      <div class="cq-opts" data-lab="chaos">
        <button type="button" class="cq-opt" data-val="close">差不多，只会一直差一点点</button>
        <button type="button" class="cq-opt" data-val="diverge">前几秒重合，随后突然彻底分道扬镳、轨迹完全不同</button>
      </div>
    </div>
    <div class="cq-stage"><canvas data-cv="chaos" width="740" height="330"></canvas></div>
    <div class="cq-ctrl">
      <div class="cq-range"><label>初始角度差 Δθ</label><input data-in="chaDiff" type="range" min="0.01" max="1.00" value="0.01" step="0.01"><span class="cq-val" data-out="chaDiff">0.01°</span></div>
      <button type="button" class="btn sm" data-act="chaStart">释放双摆</button>
      <button type="button" class="btn sm ghost" data-act="chaReset">重置</button>
    </div>
    <div class="cq-tasks">
      <span class="cq-task" data-task="cha1">○ 目标 1：释放双摆观察前几秒重合轨迹</span>
      <span class="cq-task" data-task="cha2">○ 目标 2：等待两根双摆彻底分道扬镳（蝴蝶效应触发）</span>
    </div>
    <div class="cq-insight hidden" data-insight="chaos">
      <div style="font-size:11px;font-weight:800;color:#059669">✦ 顿悟时刻已解锁</div>
      <div class="cq-insight-q">“方程 100% 确定，未来却 100% 不可预测——差 0.01° 就能改写整个宇宙的轨迹。”</div>
      <p class="cq-insight-b">双摆完全遵循牛顿力学确定方程，但对初始条件极端敏感（误差呈指数级放大），这就是<strong>混沌与蝴蝶效应</strong>——也是为什么天气预报很难精准预测两周之后。</p>
      <div class="row-between" style="gap:8px;flex-wrap:wrap"><span style="font-size:11.5px;font-weight:700;color:#2563eb" data-guess="chaos"></span><button type="button" class="btn sm" data-goto="slingshot">下一场：木星引力弹弓 →</button></div>
    </div>
  </section>

  <!-- 2: GRAVITY ASSIST -->
  <section class="panel hidden" data-pane="slingshot">
    <div style="font-size:17px;font-weight:800;margin-bottom:4px">木星引力弹弓：不烧一滴额外燃料，如何把探测器甩出太阳系？</div>
    <div style="font-size:12.5px;color:var(--ink-2)">木星正高速向上运动！调好探测器发射角度点「🚀 发射探测器」，绕过木星后方“白嫖”它的公转速度！</div>
    <div class="cq-predict">
      <div class="cq-predict-q">① 先猜一猜：引力弹弓让探测器加速狂飙，多出来的动能是从哪儿白嫖来的？</div>
      <div class="cq-opts" data-lab="slingshot">
        <button type="button" class="cq-opt" data-val="magic">木星的引力凭空创造了能量</button>
        <button type="button" class="cq-opt" data-val="planet">偷了木星一点点公转轨道动能（木星太重，几乎察觉不到）</button>
      </div>
    </div>
    <div class="cq-stage"><canvas data-cv="slingshot" width="740" height="330"></canvas></div>
    <div class="cq-ctrl">
      <div class="cq-range"><label>发射仰角</label><input data-in="sliAng" type="range" min="-25" max="25" value="-6" step="1"><span class="cq-val" data-out="sliAng">-6°</span></div>
      <button type="button" class="btn sm" style="background:#2563eb" data-act="sliFire">🚀 发射探测器</button>
      <button type="button" class="btn sm ghost" data-act="sliReset">重置</button>
    </div>
    <div class="cq-tasks">
      <span class="cq-task" data-task="sli1">○ 目标 1：发射探测器靠近运动中的木星</span>
      <span class="cq-task" data-task="sli2">○ 目标 2：成功触发引力弹弓加速（速度提升 ≥ 25%）</span>
    </div>
    <div class="cq-insight hidden" data-insight="slingshot">
      <div style="font-size:11px;font-weight:800;color:#059669">✦ 顿悟时刻已解锁</div>
      <div class="cq-insight-q">“不烧一滴额外燃料，算准角度‘借’行星一点公转速度，探测器就能白嫖飞出太阳系。”</div>
      <p class="cq-insight-b">在太阳参考系中，探测器绕过运动行星后方相当于一次弹性“拉拽”，偷走了行星极微小的轨道动能却让自己速度暴涨。旅行者 1 号、2 号就是靠木星与土星连环弹弓飞出太阳系的！</p>
      <div class="row-between" style="gap:8px;flex-wrap:wrap"><span style="font-size:11.5px;font-weight:700;color:#2563eb" data-guess="slingshot"></span><button type="button" class="btn sm" data-goto="photo">下一场：光电效应 →</button></div>
    </div>
  </section>

  <!-- 3: PHOTOELECTRIC EFFECT -->
  <section class="panel hidden" data-pane="photo">
    <div style="font-size:17px;font-weight:800;margin-bottom:4px">光电效应：为什么 100% 亮度的红光，打不出一颗电子？</div>
    <div style="font-size:12.5px;color:var(--ink-2)">先用 650nm 红光把亮度拉满试试，再把波长滑块往左划进蓝紫光（&lt; 480nm），看金属板瞬间烟花般迸出光电子！</div>
    <div class="cq-predict">
      <div class="cq-predict-q">① 先猜一猜：红光照射金属板打不出电子，如果把红光亮度调大 100 倍，能打出电子吗？</div>
      <div class="cq-opts" data-lab="photo">
        <button type="button" class="cq-opt" data-val="bright">能，光越强能量越大，总能把电子烤出来</button>
        <button type="button" class="cq-opt" data-val="freq">不能！单颗红光光子能量不够逸出功，再亮也打不出一颗</button>
      </div>
    </div>
    <div class="cq-stage"><canvas data-cv="photo" width="740" height="310"></canvas></div>
    <div class="cq-ctrl">
      <div class="cq-range"><label>激光波长 λ</label><input data-in="phoLam" type="range" min="280" max="700" value="650" step="10"><span class="cq-val" data-out="phoLam">650 nm 红</span></div>
      <div class="cq-range"><label>光照强度 I</label><input data-in="phoInt" type="range" min="15" max="100" value="80" step="5"><span class="cq-val" data-out="phoInt">80%</span></div>
    </div>
    <div class="cq-tasks">
      <span class="cq-task" data-task="pho1">○ 目标 1：用红光（≥ 600nm）高亮度照射，确认 0 颗电子逸出</span>
      <span class="cq-task" data-task="pho2">○ 目标 2：把波长调到蓝紫光（≤ 450nm），亲眼打出电子流</span>
    </div>
    <div class="cq-insight hidden" data-insight="photo">
      <div style="font-size:11px;font-weight:800;color:#059669">✦ 顿悟时刻已解锁</div>
      <div class="cq-insight-q">“红光再亮也像丢一万颗棉花糖，紫光再弱也是一颗钢珠——能量是一份一份打包的，这就是量子。”</div>
      <p class="cq-insight-b">爱因斯坦提出光量子假说 <code>E = hν = hc/λ</code>：只有单个光子能量超过金属逸出功 <code>W₀</code> 才能打出电子，光强只决定电子数量。他正是凭此获得 1921 年诺贝尔物理学奖，也奠定了今天太阳能电池与相机传感器的基础。</p>
      <div class="row-between" style="gap:8px;flex-wrap:wrap"><span style="font-size:11.5px;font-weight:700;color:#2563eb" data-guess="photo"></span><button type="button" class="btn sm" data-goto="summary">查看专题总结 🏆</button></div>
    </div>
  </section>

  <!-- SUMMARY -->
  <section class="panel hidden" data-pane="summary">
    <div style="text-align:center;margin-bottom:12px">
      <div style="font-size:18px;font-weight:900" data-sum="title">探索进行中：已完成 0 / 3 场混沌与量子实验</div>
      <div style="font-size:12.5px;color:var(--ink-2);margin-top:4px">从非线性混沌、深空引力弹弓到诺奖级量子光电效应——物理学的边界永远比想象更酷。</div>
    </div>
    <div data-sum="list"></div>
    <div class="row-between" style="margin-top:10px">
      <button type="button" class="btn sm ghost" data-act="resetAll">重新开始探索</button>
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
  function setTask(name, ok, txt) { const t = $(`[data-task="${name}"]`); t.classList.toggle('done', ok); t.textContent = (ok ? '✓ ' : '○ ') + txt; }
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
    progTxt.textContent = `已探索 ${n} / 3`;
  }
  function switchTab(name) {
    state.tab = name;
    $$('.cq-tab').forEach((b) => b.classList.toggle('active', b.dataset.tab === name));
    $$('[data-pane]').forEach((p) => p.classList.toggle('hidden', p.dataset.pane !== name));
    if (name === 'summary') renderSummary();
  }
  $$('.cq-tab').forEach((b) => b.addEventListener('click', () => switchTab(b.dataset.tab)));
  $$('[data-goto]').forEach((b) => b.addEventListener('click', () => switchTab(b.dataset.goto)));
  $$('.cq-opts').forEach((w) => {
    const lab = w.dataset.lab;
    w.querySelectorAll('.cq-opt').forEach((btn) => btn.addEventListener('click', () => {
      state.guesses[lab] = btn.dataset.val;
      w.querySelectorAll('.cq-opt').forEach((x) => x.classList.toggle('picked', x === btn));
      updateGuess(lab);
    }));
  });

  /* ---- 1. DOUBLE PENDULUM ---- */
  const cCha = $('[data-cv="chaos"]'), ctxCh = cCha.getContext('2d');
  const cha = { diff: 0.01, running: false, p1: null, p2: null, tr1: [], tr2: [], t: 0 };
  function makePend(dDeg) { return { a1: 2.15 + dDeg * Math.PI / 180, a2: 2.35, w1: 0, w2: 0 }; }
  function resetCha() { cha.running = false; cha.t = 0; cha.p1 = makePend(0); cha.p2 = makePend(cha.diff); cha.tr1 = []; cha.tr2 = []; }
  function stepPend(p, dt) {
    const g = 9.8, L1 = 1, L2 = 1, m1 = 1, m2 = 1;
    const d = p.a1 - p.a2, den = 2 * m1 + m2 - m2 * Math.cos(2 * d);
    const dw1 = (-g * (2 * m1 + m2) * Math.sin(p.a1) - m2 * g * Math.sin(p.a1 - 2 * p.a2) - 2 * Math.sin(d) * m2 * (p.w2 * p.w2 * L2 + p.w1 * p.w1 * L1 * Math.cos(d))) / (L1 * den);
    const dw2 = (2 * Math.sin(d) * (p.w1 * p.w1 * L1 * (m1 + m2) + g * (m1 + m2) * Math.cos(p.a1) + p.w2 * p.w2 * L2 * m2 * Math.cos(d))) / (L2 * den);
    p.w1 += dw1 * dt; p.w2 += dw2 * dt; p.a1 += p.w1 * dt; p.a2 += p.w2 * dt;
  }
  function checkCha() {
    setTask('cha1', state.tasks.chaRun, '目标 1：释放双摆观察前几秒重合轨迹');
    setTask('cha2', state.tasks.chaDiverge, '目标 2：等待两根双摆彻底分道扬镳');
    if (state.tasks.chaRun && state.tasks.chaDiverge && !state.done.chaos) { state.done.chaos = true; updateProgress(); }
  }
  $('[data-in="chaDiff"]').addEventListener('input', (e) => { cha.diff = Number(e.target.value); $('[data-out="chaDiff"]').textContent = `${cha.diff.toFixed(2)}°`; resetCha(); });
  $('[data-act="chaStart"]').addEventListener('click', () => { resetCha(); cha.running = true; state.tasks.chaRun = true; checkCha(); });
  $('[data-act="chaReset"]').addEventListener('click', resetCha);

  /* ---- 2. GRAVITY SLINGSHOT ---- */
  const cSli = $('[data-cv="slingshot"]'), ctxSl = cSli.getContext('2d');
  const sli = { ang: -6, running: false, jupY: 255, jupVy: -52, px: 75, py: 185, pvx: 0, pvy: 0, vInit: 145, vMax: 145, trail: [] };
  function resetSli() { sli.running = false; sli.jupY = 255; sli.px = 75; sli.py = 185; sli.pvx = 0; sli.pvy = 0; sli.vMax = sli.vInit; sli.trail = []; }
  function checkSli() {
    setTask('sli1', state.tasks.sliShot, '目标 1：发射探测器靠近运动中的木星');
    setTask('sli2', state.tasks.sliBoost, '目标 2：成功触发引力弹弓加速（提速 ≥ 25%）');
    if (state.tasks.sliShot && state.tasks.sliBoost && !state.done.slingshot) { state.done.slingshot = true; updateProgress(); }
  }
  $('[data-in="sliAng"]').addEventListener('input', (e) => { sli.ang = Number(e.target.value); $('[data-out="sliAng"]').textContent = `${sli.ang}°`; resetSli(); });
  $('[data-act="sliFire"]').addEventListener('click', () => {
    resetSli();
    const r = sli.ang * Math.PI / 180;
    sli.pvx = Math.cos(r) * sli.vInit; sli.pvy = Math.sin(r) * sli.vInit;
    sli.running = true; state.tasks.sliShot = true; checkSli();
  });
  $('[data-act="sliReset"]').addEventListener('click', resetSli);

  /* ---- 3. PHOTOELECTRIC EFFECT ---- */
  const cPho = $('[data-cv="photo"]'), ctxPh = cPho.getContext('2d');
  const pho = { lam: 650, inten: 80, photons: [], electrons: [], tick: 0 };
  function lamColor(l) {
    if (l < 380) return { c: '#a78bfa', n: '紫外' };
    if (l < 450) return { c: '#818cf8', n: '紫' };
    if (l < 495) return { c: '#38bdf8', n: '蓝' };
    if (l < 570) return { c: '#34d399', n: '绿' };
    if (l < 605) return { c: '#fbbf24', n: '黄' };
    return { c: '#f87171', n: '红' };
  }
  function checkPho() {
    setTask('pho1', state.tasks.phoRed, '目标 1：用红光（≥ 600nm）确认 0 颗电子逸出');
    setTask('pho2', state.tasks.phoUv, '目标 2：波长调至蓝紫光（≤ 450nm）打出电子流');
    if (state.tasks.phoRed && state.tasks.phoUv && !state.done.photo) { state.done.photo = true; updateProgress(); }
  }
  $('[data-in="phoLam"]').addEventListener('input', (e) => {
    pho.lam = Number(e.target.value);
    const info = lamColor(pho.lam);
    $('[data-out="phoLam"]').textContent = `${pho.lam} nm ${info.n}`;
    if (pho.lam >= 600) state.tasks.phoRed = true;
    if (pho.lam <= 450) state.tasks.phoUv = true;
    checkPho();
  });
  $('[data-in="phoInt"]').addEventListener('input', (e) => { pho.inten = Number(e.target.value); $('[data-out="phoInt"]').textContent = `${pho.inten}%`; });

  /* Main animation loop */
  function loop() {
    if (disposed) return;

    if (state.tab === 'chaos') {
      const ox = 310, oy = 115, scale = 92;
      if (cha.running) {
        for (let s = 0; s < 5; s++) { stepPend(cha.p1, 0.008); stepPend(cha.p2, 0.008); }
        cha.t += 0.04;
      }
      const pos = (p) => {
        const x1 = ox + Math.sin(p.a1) * scale, y1 = oy + Math.cos(p.a1) * scale;
        return { x1, y1, x2: x1 + Math.sin(p.a2) * scale, y2: y1 + Math.cos(p.a2) * scale };
      };
      const k1 = pos(cha.p1), k2 = pos(cha.p2);
      if (cha.running) {
        cha.tr1.push({ x: k1.x2, y: k1.y2 }); cha.tr2.push({ x: k2.x2, y: k2.y2 });
        if (cha.tr1.length > 260) { cha.tr1.shift(); cha.tr2.shift(); }
        if (Math.hypot(k1.x2 - k2.x2, k1.y2 - k2.y2) > 55) { state.tasks.chaDiverge = true; checkCha(); }
      }
      ctxCh.clearRect(0, 0, cCha.width, cCha.height); ctxCh.fillStyle = '#0b1120'; ctxCh.fillRect(0, 0, cCha.width, cCha.height);
      const drawTr = (tr, c) => { if (tr.length < 2) return; ctxCh.strokeStyle = c; ctxCh.lineWidth = 2; ctxCh.beginPath(); tr.forEach((p, i) => (i ? ctxCh.lineTo(p.x, p.y) : ctxCh.moveTo(p.x, p.y))); ctxCh.stroke(); };
      drawTr(cha.tr1, 'rgba(56,189,248,0.65)'); drawTr(cha.tr2, 'rgba(244,63,94,0.65)');
      const drawArm = (k, c) => {
        ctxCh.strokeStyle = c; ctxCh.lineWidth = 2.5; ctxCh.beginPath(); ctxCh.moveTo(ox, oy); ctxCh.lineTo(k.x1, k.y1); ctxCh.lineTo(k.x2, k.y2); ctxCh.stroke();
        ctxCh.fillStyle = c; ctxCh.beginPath(); ctxCh.arc(k.x1, k.y1, 5, 0, Math.PI * 2); ctxCh.arc(k.x2, k.y2, 7, 0, Math.PI * 2); ctxCh.fill();
      };
      drawArm(k1, '#38bdf8'); drawArm(k2, '#fb7185');
      const sep = Math.hypot(k1.x2 - k2.x2, k1.y2 - k2.y2);
      ctxCh.fillStyle = 'rgba(15,23,42,0.86)'; ctxCh.strokeStyle = '#243044'; ctxCh.beginPath(); ctxCh.roundRect(490, 18, 232, 84, 12); ctxCh.fill(); ctxCh.stroke();
      ctxCh.fillStyle = '#7dd3fc'; ctxCh.font = '800 12.5px sans-serif'; ctxCh.fillText(`初始角度差 Δθ = ${cha.diff.toFixed(2)}°`, 506, 42);
      ctxCh.fillStyle = sep > 55 ? '#fb7185' : '#34d399';
      ctxCh.fillText(sep > 55 ? '🦋 混沌决裂！轨迹已完全不同' : `末端距离差：${sep.toFixed(1)} px`, 506, 66);
      ctxCh.fillStyle = '#94a3b8'; ctxCh.font = '600 11.5px sans-serif'; ctxCh.fillText(`已运行 ${cha.t.toFixed(1)} s`, 506, 88);
    }

    if (state.tab === 'slingshot') {
      const jx = 410, jr = 28;
      if (sli.running) {
        for (let s = 0; s < 4; s++) {
          const dt = 0.004;
          sli.jupY += sli.jupVy * dt;
          const dx = jx - sli.px, dy = sli.jupY - sli.py, d = Math.max(jr + 6, Math.hypot(dx, dy));
          const acc = 1250000 / (d * d * d);
          sli.pvx += acc * dx * dt; sli.pvy += acc * dy * dt;
          sli.px += sli.pvx * dt; sli.py += sli.pvy * dt;
          const v = Math.hypot(sli.pvx, sli.pvy);
          if (v > sli.vMax) sli.vMax = v;
        }
        sli.trail.push({ x: sli.px, y: sli.py });
        if (sli.trail.length > 260) sli.trail.shift();
        if (sli.vMax >= sli.vInit * 1.25 && sli.px > jx + 40) { state.tasks.sliBoost = true; checkSli(); }
        if (sli.px > 750 || sli.px < -20 || sli.py < -20 || sli.py > 350) sli.running = false;
      }
      ctxSl.clearRect(0, 0, cSli.width, cSli.height); ctxSl.fillStyle = '#0b1120'; ctxSl.fillRect(0, 0, cSli.width, cSli.height);
      // Jupiter motion guide
      ctxSl.strokeStyle = 'rgba(251,191,36,0.25)'; ctxSl.setLineDash([5, 5]); ctxSl.beginPath(); ctxSl.moveTo(jx, 30); ctxSl.lineTo(jx, 300); ctxSl.stroke(); ctxSl.setLineDash([]);
      const jg = ctxSl.createRadialGradient(jx - 8, sli.jupY - 8, 4, jx, sli.jupY, jr);
      jg.addColorStop(0, '#fde68a'); jg.addColorStop(0.6, '#d97706'); jg.addColorStop(1, '#78350f');
      ctxSl.fillStyle = jg; ctxSl.beginPath(); ctxSl.arc(jx, sli.jupY, jr, 0, Math.PI * 2); ctxSl.fill();
      ctxSl.fillStyle = '#fde68a'; ctxSl.font = '700 11.5px sans-serif'; ctxSl.fillText('木星 ↑', jx + 34, sli.jupY + 4);
      if (sli.trail.length > 1) {
        ctxSl.strokeStyle = '#38bdf8'; ctxSl.lineWidth = 2.6; ctxSl.beginPath();
        sli.trail.forEach((p, i) => (i ? ctxSl.lineTo(p.x, p.y) : ctxSl.moveTo(p.x, p.y))); ctxSl.stroke();
      }
      ctxSl.fillStyle = '#34d399'; ctxSl.beginPath(); ctxSl.arc(sli.px, sli.py, 5.5, 0, Math.PI * 2); ctxSl.fill();
      const curV = sli.running ? Math.hypot(sli.pvx, sli.pvy) : sli.vInit;
      const gainPct = Math.round(((sli.vMax - sli.vInit) / sli.vInit) * 100);
      ctxSl.fillStyle = 'rgba(15,23,42,0.86)'; ctxSl.strokeStyle = '#243044'; ctxSl.beginPath(); ctxSl.roundRect(18, 16, 268, 72, 12); ctxSl.fill(); ctxSl.stroke();
      ctxSl.fillStyle = '#7dd3fc'; ctxSl.font = '800 12.5px sans-serif'; ctxSl.fillText(`当前速率：${(curV * 0.1).toFixed(1)} km/s（初速 14.5）`, 32, 40);
      ctxSl.fillStyle = gainPct >= 25 ? '#34d399' : '#fbbf24';
      ctxSl.fillText(gainPct >= 25 ? `🚀 引力弹弓成功！最高提速 +${gainPct}%` : '提示：瞄准木星下方绕后方擦过！', 32, 64);
    }

    if (state.tab === 'photo') {
      pho.tick++;
      const info = lamColor(pho.lam);
      const ePhoton = 1240 / pho.lam; // eV
      const workFn = 2.6; // eV (~477nm cutoff)
      const eject = ePhoton > workFn;
      if (pho.lam >= 600) state.tasks.phoRed = true;
      if (pho.lam <= 450) state.tasks.phoUv = true;
      checkPho();

      if (pho.tick % Math.max(2, Math.round(14 - pho.inten * 0.11)) === 0) {
        pho.photons.push({ x: 60, y: 70 + Math.random() * 160, vx: 6.5, c: info.c });
      }
      ctxPh.clearRect(0, 0, cPho.width, cPho.height); ctxPh.fillStyle = '#0b1120'; ctxPh.fillRect(0, 0, cPho.width, cPho.height);
      // Cathode metal plate & anode
      ctxPh.fillStyle = '#475569'; ctxPh.fillRect(260, 55, 18, 200);
      ctxPh.fillStyle = '#94a3b8'; ctxPh.font = '700 11.5px sans-serif'; ctxPh.fillText('金属阴极 (W₀=2.6 eV)', 210, 276);
      ctxPh.fillStyle = '#334155'; ctxPh.fillRect(580, 55, 14, 200);
      ctxPh.fillText('阳极接收板', 555, 276);

      const nextPh = [];
      for (const p of pho.photons) {
        p.x += p.vx;
        ctxPh.strokeStyle = p.c; ctxPh.lineWidth = 2.4; ctxPh.shadowColor = p.c; ctxPh.shadowBlur = 8;
        ctxPh.beginPath(); ctxPh.moveTo(p.x - 14, p.y); ctxPh.lineTo(p.x, p.y); ctxPh.stroke(); ctxPh.shadowBlur = 0;
        if (p.x >= 260) {
          if (eject) {
            const ke = ePhoton - workFn;
            pho.electrons.push({ x: 282, y: p.y, vx: 2.2 + Math.sqrt(ke) * 2.8, vy: (Math.random() - 0.5) * 0.9 });
          }
        } else nextPh.push(p);
      }
      pho.photons = nextPh;

      const nextEl = [];
      for (const e of pho.electrons) {
        e.x += e.vx; e.y += e.vy;
        ctxPh.fillStyle = '#fde047'; ctxPh.shadowColor = '#fde047'; ctxPh.shadowBlur = 10;
        ctxPh.beginPath(); ctxPh.arc(e.x, e.y, 4, 0, Math.PI * 2); ctxPh.fill(); ctxPh.shadowBlur = 0;
        if (e.x < 580) nextEl.push(e);
      }
      pho.electrons = nextEl;

      ctxPh.fillStyle = 'rgba(15,23,42,0.88)'; ctxPh.strokeStyle = '#243044'; ctxPh.beginPath(); ctxPh.roundRect(320, 14, 245, 76, 12); ctxPh.fill(); ctxPh.stroke();
      ctxPh.fillStyle = info.c; ctxPh.font = '800 12.5px sans-serif'; ctxPh.fillText(`单光子能量 E = ${ePhoton.toFixed(2)} eV`, 336, 38);
      ctxPh.fillStyle = eject ? '#34d399' : '#f87171';
      ctxPh.fillText(eject ? `✨ 超过逸出功！光电子喷射中` : '✗ 能量 < 2.6 eV，光再亮也是 0 电子', 336, 62);
    }

    rafId = requestAnimationFrame(loop);
  }

  function renderSummary() {
    const dN = KEYS.filter((k) => state.done[k]).length;
    $('[data-sum="title"]').textContent = dN === 3 ? '🏆 混沌与量子专题通关！三场脑洞实验全解锁' : `探索进行中：已完成 ${dN} / 3 场实验`;
    const rows = [
      { k: 'chaos', t: '1. 双摆混沌蝴蝶效应', p: '“方程 100% 确定，未来却 100% 不可预测——差 0.01° 改写轨迹。”' },
      { k: 'slingshot', t: '2. 木星引力弹弓', p: '“不烧一滴额外燃料，借行星一点公转速度白嫖飞出太阳系。”' },
      { k: 'photo', t: '3. 光电效应打电子', p: '“红光再亮像棉花糖，紫光再弱也是钢珠——能量是一份份打包的。”' },
    ];
    $('[data-sum="list"]').innerHTML = rows.map((r) => `<div class="cq-recap"><div style="font-size:13.5px;font-weight:800">${state.done[r.k] ? '✅ ' : '🔒 '}${r.t}</div><div style="font-size:12.5px;color:var(--ink-2);margin-top:3px">${state.done[r.k] ? r.p : '完成对应实验探索后解锁'}</div></div>`).join('');
  }
  $('[data-act="resetAll"]').addEventListener('click', () => {
    KEYS.forEach((k) => { state.guesses[k] = null; state.done[k] = false; });
    state.tasks = { chaRun: false, chaDiverge: false, sliShot: false, sliBoost: false, phoRed: false, phoUv: false };
    $$('.cq-opt').forEach((b) => b.classList.remove('picked'));
    resetCha(); resetSli();
    checkCha(); checkSli(); checkPho(); updateProgress(); renderSummary(); switchTab('chaos');
  });
  $('[data-act="backSubjects"]').addEventListener('click', () => navigate('#/subjects'));

  view.innerHTML = '';
  view.appendChild(root);
  resetCha(); resetSli();
  checkCha(); checkSli(); checkPho(); updateProgress();
  rafId = requestAnimationFrame(loop);
  mountLabBonus(root, '.cq-tabs');
  return () => { disposed = true; cancelAnimationFrame(rafId); };
}
