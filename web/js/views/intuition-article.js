/* 长文专题：数学与物理直觉思维的养成（含原创 SVG 插图与 A4 打印排版） */

import { el } from '../ui.js';
import { navigate } from '../router.js';
import { COLUMN, essayBySlug, essayNeighbors, countChars } from '../essays.js';

const ARTICLE_CSS = `
.ig-wrap{display:flex;flex-direction:column;gap:14px}
.ig-doc{background:#fff;border:1px solid var(--line);border-radius:18px;padding:24px 22px 30px;color:#2f2a26;line-height:1.85;font-size:15px}
.ig-doc h2{font-size:21px;font-weight:900;margin:28px 0 12px;color:#1e293b;padding-bottom:6px;border-bottom:2px solid #f1e6d6;line-height:1.35}
.ig-doc h2:first-of-type{margin-top:16px}
.ig-doc h3{font-size:16px;font-weight:800;margin:18px 0 8px;color:#334155}
.ig-doc p{margin:0 0 13px;color:#3f3a36}
.ig-doc ul,.ig-doc ol{margin:0 0 14px;padding-left:22px;color:#3f3a36}
.ig-doc li{margin-bottom:7px}
.ig-doc code{font-family:ui-monospace,SFMono-Regular,Menlo,monospace;font-size:13px;background:#f8f3eb;color:#1e3a8a;padding:1px 5px;border-radius:5px}
.ig-hero{padding-bottom:18px;border-bottom:1px solid #efe4d3;margin-bottom:8px}
.ig-kicker{font-size:12px;font-weight:800;color:#2563eb;letter-spacing:.06em;margin-bottom:6px}
.ig-title{margin:0 0 10px;font-size:26px;font-weight:900;line-height:1.25;color:#111827}
.ig-lead{margin:0;font-size:14.5px;color:#64748b;line-height:1.75}
.ig-quote{margin:16px 0;padding:13px 16px;border-left:4px solid #2563eb;background:#f8fafc;border-radius:0 12px 12px 0;font-size:14.5px;font-weight:700;color:#1e293b}
.ig-fig{margin:18px 0;padding:14px;border:1px solid #efe4d3;border-radius:14px;background:#fcfaf5;break-inside:avoid}
.ig-fig svg{display:block;width:100%;height:auto}
.ig-cap{margin-top:8px;font-size:12px;color:#78716c;text-align:center}
.ig-box{margin:16px 0;padding:15px 16px;border-radius:14px;background:linear-gradient(135deg,#fffbeb 0%,#f0fdf4 100%);border:1px solid #fde68a;break-inside:avoid}
.ig-box h3{margin-top:0;color:#92400e}
.ig-appendix{margin-top:26px;padding:18px;border-radius:16px;background:#f8fafc;border:1px solid #cbd5e1;break-inside:avoid}
.ig-appendix h2{margin-top:0;border-bottom-color:#cbd5e1;color:#1e3a8a}
.ig-crumb{display:flex;gap:6px;align-items:center;font-size:11.5px;font-weight:700;color:#a3928a;padding:0 3px}
.ig-crumb b{color:#b45309;font-weight:900}
.ig-meta{display:flex;gap:7px;flex-wrap:wrap;align-items:center;font-size:11px;color:#a3928a;padding:0 3px}
.ig-meta .sep{width:3px;height:3px;border-radius:50%;background:#d9c8b4}
.ig-toc{display:flex;gap:6px;flex-wrap:wrap;padding:2px 3px 4px}
.ig-toc button{flex:0 0 auto;font-size:11.5px;font-weight:700;color:#6b5b52;background:#fff;
  border:1px solid #f0e4d4;border-radius:999px;padding:5px 11px;white-space:nowrap}
.ig-toc button:active{background:#fff7e6;border-color:#f5dfbc}
.ig-fig .fig-wide{display:block}
.ig-fig .fig-narrow{display:none}
.ig-next{display:flex;flex-direction:column;gap:8px}
.ig-next .card{display:block;padding:13px 15px;border-radius:16px;background:#fff;border:1px solid var(--line)}
.ig-progress{position:fixed;top:0;left:0;right:0;height:3px;z-index:60;pointer-events:none}
.ig-progress i{display:block;height:100%;width:0;border-radius:0 3px 3px 0;
  background:linear-gradient(90deg,#f59e0b,#2563eb);transition:width .08s linear}
@media (max-width:560px){
  .ig-doc{padding:20px 16px 26px;font-size:15.5px}
  .ig-title{font-size:23px}
  .ig-doc h2{font-size:19px}
  .ig-fig{padding:10px 6px}
  .ig-quote{padding:12px 13px}
  .ig-appendix{padding:14px 9px}
  /* 700 宽的插图压到手机上只剩 0.47 倍，改用竖排窄版，字才看得清 */
  .ig-fig .fig-wide{display:none}
  .ig-fig .fig-narrow{display:block}
}
@media print{
  @page{size:A4;margin:14mm 14mm}
  body{background:#fff !important}
  .tabbar,.ig-noprint,.topbar,.ig-toc,.ig-meta,.ig-crumb,.ig-progress{display:none !important}
  .ig-fig .fig-wide{display:block !important}
  .ig-fig .fig-narrow{display:none !important}
  .view{max-width:none !important;padding:0 !important;margin:0 !important}
  .ig-doc{border:none !important;box-shadow:none !important;padding:0 !important;font-size:11.5pt;line-height:1.7}
  .ig-title{font-size:20pt}
  .ig-doc h2{font-size:14pt;page-break-after:avoid}
  .ig-fig,.ig-box,.ig-appendix,.ig-quote{break-inside:avoid;page-break-inside:avoid}
}
`;

