/* 生活中的物理：电动机与发电机工作原理（换向器秘密 + 实时交流/直流示波器） */

import { el } from '../ui.js';
import { navigate } from '../router.js';
import { mountLabBonus } from '../lab-bonus.js';
import { canvasHud, FS } from '../lab-canvas.js';

const LAB_CSS = `
.mglab{display:flex;flex-direction:column;gap:12px}
.mglab .mg-pill{display:inline-flex;align-items:center;gap:6px;padding:5px 11px;border-radius:999px;background:#fff;border:1px solid var(--line);font-size:12px;font-weight:700;color:var(--ink-2)}
.mglab .mg-dot{width:8px;height:8px;border-radius:50%;background:#d6c7b2;transition:background .2s}
.mglab .mg-dot.done{background:#059669}
.mglab .mg-tabs{display:flex;flex-wrap:wrap;gap:7px}
.mglab .mg-t{appearance:none;border:1px solid var(--line);background:#fff;color:var(--ink-2);padding:7px 12px;border-radius:999px;font-size:12px;font-weight:700;cursor:pointer;display:inline-flex;align-items:center;gap:5px}
.mglab .mg-t.active{background:#0f172a;border-color:#38bdf8;color:#7dd3fc}
.mglab .mg-t .chk{font-size:10.5px;padding:1px 5px;border-radius:999px;background:#ecfdf5;color:#059669}
.mglab .mg-t.active .chk{background:rgba(56,189,248,.22);color:#7dd3fc}
.mglab .mg-predict{background:#faf6ef;border:1px dashed #dfcfb7;border-radius:12px;padding:11px 12px;margin:10px 0 12px}
.mglab .mg-predict-q{font-size:13px;font-weight:800;margin:0 0 8px;color:var(--ink)}
.mglab .mg-opts{display:flex;flex-wrap:wrap;gap:7px}
.mglab .mg-opt{appearance:none;background:#fff;border:1px solid #dfd2be;color:var(--ink-2);padding:6px 11px;border-radius:9px;font-size:12px;font-weight:700;cursor:pointer}
.mglab .mg-opt.picked{background:#eff6ff;border-color:#2563eb;color:#2563eb}
.mglab .mg-stage{border-radius:14px;overflow:hidden;border:1px solid #1e293b;background:#0b1120;margin-bottom:12px;box-shadow:0 8px 24px rgba(15,23,42,.18)}
.mglab .mg-stage canvas{display:block;width:100%;height:auto;touch-action:none}
.mglab .mg-ctrl{display:flex;flex-wrap:wrap;align-items:center;gap:10px 18px;padding:10px 12px;background:#faf7f2;border-radius:12px;border:1px solid var(--line);margin-bottom:10px}
.mglab .mg-range{display:flex;align-items:center;gap:8px;flex:1 1 240px;min-width:210px}
.mglab .mg-range label{font-size:12px;font-weight:700;color:var(--ink-2);white-space:nowrap}
.mglab .mg-range input{flex:1;min-width:80px;cursor:pointer}
.mglab .mg-val{font-size:12px;font-weight:800;color:#2563eb;min-width:66px;text-align:right;white-space:nowrap;font-variant-numeric:tabular-nums}
.mglab .mg-tasks{display:flex;flex-wrap:wrap;gap:7px;margin-bottom:4px}
.mglab .mg-task{font-size:11.5px;font-weight:700;padding:4px 10px;border-radius:9px;background:#f5f0e7;color:var(--ink-3)}
.mglab .mg-task.done{background:#ecfdf5;color:#059669;border:1px solid #a7f3d0}
.mglab .mg-insight{margin-top:12px;padding:14px;border-radius:13px;background:linear-gradient(135deg,#f0fdf4 0%,#eff6ff 100%);border:1px solid #bbf7d0}
.mglab .mg-insight-q{font-size:15px;font-weight:900;color:var(--ink);margin:4px 0 6px;line-height:1.5}
.mglab .mg-insight-b{font-size:12.5px;color:var(--ink-2);margin:0 0 10px;line-height:1.65}
.mglab .mg-cmp{width:100%;border-collapse:collapse;font-size:12.5px;margin-top:10px}
.mglab .mg-cmp th,.mglab .mg-cmp td{padding:8px 10px;border-bottom:1px solid var(--line);text-align:left}
.mglab .mg-cmp th{background:#faf7f2;color:var(--ink-2);font-weight:800}
.mglab .mg-cmp th:first-child,.mglab .mg-cmp td:first-child{white-space:nowrap}
.mglab .hidden{display:none !important}
`;

