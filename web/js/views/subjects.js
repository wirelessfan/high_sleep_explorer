/* 科目 / 主题列表 */

import * as api from '../api.js';
import { el, SUBJECT_LABEL, SUBJECT_CLASS, SUBJECT_COLOR } from '../ui.js';
import { navigate } from '../router.js';

export async function renderSubjects(view) {
  const catalog = await api.getCatalog();
  const root = el('div', { class: 'stack' });

  root.appendChild(el('div', { style: 'padding:2px 2px 0' }, [
    el('div', { style: 'font-size:11px;letter-spacing:.16em;color:#94a3b8;font-weight:700;text-transform:uppercase', text: 'Subjects' }),
    el('div', { style: 'font-size:19px;font-weight:800;letter-spacing:-.01em;margin-top:2px', text: '全部主题' }),
  ]));

  for (const subj of catalog.subjects) {
    root.appendChild(el('div', { class: 'section-head' }, [
      el('h3', { text: subj.name }),
      el('span', { class: 'hint', text: `${subj.items.length} 个主题` }),
    ]));

    for (const t of subj.items) {
      root.appendChild(el('div', {
        class: 'topic-card',
        style: 'cursor:pointer',
        onclick: () => navigate(`#/topic/${t.id}`),
      }, [
        el('div', { class: 'accent', style: `background:${SUBJECT_COLOR[subj.id]}` }),
        el('div', { class: 'body' }, [
          el('div', { class: 'row', style: 'gap:7px' }, [
            el('div', { class: 'ttl', text: t.title }),
            t.complete ? el('span', {
              class: 'chip', style: 'font-size:10px;padding:1px 7px;background:#ecfdf5;border-color:#a7f3d0;color:#047857',
              text: '已完成',
            }) : null,
          ]),
          el('div', { class: 'dsc', text: t.subtitle }),
          el('div', { class: 'row', style: 'gap:6px;margin-top:9px' }, [
            el('span', { class: `chip ${SUBJECT_CLASS[subj.id]}`, style: 'font-size:10px;padding:2px 8px', text: t.grade }),
            el('span', { class: 'chip', style: 'font-size:10px;padding:2px 8px', text: `⏱ ${t.minutes} 分钟` }),
            el('span', { class: 'chip', style: 'font-size:10px;padding:2px 8px', text: `${t.done}/${t.total}` }),
          ]),
        ]),
        el('div', { style: 'font-size:18px;color:#cbd5e1;flex:0 0 auto', text: '›' }),
      ]));
    }
  }

  view.innerHTML = '';
  view.appendChild(root);
}
