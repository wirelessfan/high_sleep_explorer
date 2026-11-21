/* 物理学实验简史：5 场互动探索实验室（先猜直觉 -> 动手实验 -> 解锁画龙点睛 -> 全景总结） */

import { el } from '../ui.js';
import { navigate } from '../router.js';
import { mountLabBonus } from '../lab-bonus.js';
import { canvasHud, FS } from '../lab-canvas.js';

const LAB_CSS = `
.explab{display:flex;flex-direction:column;gap:12px}
.explab .el-pill{display:inline-flex;align-items:center;gap:6px;padding:5px 11px;border-radius:999px;background:#fff;border:1px solid var(--line);font-size:12px;font-weight:700;color:var(--ink-2)}
.explab .el-dot{width:8px;height:8px;border-radius:50%;background:#d6c7b2;transition:background .2s}
.explab .el-dot.done{background:#059669}
.explab .el-tabs{display:flex;flex-wrap:wrap;gap:7px}
.explab .el-tab{appearance:none;border:1px solid var(--line);background:#fff;color:var(--ink-2);padding:7px 11px;border-radius:999px;font-size:12px;font-weight:700;cursor:pointer;display:inline-flex;align-items:center;gap:5px}
.explab .el-tab.active{background:#5a463a;border-color:#5a463a;color:#fffdf8}
.explab .el-tab .chk{font-size:10.5px;padding:1px 5px;border-radius:999px;background:#ecfdf5;color:#059669}
.explab .el-tab.active .chk{background:rgba(255,255,255,.22);color:#fff}
.explab .el-predict{background:#faf6ef;border:1px dashed #dfcfb7;border-radius:12px;padding:11px 12px;margin:10px 0 12px}
.explab .el-predict-q{font-size:13px;font-weight:800;margin:0 0 8px;color:var(--ink)}
.explab .el-opts{display:flex;flex-wrap:wrap;gap:7px}
.explab .el-opt{appearance:none;background:#fff;border:1px solid #dfd2be;color:var(--ink-2);padding:6px 11px;border-radius:9px;font-size:12px;font-weight:700;cursor:pointer}
.explab .el-opt.picked{background:#eff6ff;border-color:#2563eb;color:#2563eb}
.explab .el-stage{border-radius:12px;overflow:hidden;border:1px solid var(--line);background:#fcfaf5;margin-bottom:12px}
.explab .el-stage canvas{display:block;width:100%;height:auto;touch-action:none}
.explab .el-ctrl{display:flex;flex-wrap:wrap;align-items:center;gap:10px 14px;padding:10px 12px;background:#faf7f2;border-radius:12px;border:1px solid var(--line);margin-bottom:10px}
.explab .el-range{display:flex;align-items:center;gap:8px;flex:1 1 190px;min-width:170px}
.explab .el-range label{font-size:12px;font-weight:700;color:var(--ink-2);white-space:nowrap}
.explab .el-range input{flex:1;cursor:pointer}
.explab .el-val{font-size:12px;font-weight:800;color:#2563eb;min-width:60px;text-align:right;font-variant-numeric:tabular-nums}
.explab .el-tasks{display:flex;flex-wrap:wrap;gap:7px;margin-bottom:4px}
.explab .el-task{font-size:11.5px;font-weight:700;padding:4px 10px;border-radius:9px;background:#f5f0e7;color:var(--ink-3)}
.explab .el-task.done{background:#ecfdf5;color:#059669;border:1px solid #a7f3d0}
.explab .el-insight{margin-top:12px;padding:14px;border-radius:13px;background:linear-gradient(135deg,#f0fdf4 0%,#eff6ff 100%);border:1px solid #bbf7d0}
.explab .el-insight-q{font-size:15px;font-weight:900;color:var(--ink);margin:4px 0 6px;line-height:1.5}
.explab .el-insight-b{font-size:12.5px;color:var(--ink-2);margin:0 0 10px;line-height:1.65}
.explab .el-sum-grid{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:8px;margin:12px 0}
.explab .el-stat{background:#faf7f2;border:1px solid var(--line);border-radius:12px;padding:10px;text-align:center}
.explab .el-stat b{display:block;font-size:18px;color:#2563eb}
.explab .el-stat span{font-size:11px;color:var(--ink-3)}
.explab .el-recap{border:1px solid var(--line);border-radius:12px;padding:11px 13px;background:#fffdf9;margin-bottom:8px}
.explab .hidden{display:none !important}
`;

