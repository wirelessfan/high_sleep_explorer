"""生成「谬误研究所」怪人军团：SVG 立绘 + 角色表 + 预览图鉴。

设计说明
--------
不复用任何商业卡通 / 游戏的现成角色，避免版权问题；改用公有领域的
「科学怪人 / 实验室造物」母题作为统一班底：缝合线、颈部螺栓、玻璃罩、
电极、绷带、Q 版三头身、实验编号牌。18 个角色共享同一套骨架与部件库，
只替换配色、头部装饰、手持道具与躯干纹理，因此天然像同一部片子的角色表。

- 每个主题前 5 个版块 = 1 只小 boss（用「错误概念」培育的实验体）。
- 每个主题最后的 boss 版块 = 该主题对应的科学家，作为研究所所长 / 大 boss，
  并绑定 content/cards/cards.json 里的卡片 id。

用法::

    python tools/generate_bosses.py

产物::
    assets/bosses/*.svg        18 个独立立绘（透明底，viewBox 0 0 240 280）
    content/bosses.json        角色表（供后端读取）
    design/bosses/gallery.html 离线预览图鉴

本脚本只依赖标准库，可重复执行；不改动任何已有业务文件。
"""
from __future__ import annotations

import json
import re
from pathlib import Path
from string import Template

ROOT = Path(__file__).resolve().parent.parent
SVG_DIR = ROOT / "assets" / "bosses"
GALLERY = ROOT / "design" / "bosses" / "gallery.html"
BOSS_JSON = ROOT / "content" / "bosses.json"
TOPIC_DIR = ROOT / "content" / "topics"

# ---------------------------------------------------------------- 配色班底

PAL = {
    "physics": dict(main="#6366f1", dark="#312e81", light="#a5b4fc",
                    accent="#fbbf24", halo="#c7d2fe", line="#4338ca"),
    "chemistry": dict(main="#10b981", dark="#065f46", light="#6ee7b7",
                      accent="#38bdf8", halo="#a7f3d0", line="#047857"),
    "math": dict(main="#f59e0b", dark="#b45309", light="#fcd34d",
                 accent="#fb7185", halo="#fde68a", line="#d97706"),
}

SECTION_NAME = {
    "quick": "快速测试", "basic": "基础闯关", "summary": "知识点总结",
    "hard": "难点剖析", "practice": "实战巩固", "boss": "Boss 彩蛋",
}

PAL_SUBJECT = {"physics": "物理", "chemistry": "化学", "math": "数学"}

# ---------------------------------------------------------------- 角色表
# shape: round / tank / ghost —— 躯干轮廓
# head:  头顶装饰  prop: 手持道具  overlay: 躯干纹理
# tier=big 的角色使用科学家骨架，head/prop 决定权杖与徽记。

