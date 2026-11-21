/* 专题 F：相对论与核风暴（爱因斯坦光钟时间膨胀 + 卢瑟福金箔散射 + 铀-235 核裂变控制棒） */

import { el } from '../ui.js';
import { navigate } from '../router.js';
import { FS, canvasHud } from '../lab-canvas.js';
import { mountLabBonus } from '../lab-bonus.js';

const LAB_CSS = `
.rnlab{display:flex;flex-direction:column;gap:12px}
.rnlab .rn-pill{display:inline-flex;align-items:center;gap:6px;padding:5px 11px;border-radius:999px;background:#fff;border:1px solid var(--line);font-size:12px;font-weight:700;color:var(--ink-2)}
.rnlab .rn-dot{width:8px;height:8px;border-radius:50%;background:#d6c7b2;transition:background .2s}
.rnlab .rn-dot.done{background:#059669}
.rnlab .rn-tabs{display:flex;flex-wrap:wrap;gap:7px}
.rnlab .rn-tab{appearance:none;border:1px solid var(--line);background:#fff;color:var(--ink-2);padding:7px 12px;border-radius:999px;font-size:12px;font-weight:700;cursor:pointer;display:inline-flex;align-items:center;gap:5px}
.rnlab .rn-tab.active{background:#0f172a;border-color:#a78bfa;color:#ddd6fe}
.rnlab .rn-tab .chk{font-size:10.5px;padding:1px 5px;border-radius:999px;background:#ecfdf5;color:#059669}
.rnlab .rn-tab.active .chk{background:rgba(167,139,250,.24);color:#ddd6fe}
.rnlab .rn-predict{background:#faf6ef;border:1px dashed #dfcfb7;border-radius:12px;padding:11px 12px;margin:10px 0 12px}
.rnlab .rn-predict-q{font-size:13px;font-weight:800;margin:0 0 8px;color:var(--ink)}
.rnlab .rn-opts{display:flex;flex-wrap:wrap;gap:7px}
.rnlab .rn-opt{appearance:none;background:#fff;border:1px solid #dfd2be;color:var(--ink-2);padding:6px 11px;border-radius:9px;font-size:12px;font-weight:700;cursor:pointer}
.rnlab .rn-opt.picked{background:#eff6ff;border-color:#2563eb;color:#2563eb}
.rnlab .rn-stage{border-radius:14px;overflow:hidden;border:1px solid #1e293b;background:#0b1120;margin-bottom:12px;box-shadow:0 8px 24px rgba(15,23,42,.18)}
.rnlab .rn-stage canvas{display:block;width:100%;height:auto;touch-action:none}
.rnlab .rn-ctrl{display:flex;flex-wrap:wrap;align-items:center;gap:10px 18px;padding:10px 12px;background:#faf7f2;border-radius:12px;border:1px solid var(--line);margin-bottom:10px}
.rnlab .rn-range{display:flex;align-items:center;gap:8px;flex:1 1 240px;min-width:220px}
.rnlab .rn-range label{font-size:12px;font-weight:700;color:var(--ink-2);white-space:nowrap}
.rnlab .rn-range input{flex:1;min-width:80px;cursor:pointer}
.rnlab .rn-val{font-size:12px;font-weight:800;color:#2563eb;min-width:68px;text-align:right;white-space:nowrap;font-variant-numeric:tabular-nums}
.rnlab .rn-tasks{display:flex;flex-wrap:wrap;gap:7px;margin-bottom:4px}
.rnlab .rn-task{font-size:11.5px;font-weight:700;padding:4px 10px;border-radius:9px;background:#f5f0e7;color:var(--ink-3)}
.rnlab .rn-task.done{background:#ecfdf5;color:#059669;border:1px solid #a7f3d0}
.rnlab .rn-insight{margin-top:12px;padding:14px;border-radius:13px;background:linear-gradient(135deg,#f0fdf4 0%,#eff6ff 100%);border:1px solid #bbf7d0}
.rnlab .rn-insight-q{font-size:15px;font-weight:900;color:var(--ink);margin:4px 0 6px;line-height:1.5}
.rnlab .rn-insight-b{font-size:12.5px;color:var(--ink-2);margin:0 0 10px;line-height:1.65}
.rnlab .rn-recap{border:1px solid var(--line);border-radius:12px;padding:11px 13px;background:#fffdf9;margin-bottom:8px}
.rnlab .hidden{display:none !important}
`;

