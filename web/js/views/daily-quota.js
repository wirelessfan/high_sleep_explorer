/* 休闲广场每日额度：面板展示 + 服务端消耗封装。
 * 计数在后端权威维护，前端只做展示与调用，清缓存无法重置次数。 */

import * as api from '../api.js';
import { el, toast } from '../ui.js';

const DAY_LABEL = {
  weekday: '平日',
  'crazy-saturday': '疯狂星期六',
  weekend: '周末',
  holiday: '节假日',
};

const DAY_NOTE = {
  weekday: '每天 10 次',
  'crazy-saturday': '疯狂星期六 · 每天 20 次',
  weekend: '周末放松 · 每天 20 次',
  holiday: '节假日 · 每天 20 次',
};

export async function loadQuota() {
  try {
    return await api.getQuota();
  } catch {
    return null;
  }
}

let seq = 0;
function newKey() {
  seq += 1;
  return `${Date.now().toString(36)}-${seq}-${Math.random().toString(36).slice(2, 8)}`;
}

/**
 * 消耗次数。成功返回 { ok:true, quota }；失败返回 { ok:false, quota } 并提示。
 * 每次调用生成唯一幂等 key，网络重试/双击不会重复扣次数。
 */
export async function useQuota(count = 1) {
  try {
    const quota = await api.consumeQuota(count, newKey());
    return { ok: true, quota };
  } catch (err) {
    const detail = err?.detail;
    if (err?.status === 409) {
      const quota = detail && typeof detail === 'object' ? detail.quota : await loadQuota();
      toast((detail && detail.message) || '今天的次数用完了，明天再来吧');
      return { ok: false, quota };
    }
    toast('次数校验失败，请稍后再试');
    return { ok: false, quota: await loadQuota() };
  }
}

/** 消耗 1 次实体奖免费机会。返回结构与 useQuota 一致。 */
export async function usePrizeQuota() {
  try {
    const quota = await api.consumePrizeQuota(newKey());
    return { ok: true, quota };
  } catch (err) {
    const detail = err?.detail;
    if (err?.status === 409) {
      const quota = detail && typeof detail === 'object' ? detail.quota : await loadQuota();
      toast((detail && detail.message) || '今天的实体奖机会用完了，明天再来吧');
      return { ok: false, quota };
    }
    toast('机会校验失败，请稍后再试');
    return { ok: false, quota: await loadQuota() };
  }
}

/** 把 2026-11-26 显示为 11-26；无到期日返回空串。 */
function shortDay(day) {
  return day ? String(day).slice(5) : '';
}

/** 赠送池文案：7 天内有效、用完即止，不按天刷新。 */
export function grantNote(granted, grantTotal, grantUsed, grantEnd) {
  if (!granted && !grantTotal) return '';
  if (granted > 0) {
    const end = shortDay(grantEnd);
    const total = grantTotal || granted;
    const used = total - granted;
    return `🎁 赠送剩余 ${granted}/${total} 次${used ? `（已用 ${used}）` : ''}${end ? ` · ${end} 前有效` : ''} · 用完即止`;
  }
  return `🎁 赠送的 ${grantTotal || grantUsed || 0} 次已用完或已过期`;
}

function prizeBlock(p) {
  if (!p) return null;
  const reasons = [];
  reasons.push(p.free ? `${p.free_days} 免费 1 次` : '今天不是免费日');
  if (p.points_bonus) reasons.push(`今日积分 ${p.earned_points} ≥ ${p.points_threshold}，额外 1 次`);
  else reasons.push(`今日积分 ${p.earned_points}，再得 ${p.next_in} 分额外 +1 次`);
  const grant = grantNote(p.granted, p.grant_total, p.grant_used, p.grant_end);
  return el('div', { class: 'dq-prize' }, [
    el('div', { class: 'dq-prize-head' }, [
      el('span', { class: 'dq-prize-title', text: '🎁 实体奖免费机会' }),
      el('span', { class: 'dq-day', text: `${p.remaining} / ${p.total} 次` }),
    ]),
    el('div', { class: 'dq-prize-reasons', text: reasons.join(' · ') }),
    grant ? el('div', { class: 'dq-grant', text: grant }) : null,
  ]);
}

/** 生成「今日抽奖额度」面板。q 为 null 时显示占位。 */
export function quotaPanel(q) {
  if (!q) {
    return el('section', { class: 'panel dq-panel', style: 'margin-top:10px' }, [
      el('div', { class: 'hint', text: '今日额度加载失败，请下拉刷新后重试。' }),
    ]);
  }
  const label = DAY_LABEL[q.day_type] || '平日';
  const pct = q.total ? Math.min(100, Math.round((q.used / q.total) * 100)) : 0;
  const bonusPart = q.bonus > 0
    ? ` + 学习积分奖励 ${q.bonus} 次`
    : ` · 今日学习积分 ${q.earned_points}，再得 ${q.next_bonus_in} 分 +1 次`;
  const grantPart = q.granted > 0 ? ` + 赠送池 ${q.granted} 次` : '';
  const capNote = q.bonus >= q.bonus_cap ? '（已达积分奖励上限）' : '';
  const grant = grantNote(q.granted, q.grant_total, q.grant_used, q.grant_end);
  return el('section', { class: 'panel dq-panel', style: 'margin-top:10px' }, [
    el('div', { class: 'dq-head' }, [
      el('span', { class: 'dq-title', text: '🎯 今日抽奖额度' }),
      el('span', { class: 'dq-day', text: label }),
    ]),
    el('div', { class: 'dq-main' }, [
      el('div', { class: 'dq-num' }, [
        el('b', { text: String(q.remaining) }),
        el('span', { text: ` / ${q.total} 次可用` }),
      ]),
      el('div', { class: 'dq-sub', text: `${DAY_NOTE[q.day_type] || '每天 10 次'} · 已用 ${q.used}${bonusPart}${grantPart}${capNote}` }),
    ]),
    grant ? el('div', { class: 'dq-grant', text: `${grant}（普通抽奖，已计入上面的可用次数）` }) : null,
    el('div', { class: 'dq-bar' }, [
      el('div', { class: 'dq-fill', style: `width:${pct}%` }),
    ]),
    el('div', { class: 'dq-foot', text: '积分照常累积，这里只按今日新获得的积分额外送次数（每 10 分 1 次，最多 20 次）。赠送次数为一次性额度，7 天内有效、用完即止，不会每天刷新。' }),
    prizeBlock(q.prize),
  ]);
}
