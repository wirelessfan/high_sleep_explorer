/* 首页：今日任务、签到、进度 */

import { studyPlanCard, studyLabel } from '../study-plan.js';
import * as api from '../api.js';
import { el, toast, SUBJECT_LABEL, SUBJECT_CLASS, SUBJECT_COLOR } from '../ui.js';
import { navigate } from '../router.js';
import { loadBuild, versionLine } from '../build-info.js';

export async function renderHome(view) {
  const [catalog, me, checkin, daily, history, build] = await Promise.all([
    api.getCatalog(),
    api.fetchMe(),
    api.getCheckin(),
    api.getDaily(),
    /* 历史事件库为空或接口异常时不应拖垮整个首页 */
    api.getHistory().catch(() => null),
    loadBuild(),
  ]);

  const topics = catalog.subjects.flatMap((s) =>
    s.items.map((t) => ({ ...t, subjectId: s.id, subjectName: s.name, color: s.color }))
  );
  const next = topics.find((t) => !t.complete) || topics[0];
  const doneToday = checkin.checked_today;
  /* 三档扩容后主题时长差异很大（36–181 分钟），文案一律按目录实时值算 */
  const allMinutes = topics.map((t) => t.minutes || 0);
  const minMinutes = allMinutes.length ? Math.min(...allMinutes) : 0;
  const maxMinutes = allMinutes.length ? Math.max(...allMinutes) : 0;

  const root = el('div', { class: 'stack' });

  /* ---- 顶部问候 ---- */
  const who = (me.username || me.nickname || 'sunny').toLowerCase();
  root.appendChild(el('div', { class: 'row-between', style: 'padding:2px 2px 0' }, [
    el('div', {}, [
      el('div', { style: 'font-size:11px;letter-spacing:.16em;color:var(--ink-3);font-weight:700;text-transform:uppercase', text: 'Sunny · Exploring' }),
      el('div', {
        style: 'font-size:20px;font-weight:800;letter-spacing:-.01em;margin-top:2px',
        text: `hello, ${who}`,
      }),
    ]),
    el('div', { class: 'row', style: 'gap:6px' }, [
      el('span', { class: 'chip', text: `⚡ ${me.points}` }),
      el('span', { class: 'chip', text: `🎟 ${me.tickets}` }),
    ]),
  ]));

  if (catalog.study_plan) root.appendChild(studyPlanCard(catalog.study_plan));

  /* ---- 每日主题（节日特辑优先） ---- */
  root.appendChild(renderDaily(daily));

  /* ---- 今日任务 ---- */
  if (next && !catalog.study_plan?.active) {
    const left = next.total - next.done;
    const mins = Math.max(5, Math.min(30, Math.round(next.minutes * (left / next.total))));
    root.appendChild(el('section', { class: 'panel hero' }, [
      el('div', { class: 'hero-art' }, [
        el('img', { src: '/assets/art/hero-journey.svg', alt: '', loading: 'eager' }),
        el('span', { class: 'badge', text: '☀️ 今天的探险' }),
      ]),
      el('div', { class: 'eyebrow', text: `今日约 ${mins} 分钟` }),
      el('h2', { text: next.title }),
      el('p', { text: next.description || next.subtitle }),
      el('div', { class: 'meta' }, [
        el('span', { class: `chip ${SUBJECT_CLASS[next.subjectId]}`, text: SUBJECT_LABEL[next.subjectId] }),
        el('span', { class: 'chip', text: `⏱ 约 ${mins} 分钟` }),
        el('span', { class: 'chip', text: next.done > 0 ? `✓ ${next.done}/${next.total} 单元` : `${next.done}/${next.total} 单元` }),
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

  /* ---- 放松抽卡入口 ---- */
  root.appendChild(el('section', { class: 'panel', style: 'padding:13px;margin-top:10px' }, [
    el('div', { class: 'row-between' }, [
      el('div', { class: 'row', style: 'gap:10px;min-width:0' }, [
        el('div', {
          style: 'width:36px;height:36px;border-radius:12px;background:#fff7ed;border:1px solid #fed7aa;display:grid;place-items:center;font-size:17px;flex:0 0 auto',
          text: '🎁',
        }),
        el('div', { style: 'min-width:0' }, [
          el('div', { style: 'font-size:13px;font-weight:800', text: '学累了？去休闲游戏广场放松' }),
          el('div', { style: 'font-size:11px;color:#a3928a;margin-top:2px', text: '砸金蛋、转盘、扑克对决，想玩就玩' }),
        ]),
      ]),
      el('button', {
        class: 'btn sm', text: '去玩',
        onclick: () => navigate('#/games'),
      }),
    ]),
  ]));

  /* ---- 历史上的今天 ---- */
  if (history && history.entry) root.appendChild(renderHistory(history));

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
        el('div', { style: 'font-size:11.5px;color:#a3928a;margin-top:3px', text: `${doneSections}/${totalSections} 个单元 · ${doneTopics}/${totalTopics} 个主题全通` }),
      ]),
    ]),
  ]));

  /* ---- 各科入口 ---- */
  const sec = el('div', { class: 'section-head' }, [
    el('h3', { text: '按科目' }),
    el('span', { class: 'hint', text: catalog.study_plan?.active ? '挑一个好奇的话题，慢慢逛' : `每个主题 ${minMinutes}–${maxMinutes} 分钟` }),
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
            el('div', { class: 'dsc', text: studyLabel(t.study) || t.subtitle }),
            el('div', { class: 'bar' }, [
              el('i', { style: `width:${t.percent}%;background:${SUBJECT_COLOR[subj.id]}` }),
            ]),
          ]),
          el('div', { style: 'font-size:11px;font-weight:800;color:#a3928a;flex:0 0 auto', text: `${t.done}/${t.total}` }),
        ])
      )),
    ]));
  }

  /* ---- 底部小提示 + 版本号 ---- */
  root.appendChild(versionLine(build, '有空就逛一小站，带着好奇心慢慢发现'));

  view.innerHTML = '';
  view.appendChild(root);
}