CAST = [
    # ===== 物理 · 电磁感应 =====
    dict(topic="physics-induction", subject="physics", section="quick",
         name="火花豆", en="Sparky", element="静电火花", shape="round",
         head="bulb", prop="bolt", overlay="spark", skill="静电乱流",
         taunt="噼啪！先把磁通量想清楚再碰我。",
         purified="火花收进灯泡，它终于安静了。"),
    dict(topic="physics-induction", subject="physics", section="basic",
         name="线圈兽", en="Coily", element="乱绕线圈", shape="round",
         head="magnet", prop="coil", overlay="coils", skill="匝数迷阵",
         taunt="绕啊绕……你数得清我身上几匝吗？",
         purified="线圈理顺了，感应电动势有了方向。"),
    dict(topic="physics-induction", subject="physics", section="summary",
         name="磁通雾", en="Fluxy", element="模糊磁通", shape="ghost",
         head="field", prop="none", overlay="waves", skill="力线障眼法",
         taunt="穿过我的到底是 B、S，还是 BS？",
         purified="雾散了，力线一根根排得整整齐齐。"),
    dict(topic="physics-induction", subject="physics", section="hard",
         name="楞次双脸", en="Lenz", element="反向直觉", shape="round",
         head="mirror", prop="arrows", overlay="reverse", skill="来拒去留",
         taunt="你增我就减，你走我就留——猜猜我朝哪边？",
         purified="两张脸终于达成共识：总是阻碍变化。"),
    dict(topic="physics-induction", subject="physics", section="practice",
         name="齿轮将", en="Dynamo", element="空转发电机", shape="tank",
         head="gear", prop="crank", overlay="cogs", skill="无功耗空转",
         taunt="想发电？先说说能量从哪儿来！",
         purified="齿轮咬合上，机械能真的变成了电能。"),
    dict(topic="physics-induction", subject="physics", section="boss",
         tier="big", name="法拉第", en="Michael Faraday", card_id="faraday",
         element="电磁感应定律", staff="coil", skill="力线审判",
         taunt="只要磁通量在变，我就有办法。你，准备好了吗？",
         purified="他把线圈递给你：现在，这间实验室归你了。"),
    # ===== 化学 · 化学平衡 =====
    dict(topic="chemistry-equilibrium", subject="chemistry", section="quick",
         name="气泡怪", en="Bubbly", element="乱冒气泡", shape="round",
         head="tube", prop="bubbles", overlay="bubbles", skill="假沸腾",
         taunt="咕嘟咕嘟～看到气泡就是反应在动？",
         purified="气泡停了，它承认自己只是被搅动了一下。"),
    dict(topic="chemistry-equilibrium", subject="chemistry", section="basic",
         name="歪天平", en="Tilty", element="失衡浓度", shape="round",
         head="balance", prop="weight", overlay="scale", skill="左右摇摆",
         taunt="这边多一点，那边少一点，反正永远不平衡～",
         purified="横梁放平：正逆速率相等，才是真的平衡。"),
    dict(topic="chemistry-equilibrium", subject="chemistry", section="summary",
         name="浓度云", en="Cloudy", element="浓度错觉", shape="ghost",
         head="beaker", prop="none", overlay="layers", skill="稀释迷雾",
         taunt="加水之后，所有浓度都变小了哦……真的吗？",
         purified="云雾分层沉淀，Q 和 K 各归其位。"),
    dict(topic="chemistry-equilibrium", subject="chemistry", section="hard",
         name="双面勒夏", en="Le Chatelier", element="条件误判", shape="round",
         head="mirror", prop="arrows", overlay="reverse", skill="压强诡辩",
         taunt="升温！加压！我到底该往哪边躲？",
         purified="两张脸同时点头：只向着减弱改变的方向移动。"),
    dict(topic="chemistry-equilibrium", subject="chemistry", section="practice",
         name="反应釜将", en="Kettle", element="催化误会", shape="tank",
         head="gauge", prop="wrench", overlay="cogs", skill="催化剂偷渡",
         taunt="加一勺催化剂，平衡就该往右跑了吧？",
         purified="压力表归零：催化剂只改快慢，不改终点。"),
    dict(topic="chemistry-equilibrium", subject="chemistry", section="boss",
         tier="big", name="居里夫人", en="Marie Curie", card_id="curie",
         element="放射性研究", staff="flask", skill="恒心审判",
         taunt="没有什么可怕的，只有值得理解的东西。",
         purified="她把发光的烧瓶放在你手里：别怕，慢慢来。"),
    # ===== 数学 · 有趣的概率论 =====
    dict(topic="math-probability", subject="math", section="quick",
         name="骰子精", en="Dicey", element="等可能错觉", shape="round",
         head="zigzag", prop="segment", overlay="grid", skill="点数迷阵",
         taunt="六个面看起来一样，可你真的数对了吗？",
         purified="骰子停下：样本点有限且等可能，才叫古典概型。"),
    dict(topic="math-probability", subject="math", section="basic",
         name="等可能怪", en="Fairly", element="伪公平", shape="round",
         head="balance", prop="weight", overlay="scale", skill="倾斜天平",
         taunt="我说每个结果概率一样，你有意见？",
         purified="天平放平：等可能是条件，不是口号。"),
    dict(topic="math-probability", subject="math", section="summary",
         name="概率云", en="Cloudy", element="模糊直觉", shape="ghost",
         head="field", prop="none", overlay="waves", skill="直觉迷雾",
         taunt="感觉像一半？感觉可不算数。",
         purified="云雾散开，样本空间一条条列了出来。"),
    dict(topic="math-probability", subject="math", section="hard",
         name="互斥双生", en="Exclu", element="概念混淆", shape="round",
         head="mirror", prop="arrows", overlay="reverse", skill="互斥独立之争",
         taunt="不能同时发生，就等于互不影响吗？",
         purified="两张脸分开：互斥与独立是两回事。"),
    dict(topic="math-probability", subject="math", section="practice",
         name="树状妖", en="Treey", element="分支混乱", shape="tank",
         head="triangle", prop="slash", overlay="diagonal", skill="路径缠绕",
         taunt="先乘还是先加？你分得清分步和分类吗？",
         purified="枝干理顺：分步相乘、分类相加。"),
    dict(topic="math-probability", subject="math", section="boss",
         tier="big", name="帕斯卡", en="Blaise Pascal", card_id="euler",
         element="概率论奠基", staff="orb", skill="赌金审判",
         taunt="赌局中断了，赌金该怎么分？想清楚再回答。",
         purified="他收起算筹：你已学会用等可能来衡量未知。"),
    # ===== 数学 · 神奇的椭圆 =====
    dict(topic="math-ellipse", subject="math", section="quick",
         name="绳结怪", en="Knotty", element="距离失衡", shape="round",
         head="bulb", prop="segment", overlay="curve", skill="绳长束缚",
         taunt="绳长固定，可我到底能不能画出圆？",
         purified="绳子绷紧：到两焦点距离之和恒为 2a。"),
    dict(topic="math-ellipse", subject="math", section="basic",
         name="焦距精", en="Focusy", element="参数错位", shape="round",
         head="gauge", prop="weight", overlay="scale", skill="a、b 混淆",
         taunt="a 和 b 谁大？焦点又在哪条轴上？",
         purified="量具归零：a²=b²+c²，焦点看分母。"),
    dict(topic="math-ellipse", subject="math", section="summary",
         name="扁平雾", en="Flato", element="形状错觉", shape="ghost",
         head="field", prop="none", overlay="waves", skill="离心迷雾",
         taunt="e 越大越圆，对吧？",
         purified="雾散形现：e 越大，椭圆越扁。"),
    dict(topic="math-ellipse", subject="math", section="hard",
         name="双焦点", en="Twin", element="焦点遗漏", shape="round",
         head="mirror", prop="arrows", overlay="reverse", skill="焦点分心",
         taunt="只盯着一个焦点，另一个就不存在了？",
         purified="两点对齐：定义要求两个焦点同时参与。"),
    dict(topic="math-ellipse", subject="math", section="practice",
         name="切线将", en="Tangent", element="弦长错算", shape="tank",
         head="triangle", prop="slash", overlay="diagonal", skill="焦点弦",
         taunt="弦过焦点，周长就一定是 4a 吗？",
         purified="图形归位：焦点三角形周长 2a+2c。"),
    dict(topic="math-ellipse", subject="math", section="boss",
         tier="big", name="开普勒", en="Johannes Kepler", card_id="descartes",
         element="行星轨道", staff="orb", skill="椭圆审判",
         taunt="行星的轨道不是圆，而是椭圆。你敢改写教科书吗？",
         purified="他把星图递给你：从此椭圆有了天空。"),
    # ===== 数学 · 换元法的妙用 =====
    dict(topic="math-substitution", subject="math", section="quick",
         name="换元豆", en="Swapy", element="变量僵化", shape="round",
         head="bulb", prop="epsilon", overlay="spark", skill="形式束缚",
         taunt="式子那么长，你就不会换个角度看？",
         purified="它把自己缩写成一个字母：世界清爽了。"),
    dict(topic="math-substitution", subject="math", section="basic",
         name="根号兽", en="Rooty", element="根式缠绕", shape="round",
         head="zigzag", prop="segment", overlay="grid", skill="开方纠缠",
         taunt="根号套根号，你敢直接平方吗？",
         purified="根号退去：整体换元，一次拆开。"),
    dict(topic="math-substitution", subject="math", section="summary",
         name="变量雾", en="Vary", element="范围丢失", shape="ghost",
         head="field", prop="none", overlay="waves", skill="范围迷雾",
         taunt="t 是实数就行？你问过原变量吗？",
         purified="雾气收束：t=x² 只能取非负值。"),
    dict(topic="math-substitution", subject="math", section="hard",
         name="范围鬼", en="Rangey", element="定义域越界", shape="round",
         head="mirror", prop="arrows", overlay="reverse", skill="增根陷阱",
         taunt="换元不写范围，答案就多出来了哦。",
         purified="范围补齐：换得干净，也要收得回来。"),
    dict(topic="math-substitution", subject="math", section="practice",
         name="三角匠", en="Trigon", element="角度失控", shape="tank",
         head="triangle", prop="slash", overlay="curve", skill="开方错号",
         taunt="cosθ 一定是正的吗？先说说 θ 的范围。",
         purified="角域锁定：开方不再加绝对值。"),
    dict(topic="math-substitution", subject="math", section="boss",
         tier="big", name="拉马努金", en="Srinivasa Ramanujan", card_id="ramanujan",
         element="恒等式艺术", staff="orb", skill="无穷级数审判",
         taunt="这些公式是女神告诉我的。你能证明几个？",
         purified="他笑着递过笔记本：换元做到极致，就是美。"),
    # ===== 数学 · 导数的几何意义 =====
    dict(topic="math-derivative", subject="math", section="quick",
         name="切线豆", en="Tangy", element="斜线乱切", shape="round",
         head="ruler", prop="slash", overlay="diagonal", skill="斜率碰瓷",
         taunt="随手画条线就说自己是切线，你能证吗？",
         purified="它把直尺摆到极限位置：这才是切线。"),
    dict(topic="math-derivative", subject="math", section="basic",
         name="割线虫", en="Secant", element="两点硬凑", shape="round",
         head="zigzag", prop="segment", overlay="grid", skill="Δx 拖堂",
         taunt="我就赖在两个点上，绝不让你取极限～",
         purified="Δx 终于趋近 0，虫子蜷成了切线。"),
    dict(topic="math-derivative", subject="math", section="summary",
         name="斜率方士", en="Slopey", element="坐标错位", shape="tank",
         head="triangle", prop="none", overlay="grid", skill=" Rise over Run",
         taunt="纵坐标除以横坐标？先看清是谁除以谁。",
         purified="三角板转正，导数有了几何的样子。"),
    dict(topic="math-derivative", subject="math", section="hard",
         name="极值双生", en="Extrema", element="导数为零", shape="round",
         head="peaks", prop="arrows", overlay="curve", skill="驻点伪装",
         taunt="f′=0 就是极值？山顶和山谷我可都占着。",
         purified="双胞胎分开站好：还要看两侧符号怎么变。"),
    dict(topic="math-derivative", subject="math", section="practice",
         name="ε 幽灵", en="Epsilon", element="无穷小", shape="ghost",
         head="field", prop="epsilon", overlay="waves", skill="趋近未达",
         taunt="我无限接近 0，可我从来不等于 0。",
         purified="幽灵淡到看不见，极限却稳稳落了下来。"),
    dict(topic="math-derivative", subject="math", section="boss",
         tier="big", name="高斯", en="C. F. Gauss", card_id="gauss",
         element="数学王子", staff="bell", skill="极限审判",
         taunt="少一点，但成熟一点。先把定义讲清楚。",
         purified="他在钟形曲线旁签下名字：这一关，你过了。"),
    # ===== 物理 · 牛顿运动定律 =====
    dict(topic="physics-newton", subject="physics", section="quick",
         name="惯性球", en="Inerto", element="固执惯性", shape="round",
         head="gauge", prop="weight", overlay="scale", skill="原地装死",
         taunt="不动！我就是不动！有本事把我的合外力变成零再来。",
         purified="它终于滚动起来：力不是维持运动的原因，是改变运动的原因。"),
    dict(topic="physics-newton", subject="physics", section="basic",
         name="斜面兽", en="Inclino", element="变幻斜坡", shape="round",
         head="triangle", prop="slash", overlay="diagonal", skill="倾角乱变",
         taunt="θ 取什么值，我的加速度就唱什么歌～",
         purified="斜面放平：a = g·sinθ，两个极端检验全过。"),
    dict(topic="physics-newton", subject="physics", section="summary",
         name="矢量雾", en="Vecto", element="迷失方向", shape="ghost",
         head="field", prop="none", overlay="waves", skill="分量障眼法",
         taunt="F 和 a 被我拆得七零八落，你还拼得回来吗？",
         purified="雾中分量归位：x 方向 y 方向，各列各的牛二。"),
    dict(topic="physics-newton", subject="physics", section="hard",
         name="失重幽灵", en="Floaty", element="视重错觉", shape="ghost",
         head="mirror", prop="bubbles", overlay="layers", skill="视重戏法",
         taunt="我轻了！我失重了！——不，是你的支持力在骗你。",
         purified="幽灵现形：重力没变，变的只是体重计的读数。"),
    dict(topic="physics-newton", subject="physics", section="practice",
         name="传送带将", en="Belty", element="皮带空转", shape="tank",
         head="gear", prop="crank", overlay="cogs", skill="摩擦反转",
         taunt="我的摩擦力一会儿向前一会儿向后，你猜猜看？",
         purified="皮带停稳：摩擦力方向看相对运动趋势，不再靠猜。"),
    dict(topic="physics-newton", subject="physics", section="boss",
         tier="big", name="牛顿", en="Isaac Newton", card_id="newton",
         element="万有引力与三定律", staff="apple", skill="巨肩审判",
         taunt="如果说我看得更远，那是因为我站在巨人的肩上。现在，轮到你往上爬了。",
         purified="他从苹果树下起身：这颗果实，交给你了。"),
    # ===== 物理 · 匀变速直线运动与运动学 =====
    dict(topic="physics-kinematics", subject="physics", section="quick",
         name="位移小怪", en="Displa", element="位移路程混淆", shape="round",
         head="bulb", prop="arrows", overlay="grid", skill="方向迷宫",
         taunt="从原点走一圈回到原点，你的位移可不是路程哦～",
         purified="小怪立正：位移看初末位置向量，路程看实际轨迹长度。"),
    dict(topic="physics-kinematics", subject="physics", section="basic",
         name="斜率尺", en="Slopey", element="v-t图像斜率", shape="tank",
         head="ruler", prop="segment", overlay="diagonal", skill="加速度倾角",
         taunt="看我直线的倾角！斜率越陡，速度变得越快！",
         purified="直尺放平：v-t 图的斜率是 a，面积是位移 x。"),
    dict(topic="physics-kinematics", subject="physics", section="summary",
         name="打点机", en="Ticker", element="纸带逐差法", shape="round",
         head="gauge", prop="bolt", overlay="spark", skill="等时位移差",
         taunt="滴答滴答！连续相邻相等时间的位移差 Δx = aT² 记住了吗？",
         purified="纸带拉平：逐差法消误差，运动学公式一条链。"),
    dict(topic="physics-kinematics", subject="physics", section="hard",
         name="刹车陷阱兽", en="Braker", element="刹车时间陷阱", shape="ghost",
         head="peaks", prop="weight", overlay="layers", skill="逆向反推",
         taunt="汽车停了还继续倒车？多少人算错刹车时间！",
         purified="陷阱排除：先求停下时间，速度为零后位移不再增加。"),
    dict(topic="physics-kinematics", subject="physics", section="practice",
         name="追及双雄", en="Chaser", element="追及相遇临界", shape="tank",
         head="balance", prop="arrows", overlay="curve", skill="共速临界",
         taunt="速度相等那一瞬间，是距离最大还是恰好不撞？",
         purified="双车并排：共速即临界，距离极值一眼看透。"),
    dict(topic="physics-kinematics", subject="physics", section="boss",
         tier="big", name="伽利略", en="Galileo Galilei", card_id="galileo",
         element="自由落体与斜面实验", staff="pendulum", skill="落体审判",
         taunt="重物和轻物同时落地！我的斜面实验已经为你铺好了路。",
         purified="他放下水钟与小球：实验与数学的结合，这就是近代物理的开端。"),
    # ===== 物理 · 机械能与功能关系 =====
    dict(topic="physics-energy", subject="physics", section="quick",
         name="焦耳豆", en="Jouly", element="乱窜热量", shape="round",
         head="bulb", prop="bolt", overlay="spark", skill="能量乱窜",
         taunt="能量守恒！可我藏在哪个口袋里，你找不到～",
         purified="豆子亮起来：能量没有消失，只是换了口袋。"),
    dict(topic="physics-energy", subject="physics", section="basic",
         name="动能兽", en="Kineco", element="速度平方陷阱", shape="round",
         head="gauge", prop="segment", overlay="diagonal", skill="平方迷惑",
         taunt="速度翻倍？我可不是翻倍那么简单。",
         purified="它排成一行：½mv²，那个平方终于被看清了。"),
    dict(topic="physics-energy", subject="physics", section="summary",
         name="守恒钟", en="Conso", element="恒定总量", shape="tank",
         head="balance", prop="weight", overlay="scale", skill="天平摇摆",
         taunt="左边动能右边势能，加减你来算！",
         purified="天平放平：Ek + Ep，左右永远相等。"),
    dict(topic="physics-energy", subject="physics", section="hard",
         name="摩擦双生", en="Fricto", element="生热诡辩", shape="round",
         head="mirror", prop="bubbles", overlay="layers", skill="相对路程",
         taunt="我做的功和产生的热，可不是一回事哦～",
         purified="双生合体：Q = f × 相对路程，这才是完整答案。"),
    dict(topic="physics-energy", subject="physics", section="practice",
         name="过山车将", en="Coaster", element="竖直圆环", shape="tank",
         head="peaks", prop="arrows", overlay="curve", skill="环顶失重",
         taunt="最高点为什么掉不下来？先算算你的向心加速度！",
         purified="轨道贯通：守恒求速度，牛二求力，一气呵成。"),
    dict(topic="physics-energy", subject="physics", section="boss",
         tier="big", name="伽利略", en="Galileo Galilei", card_id="galileo",
         element="理想实验", staff="pendulum", skill="斜面审判",
         taunt="我的斜面没有摩擦，我的推理没有终点。来，接住这个摆锤。",
         purified="他把摆锤挂回原位：它还会摆回来，这就是守恒。"),
    # ===== 化学 · 氧化还原反应 =====
    dict(topic="chemistry-redox", subject="chemistry", section="quick",
         name="电子跳蚤", en="Fleco", element="电子乱窜", shape="round",
         head="bulb", prop="bolt", overlay="spark", skill="电子争夺",
         taunt="抢电子！谁先抢到听谁的！",
         purified="跳蚤安分下来：得失电子总数终于相等了。"),
    dict(topic="chemistry-redox", subject="chemistry", section="basic",
         name="歪价签", en="Tagger", element="乱标价态", shape="round",
         head="ruler", prop="segment", overlay="grid", skill="价态涂鸦",
         taunt="0、+1、+5、−1……我随口报数，你敢接吗？",
         purified="价签排齐：先定 H 是 +1、O 是 −2，再解未知数。"),
    dict(topic="chemistry-redox", subject="chemistry", section="summary",
         name="双线桥怪", en="Bridgey", element="桥线缠绕", shape="ghost",
         head="zigzag", prop="none", overlay="waves", skill="箭头打结",
         taunt="两条线该从谁指到谁？绕晕你为止～",
         purified="线桥理顺：双线桥自指前后，单线桥跨元素。"),
    dict(topic="chemistry-redox", subject="chemistry", section="hard",
         name="歧化双脸", en="Disco", element="价态分裂", shape="round",
         head="mirror", prop="arrows", overlay="reverse", skill="一升一降",
         taunt="我一半升高一半降低，中间价态最刺激！",
         purified="双脸合拢：归中不交叉，歧化各一半。"),
    dict(topic="chemistry-redox", subject="chemistry", section="practice",
         name="配平天平将", en="Stoi", element="系数乱配", shape="tank",
         head="balance", prop="weight", overlay="scale", skill="守恒偷懒",
         taunt="电子守恒？我先随便配个系数凑合一下～",
         purified="天平锁定：得失电子相等，系数自然落位。"),
    dict(topic="chemistry-redox", subject="chemistry", section="boss",
         tier="big", name="拉瓦锡", en="Antoine Lavoisier", card_id="lavoisier",
         element="质量守恒", staff="burner", skill="天平审判",
         taunt="无物新生，无物消亡——先称一称，你到底带来了什么。",
         purified="他把天平递给你：质量守恒，现在也归你保管了。"),
    # ===== 化学 · 物质的量 =====
    dict(topic="chemistry-mole", subject="chemistry", section="quick",
         name="摩尔豆", en="Moley", element="数不清粒子", shape="round",
         head="tube", prop="bubbles", overlay="bubbles", skill="数数大法",
         taunt="6.02×10²³ 个粒子，你慢慢数～",
         purified="豆子排成整齐一列：n = N/NA，数数有了公式。"),
    dict(topic="chemistry-mole", subject="chemistry", section="basic",
         name="天平兽", en="Weighy", element="称量错位", shape="round",
         head="balance", prop="weight", overlay="scale", skill="单位陷阱",
         taunt="18、18 g、18 g/mol——你分得清我是谁？",
         purified="三张标签贴对位置：数值相等，身份不同。"),
    dict(topic="chemistry-mole", subject="chemistry", section="summary",
         name="量筒怪", en="Beako", element="刻度失真", shape="ghost",
         head="beaker", prop="none", overlay="layers", skill="液体冒充",
         taunt="标况下我也是 22.4 L 哦——真的吗？",
         purified="刻度清晰起来：22.4 L/mol 只属于标况下的气体。"),
    dict(topic="chemistry-mole", subject="chemistry", section="hard",
         name="22.4 幽灵", en="Gasly", element="气体幻影", shape="ghost",
         head="field", prop="epsilon", overlay="waves", skill="条件隐身",
         taunt="常温常压下我也能当 22.4 L……你就说信不信吧。",
         purified="幽灵退散：标况 + 气体，两个前提缺一不可。"),
    dict(topic="chemistry-mole", subject="chemistry", section="practice",
         name="配液将", en="Solution", element="浓度错配", shape="tank",
         head="gauge", prop="wrench", overlay="cogs", skill="定容迷惑",
         taunt="溶剂体积就是溶液体积？天真的孩子。",
         purified="容量瓶刻度线落定：c = n/V，V 是溶液的体积。"),
    dict(topic="chemistry-mole", subject="chemistry", section="boss",
         tier="big", name="阿伏伽德罗", en="Amedeo Avogadro", card_id="avogadro",
         element="气体定律", staff="molecule", skill="分子审判",
         taunt="同温同压，同体积必同分子数——这是我的定律，也是我的审判。",
         purified="他把分子模型递给你：数的桥，以后由你来架。"),
    # ===== 物理 · 电场强度与电势 =====
    dict(topic="physics-electric", subject="physics", section="quick",
         name="摩擦豆", en="Frictio", element="电子抢夺", shape="round",
         head="bulb", prop="bolt", overlay="spark", skill="静电粘身",
         taunt="噼啪！冬天摸门把手的那一下，就是我干的。",
         purified="豆子安静了：摩擦只是电子搬家，电荷总量从没变过。"),
    dict(topic="physics-electric", subject="physics", section="basic",
         name="扭秤妖", en="Torsio", element="平方反比陷阱", shape="round",
         head="gauge", prop="weight", overlay="scale", skill="距离翻倍",
         taunt="距离翻一倍，力减一半？你再想想。",
         purified="扭丝回正：力与距离的平方成反比，1/4 才对。"),
    dict(topic="physics-electric", subject="physics", section="summary",
         name="场线怪", en="Fieldy", element="场线迷雾", shape="ghost",
         head="field", prop="arrows", overlay="curve", skill="疏密迷阵",
         taunt="我的线越密，你就越站不稳——猜猜哪边场强大？",
         purified="迷雾散开：线密处场强大，切线就是场强方向。"),
    dict(topic="physics-electric", subject="physics", section="hard",
         name="零势鬼", en="Nullvolt", element="零势陷阱", shape="ghost",
         head="mirror", prop="epsilon", overlay="layers", skill="势场错位",
         taunt="这里电势是零哦——所以你一定推不出场强吧？",
         purified="鬼影透明：电势为零，场强未必为零，两件事互不干扰。"),
    dict(topic="physics-electric", subject="physics", section="practice",
         name="等势盘", en="Equipo", element="等势面错位", shape="tank",
         head="balance", prop="segment", overlay="diagonal", skill="路径迷惑",
         taunt="沿我这一圈走，电场力做的功你敢说不是零？",
         purified="盘面平放：等势面上移动电荷，电场力确实不做功。"),
    dict(topic="physics-electric", subject="physics", section="boss",
         tier="big", name="库仑", en="Charles-Augustin de Coulomb", card_id="coulomb",
         element="平方反比", staff="orb", skill="扭丝审判",
         taunt="我用一根扭丝量出了看不见的力。你，能量出自己错在哪吗？",
         purified="他把带电小球放回原处：力与距离平方成反比，记住它。"),
    # ===== 化学 · 元素周期律 =====
    dict(topic="chemistry-periodic", subject="chemistry", section="quick",
         name="周期蛙", en="Periodi", element="层数混淆", shape="round",
         head="bulb", prop="segment", overlay="diagonal", skill="数层大法",
         taunt="我住第三周期——你猜我有几层电子？",
         purified="蛙眼一亮：周期数就是电子层数，别和族序数对调。"),
    dict(topic="chemistry-periodic", subject="chemistry", section="basic",
         name="族序怪", en="Groupy", element="族序错位", shape="round",
         head="ruler", prop="arrows", overlay="layers", skill="横纵迷阵",
         taunt="最外层 7 个电子，你说我在第ⅦB 族？",
         purified="尺子摆正：最外层电子数 = 主族序数，是 A 不是 B。"),
    dict(topic="chemistry-periodic", subject="chemistry", section="summary",
         name="表匠", en="Gridsmith", element="方格迷宫", shape="tank",
         head="gear", prop="crank", overlay="grid", skill="空格设伏",
         taunt="我的表格里有空格——猜错了，整张表都要重排。",
         purified="齿轮咬合：位置、结构、性质，三者可以互相推导。"),
    dict(topic="chemistry-periodic", subject="chemistry", section="hard",
         name="半径精", en="Radix", element="半径迷雾", shape="round",
         head="gauge", prop="bubbles", overlay="spark", skill="大小幻术",
         taunt="核电荷数越大，我就越大——信我你就输了。",
         purified="雾气散去：电子层结构相同时，核电荷数越大半径越小。"),
    dict(topic="chemistry-periodic", subject="chemistry", section="practice",
         name="递变兽", en="Trendo", element="递变方向", shape="tank",
         head="peaks", prop="arrows", overlay="curve", skill="方向反转",
         taunt="往右走非金属性变弱？那我把整张表倒过来给你看。",
         purified="箭头归位：横着走越来越非金属，竖着走越来越金属。"),
    dict(topic="chemistry-periodic", subject="chemistry", section="boss",
         tier="big", name="门捷列夫", en="Dmitri Mendeleev", card_id="mendeleev",
         element="周期律", staff="grid", skill="空格预言",
         taunt="我在表上留了空格，还写下了里面元素的颜色和密度。你敢填吗？",
         purified="他把表铺开：镓、锗、锑——空格被实验一一填满。"),
    # ===== 化学 · 离子反应 =====
    dict(topic="chemistry-ionic", subject="chemistry", section="quick",
         name="电离鬼", en="Ionix", element="电离迷雾", shape="ghost",
         head="tube", prop="bubbles", overlay="spark", skill="真假电解质",
         taunt="我溶于水就导电——所以我是电解质，对吧？",
         purified="鬼影显形：先看是不是化合物，再看是不是自己在电离。"),
    dict(topic="chemistry-ionic", subject="chemistry", section="basic",
         name="拆写怪", en="Splitz", element="拆与不拆", shape="round",
         head="mirror", prop="segment", overlay="diagonal", skill="乱拆一气",
         taunt="碳酸钙？拆成 Ca²⁺ 和 CO₃²⁻ 多清爽！",
         purified="镜子照回原形：难溶物写化学式，一步都不能拆。"),
    dict(topic="chemistry-ionic", subject="chemistry", section="summary",
         name="旁观猿", en="Bystando", element="旁观离子", shape="round",
         head="zigzag", prop="epsilon", overlay="waves", skill="多余出场",
         taunt="我什么都没干，可你的方程式里全是我的名字。",
         purified="猿猴退场：不参加反应的离子，写完就该删掉。"),
    dict(topic="chemistry-ionic", subject="chemistry", section="hard",
         name="过量兽", en="Excess", element="少量过量", shape="tank",
         head="balance", prop="weight", overlay="scale", skill="配比翻盘",
         taunt="少量还是过量？我一句话就能让你的产物全变。",
         purified="天平落定：先看谁少量，按少量物质的配比写方程。"),
    dict(topic="chemistry-ionic", subject="chemistry", section="practice",
         name="共存兽", en="Coexist", element="四类冲突", shape="tank",
         head="magnet", prop="arrows", overlay="curve", skill="打架判定",
         taunt="把 Ba²⁺ 和 SO₄²⁻ 放一个杯子里，你猜还剩几个？",
         purified="磁力松开：沉淀、气体、弱电解质、氧化还原——四类才打架。"),
    dict(topic="chemistry-ionic", subject="chemistry", section="boss",
         tier="big", name="阿伦尼乌斯", en="Svante Arrhenius", card_id="arrhenius",
         element="电离学说", staff="ion", skill="离子审判",
         taunt="他们说我的学说荒谬。现在，请你告诉我谁在水里解离。",
         purified="他把离子对举起来：电解质在水中自发解离，这就是导电的原因。"),
]

