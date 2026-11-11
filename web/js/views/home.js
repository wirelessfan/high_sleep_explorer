/* 首页：今日任务、签到、进度 */

import * as api from '../api.js';
import { el, toast, SUBJECT_LABEL, SUBJECT_CLASS, SUBJECT_COLOR } from '../ui.js';
import { navigate } from '../router.js';

export async function renderHome(view) {
  const [catalog, me, checkin] = await Promise.all([
    api.getCatalog(),
    api.fetchMe(),
    api.getCheckin(),
  ]);

  const topics = catalog.subjects.flatMap((s) =>
    s.items.map((t) => ({ ...t, subjectId: s.id, subjectName: s.name, color: s.color }))
  );
  const next = topics.find((t) => !t.complete) || topics[0];
  const doneToday = checkin.checked_today;

  const root = el('div', { class: 'stack' });

  /* ---- 顶部问候 ---- */
  root.appendChild(el('div', { class: 'row-between', style: 'padding:2px 2px 0' }, [
    el('div', {}, [
      el('div', { style: 'font-size:11px;letter-spacing:.16em;color:var(--ink-3);font-weight:700;text-transform:uppercase', text: 'Sunny · Exploring' }),
      el('div', {
        style: 'font-size:20px;font-weight:800;letter-spacing:-.01em;margin-top:2px',
        text: 'hello, sunny',
      }),
    ]),
    el('div', { class: 'row', style: 'gap:6px' }, [
      el('span', { class: 'chip', text: `⚡ ${me.points}` }),
      el('span', { class: 'chip', text: `🎟 ${me.tickets}` }),
    ]),
  ]));

  /* ---- 今日任务 ---- */
  if (next) {
    const left = next.total - next.done;
    const mins = Math.max(5, Math.min(30, Math.round(next.minutes * (left / next.total))));
    root.appendChild(el('section', { class: 'panel hero' }, [
      el('div', { class: 'hero-art' }, [
        el('img', { src: '/assets/art/hero-journey.svg', alt: '', loading: 'eager' }),
        el('span', { class: 'badge', text: '☀️ 今天的探险' }),
      ]),
      el('div', { class: 'eyebrow', text: '今日 25 分钟' }),
      el('h2', { text: next.title }),
      el('p', { text: next.description || next.subtitle }),
      el('div', { class: 'meta' }, [
        el('span', { class: `chip ${SUBJECT_CLASS[next.subjectId]}`, text: SUBJECT_LABEL[next.subjectId] }),
        el('span', { class: 'chip', text: `⏱ 约 ${mins} 分钟` }),
        el('span', { class: 'chip', text: `✓ ${next.done}/${next.total} 版块` }),
      ]),
      el('div', { class: 'row', style: 'margin-top:16px;gap:9px' }, [
        el('button', {
          class: 'btn', text: next.done ? '继续探险' : '出发闯关',
          onclick: () => navigate(`#/topic/${next.id}`),
        }),
        el('button', {
          class: 'btn ghost', text: '全部主题',
          onclick: () => navigate('#/subjects'),
        }),
      ]),
    ]));
  }

  /* ---- 签到条 ---- */
  const checkinPanel = el('section', { class: 'panel' }, [
    el('div', { class: 'row-between' }, [
      el('div', { class: 'row', style: 'gap:11px' }, [
        el('div', {
          style: 'width:38px;height:38px;border-radius:12px;background:#fff7ed;border:1px solid #fed7aa;display:grid;place-items:center;font-size:17px',
          text: doneToday ? '✅' : '🔥',
        }),
        el('div', {}, [
          el('div', { style: 'font-size:13.5px;font-weight:800', text: doneToday ? '今天已签到' : '还没签到' }),
          el('div', { style: 'font-size:11.5px;color:#a3928a;margin-top:2px', text: `连签 ${checkin.streak} 天 · 累计 ${me.points} 分` }),
        ]),
      ]),
      doneToday ? el('span', { class: 'chip', text: '已领取' }) : el('button', {
        class: 'btn sm', text: '签到 +10',
        onclick: async (e) => {
          const btn = e.currentTarget;
          btn.disabled = true;
          try {
            const res = await api.doCheckin();
            toast(res.already ? '今天已经签过了' : `签到成功 +${res.points} 分${res.tickets ? ` · +${res.tickets} 张卡包` : ''}`);
            const me2 = await api.fetchMe();
            window.dispatchEvent(new CustomEvent('me:update', { detail: me2 }));
            const { render } = await import('../router.js');
            render();
          } catch (err) {
            toast(err.message || '签到失败');
            btn.disabled = false;
          }
        },
      }),
    ]),
  ]);
  root.appendChild(checkinPanel);

  /* ---- 学习进度 ---- */
  const totalTopics = topics.length;
  const doneTopics = topics.filter((t) => t.complete).length;
  const totalSections = topics.reduce((a, t) => a + t.total, 0);
  const doneSections = topics.reduce((a, t) => a + t.done, 0);
  const pct = totalSections ? Math.round((doneSections / totalSections) * 100) : 0;

  root.appendChild(el('section', { class: 'panel' }, [
    el('div', { class: 'row', style: 'gap:14px' }, [
      el('div', { class: 'ring', style: `--p:${pct};--ring-color:#10b981` }, [
        el('span', { text: `${pct}%` }),
      ]),
      el('div', { style: 'flex:1' }, [
        el('div', { style: 'font-size:14px;font-weight:800', text: '总体进度' }),
        el('div', { style: 'font-size:11.5px;color:#a3928a;margin-top:3px', text: `${doneSections}/${totalSections} 个版块 · ${doneTopics}/${totalTopics} 个主题全通` }),
      ]),
    ]),
  ]));

  /* ---- 各科入口 ---- */
  const sec = el('div', { class: 'section-head' }, [
    el('h3', { text: '按科目' }),
    el('span', { class: 'hint', text: '每个主题 25 分钟' }),
  ]);
  root.appendChild(sec);

  for (const subj of catalog.subjects) {
    const items = subj.items;
    const allDone = items.every((t) => t.complete);
    root.appendChild(el('section', { class: 'panel', style: 'padding:14px' }, [
      el('div', { class: 'row-between', style: 'margin-bottom:10px' }, [
        el('div', { class: 'row', style: 'gap:8px' }, [
          el('span', { class: `chip ${SUBJECT_CLASS[subj.id]}`, text: subj.name }),
          el('span', { style: 'font-size:11.5px;color:#a3928a', text: allDone ? '已完成' : `${items.filter(t=>t.complete).length}/${items.length} 主题` }),
        ]),
        el('button', {
          style: `font-size:12px;font-weight:700;color:${SUBJECT_COLOR[subj.id]}`,
          text: '查看全部 →',
          onclick: () => navigate('#/subjects'),
        }),
      ]),
      el('div', { class: 'stack', style: 'gap:8px' }, items.map((t) =>
        el('div', {
          class: 'topic-card', style: 'cursor:pointer;box-shadow:none;padding:11px',
          onclick: () => navigate(`#/topic/${t.id}`),
        }, [
          el('div', { class: 'accent', style: `background:${SUBJECT_COLOR[subj.id]}` }),
          el('div', { class: 'body' }, [
            el('div', { class: 'ttl', text: t.title }),
            el('div', { class: 'dsc', text: t.subtitle }),
            el('div', { class: 'bar' }, [
              el('i', { style: `width:${t.percent}%;background:${SUBJECT_COLOR[subj.id]}` }),
            ]),
          ]),
          el('div', { style: 'font-size:11px;font-weight:800;color:#a3928a;flex:0 0 auto', text: `${t.done}/${t.total}` }),
        ])
      )),
    ]));
  }

  /* ---- 底部小提示 ---- */
  root.appendChild(el('div', {
    style: 'text-align:center;font-size:11px;color:#b6c2d2;padding:10px 0 4px',
    text: '每天 20–30 分钟，一个主题刚好',
  }));

  view.innerHTML = '';
  view.appendChild(root);
}