export async function renderMotorGeneratorLab(view) {
  const KEYS = ['motor', 'gen'];
  const state = {
    tab: 'motor',
    guesses: { motor: null, gen: null },
    correct: { motor: 'stall', gen: 'parallel' },
    done: { motor: false, gen: false },
    tasks: { moNoComm: false, moSpin: false, geFast: false, geDc: false },
  };
  let disposed = false, rafId = 0;

  const root = el('div', { class: 'mglab' });
  const st = document.createElement('style'); st.textContent = LAB_CSS; root.appendChild(st);
  const dots = KEYS.map(() => el('span', { class: 'mg-dot' }));
  const progTxt = el('span', { text: '已探索 0 / 2' });
  root.appendChild(el('div', { class: 'topbar' }, [
    el('button', { class: 'back', text: '‹', onclick: () => { if (history.length > 1) history.back(); else navigate('#/subjects'); } }),
    el('div', { style: 'flex:1;min-width:0' }, [
      el('h1', { text: '生活中的物理：电动机与发电机' }),
      el('div', { class: 'sub', text: '电风扇怎么转起来 · 电站怎么发出交流电' }),
    ]),
    el('div', { class: 'mg-pill' }, [...dots, progTxt]),
  ]));

  const body = el('div', { html: `
  <nav class="mg-tabs">
    <button type="button" class="mg-t active" data-tab="motor">⚙️ 1. 电动机原理 <span class="chk hidden" data-chk="motor">✓</span></button>
    <button type="button" class="mg-t" data-tab="gen">💡 2. 发电机原理 <span class="chk hidden" data-chk="gen">✓</span></button>
    <button type="button" class="mg-t" data-tab="summary">🏆 对比总结</button>
  </nav>

  <!-- 1: ELECTRIC MOTOR -->
  <section class="panel" data-pane="motor">
    <div style="font-size:17px;font-weight:800;margin-bottom:4px">电动机（电生动）：为什么必须装上那两个“半圆铜环”？</div>
    <div style="font-size:12.5px;color:var(--ink-2)">通电线圈在 N–S 磁场中受安培力（左手定则）转动。试试先「拆掉换向器」看线圈卡死抖动，再装回换向器让它持续高速旋转！</div>
    <div class="mg-predict">
      <div class="mg-predict-q">① 先猜一猜：把直流电池直接接在转动线圈上、不装换向器，通电后线圈会一直转下去吗？</div>
      <div class="mg-opts" data-lab="motor">
        <button type="button" class="mg-opt" data-val="spin">会的，有电有磁场就会一直转</button>
        <button type="button" class="mg-opt" data-val="stall">不会！转过竖直平衡面后受力反向，会来回抖动卡停</button>
      </div>
    </div>
    <div class="mg-stage"><canvas data-cv="motor" width="740" height="320"></canvas></div>
    <div class="mg-ctrl">
      <div class="mg-range"><label>电池电压 U</label><input data-in="moU" type="range" min="0" max="12" value="6" step="1"><span class="mg-val" data-out="moU">6 V</span></div>
      <button type="button" class="btn sm" style="background:#059669" data-act="moComm">当前：已装换向器</button>
      <button type="button" class="btn sm ghost" data-act="moPol">反转电池正负极</button>
    </div>
    <div class="mg-tasks">
      <span class="mg-task" data-task="mo1">○ 目标 1：拆掉换向器，亲眼看线圈过平衡面后被拉回抖动</span>
      <span class="mg-task" data-task="mo2">○ 目标 2：装回换向器并反转一次正负极，看连续换向转动</span>
    </div>
    <div class="mg-insight hidden" data-insight="motor">
      <div style="font-size:11px;font-weight:800;color:#059669">✦ 顿悟时刻已解锁</div>
      <div class="mg-insight-q">“换向器每转半圈自动倒一次电流——让左边的线永远向上推、右边的线永远向下压，马达才能连转不停！”</div>
      <p class="mg-insight-b">电动机把<strong>电能转化为机械能</strong>（左手定则判安培力方向）。你家里的电风扇、洗衣机、无人机和新能源汽车驱动电机，核心秘密都在这种精准的“电流换向”。</p>
      <div class="row-between" style="gap:8px;flex-wrap:wrap"><span style="font-size:11.5px;font-weight:700;color:#2563eb" data-guess="motor"></span><button type="button" class="btn sm" data-goto="gen">下一场：发电机原理 →</button></div>
    </div>
  </section>

  <!-- 2: ELECTRIC GENERATOR -->
  <section class="panel hidden" data-pane="gen">
    <div style="font-size:17px;font-weight:800;margin-bottom:4px">发电机（动生电）：转动的线圈怎么在示波器上画出正弦波？</div>
    <div style="font-size:12.5px;color:var(--ink-2)">外力摇动线圈在磁场中切割磁感线，右侧示波器实时画出感应电压波形！调高转速，再切换「双滑环 AC / 换向器 DC」对比。</div>
    <div class="mg-predict">
      <div class="mg-predict-q">① 先猜一猜：发电机线圈匀速旋转时，哪一瞬间小灯泡最亮、感应电动势最大？</div>
      <div class="mg-opts" data-lab="gen">
        <button type="button" class="mg-opt" data-val="perp">线圈竖直垂直磁感线（穿过磁通量最大时）</button>
        <button type="button" class="mg-opt" data-val="parallel">线圈水平平行磁感线（两边垂直切割磁感线最快时！）</button>
      </div>
    </div>
    <div class="mg-stage"><canvas data-cv="gen" width="740" height="320"></canvas></div>
    <div class="mg-ctrl">
      <div class="mg-range"><label>摇动转速 ω</label><input data-in="geW" type="range" min="0.5" max="3.0" value="1.2" step="0.1"><span class="mg-val" data-out="geW">1.2 圈/秒</span></div>
      <button type="button" class="btn sm" style="background:#2563eb" data-act="geMode">输出：双滑环（交流电 AC）</button>
      <button type="button" class="btn sm ghost" data-act="gePause">暂停观察</button>
    </div>
    <div class="mg-tasks">
      <span class="mg-task" data-task="ge1">○ 目标 1：把转速拉到 ≥ 2.2 圈/秒，观察波形幅度与频率同时变大</span>
      <span class="mg-task" data-task="ge2">○ 目标 2：切换到「半圆换向器（直流电 DC）」，对比波形翻转</span>
    </div>
    <div class="mg-insight hidden" data-insight="gen">
      <div style="font-size:11px;font-weight:800;color:#059669">✦ 顿悟时刻已解锁</div>
      <div class="mg-insight-q">“磁通量最大时变化率为零（灯灭），磁通量为零时切割最快（灯最亮）——转一圈自然长出一个正弦波！”</div>
      <p class="mg-insight-b">发电机把<strong>机械能转化为电能</strong>（右手定则判感应电流方向），峰值电动势 <code>Eₘ = NBSω</code>，转速越快电压越高、频率越密。三峡水电站与风力发电机都是这样把 50Hz 交流电送进千家万户。</p>
      <div class="row-between" style="gap:8px;flex-wrap:wrap"><span style="font-size:11.5px;font-weight:700;color:#2563eb" data-guess="gen"></span><button type="button" class="btn sm" data-goto="summary">查看双机对比总结 🏆</button></div>
    </div>
  </section>

  <!-- SUMMARY -->
  <section class="panel hidden" data-pane="summary">
    <div style="text-align:center;margin-bottom:8px">
      <div style="font-size:18px;font-weight:900" data-sum="title">探索进行中：已完成 0 / 2 场电机实验</div>
      <div style="font-size:12.5px;color:var(--ink-2);margin-top:4px">电动机和发电机结构几乎一模一样，本质上互为逆过程——记住这张对照表永不混淆！</div>
    </div>
    <table class="mg-cmp">
      <thead><tr><th>对比维度</th><th>⚙️ 电动机</th><th>💡 发电机</th></tr></thead>
      <tbody>
        <tr><td><strong>能量转化</strong></td><td>电能 → 机械能</td><td>机械能 → 电能</td></tr>
        <tr><td><strong>核心原理</strong></td><td>通电导体在磁场受安培力</td><td>闭合线圈切割磁感线（电磁感应）</td></tr>
        <tr><td><strong>判断定则</strong></td><td>左手定则（力）</td><td>右手定则（电）</td></tr>
        <tr><td><strong>外电路特征</strong></td><td>必须接<strong>电源（电池）</strong></td><td>无电源，接<strong>用电器/灯泡</strong></td></tr>
        <tr><td><strong>生活实例</strong></td><td>电风扇、电动车、洗衣机</td><td>水电站、风力发电、手摇电筒</td></tr>
      </tbody>
    </table>
    <div class="row-between" style="margin-top:14px">
      <button type="button" class="btn sm ghost" data-act="resetAll">重新探索</button>
      <button type="button" class="btn sm" data-act="backSubjects">返回路线 →</button>
    </div>
  </section>
  ` });
  root.appendChild(body);

  const $ = (s) => body.querySelector(s);
  const $$ = (s) => [...body.querySelectorAll(s)];
  function updateGuess(lab) { const o = $(`[data-guess="${lab}"]`); if (!o) return; const g = state.guesses[lab]; o.textContent = !g ? '下次可先做直觉押注再动手！' : (g === state.correct[lab] ? '🎯 直觉押注命中真相！' : '💡 动画反转了刚才的直觉！'); }
  function setTask(n, ok, txt) { const t = $(`[data-task="${n}"]`); t.classList.toggle('done', ok); t.textContent = (ok ? '✓ ' : '○ ') + txt; }
  function updateProgress() {
    let n = 0;
    KEYS.forEach((k, i) => { const ok = state.done[k]; if (ok) n++; dots[i].classList.toggle('done', ok); $(`[data-chk="${k}"]`).classList.toggle('hidden', !ok); $(`[data-insight="${k}"]`).classList.toggle('hidden', !ok); if (ok) updateGuess(k); });
    progTxt.textContent = `已探索 ${n} / 2`;
  }
  function switchTab(name) {
    state.tab = name;
    $$('.mg-t').forEach((b) => b.classList.toggle('active', b.dataset.tab === name));
    $$('[data-pane]').forEach((p) => p.classList.toggle('hidden', p.dataset.pane !== name));
    if (name === 'summary') {
      const dN = KEYS.filter((k) => state.done[k]).length;
      $('[data-sum="title"]').textContent = dN === 2 ? '🏆 电动机 & 发电机原理全部通关！' : `探索进行中：已完成 ${dN} / 2 场实验`;
    }
  }
  $$('.mg-t').forEach((b) => b.addEventListener('click', () => switchTab(b.dataset.tab)));
  $$('[data-goto]').forEach((b) => b.addEventListener('click', () => switchTab(b.dataset.goto)));
  $$('.mg-opts').forEach((w) => {
    const lab = w.dataset.lab;
    w.querySelectorAll('.mg-opt').forEach((btn) => btn.addEventListener('click', () => {
      state.guesses[lab] = btn.dataset.val; w.querySelectorAll('.mg-opt').forEach((x) => x.classList.toggle('picked', x === btn)); updateGuess(lab);
    }));
  });

  function drawMagnets(ctx, cx, cy) {
    ctx.fillStyle = '#dc2626'; ctx.beginPath(); ctx.roundRect(cx - 172, cy - 68, 48, 136, 8); ctx.fill();
    ctx.fillStyle = '#2563eb'; ctx.beginPath(); ctx.roundRect(cx + 124, cy - 68, 48, 136, 8); ctx.fill();
    ctx.fillStyle = '#fff'; ctx.font = FS.label;
    ctx.fillText('N', cx - 157, cy + 8); ctx.fillText('S', cx + 141, cy + 8);
    ctx.strokeStyle = 'rgba(148,163,184,0.22)'; ctx.lineWidth = 1.4;
    for (let dy = -48; dy <= 48; dy += 24) {
      ctx.beginPath(); ctx.moveTo(cx - 120, cy + dy); ctx.lineTo(cx + 120, cy + dy); ctx.stroke();
    }
  }

  /* ---- 1. MOTOR ---- */
  const cMo = $('[data-cv="motor"]'), ctxMo = cMo.getContext('2d');
  const mo = { U: 6, comm: true, pol: 1, theta: 0.35, omega: 0 };
  function checkMo() {
    setTask('mo1', state.tasks.moNoComm, '目标 1：拆掉换向器看线圈过平衡面来回抖动');
    setTask('mo2', state.tasks.moSpin, '目标 2：装回换向器并反转正负极看连续旋转');
    if (state.tasks.moNoComm && state.tasks.moSpin && !state.done.motor) { state.done.motor = true; updateProgress(); }
  }
  $('[data-in="moU"]').addEventListener('input', (e) => { mo.U = Number(e.target.value); $('[data-out="moU"]').textContent = `${mo.U} V`; });
  $('[data-act="moComm"]').addEventListener('click', (e) => {
    mo.comm = !mo.comm;
    e.currentTarget.textContent = mo.comm ? '当前：已装换向器' : '当前：已拆换向器（直连）';
    e.currentTarget.style.background = mo.comm ? '#059669' : '#dc2626';
    if (!mo.comm) { state.tasks.moNoComm = true; checkMo(); }
  });
  $('[data-act="moPol"]').addEventListener('click', () => {
    mo.pol = -mo.pol;
    if (mo.comm && mo.U > 0) { state.tasks.moSpin = true; checkMo(); }
  });

  /* ---- 2. GENERATOR ---- */
  const cGe = $('[data-cv="gen"]'), ctxGe = cGe.getContext('2d');
  const ge = { w: 1.2, dc: false, paused: false, theta: 0, wave: [] };
  function checkGe() {
    setTask('ge1', state.tasks.geFast, '目标 1：转速拉到 ≥ 2.2 圈/秒观察幅频同增');
    setTask('ge2', state.tasks.geDc, '目标 2：切换「换向器直流电 DC」对比波形');
    if (state.tasks.geFast && state.tasks.geDc && !state.done.gen) { state.done.gen = true; updateProgress(); }
  }
  $('[data-in="geW"]').addEventListener('input', (e) => {
    ge.w = Number(e.target.value); $('[data-out="geW"]').textContent = `${ge.w.toFixed(1)} 圈/秒`;
    if (ge.w >= 2.2) { state.tasks.geFast = true; checkGe(); }
  });
  $('[data-act="geMode"]').addEventListener('click', (e) => {
    ge.dc = !ge.dc;
    e.currentTarget.textContent = ge.dc ? '输出：半圆换向器（直流电 DC）' : '输出：双滑环（交流电 AC）';
    e.currentTarget.style.background = ge.dc ? '#d97706' : '#2563eb';
    if (ge.dc) { state.tasks.geDc = true; checkGe(); }
  });
  $('[data-act="gePause"]').addEventListener('click', (e) => {
    ge.paused = !ge.paused; e.currentTarget.textContent = ge.paused ? '继续旋转' : '暂停观察';
  });

  function loop() {
    if (disposed) return;

    if (state.tab === 'motor') {
      const cx = 225, cy = 162, r = 74;
      const cosT = Math.cos(mo.theta);
      // With commutator, current sign flips whenever cosT changes sign so torque stays unidirectional!
      const effI = mo.U * mo.pol * (mo.comm ? (cosT >= 0 ? 1 : -1) : 1);
      const torque = effI * cosT * 0.42;
      mo.omega = (mo.omega + torque * 0.05) * 0.965;
      mo.theta += mo.omega * 0.06;

      ctxMo.clearRect(0, 0, cMo.width, cMo.height); ctxMo.fillStyle = '#0b1120'; ctxMo.fillRect(0, 0, cMo.width, cMo.height);
      drawMagnets(ctxMo, cx, cy);

      // Neutral equilibrium vertical dashed line
      ctxMo.strokeStyle = 'rgba(251,191,36,0.28)'; ctxMo.setLineDash([4, 4]);
      ctxMo.beginPath(); ctxMo.moveTo(cx, cy - 95); ctxMo.lineTo(cx, cy + 95); ctxMo.stroke(); ctxMo.setLineDash([]);

      // Coil bar end-view (a on one end, c on opposite end)
      const ax = cx + Math.cos(mo.theta) * r, ay = cy + Math.sin(mo.theta) * r;
      const bx = cx - Math.cos(mo.theta) * r, by = cy - Math.sin(mo.theta) * r;
      ctxMo.strokeStyle = '#fbbf24'; ctxMo.lineWidth = 5; ctxMo.beginPath(); ctxMo.moveTo(ax, ay); ctxMo.lineTo(bx, by); ctxMo.stroke();

      // Current symbols + Ampere force arrows (vertical!)
      const fDir = effI === 0 ? 0 : (effI > 0 ? 1 : -1);
      const drawWire = (x, y, outOfPage, fy) => {
        ctxMo.fillStyle = '#f59e0b'; ctxMo.beginPath(); ctxMo.arc(x, y, 14, 0, Math.PI * 2); ctxMo.fill();
        ctxMo.fillStyle = '#0b1120'; ctxMo.font = FS.label;
        ctxMo.fillText(outOfPage ? '⊙' : '⊗', x - 9, y + 7);
        if (fy !== 0) {
          ctxMo.strokeStyle = '#34d399'; ctxMo.lineWidth = 3;
          ctxMo.beginPath(); ctxMo.moveTo(x, y); ctxMo.lineTo(x, y + fy * 42); ctxMo.stroke();
        }
      };
      drawWire(ax, ay, fDir > 0, fDir * (mo.U > 0 ? 1 : 0));
      drawWire(bx, by, fDir < 0, -fDir * (mo.U > 0 ? 1 : 0));

      // Split-ring commutator visual at center
      ctxMo.strokeStyle = mo.comm ? '#34d399' : '#f87171'; ctxMo.lineWidth = 4;
      if (mo.comm) {
        ctxMo.beginPath(); ctxMo.arc(cx, cy, 18, mo.theta + 0.25, mo.theta + Math.PI - 0.25); ctxMo.stroke();
        ctxMo.beginPath(); ctxMo.arc(cx, cy, 18, mo.theta + Math.PI + 0.25, mo.theta + Math.PI * 2 - 0.25); ctxMo.stroke();
      } else {
        ctxMo.beginPath(); ctxMo.arc(cx, cy, 18, 0, Math.PI * 2); ctxMo.stroke();
      }

      // 遥测面板：改用自适应信息板，字号按放大后的逻辑像素写（窄屏不会被压到 5px）
      const rpm = Math.round(Math.abs(mo.omega) * 48);
      canvasHud(ctxMo, { x: 728, y: 10, lh: 29, align: 'right', bg: 'rgba(15,23,42,0.88)', stroke: '#243044', lines: [
        { text: '电动机状态监控', font: FS.hud, color: '#7dd3fc' },
        { text: `电源 ${mo.U} V · ${mo.pol > 0 ? '正接 ↻' : '反接 ↺'}`, font: FS.small, color: '#cbd5e1' },
        { text: mo.comm ? '✓ 换向器：半圈自动倒电流' : '⚠️ 无换向器：受力反向！', font: FS.small, color: mo.comm ? '#34d399' : '#f87171' },
        { text: `当前转速 ${rpm} RPM`, font: FS.hudSub, color: '#fde047' },
        { text: '绿色箭头 = 左手定则安培力 F', font: FS.small, color: '#94a3b8' },
        { text: '⊙ 电流向外 · ⊗ 电流向内', font: FS.small, color: '#94a3b8' },
        { text: mo.comm ? '平稳持续转动中！' : '被拉回平衡面来回抖动！', font: FS.small, color: mo.comm ? '#34d399' : '#f87171' },
      ] });
    }

    if (state.tab === 'gen') {
      const cx = 205, cy = 165, r = 68;
      if (!ge.paused) ge.theta += ge.w * 0.055;
      // Induced EMF proportional to w * cos(theta) (max when horizontal theta=0/pi, zero when vertical theta=pi/2)
      const rawE = ge.w * Math.cos(ge.theta);
      const outE = ge.dc ? Math.abs(rawE) : rawE;
      if (!ge.paused) { ge.wave.push(outE); if (ge.wave.length > 220) ge.wave.shift(); }

      ctxGe.clearRect(0, 0, cGe.width, cGe.height); ctxGe.fillStyle = '#0b1120'; ctxGe.fillRect(0, 0, cGe.width, cGe.height);
      drawMagnets(ctxGe, cx, cy);

      // Neutral plane vertical dashed line
      ctxGe.strokeStyle = 'rgba(148,163,184,0.35)'; ctxGe.setLineDash([4, 4]);
      ctxGe.beginPath(); ctxGe.moveTo(cx, cy - 90); ctxGe.lineTo(cx, cy + 90); ctxGe.stroke(); ctxGe.setLineDash([]);
      ctxGe.fillStyle = '#94a3b8'; ctxGe.font = FS.small; ctxGe.fillText('中性面 (e=0)', cx - 52, cy - 96);

      // Rotating coil
      const ax = cx + Math.cos(ge.theta) * r, ay = cy + Math.sin(ge.theta) * r;
      const bx = cx - Math.cos(ge.theta) * r, by = cy - Math.sin(ge.theta) * r;
      ctxGe.strokeStyle = '#38bdf8'; ctxGe.lineWidth = 5; ctxGe.beginPath(); ctxGe.moveTo(ax, ay); ctxGe.lineTo(bx, by); ctxGe.stroke();
      ctxGe.fillStyle = '#fde047'; ctxGe.beginPath(); ctxGe.arc(ax, ay, 8, 0, Math.PI * 2); ctxGe.arc(bx, by, 8, 0, Math.PI * 2); ctxGe.fill();

      // Light bulb brightness synced to |outE|
      const bright = Math.min(1, Math.abs(outE) / 2.6);
      if (bright > 0.06) {
        const bg = ctxGe.createRadialGradient(cx, 282, 4, cx, 282, 34 * bright + 8);
        bg.addColorStop(0, `rgba(253,224,71,${0.9 * bright})`); bg.addColorStop(1, 'rgba(253,224,71,0)');
        ctxGe.fillStyle = bg; ctxGe.beginPath(); ctxGe.arc(cx, 282, 34 * bright + 8, 0, Math.PI * 2); ctxGe.fill();
      }
      ctxGe.fillStyle = bright > 0.1 ? `rgba(253,224,71,${0.35 + 0.65 * bright})` : '#334155';
      ctxGe.beginPath(); ctxGe.arc(cx, 282, 14, 0, Math.PI * 2); ctxGe.fill();
      ctxGe.fillStyle = '#cbd5e1'; ctxGe.font = FS.small; ctxGe.fillText('负载灯泡', cx + 26, 292);

      // Right: Live Oscilloscope
      const ox = 415, oy = 32, ow = 300, oh = 220, midY = oy + oh / 2;
      ctxGe.fillStyle = '#07101f'; ctxGe.strokeStyle = '#243044'; ctxGe.lineWidth = 1.5;
      ctxGe.beginPath(); ctxGe.roundRect(ox, oy, ow, oh, 12); ctxGe.fill(); ctxGe.stroke();
      ctxGe.strokeStyle = 'rgba(148,163,184,0.25)'; ctxGe.beginPath(); ctxGe.moveTo(ox + 10, midY); ctxGe.lineTo(ox + ow - 10, midY); ctxGe.stroke();
      ctxGe.fillStyle = '#7dd3fc'; ctxGe.font = FS.small;
      ctxGe.fillText(ge.dc ? '实时示波器：脉动直流 DC' : '实时示波器：正弦交流 AC', ox + 14, oy + 26);
      if (ge.wave.length > 1) {
        ctxGe.strokeStyle = ge.dc ? '#fbbf24' : '#34d399'; ctxGe.lineWidth = 2.6;
        ctxGe.beginPath();
        ge.wave.forEach((v, i) => {
          const px = ox + 14 + (i / 220) * (ow - 28);
          const py = midY - v * 28;
          if (i === 0) ctxGe.moveTo(px, py); else ctxGe.lineTo(px, py);
        });
        ctxGe.stroke();
      }
      ctxGe.fillStyle = '#fde047'; ctxGe.font = FS.small;
      ctxGe.fillText(`瞬时 e = ${outE >= 0 ? '+' : ''}${(outE * 4.5).toFixed(1)} V · 峰值 ${(ge.w * 4.5).toFixed(1)} V`, ox + 14, oy + oh + 26);
    }

    rafId = requestAnimationFrame(loop);
  }

  $('[data-act="resetAll"]').addEventListener('click', () => {
    KEYS.forEach((k) => { state.guesses[k] = null; state.done[k] = false; });
    state.tasks = { moNoComm: false, moSpin: false, geFast: false, geDc: false };
    $$('.mg-opt').forEach((b) => b.classList.remove('picked'));
    checkMo(); checkGe(); updateProgress(); switchTab('motor');
  });
  $('[data-act="backSubjects"]').addEventListener('click', () => navigate('#/subjects'));

  view.innerHTML = ''; view.appendChild(root);
  mountLabBonus(root, '.mg-tabs');
  checkMo(); checkGe(); updateProgress();
  rafId = requestAnimationFrame(loop);
  return () => { disposed = true; cancelAnimationFrame(rafId); };
}
