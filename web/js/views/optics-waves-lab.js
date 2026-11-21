/* 光与波的魔法：激光光纤全反射 + 突破音障马赫锥 + 主动降噪波干涉（暗黑霓虹互动实验室） */

import { el } from '../ui.js';
import { navigate } from '../router.js';
import { mountLabBonus } from '../lab-bonus.js';

const LAB_CSS = `
.owlab{display:flex;flex-direction:column;gap:12px}
.owlab .ow-pill{display:inline-flex;align-items:center;gap:6px;padding:5px 11px;border-radius:999px;background:#fff;border:1px solid var(--line);font-size:12px;font-weight:700;color:var(--ink-2)}
.owlab .ow-dot{width:8px;height:8px;border-radius:50%;background:#d6c7b2;transition:background .2s}
.owlab .ow-dot.done{background:#059669}
.owlab .ow-tabs{display:flex;flex-wrap:wrap;gap:7px}
.owlab .ow-tab{appearance:none;border:1px solid var(--line);background:#fff;color:var(--ink-2);padding:7px 12px;border-radius:999px;font-size:12px;font-weight:700;cursor:pointer;display:inline-flex;align-items:center;gap:5px}
.owlab .ow-tab.active{background:#0f172a;border-color:#38bdf8;color:#7dd3fc}
.owlab .ow-tab .chk{font-size:10.5px;padding:1px 5px;border-radius:999px;background:#ecfdf5;color:#059669}
.owlab .ow-tab.active .chk{background:rgba(56,189,248,.22);color:#7dd3fc}
.owlab .ow-predict{background:#faf6ef;border:1px dashed #dfcfb7;border-radius:12px;padding:11px 12px;margin:10px 0 12px}
.owlab .ow-predict-q{font-size:13px;font-weight:800;margin:0 0 8px;color:var(--ink)}
.owlab .ow-opts{display:flex;flex-wrap:wrap;gap:7px}
.owlab .ow-opt{appearance:none;background:#fff;border:1px solid #dfd2be;color:var(--ink-2);padding:6px 11px;border-radius:9px;font-size:12px;font-weight:700;cursor:pointer}
.owlab .ow-opt.picked{background:#eff6ff;border-color:#2563eb;color:#2563eb}
.owlab .ow-stage{border-radius:14px;overflow:hidden;border:1px solid #1e293b;background:#0b1120;margin-bottom:12px;box-shadow:0 8px 24px rgba(15,23,42,.18)}
.owlab .ow-stage canvas{display:block;width:100%;height:auto;touch-action:none}
.owlab .ow-ctrl{display:flex;flex-wrap:wrap;align-items:center;gap:10px 18px;padding:10px 12px;background:#faf7f2;border-radius:12px;border:1px solid var(--line);margin-bottom:10px}
.owlab .ow-range{display:flex;align-items:center;gap:8px;flex:1 1 240px;min-width:220px}
.owlab .ow-range label{font-size:12px;font-weight:700;color:var(--ink-2);white-space:nowrap}
.owlab .ow-range input{flex:1;min-width:80px;cursor:pointer}
.owlab .ow-val{font-size:12px;font-weight:800;color:#2563eb;min-width:64px;text-align:right;white-space:nowrap;font-variant-numeric:tabular-nums}
.owlab .ow-tasks{display:flex;flex-wrap:wrap;gap:7px;margin-bottom:4px}
.owlab .ow-task{font-size:11.5px;font-weight:700;padding:4px 10px;border-radius:9px;background:#f5f0e7;color:var(--ink-3)}
.owlab .ow-task.done{background:#ecfdf5;color:#059669;border:1px solid #a7f3d0}
.owlab .ow-insight{margin-top:12px;padding:14px;border-radius:13px;background:linear-gradient(135deg,#f0fdf4 0%,#eff6ff 100%);border:1px solid #bbf7d0}
.owlab .ow-insight-q{font-size:15px;font-weight:900;color:var(--ink);margin:4px 0 6px;line-height:1.5}
.owlab .ow-insight-b{font-size:12.5px;color:var(--ink-2);margin:0 0 10px;line-height:1.65}
.owlab .ow-recap{border:1px solid var(--line);border-radius:12px;padding:11px 13px;background:#fffdf9;margin-bottom:8px}
.owlab .hidden{display:none !important}
`;

