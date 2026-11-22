/* 电磁宇宙加速器：回旋加速器 + 电磁轨道炮 + 地球磁场极光捕获（暗黑霓虹互动实验室） */

import { el } from '../ui.js';
import { navigate } from '../router.js';
import { mountLabBonus } from '../lab-bonus.js';
import { canvasHud, FS } from '../lab-canvas.js';

const LAB_CSS = `
.emlab{display:flex;flex-direction:column;gap:12px}
.emlab .em-pill{display:inline-flex;align-items:center;gap:6px;padding:5px 11px;border-radius:999px;background:#fff;border:1px solid var(--line);font-size:12px;font-weight:700;color:var(--ink-2)}
.emlab .em-dot{width:8px;height:8px;border-radius:50%;background:#d6c7b2;transition:background .2s}
.emlab .em-dot.done{background:#059669}
.emlab .em-tabs{display:flex;flex-wrap:wrap;gap:7px}
.emlab .em-tab{appearance:none;border:1px solid var(--line);background:#fff;color:var(--ink-2);padding:7px 12px;border-radius:999px;font-size:12px;font-weight:700;cursor:pointer;display:inline-flex;align-items:center;gap:5px}
.emlab .em-tab.active{background:#0f172a;border-color:#38bdf8;color:#7dd3fc}
.emlab .em-tab .chk{font-size:10.5px;padding:1px 5px;border-radius:999px;background:#ecfdf5;color:#059669}
.emlab .em-tab.active .chk{background:rgba(56,189,248,.22);color:#7dd3fc}
.emlab .em-predict{background:#faf6ef;border:1px dashed #dfcfb7;border-radius:12px;padding:11px 12px;margin:10px 0 12px}
.emlab .em-predict-q{font-size:13px;font-weight:800;margin:0 0 8px;color:var(--ink)}
.emlab .em-opts{display:flex;flex-wrap:wrap;gap:7px}
.emlab .em-opt{appearance:none;background:#fff;border:1px solid #dfd2be;color:var(--ink-2);padding:6px 11px;border-radius:9px;font-size:12px;font-weight:700;cursor:pointer}
.emlab .em-opt.picked{background:#eff6ff;border-color:#2563eb;color:#2563eb}
.emlab .em-stage{border-radius:14px;overflow:hidden;border:1px solid #1e293b;background:#0b1120;margin-bottom:12px;box-shadow:0 8px 24px rgba(15,23,42,.18)}
.emlab .em-stage canvas{display:block;width:100%;height:auto;touch-action:none}
.emlab .em-ctrl{display:flex;flex-wrap:wrap;align-items:center;gap:10px 18px;padding:10px 12px;background:#faf7f2;border-radius:12px;border:1px solid var(--line);margin-bottom:10px}
.emlab .em-range{display:flex;align-items:center;gap:8px;flex:1 1 240px;min-width:220px}
.emlab .em-range label{font-size:12px;font-weight:700;color:var(--ink-2);white-space:nowrap}
.emlab .em-range input{flex:1;min-width:80px;cursor:pointer}
.emlab .em-val{font-size:12px;font-weight:800;color:#2563eb;min-width:64px;text-align:right;white-space:nowrap;font-variant-numeric:tabular-nums}
.emlab .em-tasks{display:flex;flex-wrap:wrap;gap:7px;margin-bottom:4px}
.emlab .em-task{font-size:11.5px;font-weight:700;padding:4px 10px;border-radius:9px;background:#f5f0e7;color:var(--ink-3)}
.emlab .em-task.done{background:#ecfdf5;color:#059669;border:1px solid #a7f3d0}
.emlab .em-insight{margin-top:12px;padding:14px;border-radius:13px;background:linear-gradient(135deg,#f0fdf4 0%,#eff6ff 100%);border:1px solid #bbf7d0}
.emlab .em-insight-q{font-size:15px;font-weight:900;color:var(--ink);margin:4px 0 6px;line-height:1.5}
.emlab .em-insight-b{font-size:12.5px;color:var(--ink-2);margin:0 0 10px;line-height:1.65}
.emlab .em-recap{border:1px solid var(--line);border-radius:12px;padding:11px 13px;background:#fffdf9;margin-bottom:8px}
.emlab .hidden{display:none !important}
`;