/* ---------- 每日主题卡片 ---------- */

function fmtDate(iso) {
  const parts = String(iso || '').split('-');
  if (parts.length !== 3) return '';
  return `${Number(parts[1])} 月 ${Number(parts[2])} 日`;
}

function renderDaily(daily) {
  const s = daily.special;
  const t = daily.topic;
  const wrap = el('section', {
    class: `panel daily${s ? ` acc-${s.accent || 'fresh'}` : ''}`,
    'data-daily': daily.date,
  });

  /* 头部：特辑用节日 emoji，平日用日历 */
  wrap.appendChild(el('div', { class: 'daily-head' }, [
    el('span', { class: 'daily-emoji', text: s ? (s.emoji || '📅') : '📅' }),
    el('div', { class: 'daily-head-txt' }, [
      el('div', {
        class: 'daily-eyebrow',
        text: `${daily.study_plan?.active ? '今天想探索什么' : s ? '节日特辑' : '今日主题'} · ${daily.weekday} · ${fmtDate(daily.date)}`,
      }),
      el('h2', { class: 'daily-title', text: s ? s.title : t.title }),
    ]),
  ]));

  if (s) {
    if (s.tagline) wrap.appendChild(el('p', { class: 'daily-tag', text: s.tagline }));
    if (s.description) wrap.appendChild(el('p', { class: 'daily-desc', text: s.description }));

    /* 三道「算一算」：点击展开答案，不判分、不落库 */
    for (const item of s.digest || []) {
      const ans = el('div', { class: 'digest-a', hidden: true, text: item.a });
      const more = el('span', { class: 'digest-more', text: '看答案' });
      const btn = el('button', { class: 'digest-q', type: 'button' }, [
        el('span', { class: 'digest-mark', text: 'Q' }),
        el('span', { class: 'digest-txt', text: item.q }),
        more,
      ]);
      btn.addEventListener('click', () => {
        ans.hidden = !ans.hidden;
        btn.classList.toggle('open', !ans.hidden);
        more.textContent = ans.hidden ? '看答案' : '收起';
      });
      wrap.appendChild(el('div', { class: 'digest' }, [btn, ans]));
    }

    if (s.aside) wrap.appendChild(el('div', { class: 'daily-aside', text: s.aside }));
  } else {
    wrap.appendChild(el('p', { class: 'daily-tag', text: t.subtitle }));
    wrap.appendChild(el('p', { class: 'daily-desc', text: daily.study_plan?.active ? '从图像和小问题出发，慢慢把规律想明白。可以先看提示，再试试自己的想法。' : t.description }));
    if (daily.quote) {
      wrap.appendChild(el('div', { class: 'daily-quote' }, [
        el('span', { text: daily.quote.text }),
        el('b', { text: `— ${daily.quote.by}` }),
      ]));
    }
  }

  /* 底部：今日主题的身份 + 入口 */
  wrap.appendChild(el('div', { class: 'daily-foot' }, [
    el('div', { class: 'row', style: 'gap:6px;flex-wrap:wrap' }, [
      el('span', { class: `chip ${SUBJECT_CLASS[t.subject]}`, text: t.subject_name }),
      !daily.study_plan?.active ? el('span', { class: 'chip', text: `⏱ 全程 ${t.minutes} 分钟` }) : null,
      el('span', { class: 'chip', text: daily.study_plan?.active ? `已探索 ${t.done} 个小站` : `${t.done}/${t.total} 单元` }),
    ]),
    el('button', {
      class: 'btn sm',
      text: daily.study_plan?.active ? (daily.study_plan.recommendations[0]?.action === 'wrongbook' ? '再看看，可能有新发现' : '逛逛这个小站') : s ? '开始今日主题' : (t.complete ? '复习一遍' : '去闯关'),
      onclick: () => {
        const r = daily.study_plan?.active && daily.study_plan.recommendations[0];
        navigate(r?.action === "wrongbook" ? "#/wrongbook" : r ? `#/topic/${r.topic_id}/${r.section_id}/${r.tier}` : `#/topic/${t.id}`);
      },
    }),
  ]));
  return wrap;
}