export async function renderOpticsWavesLab(view) {
  const KEYS = ['fiber', 'sonic', 'anc'];
  const state = {
    tab: 'fiber',
    guesses: { fiber: null, sonic: null, anc: null },
    correct: { fiber: 'total', sonic: 'cone', anc: 'cancel' },
    done: { fiber: false, sonic: false, anc: false },
    tasks: { fibLeak: false, fibTotal: false, sonSub: false, sonSuper: false, ancAdd: false, ancCancel: false },
  };
  let disposed = false;
  let rafId = 0;

  const root = el('div', { class: 'owlab' });
  const styleTag = document.createElement('style');
  styleTag.textContent = LAB_CSS;
  root.appendChild(styleTag);

  const dots = KEYS.map(() => el('span', { class: 'ow-dot' }));
  const progTxt = el('span', { text: '已探索 0 / 3' });
  root.appendChild(el('div', { class: 'topbar' }, [
    el('button', { class: 'back', text: '‹', onclick: () => { if (history.length > 1) history.back(); else navigate('#/subjects'); } }),
    el('div', { style: 'flex:1;min-width:0' }, [
      el('h1', { text: '光与波的魔法剧场' }),
      el('div', { class: 'sub', text: '激光光纤 · 超音速音爆 · 主动降噪干涉' }),
    ]),
    el('div', { class: 'ow-pill' }, [...dots, progTxt]),
  ]));

  const body = el('div', { html: `
  <nav class="ow-tabs">
    <button type="button" class="ow-tab active" data-tab="fiber">🔦 1. 激光光纤全反射 <span class="chk hidden" data-chk="fiber">✓</span></button>
    <button type="button" class="ow-tab" data-tab="sonic">✈️ 2. 音爆马赫锥 <span class="chk hidden" data-chk="sonic">✓</span></button>
    <button type="button" class="ow-tab" data-tab="anc">🎧 3. 主动降噪干涉 <span class="chk hidden" data-chk="anc">✓</span></button>
    <button type="button" class="ow-tab" data-tab="summary">🏆 专题总结</button>
  </nav>

  <!-- 1: FIBER OPTICS -->
  <section class="panel" data-pane="fiber">
    <div style="font-size:17px;font-weight:800;margin-bottom:4px">激光光纤：透明玻璃如何把光死死关在管子里？</div>
    <div style="font-size:12.5px;color:var(--ink-2)">拖动激光入射角 θ：低于临界角时激光会从管壁漏出去；越过临界角瞬间触发全反射，一路飙到终点！</div>
    <div class="ow-predict">
      <div class="ow-predict-q">① 先猜一猜：把玻璃光纤弯成弧形，激光为什么不会从透明的玻璃外壁直接射出去？</div>
      <div class="ow-opts" data-lab="fiber">
        <button type="button" class="ow-opt" data-val="mirror">光纤外面贴了很厚的金属镜子</button>
        <button type="button" class="ow-opt" data-val="total">光斜着撞向管壁超过临界角，玻璃界面自动发生 100% 全反射</button>
      </div>
    </div>
    <div class="ow-stage"><canvas data-cv="fiber" width="740" height="310"></canvas></div>
    <div class="ow-ctrl">
      <div class="ow-range"><label>管壁入射角 θ</label><input data-in="fibAng" type="range" min="20" max="75" value="32" step="1"><span class="ow-val" data-out="fibAng">32°</span></div>
      <div class="ow-range"><label>玻璃折射率 n</label><input data-in="fibN" type="range" min="1.25" max="1.80" value="1.50" step="0.05"><span class="ow-val" data-out="fibN">1.50</span></div>
    </div>
    <div class="ow-tasks">
      <span class="ow-task" data-task="fib1">○ 目标 1：在小于临界角时观察激光漏出管壁</span>
      <span class="ow-task" data-task="fib2">○ 目标 2：把入射角调过临界角，点亮右侧全反射接收器</span>
    </div>
    <div class="ow-insight hidden" data-insight="fiber">
      <div style="font-size:11px;font-weight:800;color:#059669">✦ 顿悟时刻已解锁</div>
      <div class="ow-insight-q">“角度够斜时，透明玻璃也能变成关住光线的镜子——你刷的每一条短视频，都是光这么撞出来的。”</div>
      <p class="ow-insight-b">光从高折射率玻璃射向空气时，只要入射角 <code>θ ≥ arcsin(1/n)</code>，折射光彻底消失、能量几乎 100% 反射回管内。跨洋海底光缆每秒传输的 TB 级数据全靠全反射。</p>
      <div class="row-between" style="gap:8px;flex-wrap:wrap"><span style="font-size:11.5px;font-weight:700;color:#2563eb" data-guess="fiber"></span><button type="button" class="btn sm" data-goto="sonic">下一场：音爆马赫锥 →</button></div>
    </div>
  </section>

  <!-- 2: SONIC BOOM -->
  <section class="panel hidden" data-pane="sonic">
    <div style="font-size:17px;font-weight:800;margin-bottom:4px">突破音障：飞得比自己的声音还快，天上会发生什么？</div>
    <div style="font-size:12.5px;color:var(--ink-2)">拖动战机马赫数从 0.5 Mach 拉到 1.8 Mach，亲眼看声波圆环如何叠成发光激波墙并拉出马赫锥！</div>
    <div class="ow-predict">
      <div class="ow-predict-q">① 先猜一猜：超音速战机从你头顶飞过时，你是先看到飞机飞过去，还是先听到轰鸣音爆？</div>
      <div class="ow-opts" data-lab="sonic">
        <button type="button" class="ow-opt" data-val="sound">先听到轰鸣，再看到飞机</button>
        <button type="button" class="ow-opt" data-val="cone">飞机已经飞过去了，激波锥扫到耳朵时才突然“轰”一声炸响</button>
      </div>
    </div>
    <div class="ow-stage"><canvas data-cv="sonic" width="740" height="310"></canvas></div>
    <div class="ow-ctrl">
      <div class="ow-range"><label>战机速度（马赫）</label><input data-in="sonM" type="range" min="0.4" max="2.0" value="0.6" step="0.1"><span class="ow-val" data-out="sonM">0.6 Mach</span></div>
      <button type="button" class="btn sm ghost" data-act="sonReset">重新起飞</button>
    </div>
    <div class="ow-tasks">
      <span class="ow-task" data-task="son1">○ 目标 1：在亚音速（&lt; 1.0M）观察前密后疏的多普勒效应</span>
      <span class="ow-task" data-task="son2">○ 目标 2：把速度拉过 1.2M，亲眼拉出超音速马赫锥</span>
    </div>
    <div class="ow-insight hidden" data-insight="sonic">
      <div style="font-size:11px;font-weight:800;color:#059669">✦ 顿悟时刻已解锁</div>
      <div class="ow-insight-q">“飞得比自己的声音还快时，所有声波挤在同一瞬间炸开——那就是音爆。”</div>
      <p class="ow-insight-b">亚音速时前方波纹变密（音调变高，多普勒效应）；速度超过音速后，所有声波包络成一个圆锥面（马赫锥，<code>sin α = 1/M</code>），锥面扫过地面瞬间压强骤变，爆出雷鸣般音爆。</p>
      <div class="row-between" style="gap:8px;flex-wrap:wrap"><span style="font-size:11.5px;font-weight:700;color:#2563eb" data-guess="sonic"></span><button type="button" class="btn sm" data-goto="anc">下一场：主动降噪干涉 →</button></div>
    </div>
  </section>

  <!-- 3: ACTIVE NOISE CANCELLATION -->
  <section class="panel hidden" data-pane="anc">
    <div style="font-size:17px;font-weight:800;margin-bottom:4px">主动降噪耳机：为什么“声音 + 声音”居然能变成静音？</div>
    <div style="font-size:12.5px;color:var(--ink-2)">红色是外界地铁噪音，青色是耳机发出的反相声波，下方金色是传进你耳朵的合成声音。拖动相位差试试！</div>
    <div class="ow-predict">
      <div class="ow-predict-q">① 先猜一猜：主动降噪耳机（ANC）消除外界低频轰鸣的核心秘密是什么？</div>
      <div class="ow-opts" data-lab="anc">
        <button type="button" class="ow-opt" data-val="block">靠超级厚的海绵把声音全部挡在外面</button>
        <button type="button" class="ow-opt" data-val="cancel">麦克风先听噪音，再发射一束相位正好相反（差 180°）的声波把它抵消</button>
      </div>
    </div>
    <div class="ow-stage"><canvas data-cv="anc" width="740" height="310"></canvas></div>
    <div class="ow-ctrl">
      <div class="ow-range"><label>反相波相位差 Δφ</label><input data-in="ancPhi" type="range" min="0" max="180" value="0" step="10"><span class="ow-val" data-out="ancPhi">0° (同相)</span></div>
      <button type="button" class="btn sm" style="background:#059669" data-act="ancSnap">一键 180° 极致降噪</button>
    </div>
    <div class="ow-tasks">
      <span class="ow-task" data-task="anc1">○ 目标 1：观察相位差 0° 时两列波叠加音量翻倍（相长干涉）</span>
      <span class="ow-task" data-task="anc2">○ 目标 2：把相位差调到 180°，亲眼把合成波压成一条静音直线</span>
    </div>
    <div class="ow-insight hidden" data-insight="anc">
      <div style="font-size:11px;font-weight:800;color:#059669">✦ 顿悟时刻已解锁</div>
      <div class="ow-insight-q">“声音加声音可以等于静音——降噪耳机不是堵住噪音，而是派出一束‘反派声波’同归于尽。”</div>
      <p class="ow-insight-b">两列同频声波相位差为 <code>0°</code> 时波峰叠波峰（振幅翻倍，相长干涉）；相位差为 <code>180°</code> 时波峰正好撞上波谷，合成振幅归零（相消干涉）。</p>
      <div class="row-between" style="gap:8px;flex-wrap:wrap"><span style="font-size:11.5px;font-weight:700;color:#2563eb" data-guess="anc"></span><button type="button" class="btn sm" data-goto="summary">查看专题总结 🏆</button></div>
    </div>
  </section>

  <!-- SUMMARY -->
  <section class="panel hidden" data-pane="summary">
    <div style="text-align:center;margin-bottom:12px">
      <div style="font-size:18px;font-weight:900" data-sum="title">探索进行中：已完成 0 / 3 场光与波实验</div>
      <div style="font-size:12.5px;color:var(--ink-2);margin-top:4px">从光纤里的全反射、天上的音爆激波到耳边的主动降噪——波动规律藏在现代生活的每个角落。</div>
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
    $$('.ow-tab').forEach((b) => b.classList.toggle('active', b.dataset.tab === name));
    $$('[data-pane]').forEach((p) => p.classList.toggle('hidden', p.dataset.pane !== name));
    if (name === 'summary') renderSummary();
    if (name === 'fiber') drawFiber();
  }
  $$('.ow-tab').forEach((b) => b.addEventListener('click', () => switchTab(b.dataset.tab)));
  $$('[data-goto]').forEach((b) => b.addEventListener('click', () => switchTab(b.dataset.goto)));
  $$('.ow-opts').forEach((w) => {
    const lab = w.dataset.lab;
    w.querySelectorAll('.ow-opt').forEach((btn) => btn.addEventListener('click', () => {
      state.guesses[lab] = btn.dataset.val;
      w.querySelectorAll('.ow-opt').forEach((x) => x.classList.toggle('picked', x === btn));
      updateGuess(lab);
    }));
  });

  /* ---- 1. FIBER OPTICS ---- */
  const cFib = $('[data-cv="fiber"]'), ctxFi = cFib.getContext('2d');
  const fib = { ang: 32, n: 1.50 };
  function checkFib() {
    setTask('fib1', state.tasks.fibLeak, '目标 1：小于临界角观察激光漏出管壁');
    setTask('fib2', state.tasks.fibTotal, '目标 2：超过临界角点亮右侧全反射接收器');
    if (state.tasks.fibLeak && state.tasks.fibTotal && !state.done.fiber) { state.done.fiber = true; updateProgress(); }
  }
  function drawFiber() {
    const W = cFib.width, H = cFib.height;
    ctxFi.clearRect(0, 0, W, H); ctxFi.fillStyle = '#0b1120'; ctxFi.fillRect(0, 0, W, H);
    const topY = 108, botY = 208, leftX = 72, rightX = 650;
    const crit = Math.asin(1 / fib.n) * 180 / Math.PI;
    const isTotal = fib.ang >= crit;
    if (isTotal) state.tasks.fibTotal = true; else state.tasks.fibLeak = true;
    checkFib();

    // Glass fiber tube
    ctxFi.fillStyle = 'rgba(56,189,248,0.12)'; ctxFi.fillRect(leftX, topY, rightX - leftX, botY - topY);
    ctxFi.strokeStyle = '#38bdf8'; ctxFi.lineWidth = 2;
    ctxFi.beginPath(); ctxFi.moveTo(leftX, topY); ctxFi.lineTo(rightX, topY); ctxFi.moveTo(leftX, botY); ctxFi.lineTo(rightX, botY); ctxFi.stroke();

    // Trace laser ray bouncing inside fiber
    const rad = fib.ang * Math.PI / 180;
    const stepX = (botY - topY) * Math.tan(rad);
    let x = leftX, y = (topY + botY) / 2, dir = -1;
    let firstX = x + ((botY - topY) / 2) * Math.tan(rad);
    ctxFi.strokeStyle = '#38bdf8'; ctxFi.lineWidth = 3; ctxFi.shadowColor = '#38bdf8'; ctxFi.shadowBlur = 12;
    ctxFi.beginPath(); ctxFi.moveTo(x, y);
    if (!isTotal) {
      // Hits top wall and leaks out!
      const hitX = Math.min(rightX, firstX);
      ctxFi.lineTo(hitX, topY); ctxFi.stroke(); ctxFi.shadowBlur = 0;
      const refrRad = Math.asin(Math.min(0.99, fib.n * Math.sin(rad)));
      ctxFi.strokeStyle = 'rgba(248,113,113,0.85)'; ctxFi.lineWidth = 2.5;
      ctxFi.beginPath(); ctxFi.moveTo(hitX, topY); ctxFi.lineTo(hitX + Math.sin(refrRad) * 95, topY - Math.cos(refrRad) * 95); ctxFi.stroke();
      // 提示写在管壁下方，避免被左上角 HUD 盖住
      ctxFi.fillStyle = '#f87171'; ctxFi.font = '800 13px sans-serif';
      ctxFi.fillText('⚠️ 光从管壁漏出去了！', Math.min(hitX + 6, rightX - 150), botY + 34);
    } else {
      x = firstX; y = topY; ctxFi.lineTo(x, y); dir = 1;
      let guard = 0;
      while (x < rightX && guard++ < 25) {
        const nextX = x + stepX;
        const nextY = dir === 1 ? botY : topY;
        if (nextX >= rightX) {
          const frac = (rightX - x) / Math.max(1, stepX);
          ctxFi.lineTo(rightX, y + (nextY - y) * frac);
          break;
        }
        ctxFi.lineTo(nextX, nextY); x = nextX; y = nextY; dir = -dir;
      }
      ctxFi.stroke(); ctxFi.shadowBlur = 0;
    }

    // Receiver lamp on right
    ctxFi.fillStyle = isTotal ? '#34d399' : '#334155';
    ctxFi.shadowColor = isTotal ? '#34d399' : 'transparent'; ctxFi.shadowBlur = isTotal ? 16 : 0;
    ctxFi.beginPath(); ctxFi.roundRect(rightX + 4, topY + 12, 22, botY - topY - 24, 6); ctxFi.fill(); ctxFi.shadowBlur = 0;

    // HUD
    ctxFi.fillStyle = 'rgba(15,23,42,0.88)'; ctxFi.strokeStyle = '#243044';
    ctxFi.beginPath(); ctxFi.roundRect(18, 16, 330, 68, 12); ctxFi.fill(); ctxFi.stroke();
    ctxFi.fillStyle = '#7dd3fc'; ctxFi.font = '800 12.5px sans-serif';
    ctxFi.fillText(`入射角 θ = ${fib.ang}° · 临界角 θc = ${crit.toFixed(1)}°`, 32, 40);
    ctxFi.fillStyle = isTotal ? '#34d399' : '#f87171';
    ctxFi.fillText(isTotal ? '✨ 全反射达成！100% 激光信号送达接收器' : '⚠️ 未达临界角，激光折射漏出光纤', 32, 64);
  }
  $('[data-in="fibAng"]').addEventListener('input', (e) => { fib.ang = Number(e.target.value); $('[data-out="fibAng"]').textContent = `${fib.ang}°`; drawFiber(); });
  $('[data-in="fibN"]').addEventListener('input', (e) => { fib.n = Number(e.target.value); $('[data-out="fibN"]').textContent = fib.n.toFixed(2); drawFiber(); });

  /* ---- 2. SONIC BOOM ---- */
  const cSon = $('[data-cv="sonic"]'), ctxSo = cSon.getContext('2d');
  const son = { M: 0.6, x: 120, rings: [], tick: 0 };
  function checkSon() {
    setTask('son1', state.tasks.sonSub, '目标 1：亚音速（< 1.0M）观察多普勒波纹');
    setTask('son2', state.tasks.sonSuper, '目标 2：速度拉过 1.2M 拉出超音速马赫锥');
    if (state.tasks.sonSub && state.tasks.sonSuper && !state.done.sonic) { state.done.sonic = true; updateProgress(); }
  }
  $('[data-in="sonM"]').addEventListener('input', (e) => {
    son.M = Number(e.target.value); $('[data-out="sonM"]').textContent = `${son.M.toFixed(1)} Mach`;
    if (son.M < 1.0) state.tasks.sonSub = true;
    if (son.M >= 1.2) state.tasks.sonSuper = true;
    checkSon();
  });
  $('[data-act="sonReset"]').addEventListener('click', () => { son.x = 100; son.rings = []; });

  /* ---- 3. ANC INTERFERENCE ---- */
  const cAnc = $('[data-cv="anc"]'), ctxAn = cAnc.getContext('2d');
  const anc = { phi: 0, phase: 0 };
  function checkAnc() {
    setTask('anc1', state.tasks.ancAdd, '目标 1：观察 0° 同相叠加音量翻倍');
    setTask('anc2', state.tasks.ancCancel, '目标 2：调到 180° 把合成波压成静音直线');
    if (state.tasks.ancAdd && state.tasks.ancCancel && !state.done.anc) { state.done.anc = true; updateProgress(); }
  }
  $('[data-in="ancPhi"]').addEventListener('input', (e) => {
    anc.phi = Number(e.target.value);
    $('[data-out="ancPhi"]').textContent = anc.phi === 0 ? '0° (同相)' : anc.phi === 180 ? '180° (反相)' : `${anc.phi}°`;
    if (anc.phi === 0) state.tasks.ancAdd = true;
    if (anc.phi === 180) state.tasks.ancCancel = true;
    checkAnc();
  });
  $('[data-act="ancSnap"]').addEventListener('click', () => {
    anc.phi = 180; $('[data-in="ancPhi"]').value = '180'; $('[data-out="ancPhi"]').textContent = '180° (反相)';
    state.tasks.ancCancel = true; checkAnc();
  });

  /* Unified loop for sonic + anc */
  function loop() {
    if (disposed) return;
    if (state.tab === 'sonic') {
      const cSound = 1.65;
      son.x += cSound * son.M;
      if (son.x > 700) { son.x = 80; son.rings = []; }
      son.tick++;
      if (son.tick % 9 === 0) son.rings.push({ x: son.x, y: 165, r: 2 });
      if (son.M < 1.0) state.tasks.sonSub = true;
      if (son.M >= 1.2) state.tasks.sonSuper = true;
      checkSon();

      ctxSo.clearRect(0, 0, cSon.width, cSon.height);
      ctxSo.fillStyle = '#0b1120'; ctxSo.fillRect(0, 0, cSon.width, cSon.height);
      son.rings.forEach((rg) => {
        rg.r += cSound;
        const a = Math.max(0, 1 - rg.r / 220);
        ctxSo.strokeStyle = `rgba(56,189,248,${a * 0.7})`; ctxSo.lineWidth = 1.6;
        ctxSo.beginPath(); ctxSo.arc(rg.x, rg.y, rg.r, 0, Math.PI * 2); ctxSo.stroke();
      });
      son.rings = son.rings.filter((rg) => rg.r < 220);

      if (son.M > 1.02) {
        const halfA = Math.asin(1 / son.M);
        ctxSo.strokeStyle = '#fbbf24'; ctxSo.lineWidth = 2.4; ctxSo.shadowColor = '#fbbf24'; ctxSo.shadowBlur = 10;
        ctxSo.beginPath();
        ctxSo.moveTo(son.x, 165); ctxSo.lineTo(son.x - 240 * Math.cos(halfA), 165 - 240 * Math.sin(halfA));
        ctxSo.moveTo(son.x, 165); ctxSo.lineTo(son.x - 240 * Math.cos(halfA), 165 + 240 * Math.sin(halfA));
        ctxSo.stroke(); ctxSo.shadowBlur = 0;
      }
      // Jet triangle
      ctxSo.fillStyle = '#f8fafc'; ctxSo.beginPath();
      ctxSo.moveTo(son.x + 14, 165); ctxSo.lineTo(son.x - 10, 156); ctxSo.lineTo(son.x - 10, 174); ctxSo.closePath(); ctxSo.fill();

      ctxSo.fillStyle = 'rgba(15,23,42,0.85)'; ctxSo.strokeStyle = '#243044';
      ctxSo.beginPath(); ctxSo.roundRect(18, 16, 290, 62, 12); ctxSo.fill(); ctxSo.stroke();
      ctxSo.fillStyle = '#7dd3fc'; ctxSo.font = '800 12.5px sans-serif'; ctxSo.fillText(`当前速度：${son.M.toFixed(1)} Mach`, 32, 38);
      ctxSo.fillStyle = son.M >= 1.0 ? '#fbbf24' : '#34d399';
      ctxSo.fillText(son.M > 1.0 ? `💥 超音速！马赫锥半角 ≈ ${(Math.asin(1 / son.M) * 180 / Math.PI).toFixed(0)}°` : (son.M === 1.0 ? '⚡ 音障临界！声波堆叠成墙' : '亚音速：前方波纹压缩，后方拉宽'), 32, 60);
    }
    if (state.tab === 'anc') {
      anc.phase += 0.08;
      if (anc.phi === 0) state.tasks.ancAdd = true;
      checkAnc();
      const W = cAnc.width, H = cAnc.height;
      ctxAn.clearRect(0, 0, W, H); ctxAn.fillStyle = '#0b1120'; ctxAn.fillRect(0, 0, W, H);
      const phiRad = anc.phi * Math.PI / 180;
      const drawW = (y0, fn, color, label) => {
        ctxAn.strokeStyle = 'rgba(148,163,184,0.18)'; ctxAn.lineWidth = 1;
        ctxAn.beginPath(); ctxAn.moveTo(30, y0); ctxAn.lineTo(710, y0); ctxAn.stroke();
        ctxAn.strokeStyle = color; ctxAn.lineWidth = 2.6; ctxAn.beginPath();
        for (let x = 30; x <= 710; x += 4) {
          const y = y0 - fn((x - 30) * 0.032 - anc.phase) * 26;
          if (x === 30) ctxAn.moveTo(x, y); else ctxAn.lineTo(x, y);
        }
        ctxAn.stroke();
        ctxAn.fillStyle = color; ctxAn.font = '700 12px sans-serif'; ctxAn.fillText(label, 34, y0 - 32);
      };
      drawW(68, (t) => Math.sin(t), '#f87171', '① 外界噪音波');
      drawW(154, (t) => Math.sin(t + phiRad), '#38bdf8', `② 耳机反向波（相位差 ${anc.phi}°）`);
      const ampPct = Math.round(Math.abs(Math.cos(phiRad / 2)) * 100);
      drawW(246, (t) => 0.5 * (Math.sin(t) + Math.sin(t + phiRad)) * 1.4, '#fbbf24', `③ 传进耳朵的合成声波（剩余音量：${ampPct}%${ampPct === 0 ? ' 🔇 彻底静音！' : ''}）`);
    }
    rafId = requestAnimationFrame(loop);
  }

  function renderSummary() {
    const dN = KEYS.filter((k) => state.done[k]).length;
    $('[data-sum="title"]').textContent = dN === 3 ? '🏆 光与波专题通关！全反射、激波与干涉全解锁' : `探索进行中：已完成 ${dN} / 3 场实验`;
    const rows = [
      { k: 'fiber', t: '1. 激光光纤全反射', p: '“角度够斜时，透明玻璃也能变成关住光线的镜子。”' },
      { k: 'sonic', t: '2. 超音速音爆马赫锥', p: '“飞得比自己的声音还快时，所有声波挤在同一瞬间炸开。”' },
      { k: 'anc', t: '3. 主动降噪干涉', p: '“声音加声音可以等于静音——反相 180° 波峰撞波谷互相抵消。”' },
    ];
    $('[data-sum="list"]').innerHTML = rows.map((r) => `<div class="ow-recap"><div style="font-size:13.5px;font-weight:800">${state.done[r.k] ? '✅ ' : '🔒 '}${r.t}</div><div style="font-size:12.5px;color:var(--ink-2);margin-top:3px">${state.done[r.k] ? r.p : '完成对应实验探索后解锁'}</div></div>`).join('');
  }
  $('[data-act="resetAll"]').addEventListener('click', () => {
    KEYS.forEach((k) => { state.guesses[k] = null; state.done[k] = false; });
    state.tasks = { fibLeak: false, fibTotal: false, sonSub: false, sonSuper: false, ancAdd: false, ancCancel: false };
    $$('.ow-opt').forEach((b) => b.classList.remove('picked'));
    checkFib(); checkSon(); checkAnc(); updateProgress(); renderSummary(); switchTab('fiber');
  });
  $('[data-act="backSubjects"]').addEventListener('click', () => navigate('#/subjects'));

  view.innerHTML = '';
  view.appendChild(root);
  checkFib(); checkSon(); checkAnc(); updateProgress(); drawFiber();
  rafId = requestAnimationFrame(loop);
  mountLabBonus(root, '.ow-tabs');
  return () => { disposed = true; cancelAnimationFrame(rafId); };
}
