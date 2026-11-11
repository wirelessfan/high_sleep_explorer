/* 主题详情：六版块列表 */

import * as api from '../api.js';
import { el, SUBJECT_LABEL, SUBJECT_CLASS, SUBJECT_COLOR } from '../ui.js';
import { navigate } from '../router.js';
import { bossBanner, bossThumb, bossInline } from '../boss.js';

export async function renderTopic(view, { id }) {
  const topic = await api.getTopic(id);
  const root = el('div', { class: 'stack' });

  root.appendChild(el('div', { class: 'topbar' }, [
    el('button', { class: 'back', text: '‹', onclick: () => history.back() }),
    el('div', { style: 'flex:1' }, [
      el('h1', { text: topic.title }),
      el('div', { class: 'sub', text: topic.subtitle }),
    ]),
  ]));

  const doneCount = topic.sections.filter((s) => s.status === 'done').length;
  const pct = Math.round((doneCount / topic.sections.length) * 100);
  const color = SUBJECT_COLOR[topic.subject] || '#3b82f6';

  root.appendChild(el('section', { class: 'panel hero', style: 'padding:15px' }, [
    el('div', { class: 'row-between' }, [
      el('div', { class: 'row', style: 'gap:7px' }, [
        el('span', { class: `chip ${SUBJECT_CLASS[topic.subject]}`, text: SUBJECT_LABEL[topic.subject] }),
        el('span', { class: 'chip', text: `⏱ ${topic.minutes} 分钟` }),
        el('span', { class: 'chip', text: topic.grade }),
      ]),
      el('div', { class: 'ring', style: `--p:${pct};--ring-color:${color}` }, [
        el('span', { text: `${pct}%` }),
      ]),
    ]),
    el('p', { style: 'margin-top:12px', text: topic.description }),
  ]));

  // 关底守关者预告：科学家是唯一的大 BOSS，五个小怪人只是实验体
  const bigBoss = (topic.sections.find((s) => s.boss && s.boss.tier === 'big') || {}).boss;
  const bossPreview = bossBanner(bigBoss, {
    compact: true, kicker: '通关全部版块后挑战',
  });
  if (bossPreview) root.appendChild(bossPreview);

  root.appendChild(el('div', { class: 'section-head' }, [
    el('h3', { text: '六个版块' }),
    el('span', { class: 'hint', text: `已完成 ${doneCount}/${topic.sections.length}` }),
  ]));

  const list = el('div', { class: 'sec-list' });
  topic.sections.forEach((s, i) => {
    const done = s.status === 'done';
    list.appendChild(el('button', {
      class: `sec-item ${done ? 'done' : ''}`,
      style: 'text-align:left;width:100%',
      onclick: () => navigate(`#/topic/${id}/${s.id}`),
    }, [
      bossThumb(s.boss, { done, fallback: done ? '✓' : (s.icon || String(i + 1)) }),
      el('div', { class: 'body' }, [
        el('div', { class: 'nm', text: s.name }),
        el('div', { class: 'mt', text: done ? '已完成 · 可复习' : `${s.minutes} 分钟` }),
        bossInline(s.boss),
      ]),
      el('div', { class: 'go', text: done ? '复习' : '开始 ›' }),
    ]));
  });
  root.appendChild(list);

  root.appendChild(el('div', {
    style: 'text-align:center;font-size:11px;color:#b6c2d2;padding:12px 0 4px',
    text: '按顺序做效果最好，也可以跳着看',
  }));

  view.innerHTML = '';
  view.appendChild(root);
}
