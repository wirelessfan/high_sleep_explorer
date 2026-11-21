/* 专题 D：热学与微观宇宙（布朗运动显形 + 麦克斯韦妖守门 + 绝热压缩点火） */

import { el } from '../ui.js';
import { navigate } from '../router.js';
import { FS } from '../lab-canvas.js';
import { mountLabBonus } from '../lab-bonus.js';

const LAB_CSS = `
.thlab{display:flex;flex-direction:column;gap:12px}
.thlab .th-pill{display:inline-flex;align-items:center;gap:6px;padding:5px 11px;border-radius:999px;background:#fff;border:1px solid var(--line);font-size:12px;font-weight:700;color:var(--ink-2)}
.thlab .th-dot{width:8px;height:8px;border-radius:50%;background:#d6c7b2;transition:background .2s}
.thlab .th-dot.done{background:#059669}
.thlab .th-tabs{display:flex;flex-wrap:wrap;gap:7px}
.thlab .th-tab{appearance:none;border:1px solid var(--line);background:#fff;color:var(--ink-2);padding:7px 12px;border-radius:999px;font-size:12px;font-weight:700;cursor:pointer;display:inline-flex;align-items:center;gap:5px}
.thlab .th-tab.active{background:#0f172a;border-color:#f97316;color:#fdba74}
.thlab .th-tab .chk{font-size:10.5px;padding:1px 5px;border-radius:999px;background:#ecfdf5;color:#059669}
.thlab .th-tab.active .chk{background:rgba(249,115,22,.24);color:#fdba74}
.thlab .th-predict{background:#faf6ef;border:1px dashed #dfcfb7;border-radius:12px;padding:11px 12px;margin:10px 0 12px}
.thlab .th-predict-q{font-size:13px;font-weight:800;margin:0 0 8px;color:var(--ink)}
.thlab .th-opts{display:flex;flex-wrap:wrap;gap:7px}
.thlab .th-opt{appearance:none;background:#fff;border:1px solid #dfd2be;color:var(--ink-2);padding:6px 11px;border-radius:9px;font-size:12px;font-weight:700;cursor:pointer}
.thlab .th-opt.picked{background:#eff6ff;border-color:#2563eb;color:#2563eb}
.thlab .th-stage{border-radius:14px;overflow:hidden;border:1px solid #1e293b;background:#0b1120;margin-bottom:12px;box-shadow:0 8px 24px rgba(15,23,42,.18)}
.thlab .th-stage canvas{display:block;width:100%;height:auto;touch-action:none}
.thlab .th-ctrl{display:flex;flex-wrap:wrap;align-items:center;gap:10px 18px;padding:10px 12px;background:#faf7f2;border-radius:12px;border:1px solid var(--line);margin-bottom:10px}
.thlab .th-range{display:flex;align-items:center;gap:8px;flex:1 1 240px;min-width:220px}
.thlab .th-range label{font-size:12px;font-weight:700;color:var(--ink-2);white-space:nowrap}
.thlab .th-range input{flex:1;min-width:80px;cursor:pointer}
.thlab .th-val{font-size:12px;font-weight:800;color:#2563eb;min-width:64px;text-align:right;white-space:nowrap;font-variant-numeric:tabular-nums}
.thlab .th-tasks{display:flex;flex-wrap:wrap;gap:7px;margin-bottom:4px}
.thlab .th-task{font-size:11.5px;font-weight:700;padding:4px 10px;border-radius:9px;background:#f5f0e7;color:var(--ink-3)}
.thlab .th-task.done{background:#ecfdf5;color:#059669;border:1px solid #a7f3d0}
.thlab .th-insight{margin-top:12px;padding:14px;border-radius:13px;background:linear-gradient(135deg,#f0fdf4 0%,#eff6ff 100%);border:1px solid #bbf7d0}
.thlab .th-insight-q{font-size:15px;font-weight:900;color:var(--ink);margin:4px 0 6px;line-height:1.5}
.thlab .th-insight-b{font-size:12.5px;color:var(--ink-2);margin:0 0 10px;line-height:1.65}
.thlab .th-recap{border:1px solid var(--line);border-radius:12px;padding:11px 13px;background:#fffdf9;margin-bottom:8px}
.thlab .hidden{display:none !important}
`;

