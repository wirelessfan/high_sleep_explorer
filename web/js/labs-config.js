/* 「路线」页的入口配置：跨学科工具卡 + 各科互动实验室
 *
 * 以后要加实验室，只在 LABS_BY_SUBJECT 里追加一行对象即可，
 * 学科页会按 subject / category 自动归类排版，不用再改视图代码。
 */

/* 顶层：不属于任何一个学科的通用入口（压缩成 1 行双列） */
export const TOP_TOOLS = [
  {
    icon: '📖',
    title: '数理直觉思维养成',
    desc: '方法论必读 · 可打印',
    route: '#/intuition-guide',
  },
  {
    icon: '🎯',
    title: '看图找规律',
    desc: '综合刷题 · 顺手抽奖',
    route: '#/exam-training',
  },
];

/* 实验室的模块标签顺序（筛选胶囊按这个顺序排） */
export const LAB_CATEGORIES = ['力学', '电磁', '光波热', '近代'];

export const LABS_BY_SUBJECT = {
  physics: [
    {
      id: 'experiments',
      icon: '🔭',
      title: '物理学实验简史',
      kw: '5 场互动探索实验室',
      category: '力学',
      route: '#/experiments',
      featured: true,
    },
    {
      id: 'momentum-energy',
      icon: '💥',
      title: '动量 & 机械能守恒',
      kw: '5 场碰撞与能量实验室',
      category: '力学',
      route: '#/momentum-energy',
      featured: false,
    },
    {
      id: 'fluid-windtunnel',
      icon: '🛫',
      title: '风洞与流体奇观',
      kw: '机翼失速 · 香蕉球 · 安全线',
      category: '力学',
      route: '#/fluid-windtunnel',
      featured: false,
    },
    {
      id: 'em-cosmos',
      icon: '⚡',
      title: '电磁宇宙加速器',
      kw: '回旋 · 轨道炮 · 极光',
      category: '电磁',
      route: '#/em-cosmos',
      featured: true,
    },
    {
      id: 'motor-generator',
      icon: '⚙️',
      title: '生活中的物理：电机',
      kw: '电动机换向器 · 交流发电机',
      category: '电磁',
      route: '#/motor-generator',
      featured: false,
    },
    {
      id: 'optics-waves',
      icon: '🔦',
      title: '光与波的魔法',
      kw: '激光光纤 · 音爆 · 降噪',
      category: '光波热',
      route: '#/optics-waves',
      featured: true,
    },
    {
      id: 'thermal-micro',
      icon: '🔥',
      title: '热学与微观宇宙',
      kw: '布朗运动 · 麦克斯韦妖 · 绝热点火',
      category: '光波热',
      route: '#/thermal-micro',
      featured: false,
    },
    {
      id: 'relativity-nuclear',
      icon: '☢️',
      title: '相对论与核风暴',
      kw: '光钟 · 金箔散射 · 控制棒',
      category: '近代',
      route: '#/relativity-nuclear',
      featured: true,
    },
    {
      id: 'chaos-quantum',
      icon: '🦋',
      title: '混沌与量子脑洞',
      kw: '双摆 · 引力弹弓 · 光电效应',
      category: '近代',
      route: '#/chaos-quantum',
      featured: false,
    },
  ],
  math: [
    {
      id: 'math-trig-lab',
      icon: '📐',
      title: '数学直觉实验室',
      kw: '函数图像 · 值域扫描 · 三角推导',
      category: '错题专项',
      route: '#/math-trig-lab',
      featured: true,
      hero: true,
    },
  ],
  chemistry: [],
};

/* 各科实验区的标题（数学是「先清错题」，物理是「先建直觉」） */
export const LAB_ZONE_TITLE = {
  physics: { title: '互动探索实验室', kicker: '先建直觉' },
  math: { title: '错题专项突破', kicker: '先玩直觉 · 再刷主线' },
};

/* 年级分组：把 catalog 里的 t.grade 变成带序号的区块标题 */
export const GRADE_ORDER = ['高一', '高二', '高三'];

export function gradeLabel(grade) {
  if (!grade) return '其他主题';
  if (grade.startsWith('高一')) return '高一 · 必修';
  if (grade.startsWith('高二')) return '高二 · 选择性必修';
  if (grade.startsWith('高三')) return '高三 · 总复习';
  return grade;
}