export async function renderEmCosmosLab(view) {
  const KEYS = ['cyclotron', 'railgun', 'aurora'];
  const state = {
    tab: 'cyclotron',
    guesses: { cyclotron: null, railgun: null, aurora: null },
    correct: { cyclotron: 'efield', railgun: 'both', aurora: 'poles' },
    done: { cyclotron: false, railgun: false, aurora: false },
    tasks: {
      cycShot: false, cycBSet: new Set(),
      railShot: false, railMach5: false,
      aurNormal: false, aurZero: false,
    },
  };
  let disposed = false;
  const rafs = { cyc: 0, rail: 0, aur: 0 };

  const root = el('div', { class: 'emlab' });
  const styleTag = document.createElement('style');
  styleTag.textContent = LAB_CSS;
  root.appendChild(styleTag);

  const dots = KEYS.map(() => el('span', { class: 'em-dot' }));
  const progTxt = el('span', { text: '已探索 0 / 3' });
  root.appendChild(el('div', { class: 'topbar' }, [
    el('button', { class: 'back', text: '‹', onclick: () => { if (history.length > 1) history.back(); else navigate('#/subjects'); } }),
    el('div', { style: 'flex:1;min-width:0' }, [
      el('h1', { text: '电磁宇宙加速器' }),
      el('div', { class: 'sub', text: '洛伦兹力 · 安培力轨道炮 · 地磁极光特效实验室' }),
    ]),
    el('div', { class: 'em-pill' }, [...dots, progTxt]),
  ]));

  const body = el('div', { html: `
  <nav class="em-tabs">
    <button type="button" class="em-tab active" data-tab="cyclotron">🌀 1. 回旋加速器 <span class="chk hidden" data-chk="cyclotron">✓</span></button>
    <button type="button" class="em-tab" data-tab="railgun">⚡ 2. 电磁轨道炮 <span class="chk hidden" data-chk="railgun">✓</span></button>
    <button type="button" class="em-tab" data-tab="aurora">🌌 3. 地球极光捕获 <span class="chk hidden" data-chk="aurora">✓</span></button>
    <button type="button" class="em-tab" data-tab="summary">🏆 专题总结</button>
  </nav>

  <!-- 1: CYCLOTRON -->
  <section class="panel" data-pane="cyclotron">
    <div style="font-size:17px;font-weight:800;margin-bottom:4px">回旋加速器：谁在给粒子踩油门？谁在握方向盘？</div>
    <div style="font-size:12.5px;color:var(--ink-2)">调匀强磁场 B 和加速电压 U，发射带电粒子，看它如何在两个 D 形盒之间画出霓虹螺旋光环！</div>
    <div class="em-predict">
      <div class="em-predict-q">① 先猜一猜：在回旋加速器里，带电粒子越来越快，主要是谁对它做了功？</div>
      <div class="em-opts" data-lab="cyclotron">
        <button type="button" class="em-opt" data-val="bfield">强大的磁场把粒子越推越快</button>
        <button type="button" class="em-opt" data-val="efield">磁场不做功只拐弯，真正加速的是中间缝隙的电场</button>
      </div>
    </div>
    <div class="em-stage"><canvas data-cv="cyclotron" width="740" height="330"></canvas></div>
    <div class="em-ctrl">
      <div class="em-range"><label>磁场 B</label><input data-in="cycB" type="range" min="0.8" max="2.4" value="1.4" step="0.2"><span class="em-val" data-out="cycB">1.4 T</span></div>
      <div class="em-range"><label>缝隙电压 U</label><input data-in="cycU" type="range" min="10" max="45" value="25" step="5"><span class="em-val" data-out="cycU">25 kV</span></div>
      <button type="button" class="btn sm" data-act="cycFire">发射粒子</button>
      <button type="button" class="btn sm ghost" data-act="cycReset">重置</button>
    </div>
    <div class="em-tasks">
      <span class="em-task" data-task="cyc1">○ 目标 1：发射粒子看螺旋加速并冲出出口</span>
      <span class="em-task" data-task="cyc2">○ 目标 2：换一个磁场强度 B 再发射，观察出射最大动能变化</span>
    </div>
    <div class="em-insight hidden" data-insight="cyclotron">
      <div style="font-size:11px;font-weight:800;color:#059669">✦ 顿悟时刻已解锁</div>
      <div class="em-insight-q">“磁场永远不做功，只负责当‘方向盘’；真正踩油门的，是两半圆之间那一瞬间的电场。”</div>
      <p class="em-insight-b">洛伦兹力始终垂直速度，只让粒子转弯；每次穿过缝隙被电场加速，半径 <code>r = mv/(qB)</code> 变大。最终最大动能 <code>Emax = q²B²R²/(2m)</code> 只取决于磁场 B 和 D 盒半径 R，与单次电压 U 无关！</p>
      <div class="row-between" style="gap:8px;flex-wrap:wrap"><span style="font-size:11.5px;font-weight:700;color:#2563eb" data-guess="cyclotron"></span><button type="button" class="btn sm" data-goto="railgun">下一场：电磁轨道炮 →</button></div>
    </div>
  </section>

  <!-- 2: RAILGUN -->
  <section class="panel hidden" data-pane="railgun">
    <div style="font-size:17px;font-weight:800;margin-bottom:4px">电磁轨道炮：不装一克火药，如何把铁块轰到 7 倍音速？</div>
    <div style="font-size:12.5px;color:var(--ink-2)">调高脉冲电流 I 与磁场 B，点击「⚡ 充能发射」，看安培力 F = BIL 如何拉出蓝白电弧！</div>
    <div class="em-predict">
      <div class="em-predict-q">① 先猜一猜：要让轨道炮出膛速度翻倍，把脉冲电流 I 调成原来的 2 倍够吗？</div>
      <div class="em-opts" data-lab="railgun">
        <button type="button" class="em-opt" data-val="double">够，电流翻倍速度就翻倍</button>
        <button type="button" class="em-opt" data-val="both">不够，推力翻倍只让动能翻倍，速度只变 √2 倍（需加大 I 和 B）</button>
      </div>
    </div>
    <div class="em-stage"><canvas data-cv="railgun" width="740" height="310"></canvas></div>
    <div class="em-ctrl">
      <div class="em-range"><label>脉冲电流 I</label><input data-in="railI" type="range" min="10" max="60" value="30" step="5"><span class="em-val" data-out="railI">30 kA</span></div>
      <div class="em-range"><label>垂直磁场 B</label><input data-in="railB" type="range" min="1.0" max="5.0" value="2.5" step="0.5"><span class="em-val" data-out="railB">2.5 T</span></div>
      <button type="button" class="btn sm" style="background:#2563eb" data-act="railFire">⚡ 充能发射！</button>
      <button type="button" class="btn sm ghost" data-act="railReset">重置</button>
    </div>
    <div class="em-tasks">
      <span class="em-task" data-task="rail1">○ 目标 1：充能发射一次观察电弧加速</span>
      <span class="em-task" data-task="rail2">○ 目标 2：调高电流与磁场，把出膛速度轰破 5 倍音速（Mach 5）</span>
    </div>
    <div class="em-insight hidden" data-insight="railgun">
      <div style="font-size:11px;font-weight:800;color:#059669">✦ 顿悟时刻已解锁</div>
      <div class="em-insight-q">“不用一克火药，只靠电流和磁场垂直一推，就能把铁块推出 7 倍音速。”</div>
      <p class="em-insight-b">通电弹丸在垂直磁场中受安培力 <code>F = BIL</code>（左手定则），沿轨道做功 <code>W = BIL·s = ½mv²</code>，因此 <code>v ∝ √(B·I)</code>。现代航母电磁弹射器正是同款原理。</p>
      <div class="row-between" style="gap:8px;flex-wrap:wrap"><span style="font-size:11.5px;font-weight:700;color:#2563eb" data-guess="railgun"></span><button type="button" class="btn sm" data-goto="aurora">下一场：地球极光捕获 →</button></div>
    </div>
  </section>

  <!-- 3: AURORA -->
  <section class="panel hidden" data-pane="aurora">
    <div style="font-size:17px;font-weight:800;margin-bottom:4px">极光生成器：为什么极光总出现在南北极，而不是赤道？</div>
    <div style="font-size:12.5px;color:var(--ink-2)">太阳风带电粒子流正高速扑向地球！拖动「地磁场强度」从 100% 降到 0%，亲眼看看地磁场如何保护地球并点亮极光。</div>
    <div class="em-predict">
      <div class="em-predict-q">① 先猜一猜：如果地球突然失去磁场，太阳风会怎样？</div>
      <div class="em-opts" data-lab="aurora">
        <button type="button" class="em-opt" data-val="same">极光会变得更亮、全球都能看</button>
        <button type="button" class="em-opt" data-val="poles">失去地磁偏转保护，高能粒子会直击赤道大气并剥离大气层</button>
      </div>
    </div>
    <div class="em-stage"><canvas data-cv="aurora" width="740" height="330"></canvas></div>
    <div class="em-ctrl">
      <div class="em-range"><label>地磁场强度</label><input data-in="aurB" type="range" min="0" max="180" value="100" step="10"><span class="em-val" data-out="aurB">100%</span></div>
      <button type="button" class="btn sm" style="background:#059669" data-act="aurStorm">☀ 触发太阳风暴</button>
    </div>
    <div class="em-tasks">
      <span class="em-task" data-task="aur1">○ 目标 1：在有磁场（≥ 60%）时触发太阳风暴，看两极点亮极光</span>
      <span class="em-task" data-task="aur2">○ 目标 2：把地磁场调到 0%，对比失去磁场保护的后果</span>
    </div>
    <div class="em-insight hidden" data-insight="aurora">
      <div style="font-size:11px;font-weight:800;color:#059669">✦ 顿悟时刻已解锁</div>
      <div class="em-insight-q">“极光不是浪漫的巧合，而是地球磁场替人类挡下致命太阳辐射时的‘战损火花’。”</div>
      <p class="em-insight-b">带电太阳风粒子受洛伦兹力偏转，无法穿透赤道磁感线，只能沿着磁感线螺旋汇入南北磁极，撞击高空氧/氮原子发出绿紫色极光。火星正是因失去全球磁场，大气才被太阳风吹薄。</p>
      <div class="row-between" style="gap:8px;flex-wrap:wrap"><span style="font-size:11.5px;font-weight:700;color:#2563eb" data-guess="aurora"></span><button type="button" class="btn sm" data-goto="summary">查看专题总结 🏆</button></div>
    </div>
  </section>

  <!-- SUMMARY -->
  <section class="panel hidden" data-pane="summary">
    <div style="text-align:center;margin-bottom:12px">
      <div style="font-size:18px;font-weight:900" data-sum="title">探索进行中：已完成 0 / 3 场电磁宇宙实验</div>
      <div style="font-size:12.5px;color:var(--ink-2);margin-top:4px">从实验室里的回旋加速器，到电磁弹射与守护地球的极光——背后都是同一套洛伦兹力与安培力规律。</div>
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
    progTxt.textContent = `已探索 ${n} / 3`;
  }
  function switchTab(name) {
    state.tab = name;
    $$('.em-tab').forEach((b) => b.classList.toggle('active', b.dataset.tab === name));
    $$('[data-pane]').forEach((p) => p.classList.toggle('hidden', p.dataset.pane !== name));
    if (name === 'summary') renderSummary();
    if (name === 'cyclotron') drawCyc();
    if (name === 'railgun') drawRail();
  }

  $$('.em-tab').forEach((b) => b.addEventListener('click', () => switchTab(b.dataset.tab)));
  $$('[data-goto]').forEach((b) => b.addEventListener('click', () => switchTab(b.dataset.goto)));
  $$('.em-opts').forEach((w) => {
    const lab = w.dataset.lab;
    w.querySelectorAll('.em-opt').forEach((btn) => btn.addEventListener('click', () => {
      state.guesses[lab] = btn.dataset.val;
      w.querySelectorAll('.em-opt').forEach((x) => x.classList.toggle('picked', x === btn));
      updateGuess(lab);
    }));
  });

  /* ==================== 1: CYCLOTRON ==================== */
  const cCyc = $('[data-cv="cyclotron"]'), ctxCy = cCyc.getContext('2d');
  const cyc = { B: 1.4, U: 25, cx: 255, cy: 165, R: 125, running: false, escaped: false, x: 255, y: 165, vx: 0, vy: 0, trail: [], gapFlash: 0, kicks: 0, lastSide: 0, polarity: 1, lastTs: 0 };
  function checkCyc() {
    const t2 = state.tasks.cycBSet.size >= 2;
    setTask('cyc1', state.tasks.cycShot, '目标 1：发射粒子看螺旋加速并冲出出口');
    setTask('cyc2', t2, `目标 2：换不同磁场 B 再发射（已试 ${Math.min(2, state.tasks.cycBSet.size)}/2）`);
    if (state.tasks.cycShot && t2 && !state.done.cyclotron) { state.done.cyclotron = true; updateProgress(); }
  }
  function drawCyc() {
    const W = cCyc.width, H = cCyc.height;
    ctxCy.clearRect(0, 0, W, H); ctxCy.fillStyle = '#0b1120'; ctxCy.fillRect(0, 0, W, H);
    // D-shaped chambers（随交变电压正反切换染色，直观区分左右电势高低）
    const leftPos = cyc.polarity > 0;
    ctxCy.fillStyle = leftPos ? 'rgba(245, 158, 11, 0.20)' : 'rgba(30, 58, 138, 0.38)';
    ctxCy.strokeStyle = leftPos ? '#fbbf24' : '#38bdf8'; ctxCy.lineWidth = 2;
    ctxCy.beginPath(); ctxCy.arc(cyc.cx - 8, cyc.cy, cyc.R, Math.PI * 0.5, Math.PI * 1.5); ctxCy.closePath(); ctxCy.fill(); ctxCy.stroke();
    ctxCy.fillStyle = leftPos ? 'rgba(30, 58, 138, 0.38)' : 'rgba(245, 158, 11, 0.20)';
    ctxCy.strokeStyle = leftPos ? '#38bdf8' : '#fbbf24';
    ctxCy.beginPath(); ctxCy.arc(cyc.cx + 8, cyc.cy, cyc.R, -Math.PI * 0.5, Math.PI * 0.5); ctxCy.closePath(); ctxCy.fill(); ctxCy.stroke();
    // 交变电压极性标记与缝隙电场方向箭头（每次过缝自动翻转）
    ctxCy.font = '900 18px monospace';
    ctxCy.fillStyle = leftPos ? '#fbbf24' : '#38bdf8'; ctxCy.fillText(leftPos ? '+' : '−', cyc.cx - 32, cyc.cy - cyc.R + 24);
    ctxCy.fillStyle = leftPos ? '#38bdf8' : '#fbbf24'; ctxCy.fillText(leftPos ? '−' : '+', cyc.cx + 20, cyc.cy - cyc.R + 24);
    ctxCy.fillStyle = '#fde047'; ctxCy.font = '800 13px sans-serif';
    ctxCy.fillText(leftPos ? 'E →' : '← E', cyc.cx - 12, cyc.cy - cyc.R - 8);
    // Electric gap flash
    if (cyc.gapFlash > 0.05) {
      ctxCy.fillStyle = `rgba(251, 191, 36, ${cyc.gapFlash * 0.65})`;
      ctxCy.fillRect(cyc.cx - 7, cyc.cy - cyc.R, 14, cyc.R * 2);
    }
    // B-field crosses
    ctxCy.fillStyle = 'rgba(125, 211, 252, 0.32)'; ctxCy.font = '700 13px monospace';
    for (let dx = -90; dx <= 90; dx += 45) {
      for (let dy = -80; dy <= 80; dy += 45) {
        if (Math.hypot(dx, dy) < cyc.R - 18 && Math.abs(dx) > 12) ctxCy.fillText('×', cyc.cx + dx - 4, cyc.cy + dy + 4);
      }
    }
    // Neon particle trail
    if (cyc.trail.length > 1) {
      ctxCy.strokeStyle = '#38bdf8'; ctxCy.lineWidth = 2.4; ctxCy.shadowColor = '#38bdf8'; ctxCy.shadowBlur = 10;
      ctxCy.beginPath(); cyc.trail.forEach((p, i) => (i ? ctxCy.lineTo(p.x, p.y) : ctxCy.moveTo(p.x, p.y))); ctxCy.stroke();
      ctxCy.shadowBlur = 0;
    }
    // Particle dot
    ctxCy.fillStyle = '#fde047'; ctxCy.shadowColor = '#fde047'; ctxCy.shadowBlur = 12;
    ctxCy.beginPath(); ctxCy.arc(cyc.x, cyc.y, 5.5, 0, Math.PI * 2); ctxCy.fill(); ctxCy.shadowBlur = 0;

    // Telemetry HUD on right
    const speed = Math.hypot(cyc.vx, cyc.vy);
    const eMaxMeV = (cyc.B * cyc.B * 12.5).toFixed(1);
    canvasHud(ctxCy, { x: 728, y: 12, lh: 34, align: 'right', stroke: '#243044', lines: [
      { text: '回旋加速器遥测', font: '800 20px sans-serif', color: '#7dd3fc' },
      { text: `B ${cyc.B.toFixed(1)} T · 交流 ±${cyc.U} kV`, font: FS.hudSub, color: '#cbd5e1' },
      { text: `电场 ${leftPos ? '左+右− (E→)' : '左−右+ (←E)'}`, font: FS.hudSub, color: '#fbbf24' },
      { text: `加速 ${cyc.kicks} 次`, font: FS.hudSub, color: '#cbd5e1' },
      { text: `速率 ${(speed * 0.08).toFixed(1)} ×10⁶ m/s`, font: FS.hudSub, color: '#fde047' },
      { text: `最大动能 ${eMaxMeV} MeV`, font: FS.hudSub, color: '#34d399' },
      { text: cyc.escaped ? '✨ 已射出 D 形盒' : 'B 越大，螺旋越密', font: FS.small, color: '#94a3b8' },
    ] });
  }
  function stepCyc(ts) {
    if (disposed) return;
    if (!cyc.lastTs) cyc.lastTs = ts;
    const dt = Math.min(0.03, (ts - cyc.lastTs) / 1000); cyc.lastTs = ts;
    cyc.gapFlash = Math.max(0, cyc.gapFlash - dt * 4);
    for (let s = 0; s < 8; s++) {
      const hdt = dt / 8;
      const dx = cyc.x - cyc.cx, dy = cyc.y - cyc.cy, dist = Math.hypot(dx, dy);
      if (!cyc.escaped && dist >= cyc.R - 4) {
        cyc.escaped = true;
        state.tasks.cycShot = true; state.tasks.cycBSet.add(cyc.B); checkCyc();
      }
      if (!cyc.escaped) {
        const side = dx >= 0 ? 1 : -1;
        if (Math.abs(dx) < 7 && cyc.lastSide !== 0 && side !== cyc.lastSide) {
          // 交流电源每半周期同步翻转极性，保证每次过缝电场方向与速度同向加速
          cyc.polarity = cyc.vx >= 0 ? 1 : -1;
          const v = Math.hypot(cyc.vx, cyc.vy);
          const vNew = Math.sqrt(v * v + cyc.U * 260);
          cyc.vx = (cyc.vx / Math.max(1, v)) * vNew;
          cyc.vy = (cyc.vy / Math.max(1, v)) * vNew;
          cyc.lastSide = side;
          cyc.gapFlash = 1; cyc.kicks++;
        }
        if (Math.abs(dx) >= 7) {
          cyc.lastSide = side;
          // 精确保能旋转（洛伦兹力严格不做功，消除欧拉积分能量漂移）
          const dTheta = cyc.B * 4.2 * hdt;
          const ca = Math.cos(dTheta), sa = Math.sin(dTheta);
          const nvx = cyc.vx * ca - cyc.vy * sa;
          const nvy = cyc.vx * sa + cyc.vy * ca;
          cyc.vx = nvx; cyc.vy = nvy;
        }
      }
      cyc.x += cyc.vx * hdt; cyc.y += cyc.vy * hdt;
    }
    cyc.trail.push({ x: cyc.x, y: cyc.y });
    if (cyc.trail.length > 420) cyc.trail.shift();
    drawCyc();
    if (cyc.x > -20 && cyc.x < 760 && cyc.y > -20 && cyc.y < 350 && cyc.running) rafs.cyc = requestAnimationFrame(stepCyc);
    else cyc.running = false;
  }
  $('[data-in="cycB"]').addEventListener('input', (e) => { cyc.B = Number(e.target.value); $('[data-out="cycB"]').textContent = `${cyc.B.toFixed(1)} T`; drawCyc(); });
  $('[data-in="cycU"]').addEventListener('input', (e) => { cyc.U = Number(e.target.value); $('[data-out="cycU"]').textContent = `${cyc.U} kV`; drawCyc(); });
  // 发射即记账：不等粒子真的飞出 D 形盒，换磁场重放也能累计到两个不同 B。
  $('[data-act="cycFire"]').addEventListener('click', () => {
    state.tasks.cycShot = true;
    state.tasks.cycBSet.add(cyc.B);
    checkCyc();
    cancelAnimationFrame(rafs.cyc);
    cyc.x = cyc.cx - 8; cyc.y = cyc.cy; cyc.vx = 52; cyc.vy = 0; cyc.trail = [{ x: cyc.cx - 8, y: cyc.cy }];
    cyc.kicks = 0; cyc.escaped = false; cyc.lastSide = -1; cyc.polarity = 1; cyc.running = true; cyc.lastTs = 0;
    rafs.cyc = requestAnimationFrame(stepCyc);
  });
  $('[data-act="cycReset"]').addEventListener('click', () => { cancelAnimationFrame(rafs.cyc); cyc.running = false; cyc.x = cyc.cx; cyc.y = cyc.cy; cyc.vx = 0; cyc.vy = 0; cyc.trail = []; cyc.kicks = 0; cyc.escaped = false; cyc.polarity = 1; drawCyc(); });

  /* ==================== 2: RAILGUN ==================== */
  const cRail = $('[data-cv="railgun"]'), ctxRa = cRail.getContext('2d');
  const rail = { I: 30, B: 2.5, x: 95, vx: 0, firing: false, mach: 0, sparks: [], lastTs: 0 };
  function checkRail() {
    setTask('rail1', state.tasks.railShot, '目标 1：充能发射一次观察电弧加速');
    setTask('rail2', state.tasks.railMach5, '目标 2：把出膛速度轰破 5 倍音速（Mach 5）');
    if (state.tasks.railShot && state.tasks.railMach5 && !state.done.railgun) { state.done.railgun = true; updateProgress(); }
  }
  function drawRail() {
    const W = cRail.width, H = cRail.height;
    ctxRa.clearRect(0, 0, W, H); ctxRa.fillStyle = '#0b1120'; ctxRa.fillRect(0, 0, W, H);
    // Magnetic field symbols between rails
    ctxRa.fillStyle = 'rgba(56,189,248,0.28)'; ctxRa.font = '700 13px monospace';
    for (let gx = 90; gx <= 560; gx += 42) ctxRa.fillText('⊗', gx, 162);
    // Top & bottom glowing rails
    ctxRa.fillStyle = '#334155'; ctxRa.fillRect(60, 118, 520, 14); ctxRa.fillRect(60, 184, 520, 14);
    ctxRa.strokeStyle = rail.firing ? '#38bdf8' : '#64748b'; ctxRa.lineWidth = 2;
    ctxRa.strokeRect(60, 118, 520, 14); ctxRa.strokeRect(60, 184, 520, 14);
    // Current arrows
    ctxRa.fillStyle = '#fbbf24'; ctxRa.font = FS.small;
    ctxRa.fillText(`电流 I = ${rail.I} kA →`, 72, 108);
    ctxRa.fillText('← 回路电流', 72, 222);
    // Plasma sparks
    rail.sparks.forEach((sp) => {
      ctxRa.fillStyle = `rgba(125,211,252,${sp.a})`;
      ctxRa.beginPath(); ctxRa.arc(sp.x, sp.y, sp.r, 0, Math.PI * 2); ctxRa.fill();
    });
    // Armature projectile
    ctxRa.fillStyle = '#38bdf8'; ctxRa.shadowColor = '#38bdf8'; ctxRa.shadowBlur = rail.firing ? 16 : 4;
    ctxRa.beginPath(); ctxRa.roundRect(rail.x - 12, 132, 26, 52, 5); ctxRa.fill(); ctxRa.shadowBlur = 0;
    // HUD
    const forceKN = (rail.B * rail.I * 0.25).toFixed(1);
    const targetMach = (Math.sqrt(rail.B * rail.I * 0.25) * 1.18).toFixed(1);
    canvasHud(ctxRa, { x: 728, y: 6, lh: 32, align: 'right', stroke: null, lines: [
      { text: `推力 F = BIL ≈ ${forceKN} kN`, font: FS.hud, color: '#7dd3fc' },
      { text: `预计出膛 Mach ${targetMach}${Number(targetMach) >= 5 ? ' 🚀' : ''}`, font: FS.hudSub, color: '#fbbf24' },
      { text: rail.mach > 0 ? `上次实测 Mach ${rail.mach.toFixed(1)}` : '点「⚡ 充能发射」测试', font: FS.small, color: '#94a3b8' },
    ] });
  }
  function stepRail(ts) {
    if (disposed) return;
    if (!rail.lastTs) rail.lastTs = ts;
    const dt = Math.min(0.03, (ts - rail.lastTs) / 1000); rail.lastTs = ts;
    const acc = rail.B * rail.I * 18;
    if (rail.x < 580) {
      rail.vx += acc * dt;
      for (let k = 0; k < 3; k++) rail.sparks.push({ x: rail.x - 10, y: 132 + Math.random() * 52, vx: -60 - Math.random() * 90, vy: (Math.random() - 0.5) * 80, r: 2 + Math.random() * 2.5, a: 1 });
    }
    rail.x += rail.vx * dt;
    rail.sparks.forEach((sp) => { sp.x += sp.vx * dt; sp.y += sp.vy * dt; sp.a -= dt * 2.6; });
    rail.sparks = rail.sparks.filter((sp) => sp.a > 0);
    drawRail();
    if (rail.x < 770) rafs.rail = requestAnimationFrame(stepRail);
    else {
      rail.firing = false;
      rail.mach = Math.sqrt(rail.B * rail.I * 0.25) * 1.18;
      state.tasks.railShot = true;
      if (rail.mach >= 5) state.tasks.railMach5 = true;
      checkRail(); drawRail();
    }
  }
  $('[data-in="railI"]').addEventListener('input', (e) => { rail.I = Number(e.target.value); $('[data-out="railI"]').textContent = `${rail.I} kA`; drawRail(); });
  $('[data-in="railB"]').addEventListener('input', (e) => { rail.B = Number(e.target.value); $('[data-out="railB"]').textContent = `${rail.B.toFixed(1)} T`; drawRail(); });
  $('[data-act="railFire"]').addEventListener('click', () => { cancelAnimationFrame(rafs.rail); rail.x = 95; rail.vx = 0; rail.sparks = []; rail.firing = true; rail.lastTs = 0; rafs.rail = requestAnimationFrame(stepRail); });
  $('[data-act="railReset"]').addEventListener('click', () => { cancelAnimationFrame(rafs.rail); rail.firing = false; rail.x = 95; rail.vx = 0; rail.sparks = []; drawRail(); });

  /* ==================== 3: AURORA ==================== */
  const cAur = $('[data-cv="aurora"]'), ctxAu = cAur.getContext('2d');
  const aur = { B: 100, particles: [], glow: 0, eqHit: 0 };
  function spawnSolar(count = 12) {
    for (let i = 0; i < count; i++) {
      aur.particles.push({
        x: -10 - Math.random() * 60,
        y: 65 + Math.random() * 200,
        vx: 135 + Math.random() * 55,
        vy: (Math.random() - 0.5) * 18,
        pole: Math.random() < 0.5 ? -1 : 1,
        hue: Math.random() < 0.65 ? '#34d399' : '#a78bfa',
      });
    }
  }
  function checkAur() {
    setTask('aur1', state.tasks.aurNormal, '目标 1：有磁场（≥ 60%）触发风暴，看两极点亮极光');
    setTask('aur2', state.tasks.aurZero, '目标 2：把地磁场调到 0%，对比失去保护的后果');
    if (state.tasks.aurNormal && state.tasks.aurZero && !state.done.aurora) { state.done.aurora = true; updateProgress(); }
  }
  function stepAurora() {
    if (disposed) return;
    if (state.tab === 'aurora') {
      if (aur.particles.length < 38) spawnSolar(2);
      const ex = 515, ey = 165, er = 68;
      aur.glow = Math.max(0, aur.glow - 0.015);
      aur.eqHit = Math.max(0, aur.eqHit - 0.02);

      ctxAu.clearRect(0, 0, cAur.width, cAur.height);
      ctxAu.fillStyle = '#0b1120'; ctxAu.fillRect(0, 0, cAur.width, cAur.height);

      // Dipolar magnetic field arcs when B > 0
      if (aur.B > 0) {
        const alpha = Math.min(0.55, (aur.B / 100) * 0.35);
        ctxAu.strokeStyle = `rgba(56,189,248,${alpha})`; ctxAu.lineWidth = 1.5;
        [95, 145, 195].forEach((rLoop) => {
          ctxAu.beginPath(); ctxAu.ellipse(ex - rLoop * 0.45, ey, rLoop * 0.62, rLoop * 0.58, 0, 0, Math.PI * 2); ctxAu.stroke();
        });
      }

      // Earth
      const eg = ctxAu.createRadialGradient(ex - 20, ey - 20, 10, ex, ey, er);
      eg.addColorStop(0, '#60a5fa'); eg.addColorStop(0.65, '#1d4ed8'); eg.addColorStop(1, '#1e3a8a');
      ctxAu.fillStyle = eg; ctxAu.beginPath(); ctxAu.arc(ex, ey, er, 0, Math.PI * 2); ctxAu.fill();

      // Aurora glow at North & South poles
      if (aur.B >= 40 && aur.glow > 0.05) {
        [-1, 1].forEach((dir) => {
          const ag = ctxAu.createRadialGradient(ex, ey + dir * (er + 4), 4, ex, ey + dir * (er + 4), 44);
          ag.addColorStop(0, `rgba(52,211,153,${0.85 * aur.glow})`);
          ag.addColorStop(0.5, `rgba(167,139,250,${0.45 * aur.glow})`);
          ag.addColorStop(1, 'rgba(52,211,153,0)');
          ctxAu.fillStyle = ag; ctxAu.beginPath(); ctxAu.arc(ex, ey + dir * (er + 4), 44, 0, Math.PI * 2); ctxAu.fill();
        });
      }
      // Red danger glow on equator when B = 0
      if (aur.B === 0 && aur.eqHit > 0.05) {
        const dg = ctxAu.createRadialGradient(ex - er, ey, 6, ex - er, ey, 58);
        dg.addColorStop(0, `rgba(239,68,68,${0.8 * aur.eqHit})`); dg.addColorStop(1, 'rgba(239,68,68,0)');
        ctxAu.fillStyle = dg; ctxAu.beginPath(); ctxAu.arc(ex - er, ey, 58, 0, Math.PI * 2); ctxAu.fill();
      }

      // Update & draw solar wind particles
      const bFactor = aur.B / 100;
      const alive = [];
      for (const p of aur.particles) {
        const dx = ex - p.x, dy = ey - p.y, dist = Math.hypot(dx, dy);
        if (bFactor > 0.15 && dist < 210) {
          const targetY = ey + p.pole * (er + 6);
          p.vy += ((targetY - p.y) * 0.065 * bFactor) + Math.sin(p.x * 0.12) * 3.5;
          p.vy *= 0.92;
        }
        p.x += p.vx * 0.016; p.y += p.vy * 0.016;
        ctxAu.fillStyle = p.hue;
        ctxAu.beginPath(); ctxAu.arc(p.x, p.y, 2.6, 0, Math.PI * 2); ctxAu.fill();
        if (dist <= er + 6) {
          if (bFactor >= 0.4 && Math.abs(p.y - ey) > er * 0.55) aur.glow = Math.min(1, aur.glow + 0.18);
          else if (aur.B === 0) aur.eqHit = Math.min(1, aur.eqHit + 0.25);
        } else if (p.x < 750 && p.y > 0 && p.y < 330) {
          alive.push(p);
        }
      }
      aur.particles = alive;

      // HUD
      canvasHud(ctxAu, { x: 14, y: 10, lh: 34, stroke: null, bg: 'rgba(15,23,42,0.86)', lines: [
        { text: `地磁场强度 ${aur.B}%`, font: FS.hud, color: '#7dd3fc' },
        { text: aur.B === 0 ? '⚠️ 磁场消失，粒子直击赤道' : '✨ 粒子汇入两极，点亮极光', font: FS.hudSub, color: aur.B === 0 ? '#f87171' : '#34d399' },
      ] });
    }
    rafs.aur = requestAnimationFrame(stepAurora);
  mountLabBonus(root, '.em-tabs');
  }
  $('[data-in="aurB"]').addEventListener('input', (e) => {
    aur.B = Number(e.target.value); $('[data-out="aurB"]').textContent = `${aur.B}%`;
    if (aur.B === 0) { state.tasks.aurZero = true; checkAur(); }
  });
  $('[data-act="aurStorm"]').addEventListener('click', () => {
    spawnSolar(36);
    if (aur.B >= 60) state.tasks.aurNormal = true;
    if (aur.B === 0) state.tasks.aurZero = true;
    checkAur();
  });

  /* ==================== SUMMARY ==================== */
  function renderSummary() {
    const dN = KEYS.filter((k) => state.done[k]).length;
    $('[data-sum="title"]').textContent = dN === 3 ? '🏆 电磁宇宙专题通关！洛伦兹力与安培力全解锁' : `探索进行中：已完成 ${dN} / 3 场实验`;
    const rows = [
      { k: 'cyclotron', t: '1. 回旋加速器', p: '“磁场永远不做功，只负责当方向盘；真正踩油门的是中间缝隙的电场。”' },
      { k: 'railgun', t: '2. 电磁轨道炮', p: '“不用一克火药，只靠电流和磁场垂直一推，就能把铁块推出 7 倍音速。”' },
      { k: 'aurora', t: '3. 地球极光捕获', p: '“极光不是浪漫的巧合，而是地球磁场替人类挡下致命太阳辐射时的战损火花。”' },
    ];
    $('[data-sum="list"]').innerHTML = rows.map((r) => `<div class="em-recap"><div style="font-size:13.5px;font-weight:800">${state.done[r.k] ? '✅ ' : '🔒 '}${r.t}</div><div style="font-size:12.5px;color:var(--ink-2);margin-top:3px">${state.done[r.k] ? r.p : '完成对应实验探索后解锁'}</div></div>`).join('');
  }
  $('[data-act="resetAll"]').addEventListener('click', () => {
    KEYS.forEach((k) => { state.guesses[k] = null; state.done[k] = false; });
    state.tasks = { cycShot: false, cycBSet: new Set(), railShot: false, railMach5: false, aurNormal: false, aurZero: false };
    $$('.em-opt').forEach((b) => b.classList.remove('picked'));
    checkCyc(); checkRail(); checkAur(); updateProgress(); renderSummary(); switchTab('cyclotron');
  });
  $('[data-act="backSubjects"]').addEventListener('click', () => navigate('#/subjects'));

  view.innerHTML = '';
  view.appendChild(root);

  checkCyc(); checkRail(); checkAur(); updateProgress();
  drawCyc(); drawRail();
  rafs.aur = requestAnimationFrame(stepAurora);

  return () => {
    disposed = true;
    Object.values(rafs).forEach((id) => cancelAnimationFrame(id));
  };
}
