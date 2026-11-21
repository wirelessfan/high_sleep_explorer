/* 专题 E：风洞与流体奇观（机翼风洞失速 + 足球香蕉球 + 站台安全线伯努利） */

import { el } from '../ui.js';
import { navigate } from '../router.js';
import { FS, canvasHud } from '../lab-canvas.js';
import { mountLabBonus } from '../lab-bonus.js';

const LAB_CSS = `
.fllab{display:flex;flex-direction:column;gap:12px}
.fllab .fl-pill{display:inline-flex;align-items:center;gap:6px;padding:5px 11px;border-radius:999px;background:#fff;border:1px solid var(--line);font-size:12px;font-weight:700;color:var(--ink-2)}
.fllab .fl-dot{width:8px;height:8px;border-radius:50%;background:#d6c7b2;transition:background .2s}
.fllab .fl-dot.done{background:#059669}
.fllab .fl-tabs{display:flex;flex-wrap:wrap;gap:7px}
.fllab .fl-tab{appearance:none;border:1px solid var(--line);background:#fff;color:var(--ink-2);padding:7px 12px;border-radius:999px;font-size:12px;font-weight:700;cursor:pointer;display:inline-flex;align-items:center;gap:5px}
.fllab .fl-tab.active{background:#0f172a;border-color:#34d399;color:#6ee7b7}
.fllab .fl-tab .chk{font-size:10.5px;padding:1px 5px;border-radius:999px;background:#ecfdf5;color:#059669}
.fllab .fl-tab.active .chk{background:rgba(52,211,153,.24);color:#6ee7b7}
.fllab .fl-predict{background:#faf6ef;border:1px dashed #dfcfb7;border-radius:12px;padding:11px 12px;margin:10px 0 12px}
.fllab .fl-predict-q{font-size:13px;font-weight:800;margin:0 0 8px;color:var(--ink)}
.fllab .fl-opts{display:flex;flex-wrap:wrap;gap:7px}
.fllab .fl-opt{appearance:none;background:#fff;border:1px solid #dfd2be;color:var(--ink-2);padding:6px 11px;border-radius:9px;font-size:12px;font-weight:700;cursor:pointer}
.fllab .fl-opt.picked{background:#eff6ff;border-color:#2563eb;color:#2563eb}
.fllab .fl-stage{border-radius:14px;overflow:hidden;border:1px solid #1e293b;background:#0b1120;margin-bottom:12px;box-shadow:0 8px 24px rgba(15,23,42,.18)}
.fllab .fl-stage canvas{display:block;width:100%;height:auto;touch-action:none}
.fllab .fl-ctrl{display:flex;flex-wrap:wrap;align-items:center;gap:10px 18px;padding:10px 12px;background:#faf7f2;border-radius:12px;border:1px solid var(--line);margin-bottom:10px}
.fllab .fl-range{display:flex;align-items:center;gap:8px;flex:1 1 240px;min-width:220px}
.fllab .fl-range label{font-size:12px;font-weight:700;color:var(--ink-2);white-space:nowrap}
.fllab .fl-range input{flex:1;min-width:80px;cursor:pointer}
.fllab .fl-val{font-size:12px;font-weight:800;color:#2563eb;min-width:64px;text-align:right;white-space:nowrap;font-variant-numeric:tabular-nums}
.fllab .fl-tasks{display:flex;flex-wrap:wrap;gap:7px;margin-bottom:4px}
.fllab .fl-task{font-size:11.5px;font-weight:700;padding:4px 10px;border-radius:9px;background:#f5f0e7;color:var(--ink-3)}
.fllab .fl-task.done{background:#ecfdf5;color:#059669;border:1px solid #a7f3d0}
.fllab .fl-insight{margin-top:12px;padding:14px;border-radius:13px;background:linear-gradient(135deg,#f0fdf4 0%,#eff6ff 100%);border:1px solid #bbf7d0}
.fllab .fl-insight-q{font-size:15px;font-weight:900;color:var(--ink);margin:4px 0 6px;line-height:1.5}
.fllab .fl-insight-b{font-size:12.5px;color:var(--ink-2);margin:0 0 10px;line-height:1.65}
.fllab .fl-recap{border:1px solid var(--line);border-radius:12px;padding:11px 13px;background:#fffdf9;margin-bottom:8px}
.fllab .hidden{display:none !important}
`;