export async function renderRelativityNuclearLab(view) {
  const KEYS = ['clock', 'foil', 'fission'];
  const state = {
    tab: 'clock',
    guesses: { clock: null, foil: null, fission: null },
    correct: { clock: 'slower', foil: 'empty', fission: 'rods' },
    done: { clock: false, foil: false, fission: false },
    tasks: { clLow: false, clHigh: false, foPlum: false, foNuc: false, fiBoom: false, fiControl: false },
  };
  let disposed = false, rafId = 0;

  const root = el('div', { class: 'rnlab' });
  const st = document.createElement('style'); st.textContent = LAB_CSS; root.appendChild(st);
  const dots = KEYS.map(() => el('span', { class: 'rn-dot' }));
  const progTxt = el('span', { text: '已探索 0 / 3' });
  root.appendChild(el('div', { class: 'topbar' }, [
    el('button', { class: 'back', text: '‹', onclick: () => { if (history.length > 1) history.back(); else navigate('#/subjects'); } }),
    el('div', { style: 'flex:1;min-width:0' }, [
      el('h1', { text: '相对论与核风暴' }),
      el('div', { class: 'sub', text: '爱因斯坦光钟 · 卢瑟福金箔散射 · 核裂变控制棒' }),
    ]),
    el('div', { class: 'rn-pill' }, [...dots, progTxt]),
  ]));

  const body = el('div', { html: `
  <nav class="rn-tabs">
    <button type="button" class="rn-tab active" data-tab="clock">⏱️ 1. 爱因斯坦光钟 <span class="chk hidden" data-chk="clock">✓</span></button>
    <button type="button" class="rn-tab" data-tab="foil">✨ 2. 卢瑟福金箔散射 <span class="chk hidden" data-chk="foil">✓</span></button>
    <button type="button" class="rn-tab" data-tab="fission">☢️ 3. 核裂变控制棒 <span class="chk hidden" data-chk="fission">✓</span></button>
    <button type="button" class="rn-tab" data-tab="summary">🏆 专题总结</button>
  </nav>

  <section class="panel" data-pane="clock">
    <div style="font-size:17px;font-weight:800;margin-bottom:4px">爱因斯坦光钟：为什么飞船越接近光速，时间走得越慢？</div>
    <div style="font-size:12.5px;color:var(--ink-2)">两台光钟靠光子在上下镜面间反射计“滴答”。拖动飞船速度到 0.90c，对比地球时间与飞船时间！</div>
    <div class="rn-predict">
      <div class="rn-predict-q">① 先猜一猜：飞船以 0.87 倍光速狂飙，光速 c 不变，地球人看飞船里的时钟会怎样？</div>
      <div class="rn-opts" data-lab="clock">
        <button type="button" class="rn-opt" data-val="same">全宇宙时间统一，走得一样快</button>
        <button type="button" class="rn-opt" data-val="slower">光子要走更长的斜线，飞船时钟慢了一半！</button>
      </div>
    </div>
    <div class="rn-stage"><canvas data-cv="clock" width="740" height="310"></canvas></div>
    <div class="rn-ctrl">
      <div class="rn-range"><label>飞船速度 v/c</label><input data-in="clV" type="range" min="0" max="0.95" value="0.00" step="0.05"><span class="rn-val" data-out="clV">0.00 c</span></div>
      <button type="button" class="btn sm ghost" data-act="clReset">重置计时</button>
    </div>
    <div class="rn-tasks">
      <span class="rn-task" data-task="cl1">○ 目标 1：在低速（≤ 0.2c）观察两台时钟几乎同步</span>
      <span class="rn-task" data-task="cl2">○ 目标 2：把飞船拉到 ≥ 0.85c，亲眼看斜锯齿拉长、飞船变慢</span>
    </div>
    <div class="rn-insight hidden" data-insight="clock">
      <div style="font-size:11px;font-weight:800;color:#059669">✦ 顿悟时刻已解锁</div>
      <div class="rn-insight-q">“光速永远不变，飞船跑得越快，光子走过的斜边越长——于是‘一滴答’被硬生生拉慢了！”</div>
      <p class="rn-insight-b">用初中勾股定理就能推导出狭义相对论时间膨胀公式 <code>Δt' = Δt / √(1 - v²/c²)</code>。北斗与 GPS 卫星每天都必须扣除相对论时钟误差，否则导航每天漂移 11 公里。</p>
      <div class="row-between" style="gap:8px;flex-wrap:wrap"><span style="font-size:11.5px;font-weight:700;color:#2563eb" data-guess="clock"></span><button type="button" class="btn sm" data-goto="foil">下一场：卢瑟福金箔散射 →</button></div>
    </div>
  </section>

  <section class="panel hidden" data-pane="foil">
    <div style="font-size:17px;font-weight:800;margin-bottom:4px">卢瑟福金箔散射：凭什么说“原子内部几乎全是空的”？</div>
    <div style="font-size:12.5px;color:var(--ink-2)">先看旧的「汤姆孙枣糕模型」，再切换到「卢瑟福核式模型」，盯紧偶尔撞上极小原子核后大角度弹回的 α 粒子！</div>
    <div class="rn-predict">
      <div class="rn-predict-q">① 先猜一猜：用高速 α 粒子轰击极薄金箔，极少数粒子竟然反弹回来，说明原子内部结构是？</div>
      <div class="rn-opts" data-lab="foil">
        <button type="button" class="rn-opt" data-val="solid">原子是实心硬球，粒子撞墙弹回</button>
        <button type="button" class="rn-opt" data-val="empty">绝大部分是空的，但中心藏着极小、极重、带正电的原子核</button>
      </div>
    </div>
    <div class="rn-stage"><canvas data-cv="foil" width="740" height="310"></canvas></div>
    <div class="rn-ctrl">
      <button type="button" class="btn sm" style="background:#7c3aed" data-act="foMode">当前：汤姆孙枣糕模型（点击切换）</button>
      <button type="button" class="btn sm ghost" data-act="foBurst">发射 α 粒子脉冲</button>
    </div>
    <div class="rn-tasks">
      <span class="rn-task" data-task="fo1">○ 目标 1：在枣糕模型下观察粒子几乎全部直穿</span>
      <span class="rn-task" data-task="fo2">○ 目标 2：切换到核式模型，亲眼看到大角度反弹星芒</span>
    </div>
    <div class="rn-insight hidden" data-insight="foil">
      <div style="font-size:11px;font-weight:800;color:#059669">✦ 顿悟时刻已解锁</div>
      <div class="rn-insight-q">“像拿炮弹打薄纸却弹回来砸中自己——99.9% 的空间都是空的，重量全挤在针尖大的原子核里。”</div>
      <p class="rn-insight-b">如果把原子放大成一座足球场，原子核只有场中心一颗绿豆那么大，却集中了 99.95% 以上的质量。卢瑟福由此开启了核物理时代。</p>
      <div class="row-between" style="gap:8px;flex-wrap:wrap"><span style="font-size:11.5px;font-weight:700;color:#2563eb" data-guess="foil"></span><button type="button" class="btn sm" data-goto="fission">下一场：核裂变控制棒 →</button></div>
    </div>
  </section>

  <section class="panel hidden" data-pane="fission">
    <div style="font-size:17px;font-weight:800;margin-bottom:4px">铀-235 核裂变：如何驯服 1 变 3 的指数级链式雪崩？</div>
    <div style="font-size:12.5px;color:var(--ink-2)">先拔出硼控制棒（0%）发射一颗中子体验失控雪崩，再把控制棒插入 65% 左右稳住核电站安全发电！</div>
    <div class="rn-predict">
      <div class="rn-predict-q">① 先猜一猜：核电站和原子弹都用铀-235 裂变，核电站靠什么避免发生爆炸？</div>
      <div class="rn-opts" data-lab="fission">
        <button type="button" class="rn-opt" data-val="ice">靠大量冷水把反应堆冻住</button>
        <button type="button" class="rn-opt" data-val="rods">用硼/镉控制棒精准吸收多余中子，让每次裂变只保留 1 颗中子继续反应</button>
      </div>
    </div>
    <div class="rn-stage"><canvas data-cv="fission" width="740" height="310"></canvas></div>
    <div class="rn-ctrl">
      <div class="rn-range"><label>硼控制棒插入深度</label><input data-in="fiRod" type="range" min="0" max="90" value="0" step="10"><span class="rn-val" data-out="fiRod">0% (拔出)</span></div>
      <button type="button" class="btn sm" style="background:#dc2626" data-act="fiFire">☢️ 发射中子引发裂变</button>
      <button type="button" class="btn sm ghost" data-act="fiReset">装填新铀核</button>
    </div>
    <div class="rn-tasks">
      <span class="rn-task" data-task="fi1">○ 目标 1：拔出控制棒（0%）引发一次链式裂变雪崩</span>
      <span class="rn-task" data-task="fi2">○ 目标 2：把控制棒插到 ≥ 60% 再发射，观察中子被吸收稳态运行</span>
    </div>
    <div class="rn-insight hidden" data-insight="fission">
      <div style="font-size:11px;font-weight:800;color:#059669">✦ 顿悟时刻已解锁</div>
      <div class="rn-insight-q">“1 变 3、3 变 9 是原子弹；靠控制棒吸走多余中子稳在 1 变 1，就是清洁核电站。”</div>
      <p class="rn-insight-b">每次铀-235 裂变释放 2–3 颗中子与巨大质量亏损能量（<code>E = Δmc²</code>）。硼控制棒像“中子海绵”，把增殖系数 <code>k</code> 精准锁在 1.0 实现可控发电。</p>
      <div class="row-between" style="gap:8px;flex-wrap:wrap"><span style="font-size:11.5px;font-weight:700;color:#2563eb" data-guess="fission"></span><button type="button" class="btn sm" data-goto="summary">查看专题总结 🏆</button></div>
    </div>
  </section>

  <section class="panel hidden" data-pane="summary">
    <div style="text-align:center;margin-bottom:12px">
      <div style="font-size:18px;font-weight:900" data-sum="title">探索进行中：已完成 0 / 3 场近代物理实验</div>
      <div style="font-size:12.5px;color:var(--ink-2);margin-top:4px">从时间膨胀、原子核结构到受控核裂变，近代物理彻底改写了人类对时空与能量的认知。</div>
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
  function updateGuess(lab) { const o = $(`[data-guess="${lab}"]`); if (!o) return; const g = state.guesses[lab]; o.textContent = !g ? '下次可先做直觉押注再动手！' : (g === state.correct[lab] ? '🎯 直觉押注命中真相！' : '💡 实验反转了刚才的直觉！'); }
  function setTask(n, ok, txt) { const t = $(`[data-task="${n}"]`); t.classList.toggle('done', ok); t.textContent = (ok ? '✓ ' : '○ ') + txt; }
  function updateProgress() {
    let n = 0;
    KEYS.forEach((k, i) => { const ok = state.done[k]; if (ok) n++; dots[i].classList.toggle('done', ok); $(`[data-chk="${k}"]`).classList.toggle('hidden', !ok); $(`[data-insight="${k}"]`).classList.toggle('hidden', !ok); if (ok) updateGuess(k); });
    progTxt.textContent = `已探索 ${n} / 3`;
  }
  function switchTab(name) {
    state.tab = name;
    $$('.rn-tab').forEach((b) => b.classList.toggle('active', b.dataset.tab === name));
    $$('[data-pane]').forEach((p) => p.classList.toggle('hidden', p.dataset.pane !== name));
    if (name === 'summary') renderSummary();
  }
  $$('.rn-tab').forEach((b) => b.addEventListener('click', () => switchTab(b.dataset.tab)));
  $$('[data-goto]').forEach((b) => b.addEventListener('click', () => switchTab(b.dataset.goto)));
  $$('.rn-opts').forEach((w) => {
    const lab = w.dataset.lab;
    w.querySelectorAll('.rn-opt').forEach((btn) => btn.addEventListener('click', () => {
      state.guesses[lab] = btn.dataset.val; w.querySelectorAll('.rn-opt').forEach((x) => x.classList.toggle('picked', x === btn)); updateGuess(lab);
    }));
  });

  /* ---- 1. LIGHT CLOCK ---- */
  const cCl = $('[data-cv="clock"]'), ctxCl = cCl.getContext('2d');
  const cl = { vc: 0.0, tEarth: 0, tShip: 0, shipX: 300, trail: [] };
  function checkCl() {
    setTask('cl1', state.tasks.clLow, '目标 1：低速（≤ 0.2c）观察两台时钟同步');
    setTask('cl2', state.tasks.clHigh, '目标 2：飞船拉到 ≥ 0.85c 亲眼看时间变慢');
    if (state.tasks.clLow && state.tasks.clHigh && !state.done.clock) { state.done.clock = true; updateProgress(); }
  }
  $('[data-in="clV"]').addEventListener('input', (e) => {
    cl.vc = Number(e.target.value); $('[data-out="clV"]').textContent = `${cl.vc.toFixed(2)} c`;
    cl.trail = [];
    if (cl.vc <= 0.2) state.tasks.clLow = true;
    if (cl.vc >= 0.85) state.tasks.clHigh = true;
    checkCl();
  });
  $('[data-act="clReset"]').addEventListener('click', () => { cl.tEarth = 0; cl.tShip = 0; cl.shipX = 300; cl.trail = []; });

  /* ---- 2. RUTHERFORD FOIL ---- */
  const cFo = $('[data-cv="foil"]'), ctxFo = cFo.getContext('2d');
  const fo = { nuclear: false, ps: [], bounces: 0, flashes: [] };
  const nuclei = [{ x: 430, y: 90 }, { x: 430, y: 155 }, { x: 430, y: 220 }];
  function spawnAlpha(n = 14) {
    for (let i = 0; i < n; i++) fo.ps.push({ x: 40 - Math.random() * 60, y: 55 + Math.random() * 200, vx: 5.8, vy: 0, hit: false });
  }
  function checkFo() {
    setTask('fo1', state.tasks.foPlum, '目标 1：枣糕模型下观察粒子几乎直穿');
    setTask('fo2', state.tasks.foNuc, '目标 2：核式模型下观察大角度反弹星芒');
    if (state.tasks.foPlum && state.tasks.foNuc && !state.done.foil) { state.done.foil = true; updateProgress(); }
  }
  $('[data-act="foMode"]').addEventListener('click', (e) => {
    fo.nuclear = !fo.nuclear; fo.ps = []; fo.bounces = 0;
    e.currentTarget.textContent = fo.nuclear ? '当前：卢瑟福核式模型（点击切换）' : '当前：汤姆孙枣糕模型（点击切换）';
    spawnAlpha(18);
  });
  $('[data-act="foBurst"]').addEventListener('click', () => spawnAlpha(22));

  /* ---- 3. NUCLEAR FISSION ---- */
  const cFi = $('[data-cv="fission"]'), ctxFi = cFi.getContext('2d');
  const fi = { rod: 0, atoms: [], neutrons: [], splits: 0, flashes: [] };
  function resetAtoms() {
    fi.atoms = []; fi.neutrons = []; fi.splits = 0; fi.flashes = [];
    for (let gx = 160; gx <= 620; gx += 75) {
      for (let gy = 62; gy <= 226; gy += 55) fi.atoms.push({ x: gx + (Math.random() - 0.5) * 18, y: gy + (Math.random() - 0.5) * 14, alive: true });
    }
  }
  function checkFi() {
    setTask('fi1', state.tasks.fiBoom, '目标 1：控制棒 0% 引发链式裂变雪崩');
    setTask('fi2', state.tasks.fiControl, '目标 2：插入控制棒 ≥ 60% 吸收多余中子');
    if (state.tasks.fiBoom && state.tasks.fiControl && !state.done.fission) { state.done.fission = true; updateProgress(); }
  }
  $('[data-in="fiRod"]').addEventListener('input', (e) => {
    fi.rod = Number(e.target.value); $('[data-out="fiRod"]').textContent = fi.rod === 0 ? '0% (拔出)' : `${fi.rod}%`;
  });
  $('[data-act="fiFire"]').addEventListener('click', () => {
    fi.neutrons.push({ x: 40, y: 155, vx: 4.5, vy: (Math.random() - 0.5) * 0.4 });
  });
  $('[data-act="fiReset"]').addEventListener('click', resetAtoms);

  function loop() {
    if (disposed) return;

    if (state.tab === 'clock') {
      if (cl.vc <= 0.2) state.tasks.clLow = true;
      checkCl();
      const gamma = 1 / Math.sqrt(Math.max(0.05, 1 - cl.vc * cl.vc));
      cl.tEarth += 0.032; cl.tShip += 0.032 / gamma;
      cl.shipX += cl.vc * 3.2;
      if (cl.shipX > 650) { cl.shipX = 280; cl.trail = []; }
      const yTop = 85, yBot = 225, span = yBot - yTop;
      const triWave = (t) => { const p = t % 2; return p < 1 ? p : 2 - p; };
      const ey = yTop + triWave(cl.tEarth) * span;
      const sy = yTop + triWave(cl.tShip) * span;
      cl.trail.push({ x: cl.shipX, y: sy }); if (cl.trail.length > 160) cl.trail.shift();

      ctxCl.clearRect(0, 0, cCl.width, cCl.height); ctxCl.fillStyle = '#0b1120'; ctxCl.fillRect(0, 0, cCl.width, cCl.height);
      // Earth clock (left)
      ctxCl.fillStyle = '#94a3b8'; ctxCl.fillRect(90, yTop - 6, 70, 6); ctxCl.fillRect(90, yBot, 70, 6);
      ctxCl.strokeStyle = 'rgba(56,189,248,0.3)'; ctxCl.beginPath(); ctxCl.moveTo(125, yTop); ctxCl.lineTo(125, yBot); ctxCl.stroke();
      ctxCl.fillStyle = '#38bdf8'; ctxCl.shadowColor = '#38bdf8'; ctxCl.shadowBlur = 12;
      ctxCl.beginPath(); ctxCl.arc(125, ey, 6, 0, Math.PI * 2); ctxCl.fill(); ctxCl.shadowBlur = 0;
      ctxCl.fillStyle = '#7dd3fc'; ctxCl.font = FS.label; ctxCl.fillText(`地球时间：${cl.tEarth.toFixed(1)} s`, 64, 266);

      // Ship clock (moving right)
      ctxCl.fillStyle = '#a78bfa'; ctxCl.fillRect(cl.shipX - 35, yTop - 6, 70, 6); ctxCl.fillRect(cl.shipX - 35, yBot, 70, 6);
      if (cl.trail.length > 1) {
        ctxCl.strokeStyle = 'rgba(251,191,36,0.75)'; ctxCl.lineWidth = 2; ctxCl.beginPath();
        cl.trail.forEach((p, i) => (i ? ctxCl.lineTo(p.x, p.y) : ctxCl.moveTo(p.x, p.y))); ctxCl.stroke();
      }
      ctxCl.fillStyle = '#fde047'; ctxCl.shadowColor = '#fde047'; ctxCl.shadowBlur = 12;
      ctxCl.beginPath(); ctxCl.arc(cl.shipX, sy, 6, 0, Math.PI * 2); ctxCl.fill(); ctxCl.shadowBlur = 0;

      canvasHud(ctxCl, {
        x: 724, y: 12, align: 'right', lh: 32, bg: 'rgba(15,23,42,0.88)', stroke: '#243044',
        lines: [{ text: `飞船速度 ${cl.vc.toFixed(2)}c · γ = ${gamma.toFixed(2)}× · 飞船时间 ${cl.tShip.toFixed(1)} s`, font: FS.hudSub, color: '#ddd6fe' }],
      });
    }

    if (state.tab === 'foil') {
      if (fo.ps.length < 18) spawnAlpha(2);
      ctxFo.clearRect(0, 0, cFo.width, cFo.height); ctxFo.fillStyle = '#0b1120'; ctxFo.fillRect(0, 0, cFo.width, cFo.height);
      ctxFo.fillStyle = 'rgba(251,191,36,0.12)'; ctxFo.fillRect(405, 30, 50, 250);
      nuclei.forEach((nu) => {
        if (!fo.nuclear) {
          ctxFo.fillStyle = 'rgba(251,191,36,0.22)'; ctxFo.beginPath(); ctxFo.arc(nu.x, nu.y, 26, 0, Math.PI * 2); ctxFo.fill();
        } else {
          ctxFo.strokeStyle = 'rgba(148,163,184,0.2)'; ctxFo.beginPath(); ctxFo.arc(nu.x, nu.y, 26, 0, Math.PI * 2); ctxFo.stroke();
          ctxFo.fillStyle = '#f59e0b'; ctxFo.shadowColor = '#f59e0b'; ctxFo.shadowBlur = 10;
          ctxFo.beginPath(); ctxFo.arc(nu.x, nu.y, 6, 0, Math.PI * 2); ctxFo.fill(); ctxFo.shadowBlur = 0;
        }
      });
      const alive = [];
      for (const p of fo.ps) {
        p.x += p.vx; p.y += p.vy;
        if (fo.nuclear && !p.hit) {
          for (const nu of nuclei) {
            const dx = p.x - nu.x, dy = p.y - nu.y, d = Math.hypot(dx, dy);
            if (d < 14) {
              p.hit = true; fo.bounces++; state.tasks.foNuc = true; checkFo();
              const ang = Math.atan2(dy, dx) + (Math.random() - 0.5) * 0.4;
              p.vx = Math.cos(ang) * 5.6; p.vy = Math.sin(ang) * 5.6;
              fo.flashes.push({ x: nu.x, y: nu.y, r: 4, a: 1 });
            }
          }
        }
        ctxFo.fillStyle = p.hit ? '#f87171' : '#38bdf8';
        ctxFo.beginPath(); ctxFo.arc(p.x, p.y, 3.2, 0, Math.PI * 2); ctxFo.fill();
        if (p.x > 0 && p.x < 740 && p.y > 0 && p.y < 310) alive.push(p);
        else if (!fo.nuclear && p.x >= 740) { state.tasks.foPlum = true; checkFo(); }
      }
      fo.ps = alive;
      fo.flashes.forEach((f) => { f.r += 2.2; f.a -= 0.06; ctxFo.strokeStyle = `rgba(253,224,71,${f.a})`; ctxFo.lineWidth = 2; ctxFo.beginPath(); ctxFo.arc(f.x, f.y, f.r, 0, Math.PI * 2); ctxFo.stroke(); });
      fo.flashes = fo.flashes.filter((f) => f.a > 0);
      ctxFo.fillStyle = '#fde047'; ctxFo.font = FS.label;
      ctxFo.fillText(fo.nuclear ? `核式模型：大角度反弹 ${fo.bounces} 次` : '枣糕模型：正电荷弥散，粒子几乎全直穿', 22, 40);
    }

    if (state.tab === 'fission') {
      ctxFi.clearRect(0, 0, cFi.width, cFi.height); ctxFi.fillStyle = '#0b1120'; ctxFi.fillRect(0, 0, cFi.width, cFi.height);
      // Boron control rods dropping from top
      const rodH = (fi.rod / 100) * 265;
      const rodXs = [235, 385, 535];
      if (rodH > 4) {
        ctxFi.fillStyle = '#475569'; ctxFi.strokeStyle = '#94a3b8'; ctxFi.lineWidth = 2;
        rodXs.forEach((rx) => { ctxFi.fillRect(rx - 7, 0, 14, rodH); ctxFi.strokeRect(rx - 7, 0, 14, rodH); });
      }
      // U-235 atoms
      fi.atoms.forEach((a) => {
        if (!a.alive) return;
        ctxFi.fillStyle = '#34d399'; ctxFi.beginPath(); ctxFi.arc(a.x, a.y, 13, 0, Math.PI * 2); ctxFi.fill();
        ctxFi.fillStyle = '#064e3b'; ctxFi.font = '800 16px sans-serif'; ctxFi.textAlign = 'center'; ctxFi.fillText('U', a.x, a.y + 6); ctxFi.textAlign = 'left';
      });
      // Neutrons
      const nextN = [];
      for (const n of fi.neutrons) {
        n.x += n.vx; n.y += n.vy;
        let absorbed = false;
        if (rodH > 4 && n.y < rodH) {
          for (const rx of rodXs) {
            if (Math.abs(n.x - rx) < 10) {
              absorbed = true;
              if (fi.rod >= 60) { state.tasks.fiControl = true; checkFi(); }
              break;
            }
          }
        }
        if (absorbed) continue;
        let hitAtom = false;
        for (const a of fi.atoms) {
          if (a.alive && Math.hypot(n.x - a.x, n.y - a.y) < 15) {
            a.alive = false; hitAtom = true; fi.splits++;
            fi.flashes.push({ x: a.x, y: a.y, r: 6, a: 1 });
            for (let k = 0; k < 3; k++) {
              const ang = (Math.random() - 0.5) * Math.PI * 1.4;
              nextN.push({ x: a.x, y: a.y, vx: Math.cos(ang) * 4.2, vy: Math.sin(ang) * 4.2 });
            }
            if (fi.rod === 0 && fi.splits >= 5) { state.tasks.fiBoom = true; checkFi(); }
            break;
          }
        }
        if (!hitAtom && n.x > 0 && n.x < 740 && n.y > 0 && n.y < 310) {
          ctxFi.fillStyle = '#38bdf8'; ctxFi.shadowColor = '#38bdf8'; ctxFi.shadowBlur = 8;
          ctxFi.beginPath(); ctxFi.arc(n.x, n.y, 4, 0, Math.PI * 2); ctxFi.fill(); ctxFi.shadowBlur = 0;
          nextN.push(n);
        }
      }
      fi.neutrons = nextN.slice(0, 80);
      fi.flashes.forEach((f) => { f.r += 2.6; f.a -= 0.05; ctxFi.strokeStyle = `rgba(56,189,248,${f.a})`; ctxFi.lineWidth = 2.5; ctxFi.beginPath(); ctxFi.arc(f.x, f.y, f.r, 0, Math.PI * 2); ctxFi.stroke(); });
      fi.flashes = fi.flashes.filter((f) => f.a > 0);
      ctxFi.fillStyle = '#7dd3fc'; ctxFi.font = FS.label;
      ctxFi.fillText(`已裂变铀核：${fi.splits} · 硼控制棒：${fi.rod}%`, 20, 300);
    }

    rafId = requestAnimationFrame(loop);
  }

  function renderSummary() {
    const dN = KEYS.filter((k) => state.done[k]).length;
    $('[data-sum="title"]').textContent = dN === 3 ? '🏆 相对论与核风暴专题通关！' : `探索进行中：已完成 ${dN} / 3 场实验`;
    const rows = [
      { k: 'clock', t: '1. 爱因斯坦光钟', p: '“光速不变迫使飞船里的斜线光程拉长，于是时间被硬生生拉慢。”' },
      { k: 'foil', t: '2. 卢瑟福金箔散射', p: '“99.9% 的原子都是空的，质量几乎全挤在针尖大的原子核里。”' },
      { k: 'fission', t: '3. 核裂变控制棒', p: '“1 变 3 是雪崩，用硼控制棒稳在 1 变 1 就是核电站。”' },
    ];
    $('[data-sum="list"]').innerHTML = rows.map((r) => `<div class="rn-recap"><div style="font-size:13.5px;font-weight:800">${state.done[r.k] ? '✅ ' : '🔒 '}${r.t}</div><div style="font-size:12.5px;color:var(--ink-2);margin-top:3px">${state.done[r.k] ? r.p : '完成对应实验探索后解锁'}</div></div>`).join('');
  }
  $('[data-act="resetAll"]').addEventListener('click', () => {
    KEYS.forEach((k) => { state.guesses[k] = null; state.done[k] = false; });
    state.tasks = { clLow: false, clHigh: false, foPlum: false, foNuc: false, fiBoom: false, fiControl: false };
    $$('.rn-opt').forEach((b) => b.classList.remove('picked'));
    resetAtoms(); checkCl(); checkFo(); checkFi(); updateProgress(); renderSummary(); switchTab('clock');
  });
  $('[data-act="backSubjects"]').addEventListener('click', () => navigate('#/subjects'));

  view.innerHTML = ''; view.appendChild(root);
  resetAtoms(); checkCl(); checkFo(); checkFi(); updateProgress();
  rafId = requestAnimationFrame(loop);
  mountLabBonus(root, '.rn-tabs');
  return () => { disposed = true; cancelAnimationFrame(rafId); };
}
