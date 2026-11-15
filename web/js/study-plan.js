import { el } from './ui.js';
import { navigate } from './router.js';

export function studyPlanCard(plan, compact = false) {
  if (!plan) return null;
  const wrap = el('section', { class: 'panel', 'data-study-plan': plan.id });
  wrap.appendChild(el('div', { class: 'eyebrow', text: `Sunny · ${plan.region} · ${plan.grade}` }));
  wrap.appendChild(el('h2', { text: plan.scope }));
  wrap.appendChild(el('p', { text: `${plan.date_estimated ? '预计' : ''}${plan.exam_date} 考试 · ${plan.active ? `还有 ${plan.days_left} 天` : '活动未开始或已结束'} · ${plan.phase.name}` }));
  wrap.appendChild(el('div', { class: 'row', style: 'gap:7px;flex-wrap:wrap' }, [
    el('span', { class: 'chip', text: `学习积分 ×${plan.points_multiplier}` }),
    el('span', { class: 'chip', text: `学习卡包 ×${plan.tickets_multiplier}` }),
    el('span', { class: 'chip', text: `备考单元 ${plan.done}/${plan.total}` }),
  ]));
  if (!compact) {
    wrap.appendChild(el('p', { text: plan.phase.advice }));
    if (plan.active) for (const r of plan.recommendations) {
      wrap.appendChild(el('div', { style: 'margin-top:12px' }, [
        el('div', { class: 'hint', text: r.reason }),
        el('button', { class: 'btn ghost sm', style: 'margin-top:4px',
          text: `${r.action === "wrongbook" ? "去错题本 · " : ""}${r.title} · ${r.section_name} · ${r.tier_name} →`,
          onclick: () => navigate(r.action === "wrongbook" ? "#/wrongbook" : `#/topic/${r.topic_id}/${r.section_id}/${r.tier}`) }),
      ]));
    }
  }
  const details = el('details', { style: 'font-size:12px;line-height:1.7;margin-top:14px' }, [
    el('summary', { text: '查看备考范围与奖励规则' }),
    el('p', { text: plan.assumptions }), el('p', { text: plan.coverage_note }), el('p', { text: plan.reward_note }),
  ]);
  wrap.appendChild(details);
  return wrap;
}

export function studyLabel(study) {
  if (!study) return '';
  if (!study.eligible) return study.label;
  return `${study.label}${study.active ? ' · 学习奖励 ×2' : ''} · ${study.done}/${study.total} 备考单元`;
}
