import { el } from './ui.js';
import { navigate } from './router.js';

export function studyPlanCard(plan, compact = false) {
  if (!plan) return null;
  const wrap = el('section', { class: 'panel', 'data-study-plan': plan.id });
  wrap.appendChild(el('div', { class: 'eyebrow', text: `Sunny · ${plan.region} · ${plan.grade}` }));
  wrap.appendChild(el('h2', { text: plan.scope }));
  wrap.appendChild(el('p', { style:'font-weight:700;color:#607b69', text: '轻松备考，抽着奖把题做了 🙂' }));
  wrap.appendChild(el('div', { class: 'row', style: 'gap:7px;flex-wrap:wrap' }, [
    el('span', { class: 'chip', text: `学习积分 ×${plan.points_multiplier}` }),
    el('span', { class: 'chip', text: `学习卡包 ×${plan.tickets_multiplier}` }),
    el('span', { class: 'chip', text: `已探索 ${plan.done} 个小站` }),
  ]));
  wrap.appendChild(el('button', { class:'btn sm',style:'margin-top:12px',text:'看图找规律 · 顺手收惊喜 →',onclick:()=>navigate('#/exam-training') }));
  if (!compact) {
    wrap.appendChild(el('p', { text: plan.phase.advice }));
    if (plan.active) for (const r of plan.recommendations) {
      wrap.appendChild(el('div', { style: 'margin-top:12px' }, [
        el('div', { class: 'hint', text: r.reason }),
        el('button', { class: 'btn ghost sm', style: 'margin-top:4px',
          text: `${r.action === "wrongbook" ? "再遇老朋友 · " : ""}${r.title} · ${r.section_name} · ${r.tier_name} →`,
          onclick: () => navigate(r.action === "wrongbook" ? "#/wrongbook" : `#/topic/${r.topic_id}/${r.section_id}/${r.tier}`) }),
      ]));
    }
  }
  const details = el('details', { style: 'font-size:12px;line-height:1.7;margin-top:14px' }, [
    el('summary', { text: '看看学习地图和奖励规则' }),
    el('p', { text: plan.assumptions }), el('p', { text: plan.coverage_note }), el('p', { text: plan.reward_note }),
  ]);
  wrap.appendChild(details);
  return wrap;
}

export function studyLabel(study) {
  if (!study) return '';
  if (!study.eligible) return study.label;
  return `${study.label}${study.active ? ' · 学习奖励 ×2' : ''} · 已探索 ${study.done} 个小站`;
}
