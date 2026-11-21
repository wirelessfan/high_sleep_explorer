/* 数学直觉实验室：函数图像变换 + 区间值域单位圆扫描 + 二倍角/辅助角合成 + 诱导公式旋转（针对错题本专项突破） */

import { el } from '../ui.js';
import { navigate } from '../router.js';
import { FS, canvasHud } from '../lab-canvas.js';
import { mountLabBonus } from '../lab-bonus.js';

const LAB_CSS = `
.mtlab{display:flex;flex-direction:column;gap:12px}
.mtlab .mt-pill{display:inline-flex;align-items:center;gap:6px;padding:5px 11px;border-radius:999px;background:#fff;border:1px solid var(--line);font-size:12px;font-weight:700;color:var(--ink-2)}
.mtlab .mt-dot{width:8px;height:8px;border-radius:50%;background:#d6c7b2;transition:background .2s}
.mtlab .mt-dot.done{background:#059669}
.mtlab .mt-tabs{display:flex;flex-wrap:wrap;gap:7px}
.mtlab .mt-tab{appearance:none;border:1px solid var(--line);background:#fff;color:var(--ink-2);padding:7px 12px;border-radius:999px;font-size:12px;font-weight:700;cursor:pointer;display:inline-flex;align-items:center;gap:5px}
.mtlab .mt-tab.active{background:#0f172a;border-color:#f59e0b;color:#fcd34d}
.mtlab .mt-tab .chk{font-size:10.5px;padding:1px 5px;border-radius:999px;background:#ecfdf5;color:#059669}
.mtlab .mt-tab.active .chk{background:rgba(245,158,11,.24);color:#fcd34d}
.mtlab .mt-predict{background:#faf6ef;border:1px dashed #dfcfb7;border-radius:12px;padding:11px 12px;margin:10px 0 12px}
.mtlab .mt-predict-q{font-size:13px;font-weight:800;margin:0 0 8px;color:var(--ink)}
.mtlab .mt-opts{display:flex;flex-wrap:wrap;gap:7px}
.mtlab .mt-opt{appearance:none;background:#fff;border:1px solid #dfd2be;color:var(--ink-2);padding:6px 11px;border-radius:9px;font-size:12px;font-weight:700;cursor:pointer}
.mtlab .mt-opt.picked{background:#eff6ff;border-color:#2563eb;color:#2563eb}
.mtlab .mt-stage{border-radius:14px;overflow:hidden;border:1px solid #1e293b;background:#0b1120;margin-bottom:12px;box-shadow:0 8px 24px rgba(15,23,42,.18)}
.mtlab .mt-stage canvas{display:block;width:100%;height:auto;touch-action:none}
.mtlab .mt-ctrl{display:flex;flex-wrap:wrap;align-items:center;gap:10px 18px;padding:10px 12px;background:#faf7f2;border-radius:12px;border:1px solid var(--line);margin-bottom:10px}
.mtlab .mt-range{display:flex;align-items:center;gap:8px;flex:1 1 240px;min-width:210px}
.mtlab .mt-range label{font-size:12px;font-weight:700;color:var(--ink-2);white-space:nowrap}
.mtlab .mt-range input{flex:1;min-width:80px;cursor:pointer}
.mtlab .mt-val{font-size:12px;font-weight:800;color:#2563eb;min-width:72px;text-align:right;white-space:nowrap;font-variant-numeric:tabular-nums}
.mtlab .mt-tasks{display:flex;flex-wrap:wrap;gap:7px;margin-bottom:4px}
.mtlab .mt-task{font-size:11.5px;font-weight:700;padding:4px 10px;border-radius:9px;background:#f5f0e7;color:var(--ink-3)}
.mtlab .mt-task.done{background:#ecfdf5;color:#059669;border:1px solid #a7f3d0}
.mtlab .mt-insight{margin-top:12px;padding:14px;border-radius:13px;background:linear-gradient(135deg,#f0fdf4 0%,#eff6ff 100%);border:1px solid #bbf7d0}
.mtlab .mt-insight-q{font-size:15px;font-weight:900;color:var(--ink);margin:4px 0 6px;line-height:1.5}
.mtlab .mt-insight-b{font-size:12.5px;color:var(--ink-2);margin:0 0 10px;line-height:1.65}
.mtlab .mt-recap{border:1px solid var(--line);border-radius:12px;padding:11px 13px;background:#fffdf9;margin-bottom:8px}
.mtlab .hidden{display:none !important}
`;