export async function renderExperimentsLab(view) {
  const LAB_KEYS = ['galileo', 'newton', 'brach', 'centri', 'faraday'];
  const state = {
    activeTab: 'galileo',
    guesses: { galileo: null, newton: null, brach: null, centri: null, faraday: null },
    correctGuess: { galileo: 'same', newton: 'falling', brach: 'cycloid', centri: 'tangent', faraday: 'onlymove' },
    done: { galileo: false, newton: false, brach: false, centri: false, faraday: false },
    tasks: {
      galAngles: new Set(), galAirChecked: false,
      newFall: false, newOrbit: false,
      brachRace: false, brachTauto: false,
      centriCut: false, centriFrame: false,
      farIn: false, farStop: false, farOut: false,
    },
  };

  let disposed = false;
  const rafs = { gal: 0, newt: 0, brach: 0, centri: 0, far: 0, farDemo: 0 };

  const root = el('div', { class: 'explab' });
  const styleTag = document.createElement('style');
  styleTag.textContent = LAB_CSS;
  root.appendChild(styleTag);

  const progressDots = LAB_KEYS.map(() => el('span', { class: 'el-dot' }));
  const progressText = el('span', { text: '已探索 0 / 5' });
  root.appendChild(el('div', { class: 'topbar' }, [
    el('button', {
      class: 'back', text: '‹',
      onclick: () => { if (history.length > 1) history.back(); else navigate('#/subjects'); },
    }),
    el('div', { style: 'flex:1;min-width:0' }, [
      el('h1', { text: '物理学实验简史' }),
      el('div', { class: 'sub', text: '先猜直觉 · 动手调参数 · 解锁画龙点睛' }),
    ]),
    el('div', { class: 'el-pill' }, [...progressDots, progressText]),
  ]));

  const body = el('div', { html: `
  <nav class="el-tabs">
    <button type="button" class="el-tab active" data-tab="galileo">1. 伽利略斜面 <span class="chk hidden" data-chk="galileo">✓</span></button>
    <button type="button" class="el-tab" data-tab="newton">2. 牛顿大炮 <span class="chk hidden" data-chk="newton">✓</span></button>
    <button type="button" class="el-tab" data-tab="brach">3. 最速曲线 <span class="chk hidden" data-chk="brach">✓</span></button>
    <button type="button" class="el-tab" data-tab="centri">4. 向心力与离心 <span class="chk hidden" data-chk="centri">✓</span></button>
    <button type="button" class="el-tab" data-tab="faraday">5. 法拉第磁生电 <span class="chk hidden" data-chk="faraday">✓</span></button>
    <button type="button" class="el-tab" data-tab="summary">🏆 全景总结</button>
  </nav>

  <section class="panel" data-pane="galileo">
    <div style="font-size:17px;font-weight:800;margin-bottom:4px">伽利略（1604）：把下落变慢，看见 1 : 3 : 5 : 7</div>
    <div style="font-size:12.5px;color:var(--ink-2)">调倾角并释放小球，每隔 1 秒打点；切换「空气阻力」对比铁球与羽毛。</div>
    <div class="el-predict">
      <div class="el-predict-q">① 先猜一猜：斜面从 15° 调陡到 35°，相等时间位移比 1:3:5:7 会变吗？</div>
      <div class="el-opts" data-lab="galileo">
        <button type="button" class="el-opt" data-val="change">会变大，越陡拉得越开</button>
        <button type="button" class="el-opt" data-val="same">不变，永远是 1 : 3 : 5 : 7</button>
      </div>
    </div>
    <div class="el-stage"><canvas data-cv="galileo" width="720" height="320"></canvas></div>
    <div class="el-ctrl">
      <div class="el-range"><label>斜面倾角</label><input data-in="galAngle" type="range" min="12" max="36" value="18" step="2"><span class="el-val" data-out="galAngle">18°</span></div>
      <button type="button" class="btn sm" data-act="galRun">释放小球</button>
      <button type="button" class="btn sm ghost" data-act="galVacuum">当前：真空无阻力</button>
      <button type="button" class="btn sm ghost" data-act="galReset">重置</button>
    </div>
    <div class="el-tasks">
      <span class="el-task" data-task="gal1">○ 目标 1：在两个不同倾角下释放小球</span>
      <span class="el-task" data-task="gal2">○ 目标 2：开启空气阻力对比铁球与羽毛</span>
    </div>
    <div class="el-insight hidden" data-insight="galileo">
      <div style="font-size:11px;font-weight:800;color:#059669">✦ 顿悟时刻已解锁</div>
      <div class="el-insight-q">“靠纯逻辑就能推翻权威；把下落变慢，才能看清时间的刻度。”</div>
      <p class="el-insight-b">无论倾角怎么变，无阻力匀加速的相等时间位移比恒为 <strong>1:3:5:7</strong>；空气阻力骗了人类两千年。伽利略由此确立了现代实验科学方法。</p>
      <div class="row-between" style="gap:8px;flex-wrap:wrap"><span style="font-size:11.5px;font-weight:700;color:#2563eb" data-guess="galileo"></span><button type="button" class="btn sm" data-goto="newton">下一场：牛顿大炮 →</button></div>
    </div>
  </section>

  <section class="panel hidden" data-pane="newton">
    <div style="font-size:17px;font-weight:800;margin-bottom:4px">牛顿大炮（1687）：打得多快，就永远落不到地上？</div>
    <div style="font-size:12.5px;color:var(--ink-2)">拖动初速度多次开炮，对比旧轨迹，亲手把抛物线拉成绕地轨道！</div>
    <div class="el-predict">
      <div class="el-predict-q">① 先猜一猜：卫星绕地球转不掉下来，是因为太空里没引力了吗？</div>
      <div class="el-opts" data-lab="newton">
        <button type="button" class="el-opt" data-val="nograv">是的，到了太空就没引力了</button>
        <button type="button" class="el-opt" data-val="falling">不是，它一直在下落，只是地面弯走了</button>
      </div>
    </div>
    <div class="el-stage"><canvas data-cv="newton" width="720" height="340"></canvas></div>
    <div class="el-ctrl">
      <div class="el-range"><label>初速度 v₀</label><input data-in="newSpeed" type="range" min="3.5" max="11.5" value="5.0" step="0.1"><span class="el-val" data-out="newSpeed">5.0 km/s</span></div>
      <button type="button" class="btn sm" data-act="newFire">开炮发射</button>
      <button type="button" class="btn sm ghost" data-act="newClear">清空轨迹</button>
    </div>
    <div class="el-tasks">
      <span class="el-task" data-task="new1">○ 目标 1：低速开炮看炮弹落地</span>
      <span class="el-task" data-task="new2">○ 目标 2：调到 ≥ 7.9 km/s 发射绕地卫星</span>
    </div>
    <div class="el-insight hidden" data-insight="newton">
      <div style="font-size:11px;font-weight:800;color:#059669">✦ 顿悟时刻已解锁</div>
      <div class="el-insight-q">“苹果落地和月亮绕地球，本质上是一回事。”</div>
      <p class="el-insight-b">达到 <strong>7.9 km/s</strong>（第一宇宙速度）时，炮弹下落弧度恰好匹配地球曲率，永远在下落却永不落地，奠定了卫星轨道工程基石。</p>
      <div class="row-between" style="gap:8px;flex-wrap:wrap"><span style="font-size:11.5px;font-weight:700;color:#2563eb" data-guess="newton"></span><button type="button" class="btn sm" data-goto="brach">下一场：最速曲线 →</button></div>
    </div>
  </section>

  <section class="panel hidden" data-pane="brach">
    <div style="font-size:17px;font-weight:800;margin-bottom:4px">伯努利最速曲线（1696）：直线最短，为何最快的不是直线？</div>
    <div style="font-size:12.5px;color:var(--ink-2)">三轨无摩擦同时发车，再切到「等时性对比」看高低两球同时撞线！</div>
    <div class="el-predict">
      <div class="el-predict-q">① 先猜一猜：从高处 A 无摩擦滑到低处 B，哪条轨道用时最短？</div>
      <div class="el-opts" data-lab="brach">
        <button type="button" class="el-opt" data-val="line">直线最短，肯定最先到</button>
        <button type="button" class="el-opt" data-val="cycloid">先陡后缓的摆线反而最先到</button>
      </div>
    </div>
    <div class="el-stage"><canvas data-cv="brach" width="720" height="330"></canvas></div>
    <div class="el-ctrl">
      <button type="button" class="btn sm" data-act="brachRun">开始发车</button>
      <button type="button" class="btn sm ghost" data-act="brachMode">当前：三轨竞速</button>
      <button type="button" class="btn sm ghost" data-act="brachReset">重置</button>
    </div>
    <div class="el-tasks">
      <span class="el-task" data-task="brach1">○ 目标 1：跑完三轨竞速看摆线反超直线</span>
      <span class="el-task" data-task="brach2">○ 目标 2：切换「等时性对比」看高低两球同时撞线</span>
    </div>
    <div class="el-insight hidden" data-insight="brach">
      <div style="font-size:11px;font-weight:800;color:#059669">✦ 顿悟时刻已解锁</div>
      <div class="el-insight-q">“两点之间直线最短，但最快到达的不是直线——先俯冲蓄能，才能后发先至。”</div>
      <p class="el-insight-b">摆线前期更陡尽早换取高速，还具备神奇的<strong>等时性</strong>。1696 年这场公开挑战直接催生了变分法，支撑现代火箭最优轨道与过山车设计。</p>
      <div class="row-between" style="gap:8px;flex-wrap:wrap"><span style="font-size:11.5px;font-weight:700;color:#2563eb" data-guess="brach"></span><button type="button" class="btn sm" data-goto="centri">下一场：向心力与离心 →</button></div>
    </div>
  </section>

  <section class="panel hidden" data-pane="centri">
    <div style="font-size:17px;font-weight:800;margin-bottom:4px">惠更斯向心力（1659）：绳子一断，小球往哪飞？</div>
    <div style="font-size:12.5px;color:var(--ink-2)">调高转速拉断绳子或点击「剪断绳子」，再切「随动转盘视角」看清“离心错觉”。</div>
    <div class="el-predict">
      <div class="el-predict-q">① 先猜一猜：圆周运动中细绳突然断掉，小球会怎么飞出去？</div>
      <div class="el-opts" data-lab="centri">
        <button type="button" class="el-opt" data-val="radial">被“离心力”沿半径向外直甩出去</button>
        <button type="button" class="el-opt" data-val="tangent">沿断绳瞬间的切线方向直线飞出</button>
      </div>
    </div>
    <div class="el-stage"><canvas data-cv="centri" width="720" height="330"></canvas></div>
    <div class="el-ctrl">
      <div class="el-range"><label>转速 ω</label><input data-in="centriOmega" type="range" min="1.2" max="5.2" value="2.4" step="0.1"><span class="el-val" data-out="centriOmega">2.4 rad/s</span></div>
      <button type="button" class="btn sm" style="background:#dc2626" data-act="centriCut">剪断绳子！</button>
      <button type="button" class="btn sm ghost" data-act="centriFrame">视角：地面观察者</button>
      <button type="button" class="btn sm ghost" data-act="centriReset">重新绑绳</button>
    </div>
    <div class="el-tasks">
      <span class="el-task" data-task="centri1">○ 目标 1：剪断或拉断绳子，观察切线飞出</span>
      <span class="el-task" data-task="centri2">○ 目标 2：切换一次「随动转盘视角」</span>
    </div>
    <div class="el-insight hidden" data-insight="centri">
      <div style="font-size:11px;font-weight:800;color:#059669">✦ 顿悟时刻已解锁</div>
      <div class="el-insight-q">“根本没有把你往外拉的‘离心力’——那只是物体想按惯性走直线，而绳子拉不住了。”</div>
      <p class="el-insight-b">地面视角下只有指向圆心的向心力 <code>F=mω²r</code>；断绳后小球顺切线飞出。洗衣机脱水桶、医用离心机与高速弯道倾斜都运用了这一原理。</p>
      <div class="row-between" style="gap:8px;flex-wrap:wrap"><span style="font-size:11.5px;font-weight:700;color:#2563eb" data-guess="centri"></span><button type="button" class="btn sm" data-goto="faraday">下一场：法拉第磁生电 →</button></div>
    </div>
  </section>

  <section class="panel hidden" data-pane="faraday">
    <div style="font-size:17px;font-weight:800;margin-bottom:4px">法拉第（1831）：亲手拖磁铁进出线圈，点亮灯泡</div>
    <div style="font-size:12.5px;color:var(--ink-2)">在画布直接按住磁铁左右拖动（或拉滑块），观察插入、停住、拔出时灯泡与指针变化。</div>
    <div class="el-predict">
      <div class="el-predict-q">① 先猜一猜：把磁铁插进线圈稳稳停住不动，小灯泡会一直亮着吗？</div>
      <div class="el-opts" data-lab="faraday">
        <button type="button" class="el-opt" data-val="staylit">会一直亮，里面磁场最强</button>
        <button type="button" class="el-opt" data-val="onlymove">不会，一停就灭，动的时候才亮</button>
      </div>
    </div>
    <div class="el-stage"><canvas data-cv="faraday" width="720" height="320"></canvas></div>
    <div class="el-ctrl">
      <div class="el-range"><label>磁铁位置</label><input data-in="farPos" type="range" min="110" max="530" value="150" step="1"><span class="el-val" data-out="farEmf">0.0 V</span></div>
      <button type="button" class="btn sm ghost" data-act="farDemo">自动演示插拔</button>
    </div>
    <div class="el-tasks">
      <span class="el-task" data-task="far1">○ 目标 1：插入线圈点亮灯泡</span>
      <span class="el-task" data-task="far2">○ 目标 2：在线圈内停住看熄灭</span>
      <span class="el-task" data-task="far3">○ 目标 3：快速拔出看指针反偏</span>
    </div>
    <div class="el-insight hidden" data-insight="faraday">
      <div style="font-size:11px;font-weight:800;color:#059669">✦ 顿悟时刻已解锁</div>
      <div class="el-insight-q">“不是磁场生电，而是磁场的‘变化’在生电。”</div>
      <p class="el-insight-b">磁铁静止时磁通量变化率为零，电流归零；动得越快灯泡越亮，拔出方向相反指针立刻反偏。这一发现直接催生了发电机与全球电网。</p>
      <div class="row-between" style="gap:8px;flex-wrap:wrap"><span style="font-size:11.5px;font-weight:700;color:#2563eb" data-guess="faraday"></span><button type="button" class="btn sm" data-goto="summary">查看全景总结 🏆</button></div>
    </div>
  </section>

  <section class="panel hidden" data-pane="summary">
    <div style="text-align:center;margin-bottom:10px">
      <div style="font-size:18px;font-weight:900" data-sum="title">探索进行中：已完成 0 / 5 场实验</div>
      <div style="font-size:12.5px;color:var(--ink-2);margin-top:4px" data-sum="sub">完成全部 5 场互动操作，解锁你的物理学破局档案。</div>
    </div>
    <div class="el-sum-grid">
      <div class="el-stat"><b data-sum="done">0 / 5</b><span>已解锁实验</span></div>
      <div class="el-stat"><b data-sum="hit">0 / 5</b><span>直觉押注命中</span></div>
      <div class="el-stat"><b>227 年</b><span>科学史跨度</span></div>
    </div>
    <div data-sum="list"></div>
    <div class="row-between" style="margin-top:10px">
      <button type="button" class="btn sm ghost" data-act="resetAll">重新开始全部探索</button>
      <button type="button" class="btn sm" data-act="backSubjects">返回路线 →</button>
    </div>
  </section>
  ` });
  root.appendChild(body);

  const $ = (s) => body.querySelector(s);
  const $$ = (s) => [...body.querySelectorAll(s)];

  function updateGuessTag(lab) {
    const out = $(`[data-guess="${lab}"]`);
    if (!out) return;
    const g = state.guesses[lab];
    out.textContent = !g ? '下次可先做直觉押注再动手！' : (g === state.correctGuess[lab] ? '🎯 直觉押注命中真相！' : '💡 实验反转了刚才的直觉！');
  }

  function updateProgressUI() {
    let n = 0;
    LAB_KEYS.forEach((k, i) => {
      const ok = state.done[k];
      if (ok) n++;
      progressDots[i].classList.toggle('done', ok);
      $(`[data-chk="${k}"]`).classList.toggle('hidden', !ok);
      $(`[data-insight="${k}"]`).classList.toggle('hidden', !ok);
      if (ok) updateGuessTag(k);
    });
    progressText.textContent = `已探索 ${n} / 5`;
  }

  function setTask(name, ok, txt) {
    const t = $(`[data-task="${name}"]`);
    t.classList.toggle('done', ok);
    t.textContent = (ok ? '✓ ' : '○ ') + txt;
  }

  function switchTab(name) {
    state.activeTab = name;
    $$('.el-tab').forEach((b) => b.classList.toggle('active', b.dataset.tab === name));
    $$('[data-pane]').forEach((p) => p.classList.toggle('hidden', p.dataset.pane !== name));
    if (name === 'summary') renderSummary();
    if (name === 'galileo') drawGalileo();
    if (name === 'newton') drawNewton();
    if (name === 'brach') drawBrach();
    if (name === 'centri') drawCentri();
    if (name === 'faraday') drawFaraday();
  }

  $$('.el-tab').forEach((b) => b.addEventListener('click', () => switchTab(b.dataset.tab)));
  $$('[data-goto]').forEach((b) => b.addEventListener('click', () => switchTab(b.dataset.goto)));
  $$('.el-opts').forEach((w) => {
    const lab = w.dataset.lab;
    w.querySelectorAll('.el-opt').forEach((btn) => btn.addEventListener('click', () => {
      state.guesses[lab] = btn.dataset.val;
      w.querySelectorAll('.el-opt').forEach((x) => x.classList.toggle('picked', x === btn));
      updateGuessTag(lab);
    }));
  });

  /* ---- 1. 伽利略斜面 ---- */
  const cGal = $('[data-cv="galileo"]'), ctxG = cGal.getContext('2d');
  const gal = { angle: 18, air: false, running: false, t: 0, maxT: 4.0, lastTs: 0 };
  function checkGal() {
    const t1 = state.tasks.galAngles.size >= 2;
    setTask('gal1', t1, `目标 1：在两个不同倾角释放（${Math.min(2, state.tasks.galAngles.size)}/2）`);
    setTask('gal2', state.tasks.galAirChecked, '目标 2：开启空气阻力对比铁球与羽毛');
    if (t1 && state.tasks.galAirChecked && !state.done.galileo) { state.done.galileo = true; updateProgressUI(); }
  }
  function drawGalileo() {
    const W = cGal.width, H = cGal.height;
    ctxG.clearRect(0, 0, W, H); ctxG.fillStyle = '#fcfaf5'; ctxG.fillRect(0, 0, W, H);
    const rad = gal.angle * Math.PI / 180, L = 520, x0 = 95, yB = 268, y0 = yB - L * Math.sin(rad), x1 = x0 + L * Math.cos(rad);
    ctxG.fillStyle = '#f3e8d8'; ctxG.beginPath(); ctxG.moveTo(x0, y0); ctxG.lineTo(x1, yB); ctxG.lineTo(x0, yB); ctxG.closePath(); ctxG.fill();
    ctxG.strokeStyle = '#5a463a'; ctxG.lineWidth = 4; ctxG.beginPath(); ctxG.moveTo(x0, y0); ctxG.lineTo(x1, yB); ctxG.stroke();
    const aScale = L / 16;
    for (let k = 1; k <= 4; k++) {
      const s = aScale * k * k, mx = x0 + s * Math.cos(rad), my = y0 + s * Math.sin(rad), ok = gal.t >= k;
      ctxG.fillStyle = ok ? '#2563eb' : '#d6c7b2'; ctxG.beginPath(); ctxG.arc(mx, my, ok ? 6 : 4, 0, Math.PI * 2); ctxG.fill();
      ctxG.fillStyle = ok ? '#1e3a8a' : '#9c8b7e'; ctxG.font = FS.small; ctxG.fillText(`${k}s`, mx - 10, my - 18);
    }
    canvasHud(ctxG, { x: 724, y: 14, lh: 32, align: 'right', bg: '#fff', stroke: '#efe4d3', radius: 12, lines: [
      { text: `倾角 ${gal.angle}° · ${gal.air ? '有空气阻力' : '真空无阻力'}`, font: FS.hudSub, color: '#5b5049' },
      { text: '位移比 1 : 3 : 5 : 7', font: FS.hudSub, color: '#2563eb' },
      { text: gal.air ? '羽毛被阻力拖慢' : '铁球与羽毛同步抵达', font: FS.small, color: gal.air ? '#b45309' : '#059669' },
    ] });
    const sI = Math.min(L, aScale * gal.t * gal.t), ix = x0 + sI * Math.cos(rad), iy = y0 + sI * Math.sin(rad) - 11;
    const sF = gal.air ? Math.min(L, L * 0.42 * (1 - Math.exp(-gal.t * 0.75)) + 26 * gal.t) : sI;
    const fx = x0 + Math.min(L, sF) * Math.cos(rad), fy = y0 + Math.min(L, sF) * Math.sin(rad) - 28;
    ctxG.fillStyle = '#2563eb'; ctxG.beginPath(); ctxG.arc(ix, iy, 10, 0, Math.PI * 2); ctxG.fill();
    ctxG.fillStyle = '#1e3a8a'; ctxG.font = FS.small; ctxG.fillText('铁球', ix + 14, iy + 6);
    ctxG.save(); ctxG.translate(fx, fy); ctxG.rotate(rad - 0.15 + (gal.air && gal.running ? Math.sin(gal.t * 6) * 0.2 : 0));
    ctxG.fillStyle = '#f59e0b'; ctxG.beginPath(); ctxG.ellipse(0, 0, 14, 5, 0, 0, Math.PI * 2); ctxG.fill(); ctxG.restore();
    ctxG.fillStyle = '#8c7b70'; ctxG.font = FS.small; ctxG.fillText(`计时 ${gal.t.toFixed(2)} s`, 24, 300);
  }
  function stepGal(ts) {
    if (disposed) return;
    if (!gal.lastTs) gal.lastTs = ts;
    gal.t = Math.min(gal.maxT, gal.t + Math.min(0.05, (ts - gal.lastTs) / 1000) * 1.45);
    gal.lastTs = ts; drawGalileo();
    if (gal.t < gal.maxT && gal.running) rafs.gal = requestAnimationFrame(stepGal);
    else { gal.running = false; state.tasks.galAngles.add(gal.angle); if (gal.air) state.tasks.galAirChecked = true; checkGal(); }
  }
  $('[data-in="galAngle"]').addEventListener('input', (e) => { gal.angle = Number(e.target.value); $('[data-out="galAngle"]').textContent = `${gal.angle}°`; cancelAnimationFrame(rafs.gal); gal.running = false; gal.t = 0; drawGalileo(); });
  // 释放即记账：不等小球跑到终点，改倾角后立刻重放也能累计到两个不同倾角。
  $('[data-act="galRun"]').addEventListener('click', () => {
    state.tasks.galAngles.add(gal.angle);
    if (gal.air) state.tasks.galAirChecked = true;
    checkGal();
    cancelAnimationFrame(rafs.gal); gal.t = 0; gal.lastTs = 0; gal.running = true; rafs.gal = requestAnimationFrame(stepGal);
  });
  $('[data-act="galVacuum"]').addEventListener('click', (e) => { gal.air = !gal.air; e.currentTarget.textContent = gal.air ? '当前：开启空气阻力' : '当前：真空无阻力'; if (gal.air) state.tasks.galAirChecked = true; checkGal(); cancelAnimationFrame(rafs.gal); gal.t = 0; gal.lastTs = 0; gal.running = true; rafs.gal = requestAnimationFrame(stepGal); });
  $('[data-act="galReset"]').addEventListener('click', () => { cancelAnimationFrame(rafs.gal); gal.running = false; gal.t = 0; drawGalileo(); });

  /* ---- 2. 牛顿大炮 ---- */
  const cNew = $('[data-cv="newton"]'), ctxN = cNew.getContext('2d');
  const nSim = { v0: 5.0, R: 86, cx: 360, cy: 178, mountH: 20, trails: [], active: null, status: '拖动初速度并点击「开炮发射」' };
  function checkNewt() {
    setTask('new1', state.tasks.newFall, '目标 1：低速开炮看炮弹落地');
    setTask('new2', state.tasks.newOrbit, '目标 2：调到 ≥ 7.9 km/s 发射绕地卫星');
    if (state.tasks.newFall && state.tasks.newOrbit && !state.done.newton) { state.done.newton = true; updateProgressUI(); }
  }
  function drawNewton() {
    const W = cNew.width, H = cNew.height;
    ctxN.clearRect(0, 0, W, H); ctxN.fillStyle = '#0f172a'; ctxN.fillRect(0, 0, W, H);
    const g = ctxN.createRadialGradient(nSim.cx - 26, nSim.cy - 26, 12, nSim.cx, nSim.cy, nSim.R);
    g.addColorStop(0, '#60a5fa'); g.addColorStop(0.65, '#2563eb'); g.addColorStop(1, '#1e3a8a');
    ctxN.fillStyle = g; ctxN.beginPath(); ctxN.arc(nSim.cx, nSim.cy, nSim.R, 0, Math.PI * 2); ctxN.fill();
    ctxN.fillStyle = '#a8a29e'; ctxN.beginPath(); ctxN.moveTo(nSim.cx - 12, nSim.cy - nSim.R + 2); ctxN.lineTo(nSim.cx, nSim.cy - nSim.R - nSim.mountH); ctxN.lineTo(nSim.cx + 12, nSim.cy - nSim.R + 2); ctxN.closePath(); ctxN.fill();
    nSim.trails.forEach((tr) => { ctxN.strokeStyle = tr.color; ctxN.lineWidth = 2; ctxN.beginPath(); tr.pts.forEach((p, i) => (i ? ctxN.lineTo(p.x, p.y) : ctxN.moveTo(p.x, p.y))); ctxN.stroke(); });
    if (nSim.active) {
      const a = nSim.active;
      ctxN.strokeStyle = a.color; ctxN.lineWidth = 2.6; ctxN.beginPath(); a.pts.forEach((p, i) => (i ? ctxN.lineTo(p.x, p.y) : ctxN.moveTo(p.x, p.y))); ctxN.stroke();
      ctxN.fillStyle = '#fde047'; ctxN.beginPath(); ctxN.arc(a.x, a.y, 5.5, 0, Math.PI * 2); ctxN.fill();
    }
    canvasHud(ctxN, { x: 14, y: 10, lh: 32, bg: 'rgba(15,23,42,.85)', lines: [
      { text: `v₀ = ${nSim.v0.toFixed(1)} km/s`, font: FS.hud, color: '#e2e8f0' },
      { text: nSim.status, font: FS.small, color: '#fcd34d' },
    ] });
  }
  function fireCannon() {
    cancelAnimationFrame(rafs.newt);
    if (nSim.active) { nSim.trails.push({ pts: nSim.active.pts, color: 'rgba(148,163,184,.45)' }); if (nSim.trails.length > 5) nSim.trails.shift(); }
    const r0 = nSim.R + nSim.mountH, GM = 7.9 * 7.9 * r0;
    const color = nSim.v0 < 7.85 ? '#f97316' : nSim.v0 < 11.1 ? '#34d399' : '#38bdf8';
    nSim.active = { x: nSim.cx, y: nSim.cy - r0, vx: nSim.v0, vy: 0, pts: [{ x: nSim.cx, y: nSim.cy - r0 }], steps: 0, color, GM, swept: 0, prevAng: -Math.PI / 2 };
    nSim.status = '炮弹飞行中...';
    const step = () => {
      if (disposed || !nSim.active) return;
      const a = nSim.active;
      for (let sub = 0; sub < 4; sub++) {
        const dx = a.x - nSim.cx, dy = a.y - nSim.cy, dist = Math.hypot(dx, dy);
        if (dist <= nSim.R) { nSim.status = '💥 速度不够，落回地球表面！'; state.tasks.newFall = true; checkNewt(); drawNewton(); return; }
        if (dist > 390) { nSim.status = '🚀 超过第二宇宙速度，挣脱地球！'; state.tasks.newOrbit = true; checkNewt(); drawNewton(); return; }
        const dt = 0.22, acc = -a.GM / (dist * dist * dist);
        a.vx += acc * dx * dt; a.vy += acc * dy * dt; a.x += a.vx * dt; a.y += a.vy * dt;
        let dAng = Math.atan2(a.y - nSim.cy, a.x - nSim.cx) - a.prevAng;
        if (dAng > Math.PI) dAng -= 2 * Math.PI;
        if (dAng < -Math.PI) dAng += 2 * Math.PI;
        a.swept += Math.abs(dAng); a.prevAng = Math.atan2(a.y - nSim.cy, a.x - nSim.cx);
      }
      a.pts.push({ x: a.x, y: a.y }); a.steps++;
      if (a.swept >= Math.PI * 2.02) { nSim.status = '🛰️ 成功入轨！永远在下落却永不落地！'; state.tasks.newOrbit = true; checkNewt(); drawNewton(); return; }
      drawNewton();
      if (a.steps < 520) rafs.newt = requestAnimationFrame(step);
    };
    rafs.newt = requestAnimationFrame(step);
  }
  $('[data-in="newSpeed"]').addEventListener('input', (e) => { nSim.v0 = Number(e.target.value); $('[data-out="newSpeed"]').textContent = `${nSim.v0.toFixed(1)} km/s`; drawNewton(); });
  $('[data-act="newFire"]').addEventListener('click', fireCannon);
  $('[data-act="newClear"]').addEventListener('click', () => { cancelAnimationFrame(rafs.newt); nSim.trails = []; nSim.active = null; nSim.status = '已清空轨迹'; drawNewton(); });

  /* ---- 3. 最速曲线 ---- */
  const cBr = $('[data-cv="brach"]'), ctxB = cBr.getContext('2d');
  const BR = { x0: 155, y0: 52, R: 112, mode: 'race', running: false, t: 0, lastTs: 0, g: 420 };
  BR.x1 = BR.x0 + Math.PI * BR.R; BR.y1 = BR.y0 + 2 * BR.R;
  function buildTrack(fn, n = 220) {
    const pts = []; let tAcc = 0;
    for (let i = 0; i <= n; i++) {
      const p = fn(i / n);
      if (i > 0) {
        const pr = pts[i - 1], ds = Math.hypot(p.x - pr.x, p.y - pr.y);
        tAcc += ds / Math.sqrt(2 * BR.g * Math.max(0.5, (pr.y + p.y) / 2 - BR.y0));
      }
      pts.push({ x: p.x, y: p.y, t: tAcc });
    }
    return pts;
  }
  const tCyc = buildTrack((u) => { const th = u * Math.PI; return { x: BR.x0 + BR.R * (th - Math.sin(th)), y: BR.y0 + BR.R * (1 - Math.cos(th)) }; });
  const tLin = buildTrack((u) => ({ x: BR.x0 + u * (BR.x1 - BR.x0), y: BR.y0 + u * (BR.y1 - BR.y0) }));
  const tDep = buildTrack((u) => ({ x: BR.x0 + (BR.x1 - BR.x0) * Math.pow(u, 2.2), y: BR.y0 + (BR.y1 - BR.y0) * (1 - Math.pow(1 - u, 3.2)) }));
  function sampleTrack(tbl, t) {
    if (t <= 0) return { ...tbl[0], done: false };
    const last = tbl[tbl.length - 1];
    if (t >= last.t) return { ...last, done: true };
    let lo = 0, hi = tbl.length - 1;
    while (lo + 1 < hi) { const m = (lo + hi) >> 1; if (tbl[m].t <= t) lo = m; else hi = m; }
    const a = tbl[lo], b = tbl[hi], f = (t - a.t) / Math.max(1e-6, b.t - a.t);
    return { x: a.x + (b.x - a.x) * f, y: a.y + (b.y - a.y) * f, done: false };
  }
  function sampleTauto(th0, t) {
    const om = Math.sqrt(BR.g / (4 * BR.R)), T = (Math.PI / 2) / om;
    const th = 2 * Math.acos(Math.max(0, Math.min(1, Math.cos(th0 / 2) * Math.cos(om * Math.min(t, T)))));
    return { x: BR.x0 + BR.R * (th - Math.sin(th)), y: BR.y0 + BR.R * (1 - Math.cos(th)), done: t >= T, T };
  }
  function checkBrach() {
    setTask('brach1', state.tasks.brachRace, '目标 1：跑完三轨竞速看摆线反超直线');
    setTask('brach2', state.tasks.brachTauto, '目标 2：切换「等时性对比」看高低两球同时撞线');
    if (state.tasks.brachRace && state.tasks.brachTauto && !state.done.brach) { state.done.brach = true; updateProgressUI(); }
  }
  function drawBrach() {
    const W = cBr.width, H = cBr.height;
    ctxB.clearRect(0, 0, W, H); ctxB.fillStyle = '#fcfaf5'; ctxB.fillRect(0, 0, W, H);
    const drawLine = (tbl, c, w) => { ctxB.strokeStyle = c; ctxB.lineWidth = w; ctxB.beginPath(); tbl.forEach((p, i) => (i ? ctxB.lineTo(p.x, p.y) : ctxB.moveTo(p.x, p.y))); ctxB.stroke(); };
    if (BR.mode === 'race') {
      drawLine(tLin, '#f97316', 3); drawLine(tDep, '#94a3b8', 3); drawLine(tCyc, '#2563eb', 4);
      const pC = sampleTrack(tCyc, BR.t), pL = sampleTrack(tLin, BR.t), pD = sampleTrack(tDep, BR.t);
      [{ p: pL, c: '#f97316', l: '直' }, { p: pD, c: '#64748b', l: '陡' }, { p: pC, c: '#2563eb', l: '摆' }].forEach(({ p, c, l }) => {
        ctxB.fillStyle = c; ctxB.beginPath(); ctxB.arc(p.x, p.y, 10, 0, Math.PI * 2); ctxB.fill();
        ctxB.fillStyle = c; ctxB.font = FS.label; ctxB.fillText(l, p.x + 13, p.y + 6);
      });
      canvasHud(ctxB, { x: 724, y: 14, lh: 30, align: 'right', bg: '#fff', stroke: '#efe4d3', lines: [
        { text: `计时 ${BR.t.toFixed(2)} s`, font: FS.hudSub, color: '#5b5049' },
        { text: `● 摆线 ${pC.done ? tCyc[tCyc.length - 1].t.toFixed(2) + 's 🏆' : '滑行中…'}`, font: FS.small, color: '#2563eb' },
        { text: `● 直线 ${pL.done ? tLin[tLin.length - 1].t.toFixed(2) + 's' : '滑行中…'}`, font: FS.small, color: '#ea580c' },
        { text: `● 深弯 ${pD.done ? tDep[tDep.length - 1].t.toFixed(2) + 's' : '滑行中…'}`, font: FS.small, color: '#64748b' },
      ] });
    } else {
      drawLine(tCyc, '#2563eb', 4);
      const pH = sampleTauto(0.05, BR.t), pM = sampleTauto(1.45, BR.t);
      [{ p: pH, c: '#2563eb', l: '高' }, { p: pM, c: '#059669', l: '低' }].forEach(({ p, c, l }) => {
        ctxB.fillStyle = c; ctxB.beginPath(); ctxB.arc(p.x, p.y, 10, 0, Math.PI * 2); ctxB.fill();
        ctxB.fillStyle = c; ctxB.font = FS.label; ctxB.fillText(l, p.x + 13, p.y + 6);
      });
      canvasHud(ctxB, { x: 724, y: 14, lh: 32, align: 'right', bg: '#fff', stroke: '#efe4d3', lines: [
        { text: `计时 ${BR.t.toFixed(2)} s（等时性）`, font: FS.hudSub, color: '#5b5049' },
        { text: pH.done ? `✨ 同时撞线 ${pH.T.toFixed(2)} s` : '两球同向谷底滑行…', font: FS.small, color: '#059669' },
      ] });
    }
  }
  function stepBrach(ts) {
    if (disposed) return;
    if (!BR.lastTs) BR.lastTs = ts;
    BR.t += Math.min(0.05, (ts - BR.lastTs) / 1000); BR.lastTs = ts; drawBrach();
    const maxT = BR.mode === 'race' ? Math.max(tLin[tLin.length - 1].t, tDep[tDep.length - 1].t) + 0.05 : sampleTauto(0.05, 0).T + 0.05;
    if (BR.t < maxT && BR.running) rafs.brach = requestAnimationFrame(stepBrach);
    else { BR.running = false; if (BR.mode === 'race') state.tasks.brachRace = true; else state.tasks.brachTauto = true; checkBrach(); drawBrach(); }
  }
  $('[data-act="brachRun"]').addEventListener('click', () => { cancelAnimationFrame(rafs.brach); BR.t = 0; BR.lastTs = 0; BR.running = true; rafs.brach = requestAnimationFrame(stepBrach); });
  $('[data-act="brachMode"]').addEventListener('click', (e) => { cancelAnimationFrame(rafs.brach); BR.mode = BR.mode === 'race' ? 'tauto' : 'race'; e.currentTarget.textContent = BR.mode === 'race' ? '当前：三轨竞速' : '当前：等时性对比'; BR.t = 0; BR.lastTs = 0; BR.running = true; rafs.brach = requestAnimationFrame(stepBrach); });
  $('[data-act="brachReset"]').addEventListener('click', () => { cancelAnimationFrame(rafs.brach); BR.running = false; BR.t = 0; drawBrach(); });

  /* ---- 4. 向心力与离心 ---- */
  const cCen = $('[data-cv="centri"]'), ctxC = cCen.getContext('2d');
  const CEN = { cx: 325, cy: 168, r: 96, omega: 2.4, angle: 0, cut: false, rot: false, bx: 421, by: 168, vx: 0, vy: 0, cutPt: null, cutAng: 0, trail: [], lastTs: 0 };
  function checkCentri() {
    setTask('centri1', state.tasks.centriCut, '目标 1：剪断或拉断绳子，观察切线飞出');
    setTask('centri2', state.tasks.centriFrame, '目标 2：切换一次「随动转盘视角」');
    if (state.tasks.centriCut && state.tasks.centriFrame && !state.done.centri) { state.done.centri = true; updateProgressUI(); }
  }
  function cutString() {
    if (CEN.cut) return;
    CEN.cut = true; CEN.cutAng = CEN.angle;
    CEN.bx = CEN.cx + Math.cos(CEN.angle) * CEN.r; CEN.by = CEN.cy + Math.sin(CEN.angle) * CEN.r;
    CEN.vx = -Math.sin(CEN.angle) * CEN.omega * CEN.r; CEN.vy = Math.cos(CEN.angle) * CEN.omega * CEN.r;
    CEN.cutPt = { x: CEN.bx, y: CEN.by }; CEN.trail = [{ x: CEN.bx, y: CEN.by }];
    state.tasks.centriCut = true; checkCentri();
  }
  function arrow(ctx, x1, y1, x2, y2, color, lbl) {
    const a = Math.atan2(y2 - y1, x2 - x1);
    ctx.strokeStyle = color; ctx.fillStyle = color; ctx.lineWidth = 2.5;
    ctx.beginPath(); ctx.moveTo(x1, y1); ctx.lineTo(x2, y2); ctx.stroke();
    ctx.beginPath(); ctx.moveTo(x2, y2); ctx.lineTo(x2 - 8 * Math.cos(a - 0.4), y2 - 8 * Math.sin(a - 0.4)); ctx.lineTo(x2 - 8 * Math.cos(a + 0.4), y2 - 8 * Math.sin(a + 0.4)); ctx.closePath(); ctx.fill();
    if (lbl) { ctx.font = FS.label; ctx.fillText(lbl, x2 + 6, y2 + 6); }
  }
  function drawCentri() {
    const W = cCen.width, H = cCen.height;
    ctxC.clearRect(0, 0, W, H); ctxC.fillStyle = '#fcfaf5'; ctxC.fillRect(0, 0, W, H);
    ctxC.save();
    if (CEN.rot) { ctxC.translate(CEN.cx, CEN.cy); ctxC.rotate(-CEN.angle); ctxC.translate(-CEN.cx, -CEN.cy); }
    ctxC.fillStyle = '#f5eee2'; ctxC.strokeStyle = '#dfd0b8'; ctxC.lineWidth = 2; ctxC.beginPath(); ctxC.arc(CEN.cx, CEN.cy, CEN.r + 22, 0, Math.PI * 2); ctxC.fill(); ctxC.stroke();
    ctxC.strokeStyle = 'rgba(140,123,112,.25)'; ctxC.lineWidth = 1.5;
    for (let k = 0; k < 6; k++) { const a = k * Math.PI / 3 + (CEN.rot ? 0 : CEN.angle); ctxC.beginPath(); ctxC.moveTo(CEN.cx, CEN.cy); ctxC.lineTo(CEN.cx + Math.cos(a) * (CEN.r + 20), CEN.cy + Math.sin(a) * (CEN.r + 20)); ctxC.stroke(); }
    ctxC.fillStyle = '#5a463a'; ctxC.beginPath(); ctxC.arc(CEN.cx, CEN.cy, 6, 0, Math.PI * 2); ctxC.fill();
    if (!CEN.cut) {
      const bx = CEN.cx + Math.cos(CEN.angle) * CEN.r, by = CEN.cy + Math.sin(CEN.angle) * CEN.r;
      const ratio = Math.min(1, (CEN.omega * CEN.omega) / (4.8 * 4.8));
      ctxC.strokeStyle = ratio > 0.78 ? '#dc2626' : '#5a463a'; ctxC.lineWidth = 2.5 + ratio * 2;
      ctxC.beginPath(); ctxC.moveTo(CEN.cx, CEN.cy); ctxC.lineTo(bx, by); ctxC.stroke();
      const fLen = 24 + ratio * 46;
      arrow(ctxC, bx, by, bx - Math.cos(CEN.angle) * fLen, by - Math.sin(CEN.angle) * fLen, '#2563eb', 'F向');
      arrow(ctxC, bx, by, bx - Math.sin(CEN.angle) * (28 + CEN.omega * 8), by + Math.cos(CEN.angle) * (28 + CEN.omega * 8), '#059669', 'v切线');
      if (CEN.rot) { ctxC.setLineDash([4, 3]); arrow(ctxC, bx, by, bx + Math.cos(CEN.angle) * fLen, by + Math.sin(CEN.angle) * fLen, '#b45309', '体感甩出'); ctxC.setLineDash([]); }
      ctxC.fillStyle = '#2563eb'; ctxC.beginPath(); ctxC.arc(bx, by, 11, 0, Math.PI * 2); ctxC.fill();
    } else {
      if (CEN.cutPt) {
        const rx = CEN.cutPt.x + Math.cos(CEN.cutAng) * 105, ry = CEN.cutPt.y + Math.sin(CEN.cutAng) * 105;
        ctxC.strokeStyle = 'rgba(220,38,38,.45)'; ctxC.setLineDash([5, 4]); ctxC.lineWidth = 2;
        ctxC.beginPath(); ctxC.moveTo(CEN.cutPt.x, CEN.cutPt.y); ctxC.lineTo(rx, ry); ctxC.stroke(); ctxC.setLineDash([]);
      }
      ctxC.strokeStyle = '#059669'; ctxC.lineWidth = 3; ctxC.beginPath(); CEN.trail.forEach((p, i) => (i ? ctxC.lineTo(p.x, p.y) : ctxC.moveTo(p.x, p.y))); ctxC.stroke();
      ctxC.fillStyle = '#059669'; ctxC.beginPath(); ctxC.arc(CEN.bx, CEN.by, 11, 0, Math.PI * 2); ctxC.fill();
    }
    ctxC.restore();
    canvasHud(ctxC, { x: 724, y: 14, lh: 32, align: 'right', bg: '#fff', stroke: '#efe4d3', lines: [
      { text: CEN.rot ? '视角：随动转盘内' : '视角：地面观察者', font: FS.small, color: '#5b5049' },
      { text: `向心力 F ≈ ${CEN.cut ? '0.0' : (CEN.omega * CEN.omega * 0.96).toFixed(1)} N`, font: FS.hudSub, color: '#2563eb' },
      { text: '细绳极限 22.0 N', font: FS.small, color: '#8c7b70' },
      { text: CEN.cut ? '✓ 沿切线飞出' : '可剪断或提速拉断', font: FS.small, color: CEN.cut ? '#059669' : '#5b5049' },
    ] });
  }
  function stepCentri(ts) {
    if (disposed) return;
    if (!CEN.lastTs) CEN.lastTs = ts;
    const dt = Math.min(0.05, (ts - CEN.lastTs) / 1000); CEN.lastTs = ts;
    if (!CEN.cut) { CEN.angle += CEN.omega * dt; if (CEN.omega >= 4.8) cutString(); }
    else { CEN.bx += CEN.vx * dt; CEN.by += CEN.vy * dt; if (CEN.trail.length < 180) CEN.trail.push({ x: CEN.bx, y: CEN.by }); }
    if (state.activeTab === 'centri') drawCentri();
    rafs.centri = requestAnimationFrame(stepCentri);
  }
  $('[data-in="centriOmega"]').addEventListener('input', (e) => { CEN.omega = Number(e.target.value); $('[data-out="centriOmega"]').textContent = `${CEN.omega.toFixed(1)} rad/s`; });
  $('[data-act="centriCut"]').addEventListener('click', cutString);
  $('[data-act="centriFrame"]').addEventListener('click', (e) => { CEN.rot = !CEN.rot; e.currentTarget.textContent = CEN.rot ? '视角：随动转盘内' : '视角：地面观察者'; state.tasks.centriFrame = true; checkCentri(); drawCentri(); });
  $('[data-act="centriReset"]').addEventListener('click', () => { CEN.cut = false; if (CEN.omega >= 4.8) { CEN.omega = 2.4; $('[data-in="centriOmega"]').value = '2.4'; $('[data-out="centriOmega"]').textContent = '2.4 rad/s'; } CEN.trail = []; CEN.cutPt = null; drawCentri(); });

  /* ---- 5. 法拉第磁生电 ---- */
  const cFar = $('[data-cv="faraday"]'), ctxF = cFar.getContext('2d');
  const farPosEl = $('[data-in="farPos"]'), farEmfOut = $('[data-out="farEmf"]');
  const far = { x: 150, prevX: 150, emf: 0, drag: false, stopFrames: 0 };
  function checkFar() {
    setTask('far1', state.tasks.farIn, '目标 1：插入线圈点亮灯泡');
    setTask('far2', state.tasks.farStop, '目标 2：在线圈内停住看熄灭');
    setTask('far3', state.tasks.farOut, '目标 3：快速拔出看指针反偏');
    if (state.tasks.farIn && state.tasks.farStop && state.tasks.farOut && !state.done.faraday) { state.done.faraday = true; updateProgressUI(); }
  }
  function drawFaraday() {
    const W = cFar.width, H = cFar.height;
    ctxF.clearRect(0, 0, W, H); ctxF.fillStyle = '#fcfaf5'; ctxF.fillRect(0, 0, W, H);
    const coilX = 350, coilY = 175, coilW = 130, coilH = 74, magW = 110, magH = 38, magY = coilY + coilH / 2 - magH / 2;
    ctxF.strokeStyle = '#92400e'; ctxF.lineWidth = 3;
    ctxF.beginPath(); ctxF.moveTo(coilX + 16, coilY); ctxF.lineTo(coilX + 16, 68); ctxF.lineTo(295, 68); ctxF.moveTo(coilX + coilW - 16, coilY); ctxF.lineTo(coilX + coilW - 16, 68); ctxF.lineTo(545, 68); ctxF.stroke();
    const bright = Math.min(1, Math.abs(far.emf) / 3.2);
    if (bright > 0.05) {
      const g = ctxF.createRadialGradient(260, 68, 4, 260, 68, 48 * bright + 12);
      g.addColorStop(0, `rgba(250,204,21,${0.85 * bright})`); g.addColorStop(1, 'rgba(250,204,21,0)');
      ctxF.fillStyle = g; ctxF.beginPath(); ctxF.arc(260, 68, 48 * bright + 12, 0, Math.PI * 2); ctxF.fill();
    }
    ctxF.fillStyle = bright > 0.08 ? `rgba(253,224,71,${0.35 + 0.65 * bright})` : '#e5e7eb';
    ctxF.strokeStyle = '#78716c'; ctxF.lineWidth = 2; ctxF.beginPath(); ctxF.arc(260, 68, 22, 0, Math.PI * 2); ctxF.fill(); ctxF.stroke();
    ctxF.fillStyle = '#5b5049'; ctxF.font = FS.small; ctxF.fillText(bright > 0.12 ? '💡 灯泡亮了' : '熄灭', 226, 116);
    ctxF.fillStyle = '#fff'; ctxF.strokeStyle = '#d6c2a8'; ctxF.beginPath(); ctxF.arc(590, 68, 36, 0, Math.PI * 2); ctxF.fill(); ctxF.stroke();
    const ang = Math.max(-1.1, Math.min(1.1, far.emf * 0.32));
    ctxF.strokeStyle = '#dc2626'; ctxF.lineWidth = 2.5; ctxF.beginPath(); ctxF.moveTo(590, 74); ctxF.lineTo(590 + Math.sin(ang) * 28, 74 - Math.cos(ang) * 28); ctxF.stroke();
    ctxF.strokeStyle = '#d97706'; ctxF.lineWidth = 5;
    for (let i = 0; i < 6; i++) { ctxF.beginPath(); ctxF.ellipse(coilX + 12 + i * 21, coilY + coilH / 2, 10, coilH / 2, 0, Math.PI * 0.5, Math.PI * 1.5); ctxF.stroke(); }
    ctxF.fillStyle = '#2563eb'; ctxF.fillRect(far.x - magW / 2, magY, magW / 2, magH);
    ctxF.fillStyle = '#dc2626'; ctxF.fillRect(far.x, magY, magW / 2, magH);
    ctxF.fillStyle = '#fff'; ctxF.font = FS.label; ctxF.fillText('S', far.x - magW / 4 - 6, magY + 26); ctxF.fillText('N', far.x + magW / 4 - 8, magY + 26);
    ctxF.strokeStyle = '#b45309'; ctxF.lineWidth = 5;
    for (let i = 0; i < 6; i++) { ctxF.beginPath(); ctxF.ellipse(coilX + 12 + i * 21, coilY + coilH / 2, 10, coilH / 2, 0, -Math.PI * 0.5, Math.PI * 0.5); ctxF.stroke(); }
  }
  function stepFar() {
    if (disposed) return;
    const vx = far.x - far.prevX; far.prevX = far.x;
    const u = (far.x - 415) / 85, raw = vx * (-2 * u * Math.exp(-u * u)) * 1.35;
    far.emf = far.emf * 0.72 + raw * 0.28;
    if (Math.abs(far.emf) < 0.03 && Math.abs(vx) < 0.2) far.emf = 0;
    if (far.x > 310 && far.x < 480) {
      if (far.emf > 0.7) state.tasks.farIn = true;
      if (Math.abs(vx) < 0.4 && Math.abs(far.emf) < 0.15) { far.stopFrames++; if (far.stopFrames > 18 && state.tasks.farIn) state.tasks.farStop = true; }
      else far.stopFrames = 0;
    }
    if (far.emf < -0.7) state.tasks.farOut = true;
    checkFar();
    farEmfOut.textContent = `${far.emf >= 0 ? '+' : ''}${far.emf.toFixed(1)} V`;
    if (state.activeTab === 'faraday') drawFaraday();
    rafs.far = requestAnimationFrame(stepFar);
  }
  const ptrX = (e) => { const r = cFar.getBoundingClientRect(); return Math.max(110, Math.min(530, (e.clientX - r.left) * (cFar.width / r.width))); };
  cFar.addEventListener('pointerdown', (e) => { far.drag = true; cFar.setPointerCapture(e.pointerId); far.x = ptrX(e); farPosEl.value = Math.round(far.x); });
  cFar.addEventListener('pointermove', (e) => { if (!far.drag) return; far.x = ptrX(e); farPosEl.value = Math.round(far.x); });
  cFar.addEventListener('pointerup', () => { far.drag = false; });
  farPosEl.addEventListener('input', () => { far.x = Number(farPosEl.value); });
  $('[data-act="farDemo"]').addEventListener('click', () => {
    cancelAnimationFrame(rafs.farDemo);
    let s = 0;
    const anim = () => {
      if (disposed) return;
      s++;
      if (s < 45) far.x = 150 + (s / 45) * 265;
      else if (s < 95) far.x = 415;
      else if (s < 140) far.x = 415 - ((s - 95) / 45) * 265;
      else return;
      farPosEl.value = Math.round(far.x);
      rafs.farDemo = requestAnimationFrame(anim);
    };
    rafs.farDemo = requestAnimationFrame(anim);
  });

  /* ---- 全景总结 ---- */
  function renderSummary() {
    const doneCount = LAB_KEYS.filter((k) => state.done[k]).length;
    const hitCount = LAB_KEYS.filter((k) => state.guesses[k] && state.guesses[k] === state.correctGuess[k]).length;
    $('[data-sum="done"]').textContent = `${doneCount} / 5`;
    $('[data-sum="hit"]').textContent = `${hitCount} / 5`;
    $('[data-sum="title"]').textContent = doneCount === 5 ? '🏆 恭喜完成全部探索！你的物理学破局档案' : `探索进行中：已完成 ${doneCount} / 5 场实验`;
    const items = [
      { k: 'galileo', t: '1604 · 伽利略斜面', p: '“靠纯逻辑就能推翻权威；把下落变慢，才能看清时间的刻度。”', s: '确立现代实验科学方法。' },
      { k: 'newton', t: '1687 · 牛顿大炮', p: '“苹果落地和月亮绕地球，本质上是一回事。”', s: '奠定工业力学与人造卫星轨道工程。' },
      { k: 'brach', t: '1696 · 伯努利最速曲线', p: '“两点之间直线最短，但最快到达的不是直线——先俯冲蓄能，才能后发先至。”', s: '催生变分法，支撑航天最优轨道设计。' },
      { k: 'centri', t: '1659 · 惠更斯向心力与断绳', p: '“根本没有把你往外拉的‘离心力’——那只是物体想按惯性走直线。”', s: '应用于洗衣机脱水、医用离心机与高速弯道。' },
      { k: 'faraday', t: '1831 · 法拉第磁生电', p: '“不是磁场生电，而是磁场的‘变化’在生电。”', s: '直接催生发电机与现代电网。' },
    ];
    $('[data-sum="list"]').innerHTML = items.map((it) => {
      const ok = state.done[it.k];
      return `<div class="el-recap"><div style="font-size:13.5px;font-weight:800">${ok ? '✅ ' : '🔒 '}${it.t}</div><div style="font-size:12.5px;font-weight:700;margin-top:3px">${ok ? it.p : '完成该实验探索后解锁'}</div><div style="font-size:12px;color:var(--ink-2);margin-top:2px">${ok ? it.s : ''}</div></div>`;
    }).join('');
  }

  $('[data-act="resetAll"]').addEventListener('click', () => {
    LAB_KEYS.forEach((k) => { state.guesses[k] = null; state.done[k] = false; });
    state.tasks = { galAngles: new Set(), galAirChecked: false, newFall: false, newOrbit: false, brachRace: false, brachTauto: false, centriCut: false, centriFrame: false, farIn: false, farStop: false, farOut: false };
    $$('.el-opt').forEach((b) => b.classList.remove('picked'));
    checkGal(); checkNewt(); checkBrach(); checkCentri(); checkFar(); updateProgressUI(); renderSummary(); switchTab('galileo');
  });
  $('[data-act="backSubjects"]').addEventListener('click', () => navigate('#/subjects'));

  view.innerHTML = '';
  view.appendChild(root);

  checkGal(); checkNewt(); checkBrach(); checkCentri(); checkFar();
  updateProgressUI();
  drawGalileo(); drawNewton(); drawBrach(); drawCentri(); drawFaraday();
  rafs.centri = requestAnimationFrame(stepCentri);
  rafs.far = requestAnimationFrame(stepFar);
  mountLabBonus(root, '.el-tabs');

  return () => {
    disposed = true;
    Object.values(rafs).forEach((id) => cancelAnimationFrame(id));
  };
}