# ---------------------------------------------------------------- SVG 部件库


def _defs(c: dict, big: bool) -> str:
    gold = "#fbbf24"
    return f"""<defs>
  <linearGradient id="body" x1="0" y1="0" x2="0" y2="1">
    <stop offset="0" stop-color="{c['light']}"/>
    <stop offset=".55" stop-color="{c['main']}"/>
    <stop offset="1" stop-color="{c['dark']}"/>
  </linearGradient>
  <linearGradient id="glass" x1="0" y1="0" x2="1" y2="1">
    <stop offset="0" stop-color="#ffffff" stop-opacity=".75"/>
    <stop offset=".45" stop-color="#ffffff" stop-opacity=".08"/>
    <stop offset="1" stop-color="#ffffff" stop-opacity=".35"/>
  </linearGradient>
  <linearGradient id="metal" x1="0" y1="0" x2="0" y2="1">
    <stop offset="0" stop-color="#f1f5f9"/>
    <stop offset="1" stop-color="#94a3b8"/>
  </linearGradient>
  <radialGradient id="halo">
    <stop offset="0" stop-color="{c['halo']}" stop-opacity=".85"/>
    <stop offset=".7" stop-color="{c['halo']}" stop-opacity=".22"/>
    <stop offset="1" stop-color="{c['halo']}" stop-opacity="0"/>
  </radialGradient>
  <radialGradient id="glow">
    <stop offset="0" stop-color="{c['accent']}" stop-opacity=".9"/>
    <stop offset="1" stop-color="{c['accent']}" stop-opacity="0"/>
  </radialGradient>
  <linearGradient id="robe" x1="0" y1="0" x2="0" y2="1">
    <stop offset="0" stop-color="#ffffff"/>
    <stop offset="1" stop-color="#dbe4f0"/>
  </linearGradient>
  {'<linearGradient id="gold" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#fde68a"/><stop offset="1" stop-color="#d97706"/></linearGradient>' if big else ''}
</defs>"""


def _stage(c: dict, big: bool) -> str:
    ring = "#fbbf24" if big else c["line"]
    return f"""<ellipse cx="120" cy="258" rx="66" ry="9" fill="#0f172a" opacity=".10"/>
<circle cx="120" cy="140" r="98" fill="url(#halo)"/>
<ellipse cx="120" cy="248" rx="58" ry="10" fill="none" stroke="{ring}" stroke-width="2" opacity=".45"/>
<ellipse cx="120" cy="248" rx="46" ry="7" fill="none" stroke="{ring}" stroke-width="1" opacity=".25" stroke-dasharray="4 5"/>"""


def _bolt(cx: float, cy: float, c: dict, gold: bool = False) -> str:
    fill = "url(#gold)" if gold else "url(#metal)"
    stroke = "#b45309" if gold else "#64748b"
    return f"""<g transform="translate({cx} {cy})">
  <polygon points="-9,-5 0,-10 9,-5 9,5 0,10 -9,5" fill="{fill}" stroke="{stroke}" stroke-width="1.5"/>
  <path d="M-4 0 H4 M0 -4 V4" stroke="{stroke}" stroke-width="1.6" stroke-linecap="round"/>
</g>"""


def _stitches(y: float = 80, x1: float = 84, x2: float = 156, color: str = "#1e293b") -> str:
    """额头缝合线：怪人军团的统一印记。"""
    seg = f'<path d="M{x1} {y} Q120 {y + 5} {x2} {y}" fill="none" stroke="{color}" stroke-width="2" opacity=".7"/>'
    ticks = "".join(
        f'<path d="M{x} {y - 6} l3 11" stroke="{color}" stroke-width="1.7" stroke-linecap="round" opacity=".7"/>'
        for x in range(int(x1) + 8, int(x2) - 4, 13)
    )
    return seg + ticks


