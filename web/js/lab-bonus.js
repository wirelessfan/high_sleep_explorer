/* 物理实验板块的「初次见面礼」：首次点开赠送 20 次抽奖（服务端幂等，每账号一次） */

import { el, toast } from './ui.js';
import { navigate } from './router.js';
import { claimLabBonus } from './api.js';

/** 挂载赠送横幅；只有真的首次领取（granted_now > 0）才显示，重复进入不打扰。 */
export async function mountLabBonus(root, anchorSelector) {
  let q;
  try {
    q = await claimLabBonus();
  } catch {
    return;   // 网络问题就安静跳过，不影响实验本身
  }
  if (!q || !q.granted_now) return;

  const endLabel = (q.grant_end || '').slice(5).replace('-', '/');
  const card = el('div', { class: 'lab-bonus' }, [
    el('div', { class: 'lab-bonus-ico', text: '🎁' }),
    el('div', { style: 'flex:1;min-width:0' }, [
      el('div', { class: 'lab-bonus-t', text: `实验板块见面礼：${q.granted_now} 次抽奖已到账` }),
      el('div', {
        class: 'lab-bonus-d',
        text: `算在「赠送池」里，${endLabel || '30 天'} 前有效、用完即止；去休闲广场抽卡时自动优先用当日额度。`,
      }),
    ]),
    el('button', {
      class: 'btn sm', style: 'flex:0 0 auto', text: '去抽卡 →',
      onclick: () => navigate('#/relax'),
    }),
  ]);

  const anchor = anchorSelector ? root.querySelector(anchorSelector) : null;
  if (anchor && anchor.parentNode) anchor.parentNode.insertBefore(card, anchor);
  else root.appendChild(card);

  toast(`🎁 见面礼到账：${q.granted_now} 次抽奖`);
}