const ARTICLE_HTML = `
<header class="ig-hero">
  <div class="ig-kicker">数理思维方法论 · 可打印收藏版</div>
  <h1 class="ig-title">看见公式背后的风：数学与物理直觉思维的养成</h1>
  <p class="ig-lead">公式是乐谱，直觉是乐感。背熟乐谱能按部就班弹出音符，但只有长出了乐感，你才能在考场和探索里一眼听出哪里跑了调、哪里藏着捷径。</p>
</header>

<h2>一、为什么数学和物理需要建立直觉思维？</h2>
<p>很多人一听“直觉”，就以为是闭着眼睛瞎蒙——其实恰恰相反。心理学和科学史上把直觉分成两种：一种是没经过训练的<strong>“野生直觉”</strong>（比如觉得重铁球一定比羽毛先落地、觉得红光开到最亮总能把电子烤出来、觉得求函数值域只要代入左右端点就行）；另一种是经过大量观察、画图与碰撞后长出来的<strong>“数理直觉”</strong>。</p>
<p>如果把解题比作在陌生城市开车，知识点是路标，计算是踩油门，<strong>数理直觉就是你脑子里的实时导航雷达</strong>。没有直觉的刷题，就像蒙着眼睛背诵“前方 50 米左转、再 30 米右转”——路牌稍微换个样式就会原地迷路；而拥有直觉的人，心里有一张俯瞰地图，题目刚读一半，雷达就已经亮了：</p>
<ul>
  <li><strong>自带“防离谱警报器”</strong>：算完一道物理题发现小车速度算成了 <code>5×10⁸ m/s</code>（超光速了！），或者三角函数值算出了 <code>1.4</code>，直觉会在 0.5 秒内拉响警报，帮你当场抓出符号或小数点错误。</li>
  <li><strong>把“陌生压轴题”翻译成“老熟人”</strong>：题目换了马甲（比如把弹簧换成磁场、把正弦换成余弦），靠死记题型会慌，靠直觉一眼就能认出“这不还是能量守恒 / 单位圆上扫一段弧吗？”</li>
  <li><strong>省下宝贵的脑力预算</strong>：高中的推导链条越来越长，直觉负责先指明大方向，把宝贵的注意力留给最关键的一两步严密计算。</li>
</ul>

<figure class="ig-fig">
  <div class="fig-wide">
    <svg viewBox="0 0 700 220" role="img" aria-label="野生直觉与数理直觉对比示意图">
    <rect x="14" y="16" width="316" height="184" rx="14" fill="#fff7ed" stroke="#fed7aa" stroke-width="1.5"/>
    <text x="34" y="46" font-size="15" font-weight="800" fill="#9a3412">野生直觉（日常错觉）</text>
    <text x="34" y="76" font-size="13" fill="#57534e">• 重球一定比轻球先落地</text>
    <text x="34" y="102" font-size="13" fill="#57534e">• 磁铁插进线圈停住，灯泡会一直亮</text>
    <text x="34" y="128" font-size="13" fill="#57534e">• 绳子一断，小球沿半径直飞出去</text>
    <text x="34" y="154" font-size="13" fill="#57534e">• 求区间值域，只算左右两个端点</text>
    <text x="34" y="182" font-size="12" font-weight="700" fill="#c2410c">来源：未剥离干扰的模糊生活经验</text>

    <path d="M338 108 L362 108" stroke="#2563eb" stroke-width="3" stroke-linecap="round"/>
    <polygon points="362,102 372,108 362,114" fill="#2563eb"/>

    <rect x="376" y="16" width="310" height="184" rx="14" fill="#eff6ff" stroke="#bfdbfe" stroke-width="1.5"/>
    <text x="396" y="46" font-size="15" font-weight="800" fill="#1e3a8a">练出来的数理直觉（科学雷达）</text>
    <text x="396" y="76" font-size="13" fill="#334155">• 抽掉空气，铁球羽毛同步落地</text>
    <text x="396" y="102" font-size="13" fill="#334155">• 只有磁场的“变化”才能生电</text>
    <text x="396" y="128" font-size="13" fill="#334155">• 断绳瞬间按惯性沿切线飞出</text>
    <text x="396" y="154" font-size="13" fill="#334155">• 先画单位圆弧，一眼看出内部极值</text>
    <text x="396" y="182" font-size="12" font-weight="700" fill="#1d4ed8">来源：实验碰撞 + 图像化 + 严密校准</text>
  </svg>
  </div>
  <div class="fig-narrow">
    <svg viewBox="0 0 340 388" role="img" aria-label="野生直觉与数理直觉对比示意图（竖排）">
      <rect x="8" y="8" width="324" height="172" rx="14" fill="#fff7ed" stroke="#fed7aa" stroke-width="1.5"/>
      <text x="24" y="36" font-size="13.5" font-weight="800" fill="#9a3412">野生直觉（日常错觉）</text>
      <text x="24" y="64" font-size="12" fill="#57534e">• 重球一定比轻球先落地</text>
      <text x="24" y="88" font-size="12" fill="#57534e">• 磁铁插进线圈停住，灯泡会一直亮</text>
      <text x="24" y="112" font-size="12" fill="#57534e">• 绳子一断，小球沿半径直飞出去</text>
      <text x="24" y="136" font-size="12" fill="#57534e">• 求区间值域，只算左右两个端点</text>
      <text x="24" y="164" font-size="11" font-weight="700" fill="#c2410c">来源：未剥离干扰的模糊生活经验</text>

      <path d="M170 186 L170 196" stroke="#2563eb" stroke-width="3" stroke-linecap="round"/>
      <polygon points="164,196 176,196 170,206" fill="#2563eb"/>

      <rect x="8" y="210" width="324" height="170" rx="14" fill="#eff6ff" stroke="#bfdbfe" stroke-width="1.5"/>
      <text x="24" y="238" font-size="13.5" font-weight="800" fill="#1e3a8a">练出来的数理直觉（科学雷达）</text>
      <text x="24" y="266" font-size="12" fill="#334155">• 抽掉空气，铁球羽毛同步落地</text>
      <text x="24" y="290" font-size="12" fill="#334155">• 只有磁场的「变化」才能生电</text>
      <text x="24" y="314" font-size="12" fill="#334155">• 断绳瞬间按惯性沿切线飞出</text>
      <text x="24" y="338" font-size="12" fill="#334155">• 先画单位圆弧，一眼看出内部极值</text>
      <text x="24" y="366" font-size="11" font-weight="700" fill="#1d4ed8">来源：实验碰撞 + 图像化 + 严密校准</text>
    </svg>
  </div>
  <div class="ig-cap">图 1：真正的数理直觉不是“凭感觉猜”，而是被实验与逻辑反复校准过的“大脑雷达”</div>
</figure>

<h2>二、伟大头脑的“直觉高光时刻”</h2>
<p>翻开科学史你会发现，几乎每一次掀翻屋顶的重大突破，最初都不是从十页密密麻麻的草稿纸里算出来的，而是先在某位大师脑海里闪现出一幅<strong>生动到近乎顽皮的画面</strong>：</p>
<ul>
  <li><strong>伽利略的“一根绳子破案”</strong>：亚里士多德说“重物下落更快”，全欧洲信了两千年。伽利略根本没费劲去搬大石头，只在脑子里拿了一根绳子把重球和轻球绑在一起——按旧理论，轻球会拖慢重球（合体更慢），可绑在一起总重量更重又该落得更快（合体更快）！一个逻辑自相矛盾，两千年的权威瞬间崩塌。</li>
  <li><strong>法拉第的“漫天橡皮筋”</strong>：法拉第出身装订工学徒，几乎没学过微积分，但他拥有惊人的空间直觉——在他眼里，磁铁周围不是空的，而是布满了一根根有弹性、会排斥的<strong>磁感线</strong>。靠着这幅脑内动画，他发现了电磁感应；多年后，数学天才麦克斯韦把法拉第脑子里的画面翻译成四个方程，直接点亮了整个人类电气文明。</li>
  <li><strong>爱因斯坦的“追光少年与坠落电梯”</strong>：16 岁时他上课发呆，想象自己骑在一束光上狂奔：“这时我照镜子，还能看见自己的脸吗？”28 岁在专利局椅子上，他突然想到“一个自由下落的人感觉不到自己的体重”——他称这是自己一生中最快乐的念头，广义相对论就从这间想象中的电梯里长了出来。</li>
  <li><strong>小高斯的“折纸算术”</strong>：老师罚全班算 <code>1 + 2 + … + 100</code>，大家埋头苦加，9 岁的高斯一眼看见数字排成队列时的<strong>左右对称</strong>：把队尾折到队头，<code>1+100=101</code>、<code>2+99=101</code>，一共 50 对，秒出 <code>5050</code>。这正是数学直觉最迷人的地方——看见结构，而不是蛮干。</li>
</ul>

<div class="ig-quote">物理学家费曼说过一句大实话：“如果你没法在黑板上画两根箭头，把一个定律讲给刚进校的新生听懂，那说明你自己也还没真懂它。”</div>

<h2>三、直觉与知识点、计算、推导的关系：如何科学地养成直觉？</h2>
<p>必须先说清一个关键底线：<strong>直觉绝不是用来替代严谨推导和计算的</strong>。它们三者是一支配合默契的探险队：</p>
<ul>
  <li><strong>直觉是“侦察兵”</strong>：先爬上山坡望一眼，判断“答案大概是正的、应该比 2 小、图像是对称的”，指明突破方向；</li>
  <li><strong>知识点是“装备库”</strong>：二倍角公式、动量守恒、单位圆定义，都是侦察兵和工程兵手里的工具；</li>
  <li><strong>推导与计算是“工程兵”</strong>：负责把侦察兵看到的路线一步步铺成铁桥，把每一个正负号、每一处定义域焊死。没有推导的直觉容易掉进坑里，没有直觉的推导则会像无头苍蝇一样乱撞。</li>
</ul>

<figure class="ig-fig">
  <div class="fig-wide">
    <svg viewBox="0 0 700 185" role="img" aria-label="数理直觉养成四步飞轮图">
    <rect x="20" y="34" width="142" height="112" rx="14" fill="#eff6ff" stroke="#93c5fd" stroke-width="1.5"/>
    <text x="91" y="66" text-anchor="middle" font-size="14" font-weight="800" fill="#1e3a8a">① 先猜一猜</text>
    <text x="91" y="92" text-anchor="middle" font-size="12" fill="#475569">动笔前用 10 秒</text>
    <text x="91" y="112" text-anchor="middle" font-size="12" fill="#475569">押注方向与范围</text>

    <path d="M168 90 L190 90" stroke="#64748b" stroke-width="2.5"/><polygon points="190,85 198,90 190,95" fill="#64748b"/>

    <rect x="202" y="34" width="142" height="112" rx="14" fill="#f0fdf4" stroke="#86efac" stroke-width="1.5"/>
    <text x="273" y="66" text-anchor="middle" font-size="14" font-weight="800" fill="#065f46">② 画图 / 推极限</text>
    <text x="273" y="92" text-anchor="middle" font-size="12" fill="#475569">把式子画成曲线</text>
    <text x="273" y="112" text-anchor="middle" font-size="12" fill="#475569">或把参数推到 0/∞</text>

    <path d="M350 90 L372 90" stroke="#64748b" stroke-width="2.5"/><polygon points="372,85 380,90 372,95" fill="#64748b"/>

    <rect x="384" y="34" width="142" height="112" rx="14" fill="#fffbeb" stroke="#fcd34d" stroke-width="1.5"/>
    <text x="455" y="66" text-anchor="middle" font-size="14" font-weight="800" fill="#92400e">③ 推导焊死</text>
    <text x="455" y="92" text-anchor="middle" font-size="12" fill="#475569">用严密代数计算</text>
    <text x="455" y="112" text-anchor="middle" font-size="12" fill="#475569">验证并锁死细节</text>

    <path d="M532 90 L554 90" stroke="#64748b" stroke-width="2.5"/><polygon points="554,85 562,90 554,95" fill="#64748b"/>

    <rect x="566" y="34" width="114" height="112" rx="14" fill="#fef2f2" stroke="#fca5a5" stroke-width="1.5"/>
    <text x="623" y="66" text-anchor="middle" font-size="14" font-weight="800" fill="#991b1b">④ 错题校准</text>
    <text x="623" y="92" text-anchor="middle" font-size="12" fill="#475569">猜错即升级</text>
    <text x="623" y="112" text-anchor="middle" font-size="12" fill="#475569">升级大脑雷达</text>
  </svg>
  </div>
  <div class="fig-narrow">
    <svg viewBox="0 0 340 398" role="img" aria-label="数理直觉养成四步飞轮图（竖排）">
      <rect x="24" y="8" width="292" height="78" rx="14" fill="#eff6ff" stroke="#93c5fd" stroke-width="1.5"/>
      <text x="170" y="32" text-anchor="middle" font-size="13" font-weight="800" fill="#1e3a8a">① 先猜一猜</text>
      <text x="170" y="54" text-anchor="middle" font-size="11.5" fill="#475569">动笔前用 10 秒</text>
      <text x="170" y="72" text-anchor="middle" font-size="11.5" fill="#475569">押注方向与范围</text>

      <path d="M170 90 L170 98" stroke="#64748b" stroke-width="2.5"/>
      <polygon points="165,98 175,98 170,106" fill="#64748b"/>

      <rect x="24" y="108" width="292" height="78" rx="14" fill="#f0fdf4" stroke="#86efac" stroke-width="1.5"/>
      <text x="170" y="132" text-anchor="middle" font-size="13" font-weight="800" fill="#065f46">② 画图 / 推极限</text>
      <text x="170" y="154" text-anchor="middle" font-size="11.5" fill="#475569">把式子画成曲线</text>
      <text x="170" y="172" text-anchor="middle" font-size="11.5" fill="#475569">或把参数推到 0/∞</text>

      <path d="M170 190 L170 198" stroke="#64748b" stroke-width="2.5"/>
      <polygon points="165,198 175,198 170,206" fill="#64748b"/>

      <rect x="24" y="208" width="292" height="78" rx="14" fill="#fffbeb" stroke="#fcd34d" stroke-width="1.5"/>
      <text x="170" y="232" text-anchor="middle" font-size="13" font-weight="800" fill="#92400e">③ 推导焊死</text>
      <text x="170" y="254" text-anchor="middle" font-size="11.5" fill="#475569">用严密代数计算</text>
      <text x="170" y="272" text-anchor="middle" font-size="11.5" fill="#475569">验证并锁死细节</text>

      <path d="M170 290 L170 298" stroke="#64748b" stroke-width="2.5"/>
      <polygon points="165,298 175,298 170,306" fill="#64748b"/>

      <rect x="24" y="308" width="292" height="78" rx="14" fill="#fef2f2" stroke="#fca5a5" stroke-width="1.5"/>
      <text x="170" y="332" text-anchor="middle" font-size="13" font-weight="800" fill="#991b1b">④ 错题校准</text>
      <text x="170" y="354" text-anchor="middle" font-size="11.5" fill="#475569">猜错即升级</text>
      <text x="170" y="372" text-anchor="middle" font-size="11.5" fill="#475569">升级大脑雷达</text>
    </svg>
  </div>
  <div class="ig-cap">图 2：数理直觉不是天生的魔法，而是沿着“猜想 → 图形/极限 → 推导 → 校准”滚动出来的飞轮</div>
</figure>

<h3>养成直觉的 4 把“瑞士军刀”</h3>
<ol>
  <li><strong>极限拷问法</strong>：把题里的参数推到极端——斜面倾角变成 <code>0°</code> 或 <code>90°</code>、木块质量变成无穷大、磁场变成 <code>0</code>。如果推出来的公式在极端情况下算出荒谬结果，立刻就知道中间推错了！</li>
  <li><strong>几何翻译法</strong>：大脑天生擅长看图，不擅长盯一长串符号。把“区间值域”翻译成<strong>单位圆上的一段弧</strong>，把“辅助角公式”翻译成<strong>直角三角形的斜边</strong>，把“运动学公式”翻译成<strong>v-t 图的面积</strong>，抽象立刻变具体。</li>
  <li><strong>对称与守恒雷达</strong>：拿到复杂情景先别急着列十个方程，先问自己一句：“整个过程里，什么东西死活没变？”平移不改周期、爆炸不改质心、无摩擦不改总机械能——抓住不变的，世界瞬间安静下来。</li>
  <li><strong>量纲与数量级体检</strong>：物理公式两边单位必须一模一样；数学结果先估一眼正负和大小（比如 <code>sin</code> 和 <code>cos</code> 绝不可能大于 1），养成算完顺手瞄一眼合理性的习惯。</li>
</ol>

<h2>四、学生时代如何从今天开始建立直觉思维？</h2>
<p>不需要等到大学，也不需要额外买十本厚教辅——高中每天做作业时，只要微调四个小动作，直觉就会悄悄发芽：</p>
<ul>
  <li><strong>动作 1：动笔前先停 10 秒“押个注”</strong>。读完题先在心里猜一下：“答案应该是正还是负？速度最大点在接触前还是接触后？”猜对了成就感拉满，<strong>猜错了更赚</strong>——因为“直觉被打脸”那一刻，大脑记忆刻得最深！</li>
  <li><strong>动作 2：一题多玩，把静止的题“推着动起来”</strong>。解完一道题后顺手问一句：“如果把向右平移改成向左平移、把开区间改成闭区间、把摩擦打开，结论怎么变？”把死题变成活模型，一题顶十题。</li>
  <li><strong>动作 3：把错题本用成“直觉校准仪”</strong>。记录错题时，除了抄正解，更要多写一句红字：<em>“我当时脑子里的错觉是什么？”</em>——揪出那个具体的假直觉，下次同类题自动免疫。</li>
  <li><strong>动作 4：当一次“小老师”（费曼输出）</strong>。晚饭后花 3 分钟，试着不用公式，只用手势和草图把今天搞懂的一个坑（比如“为什么卫星一直在下落却不落地”）讲给爸爸妈妈听。能讲笑、讲明白，它就彻底属于你了。</li>
</ul>

<section class="ig-appendix">
  <h2>附录 A：给 Sunny 同学的专属直觉手账</h2>
  <p>Sunny 你好呀！认真看过你最近的错题本后，其实最让人开心的一个发现是：<strong>你绝大多数错题并不是“不会做”</strong>，思路往往已经走对了 85%–90%，只是在几个固定的小弯道上轻轻滑了一脚。这说明你的知识骨架已经搭得很稳啦！只要给大脑装上下面 <strong>4 盏专属直觉警示灯</strong>，错题本里那十几道三角函数题马上就能成片清零：</p>

  <div class="ig-box">
    <h3>Sunny 的 4 盏高频“防滑警示灯”</h3>
    <ol>
      <li><strong>遇平移，先给孤零零的 <code>x</code> 穿括号</strong>：左加右减永远只替换 <code>x</code>（变成 <code>ω(x+d)+φ</code>），千万别直接加在末尾；而且平移像推着波浪走，<strong>绝对不会改变周期</strong>！读图找 φ 时，顺手瞄一眼零点是「向上穿轴」还是「向下穿轴」。</li>
      <li><strong>求区间值域，先在草稿纸上画个单位圆弧</strong>：别被区间左右端点骗啦！先算出整体相位 <code>u = ωx+φ</code> 的范围，在单位圆上描出这段弧——只要弧扫过最左端 <code>π</code>，余弦最小值必是 <code>-1</code>；判断 <code>|f(x)|&lt;2</code> 恒成立，就是看这段弧有没有严严实实避开 <code>0</code> 和 <code>π</code>。</li>
      <li><strong>降幂化简，记住“余加正减 + 常数单拎”</strong>：<code>cos²x = (1+cos2x)/2</code>（带加号），<code>sin²x = (1-cos2x)/2</code>（<strong>带减号！</strong>）。先把常数项单独算清圈出来，再用 <code>(a, b)</code> 落在第几象限锁死辅助角 <code>φ</code> 的正负号，从此告别写反符号。</li>
      <li><strong>诱导公式别死背，拿 25° 锐角转一圈</strong>：把 <code>θ</code> 想象成 25° 小锐角，<code>cos(π/2+θ)</code> 就是转到 115° 第二象限——横坐标变负且长度变成短边，一眼看出 <code>-sinθ</code>！另外顺手记牢一个小彩蛋：对数里只有<strong>“对数相加”</strong>才变真数相乘，<code>lg2·lg50</code> 千万别当成 <code>lg(2×50)</code> 哦。</li>
    </ol>
  </div>

  <figure class="ig-fig">
    <div class="fig-wide">
    <svg viewBox="0 0 700 200" role="img" aria-label="Sunny 专属随身防坑速查卡">
      <rect x="12" y="14" width="212" height="172" rx="12" fill="#ffffff" stroke="#bfdbfe" stroke-width="1.5"/>
      <text x="118" y="38" text-anchor="middle" font-size="13.5" font-weight="800" fill="#1e3a8a">① 单位圆值域雷达</text>
      <circle cx="118" cy="108" r="46" fill="none" stroke="#94a3b8" stroke-width="1.5"/>
      <line x1="60" y1="108" x2="176" y2="108" stroke="#cbd5e1" stroke-width="1.2"/>
      <line x1="118" y1="52" x2="118" y2="164" stroke="#cbd5e1" stroke-width="1.2"/>
      <path d="M141 68 A46 46 0 0 0 72 108" fill="none" stroke="#2563eb" stroke-width="4"/>
      <circle cx="72" cy="108" r="4.5" fill="#dc2626"/>
      <text x="26" y="112" font-size="11" font-weight="700" fill="#dc2626">π(-1)</text>
      <text x="168" y="112" font-size="11" font-weight="700" fill="#059669">0(+1)</text>
      <text x="118" y="176" text-anchor="middle" font-size="11" fill="#475569">弧扫过红点，必取最小值！</text>

      <rect x="244" y="14" width="212" height="172" rx="12" fill="#ffffff" stroke="#fde68a" stroke-width="1.5"/>
      <text x="350" y="38" text-anchor="middle" font-size="13.5" font-weight="800" fill="#92400e">② 降幂与平移口诀</text>
      <text x="260" y="72" font-size="12.5" font-weight="700" fill="#065f46">cos²x = (1 + cos2x) / 2</text>
      <text x="260" y="98" font-size="12.5" font-weight="700" fill="#b91c1c">sin²x = (1 - cos2x) / 2</text>
      <line x1="260" y1="114" x2="440" y2="114" stroke="#f3e8d8" stroke-width="1.2"/>
      <text x="260" y="138" font-size="12" fill="#334155">左移 d：x → (x + d)</text>
      <text x="260" y="160" font-size="12" fill="#334155">周期 T = 2π/ω 永远不变</text>

      <rect x="476" y="14" width="212" height="172" rx="12" fill="#ffffff" stroke="#a7f3d0" stroke-width="1.5"/>
      <text x="582" y="38" text-anchor="middle" font-size="13.5" font-weight="800" fill="#065f46">③ 25° 旋转定诱导符号</text>
      <text x="492" y="74" font-size="12" fill="#1e293b">一象限：sin +  cos +</text>
      <text x="492" y="98" font-size="12" fill="#1e293b">二象限：sin +  cos -</text>
      <text x="492" y="122" font-size="12" fill="#1e293b">三象限：sin -  cos -</text>
      <text x="492" y="146" font-size="12" fill="#1e293b">四象限：sin -  cos +</text>
      <text x="582" y="174" text-anchor="middle" font-size="11" font-weight="700" fill="#059669">横看 cos，竖看 sin</text>
    </svg>
  </div>
  <div class="fig-narrow">
    <svg viewBox="0 0 340 552" role="img" aria-label="Sunny 专属随身防坑速查卡（竖排）">
      <rect x="8" y="8" width="324" height="176" rx="12" fill="#ffffff" stroke="#bfdbfe" stroke-width="1.5"/>
      <text x="170" y="34" text-anchor="middle" font-size="13.5" font-weight="800" fill="#1e3a8a">① 单位圆值域雷达</text>
      <circle cx="88" cy="112" r="42" fill="none" stroke="#94a3b8" stroke-width="1.5"/>
      <line x1="38" y1="112" x2="138" y2="112" stroke="#cbd5e1" stroke-width="1.2"/>
      <line x1="88" y1="62" x2="88" y2="162" stroke="#cbd5e1" stroke-width="1.2"/>
      <path d="M109 76 A42 42 0 0 0 46 112" fill="none" stroke="#2563eb" stroke-width="3.4"/>
      <circle cx="46" cy="112" r="4.2" fill="#dc2626"/>
      <text x="10" y="116" font-size="11.5" font-weight="700" fill="#dc2626">π(-1)</text>
      <text x="142" y="116" font-size="11.5" font-weight="700" fill="#059669">0(+1)</text>
      <text x="170" y="170" text-anchor="middle" font-size="11.5" fill="#475569">弧扫过红点，必取最小值！</text>

      <rect x="8" y="196" width="324" height="140" rx="12" fill="#ffffff" stroke="#fde68a" stroke-width="1.5"/>
      <text x="170" y="222" text-anchor="middle" font-size="13.5" font-weight="800" fill="#92400e">② 降幂与平移口诀</text>
      <text x="24" y="250" font-size="12" font-weight="700" fill="#065f46">cos²x = (1 + cos2x) / 2</text>
      <text x="24" y="274" font-size="12" font-weight="700" fill="#b91c1c">sin²x = (1 - cos2x) / 2</text>
      <line x1="24" y1="288" x2="300" y2="288" stroke="#f3e8d8" stroke-width="1.2"/>
      <text x="24" y="310" font-size="12.5" fill="#334155">左移 d：x → (x + d)</text>
      <text x="24" y="330" font-size="12.5" fill="#334155">周期 T = 2π/ω 永远不变</text>

      <rect x="8" y="348" width="324" height="196" rx="12" fill="#ffffff" stroke="#a7f3d0" stroke-width="1.5"/>
      <text x="170" y="374" text-anchor="middle" font-size="13.5" font-weight="800" fill="#065f46">③ 25° 旋转定诱导符号</text>
      <text x="24" y="404" font-size="12.5" fill="#1e293b">一象限：sin +  cos +</text>
      <text x="24" y="430" font-size="12.5" fill="#1e293b">二象限：sin +  cos -</text>
      <text x="24" y="456" font-size="12.5" fill="#1e293b">三象限：sin -  cos -</text>
      <text x="24" y="482" font-size="12.5" fill="#1e293b">四象限：sin -  cos +</text>
      <text x="170" y="522" text-anchor="middle" font-size="11.5" font-weight="700" fill="#059669">横看 cos，竖看 sin</text>
    </svg>
  </div>
    <div class="ig-cap">图 3：Sunny 专属桌面防坑速查卡（打印后可直接贴在书桌前）</div>
  </figure>

  <p style="margin-bottom:0"><strong>最后想送给你的一句话：</strong>高中数理从来不是比谁背的套路更厚，而是比谁先看见公式背后吹过的风。网站里已经为你准备好了物理和数学的互动实验室——先去玩一玩、猜一猜、把直觉点亮，再回头清零错题本，你会发现自己比想象中强大得多。加油，Sunny，保持好奇，继续探险！</p>
</section>
`;