def _eyes(kind: str, c: dict) -> str:
    """眼型：round 圆眼 / sly 眯眼 / twin 四眼 / spark 星眼。"""
    def eye(x: int, y: int, r: float = 11) -> str:
        return (f'<circle cx="{x}" cy="{y}" r="{r}" fill="#fff" stroke="#1e293b" stroke-width="2"/>'
                f'<circle cx="{x + 2}" cy="{y + 1}" r="{r * .5:.1f}" fill="#1e293b"/>'
                f'<circle cx="{x}" cy="{y - 2}" r="{r * .24:.1f}" fill="#fff"/>')

    def star(x: int, y: int) -> str:
        return (f'<path d="M{x} {y-4} l1.3 2.7 2.7 1.3 -2.7 1.3 -1.3 2.7 '
                f'-1.3 -2.7 -2.7 -1.3 2.7 -1.3z" fill="{c["accent"]}"/>')

    if kind == "sly":
        return (f'<path d="M92 108 q11 -10 22 0 M126 108 q11 -10 22 0" fill="none" '
                f'stroke="#1e293b" stroke-width="3" stroke-linecap="round"/>'
                f'<circle cx="103" cy="112" r="2" fill="{c["dark"]}"/>'
                f'<circle cx="137" cy="112" r="2" fill="{c["dark"]}"/>')
    if kind == "twin":
        return (eye(100, 100, 8) + eye(140, 100, 8)
                + eye(102, 126, 6) + eye(138, 126, 6))
    if kind == "spark":
        return eye(103, 108) + eye(137, 108) + star(116, 94) + star(150, 94)
    return eye(103, 108) + eye(137, 108)


def _mouth(mood: str, dy: int = 0) -> str:
    if mood == "grin":
        inner = ('<path d="M104 130 q16 16 32 0 q-16 6 -32 0z" fill="#1e293b"/>'
                 '<path d="M110 133 l3 5 3 -4 3 5 3 -4 3 5 3 -4" fill="none" stroke="#fff" stroke-width="1.6"/>')
    elif mood == "o":
        inner = ('<ellipse cx="120" cy="133" rx="7" ry="9" fill="#1e293b"/>'
                 '<ellipse cx="120" cy="136" rx="3" ry="3" fill="#fb7185"/>')
    else:
        inner = ('<path d="M106 132 q14 12 28 0" fill="none" stroke="#1e293b" '
                 'stroke-width="2.6" stroke-linecap="round"/>'
                 '<path d="M120 132 v4" stroke="#1e293b" stroke-width="2" stroke-linecap="round"/>')
    return f'<g transform="translate(0 {dy})">{inner}</g>'


def _body(shape: str, c: dict) -> str:
    """躯干轮廓 + 围裙 + 螺栓 + 手臂 + 脚。"""
    if shape == "tank":
        outline = ('<path d="M76 168 q0 -18 20 -18 h48 q20 0 20 18 v58 '
                   'q0 18 -20 18 h-48 q-20 0 -20 -18z" fill="url(#body)" '
                   'stroke="#1e293b" stroke-width="3"/>')
    elif shape == "ghost":
        outline = ('<path d="M78 168 q0 -20 22 -20 h40 q22 0 22 20 v58 '
                   'l-12 12 -12 -12 -12 12 -12 -12 -12 12 -12 -12z" '
                   'fill="url(#body)" stroke="#1e293b" stroke-width="3" opacity=".92"/>')
    else:
        outline = ('<path d="M74 176 q0 -26 26 -26 h40 q26 0 26 26 v46 '
                   'q0 22 -24 22 h-44 q-24 0 -24 -22z" fill="url(#body)" '
                   'stroke="#1e293b" stroke-width="3"/>')
    apron = (f'<path d="M96 158 h48 l8 76 q-32 12 -64 0z" fill="#f8fafc" opacity=".92"/>'
             f'<path d="M96 158 h48 l8 76 q-32 12 -64 0z" fill="none" stroke="{c["line"]}" '
             f'stroke-width="1.6" opacity=".5"/>'
             f'<path d="M104 196 h32 v18 h-32z" fill="none" stroke="{c["line"]}" '
             f'stroke-width="1.6" opacity=".55"/>'
             f'<path d="M120 196 v18" stroke="{c["line"]}" stroke-width="1.4" opacity=".4"/>')
    arms = (f'<g><rect x="58" y="166" width="20" height="46" rx="10" fill="{c["main"]}" '
            f'stroke="#1e293b" stroke-width="2.6"/>'
            f'<rect x="162" y="166" width="20" height="46" rx="10" fill="{c["main"]}" '
            f'stroke="#1e293b" stroke-width="2.6"/>'
            f'<circle cx="68" cy="214" r="10" fill="{c["light"]}" stroke="#1e293b" stroke-width="2.4"/>'
            f'<circle cx="172" cy="214" r="10" fill="{c["light"]}" stroke="#1e293b" stroke-width="2.4"/>'
            # 左手绷带：统一细节
            f'<path d="M59 186 l18 -7 M59 196 l18 -7" stroke="#f8fafc" stroke-width="4" '
            f'stroke-linecap="round" opacity=".95"/></g>')
    feet = (f'<rect x="94" y="232" width="22" height="16" rx="8" fill="{c["dark"]}" stroke="#1e293b" stroke-width="2"/>'
            f'<rect x="124" y="232" width="22" height="16" rx="8" fill="{c["dark"]}" stroke="#1e293b" stroke-width="2"/>')
    return outline + apron + arms + feet + _bolt(88, 154, c) + _bolt(152, 154, c)


def _overlay(kind: str, c: dict) -> str:
    """躯干纹理：让同谱系的角色各有辨识度。"""
    if kind == "spark":
        return (f'<path d="M104 176 l6 10 -6 8 9 -2 M136 190 l-5 9 7 6" fill="none" '
                f'stroke="{c["accent"]}" stroke-width="3" stroke-linecap="round" opacity=".9"/>'
                f'<circle cx="112" cy="214" r="3" fill="{c["accent"]}"/>'
                f'<circle cx="130" cy="220" r="2" fill="{c["accent"]}"/>')
    if kind == "coils":
        return "".join(
            f'<path d="M92 {y} q28 12 56 0" fill="none" stroke="{c["accent"]}" '
            f'stroke-width="3" opacity=".85"/>' for y in (176, 192, 208, 224))
    if kind == "waves":
        return "".join(
            f'<path d="M88 {y} q16 -10 32 0 t32 0" fill="none" stroke="{c["accent"]}" '
            f'stroke-width="2.4" opacity=".7"/>' for y in (180, 198, 216))
    if kind == "reverse":
        return (f'<path d="M96 188 h44 m0 0 l-9 -7 m9 7 l-9 7" stroke="{c["accent"]}" '
                f'stroke-width="3" fill="none" stroke-linecap="round" stroke-linejoin="round"/>'
                f'<path d="M144 212 h-44 m0 0 l9 -7 m-9 7 l9 7" stroke="{c["accent"]}" '
                f'stroke-width="3" fill="none" stroke-linecap="round" stroke-linejoin="round"/>')
    if kind == "cogs":
        return (f'<circle cx="120" cy="204" r="22" fill="none" stroke="{c["accent"]}" stroke-width="3" opacity=".8"/>'
                f'<circle cx="120" cy="204" r="7" fill="none" stroke="{c["accent"]}" stroke-width="3" opacity=".8"/>'
                + "".join(f'<path d="M120 {182 - 0} v-8" stroke="{c["accent"]}" stroke-width="3" '
                          f'transform="rotate({a} 120 204)"/>' for a in range(0, 360, 45)))
    if kind == "bubbles":
        return "".join(
            f'<circle cx="{x}" cy="{y}" r="{r}" fill="none" stroke="{c["accent"]}" stroke-width="2" opacity=".85"/>'
            for x, y, r in ((104, 184, 5), (128, 176, 3), (136, 206, 7), (106, 220, 4)))
    if kind == "scale":
        return "".join(
            f'<path d="M100 {y} h40" stroke="{c["accent"]}" stroke-width="2" opacity=".65"/>'
            for y in (180, 192, 204, 216, 228))
    if kind == "layers":
        return (f'<path d="M92 190 q28 8 56 0 v14 q-28 8 -56 0z" fill="{c["accent"]}" opacity=".35"/>'
                f'<path d="M92 212 q28 8 56 0 v14 q-28 8 -56 0z" fill="{c["accent"]}" opacity=".55"/>')
    if kind == "diagonal":
        return (f'<path d="M92 228 L148 172" stroke="{c["accent"]}" stroke-width="4" '
                f'stroke-linecap="round" opacity=".85"/>'
                f'<path d="M92 228 l0 -12 M148 172 l0 12" stroke="{c["accent"]}" stroke-width="2" opacity=".6"/>')
    if kind == "grid":
        return ("".join(f'<path d="M96 {y} h48" stroke="{c["accent"]}" stroke-width="1.4" opacity=".45"/>'
                        for y in (178, 192, 206, 220))
                + "".join(f'<path d="M{x} 170 v62" stroke="{c["accent"]}" stroke-width="1.4" opacity=".45"/>'
                          for x in (104, 120, 136)))
    if kind == "curve":
        return (f'<path d="M92 222 q14 -46 28 -20 t28 -22" fill="none" '
                f'stroke="{c["accent"]}" stroke-width="3.2" stroke-linecap="round"/>'
                f'<path d="M92 226 h56" stroke="{c["accent"]}" stroke-width="1.6" opacity=".6"/>')
    return ""


def _head(kind: str, c: dict) -> str:
    """头顶装饰：每只怪的标志物。"""
    a = c["accent"]
    d = c["dark"]
    if kind == "bulb":
        return (f'<circle cx="120" cy="46" r="26" fill="url(#glow)"/>'
                f'<path d="M120 22 a17 17 0 0 1 11 30 v7 h-22 v-7 a17 17 0 0 1 11 -30z" '
                f'fill="#fef9c7" stroke="{d}" stroke-width="2.4"/>'
                f'<path d="M112 59 h16 v8 a8 8 0 0 1 -16 0z" fill="url(#metal)" stroke="{d}" stroke-width="2"/>'
                f'<path d="M114 34 q-6 8 -2 16" stroke="#fff" stroke-width="3" fill="none" opacity=".8"/>'
                f'<path d="M120 68 v8" stroke="{d}" stroke-width="3"/>')
    if kind == "magnet":
        return (f'<path d="M96 66 v-24 a24 24 0 0 1 48 0 v24" fill="none" stroke="{a}" '
                f'stroke-width="11" stroke-linecap="round"/>'
                f'<path d="M96 58 h12 M132 58 h12" stroke="#f8fafc" stroke-width="11"/>'
                f'<path d="M96 42 v24 M144 42 v24" stroke="{d}" stroke-width="1.4" opacity=".4"/>')
    if kind == "field":
        return (f'<g fill="none" stroke="{a}" stroke-width="2.4" opacity=".9">'
                f'<ellipse cx="120" cy="50" rx="34" ry="12"/>'
                f'<ellipse cx="120" cy="50" rx="24" ry="7"/>'
                f'<ellipse cx="120" cy="50" rx="13" ry="3"/></g>'
                f'<circle cx="120" cy="50" r="4" fill="{a}"/>')
    if kind == "mirror":
        return (f'<path d="M120 28 l-10 12 h20z" fill="{a}" stroke="{d}" stroke-width="2"/>'
                f'<path d="M120 70 l10 -12 h-20z" fill="{a}" stroke="{d}" stroke-width="2"/>'
                f'<path d="M120 32 v34" stroke="{d}" stroke-width="2" stroke-dasharray="3 4" opacity=".6"/>')
    if kind == "gear":
        pts = []
        import math
        for i in range(16):
            ang = math.pi * 2 * i / 16
            r = 24 if i % 2 == 0 else 18
            pts.append(f"{120 + r * math.cos(ang):.1f},{50 + r * math.sin(ang):.1f}")
        return (f'<polygon points="{" ".join(pts)}" fill="url(#metal)" stroke="{d}" stroke-width="2.2"/>'
                f'<circle cx="120" cy="50" r="8" fill="{a}" stroke="{d}" stroke-width="2"/>')
    if kind == "tube":
        return (f'<rect x="108" y="24" width="24" height="46" rx="6" fill="url(#glass)" '
                f'stroke="{d}" stroke-width="2.4"/>'
                f'<path d="M108 54 q12 5 24 0 v10 a6 6 0 0 1 -6 6 h-12 a6 6 0 0 1 -6 -6z" '
                f'fill="{a}" opacity=".8"/>'
                f'<rect x="104" y="20" width="32" height="7" rx="3" fill="url(#metal)" stroke="{d}" stroke-width="1.6"/>')
    if kind == "balance":
        return (f'<path d="M88 46 h64" stroke="{d}" stroke-width="3.4" stroke-linecap="round"/>'
                f'<path d="M120 46 v-16" stroke="{d}" stroke-width="3"/>'
                f'<circle cx="120" cy="28" r="4" fill="{a}" stroke="{d}" stroke-width="1.6"/>'
                f'<path d="M88 46 l-9 14 h18z M152 46 l-9 14 h18z" fill="{a}" stroke="{d}" stroke-width="2"/>')
    if kind == "beaker":
        return (f'<path d="M104 26 h32 l-4 40 a8 8 0 0 1 -8 7 h-8 a8 8 0 0 1 -8 -7z" '
                f'fill="url(#glass)" stroke="{d}" stroke-width="2.4"/>'
                f'<path d="M106 54 h28 l-2 12 a8 8 0 0 1 -8 7 h-8 a8 8 0 0 1 -8 -7z" '
                f'fill="{a}" opacity=".75"/>'
                f'<circle cx="114" cy="42" r="3" fill="#fff" opacity=".9"/>'
                f'<circle cx="126" cy="34" r="2" fill="#fff" opacity=".9"/>')
    if kind == "gauge":
        return (f'<circle cx="120" cy="48" r="22" fill="#f8fafc" stroke="{d}" stroke-width="2.6"/>'
                f'<path d="M104 56 a16 16 0 0 1 32 0" fill="none" stroke="{a}" stroke-width="2.4"/>'
                f'<path d="M120 48 l10 -10" stroke="#ef4444" stroke-width="2.6" stroke-linecap="round"/>'
                f'<circle cx="120" cy="48" r="3" fill="{d}"/>')
    if kind == "ruler":
        return (f'<rect x="82" y="26" width="76" height="20" rx="3" fill="url(#metal)" '
                f'stroke="{d}" stroke-width="2.2" transform="rotate(-12 120 36)"/>'
                + "".join(f'<path d="M{x} 26 v7" stroke="{d}" stroke-width="1.6" '
                          f'transform="rotate(-12 120 36)"/>' for x in range(90, 155, 10)))
    if kind == "zigzag":
        return (f'<path d="M88 62 l14 -18 16 14 16 -18 14 18" fill="none" stroke="{a}" '
                f'stroke-width="4" stroke-linecap="round" stroke-linejoin="round"/>'
                f'<circle cx="88" cy="62" r="3.5" fill="{d}"/><circle cx="148" cy="58" r="3.5" fill="{d}"/>')
    if kind == "triangle":
        return (f'<path d="M94 66 L120 22 L146 66z" fill="url(#glass)" stroke="{d}" stroke-width="2.6"/>'
                f'<path d="M120 36 L136 62 H104z" fill="none" stroke="{a}" stroke-width="2" opacity=".8"/>')
    if kind == "peaks":
        return (f'<path d="M86 66 q14 -34 28 -6 q6 -34 20 -30 q14 4 20 36" fill="none" '
                f'stroke="{a}" stroke-width="4" stroke-linecap="round"/>'
                f'<circle cx="108" cy="52" r="4" fill="{d}"/><circle cx="140" cy="34" r="4" fill="{d}"/>')
    return ""