/* ---------- 历史上的今天 ---------- */

function offsetLabel(n) {
  if (!n) return '';
  return n < 0 ? `${Math.abs(n)} 天前` : `${n} 天后`;
}

function renderHistory(h) {
  const e = h.entry;
  const wrap = el('section', { class: 'panel history', 'data-history': h.date });

  /* 头部：日期 + 标题 */
  const eyebrow = h.fallback
    ? `历史上的今天 · 最近的一条 ${h.entry_date}（${offsetLabel(h.offset_days)}）`
    : `历史上的今天 · ${h.entry_date}`;
  wrap.appendChild(el('div', { class: 'history-head' }, [
    el('span', { class: 'history-emoji', text: '🔭' }),
    el('div', { class: 'history-head-txt' }, [
      el('div', { class: 'history-eyebrow', text: eyebrow }),
      el('h2', { class: 'history-title', text: e.title }),
    ]),
  ]));

  /* 年代 / 领域 / 人物 */
  const chips = [];
  if (e.year) chips.push(el('span', { class: 'chip history-year', text: e.year < 1000 ? `公元 ${e.year} 年` : `${e.year} 年` }));
  if (e.field) chips.push(el('span', { class: 'chip', text: e.field }));
  if (e.person) chips.push(el('span', { class: 'chip', text: `👤 ${e.person}` }));
  if (chips.length) {
    wrap.appendChild(el('div', { class: 'row', style: 'gap:6px;flex-wrap:wrap;margin-top:10px' }, chips));
  }

  /* 故事正文；长文默认折起，避免首页被一段长故事撑满 */
  const story = el('p', { class: 'history-story', text: e.story });
  wrap.appendChild(story);
  if ((e.story || '').length > 96) {
    story.classList.add('clamp');
    const more = el('button', { class: 'history-more', type: 'button', text: '展开全文 ↓' });
    more.addEventListener('click', () => {
      story.classList.toggle('clamp');
      more.textContent = story.classList.contains('clamp') ? '展开全文 ↓' : '收起 ↑';
    });
    wrap.appendChild(more);
  }

  /* 一句话记住 */
  if (e.learn) {
    wrap.appendChild(el('div', { class: 'history-learn' }, [
      el('span', { class: 'history-learn-mark', text: '记' }),
      el('span', { text: e.learn }),
    ]));
  }

  /* 关联主题：从故事跳到课本 */
  if (h.topic) {
    wrap.appendChild(el('div', { class: 'history-foot' }, [
      el('span', { class: 'history-foot-hint', text: '这件事和你的课本有关' }),
      el('button', {
        class: 'btn sm ghost',
        text: `${h.topic.title} →`,
        onclick: () => navigate(`#/topic/${h.topic.id}`),
      }),
    ]));
  }
  return wrap;
}

