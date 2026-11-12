/* 主题详情：六版块 × 三档难度 */

import * as api from '../api.js';
import { el, SUBJECT_LABEL, SUBJECT_CLASS, SUBJECT_COLOR, previewImage, previewGallery } from '../ui.js';
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

  const sections = topic.sections || [];
  const units = sections.flatMap((s) => (s.tiers || []).filter((t) => t.available));
  const doneUnits = units.filter((t) => t.status === 'done').length;
  const pct = units.length ? Math.round((doneUnits / units.length) * 100) : 0;
  const color = SUBJECT_COLOR[topic.subject] || '#3b82f6';
  const totalQ = units.reduce((a, t) => a + (t.questions || 0), 0);
  const totalMin = units.reduce((a, t) => a + (t.minutes || 0), 0);

  root.appendChild(el('section', { class: 'panel hero', style: 'padding:15px' }, [
    el('div', { class: 'row-between' }, [
      el('div', { class: 'row', style: 'gap:7px;flex-wrap:wrap' }, [
        el('span', { class: `chip ${SUBJECT_CLASS[topic.subject]}`, text: SUBJECT_LABEL[topic.subject] }),
        el('span', { class: 'chip', text: `⏱ ${totalMin} 分钟` }),
        el('span', { class: 'chip', text: `${totalQ} 题` }),
        el('span', { class: 'chip', text: topic.grade }),
      ]),
      el('div', { class: 'ring', style: `--p:${pct};--ring-color:${color}` }, [
        el('span', { text: `${pct}%` }),
      ]),
    ]),
    el('p', { style: 'margin-top:12px', text: topic.description }),
    // 每个主题的核心过程引导图
    el('div', { class: 'topic-intro-anim', style: 'margin-top:14px;text-align:center' }, [
      el('img', {
        src: `/assets/notes/intro-${id}.svg`,
        alt: `${topic.title} 核心过程动态引导`,
        class: 'scholar-sketch',
        style: 'width:100%;border-radius:12px;display:block;cursor:zoom-in;box-shadow:0 3px 12px rgba(0,0,0,0.06);background:#fff',
      }),
      el('div', {
        class: 'sketch-caption',
        style: 'font-size:11.5px;color:#8c735d;margin-top:6px;display:flex;align-items:center;justify-content:center;gap:4px',
        text: `⚡ ${topic.title} · 过程演示（点击放大查看）`,
      }),
    ]),
    el('div', { class: 'tier-legend', style: 'margin-top:14px' }, (topic.tiers || []).map((t) => el('div', { class: 'tier-legend-item' }, [
      el('b', { text: t.name }),
      el('span', { text: t.score }),
      el('i', { text: t.desc || '' }),
    ]))),
  ]));

  // 图解补充：独立面板，左右翻页
  const diagrams = topic.diagrams || [];
  if (diagrams.length) {
    const cur = el('div', { style: 'font-size:12px;color:#6b5b52;margin-top:8px;line-height:1.6' });
    const idx = el('div', { style: 'font-size:11px;color:#a3928a' });
    const pic = el('img', {
      alt: '',
      style: 'width:100%;border-radius:12px;display:block;cursor:zoom-in;background:#fff;box-shadow:0 3px 12px rgba(0,0,0,.06)',
    });
    let pos = 0;
    const render = () => {
      const d = diagrams[pos];
      pic.src = d.src;
      pic.alt = d.title || '';
      cur.textContent = d.caption || '';
      idx.textContent = `${pos + 1} / ${diagrams.length}`;
    };
    const move = (step) => { pos = (pos + step + diagrams.length) % diagrams.length; render(); };
    pic.addEventListener('click', () => previewGallery(diagrams, pos, topic.title));
    root.appendChild(el('section', { class: 'panel', style: 'padding:13px' }, [
      el('div', { class: 'row-between' }, [
        el('div', { style: 'font-size:13.5px;font-weight:800;text-align:left', text: '图解补充' }),
        idx,
      ]),
      pic,
      cur,
      el('div', { class: 'row', style: 'justify-content:space-between;gap:8px;margin-top:10px' }, [
        el('button', { class: 'btn ghost sm', style: 'flex:1', text: '‹ 上一张', onclick: () => move(-1) }),
        el('button', { class: 'btn ghost sm', style: 'flex:1', text: '下一张 ›', onclick: () => move(1) }),
      ]),
      el('div', { style: 'font-size:11px;color:#a3928a;text-align:center;margin-top:6px', text: '点击图片可全屏查看，支持 ← → 键翻页' }),
    ]));
    render();
  }

  // 关底守关者预告：科学家是唯一的大 BOSS，五个小怪人只是实验体
  const bigBoss = (sections.find((s) => s.boss && s.boss.tier === 'big') || {}).boss;
  const bossPreview = bossBanner(bigBoss, {
    compact: true, kicker: '通关全部难度后挑战',
  });
  if (bossPreview) root.appendChild(bossPreview);

  root.appendChild(el('div', { class: 'section-head' }, [
    el('h3', { text: '六个版块 · 三档难度' }),
    el('span', { class: 'hint', text: `已完成 ${doneUnits}/${units.length} 节` }),
  ]));

  const list = el('div', { class: 'sec-list' });
  sections.forEach((s, i) => {
    const tiers = s.tiers || [];
    const finished = tiers.length > 0 && tiers.every((t) => t.status === 'done');
    const card = el('div', { class: `sec-item tier-card${finished ? ' done' : ''}` }, [
      el('div', { class: 'row', style: 'gap:12px;align-items:center' }, [
        bossThumb(s.boss, { done: finished, fallback: finished ? '✓' : (s.icon || String(i + 1)) }),
        el('div', { class: 'body', style: 'flex:1;min-width:0' }, [
          el('div', { class: 'nm', text: s.name }),
          el('div', { class: 'mt', text: `${s.minutes} 分钟 · ${tiers.reduce((a, t) => a + (t.available ? t.questions : 0), 0)} 题` }),
          bossInline(s.boss),
        ]),
      ]),
      el('div', { class: 'tier-switch tight' }, tiers.map((t) => el('button', {
        class: `tier-pill${t.available ? '' : ' locked'}${t.status === 'done' ? ' done' : ''}`,
        type: 'button',
        title: t.available ? (t.desc || '') : '该难度正在建设中',
        onclick: () => { if (t.available) navigate(`#/topic/${id}/${s.id}/${t.id}`); },
      }, [
        el('span', { class: 'tp-name', text: t.name }),
        el('span', { class: 'tp-score', text: t.available ? t.score : '建设中' }),
        t.status === 'done' ? el('span', { class: 'tp-done', text: '✓' }) : null,
      ]))),
    ]);
    list.appendChild(card);
  });
  root.appendChild(list);

  root.appendChild(el('div', {
    style: 'text-align:center;font-size:11px;color:#b6c2d2;padding:12px 0 4px',
    text: '建议顺序：先把六个版块的基础档走完，再进进阶、高级',
  }));

  view.innerHTML = '';
  view.appendChild(root);

  // 绑定引导图点击全屏放大预览
  root.addEventListener('click', (e) => {
    const target = e.target.closest('.scholar-sketch, img.zoomable');
    if (target && target.src) {
      previewImage(target.src, target.alt || `${topic.title} 动态引导`);
    }
  });
}