def _prop(kind: str, c: dict) -> str:
    """右手 / 双手持物。"""
    a, d = c["accent"], c["dark"]
    if kind == "bolt":
        return (f'<path d="M186 168 l-14 20 h10 l-8 20 20 -26 h-11 l8 -14z" fill="{a}" '
                f'stroke="{d}" stroke-width="2.2" stroke-linejoin="round"/>')
    if kind == "coil":
        return ("".join(f'<ellipse cx="186" cy="{y}" rx="14" ry="5" fill="none" '
                        f'stroke="{a}" stroke-width="3"/>' for y in (176, 186, 196, 206)))
    if kind == "arrows":
        return (f'<path d="M178 174 h22 m0 0 l-7 -6 m7 6 l-7 6" stroke="{a}" stroke-width="3" '
                f'fill="none" stroke-linecap="round" stroke-linejoin="round"/>'
                f'<path d="M200 198 h-22 m0 0 l7 -6 m-7 6 l7 6" stroke="{a}" stroke-width="3" '
                f'fill="none" stroke-linecap="round" stroke-linejoin="round"/>')
    if kind == "crank":
        return (f'<path d="M172 208 l20 -22" stroke="{d}" stroke-width="4" stroke-linecap="round"/>'
                f'<circle cx="194" cy="184" r="8" fill="url(#metal)" stroke="{d}" stroke-width="2"/>')
    if kind == "bubbles":
        return (f'<rect x="178" y="182" width="18" height="36" rx="5" fill="url(#glass)" stroke="{d}" stroke-width="2"/>'
                f'<path d="M178 202 h18 v11 a5 5 0 0 1 -5 5 h-8 a5 5 0 0 1 -5 -5z" fill="{a}" opacity=".8"/>'
                f'<circle cx="187" cy="170" r="4" fill="none" stroke="{a}" stroke-width="2"/>'
                f'<circle cx="196" cy="158" r="2.5" fill="none" stroke="{a}" stroke-width="2"/>')
    if kind == "weight":
        return (f'<path d="M178 206 h22 l-3 14 h-16z" fill="url(#metal)" stroke="{d}" stroke-width="2"/>'
                f'<path d="M189 206 v-14" stroke="{d}" stroke-width="2"/>'
                f'<circle cx="189" cy="190" r="4" fill="{a}" stroke="{d}" stroke-width="1.6"/>')
    if kind == "wrench":
        return (f'<path d="M188 168 a10 10 0 1 0 8 16 l-24 24 6 6 24 -24" fill="none" '
                f'stroke="{d}" stroke-width="5" stroke-linecap="round"/>')
    if kind == "slash":
        return (f'<path d="M176 216 L206 172" stroke="{a}" stroke-width="6" stroke-linecap="round"/>'
                f'<path d="M176 216 l0 -12 M206 172 l0 12" stroke="{d}" stroke-width="2"/>')
    if kind == "segment":
        return (f'<path d="M176 212 L206 178" stroke="{a}" stroke-width="4" stroke-linecap="round"/>'
                f'<circle cx="176" cy="212" r="4" fill="#fff" stroke="{d}" stroke-width="2"/>'
                f'<circle cx="206" cy="178" r="4" fill="#fff" stroke="{d}" stroke-width="2"/>')
    if kind == "epsilon":
        return (f'<text x="176" y="212" font-family="Georgia,serif" font-size="46" '
                f'font-style="italic" fill="{a}" stroke="{d}" stroke-width=".8">ε</text>')
    return ""


def _number_tag(code: str, big: bool) -> str:
    fill = "url(#gold)" if big else "#f8fafc"
    stroke = "#b45309" if big else "#94a3b8"
    label = "BOSS" if big else code
    return (f'<g><rect x="176" y="18" width="46" height="20" rx="10" fill="{fill}" '
            f'stroke="{stroke}" stroke-width="1.6"/>'
            f'<text x="199" y="32" text-anchor="middle" font-family="Arial,Helvetica,sans-serif" '
            f'font-size="11" font-weight="bold" fill="#1e293b">{label}</text></g>')


def render_mini(role: dict, c: dict, code: str) -> str:
    shape = role["shape"]
    head_kind = role["head"]
    eye_by_section = {"quick": "spark", "basic": "sly", "summary": "round",
                      "hard": "twin", "practice": "round"}
    eye_kind = ("twin" if head_kind in ("mirror", "peaks")
                else eye_by_section.get(role["section"], "round"))
    mood = "grin" if role["section"] == "quick" else ("o" if shape == "ghost" else "smile")
    mouth_dy = 12 if eye_kind == "twin" else 0
    parts = [
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 240 280" width="240" height="280" '
        'role="img" aria-label="' + role["name"] + '">',
        _defs(c, False),
        _stage(c, False),
        _number_tag(code, False),
        _head(head_kind, c),
        _body(shape, c),
        _overlay(role["overlay"], c),
        # 头（盖在身体上）
        f'<rect x="76" y="66" width="88" height="86" rx="34" fill="{c["light"]}" '
        f'stroke="#1e293b" stroke-width="3.2"/>',
        f'<path d="M76 108 q44 -26 88 0 v10 q-44 -22 -88 0z" fill="#fff" opacity=".18"/>',
        _stitches(80, 88, 152),
        _eyes(eye_kind, c),
        _mouth(mood, mouth_dy),
        f'<ellipse cx="90" cy="126" rx="7" ry="4" fill="#fb7185" opacity=".45"/>'
        f'<ellipse cx="150" cy="126" rx="7" ry="4" fill="#fb7185" opacity=".45"/>',
        _prop(role["prop"], c),
        # 玻璃罩高光：统一班底的最后一笔
        f'<path d="M84 78 q-8 24 2 46" fill="none" stroke="#fff" stroke-width="4" '
        f'stroke-linecap="round" opacity=".55"/>',
        '</svg>',
    ]
    return "\n".join(parts)


