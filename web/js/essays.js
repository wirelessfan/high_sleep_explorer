/* 学习心得体会专栏：文章索引（专栏列表页与文章页共用同一份数据） */

export const COLUMN = {
  route: '#/essays',
  title: '学习心得体会',
  sub: '陪读笔记 · 数理方法论 · 可打印收藏版',
  intro: '这里放的不是教辅，而是「怎么学」的复盘：哪些坑踩过、哪句话点醒了、哪张图画出来题就通了。文章都写给孩子也写给家长，手机上能读，打印成 A4 能贴在书桌前。',
};

export const ESSAYS = [
  {
    slug: 'intuition',
    route: '#/essays/intuition',
    emoji: '📖',
    kicker: '数理思维方法论 · 可打印收藏版',
    title: '看见公式背后的风：数学与物理直觉思维的养成',
    lead: '公式是乐谱，直觉是乐感。背熟乐谱能按部就班弹出音符，但只有长出了乐感，你才能在考场和探索里一眼听出哪里跑了调、哪里藏着捷径。',
    date: '2026-11-22',
    tag: '方法论',
    tags: ['直觉思维', '三角函数', '错题复盘', '亲子共读'],
    sections: ['为什么需要直觉', '大师的直觉时刻', '怎么科学地养成', '今天就能做的四个动作', '给 Sunny 的手账'],
    featured: true,
    ready: true,
  },
];

export function essayBySlug(slug) {
  return ESSAYS.find((e) => e.slug === slug) || null;
}

/* 上下篇：返回 { prev, next }，没有则为 null */
export function essayNeighbors(slug) {
  const i = ESSAYS.findIndex((e) => e.slug === slug);
  if (i < 0) return { prev: null, next: null };
  return { prev: ESSAYS[i - 1] || null, next: ESSAYS[i + 1] || null };
}

/* 正文字数（去掉标签与空白），用于自动算阅读时长 */
export function countChars(html) {
  const text = String(html || '').replace(/<[^>]*>/g, ' ').replace(/&[a-z]+;/gi, 'x');
  return text.replace(/\s+/g, '').length;
}
