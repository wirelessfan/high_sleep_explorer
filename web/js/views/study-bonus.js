/* 学习加成：把学习活跃度与成就折算成休闲广场的爆奖倍率。
 * 只读取现有接口（/me 的 streak、/achievements 的成就卡数），不改动任何学习数据。
 * 系数仅影响娱乐抽奖概率，不消耗积分、不产生真实收益。 */

import * as api from '../api.js';
import { el } from '../ui.js';

/* 活跃系数：按连续打卡天数分档 */
const ACTIVITY_TIERS = [
  { min: 14, mult: 2, label: '超级活跃' },
  { min: 7, mult: 1.6, label: '很活跃' },
  { min: 3, mult: 1.3, label: '在坚持' },
  { min: 0, mult: 1, label: '慢慢来' },
];

/* 成就系数：按已获得的成就卡总数分档 */
const ACHIEVEMENT_TIERS = [
  { min: 12, mult: 3, label: '成就达人' },
  { min: 6, mult: 2, label: '小有成就' },
  { min: 2, mult: 1.5, label: '初露锋芒' },
  { min: 0, mult: 1, label: '刚起步' },
];

function pickTier(tiers, value) {
  const n = Number(value) || 0;
  const idx = tiers.findIndex((t) => n >= t.min);
  const cur = tiers[idx === -1 ? tiers.length - 1 : idx];
  const next = idx > 0 ? tiers[idx - 1] : null;
  return {
    mult: cur.mult,
    label: cur.label,
    value: n,
    nextMin: next ? next.min : null,
    nextMult: next ? next.mult : null,
  };
}

/**
 * 读取学习加成。任一接口失败都安全降级为 ×1，绝不影响抽卡页正常打开。
 * @returns {{activity:object, achievement:object, total:number, streak:number, cards:number, points:number}}
 */
export async function loadStudyBonus() {
  let streak = 0;
  let cards = 0;
  let points = 0;
  try {
    const me = await api.fetchMe();
    streak = Math.max(0, Number(me.streak) || 0);
    points = Math.max(0, Number(me.points) || 0);
  } catch { /* 未登录或网络异常：按无加成处理 */ }
  try {
    const a = await api.getAchievements();
    cards = Math.max(0, Number(a?.stats?.total_count) || 0);
    if (!points) points = Math.max(0, Number(a?.points) || 0);
  } catch { /* 同上 */ }
  const activity = pickTier(ACTIVITY_TIERS, streak);
  const achievement = pickTier(ACHIEVEMENT_TIERS, cards);
  return {
    activity,
    achievement,
    total: Math.round(activity.mult * achievement.mult * 100) / 100,
    streak,
    cards,
    points,
  };
}

/** 加成后的实体券掉率：基础 6% × 总倍率，最高封顶 30%，避免大奖贬值。 */
export function effectivePrizeRate(bonus, baseRate = 0.06, cap = 0.3) {
  return Math.min(cap, baseRate * (bonus?.total || 1));
}

/** 加成后的 SR 贴纸权重：基础 2，随倍率提升，封顶 12。 */
export function effectiveSrWeight(bonus, base = 2, cap = 12) {
  return Math.min(cap, base * (bonus?.total || 1));
}

function nextHint(tier, unit) {
  if (tier.nextMin === null) return '已达最高档 🎉';
  return `再攒 ${Math.max(1, tier.nextMin - tier.value)} ${unit} → ×${tier.nextMult}`;
}

/** 生成「学习加成」展示面板，两页共用同一套视觉与文案。 */
export function bonusPanel(bonus, { rate = null, note = '' } = {}) {
  const rateLine = rate === null ? null :
    el('div', { class: 'sb-rate', text: `当前实体券爆率 ${(rate * 100).toFixed(1)}%（基础 6% × ${bonus.total} 倍）` });
  return el('section', { class: 'panel sb-panel' }, [
    el('div', { class: 'sb-head' }, [
      el('span', { class: 'sb-title', text: '⚡ 学习加成' }),
      el('span', { class: 'sb-total', text: `总计 ×${bonus.total}` }),
    ]),
    el('div', { class: 'sb-row' }, [
      el('span', { class: 'sb-mult', text: `活跃 ×${bonus.activity.mult}` }),
      el('span', { class: 'sb-name', text: `${bonus.activity.label} · 连续打卡 ${bonus.streak} 天` }),
      el('span', { class: 'sb-next', text: nextHint(bonus.activity, '天') }),
    ]),
    el('div', { class: 'sb-row' }, [
      el('span', { class: 'sb-mult', text: `成就 ×${bonus.achievement.mult}` }),
      el('span', { class: 'sb-name', text: `${bonus.achievement.label} · 成就卡 ${bonus.cards} 张` }),
      el('span', { class: 'sb-next', text: nextHint(bonus.achievement, '张') }),
    ]),
    rateLine,
    el('div', { class: 'sb-note', text: note || '学习越活跃、成就越多，休闲广场爆大奖的机会越高。加成只影响娱乐抽奖，不消耗积分。' }),
  ]);
}