export async function renderFluidWindtunnelLab(view) {
  const KEYS = ['wing', 'banana', 'train'];
  const state = {
    tab: 'wing',
    guesses: { wing: null, banana: null, train: null },
    correct: { wing: 'stall', banana: 'spin', train: 'pushin' },
    done: { wing: false, banana: false, train: false },
    tasks: { wiLift: false, wiStall: false, baStraight: false, baGoal: false, trSlow: false, trFast: false },
  };
  let disposed = false, rafId = 0;

  const root = el('div', { class: 'fllab' });
  const st = document.createElement('style'); st.textContent = LAB_CSS; root.appendChild(st);
  const dots = KEYS.map(() => el('span', { class: 'fl-dot' }));
  const progTxt = el('span', { text: '已探索 0 / 3' });
  root.appendChild(el('div', { class: 'topbar' }, [
    el('button', { class: 'back', text: '‹', onclick: () => { if (history.length > 1) history.back(); else navigate('#/subjects'); } }),
    el('div', { style: 'flex:1;min-width:0' }, [
      el('h1', { text: '风洞与流体奇观' }),
      el('div', { class: 'sub', text: '机翼风洞失速 · 足球香蕉球 · 站台安全线' }),
    ]),
    el('div', { class: 'fl-pill' }, [...dots, progTxt]),
  ]));

  const body = el('div', { html: `
  <nav class="fl-tabs">
    <button type="button" class="fl-tab active" data-tab="wing">🛫 1. 机翼风洞与失速 <span class="chk hidden" data-chk="wing">✓</span></button>
    <button type="button" class="fl-tab" data-tab="banana">⚽ 2. 足球香蕉球 <span class="chk hidden" data-chk="banana">✓</span></button>
    <button type="button" class="fl-tab" data-tab="train">🚄 3. 站台安全线 <span class="chk hidden" data-chk="train">✓</span></button>
    <button type="button" class="fl-tab" data-tab="summary">🏆 专题总结</button>
  </nav>

  <section class="panel" data-pane="wing">
    <div style="font-size:17px;font-weight:800;margin-bottom:4px">烟雾风洞：机翼怎么产生升力？仰角太大为何突然失速？</div>
    <div style="font-size:12.5px;color:var(--ink-2)">拖动机翼迎角 α，看风洞流线如何托举起飞；把迎角拉过 18°，亲眼看上表面流线撕裂爆出失速漩涡！</div>
    <div class="fl-predict">
      <div class="fl-predict-q">① 先猜一猜：飞机想爬升得更快，把机头仰角越拉越高，升力会一直变大吗？</div>
      <div class="fl-opts" data-lab="wing">
        <button type="button" class="fl-opt" data-val="more">会的，仰角越大兜住的风越多</button>
        <button type="button" class="fl-opt" data-val="stall">不会！超过临界迎角气流分离成漩涡，升力瞬间暴跌失速</button>
      </div>
    </div>
    <div class="fl-stage"><canvas data-cv="wing" width="740" height="310"></canvas></div>
    <div class="fl-ctrl">
      <div class="fl-range"><label>机翼迎角 α</label><input data-in="wiAng" type="range" min="0" max="28" value="8" step="1"><span class="fl-val" data-out="wiAng">8°</span></div>
      <div class="fl-range"><label>风洞风速</label><input data-in="wiV" type="range" min="120" max="320" value="220" step="20"><span class="fl-val" data-out="wiV">220 km/h</span></div>
    </div>
    <div class="fl-tasks">
      <span class="fl-task" data-task="wi1">○ 目标 1：在 6°–14° 观察稳定升力与平滑流线</span>
      <span class="fl-task" data-task="wi2">○ 目标 2：把迎角拉到 ≥ 20° 触发失速漩涡告警</span>
    </div>
    <div class="fl-insight hidden" data-insight="wing">
      <div style="font-size:11px;font-weight:800;color:#059669">✦ 顿悟时刻已解锁</div>
      <div class="fl-insight-q">“机翼上方流速快压强低、下方流速慢压强高——但一旦贪心抬头过猛，气流撕裂立刻失速。”</div>
      <p class="fl-insight-b">依据伯努利原理与牛顿反作用，合适迎角形成强劲升力；但超过约 18° 临界迎角时，上翼面气流剥离产生剧烈湍流，升力骤降、阻力暴增。</p>
      <div class="row-between" style="gap:8px;flex-wrap:wrap"><span style="font-size:11.5px;font-weight:700;color:#2563eb" data-guess="wing"></span><button type="button" class="btn sm" data-goto="banana">下一场：足球香蕉球 →</button></div>
    </div>
  </section>

  <section class="panel hidden" data-pane="banana">
    <div style="font-size:17px;font-weight:800;margin-bottom:4px">任意球香蕉球：怎么让足球绕过人墙拐进死角？</div>
    <div style="font-size:12.5px;color:var(--ink-2)">先不加旋转直踢一脚撞上人墙，再调高「弧线转速」亲手踢出一记绕过人墙破门的马格努斯香蕉球！</div>
    <div class="fl-predict">
      <div class="fl-predict-q">① 先猜一猜：足球在空中拐出夸张的香蕉弧线，背后的物理功臣是谁？</div>
      <div class="fl-opts" data-lab="banana">
        <button type="button" class="fl-opt" data-val="wind">全靠球场上刚好刮来一阵侧风</button>
        <button type="button" class="fl-opt" data-val="spin">球高速自转带动两侧气流速度不同，产生侧向压强差（马格努斯效应）</button>
      </div>
    </div>
    <div class="fl-stage"><canvas data-cv="banana" width="740" height="310"></canvas></div>
    <div class="fl-ctrl">
      <div class="fl-range"><label>足球旋转强度</label><input data-in="baSpin" type="range" min="-10" max="10" value="0" step="1"><span class="fl-val" data-out="baSpin">0 (直球)</span></div>
      <button type="button" class="btn sm" style="background:#059669" data-act="baKick">⚽ 罚球射门！</button>
      <button type="button" class="btn sm ghost" data-act="baReset">重置</button>
    </div>
    <div class="fl-tasks">
      <span class="fl-task" data-task="ba1">○ 目标 1：不加旋转踢一次直球，看球被正面人墙挡住</span>
      <span class="fl-task" data-task="ba2">○ 目标 2：加上强旋转绕过人墙，踢进右侧球门！</span>
    </div>
    <div class="fl-insight hidden" data-insight="banana">
      <div style="font-size:11px;font-weight:800;color:#059669">✦ 顿悟时刻已解锁</div>
      <div class="fl-insight-q">“旋转让足球一侧顺风更快、另一侧逆风更慢——气压差在空中硬生生把球推弯了！”</div>
      <p class="fl-insight-b">这就是<strong>马格努斯效应</strong>：旋转球体带动表面空气，流速快的一侧压强低，产生垂直飞行方向的横向力。乒乓球弧圈球和棒球曲球全是同一原理。</p>
      <div class="row-between" style="gap:8px;flex-wrap:wrap"><span style="font-size:11.5px;font-weight:700;color:#2563eb" data-guess="banana"></span><button type="button" class="btn sm" data-goto="train">下一场：站台安全线 →</button></div>
    </div>
  </section>

  <section class="panel hidden" data-pane="train">
    <div style="font-size:17px;font-weight:800;margin-bottom:4px">高铁站台安全线：为什么不能越过那条黄线？</div>
    <div style="font-size:12.5px;color:var(--ink-2)">拖动高铁进站速度从 40 km/h 拉到 280 km/h，观察乘客身前与身后的气压柱对比和推力箭头！</div>
    <div class="fl-predict">
      <div class="fl-predict-q">① 先猜一猜：高铁高速擦身而过时，站在太近的人会怎样？</div>
      <div class="fl-opts" data-lab="train">
        <button type="button" class="fl-opt" data-val="pushout">被车头带起的狂风远远推离铁轨</button>
        <button type="button" class="fl-opt" data-val="pushin">身前气流快压强骤降，被身后的大气压狠狠推向列车！</button>
      </div>
    </div>
    <div class="fl-stage"><canvas data-cv="train" width="740" height="310"></canvas></div>
    <div class="fl-ctrl">
      <div class="fl-range"><label>列车过站速度</label><input data-in="trV" type="range" min="40" max="300" value="60" step="20"><span class="fl-val" data-out="trV">60 km/h</span></div>
    </div>
    <div class="fl-tasks">
      <span class="fl-task" data-task="tr1">○ 目标 1：低速（≤ 80 km/h）观察前后气压接近平衡</span>
      <span class="fl-task" data-task="tr2">○ 目标 2：把车速拉到 ≥ 240 km/h，看低压吸力告警</span>
    </div>
    <div class="fl-insight hidden" data-insight="train">
      <div style="font-size:11px;font-weight:800;color:#059669">✦ 顿悟时刻已解锁</div>
      <div class="fl-insight-q">“不是列车在吸你，是车侧气压暴跌后，你背后正常的大气压把你狠狠推向了铁轨。”</div>
      <p class="fl-insight-b">流体流速越大压强越小（伯努利方程 <code>p + ½ρv² = 恒量</code>）。站台黄线留出安全距离，就是为了避免高速气流造成的致命压强差。</p>
      <div class="row-between" style="gap:8px;flex-wrap:wrap"><span style="font-size:11.5px;font-weight:700;color:#2563eb" data-guess="train"></span><button type="button" class="btn sm" data-goto="summary">查看专题总结 🏆</button></div>
    </div>
  </section>

  <section class="panel hidden" data-pane="summary">
    <div style="text-align:center;margin-bottom:12px">
      <div style="font-size:18px;font-weight:900" data-sum="title">探索进行中：已完成 0 / 3 场流体实验</div>
      <div style="font-size:12.5px;color:var(--ink-2);margin-top:4px">流速快则压强小——一条伯努利原理，同时解释了飞机升空、香蕉球破门与高铁安全线。</div>
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
    $$('.fl-tab').forEach((b) => b.classList.toggle('active', b.dataset.tab === name));
    $$('[data-pane]').forEach((p) => p.classList.toggle('hidden', p.dataset.pane !== name));
    if (name === 'summary') renderSummary();
  }
  $$('.fl-tab').forEach((b) => b.addEventListener('click', () => switchTab(b.dataset.tab)));
  $$('[data-goto]').forEach((b) => b.addEventListener('click', () => switchTab(b.dataset.goto)));
  $$('.fl-opts').forEach((w) => {
    const lab = w.dataset.lab;
    w.querySelectorAll('.fl-opt').forEach((btn) => btn.addEventListener('click', () => {
      state.guesses[lab] = btn.dataset.val; w.querySelectorAll('.fl-opt').forEach((x) => x.classList.toggle('picked', x === btn)); updateGuess(lab);
    }));
  });

  /* ---- 1. WING ---- */
  const cWi = $('[data-cv="wing"]'), ctxWi = cWi.getContext('2d');
  const wi = { ang: 8, v: 220, phase: 0 };
  function checkWi() {
    setTask('wi1', state.tasks.wiLift, '目标 1：在 6°–14° 观察稳定升力与平滑流线');
    setTask('wi2', state.tasks.wiStall, '目标 2：把迎角拉到 ≥ 20° 触发失速漩涡');
    if (state.tasks.wiLift && state.tasks.wiStall && !state.done.wing) { state.done.wing = true; updateProgress(); }
  }
  $('[data-in="wiAng"]').addEventListener('input', (e) => { wi.ang = Number(e.target.value); $('[data-out="wiAng"]').textContent = `${wi.ang}°`; });
  $('[data-in="wiV"]').addEventListener('input', (e) => { wi.v = Number(e.target.value); $('[data-out="wiV"]').textContent = `${wi.v} km/h`; });

  /* ---- 2. BANANA KICK ---- */
  const cBa = $('[data-cv="banana"]'), ctxBa = cBa.getContext('2d');
  const ba = { spin: 0, running: false, x: 95, y: 155, vx: 0, vy: 0, trail: [], msg: '调节旋转后点「⚽ 罚球射门！」' };
  function resetBa() { ba.running = false; ba.x = 95; ba.y = 155; ba.vx = 0; ba.vy = 0; ba.trail = []; }
  function checkBa() {
    setTask('ba1', state.tasks.baStraight, '目标 1：不加旋转直踢，看球撞上人墙');
    setTask('ba2', state.tasks.baGoal, '目标 2：加旋转绕过人墙踢进右侧球门');
    if (state.tasks.baStraight && state.tasks.baGoal && !state.done.banana) { state.done.banana = true; updateProgress(); }
  }
  $('[data-in="baSpin"]').addEventListener('input', (e) => {
    ba.spin = Number(e.target.value);
    $('[data-out="baSpin"]').textContent = ba.spin === 0 ? '0 (直球)' : (ba.spin > 0 ? `右旋 +${ba.spin}` : `左旋 ${ba.spin}`);
    resetBa();
  });
  $('[data-act="baKick"]').addEventListener('click', () => {
    resetBa();
    ba.vx = 7.4; ba.vy = -ba.spin * 0.33; ba.running = true; ba.msg = '足球高速飞行中...';
  });
  $('[data-act="baReset"]').addEventListener('click', () => { resetBa(); ba.msg = '已重置，重新调整旋转'; });

  /* ---- 3. TRAIN SAFETY LINE ---- */
  const cTr = $('[data-cv="train"]'), ctxTr = cTr.getContext('2d');
  const tr = { v: 60, tx: -260 };
  function checkTr() {
    setTask('tr1', state.tasks.trSlow, '目标 1：低速（≤ 80 km/h）观察前后气压平衡');
    setTask('tr2', state.tasks.trFast, '目标 2：车速拉到 ≥ 240 km/h 看低压吸力告警');
    if (state.tasks.trSlow && state.tasks.trFast && !state.done.train) { state.done.train = true; updateProgress(); }
  }
  $('[data-in="trV"]').addEventListener('input', (e) => {
    tr.v = Number(e.target.value); $('[data-out="trV"]').textContent = `${tr.v} km/h`;
    if (tr.v <= 80) state.tasks.trSlow = true;
    if (tr.v >= 240) state.tasks.trFast = true;
    checkTr();
  });

  function loop() {
    if (disposed) return;

    if (state.tab === 'wing') {
      wi.phase += wi.v * 0.00045;
      const stalled = wi.ang >= 18;
      if (wi.ang >= 6 && wi.ang <= 14) state.tasks.wiLift = true;
      if (wi.ang >= 20) state.tasks.wiStall = true;
      checkWi();

      ctxWi.clearRect(0, 0, cWi.width, cWi.height); ctxWi.fillStyle = '#0b1120'; ctxWi.fillRect(0, 0, cWi.width, cWi.height);
      const wx = 310, wy = 165;
      for (let i = -5; i <= 5; i++) {
        const y0 = wy + i * 24;
        ctxWi.strokeStyle = stalled && i < 0 && i > -4 ? 'rgba(248,113,113,0.72)' : 'rgba(56,189,248,0.62)';
        ctxWi.lineWidth = 2; ctxWi.beginPath();
        for (let x = 20; x <= 720; x += 12) {
          const dx = x - wx;
          let dy = Math.exp(-(dx * dx) / 9500) * (-24 - wi.ang * 1.1) * (i < 0 ? 1 : 0.45);
          if (stalled && i < 0 && i > -4 && dx > 0) dy += Math.sin(dx * 0.08 - wi.phase * 14 + i) * 16;
          const yy = y0 + dy;
          if (x === 20) ctxWi.moveTo(x, yy); else ctxWi.lineTo(x, yy);
        }
        ctxWi.stroke();
      }
      ctxWi.save(); ctxWi.translate(wx, wy); ctxWi.rotate(-wi.ang * Math.PI / 180);
      ctxWi.fillStyle = '#e2e8f0'; ctxWi.beginPath(); ctxWi.ellipse(0, 0, 74, 15, 0, 0, Math.PI * 2); ctxWi.fill(); ctxWi.restore();
      const lift = stalled ? Math.round(wi.v * 0.25) : Math.round(wi.v * (0.4 + wi.ang * 0.06));
      canvasHud(ctxWi, {
        x: 712, y: 14, align: 'right', lh: 32, bg: 'rgba(15,23,42,0.88)', stroke: '#243044',
        lines: [
          { text: stalled ? '⚠️ 失速！上翼面涡流撕裂' : `✨ 稳定升力指数：${lift}`, font: FS.hudSub, color: stalled ? '#f87171' : '#34d399' },
          { text: stalled ? '迎角过大气流剥离，升力骤降' : '上快低压 + 下慢高压 = 托举升空', font: FS.small, color: '#94a3b8' },
        ],
      });
    }

    if (state.tab === 'banana') {
      if (ba.running) {
        // Magnus lateral acceleration proportional to spin
        ba.vy += ba.spin * 0.0088;
        ba.x += ba.vx; ba.y += ba.vy;
        ba.trail.push({ x: ba.x, y: ba.y });
        // Wall at x=360, y in [115, 195]
        if (ba.x >= 352 && ba.x <= 372 && ba.y >= 112 && ba.y <= 198) {
          ba.running = false; ba.msg = '🧱 砰！被正面人墙挡下来了，试试加上旋转！';
          if (ba.spin === 0) state.tasks.baStraight = true; checkBa();
        } else if (ba.x >= 660) {
          ba.running = false;
          if (ba.y >= 102 && ba.y <= 208) { ba.msg = '⚽ 世界波破门！完美香蕉球绕过人墙！'; state.tasks.baGoal = true; checkBa(); }
          else ba.msg = '偏出球门了，微调一下旋转强度再踢！';
        } else if (ba.y < 14 || ba.y > 296) {
          ba.running = false; ba.msg = '飞出边线了，旋转调小一点试试！';
        }
      }
      ctxBa.clearRect(0, 0, cBa.width, cBa.height); ctxBa.fillStyle = '#064e3b'; ctxBa.fillRect(0, 0, cBa.width, cBa.height);
      ctxBa.strokeStyle = 'rgba(255,255,255,0.28)'; ctxBa.lineWidth = 2; ctxBa.strokeRect(20, 20, 646, 270);
      // Goal box on right
      ctxBa.strokeStyle = '#fde047'; ctxBa.lineWidth = 4; ctxBa.strokeRect(666, 102, 26, 106);
      // Human wall
      ctxBa.fillStyle = '#ef4444';
      [130, 155, 180].forEach((wy) => { ctxBa.beginPath(); ctxBa.arc(360, wy, 12, 0, Math.PI * 2); ctxBa.fill(); });
      ctxBa.textAlign = 'center';
      ctxBa.fillStyle = '#fecaca'; ctxBa.font = FS.small; ctxBa.fillText('人墙', 360, 222);
      ctxBa.textAlign = 'left';
      if (ba.trail.length > 1) {
        ctxBa.strokeStyle = '#38bdf8'; ctxBa.lineWidth = 3; ctxBa.beginPath();
        ba.trail.forEach((p, i) => (i ? ctxBa.lineTo(p.x, p.y) : ctxBa.moveTo(p.x, p.y))); ctxBa.stroke();
      }
      ctxBa.fillStyle = '#fff'; ctxBa.beginPath(); ctxBa.arc(ba.x, ba.y, 10, 0, Math.PI * 2); ctxBa.fill();
      canvasHud(ctxBa, {
        x: 24, y: 20, lh: 32, bg: 'rgba(15,23,42,0.82)',
        lines: [{ text: ba.msg, font: FS.label, color: '#fde047' }],
      });
    }

    if (state.tab === 'train') {
      if (tr.v <= 80) state.tasks.trSlow = true;
      checkTr();
      tr.tx += tr.v * 0.085;
      if (tr.tx > 820) tr.tx = -340;
      ctxTr.clearRect(0, 0, cTr.width, cTr.height); ctxTr.fillStyle = '#0b1120'; ctxTr.fillRect(0, 0, cTr.width, cTr.height);
      // Platform & yellow safety line
      ctxTr.fillStyle = '#1e293b'; ctxTr.fillRect(0, 170, 740, 140);
      ctxTr.fillStyle = '#facc15'; ctxTr.fillRect(0, 188, 740, 6);
      ctxTr.fillStyle = '#fde047'; ctxTr.font = FS.label; ctxTr.fillText('安全黄线（候车请勿越线）', 24, 220);
      // High-speed train
      ctxTr.fillStyle = '#e2e8f0'; ctxTr.beginPath(); ctxTr.roundRect(tr.tx, 76, 300, 74, [12, 34, 34, 12]); ctxTr.fill();
      ctxTr.fillStyle = '#2563eb'; ctxTr.fillRect(tr.tx + 20, 108, 250, 12);
      // Passenger standing near edge
      const pDrop = (tr.v / 300) ** 2;
      const danger = tr.v >= 220;
      ctxTr.fillStyle = danger ? '#f87171' : '#34d399';
      ctxTr.beginPath(); ctxTr.arc(360, 215, 13, 0, Math.PI * 2); ctxTr.fill();
      ctxTr.textAlign = 'right';
      ctxTr.fillStyle = '#fff'; ctxTr.font = FS.small; ctxTr.fillText('候车人', 336, 222);
      ctxTr.textAlign = 'left';
      // Push arrow from behind
      const aLen = 14 + pDrop * 44;
      ctxTr.strokeStyle = danger ? '#f87171' : '#38bdf8'; ctxTr.lineWidth = 3;
      ctxTr.beginPath(); ctxTr.moveTo(360, 275); ctxTr.lineTo(360, 275 - aLen); ctxTr.stroke();
      // Pressure HUD
      canvasHud(ctxTr, {
        x: 726, y: 162, align: 'right', lh: 32, bg: 'rgba(15,23,42,0.88)', stroke: '#243044',
        lines: [
          { text: `列车速度：${tr.v} km/h`, font: FS.hudSub, color: '#7dd3fc' },
          { text: `车侧低压降：-${(pDrop * 4.2).toFixed(2)} kPa`, font: FS.small, color: '#cbd5e1' },
          { text: danger ? '⚠️ 背后气压猛推向列车！' : '气压差较小，黄线外安全', font: FS.small, color: danger ? '#f87171' : '#34d399' },
        ],
      });
    }
    rafId = requestAnimationFrame(loop);
  }

  function renderSummary() {
    const dN = KEYS.filter((k) => state.done[k]).length;
    $('[data-sum="title"]').textContent = dN === 3 ? '🏆 风洞与流体专题通关！' : `探索进行中：已完成 ${dN} / 3 场实验`;
    const rows = [
      { k: 'wing', t: '1. 机翼风洞与失速', p: '“上快低压产生升力，但仰角过猛气流剥离立刻失速。”' },
      { k: 'banana', t: '2. 足球香蕉球', p: '“高速旋转造成两侧流速差，马格努斯力把球在空中硬推弯。”' },
      { k: 'train', t: '3. 高铁站台安全线', p: '“不是列车吸人，是车侧气压骤降后背后大气压把人推向铁轨。”' },
    ];
    $('[data-sum="list"]').innerHTML = rows.map((r) => `<div class="fl-recap"><div style="font-size:13.5px;font-weight:800">${state.done[r.k] ? '✅ ' : '🔒 '}${r.t}</div><div style="font-size:12.5px;color:var(--ink-2);margin-top:3px">${state.done[r.k] ? r.p : '完成对应实验探索后解锁'}</div></div>`).join('');
  }
  $('[data-act="resetAll"]').addEventListener('click', () => {
    KEYS.forEach((k) => { state.guesses[k] = null; state.done[k] = false; });
    state.tasks = { wiLift: false, wiStall: false, baStraight: false, baGoal: false, trSlow: false, trFast: false };
    $$('.fl-opt').forEach((b) => b.classList.remove('picked'));
    resetBa(); checkWi(); checkBa(); checkTr(); updateProgress(); renderSummary(); switchTab('wing');
  });
  $('[data-act="backSubjects"]').addEventListener('click', () => navigate('#/subjects'));

  view.innerHTML = ''; view.appendChild(root);
  checkWi(); checkBa(); checkTr(); updateProgress();
  rafId = requestAnimationFrame(loop);
  mountLabBonus(root, '.fl-tabs');
  return () => { disposed = true; cancelAnimationFrame(rafId); };
}