def _scientist_staff(kind: str, c: dict) -> str:
    a, d = c["accent"], c["dark"]
    if kind == "coil":
        head = ("".join(f'<ellipse cx="196" cy="{y}" rx="13" ry="5" fill="none" '
                        f'stroke="{a}" stroke-width="3"/>' for y in (96, 108, 120, 132)))
    elif kind == "flask":
        head = (f'<circle cx="196" cy="112" r="26" fill="url(#glow)"/>'
                f'<path d="M196 88 v22 l-16 26 a6 6 0 0 0 5 9 h22 a6 6 0 0 0 5 -9 l-16 -26z" '
                f'fill="url(#glass)" stroke="{d}" stroke-width="2.4"/>'
                f'<path d="M184 128 h24 l4 9 a6 6 0 0 1 -5 9 h-22 a6 6 0 0 1 -5 -9z" fill="{a}" opacity=".8"/>')
    elif kind == "apple":
        head = (f'<circle cx="196" cy="112" r="26" fill="url(#glow)"/>'
                f'<path d="M196 90 a20 19 0 0 1 0 38 a20 19 0 0 1 0 -38z" '
                f'fill="#f87171" stroke="{d}" stroke-width="2.2"/>'
                f'<path d="M196 90 q2 -10 8 -14" fill="none" stroke="#7c4a12" stroke-width="2.6" '
                f'stroke-linecap="round"/>'
                f'<path d="M204 76 q12 -4 14 6 q-12 6 -14 -6z" fill="#4ade80" stroke="{d}" stroke-width="1.6"/>'
                f'<path d="M186 104 q6 -6 12 -2" fill="none" stroke="#fff" stroke-width="3" '
                f'stroke-linecap="round" opacity=".7"/>')
    elif kind == "pendulum":
        head = (f'<circle cx="196" cy="112" r="24" fill="url(#glow)"/>'
                f'<path d="M196 86 v44" stroke="{d}" stroke-width="3" stroke-linecap="round"/>'
                f'<path d="M196 86 l16 34" stroke="{a}" stroke-width="2.6" '
                f'stroke-linecap="round" opacity=".85"/>'
                f'<circle cx="196" cy="132" r="9" fill="url(#gold)" stroke="#b45309" stroke-width="1.8"/>'
                f'<path d="M182 86 h28" stroke="{d}" stroke-width="4" stroke-linecap="round"/>')
    elif kind == "burner":
        head = (f'<circle cx="196" cy="112" r="26" fill="url(#glow)"/>'
                f'<path d="M182 128 h28 l-4 10 h-20z" fill="url(#metal)" stroke="{d}" stroke-width="2"/>'
                f'<path d="M196 124 q-10 -10 -4 -20 q3 6 4 4 q2 -10 8 -12 q-2 8 2 12 q6 -4 4 6 '
                f'q-2 10 -14 10z" fill="#fbbf24" stroke="#b45309" stroke-width="1.6"/>'
                f'<path d="M196 120 q-4 -5 -1 -10 q1 4 3 2 q1 -4 4 -5 q-1 4 1 6 q3 -1 1 4 '
                f'q-2 5 -8 3z" fill="#fde68a" opacity=".9"/>')
    elif kind == "molecule":
        import math
        pts = [(196 + 20 * math.cos(math.pi * 2 * i / 6 - math.pi / 2),
                112 + 20 * math.sin(math.pi * 2 * i / 6 - math.pi / 2)) for i in range(6)]
        bonds = "".join(f'<line x1="{pts[i][0]:.1f}" y1="{pts[i][1]:.1f}" '
                        f'x2="{pts[(i + 1) % 6][0]:.1f}" y2="{pts[(i + 1) % 6][1]:.1f}" '
                        f'stroke="{d}" stroke-width="2.2" opacity=".8"/>' for i in range(6))
        balls = "".join(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="7" fill="{a}" '
                        f'stroke="{d}" stroke-width="1.8"/>' for x, y in pts)
        head = (f'<circle cx="196" cy="112" r="30" fill="url(#glow)"/>' + bonds + balls
                + f'<circle cx="{pts[0][0]:.1f}" cy="{pts[0][1]:.1f}" r="3.2" fill="#fff"/>')
    elif kind == "orb":
        # 静电球：玻璃球罩 + 球内闪电 + 尖端放电火花
        sparks = "".join(
            f'<path d="M{196 + dx * 26} {112 + dy * 26} l{dx * 9} {dy * 9}" stroke="{a}" '
            f'stroke-width="2.6" stroke-linecap="round" opacity=".85"/>'
            for dx, dy in ((-1, -0.2), (0.95, 0.35), (0.15, -1), (-0.4, 0.95))
        )
        head = (f'<circle cx="196" cy="112" r="30" fill="url(#glow)"/>'
                f'<circle cx="196" cy="112" r="22" fill="url(#glass)" stroke="{d}" stroke-width="2.4"/>'
                f'<path d="M200 96 l-10 16 h6.5 l-3.5 16 12 -19 h-7.5z" fill="#fbbf24" '
                f'stroke="#b45309" stroke-width="1.3" stroke-linejoin="round"/>'
                f'<path d="M192 94 q-7 5 -8 11" fill="none" stroke="#fff" stroke-width="2.4" '
                f'stroke-linecap="round" opacity=".75"/>' + sparks)
    elif kind == "grid":
        # 元素方阵：3×3 方格，中心格高亮（门捷列夫留下的那个空格）
        cells = []
        for r in range(3):
            for col in range(3):
                x = 171 + col * 18
                y = 87 + r * 18
                solid = (r, col) == (1, 1)
                cells.append(
                    f'<rect x="{x}" y="{y}" width="14" height="14" rx="3" '
                    f'fill="{a if solid else "#f8fafc"}" stroke="{d}" stroke-width="1.8"/>'
                    f'<path d="M{x + 3} {y + 7} h8" stroke="{d if solid else a}" '
                    f'stroke-width="1.4" opacity=".65"/>'
                )
        head = (f'<circle cx="196" cy="112" r="32" fill="url(#glow)"/>'
                + "".join(cells)
                + f'<path d="M171 84 h50 M168 87 v44" stroke="{d}" stroke-width="2" opacity=".45"/>')
    elif kind == "ion":
        # 正负离子对：一正一负两颗小球，中间虚线相连
        head = (f'<circle cx="196" cy="112" r="28" fill="url(#glow)"/>'
                f'<path d="M188 104 L204 122" stroke="{d}" stroke-width="2" '
                f'stroke-dasharray="3 3" opacity=".7"/>'
                f'<circle cx="186" cy="102" r="14" fill="{a}" stroke="{d}" stroke-width="2.2"/>'
                f'<path d="M186 96 v12 M180 102 h12" stroke="#fff" stroke-width="2.6" '
                f'stroke-linecap="round"/>'
                f'<circle cx="206" cy="124" r="14" fill="#f8fafc" stroke="{d}" stroke-width="2.2"/>'
                f'<path d="M200 124 h12" stroke="{d}" stroke-width="2.8" stroke-linecap="round"/>')
    else:  # bell
        head = (f'<path d="M170 140 q26 -66 52 0" fill="none" stroke="{a}" stroke-width="4" '
                f'stroke-linecap="round"/>'
                f'<path d="M170 140 h52" stroke="{d}" stroke-width="2" opacity=".5"/>'
                f'<circle cx="196" cy="76" r="3.5" fill="{a}" opacity=".9"/>')
    # 注意：竖线的对象包围盒宽度为 0，线性渐变会失效导致整根杆消失，
    # 因此这里用纯色描边 + 一条浅色高光，而不是 url(#gold)。
    return (head
            + f'<path d="M196 134 v100" stroke="#b45309" stroke-width="8" stroke-linecap="round"/>'
            + f'<path d="M194 142 v88" stroke="#fde68a" stroke-width="2" '
              f'stroke-linecap="round" opacity=".9"/>'
            + f'<rect x="190" y="146" width="12" height="7" rx="2" fill="url(#gold)" '
              f'stroke="#b45309" stroke-width="1.4"/>'
            + f'<circle cx="196" cy="236" r="7" fill="url(#gold)" stroke="#b45309" stroke-width="1.6"/>')