export async function renderIntuitionArticle(view) {
  const slug = 'intuition';
  const essay = essayBySlug(slug) || {};
  const { prev, next } = essayNeighbors(slug);
  const chars = countChars(ARTICLE_HTML);
  const minutes = Math.max(1, Math.round(chars / 380));
  const figCount = (ARTICLE_HTML.match(/class="ig-fig"/g) || []).length;

  const root = el('div', { class: 'ig-wrap' });
  const st = document.createElement('style');
  st.textContent = ARTICLE_CSS;
  root.appendChild(st);

  root.appendChild(el('div', { class: 'topbar ig-noprint' }, [
    el('button', { class: 'back', text: '‹', onclick: () => navigate(COLUMN.route) }),
    el('div', { style: 'flex:1;min-width:0' }, [
      el('h1', { text: '数理直觉思维的养成' }),
      el('div', { class: 'sub', text: '带插图 · 支持一键打印或另存为 PDF' }),
    ]),
    el('button', { class: 'btn sm', text: '🖨️ 打印', onclick: () => window.print() }),
  ]));

  root.appendChild(el('div', { class: 'ig-crumb ig-noprint' }, [
    el('a', { href: COLUMN.route, text: '📖 学习心得体会' }),
    el('span', { text: '›' }),
    el('b', { text: '第 1 篇' }),
  ]));

  root.appendChild(el('div', { class: 'ig-meta ig-noprint' }, [
    el('span', { text: essay.date || '' }),
    el('span', { class: 'sep' }),
    el('span', { text: `约 ${chars} 字 · 阅读 ${minutes} 分钟` }),
    el('span', { class: 'sep' }),
    el('span', { text: `${(essay.sections || []).length} 个章节 · ${figCount} 张原创插图` }),
  ]));

  const doc = el('article', { class: 'ig-doc', html: ARTICLE_HTML });

  /* 目录：从正文的 h2 自动生成锚点，标题用短文案，点一下跳过去 */
  const toc = el('div', { class: 'ig-toc ig-noprint' });
  doc.querySelectorAll('h2').forEach((h, i) => {
    const id = `ig-s${i + 1}`;
    h.id = id;
    const short = (essay.sections || [])[i];
    const label = short || (h.textContent || '').trim().replace(/^[一二三四五六七八九十]+、/, '');
    toc.appendChild(el('button', {
      text: `${i + 1}. ${label}`,
      onclick: () => {
        const target = doc.querySelector(`#${id}`);
        if (target) target.scrollIntoView({ behavior: 'smooth', block: 'start' });
      },
    }));
  });
  if (toc.children.length) root.appendChild(toc);

  root.appendChild(doc);

  const nav = el('div', { class: 'ig-next ig-noprint' });
  nav.appendChild(el('div', { class: 'card' }, [
    el('div', { style: 'font-size:12px;font-weight:900;color:#b45309', text: next ? '下一篇' : '下一篇在路上' }),
    el('div', {
      style: 'font-size:13px;font-weight:800;margin-top:4px;color:#1f2937;line-height:1.5',
      text: next ? next.title : '想先看哪一篇？到许愿墙点个题，写得最多的主题先动笔。',
    }),
    el('div', { class: 'row', style: 'gap:8px;margin-top:10px;flex-wrap:wrap' }, [
      next
        ? el('button', { class: 'btn sm', text: '继续读 →', onclick: () => navigate(next.route) })
        : el('button', { class: 'btn sm', text: '💌 去点题', onclick: () => navigate('#/wishes') }),
      prev ? el('button', { class: 'btn sm ghost', text: '← 上一篇', onclick: () => navigate(prev.route) }) : null,
      el('button', { class: 'btn sm ghost', text: '📖 回到专栏首页', onclick: () => navigate(COLUMN.route) }),
    ]),
  ]));
  root.appendChild(nav);

  root.appendChild(el('div', { class: 'row-between ig-noprint', style: 'gap:8px;flex-wrap:wrap' }, [
    el('button', { class: 'btn sm ghost', text: '📐 去玩数学直觉实验室', onclick: () => navigate('#/math-trig-lab') }),
    el('button', { class: 'btn sm', text: '📒 去错题本重做清零 →', onclick: () => navigate('#/wrongbook') }),
  ]));

  /* 阅读进度条：贴在视口顶部，打印时自动隐藏 */
  const bar = el('div', { class: 'ig-progress ig-noprint' }, [el('i')]);
  const fill = bar.firstChild;
  const onScroll = () => {
    /* 视图是先渲染到游离 stage 再由 router 挂上去的：未挂载时量不到高度，直接跳过 */
    if (!doc.isConnected) return;
    const top = doc.getBoundingClientRect().top + window.scrollY;
    const h = doc.offsetHeight || 0;
    const span = Math.max(1, h - window.innerHeight * 0.45);
    const p = Math.max(0, Math.min(1, (window.scrollY + window.innerHeight * 0.28 - top) / span));
    fill.style.width = `${(p * 100).toFixed(1)}%`;
  };

  view.innerHTML = '';
  view.appendChild(root);
  document.body.appendChild(bar);
  window.addEventListener('scroll', onScroll, { passive: true });
  requestAnimationFrame(() => { onScroll(); requestAnimationFrame(onScroll); });

  return () => {
    window.removeEventListener('scroll', onScroll);
    bar.remove();
  };
}