export async function renderMathTrigLab(view) {
  const KEYS = ['shift', 'range', 'combine', 'induce'];
  const state = {
    tab: 'shift',
    guesses: { shift: null, range: null, combine: null, induce: null },
    correct: { shift: 'xonly', range: 'peak', combine: 'minus', induce: 'negsin' },
    done: { shift: false, range: false, combine: false, induce: false },
    tasks: {
      shShift: false, shWrong: false,
      rgEnd: false, rgPeak: false,
      cbPreset: new Set(),
      inModes: new Set(),
    },
  };

  const root = el('div', { class: 'mtlab' });
  const st = document.createElement('style'); st.textContent = LAB_CSS; root.appendChild(st);
  const dots = KEYS.map(() => el('span', { class: 'mt-dot' }));
  const progTxt = el('span', { text: '已突破 0 / 4' });
  root.appendChild(el('div', { class: 'topbar' }, [
    el('button', { class: 'back', text: '‹', onclick: () => { if (history.length > 1) history.back(); else navigate('#/subjects'); } }),
    el('div', { style: 'flex:1;min-width:0' }, [
      el('h1', { text: '函数图像、值域与三角推导直觉馆' }),
      el('div', { class: 'sub', text: '针对错题本高频痛点 · 4 场互动可视化突破' }),
    ]),
    el('div', { class: 'mt-pill' }, [...dots, progTxt]),
  ]));

  const body = el('div', { html: `
  <nav class="mt-tabs">
    <button type="button" class="mt-tab active" data-tab="shift">📈 1. 图像平移与穿轴 <span class="chk hidden" data-chk="shift">✓</span></button>
    <button type="button" class="mt-tab" data-tab="range">🎯 2. 区间值域扫描仪 <span class="chk hidden" data-chk="range">✓</span></button>
    <button type="button" class="mt-tab" data-tab="combine">🌊 3. 降幂与辅助角 <span class="chk hidden" data-chk="combine">✓</span></button>
    <button type="button" class="mt-tab" data-tab="induce">🧭 4. 诱导公式旋转 <span class="chk hidden" data-chk="induce">✓</span></button>
    <button type="button" class="mt-tab" data-tab="summary">🏆 错题突破总结</button>
  </nav>

  <!-- 1: SHIFT & ZERO CROSSING -->
  <section class="panel" data-pane="shift">
    <div style="font-size:17px;font-weight:800;margin-bottom:4px">图像平移与穿轴方向：为什么“左加右减”只能加在 x 上？</div>
    <div style="font-size:12.5px;color:var(--ink-2)">拖动左移距离 d，对比绿色正确图像 f(x+d) 与红色常见错解，并观察零点处的 ↓ 向下穿轴 / ↑ 向上穿轴标记！</div>
    <div class="mt-predict">
      <div class="mt-predict-q">① 先猜一猜：把 y = 2sin(2x + π/3) 向左平移 π/4 个单位，得到的解析式是？</div>
      <div class="mt-opts" data-lab="shift">
        <button type="button" class="mt-opt" data-val="direct">y = 2sin(2x + π/3 + π/4)</button>
        <button type="button" class="mt-opt" data-val="xonly">y = 2sin(2(x + π/4) + π/3) = 2sin(2x + 5π/6)</button>
      </div>
    </div>
    <div class="mt-stage"><canvas data-cv="shift" width="740" height="310"></canvas></div>
    <div class="mt-ctrl">
      <div class="mt-range"><label>角频率 ω</label><input data-in="shW" type="range" min="1" max="3" value="2" step="0.5"><span class="mt-val" data-out="shW">ω = 2.0</span></div>
      <div class="mt-range"><label>向左平移 d</label><input data-in="shD" type="range" min="0" max="12" value="0" step="1"><span class="mt-val" data-out="shD">0</span></div>
      <button type="button" class="btn sm ghost" data-act="shWrong">显示常见错解对比</button>
    </div>
    <div class="mt-tasks">
      <span class="mt-task" data-task="sh1">○ 目标 1：拖动平移量 d（如 π/4），看周期不变、相位实际增 ω·d</span>
      <span class="mt-task" data-task="sh2">○ 目标 2：点击「显示常见错解对比」，亲眼看清两条曲线错开多少</span>
    </div>
    <div class="mt-insight hidden" data-insight="shift">
      <div style="font-size:11px;font-weight:800;color:#059669">✦ 直觉已建立</div>
      <div class="mt-insight-q">“左加右减永远只替换孤零零的 x；平移像推着整条波浪走，绝不会改变周期 T = 2π/ω。”</div>
      <p class="mt-insight-b">把 <code>x</code> 换成 <code>(x+d)</code> 后再乘开，相位实际变化 <code>ωd</code>；同时读图求 φ 时，一定要看零点是<strong>向下穿轴（cos 对应 π/2）</strong>还是<strong>向上穿轴（cos 对应 3π/2）</strong>，两者差整整一个 π！</p>
      <div class="row-between" style="gap:8px;flex-wrap:wrap"><span style="font-size:11.5px;font-weight:700;color:#2563eb" data-guess="shift"></span><button type="button" class="btn sm" data-goto="range">下一关：区间值域扫描仪 →</button></div>
    </div>
  </section>

  <!-- 2: RANGE & UNIT CIRCLE SCANNER -->
  <section class="panel hidden" data-pane="range">
    <div style="font-size:17px;font-weight:800;margin-bottom:4px">区间值域扫描仪：为什么只代入左右端点经常算错最值？</div>
    <div style="font-size:12.5px;color:var(--ink-2)">针对错题本高频失分点（如 f(x)=2cos(ωx+π/3) 在给定区间的值域 / |f(x)|&lt;2）：左看曲线、右看单位圆弧扫过的位置！</div>
    <div class="mt-predict">
      <div class="mt-predict-q">① 先猜一猜：求 f(x) = 2cos(2x + π/3) 在 x ∈ [0, π/2] 上的最小值，直接算 f(0) 和 f(π/2) 谁小就行吗？</div>
      <div class="mt-opts" data-lab="range">
        <button type="button" class="mt-opt" data-val="ends">可以，最小值肯定在两个端点里</button>
        <button type="button" class="mt-opt" data-val="peak">不行！相位 2x+π/3 ∈ [π/3, 4π/3] 中间扫过了 π，最小值是 -2！</button>
      </div>
    </div>
    <div class="mt-stage"><canvas data-cv="range" width="740" height="320"></canvas></div>
    <div class="mt-ctrl">
      <div class="mt-range"><label>角频率 ω</label><input data-in="rgW" type="range" min="0.5" max="2.5" value="1.0" step="0.25"><span class="mt-val" data-out="rgW">ω = 1.00</span></div>
      <div class="mt-range"><label>区间右端 b</label><input data-in="rgB" type="range" min="2" max="12" value="4" step="1"><span class="mt-val" data-out="rgB">b = π/3</span></div>
      <button type="button" class="btn sm ghost" data-act="rgTrap">一键载入错题陷阱 (ω=2, b=π/2)</button>
    </div>
    <div class="mt-tasks">
      <span class="mt-task" data-task="rg1">○ 目标 1：在窄区间观察「仅端点决定值域」</span>
      <span class="mt-task" data-task="rg2">○ 目标 2：拉大 ω 或 b 让右侧单位圆弧扫过 π（波谷 -2）触发陷阱告警</span>
    </div>
    <div class="mt-insight hidden" data-insight="range">
      <div style="font-size:11px;font-weight:800;color:#059669">✦ 直觉已建立</div>
      <div class="mt-insight-q">“求三角函数区间值域，先算整体相位 u = ωx + φ 的范围，再在单位圆上画一段弧——弧扫到最左就是 -A，扫到最右就是 +A！”</div>
      <p class="mt-insight-b">判断 <code>|2cos(ωx+π/3)| &lt; 2</code> 在开区间恒成立，本质就是让单位圆弧<strong>严格避开 0、π、2π 这些水平极值点</strong>。先画弧再看左右边界，再也不会漏掉内部极值！</p>
      <div class="row-between" style="gap:8px;flex-wrap:wrap"><span style="font-size:11.5px;font-weight:700;color:#2563eb" data-guess="range"></span><button type="button" class="btn sm" data-goto="combine">下一关：降幂与辅助角 →</button></div>
    </div>
  </section>

  <!-- 3: DOUBLE ANGLE & AUXILIARY ANGLE -->
  <section class="panel hidden" data-pane="combine">
    <div style="font-size:17px;font-weight:800;margin-bottom:4px">二倍角降幂与辅助角合成：如何一眼锁死符号与常数项？</div>
    <div style="font-size:12.5px;color:var(--ink-2)">内置错题本 3 道原题预设！看青色 a·sin2x 与橙色 b·cos2x 如何通过右侧「矢量直角三角形」合成金色波形 R·sin(2x+φ)+c。</div>
    <div class="mt-predict">
      <div class="mt-predict-q">① 先猜一猜：把 sin²x - 1/2 降幂化简成 cos2x，前面的符号是正还是负？</div>
      <div class="mt-opts" data-lab="combine">
        <button type="button" class="mt-opt" data-val="plus">+1/2 cos 2x</button>
        <button type="button" class="mt-opt" data-val="minus">-1/2 cos 2x（因为 sin²x = (1 - cos2x)/2）</button>
      </div>
    </div>
    <div class="mt-stage"><canvas data-cv="combine" width="740" height="320"></canvas></div>
    <div class="mt-ctrl">
      <button type="button" class="btn sm" data-pre="q6">错题 6：2sinxcosx+2√3cos²x-√3</button>
      <button type="button" class="btn sm ghost" data-pre="q7">错题 7：√3sin2x-2cos²x-1</button>
      <button type="button" class="btn sm ghost" data-pre="q8">错题 8：√3sinxcosx+sin²x-1/2</button>
    </div>
    <div class="mt-tasks">
      <span class="mt-task" data-task="cb1">○ 目标 1：点击查看至少 2 道错题本原题的降幂与矢量合成拆解</span>
    </div>
    <div class="mt-insight hidden" data-insight="combine">
      <div style="font-size:11px;font-weight:800;color:#059669">✦ 直觉已建立</div>
      <div class="mt-insight-q">“记住口诀：cos² 降幂带加号、sin² 降幂带减号；常数项单独算清，再用 (a, b) 矢量象限锁死 φ 符号！”</div>
      <p class="mt-insight-b">每次化简分三步走：① <code>sin²x = (1-cos2x)/2</code>、<code>cos²x = (1+cos2x)/2</code> 单独拎出常数项 <code>c</code>；② 整理成 <code>a sin2x + b cos2x + c</code>；③ 看点 <code>(a, b)</code> 落在第几象限，直接读出 <code>R=√(a²+b²)</code> 与 φ 符号，彻底告别正负号写反！</p>
      <div class="row-between" style="gap:8px;flex-wrap:wrap"><span style="font-size:11.5px;font-weight:700;color:#2563eb" data-guess="combine"></span><button type="button" class="btn sm" data-goto="induce">下一关：诱导公式旋转 →</button></div>
    </div>
  </section>

  <!-- 4: INDUCTION FORMULAS ROTATION -->
  <section class="panel hidden" data-pane="induce">
    <div style="font-size:17px;font-weight:800;margin-bottom:4px">诱导公式单位圆旋转：不用死背，3 秒看穿正负号！</div>
    <div style="font-size:12.5px;color:var(--ink-2)">把 θ 看成第一象限小锐角（比如 25°），点击旋转按钮，看横坐标（cos）和纵坐标（sin）长度怎么互换、正负怎么变！</div>
    <div class="mt-predict">
      <div class="mt-predict-q">① 先猜一猜：cos(π/2 + θ) 化简后等于什么？</div>
      <div class="mt-opts" data-lab="induce">
        <button type="button" class="mt-opt" data-val="possin">+sin θ</button>
        <button type="button" class="mt-opt" data-val="negsin">-sin θ（逆时针转 90° 进第二象限，横坐标变负！）</button>
      </div>
    </div>
    <div class="mt-stage"><canvas data-cv="induce" width="740" height="320"></canvas></div>
    <div class="mt-ctrl">
      <div class="mt-range"><label>锐角 θ</label><input data-in="inDeg" type="range" min="15" max="40" value="25" step="5"><span class="mt-val" data-out="inDeg">25°</span></div>
      <button type="button" class="btn sm" data-rot="p90">θ + π/2</button>
      <button type="button" class="btn sm ghost" data-rot="p180">π + θ</button>
      <button type="button" class="btn sm ghost" data-rot="p270">3π/2 + θ</button>
      <button type="button" class="btn sm ghost" data-rot="m180">π - θ</button>
    </div>
    <div class="mt-tasks">
      <span class="mt-task" data-task="in1">○ 目标 1：至少切换体验 3 种诱导旋转（+π/2、π+θ、3π/2+θ 等）</span>
    </div>
    <div class="mt-insight hidden" data-insight="induce">
      <div style="font-size:11px;font-weight:800;color:#059669">✦ 直觉已建立</div>
      <div class="mt-insight-q">“把 θ 当成 25° 小锐角在脑海里转一圈：横竖互换就是‘奇变’，落进哪象限直接看横纵坐标正负！”</div>
      <p class="mt-insight-b">例如 <code>cos(π/2+θ)</code>：25°+90°=115° 在第二象限，横坐标（cos）是负的，且长度变成原来的短边（sinθ），一眼锁死 <code>-sinθ</code>！再配齐次式上下同除 <code>cosθ</code> 化成 <code>tanθ</code>，错题 #9、#12、#14 全部迎刃而解。</p>
      <div class="row-between" style="gap:8px;flex-wrap:wrap"><span style="font-size:11.5px;font-weight:700;color:#2563eb" data-guess="induce"></span><button type="button" class="btn sm" data-goto="summary">查看错题突破总结 🏆</button></div>
    </div>
  </section>

  <!-- SUMMARY -->
  <section class="panel hidden" data-pane="summary">
    <div style="text-align:center;margin-bottom:12px">
      <div style="font-size:18px;font-weight:900" data-sum="title">突破进行中：已完成 0 / 4 项直觉训练</div>
      <div style="font-size:12.5px;color:var(--ink-2);margin-top:4px">这 4 把“可视化钥匙”直接对应错题本里 16 道三角函数高频错题——建好直觉再回去重做清零！</div>
    </div>
    <div data-sum="list"></div>
    <div class="row-between" style="margin-top:10px;gap:8px;flex-wrap:wrap">
      <button type="button" class="btn sm ghost" data-act="resetAll">重新训练</button>
      <button type="button" class="btn sm" data-act="goWrongbook">去错题本重做清零 →</button>
    </div>
  </section>
  ` });
  root.appendChild(body);

  const $ = (s) => body.querySelector(s);
  const $$ = (s) => [...body.querySelectorAll(s)];
  function updateGuess(lab) { const o = $(`[data-guess="${lab}"]`); if (!o) return; const g = state.guesses[lab]; o.textContent = !g ? '下次可先做直觉押注再动手！' : (g === state.correct[lab] ? '🎯 直觉押注命中真相！' : '💡 图形一下推翻了刚才的错觉！'); }
  function setTask(n, ok, txt) { const t = $(`[data-task="${n}"]`); t.classList.toggle('done', ok); t.textContent = (ok ? '✓ ' : '○ ') + txt; }
  function updateProgress() {
    let n = 0;
    KEYS.forEach((k, i) => { const ok = state.done[k]; if (ok) n++; dots[i].classList.toggle('done', ok); $(`[data-chk="${k}"]`).classList.toggle('hidden', !ok); $(`[data-insight="${k}"]`).classList.toggle('hidden', !ok); if (ok) updateGuess(k); });
    progTxt.textContent = `已突破 ${n} / 4`;
  }
  function switchTab(name) {
    state.tab = name;
    $$('.mt-tab').forEach((b) => b.classList.toggle('active', b.dataset.tab === name));
    $$('[data-pane]').forEach((p) => p.classList.toggle('hidden', p.dataset.pane !== name));
    if (name === 'summary') renderSummary();
    if (name === 'shift') drawShift();
    if (name === 'range') drawRange();
    if (name === 'combine') drawCombine();
    if (name === 'induce') drawInduce();
  }
  $$('.mt-tab').forEach((b) => b.addEventListener('click', () => switchTab(b.dataset.tab)));
  $$('[data-goto]').forEach((b) => b.addEventListener('click', () => switchTab(b.dataset.goto)));
  $$('.mt-opts').forEach((w) => {
    const lab = w.dataset.lab;
    w.querySelectorAll('.mt-opt').forEach((btn) => btn.addEventListener('click', () => {
      state.guesses[lab] = btn.dataset.val; w.querySelectorAll('.mt-opt').forEach((x) => x.classList.toggle('picked', x === btn)); updateGuess(lab);
    }));
  });

  /* ==================== 1: SHIFT & ZERO CROSSING ==================== */
  const cSh = $('[data-cv="shift"]'), ctxSh = cSh.getContext('2d');
  const sh = { w: 2.0, dIdx: 0, showWrong: false };
  const D_STEPS = [
    { v: 0, lbl: '0' }, { v: Math.PI / 12, lbl: 'π/12' }, { v: Math.PI / 6, lbl: 'π/6' },
    { v: Math.PI / 4, lbl: 'π/4' }, { v: Math.PI / 3, lbl: 'π/3' }, { v: 5 * Math.PI / 12, lbl: '5π/12' },
    { v: Math.PI / 2, lbl: 'π/2' }, { v: 7 * Math.PI / 12, lbl: '7π/12' }, { v: 2 * Math.PI / 3, lbl: '2π/3' },
    { v: 3 * Math.PI / 4, lbl: '3π/4' }, { v: 5 * Math.PI / 6, lbl: '5π/6' }, { v: 11 * Math.PI / 12, lbl: '11π/12' },
    { v: Math.PI, lbl: 'π' },
  ];
  function checkSh() {
    setTask('sh1', state.tasks.shShift, '目标 1：拖动左移量 d，观察周期不变且相位实际增 ω·d');
    setTask('sh2', state.tasks.shWrong, '目标 2：开启「常见错解对比」看清两条曲线差异');
    if (state.tasks.shShift && state.tasks.shWrong && !state.done.shift) { state.done.shift = true; updateProgress(); }
  }
  function drawShift() {
    const W = cSh.width, H = cSh.height, cy = 175, scaleX = 95, scaleY = 68, ox = 150;
    const d = D_STEPS[sh.dIdx].v, dLbl = D_STEPS[sh.dIdx].lbl, phi0 = Math.PI / 3;
    ctxSh.clearRect(0, 0, W, H); ctxSh.fillStyle = '#0b1120'; ctxSh.fillRect(0, 0, W, H);
    ctxSh.strokeStyle = '#334155'; ctxSh.lineWidth = 1.5;
    ctxSh.beginPath(); ctxSh.moveTo(20, cy); ctxSh.lineTo(720, cy); ctxSh.moveTo(ox, 70); ctxSh.lineTo(ox, 285); ctxSh.stroke();

    const plot = (fn, col, dash = [], lw = 2.6) => {
      ctxSh.strokeStyle = col; ctxSh.lineWidth = lw; ctxSh.setLineDash(dash); ctxSh.beginPath();
      for (let px = 30; px <= 710; px += 3) {
        const x = (px - ox) / scaleX, y = cy - fn(x) * scaleY;
        if (px === 30) ctxSh.moveTo(px, y); else ctxSh.lineTo(px, y);
      }
      ctxSh.stroke(); ctxSh.setLineDash([]);
    };

    plot((x) => Math.sin(sh.w * x + phi0), 'rgba(148,163,184,0.45)', [5, 5], 2);
    if (sh.showWrong && d > 0) plot((x) => Math.sin(sh.w * x + phi0 + d), '#f87171', [6, 4], 2.4);
    plot((x) => Math.sin(sh.w * (x + d) + phi0), '#34d399', [], 3);

    // Mark zero crossings (up vs down) on the green curve
    for (let k = -2; k <= 6; k++) {
      const xz = (k * Math.PI - phi0) / sh.w - d;
      const px = ox + xz * scaleX;
      if (px > 40 && px < 688) {
        const slope = sh.w * Math.cos(k * Math.PI);
        ctxSh.fillStyle = slope > 0 ? '#38bdf8' : '#fbbf24';
        ctxSh.beginPath(); ctxSh.arc(px, cy, 5, 0, Math.PI * 2); ctxSh.fill();
        ctxSh.font = FS.small; ctxSh.textAlign = 'center';
        ctxSh.fillText(slope > 0 ? '↑上穿' : '↓下穿', px, cy + (slope > 0 ? -16 : 28));
        ctxSh.textAlign = 'left';
      }
    }

    canvasHud(ctxSh, {
      x: 16, y: 10, lh: 32, bg: 'rgba(15,23,42,0.9)', stroke: '#243044',
      lines: [
        { text: `sin(${sh.w}(x+${dLbl}) + π/3) · T = ${(2 / sh.w).toFixed(2)}π`, font: FS.hudSub, color: '#34d399' },
        { text: sh.showWrong ? `红：sin(${sh.w}x + π/3 + ${dLbl}) 漏乘 ω=${sh.w}` : '灰虚线 = 原函数 · 零点标 ↑上穿 / ↓下穿', font: FS.small, color: sh.showWrong ? '#f87171' : '#94a3b8' },
      ],
    });
  }
  $('[data-in="shW"]').addEventListener('input', (e) => { sh.w = Number(e.target.value); $('[data-out="shW"]').textContent = `ω = ${sh.w.toFixed(1)}`; drawShift(); });
  $('[data-in="shD"]').addEventListener('input', (e) => { sh.dIdx = Number(e.target.value); $('[data-out="shD"]').textContent = D_STEPS[sh.dIdx].lbl; if (sh.dIdx > 0) state.tasks.shShift = true; checkSh(); drawShift(); });
  $('[data-act="shWrong"]').addEventListener('click', (e) => { sh.showWrong = !sh.showWrong; e.currentTarget.textContent = sh.showWrong ? '隐藏错解对比' : '显示常见错解对比'; if (sh.showWrong) { state.tasks.shWrong = true; if (sh.dIdx === 0) { sh.dIdx = 3; $('[data-in="shD"]').value = '3'; $('[data-out="shD"]').textContent = D_STEPS[3].lbl; state.tasks.shShift = true; } } checkSh(); drawShift(); });

  /* ==================== 2: RANGE & UNIT CIRCLE ==================== */
  const cRg = $('[data-cv="range"]'), ctxRg = cRg.getContext('2d');
  const rg = { w: 1.0, bIdx: 4 }; // b = bIdx * pi/12, a = 0, phi = pi/3, f(x) = 2cos(wx + pi/3)
  function checkRg() {
    setTask('rg1', state.tasks.rgEnd, '目标 1：窄区间观察「仅端点决定值域」');
    setTask('rg2', state.tasks.rgPeak, '目标 2：让单位圆弧扫过波谷 π（-2）触发陷阱告警');
    if (state.tasks.rgEnd && state.tasks.rgPeak && !state.done.range) { state.done.range = true; updateProgress(); }
  }
  function drawRange() {
    const W = cRg.width, H = cRg.height;
    ctxRg.clearRect(0, 0, W, H); ctxRg.fillStyle = '#0b1120'; ctxRg.fillRect(0, 0, W, H);
    const phi = Math.PI / 3, a = 0, b = (rg.bIdx * Math.PI) / 12;
    const u1 = rg.w * a + phi, u2 = rg.w * b + phi;

    // Sample true min/max vs endpoint-only min/max
    const f = (x) => 2 * Math.cos(rg.w * x + phi);
    const fa = f(a), fb = f(b);
    const endMin = Math.min(fa, fb), endMax = Math.max(fa, fb);
    let trueMin = endMin, trueMax = endMax;
    for (let i = 0; i <= 200; i++) {
      const y = f(a + (b - a) * (i / 200));
      if (y < trueMin) trueMin = y;
      if (y > trueMax) trueMax = y;
    }
    const trap = (endMin - trueMin > 0.05) || (trueMax - endMax > 0.05);
    if (trap) state.tasks.rgPeak = true; else state.tasks.rgEnd = true;
    checkRg();

    // Left: Function plot
    const ox = 55, cy = 185, sx = 110, sy = 42;
    ctxRg.strokeStyle = '#334155'; ctxRg.lineWidth = 1.5;
    ctxRg.beginPath(); ctxRg.moveTo(30, cy); ctxRg.lineTo(445, cy); ctxRg.moveTo(ox, 85); ctxRg.lineTo(ox, 285); ctxRg.stroke();
    ctxRg.strokeStyle = 'rgba(148,163,184,0.35)'; ctxRg.lineWidth = 2; ctxRg.beginPath();
    for (let px = 40; px <= 440; px += 3) { const x = (px - ox) / sx, y = cy - f(x) * sy; if (px === 40) ctxRg.moveTo(px, y); else ctxRg.lineTo(px, y); }
    ctxRg.stroke();

    // Highlight [a, b] segment
    ctxRg.strokeStyle = trap ? '#fbbf24' : '#38bdf8'; ctxRg.lineWidth = 4; ctxRg.beginPath();
    for (let i = 0; i <= 80; i++) { const x = a + (b - a) * (i / 80), px = ox + x * sx, py = cy - f(x) * sy; if (i === 0) ctxRg.moveTo(px, py); else ctxRg.lineTo(px, py); }
    ctxRg.stroke();

    // Right: Unit circle mapping u in [u1, u2]
    const cx = 585, ccy = 178, cr = 70;
    ctxRg.strokeStyle = '#334155'; ctxRg.lineWidth = 1.5;
    ctxRg.beginPath(); ctxRg.arc(cx, ccy, cr, 0, Math.PI * 2); ctxRg.stroke();
    ctxRg.beginPath(); ctxRg.moveTo(cx - cr - 12, ccy); ctxRg.lineTo(cx + cr + 12, ccy); ctxRg.moveTo(cx, ccy - cr - 12); ctxRg.lineTo(cx, ccy + cr + 12); ctxRg.stroke();

    // Glowing arc on unit circle (canvas y is inverted, so -u)
    ctxRg.strokeStyle = trap ? '#fbbf24' : '#38bdf8'; ctxRg.lineWidth = 6; ctxRg.shadowColor = trap ? '#fbbf24' : '#38bdf8'; ctxRg.shadowBlur = 10;
    ctxRg.beginPath(); ctxRg.arc(cx, ccy, cr, -u2, -u1); ctxRg.stroke(); ctxRg.shadowBlur = 0;
    // Mark pi (-1) and 0 (+1) on unit circle
    ctxRg.fillStyle = '#f87171'; ctxRg.beginPath(); ctxRg.arc(cx - cr, ccy, 5, 0, Math.PI * 2); ctxRg.fill();
    ctxRg.fillStyle = '#94a3b8'; ctxRg.beginPath(); ctxRg.arc(cx + cr, ccy, 5, 0, Math.PI * 2); ctxRg.fill();
    ctxRg.textAlign = 'center';
    ctxRg.fillStyle = '#cbd5e1'; ctxRg.font = FS.small; ctxRg.fillText('相位 u 单位圆弧', cx, 272);
    ctxRg.fillStyle = '#fca5a5'; ctxRg.fillText('红点 π 处 = -2 · 灰点 0 处 = +2', cx, 300);
    ctxRg.textAlign = 'left';

    // Top HUD
    canvasHud(ctxRg, {
      x: 16, y: 10, lh: 32, bg: 'rgba(15,23,42,0.9)', stroke: trap ? '#fbbf24' : '#243044',
      lines: [
        { text: `2cos(${rg.w}x+π/3) · x∈[0,${rg.bIdx}π/12] · 值域[${trueMin.toFixed(2)}, ${trueMax.toFixed(2)}]`, font: FS.hudSub, color: '#7dd3fc' },
        { text: trap ? `⚠️ 端点算得 [${endMin.toFixed(2)}, ${endMax.toFixed(2)}]，漏掉弧扫过的极值` : `仅端点决定：[${endMin.toFixed(2)}, ${endMax.toFixed(2)}] 即值域`, font: FS.small, color: trap ? '#fbbf24' : '#34d399' },
      ],
    });
  }
  $('[data-in="rgW"]').addEventListener('input', (e) => { rg.w = Number(e.target.value); $('[data-out="rgW"]').textContent = `ω = ${rg.w.toFixed(2)}`; drawRange(); });
  $('[data-in="rgB"]').addEventListener('input', (e) => { rg.bIdx = Number(e.target.value); $('[data-out="rgB"]').textContent = `b = ${rg.bIdx}π/12`; drawRange(); });
  $('[data-act="rgTrap"]').addEventListener('click', () => { rg.w = 2.0; rg.bIdx = 6; $('[data-in="rgW"]').value = '2'; $('[data-out="rgW"]').textContent = 'ω = 2.00'; $('[data-in="rgB"]').value = '6'; $('[data-out="rgB"]').textContent = 'b = π/2'; drawRange(); });

  /* ==================== 3: DOUBLE ANGLE & AUXILIARY ==================== */
  const cCb = $('[data-cv="combine"]'), ctxCb = cCb.getContext('2d');
  const PRESETS = {
    q6: { name: '错题 6：2sinxcosx + 2√3cos²x - √3', a: 1, b: Math.sqrt(3), c: 0, step1: '降幂：sin2x + √3(1+cos2x) - √3 = sin2x + √3cos2x', final: '2 sin(2x + π/3)' },
    q7: { name: '错题 7：√3sin2x - 2cos²x - 1', a: Math.sqrt(3), b: -1, c: -2, step1: '降幂：√3sin2x - (1+cos2x) - 1 = √3sin2x - cos2x - 2', final: '2 sin(2x - π/6) - 2' },
    q8: { name: '错题 8：√3sinxcosx + sin²x - 1/2', a: Math.sqrt(3) / 2, b: -0.5, c: 0, step1: '降幂：(√3/2)sin2x + (1-cos2x)/2 - 1/2 = (√3/2)sin2x - (1/2)cos2x', final: 'sin(2x - π/6)' },
  };
  let curPre = 'q6';
  function checkCb() {
    const ok = state.tasks.cbPreset.size >= 2;
    setTask('cb1', ok, `目标 1：查看至少 2 道错题本原题拆解（已看 ${Math.min(2, state.tasks.cbPreset.size)}/2）`);
    if (ok && !state.done.combine) { state.done.combine = true; updateProgress(); }
  }
  function drawCombine() {
    const pr = PRESETS[curPre], W = cCb.width, H = cCb.height;
    ctxCb.clearRect(0, 0, W, H); ctxCb.fillStyle = '#0b1120'; ctxCb.fillRect(0, 0, W, H);
    const R = Math.hypot(pr.a, pr.b), phi = Math.atan2(pr.b, pr.a);

    // Top explanation banner
    canvasHud(ctxCb, {
      x: 16, y: 10, lh: 32, bg: 'rgba(15,23,42,0.9)', stroke: '#243044',
      lines: [
        { text: pr.name, font: FS.small, color: '#7dd3fc' },
        { text: pr.step1, font: FS.small, color: '#cbd5e1' },
        { text: `合成：f(x) = ${pr.final}（R = ${R.toFixed(2)}, c = ${pr.c}）`, font: FS.label, color: '#fde047' },
      ],
    });

    // Left: Component waves + combined wave
    const cy = 195, sy = 22;
    ctxCb.strokeStyle = '#334155'; ctxCb.lineWidth = 1; ctxCb.beginPath(); ctxCb.moveTo(28, cy); ctxCb.lineTo(445, cy); ctxCb.stroke();
    const plotW = (fn, col, lw) => {
      ctxCb.strokeStyle = col; ctxCb.lineWidth = lw; ctxCb.beginPath();
      for (let px = 30; px <= 440; px += 4) { const x = (px - 30) * 0.02, y = cy - fn(x) * sy; if (px === 30) ctxCb.moveTo(px, y); else ctxCb.lineTo(px, y); }
      ctxCb.stroke();
    };
    plotW((x) => pr.a * Math.sin(2 * x), 'rgba(56,189,248,0.5)', 1.8);
    plotW((x) => pr.b * Math.cos(2 * x), 'rgba(249,115,22,0.5)', 1.8);
    plotW((x) => R * Math.sin(2 * x + phi) + pr.c, '#fde047', 3.2);
    ctxCb.fillStyle = '#94a3b8'; ctxCb.font = FS.small;
    ctxCb.fillText('青 a·sin2x · 橙 b·cos2x · 金 合成波', 26, 304);

    // Right: Vector triangle (a, b) -> R, angle phi
    const vx = 530, vy = 205, vs = 55;
    ctxCb.strokeStyle = '#334155'; ctxCb.beginPath(); ctxCb.moveTo(vx - 30, vy); ctxCb.lineTo(vx + 150, vy); ctxCb.moveTo(vx, vy - 100); ctxCb.lineTo(vx, vy + 95); ctxCb.stroke();
    ctxCb.strokeStyle = '#38bdf8'; ctxCb.lineWidth = 3; ctxCb.beginPath(); ctxCb.moveTo(vx, vy); ctxCb.lineTo(vx + pr.a * vs, vy); ctxCb.stroke();
    ctxCb.strokeStyle = '#f97316'; ctxCb.beginPath(); ctxCb.moveTo(vx + pr.a * vs, vy); ctxCb.lineTo(vx + pr.a * vs, vy - pr.b * vs); ctxCb.stroke();
    ctxCb.strokeStyle = '#fde047'; ctxCb.lineWidth = 3.5; ctxCb.beginPath(); ctxCb.moveTo(vx, vy); ctxCb.lineTo(vx + pr.a * vs, vy - pr.b * vs); ctxCb.stroke();
    ctxCb.textAlign = 'center';
    ctxCb.fillStyle = '#fde047'; ctxCb.font = FS.small;
    ctxCb.fillText(`φ = ${(phi * 180 / Math.PI).toFixed(0)}°（${phi >= 0 ? '正' : '负'}）· 象限定符号`, 585, 304);
    ctxCb.textAlign = 'left';
  }
  $$('[data-pre]').forEach((btn) => btn.addEventListener('click', () => {
    curPre = btn.dataset.pre;
    state.tasks.cbPreset.add(curPre);
    $$('[data-pre]').forEach((b) => b.classList.toggle('ghost', b !== btn));
    checkCb(); drawCombine();
  }));

  /* ==================== 4: INDUCTION ROTATION ==================== */
  const cIn = $('[data-cv="induce"]'), ctxIn = cIn.getContext('2d');
  const ind = { deg: 25, mode: 'p90' };
  const ROTS = {
    p90: { lbl: 'θ + π/2', fn: (r) => r + Math.PI / 2, res: ['sin(π/2+θ) = +cosθ', 'cos(π/2+θ) = -sinθ'], hint: '逆时针 90° 进第二象限：横坐标变负' },
    p180: { lbl: 'π + θ', fn: (r) => r + Math.PI, res: ['sin(π+θ) = -sinθ', 'cos(π+θ) = -cosθ'], hint: '转 180° 进第三象限：横纵都取负' },
    p270: { lbl: '3π/2 + θ', fn: (r) => r + 1.5 * Math.PI, res: ['sin(3π/2+θ) = -cosθ', 'cos(3π/2+θ) = +sinθ'], hint: '转 270° 进第四象限：纵坐标为负' },
    m180: { lbl: 'π - θ', fn: (r) => Math.PI - r, res: ['sin(π-θ) = +sinθ', 'cos(π-θ) = -cosθ'], hint: '关于 y 轴对称：纵不变、横变负' },
  };
  function checkIn() {
    const ok = state.tasks.inModes.size >= 3;
    setTask('in1', ok, `目标 1：体验至少 3 种诱导旋转（已试 ${Math.min(3, state.tasks.inModes.size)}/3）`);
    if (ok && !state.done.induce) { state.done.induce = true; updateProgress(); }
  }
  function drawInduce() {
    const W = cIn.width, H = cIn.height, cx = 220, cy = 180, R = 100;
    const rad = ind.deg * Math.PI / 180, rotInfo = ROTS[ind.mode], rad2 = rotInfo.fn(rad);
    ctxIn.clearRect(0, 0, W, H); ctxIn.fillStyle = '#0b1120'; ctxIn.fillRect(0, 0, W, H);
    ctxIn.strokeStyle = '#334155'; ctxIn.lineWidth = 1.5;
    ctxIn.beginPath(); ctxIn.arc(cx, cy, R, 0, Math.PI * 2); ctxIn.stroke();
    ctxIn.beginPath(); ctxIn.moveTo(cx - R - 20, cy); ctxIn.lineTo(cx + R + 20, cy); ctxIn.moveTo(cx, cy - R - 20); ctxIn.lineTo(cx, cy + R + 20); ctxIn.stroke();

    const drawVec = (a, col, lbl) => {
      const px = cx + Math.cos(a) * R, py = cy - Math.sin(a) * R;
      ctxIn.strokeStyle = col; ctxIn.lineWidth = 3; ctxIn.beginPath(); ctxIn.moveTo(cx, cy); ctxIn.lineTo(px, py); ctxIn.stroke();
      ctxIn.strokeStyle = 'rgba(56,189,248,0.65)'; ctxIn.lineWidth = 2; ctxIn.beginPath(); ctxIn.moveTo(cx, cy); ctxIn.lineTo(px, cy); ctxIn.stroke();
      ctxIn.strokeStyle = 'rgba(248,113,113,0.75)'; ctxIn.beginPath(); ctxIn.moveTo(px, cy); ctxIn.lineTo(px, py); ctxIn.stroke();
      ctxIn.fillStyle = col; ctxIn.beginPath(); ctxIn.arc(px, py, 5.5, 0, Math.PI * 2); ctxIn.fill();
      ctxIn.font = FS.small; ctxIn.textAlign = 'center'; ctxIn.fillStyle = col;
      ctxIn.fillText(lbl, cx + Math.cos(a) * R * 1.16, cy - Math.sin(a) * R * 1.16 + 6);
      ctxIn.textAlign = 'left';
    };
    drawVec(rad, '#94a3b8', `θ=${ind.deg}°`);
    drawVec(rad2, '#fde047', rotInfo.lbl);

    canvasHud(ctxIn, {
      x: 356, y: 36, lh: 34, pad: 16, bg: 'rgba(15,23,42,0.9)', stroke: '#243044',
      lines: [
        { text: `当前变换：${rotInfo.lbl}`, font: FS.label, color: '#fde047' },
        { text: rotInfo.res[0], font: FS.small, color: '#34d399' },
        { text: rotInfo.res[1], font: FS.small, color: '#34d399' },
        { text: rotInfo.hint, font: FS.small, color: '#cbd5e1' },
        { text: '青横段 = cos（左右定正负）', font: FS.small, color: '#38bdf8' },
        { text: '红竖段 = sin（上下定正负）', font: FS.small, color: '#f87171' },
      ],
    });
  }
  $('[data-in="inDeg"]').addEventListener('input', (e) => { ind.deg = Number(e.target.value); $('[data-out="inDeg"]').textContent = `${ind.deg}°`; drawInduce(); });
  $$('[data-rot]').forEach((btn) => btn.addEventListener('click', () => {
    ind.mode = btn.dataset.rot; state.tasks.inModes.add(ind.mode);
    $$('[data-rot]').forEach((b) => b.classList.toggle('ghost', b !== btn));
    checkIn(); drawInduce();
  }));

  /* ==================== SUMMARY ==================== */
  function renderSummary() {
    const dN = KEYS.filter((k) => state.done[k]).length;
    $('[data-sum="title"]').textContent = dN === 4 ? '🏆 4 大错题痛点直觉全部通关！去清零错题本吧！' : `突破进行中：已完成 ${dN} / 4 项直觉训练`;
    const rows = [
      { k: 'shift', t: '1. 图像平移与穿轴（错题 #2, #4, #15）', p: '“左加右减只换 x，平移绝不改周期；过零看清上穿/下穿。”' },
      { k: 'range', t: '2. 区间值域单位圆扫描（错题 #1, #3, #16）', p: '“先算整体相位范围再画单位圆弧，扫过 0 或 π 必取极值。”' },
      { k: 'combine', t: '3. 二倍角降幂与辅助角（错题 #5–#8）', p: '“cos² 加、sin² 减，常数项单拎，矢量象限锁死 φ 正负。”' },
      { k: 'induce', t: '4. 诱导公式单位圆旋转（错题 #9–#14）', p: '“把 θ 当 25° 锐角转一圈，青横 cos、红竖 sin 一眼定符号。”' },
    ];
    $('[data-sum="list"]').innerHTML = rows.map((r) => `<div class="mt-recap"><div style="font-size:13.5px;font-weight:800">${state.done[r.k] ? '✅ ' : '🔒 '}${r.t}</div><div style="font-size:12.5px;color:var(--ink-2);margin-top:3px">${state.done[r.k] ? r.p : '完成对应互动训练后解锁'}</div></div>`).join('');
  }
  $('[data-act="resetAll"]').addEventListener('click', () => {
    KEYS.forEach((k) => { state.guesses[k] = null; state.done[k] = false; });
    state.tasks = { shShift: false, shWrong: false, rgEnd: false, rgPeak: false, cbPreset: new Set(), inModes: new Set() };
    $$('.mt-opt').forEach((b) => b.classList.remove('picked'));
    checkSh(); checkRg(); checkCb(); checkIn(); updateProgress(); renderSummary(); switchTab('shift');
  });
  $('[data-act="goWrongbook"]').addEventListener('click', () => navigate('#/wrongbook'));

  view.innerHTML = ''; view.appendChild(root);
  state.tasks.cbPreset.add('q6'); state.tasks.inModes.add('p90');
  checkSh(); checkRg(); checkCb(); checkIn(); updateProgress();
  drawShift(); drawRange(); drawCombine(); drawInduce();
  mountLabBonus(root, '.mt-tabs');
}