def render_big(role: dict, c: dict) -> str:
    """科学家大 boss：同款 Q 版比例与螺栓印记，白袍 + 光环 + 权杖 + 金框。"""
    a, d = c["accent"], c["dark"]
    # 三位所长必须一眼分得清：发型、胡须、眼镜、嘴型、胸前字母各不相同。
    LOOK = {
        "faraday": dict(
            badge="F",
            hair=('<path d="M84 88 q-4 -34 36 -34 q40 0 36 34 q-10 -18 -36 -18 q-26 0 -36 18z" '
                  'fill="#475569" stroke="#1e293b" stroke-width="2.4"/>'
                  '<path d="M86 92 q-8 20 -2 30 M154 92 q8 20 2 30" fill="none" '
                  'stroke="#475569" stroke-width="7" stroke-linecap="round"/>'
                  '<path d="M120 56 v12" stroke="#1e293b" stroke-width="1.5" opacity=".45"/>'),
            face=('<path d="M86 116 q2 26 20 32 M154 116 q-2 26 -20 32" fill="none" '
                  'stroke="#475569" stroke-width="6" stroke-linecap="round"/>'
                  '<path d="M102 142 q18 11 36 0" fill="none" stroke="#475569" '
                  'stroke-width="7" stroke-linecap="round"/>'
                  '<path d="M106 125 q7 -4 13 2 M134 125 q-7 -4 -13 2" fill="none" '
                  'stroke="#475569" stroke-width="3" stroke-linecap="round"/>'),
            mouth=('<path d="M110 131 q10 7 20 0" fill="none" stroke="#1e293b" '
                   'stroke-width="2.4" stroke-linecap="round"/>'),
        ),
        "curie": dict(
            badge="M",
            hair=('<path d="M82 96 q-6 -46 38 -46 q44 0 38 46 q-12 -22 -38 -22 q-26 0 -38 22z" '
                  'fill="#57534e" stroke="#1e293b" stroke-width="2.4"/>'
                  '<circle cx="120" cy="48" r="16" fill="#57534e" stroke="#1e293b" stroke-width="2.2"/>'
                  '<path d="M110 40 q10 8 20 0" fill="none" stroke="#78716c" stroke-width="2"/>'
                  '<path d="M84 96 q-6 16 -2 26 M156 96 q6 16 2 26" fill="none" '
                  'stroke="#57534e" stroke-width="6" stroke-linecap="round"/>'),
            face=('<path d="M96 99 l-3 -5 M104 98 l1 -5 M136 98 l-1 -5 M144 99 l3 -5" '
                  'stroke="#1e293b" stroke-width="1.6" stroke-linecap="round"/>'
                  '<circle cx="82" cy="120" r="3.2" fill="url(#gold)" stroke="#b45309" stroke-width="1.2"/>'
                  '<circle cx="158" cy="120" r="3.2" fill="url(#gold)" stroke="#b45309" stroke-width="1.2"/>'
                  '<ellipse cx="94" cy="126" rx="6" ry="3.5" fill="#fb7185" opacity=".35"/>'
                  '<ellipse cx="146" cy="126" rx="6" ry="3.5" fill="#fb7185" opacity=".35"/>'
                  '<path d="M114 138 q6 3 12 0" fill="none" stroke="#e11d48" '
                  'stroke-width="2" stroke-linecap="round" opacity=".65"/>'),
            mouth=('<path d="M112 131 q8 6 16 0" fill="none" stroke="#1e293b" '
                   'stroke-width="2.3" stroke-linecap="round"/>'),
        ),
        "gauss": dict(
            badge="G",
            hair=('<path d="M82 90 q-4 -40 38 -40 q42 0 38 40 q-14 -20 -38 -20 q-24 0 -38 20z" '
                  'fill="#cbd5e1" stroke="#1e293b" stroke-width="2.4"/>'
                  '<path d="M84 90 q-8 18 -2 30 M156 90 q8 18 2 30" fill="none" '
                  'stroke="#cbd5e1" stroke-width="7" stroke-linecap="round"/>'
                  '<path d="M94 94 h18 M128 94 h18" stroke="#94a3b8" stroke-width="3.4" '
                  'stroke-linecap="round"/>'),
            face=('<circle cx="136" cy="108" r="14" fill="none" stroke="#94a3b8" stroke-width="2.6"/>'
                  '<path d="M148 118 l6 16" stroke="#94a3b8" stroke-width="1.8" '
                  'stroke-linecap="round"/>'
                  '<path d="M104 128 q8 6 14 0 M136 128 q-8 6 -14 0" fill="none" '
                  'stroke="#cbd5e1" stroke-width="4" stroke-linecap="round"/>'
                  '<path d="M102 142 q18 8 36 0" fill="none" stroke="#cbd5e1" '
                  'stroke-width="5" stroke-linecap="round"/>'),
            mouth=('<path d="M111 133 h18" fill="none" stroke="#1e293b" '
                   'stroke-width="2.4" stroke-linecap="round"/>'),
        ),
        # 牛顿：灰白长卷发垂到肩，无胡须，嘴角微扬
        "newton": dict(
            badge="N",
            hair=('<path d="M78 96 q-10 -46 42 -46 q52 0 42 46 q-6 26 -10 44 M78 96 '
                  'q-2 26 2 44" fill="none" stroke="#e2e8f0" stroke-width="10" '
                  'stroke-linecap="round"/>'
                  '<path d="M84 92 q-4 -38 36 -38 q40 0 36 38 q-12 -18 -36 -18 q-24 0 -36 18z" '
                  'fill="#f1f5f9" stroke="#1e293b" stroke-width="2.4"/>'
                  '<path d="M82 94 q0 28 4 42 M158 94 q0 28 -4 42" fill="none" '
                  'stroke="#f1f5f9" stroke-width="9" stroke-linecap="round"/>'
                  '<path d="M96 74 q10 -6 20 -2 M124 72 q12 -4 20 4" fill="none" '
                  'stroke="#cbd5e1" stroke-width="3" stroke-linecap="round"/>'),
            face=('<path d="M100 120 q4 14 12 18 M140 120 q-4 14 -12 18" fill="none" '
                  'stroke="#cbd5e1" stroke-width="2.2" stroke-linecap="round" opacity=".8"/>'
                  '<path d="M120 114 v8" stroke="#f4a26b" stroke-width="2" '
                  'stroke-linecap="round" opacity=".7"/>'),
            mouth=('<path d="M112 133 q8 6 16 0" fill="none" stroke="#1e293b" '
                   'stroke-width="2.4" stroke-linecap="round"/>'),
        ),
        # 伽利略：秃顶 + 两侧白发 + 白色大络腮胡
        "galileo": dict(
            badge="G",
            hair=('<path d="M86 92 q0 -20 10 -28 M154 92 q0 -20 -10 -28" fill="none" '
                  'stroke="#e2e8f0" stroke-width="9" stroke-linecap="round"/>'
                  '<path d="M88 84 q6 -18 16 -20 M152 84 q-6 -18 -16 -20" fill="none" '
                  'stroke="#e2e8f0" stroke-width="7" stroke-linecap="round"/>'
                  '<path d="M104 118 q16 26 32 0 q6 22 -16 22 q-22 0 -16 -22z" '
                  'fill="#f1f5f9" stroke="#1e293b" stroke-width="2.4"/>'),
            face=('<path d="M96 100 q2 10 6 14 M144 100 q-2 10 -6 14" fill="none" '
                  'stroke="#e2e8f0" stroke-width="5" stroke-linecap="round"/>'
                  '<path d="M104 112 q16 -8 32 0" fill="none" stroke="#e2e8f0" '
                  'stroke-width="4" stroke-linecap="round"/>'
                  '<path d="M120 114 v6" stroke="#f4a26b" stroke-width="2" '
                  'stroke-linecap="round" opacity=".7"/>'),
            mouth=('<path d="M112 132 h16" fill="none" stroke="#1e293b" '
                   'stroke-width="2.4" stroke-linecap="round"/>'),
        ),
        # 拉瓦锡：18 世纪灰白假发，两侧三卷，无胡须，神态严肃
        "lavoisier": dict(
            badge="L",
            hair=('<path d="M80 98 q-4 -46 40 -46 q44 0 40 46 q-4 24 -6 40 M80 98 '
                  'q-2 22 0 40 M160 98 q2 22 0 40" fill="none" stroke="#e2e8f0" '
                  'stroke-width="9" stroke-linecap="round"/>'
                  '<path d="M84 90 q-2 -38 36 -38 q38 0 36 38 q-12 -18 -36 -18 q-24 0 -36 18z" '
                  'fill="#f1f5f9" stroke="#1e293b" stroke-width="2.4"/>'
                  '<circle cx="86" cy="106" r="9" fill="#f1f5f9" stroke="#1e293b" stroke-width="1.8"/>'
                  '<circle cx="86" cy="122" r="9" fill="#f1f5f9" stroke="#1e293b" stroke-width="1.8"/>'
                  '<circle cx="154" cy="106" r="9" fill="#f1f5f9" stroke="#1e293b" stroke-width="1.8"/>'
                  '<circle cx="154" cy="122" r="9" fill="#f1f5f9" stroke="#1e293b" stroke-width="1.8"/>'),
            face=('<path d="M120 114 v8" stroke="#f4a26b" stroke-width="2" '
                  'stroke-linecap="round" opacity=".7"/>'
                  '<path d="M108 121 q6 -3 10 1 M132 121 q-6 -3 -10 1" fill="none" '
                  'stroke="#cbd5e1" stroke-width="2" stroke-linecap="round" opacity=".8"/>'),
            mouth=('<path d="M113 134 h14" fill="none" stroke="#1e293b" '
                   'stroke-width="2.6" stroke-linecap="round"/>'),
        ),
        # 阿伏伽德罗：深色短发前秃 + 长鬓角，神态温和
        "avogadro": dict(
            badge="A",
            hair=('<path d="M86 96 q0 -14 12 -22 M154 96 q0 -14 -12 -22" fill="none" '
                  'stroke="#475569" stroke-width="10" stroke-linecap="round"/>'
                  '<path d="M90 84 q8 -24 30 -26 q22 -2 34 26 q-10 -14 -32 -14 q-22 0 -32 14z" '
                  'fill="#475569" stroke="#1e293b" stroke-width="2.4"/>'
                  '<path d="M84 92 q-2 22 2 38 M156 92 q2 22 -2 38" fill="none" '
                  'stroke="#475569" stroke-width="8" stroke-linecap="round"/>'
                  '<path d="M120 86 q0 6 -2 10" fill="none" stroke="#64748b" '
                  'stroke-width="2" stroke-linecap="round" opacity=".6"/>'),
            face=('<path d="M86 108 v20 q0 8 6 10 M154 108 v20 q0 8 -6 10" fill="none" '
                  'stroke="#475569" stroke-width="5" stroke-linecap="round"/>'
                  '<path d="M120 114 v8" stroke="#f4a26b" stroke-width="2" '
                  'stroke-linecap="round" opacity=".7"/>'
                  '<path d="M106 122 q7 -4 12 1 M134 122 q-7 -4 -12 1" fill="none" '
                  'stroke="#475569" stroke-width="2.4" stroke-linecap="round"/>'),
            mouth=('<path d="M112 133 q8 6 16 0" fill="none" stroke="#1e293b" '
                   'stroke-width="2.4" stroke-linecap="round"/>'),
        ),
        # 库仑：18 世纪假发中分 + 两侧三卷，圆脸无须，嘴角带点工程师的自信
        "coulomb": dict(
            badge="C",
            hair=('<path d="M82 96 q-2 -50 38 -50 q40 0 38 50 q-2 24 -4 38 M82 96 '
                  'q-4 24 0 38 M158 96 q4 24 0 38" fill="none" stroke="#f1f5f9" '
                  'stroke-width="10" stroke-linecap="round"/>'
                  '<path d="M84 88 q-2 -38 36 -38 q38 0 36 38 q-10 -18 -36 -18 q-26 0 -36 18z" '
                  'fill="#f1f5f9" stroke="#1e293b" stroke-width="2.4"/>'
                  '<path d="M120 52 v14" stroke="#94a3b8" stroke-width="2" opacity=".7"/>'
                  '<circle cx="88" cy="104" r="8.5" fill="#f1f5f9" stroke="#1e293b" stroke-width="1.8"/>'
                  '<circle cx="88" cy="119" r="8.5" fill="#f1f5f9" stroke="#1e293b" stroke-width="1.8"/>'
                  '<circle cx="152" cy="104" r="8.5" fill="#f1f5f9" stroke="#1e293b" stroke-width="1.8"/>'
                  '<circle cx="152" cy="119" r="8.5" fill="#f1f5f9" stroke="#1e293b" stroke-width="1.8"/>'),
            face=('<path d="M120 114 v8" stroke="#f4a26b" stroke-width="2" '
                  'stroke-linecap="round" opacity=".7"/>'
                  '<path d="M104 118 q6 -3 11 0 M136 118 q-6 -3 -11 0" fill="none" '
                  'stroke="#cbd5e1" stroke-width="2.2" stroke-linecap="round"/>'
                  '<path d="M96 142 q24 8 48 0" fill="none" stroke="#e2e8f0" '
                  'stroke-width="3" stroke-linecap="round" opacity=".55"/>'),
            mouth=('<path d="M112 132 q8 7 16 0" fill="none" stroke="#1e293b" '
                   'stroke-width="2.4" stroke-linecap="round"/>'),
        ),
        # 门捷列夫：长发披肩 + 大络腮胡盖住下半脸，最显眼的是那把胡子
        "mendeleev": dict(
            badge="M",
            hair=('<path d="M76 100 q-6 -56 44 -56 q50 0 44 56 q-6 34 -10 56 M76 100 '
                  'q-4 34 -2 56 M164 100 q4 34 2 56" fill="none" stroke="#cbd5e1" '
                  'stroke-width="11" stroke-linecap="round"/>'
                  '<path d="M84 92 q-4 -42 36 -42 q40 0 36 42 q-14 -20 -36 -20 q-22 0 -36 20z" '
                  'fill="#cbd5e1" stroke="#1e293b" stroke-width="2.4"/>'
                  '<path d="M96 70 q12 -8 24 -4 M120 66 q12 -4 24 4" fill="none" '
                  'stroke="#94a3b8" stroke-width="3" stroke-linecap="round"/>'
                  '<path d="M100 118 q20 40 40 0 q10 32 -20 34 q-30 -2 -20 -34z" '
                  'fill="#cbd5e1" stroke="#1e293b" stroke-width="2.6"/>'
                  '<path d="M110 132 q10 6 20 0 M120 130 v12" fill="none" stroke="#94a3b8" '
                  'stroke-width="2" stroke-linecap="round" opacity=".8"/>'),
            face=('<path d="M120 112 v8" stroke="#f4a26b" stroke-width="2" '
                  'stroke-linecap="round" opacity=".7"/>'
                  '<path d="M98 100 q6 -6 14 -2 M142 100 q-6 -6 -14 -2" fill="none" '
                  'stroke="#94a3b8" stroke-width="3" stroke-linecap="round"/>'),
            mouth=('<path d="M112 133 q8 4 16 0" fill="none" stroke="#1e293b" '
                   'stroke-width="2.4" stroke-linecap="round"/>'),
        ),
        # 阿伦尼乌斯：深色短发后梳 + 小胡子 + 圆框眼镜，斯文的北欧学者
        "arrhenius": dict(
            badge="A",
            hair=('<path d="M84 92 q-2 -40 36 -40 q38 0 36 40 q-8 -22 -36 -22 q-28 0 -36 22z" '
                  'fill="#334155" stroke="#1e293b" stroke-width="2.4"/>'
                  '<path d="M92 78 q14 -12 28 -12" fill="none" stroke="#475569" '
                  'stroke-width="2.6" stroke-linecap="round" opacity=".8"/>'
                  '<path d="M86 96 q-4 16 -2 26 M154 96 q4 16 2 26" fill="none" '
                  'stroke="#334155" stroke-width="7" stroke-linecap="round"/>'),
            face=('<circle cx="104" cy="108" r="10" fill="none" stroke="#94a3b8" stroke-width="2.4"/>'
                  '<circle cx="136" cy="108" r="10" fill="none" stroke="#94a3b8" stroke-width="2.4"/>'
                  '<path d="M114 108 h12" stroke="#94a3b8" stroke-width="2" stroke-linecap="round"/>'
                  '<path d="M120 114 v8" stroke="#f4a26b" stroke-width="2" '
                  'stroke-linecap="round" opacity=".7"/>'
                  '<path d="M108 128 q6 -4 12 0 M132 128 q-6 -4 -12 0" fill="none" '
                  'stroke="#334155" stroke-width="3.4" stroke-linecap="round"/>'),
            mouth=('<path d="M112 136 q8 5 16 0" fill="none" stroke="#1e293b" '
                   'stroke-width="2.4" stroke-linecap="round"/>'),
        ),
        # 帕斯卡：短发 + 小胡子，神情克制
        "euler": dict(
            badge="P",
            hair=('<path d="M86 88 q4 -36 34 -36 q30 0 34 36 q-14 -16 -34 -16 q-20 0 -34 16z" '
                  'fill="#334155" stroke="#1e293b" stroke-width="2.4"/>'
                  '<path d="M86 94 q-8 16 -3 26 M154 94 q8 16 3 26" fill="none" '
                  'stroke="#334155" stroke-width="6" stroke-linecap="round"/>'),
            face=('<path d="M104 126 q16 -6 32 0" fill="none" stroke="#334155" '
                  'stroke-width="3.6" stroke-linecap="round"/>'
                  '<path d="M104 110 q8 -4 14 0 M132 110 q8 -4 14 0" fill="none" '
                  'stroke="#334155" stroke-width="2.6" stroke-linecap="round"/>'
                  '<path d="M108 140 q12 5 24 0" fill="none" stroke="#cbd5e1" '
                  'stroke-width="4" stroke-linecap="round"/>'),
            mouth=('<path d="M112 133 q8 5 16 0" fill="none" stroke="#1e293b" '
                   'stroke-width="2.3" stroke-linecap="round"/>'),
        ),
        # 开普勒：灰白长发 + 大胡子
        "descartes": dict(
            badge="K",
            hair=('<path d="M82 96 q-6 -48 38 -48 q44 0 38 48 q-12 -22 -38 -22 q-26 0 -38 22z" '
                  'fill="#e2e8f0" stroke="#1e293b" stroke-width="2.4"/>'
                  '<path d="M82 98 q-10 30 -4 50 M158 98 q10 30 4 50" fill="none" '
                  'stroke="#e2e8f0" stroke-width="9" stroke-linecap="round"/>'),
            face=('<path d="M94 118 q26 42 52 0 q-6 30 -26 32 q-20 -2 -26 -32z" '
                  'fill="#e2e8f0" stroke="#1e293b" stroke-width="2.2"/>'
                  '<path d="M106 108 q8 -4 14 0 M132 108 q8 -4 14 0" fill="none" '
                  'stroke="#64748b" stroke-width="2.6" stroke-linecap="round"/>'),
            mouth=('<path d="M113 137 q7 4 14 0" fill="none" stroke="#1e293b" '
                   'stroke-width="2.2" stroke-linecap="round"/>'),
        ),
        # 拉马努金：黑发侧分，圆脸，安静的笑
        "ramanujan": dict(
            badge="R",
            hair=('<path d="M84 92 q0 -40 36 -40 q36 0 36 40 q-18 -14 -36 -14 q-18 0 -36 14z" '
                  'fill="#1f2937" stroke="#0f172a" stroke-width="2.4"/>'
                  '<path d="M120 54 q14 -8 26 2" fill="none" stroke="#0f172a" '
                  'stroke-width="2.2" stroke-linecap="round"/>'),
            face=('<path d="M104 110 q8 -4 14 0 M132 110 q8 -4 14 0" fill="none" '
                  'stroke="#1f2937" stroke-width="2.8" stroke-linecap="round"/>'
                  '<ellipse cx="96" cy="126" rx="5.5" ry="3" fill="#fb7185" opacity=".28"/>'
                  '<ellipse cx="144" cy="126" rx="5.5" ry="3" fill="#fb7185" opacity=".28"/>'),
            mouth=('<path d="M110 132 q10 7 20 0" fill="none" stroke="#1e293b" '
                   'stroke-width="2.4" stroke-linecap="round"/>'),
        ),
    }
    look = LOOK[role["card_id"]]
    parts = [
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 240 280" width="240" height="280" '
        'role="img" aria-label="' + role["name"] + ' 大 Boss">',
        _defs(c, True),
        f'<ellipse cx="120" cy="258" rx="70" ry="10" fill="#0f172a" opacity=".12"/>'
        f'<circle cx="120" cy="140" r="102" fill="url(#halo)"/>'
        # 大 boss 光环 + 外框
        f'<ellipse cx="120" cy="46" rx="62" ry="15" fill="none" stroke="url(#gold)" '
        f'stroke-width="5" opacity=".95"/>'
        f'<ellipse cx="120" cy="248" rx="62" ry="11" fill="none" stroke="url(#gold)" '
        f'stroke-width="2.4" opacity=".7"/>'
        f'<path d="M28 150 l-8 6 8 6 M212 150 l8 6 -8 6" fill="none" stroke="{a}" '
        f'stroke-width="3" stroke-linecap="round" opacity=".7"/>',
        _number_tag("", True),
        _scientist_staff(role["staff"], c),
        # 白袍躯干
        f'<path d="M78 162 q42 -16 84 0 l16 78 q-58 20 -116 0z" fill="url(#robe)" '
        f'stroke="#1e293b" stroke-width="3"/>'
        f'<path d="M120 148 v96" stroke="{c["line"]}" stroke-width="2" opacity=".35"/>'
        f'<path d="M104 152 l16 22 16 -22" fill="{a}" stroke="{d}" stroke-width="2.2"/>'
        f'<circle cx="120" cy="196" r="12" fill="url(#gold)" stroke="#b45309" stroke-width="2"/>'
        f'<text x="120" y="201" text-anchor="middle" font-family="Georgia,serif" '
        f'font-size="13" font-weight="bold" fill="#78350f">{look["badge"]}</text>'
        f'<rect x="58" y="166" width="20" height="48" rx="10" fill="#e2e8f0" stroke="#1e293b" stroke-width="2.4"/>'
        f'<rect x="162" y="166" width="20" height="48" rx="10" fill="#e2e8f0" stroke="#1e293b" stroke-width="2.4"/>'
        f'<circle cx="68" cy="216" r="10" fill="#f8fafc" stroke="#1e293b" stroke-width="2.2"/>'
        f'<circle cx="172" cy="216" r="10" fill="#f8fafc" stroke="#1e293b" stroke-width="2.2"/>'
        + _bolt(90, 154, c, gold=True) + _bolt(150, 154, c, gold=True)
        # 头
        + f'<rect x="80" y="66" width="80" height="82" rx="30" fill="#ffe9cf" stroke="#1e293b" stroke-width="3"/>'
        + look["hair"]
        + f'<circle cx="104" cy="108" r="9" fill="#fff" stroke="#1e293b" stroke-width="1.8"/>'
        + f'<circle cx="136" cy="108" r="9" fill="#fff" stroke="#1e293b" stroke-width="1.8"/>'
        + f'<circle cx="105" cy="109" r="4" fill="#1e293b"/><circle cx="137" cy="109" r="4" fill="#1e293b"/>'
        + f'<circle cx="103" cy="106" r="1.8" fill="#fff"/><circle cx="135" cy="106" r="1.8" fill="#fff"/>'
        + look["face"]
        + look["mouth"]
        + f'<path d="M84 80 q-8 24 2 44" fill="none" stroke="#fff" stroke-width="4" '
          f'stroke-linecap="round" opacity=".55"/>',
        '</svg>',
    ]
    return "\n".join(parts)