export async function renderThermalMicroLab(view) {
  const KEYS = ['brown', 'demon', 'piston'];
  const state = {
    tab: 'brown',
    guesses: { brown: null, demon: null, piston: null },
    correct: { brown: 'molecules', demon: 'work', piston: 'workheat' },
    done: { brown: false, demon: false, piston: false },
    tasks: { brReveal: false, brHot: false, dmGate: false, dmSep: false, pisSlow: false, pisIgnite: false },
  };
  let disposed = false, rafId = 0;

  const root = el('div', { class: 'thlab' });
  const st = document.createElement('style'); st.textContent = LAB_CSS; root.appendChild(st);
  const dots = KEYS.map(() => el('span', { class: 'th-dot' }));
  const progTxt = el('span', { text: '已探索 0 / 3' });
  root.appendChild(el('div', { class: 'topbar' }, [
    el('button', { class: 'back', text: '‹', onclick: () => { if (history.length > 1) history.back(); else navigate('#/subjects'); } }),
    el('div', { style: 'flex:1;min-width:0' }, [
      el('h1', { text: '热学与微观宇宙' }),
      el('div', { class: 'sub', text: '布朗运动显形 · 麦克斯韦妖 · 柴油机绝热点火' }),
    ]),
    el('div', { class: 'th-pill' }, [...dots, progTxt]),
  ]));

  const body = el('div', { html: `
  <nav class="th-tabs">
    <button type="button" class="th-tab active" data-tab="brown">🔬 1. 布朗运动显形 <span class="chk hidden" data-chk="brown">✓</span></button>
    <button type="button" class="th-tab" data-tab="demon">😈 2. 麦克斯韦妖 <span class="chk hidden" data-chk="demon">✓</span></button>
    <button type="button" class="th-tab" data-tab="piston">🔥 3. 绝热压缩点火 <span class="chk hidden" data-chk="piston">✓</span></button>
    <button type="button" class="th-tab" data-tab="summary">🏆 专题总结</button>
  </nav>

  <section class="panel" data-pane="brown">
    <div style="font-size:17px;font-weight:800;margin-bottom:4px">布朗运动：水里的花粉颗粒为什么像喝醉了一样乱抖？</div>
    <div style="font-size:12.5px;color:var(--ink-2)">显微镜下先看“隐身分子”模式，再一键让看不见的水分子显形，并调高温度看花粉折线如何暴走！</div>
    <div class="th-predict">
      <div class="th-predict-q">① 先猜一猜：花粉颗粒在静止清水里不停随机乱撞，到底是谁在推它？</div>
      <div class="th-opts" data-lab="brown">
        <button type="button" class="th-opt" data-val="alive">花粉自己有生命在游动</button>
        <button type="button" class="th-opt" data-val="molecules">四周看不见的水分子热运动撞击不平衡</button>
      </div>
    </div>
    <div class="th-stage"><canvas data-cv="brown" width="740" height="310"></canvas></div>
    <div class="th-ctrl">
      <div class="th-range"><label>水温 T</label><input data-in="brT" type="range" min="10" max="95" value="25" step="5"><span class="th-val" data-out="brT">25 °C</span></div>
      <button type="button" class="btn sm" data-act="brReveal">显示隐身水分子</button>
      <button type="button" class="btn sm ghost" data-act="brClear">清空轨迹</button>
    </div>
    <div class="th-tasks">
      <span class="th-task" data-task="br1">○ 目标 1：点击「显示隐身水分子」看清撞击真相</span>
      <span class="th-task" data-task="br2">○ 目标 2：把水温拉到 ≥ 75°C，观察分子狂飙与花粉剧烈抖动</span>
    </div>
    <div class="th-insight hidden" data-insight="brown">
      <div style="font-size:11px;font-weight:800;color:#059669">✦ 顿悟时刻已解锁</div>
      <div class="th-insight-q">“布朗运动不是分子本身在跑，而是肉眼可见的颗粒替亿万隐身分子当了‘传话筒’。”</div>
      <p class="th-insight-b">温度越高，液体分子无规则热运动越剧烈、撞击越不平衡，花粉颗粒折线越狂乱。爱因斯坦 1905 年用数学定量解释布朗运动，一举证实了原子分子的真实存在。</p>
      <div class="row-between" style="gap:8px;flex-wrap:wrap"><span style="font-size:11.5px;font-weight:700;color:#2563eb" data-guess="brown"></span><button type="button" class="btn sm" data-goto="demon">下一场：麦克斯韦妖 →</button></div>
    </div>
  </section>

  <section class="panel hidden" data-pane="demon">
    <div style="font-size:17px;font-weight:800;margin-bottom:4px">麦克斯韦妖：你能靠开关小门把“冷热分子”彻底分开吗？</div>
    <div style="font-size:12.5px;color:var(--ink-2)">红球是高温快分子，蓝球是低温慢分子。点击「打开 / 关闭小门」试着只让红球去右边、蓝球留左边！</div>
    <div class="th-predict">
      <div class="th-predict-q">① 先猜一猜：如果不靠外力也不靠小妖精挑拣，把小门一直敞开，冷热分子会自动分到两边吗？</div>
      <div class="th-opts" data-lab="demon">
        <button type="button" class="th-opt" data-val="auto">等久了可能会自己分开</button>
        <button type="button" class="th-opt" data-val="work">绝不会自发分开，只会越混越均匀（熵增定律）</button>
      </div>
    </div>
    <div class="th-stage"><canvas data-cv="demon" width="740" height="310"></canvas></div>
    <div class="th-ctrl">
      <button type="button" class="btn sm" style="background:#f97316" data-act="dmGate">当前：小门关闭（点击打开）</button>
      <button type="button" class="btn sm ghost" data-act="dmAuto">开启自动小妖演示</button>
      <button type="button" class="btn sm ghost" data-act="dmReset">重新混合</button>
    </div>
    <div class="th-tasks">
      <span class="th-task" data-task="dm1">○ 目标 1：手动开关小门至少 2 次感受分子乱窜</span>
      <span class="th-task" data-task="dm2">○ 目标 2：把右室平均温度拉到比左室高 ≥ 20°C（可开自动小妖）</span>
    </div>
    <div class="th-insight hidden" data-insight="demon">
      <div style="font-size:11px;font-weight:800;color:#059669">✦ 顿悟时刻已解锁</div>
      <div class="th-insight-q">“热量自发混合轻而易举，想逆转熵增必须付出能量或信息代价——宇宙没有免费空调。”</div>
      <p class="th-insight-b">自然界孤立系统总是走向更混乱（熵增）。即使有麦克斯韦妖，它“看清分子速度并清空记忆”也要消耗能量并产生更多熵，热力学第二定律依然牢不可破。</p>
      <div class="row-between" style="gap:8px;flex-wrap:wrap"><span style="font-size:11.5px;font-weight:700;color:#2563eb" data-guess="demon"></span><button type="button" class="btn sm" data-goto="piston">下一场：绝热压缩点火 →</button></div>
    </div>
  </section>

  <section class="panel hidden" data-pane="piston">
    <div style="font-size:17px;font-weight:800;margin-bottom:4px">绝热压缩点火：不用火柴和火花塞，光靠“压空气”怎么点着火？</div>
    <div style="font-size:12.5px;color:var(--ink-2)">先慢慢下压活塞看散热平衡，再点击「🔥 极速猛压活塞」，看分子撞飞、温度瞬间冲破 500°C 点燃底部棉花！</div>
    <div class="th-predict">
      <div class="th-predict-q">① 先猜一猜：柴油机没有火花塞，是怎么在气缸里把柴油点着的？</div>
      <div class="th-opts" data-lab="piston">
        <button type="button" class="th-opt" data-val="friction">靠活塞和缸壁摩擦打出火星</button>
        <button type="button" class="th-opt" data-val="workheat">极速压缩空气做功，热量来不及散出，空气内能暴涨直接高温自燃</button>
      </div>
    </div>
    <div class="th-stage"><canvas data-cv="piston" width="740" height="310"></canvas></div>
    <div class="th-ctrl">
      <div class="th-range"><label>手动压活塞</label><input data-in="pisPos" type="range" min="0" max="100" value="10" step="1"><span class="th-val" data-out="pisPos">25 °C</span></div>
      <button type="button" class="btn sm" style="background:#dc2626" data-act="pisSlam">🔥 极速猛压点火！</button>
      <button type="button" class="btn sm ghost" data-act="pisReset">拉回活塞</button>
    </div>
    <div class="th-tasks">
      <span class="th-task" data-task="pis1">○ 目标 1：手动慢慢压缩活塞观察温度缓慢回落</span>
      <span class="th-task" data-task="pis2">○ 目标 2：极速猛压冲破 500°C，亲眼点燃缸底棉花</span>
    </div>
    <div class="th-insight hidden" data-insight="piston">
      <div style="font-size:11px;font-weight:800;color:#059669">✦ 顿悟时刻已解锁</div>
      <div class="th-insight-q">“极速压缩时热量来不及逃走，外界做功 100% 灌进空气内能——这就是柴油机不用火花塞的秘密。”</div>
      <p class="th-insight-b">由热力学第一定律 <code>ΔU = W + Q</code>：绝热过程 <code>Q ≈ 0</code>，外界压缩做正功 <code>W &gt; 0</code> 使气体分子平均动能飙升、温度剧增达到燃点。</p>
      <div class="row-between" style="gap:8px;flex-wrap:wrap"><span style="font-size:11.5px;font-weight:700;color:#2563eb" data-guess="piston"></span><button type="button" class="btn sm" data-goto="summary">查看专题总结 🏆</button></div>
    </div>
  </section>

  <section class="panel hidden" data-pane="summary">
    <div style="text-align:center;margin-bottom:12px">
      <div style="font-size:18px;font-weight:900" data-sum="title">探索进行中：已完成 0 / 3 场热学实验</div>
      <div style="font-size:12.5px;color:var(--ink-2);margin-top:4px">从花粉微观抖动、熵增时间之箭到柴油机绝热点火，微观热运动撑起了宏观热力学大厦。</div>
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
    const o = $(`[data-guess="${lab}"]`); if (!o) return;
    const g = state.guesses[lab];
    o.textContent = !g ? '下次可先做直觉押注再动手！' : (g === state.correct[lab] ? '🎯 直觉押注命中真相！' : '💡 实验反转了刚才的直觉！');
  }
  function setTask(n, ok, txt) { const t = $(`[data-task="${n}"]`); t.classList.toggle('done', ok); t.textContent = (ok ? '✓ ' : '○ ') + txt; }
  function updateProgress() {
    let n = 0;
    KEYS.forEach((k, i) => {
      const ok = state.done[k]; if (ok) n++;
      dots[i].classList.toggle('done', ok);
      $(`[data-chk="${k}"]`).classList.toggle('hidden', !ok);
      $(`[data-insight="${k}"]`).classList.toggle('hidden', !ok);
      if (ok) updateGuess(k);
    });
    progTxt.textContent = `已探索 ${n} / 3`;
  }
  function switchTab(name) {
    state.tab = name;
    $$('.th-tab').forEach((b) => b.classList.toggle('active', b.dataset.tab === name));
    $$('[data-pane]').forEach((p) => p.classList.toggle('hidden', p.dataset.pane !== name));
    if (name === 'summary') renderSummary();
  }
  $$('.th-tab').forEach((b) => b.addEventListener('click', () => switchTab(b.dataset.tab)));
  $$('[data-goto]').forEach((b) => b.addEventListener('click', () => switchTab(b.dataset.goto)));
  $$('.th-opts').forEach((w) => {
    const lab = w.dataset.lab;
    w.querySelectorAll('.th-opt').forEach((btn) => btn.addEventListener('click', () => {
      state.guesses[lab] = btn.dataset.val;
      w.querySelectorAll('.th-opt').forEach((x) => x.classList.toggle('picked', x === btn));
      updateGuess(lab);
    }));
  });

  /* ---- 1. BROWNIAN MOTION ---- */
  const cBr = $('[data-cv="brown"]'), ctxBr = cBr.getContext('2d');
  const br = { T: 25, showMol: false, px: 370, py: 155, pvx: 0, pvy: 0, trail: [], mols: [] };
  for (let i = 0; i < 65; i++) br.mols.push({ x: 30 + Math.random() * 680, y: 20 + Math.random() * 270, vx: (Math.random() - 0.5) * 4, vy: (Math.random() - 0.5) * 4 });
  function checkBr() {
    setTask('br1', state.tasks.brReveal, '目标 1：点击「显示隐身水分子」看清撞击真相');
    setTask('br2', state.tasks.brHot, '目标 2：把水温拉到 ≥ 75°C 观察剧烈抖动');
    if (state.tasks.brReveal && state.tasks.brHot && !state.done.brown) { state.done.brown = true; updateProgress(); }
  }
  $('[data-in="brT"]').addEventListener('input', (e) => {
    br.T = Number(e.target.value); $('[data-out="brT"]').textContent = `${br.T} °C`;
    if (br.T >= 75) { state.tasks.brHot = true; checkBr(); }
  });
  $('[data-act="brReveal"]').addEventListener('click', (e) => {
    br.showMol = !br.showMol;
    e.currentTarget.textContent = br.showMol ? '隐藏水分子' : '显示隐身水分子';
    if (br.showMol) { state.tasks.brReveal = true; checkBr(); }
  });
  $('[data-act="brClear"]').addEventListener('click', () => { br.trail = []; br.px = 370; br.py = 155; });

  /* ---- 2. MAXWELL DEMON ---- */
  const cDm = $('[data-cv="demon"]'), ctxDm = cDm.getContext('2d');
  const dm = { open: false, auto: false, clicks: 0, ps: [] };
  function resetDemon() {
    dm.ps = [];
    for (let i = 0; i < 36; i++) {
      const hot = i % 2 === 0;
      const spd = hot ? 4.4 : 1.7, ang = Math.random() * Math.PI * 2;
      dm.ps.push({ x: i < 18 ? 60 + Math.random() * 260 : 420 + Math.random() * 260, y: 40 + Math.random() * 230, vx: Math.cos(ang) * spd, vy: Math.sin(ang) * spd, hot });
    }
  }
  function checkDm() {
    setTask('dm1', state.tasks.dmGate, '目标 1：手动开关小门至少 2 次');
    setTask('dm2', state.tasks.dmSep, '目标 2：使右室比左室温度高 ≥ 20°C');
    if (state.tasks.dmGate && state.tasks.dmSep && !state.done.demon) { state.done.demon = true; updateProgress(); }
  }
  $('[data-act="dmGate"]').addEventListener('click', (e) => {
    dm.auto = false; dm.open = !dm.open; dm.clicks++;
    e.currentTarget.textContent = dm.open ? '当前：小门打开（点击关闭）' : '当前：小门关闭（点击打开）';
    if (dm.clicks >= 2) { state.tasks.dmGate = true; checkDm(); }
  });
  $('[data-act="dmAuto"]').addEventListener('click', (e) => {
    dm.auto = !dm.auto; e.currentTarget.textContent = dm.auto ? '停止自动小妖' : '开启自动小妖演示';
  });
  $('[data-act="dmReset"]').addEventListener('click', () => { dm.auto = false; resetDemon(); });

  /* ---- 3. ADIABATIC PISTON ---- */
  const cPi = $('[data-cv="piston"]'), ctxPi = cPi.getContext('2d');
  const pi = { pos: 10, prevPos: 10, temp: 25, ignited: false, slam: false, mols: [] };
  for (let i = 0; i < 32; i++) pi.mols.push({ x: 180 + Math.random() * 340, y: 120 + Math.random() * 140, vx: (Math.random() - 0.5) * 3, vy: (Math.random() - 0.5) * 3 });
  function checkPi() {
    setTask('pis1', state.tasks.pisSlow, '目标 1：手动慢慢压缩观察散热');
    setTask('pis2', state.tasks.pisIgnite, '目标 2：极速猛压破 500°C 点燃棉花');
    if (state.tasks.pisSlow && state.tasks.pisIgnite && !state.done.piston) { state.done.piston = true; updateProgress(); }
  }
  $('[data-in="pisPos"]').addEventListener('input', (e) => {
    pi.slam = false;
    const v = Number(e.target.value);
    const dv = Math.max(0, v - pi.pos);
    pi.pos = v;
    pi.temp = Math.min(620, pi.temp + dv * 2.2);
    if (pi.pos > 55) { state.tasks.pisSlow = true; checkPi(); }
  });
  $('[data-act="pisSlam"]').addEventListener('click', () => { pi.pos = 10; pi.temp = 25; pi.ignited = false; pi.slam = true; });
  $('[data-act="pisReset"]').addEventListener('click', () => { pi.slam = false; pi.pos = 10; pi.temp = 25; pi.ignited = false; $('[data-in="pisPos"]').value = '10'; });

  function loop() {
    if (disposed) return;

    if (state.tab === 'brown') {
      const spdScale = 0.55 + (br.T / 95) * 2.1;
      ctxBr.clearRect(0, 0, cBr.width, cBr.height); ctxBr.fillStyle = '#0b1120'; ctxBr.fillRect(0, 0, cBr.width, cBr.height);
      br.mols.forEach((m) => {
        m.x += m.vx * spdScale; m.y += m.vy * spdScale;
        if (m.x < 10 || m.x > 730) m.vx = -m.vx;
        if (m.y < 10 || m.y > 300) m.vy = -m.vy;
        const dx = br.px - m.x, dy = br.py - m.y, d = Math.hypot(dx, dy);
        if (d < 22 && d > 0.1) {
          br.pvx += (dx / d) * 0.65 * spdScale; br.pvy += (dy / d) * 0.65 * spdScale;
          m.vx = -m.vx; m.vy = -m.vy;
        }
        if (br.showMol) {
          ctxBr.fillStyle = 'rgba(56,189,248,0.65)'; ctxBr.beginPath(); ctxBr.arc(m.x, m.y, 3, 0, Math.PI * 2); ctxBr.fill();
        }
      });
      br.pvx *= 0.88; br.pvy *= 0.88;
      br.px = Math.max(40, Math.min(700, br.px + br.pvx)); br.py = Math.max(40, Math.min(270, br.py + br.pvy));
      br.trail.push({ x: br.px, y: br.py }); if (br.trail.length > 260) br.trail.shift();
      if (br.trail.length > 1) {
        ctxBr.strokeStyle = 'rgba(251,191,36,0.75)'; ctxBr.lineWidth = 2; ctxBr.beginPath();
        br.trail.forEach((p, i) => (i ? ctxBr.lineTo(p.x, p.y) : ctxBr.moveTo(p.x, p.y))); ctxBr.stroke();
      }
      ctxBr.fillStyle = '#fbbf24'; ctxBr.shadowColor = '#fbbf24'; ctxBr.shadowBlur = 12;
      ctxBr.beginPath(); ctxBr.arc(br.px, br.py, 15, 0, Math.PI * 2); ctxBr.fill(); ctxBr.shadowBlur = 0;
      ctxBr.textAlign = 'center';
      ctxBr.fillStyle = '#fbbf24'; ctxBr.font = FS.small; ctxBr.fillText('花粉', br.px, br.py - 24);
      ctxBr.textAlign = 'left';
    }

    if (state.tab === 'demon') {
      const midX = 370, gateTop = 115, gateBot = 195;
      let autoOpen = dm.open;
      if (dm.auto) {
        autoOpen = dm.ps.some((p) => p.y > gateTop && p.y < gateBot && ((p.hot && p.x < midX && p.x > midX - 24 && p.vx > 0) || (!p.hot && p.x > midX && p.x < midX + 24 && p.vx < 0)));
      }
      ctxDm.clearRect(0, 0, cDm.width, cDm.height); ctxDm.fillStyle = '#0b1120'; ctxDm.fillRect(0, 0, cDm.width, cDm.height);
      ctxDm.strokeStyle = '#475569'; ctxDm.lineWidth = 4; ctxDm.strokeRect(30, 20, 680, 270);
      ctxDm.beginPath(); ctxDm.moveTo(midX, 20); ctxDm.lineTo(midX, gateTop); ctxDm.moveTo(midX, gateBot); ctxDm.lineTo(midX, 290); ctxDm.stroke();
      if (!autoOpen) { ctxDm.strokeStyle = '#f97316'; ctxDm.lineWidth = 5; ctxDm.beginPath(); ctxDm.moveTo(midX, gateTop); ctxDm.lineTo(midX, gateBot); ctxDm.stroke(); }

      let lSum = 0, lN = 0, rSum = 0, rN = 0;
      dm.ps.forEach((p) => {
        const nx = p.x + p.vx, ny = p.y + p.vy;
        if (ny < 26 || ny > 284) p.vy = -p.vy;
        if (nx < 36 || nx > 704) p.vx = -p.vx;
        const cross = (p.x < midX && nx >= midX) || (p.x > midX && nx <= midX);
        if (cross && (!autoOpen || p.y < gateTop || p.y > gateBot)) p.vx = -p.vx;
        else p.x = nx;
        p.y += p.vy;
        if (p.x < midX) { lSum += p.hot ? 85 : 15; lN++; } else { rSum += p.hot ? 85 : 15; rN++; }
        ctxDm.fillStyle = p.hot ? '#f87171' : '#38bdf8';
        ctxDm.beginPath(); ctxDm.arc(p.x, p.y, 5.5, 0, Math.PI * 2); ctxDm.fill();
      });
      const tL = lN ? lSum / lN : 25, tR = rN ? rSum / rN : 25;
      if (tR - tL >= 20) { state.tasks.dmSep = true; checkDm(); }
      ctxDm.fillStyle = '#7dd3fc'; ctxDm.font = FS.hudSub; ctxDm.fillText(`左室温度：${tL.toFixed(0)} °C`, 48, 52);
      ctxDm.textAlign = 'right';
      ctxDm.fillStyle = '#fca5a5'; ctxDm.fillText(`右室温度：${tR.toFixed(0)} °C（温差 ${(tR - tL).toFixed(0)}°C）`, 700, 52);
      ctxDm.textAlign = 'left';
    }

    if (state.tab === 'piston') {
      if (pi.slam) {
        pi.pos = Math.min(88, pi.pos + 5.5);
        pi.temp = Math.min(580, pi.temp + 38);
        $('[data-in="pisPos"]').value = String(Math.round(pi.pos));
        if (pi.temp >= 500) { pi.ignited = true; state.tasks.pisIgnite = true; checkPi(); }
        if (pi.pos >= 88) pi.slam = false;
      } else {
        pi.temp = Math.max(25, pi.temp - 1.2);
      }
      $('[data-out="pisPos"]').textContent = `${Math.round(pi.temp)} °C`;
      const cylLeft = 170, cylRight = 530, cylBot = 278, pisY = 42 + pi.pos * 2.05;
      ctxPi.clearRect(0, 0, cPi.width, cPi.height); ctxPi.fillStyle = '#0b1120'; ctxPi.fillRect(0, 0, cPi.width, cPi.height);
      ctxPi.strokeStyle = '#64748b'; ctxPi.lineWidth = 4; ctxPi.strokeRect(cylLeft, 36, cylRight - cylLeft, cylBot - 36);
      // Piston head
      ctxPi.fillStyle = '#94a3b8'; ctxPi.fillRect(cylLeft + 2, pisY - 18, cylRight - cylLeft - 4, 18);
      ctxPi.fillStyle = '#cbd5e1'; ctxPi.fillRect(340, 0, 20, pisY - 18);
      // Cotton at bottom
      ctxPi.fillStyle = pi.ignited ? '#f97316' : '#f8fafc';
      ctxPi.beginPath(); ctxPi.ellipse(350, cylBot - 10, 26, 9, 0, 0, Math.PI * 2); ctxPi.fill();
      if (pi.ignited) {
        const fg = ctxPi.createRadialGradient(350, cylBot - 18, 4, 350, cylBot - 18, 52);
        fg.addColorStop(0, 'rgba(253,224,71,0.95)'); fg.addColorStop(0.5, 'rgba(249,115,22,0.75)'); fg.addColorStop(1, 'rgba(239,68,68,0)');
        ctxPi.fillStyle = fg; ctxPi.beginPath(); ctxPi.arc(350, cylBot - 18, 52, 0, Math.PI * 2); ctxPi.fill();
      }
      const sp = 0.7 + (pi.temp / 500) * 3.0;
      pi.mols.forEach((m) => {
        m.x += m.vx * sp; m.y += m.vy * sp;
        if (m.x < cylLeft + 8 || m.x > cylRight - 8) m.vx = -m.vx;
        if (m.y < pisY + 6) { m.y = pisY + 6; m.vy = Math.abs(m.vy); }
        if (m.y > cylBot - 8) { m.y = cylBot - 8; m.vy = -Math.abs(m.vy); }
        ctxPi.fillStyle = pi.temp > 300 ? '#f97316' : '#38bdf8';
        ctxPi.beginPath(); ctxPi.arc(m.x, m.y, 3.5, 0, Math.PI * 2); ctxPi.fill();
      });
      ctxPi.textAlign = 'right';
      ctxPi.fillStyle = pi.ignited ? '#fde047' : '#7dd3fc'; ctxPi.font = FS.label;
      ctxPi.fillText(`缸内温度：${Math.round(pi.temp)} °C`, 728, 78);
      ctxPi.fillStyle = pi.ignited ? '#f97316' : '#94a3b8'; ctxPi.font = FS.small;
      ctxPi.fillText(pi.ignited ? '🔥 达到燃点！棉花自燃！' : '燃点阈值：500 °C', 728, 110);
      ctxPi.textAlign = 'left';
    }
    rafId = requestAnimationFrame(loop);
  }

  function renderSummary() {
    const dN = KEYS.filter((k) => state.done[k]).length;
    $('[data-sum="title"]').textContent = dN === 3 ? '🏆 热学与微观宇宙通关！' : `探索进行中：已完成 ${dN} / 3 场实验`;
    const rows = [
      { k: 'brown', t: '1. 布朗运动显形', p: '“花粉不是自己游，而是替看不见的分子热运动当了传话筒。”' },
      { k: 'demon', t: '2. 麦克斯韦妖与熵增', p: '“热量自发混合轻而易举，逆转熵增必付能量或信息代价。”' },
      { k: 'piston', t: '3. 绝热压缩点火', p: '“极速压缩做功 100% 转化为空气内能，无需火花塞也能高温自燃。”' },
    ];
    $('[data-sum="list"]').innerHTML = rows.map((r) => `<div class="th-recap"><div style="font-size:13.5px;font-weight:800">${state.done[r.k] ? '✅ ' : '🔒 '}${r.t}</div><div style="font-size:12.5px;color:var(--ink-2);margin-top:3px">${state.done[r.k] ? r.p : '完成对应实验探索后解锁'}</div></div>`).join('');
  }
  $('[data-act="resetAll"]').addEventListener('click', () => {
    KEYS.forEach((k) => { state.guesses[k] = null; state.done[k] = false; });
    state.tasks = { brReveal: false, brHot: false, dmGate: false, dmSep: false, pisSlow: false, pisIgnite: false };
    $$('.th-opt').forEach((b) => b.classList.remove('picked'));
    resetDemon(); checkBr(); checkDm(); checkPi(); updateProgress(); renderSummary(); switchTab('brown');
  });
  $('[data-act="backSubjects"]').addEventListener('click', () => navigate('#/subjects'));

  view.innerHTML = ''; view.appendChild(root);
  resetDemon(); checkBr(); checkDm(); checkPi(); updateProgress();
  rafId = requestAnimationFrame(loop);
  mountLabBonus(root, '.th-tabs');
  return () => { disposed = true; cancelAnimationFrame(rafId); };
}