# ---------------------------------------------------------------- 题量 → HP


def section_hp(topic_id: str, section_id: str) -> int:
    data = json.loads((TOPIC_DIR / f"{topic_id}.json").read_text(encoding="utf-8"))
    sec = next(s for s in data["sections"] if s["id"] == section_id)
    t = sec["type"]
    if t in ("quiz", "boss"):
        return len(sec.get("questions", [])) or 1
    if t == "levels":
        return sum(len(l["questions"]) for l in sec.get("levels", [])) or 1
    if t == "myths":
        return len(sec.get("myths", [])) or 1
    if t == "steps":
        return sum(len(p["steps"]) for p in sec.get("problems", [])) or 1
    return 1  # reading


# ---------------------------------------------------------------- 预览图鉴

GALLERY_TPL = Template("""<!DOCTYPE html>
<html lang="zh-CN"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>谬误研究所 · 怪人军团图鉴</title>
<style>
*{box-sizing:border-box}
body{margin:0;padding:36px 24px 64px;background:#f5f7fb;color:#1e293b;
 font-family:-apple-system,BlinkMacSystemFont,"Segoe UI","PingFang SC","Microsoft YaHei",sans-serif}
.wrap{max-width:1280px;margin:0 auto}
header{text-align:center;margin-bottom:12px}
h1{font-size:30px;font-weight:800;letter-spacing:-.02em;margin:0 0 8px}
.tag{display:inline-block;padding:5px 12px;border-radius:999px;background:#eef2ff;
 color:#4338ca;font-size:12px;font-weight:700;margin:0 4px}
.lead{max-width:720px;margin:16px auto 0;font-size:14px;line-height:1.8;color:#475569}
.note{font-size:12px;color:#94a3b8;margin-top:8px}
h2{font-size:19px;font-weight:800;margin:38px 0 6px;display:flex;align-items:center;gap:9px}
h2 .dot{width:11px;height:11px;border-radius:50%;background:$dot}
.sub{font-size:12.5px;color:#94a3b8;margin:0 0 16px}
.grid{display:grid;grid-template-columns:repeat(6,minmax(0,1fr));gap:14px}
@media(max-width:1080px){.grid{grid-template-columns:repeat(3,minmax(0,1fr))}}
@media(max-width:680px){.grid{grid-template-columns:repeat(2,minmax(0,1fr))}}
.card{background:#fff;border:1px solid #e2e8f0;border-radius:16px;padding:12px;
 box-shadow:0 2px 10px rgba(15,23,42,.04);transition:transform .18s,box-shadow .18s}
.card:hover{transform:translateY(-3px);box-shadow:0 8px 22px rgba(15,23,42,.09)}
.card.big{border:2px solid #fbbf24;background:linear-gradient(180deg,#fffbeb,#fff)}
.pic{height:190px;display:flex;align-items:center;justify-content:center;
 background:radial-gradient(circle at 50% 55%,$halo,transparent 68%);border-radius:12px}
.pic svg{width:100%;height:100%;display:block}
.nm{font-size:15px;font-weight:800;margin-top:10px;display:flex;align-items:center;gap:6px}
.en{font-size:11px;color:#94a3b8;font-weight:600}
.meta{display:flex;gap:5px;flex-wrap:wrap;margin-top:7px}
.pill{font-size:10.5px;padding:2px 7px;border-radius:6px;background:#f1f5f9;color:#475569;font-weight:700}
.pill.boss{background:#fef3c7;color:#92400e}
.pill.hp{background:#fee2e2;color:#b91c1c}
.quote{font-size:12px;line-height:1.65;color:#64748b;margin-top:9px;min-height:40px}
.pure{font-size:11px;color:#059669;margin-top:7px;line-height:1.6}
footer{margin-top:44px;text-align:center;font-size:12px;color:#94a3b8;line-height:1.9}
</style></head><body><div class="wrap">
<header>
 <h1>谬误研究所 · 怪人军团图鉴</h1>
 <div><span class="tag">The Fallacy Lab</span><span class="tag">18 名角色</span>
 <span class="tag">3 条谱系</span><span class="tag">原创 SVG</span></div>
 <p class="lead">每个学科里最常见的<strong>错误概念</strong>，被研究所培育成了怪人。
 它们共用一套造物特征：额头缝合线、颈部螺栓、玻璃罩高光、绷带、实验编号牌。
 前五关是实验体；最后一关的守关者是创造它们的<strong>科学家 · 大 Boss</strong>，
 通关后其卡片进入图鉴。答对一题，就净化一格 HP。</p>
 <p class="note">美术设定取公有领域的「科学怪人／实验室造物」母题，角色、名称、台词均为本项目原创，
 未使用任何商业卡通或游戏 IP 的现成形象。</p>
</header>
$groups
<footer>生成自 <code>tools/generate_bosses.py</code> · 立绘位于 <code>assets/bosses/</code> ·
角色表位于 <code>content/bosses.json</code><br>重跑脚本即可同步更新图鉴与角色表。</footer>
</div></body></html>""")

def inline_svg(path: Path, prefix: str) -> str:
    """预览页内联立绘：给 defs 的 id 加前缀，避免 18 份同名渐变互相覆盖。

    内联后图鉴是单文件，用 file:// 直接打开也能显示全部角色。
    """
    s = path.read_text(encoding="utf-8")
    for ident in set(re.findall(r'id="([^"]+)"', s)):
        s = s.replace(f'id="{ident}"', f'id="{prefix}-{ident}"')
        s = s.replace(f'url(#{ident})', f'url(#{prefix}-{ident})')
    return s.replace('width="240" height="280" ', '').strip()


CARD_TPL = Template("""<div class="card $cls">
 <div class="pic">$art</div>
 <div class="nm">$name <span class="en">$en</span></div>
 <div class="meta"><span class="pill">$section</span>
 <span class="pill $bosscls">$tier</span><span class="pill hp">HP $hp</span></div>
 <div class="quote">「$taunt」</div>
 <div class="pure">净化后：$purified</div>
</div>""")


def build() -> None:
    SVG_DIR.mkdir(parents=True, exist_ok=True)
    GALLERY.parent.mkdir(parents=True, exist_ok=True)

    bosses = []
    mini_no = 1
    for role in CAST:
        c = PAL[role["subject"]]
        big = role.get("tier") == "big"
        code = "No.%02d" % mini_no
        if not big:
            mini_no += 1
        bid = f"{role['topic']}-{role['section']}"
        fname = f"{bid}.svg"
        (SVG_DIR / fname).write_text(
            render_big(role, c) if big else render_mini(role, c, code),
            encoding="utf-8",
        )
        bosses.append({
            "id": bid,
            "topic_id": role["topic"],
            "section_id": role["section"],
            "tier": "big" if big else "mini",
            "name": role["name"],
            "en": role["en"],
            "code": "BOSS" if big else code,
            "element": role["element"],
            "skill": role["skill"].strip(),
            "hp": section_hp(role["topic"], role["section"]),
            "taunt": role["taunt"],
            "purified": role["purified"],
            "svg": f"/assets/bosses/{fname}",
            "colors": {"main": c["main"], "accent": c["accent"]},
            "card_id": role.get("card_id"),
        })

    payload = {
        "version": 1,
        "series": {
            "name": "谬误研究所",
            "en": "The Fallacy Lab",
            "tagline": "答对一题，净化一只怪人",
            "setting": "每个学科里最常见的错误概念被培育成实验体，科学家是研究所所长兼最终守关者。",
            "art_style": ["额头缝合线", "颈部六角螺栓", "玻璃罩高光", "左手绷带",
                          "Q 版三头身", "实验编号牌", "统一底座光环"],
            "license": "原创角色；仅取公有领域的科学怪人／实验室造物母题，"
                       "未使用任何商业卡通或游戏 IP 的现成形象。",
        },
        "bosses": bosses,
    }
    BOSS_JSON.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
                         encoding="utf-8")

    groups = []
    catalog = json.loads((ROOT / "content" / "catalog.json").read_text(encoding="utf-8"))
    for t in catalog["topics"]:
        topic, subject = t["id"], t["subject"]
        label = f'{PAL_SUBJECT[subject]} · {t["title"]}'
        dot = PAL[subject]["main"]
        cards = []
        for b in bosses:
            if b["topic_id"] != topic:
                continue
            cards.append(CARD_TPL.substitute(
                cls="big" if b["tier"] == "big" else "",
                art=inline_svg(SVG_DIR / Path(b["svg"]).name,
                               "s-" + re.sub(r"[^a-zA-Z0-9_-]", "", b["id"])),
                name=b["name"], en=b["en"],
                section=SECTION_NAME[b["section_id"]],
                bosscls="boss" if b["tier"] == "big" else "",
                tier="大 BOSS" if b["tier"] == "big" else "小 BOSS",
                hp=b["hp"], taunt=b["taunt"], purified=b["purified"],
            ))
        groups.append(
            f'<h2><span class="dot" style="background:{dot}"></span>{label}</h2>'
            f'<p class="sub">1 位研究所所长 + 5 只实验体 · 共 {len(cards)} 名角色</p>'
            f'<div class="grid">{"".join(cards)}</div>'
        )
    GALLERY.write_text(
        GALLERY_TPL.substitute(groups="\n".join(groups), dot="#6366f1",
                               halo="#eef2ff"),
        encoding="utf-8",
    )

    print(f"生成 {len(bosses)} 名角色 → {SVG_DIR.relative_to(ROOT)}")
    print(f"角色表 → {BOSS_JSON.relative_to(ROOT)}")
    print(f"预览图鉴 → {GALLERY.relative_to(ROOT)}")


if __name__ == "__main__":
    build()
