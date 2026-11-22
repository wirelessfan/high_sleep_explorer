/* 科目 / 主题列表
 *
 * 三层信息架构：
 *   ① 顶层 · 跨学科工具条（1 行 2 张卡，不再是一堵全宽按钮墙）
 *   ② 中层 · 学科 Tab（一次只看一科，sessionStorage 记住上次选的科目）
 *   ③ 底层 · 单科内部「A 互动探索实验室 → B 系统闯关主线（按年级分层）」
 */

import { studyPlanCard, studyLabel } from '../study-plan.js';
import * as api from '../api.js';
import { el, SUBJECT_CLASS, SUBJECT_COLOR } from '../ui.js';
import { navigate } from '../router.js';
import {
  TOP_TOOLS,
  LABS_BY_SUBJECT,
  LAB_CATEGORIES,
  LAB_ZONE_TITLE,
  GRADE_ORDER,
  gradeLabel,
} from '../labs-config.js';

const SUBJECT_ART = {
  physics: '/assets/art/topic-physics.svg',
  chemistry: '/assets/art/topic-chemistry.svg',
  math: '/assets/art/topic-math.svg',
};

const SUBJECT_TAGLINE = {
  physics: '力、电、光——把世界拆成能算的方程',
  chemistry: '反应、平衡、结构——看见看不见的变化',
  math: '函数、图形、极限——给规律一个符号',
};

const TAB_KEY = 'subjects.tab.v1';
const FEATURED_N = 4;

/* 跨路由保留的轻量交互状态（切 Tab / 展开 / 筛选都不丢） */
let currentTab = null;
const expanded = {};
const filters = {};

function readTab(subjects) {
  try {
    const saved = sessionStorage.getItem(TAB_KEY);
    if (saved && subjects.some((s) => s.id === saved)) return saved;
  } catch { /* 隐私模式下 sessionStorage 可能不可用 */ }
  return subjects[0]?.id || null;
}

function saveTab(id) {
  try { sessionStorage.setItem(TAB_KEY, id); } catch { /* ignore */ }
}

function gradeRank(grade) {
  const i = GRADE_ORDER.findIndex((g) => (grade || '').startsWith(g));
  return i < 0 ? GRADE_ORDER.length : i;
}

/* ---------- ① 顶层：跨学科工具条 ---------- */

function toolBar() {
  return el('div', { class: 'tool-duo' }, TOP_TOOLS.map((t) =>
    el('button', {
      type: 'button',
      class: 'tool-card',
      onclick: () => navigate(t.route),
    }, [
      el('span', { class: 'ti', text: t.icon }),
      el('span', { class: 'tc' }, [
        el('span', { class: 'tt', text: t.title }),
        el('span', { class: 'td', text: t.desc }),
      ]),
    ])));
}

function essayLine() {
  return el('button', {
    type: 'button',
    class: 'essay-line',
    onclick: () => navigate('#/essays'),
  }, [
    el('span', { text: '📖 学习心得体会' }),
    el('span', { class: 'el-sub', text: '专栏 · 第 1 篇「看见公式背后的风」' }),
    el('span', { class: 'el-go', text: '›' }),
  ]);
}

/* ---------- ③-A 单科：互动探索实验室 ---------- */

function labCard(lab) {
  if (lab.hero) {
    /* 单卡学科（数学错题专项）：横向高优卡片，不做成两个半空的小格子 */
    return el('button', {
      type: 'button',
      class: 'lab-card hero',
      onclick: () => navigate(lab.route),
    }, [
      el('span', { class: 'lc-ico big', text: lab.icon }),
      el('span', { class: 'lc-main' }, [
        el('span', { class: 'lc-ttl', text: lab.title }),
        el('span', { class: 'lc-kw', text: lab.kw }),
      ]),
      el('span', { class: 'lc-cat', text: lab.category }),
      el('span', { class: 'lc-go', text: '›' }),
    ]);
  }
  return el('button', {
    type: 'button',
    class: 'lab-card',
    onclick: () => navigate(lab.route),
  }, [
    el('span', { class: 'lc-top' }, [
      el('span', { class: 'lc-ico', text: lab.icon }),
      el('span', { class: 'lc-cat', text: lab.category }),
    ]),
    el('span', { class: 'lc-ttl', text: lab.title }),
    el('span', { class: 'lc-kw', text: lab.kw }),
  ]);
}

function labZone(subjId, rerender) {
  const labs = LABS_BY_SUBJECT[subjId] || [];
  if (!labs.length) return null; /* 化学暂无实验：整区不渲染，不留空白 */

  const meta = LAB_ZONE_TITLE[subjId] || { title: '互动探索实验室', kicker: '先建直觉' };
  const zone = el('section', { class: 'zone lab-zone' }, [
    el('div', { class: 'zone-head' }, [
      el('div', { class: 'zt', text: meta.title }),
      el('span', { class: 'zc', text: `${labs.length} 个` }),
      el('span', { class: 'zk', text: meta.kicker }),
    ]),
  ]);

  const cats = LAB_CATEGORIES.filter((c) => labs.some((l) => l.category === c));
  const useFilter = cats.length >= 2;
  let active = useFilter ? (filters[subjId] || '全部') : '全部';
  if (active !== '全部' && !cats.includes(active)) active = '全部';

  if (useFilter) {
    const row = el('div', { class: 'filter-row', role: 'group', 'aria-label': '实验室模块筛选' });
    for (const cat of ['全部', ...cats]) {
      row.appendChild(el('button', {
        type: 'button',
        class: `f-chip${cat === active ? ' active' : ''}`,
        'aria-pressed': cat === active ? 'true' : 'false',
        text: cat,
        onclick: () => {
          filters[subjId] = cat;
          rerender();
        },
      }));
    }
    zone.appendChild(row);
  }

  const shown = active === '全部' ? labs : labs.filter((l) => l.category === active);
  const ordered = [...shown.filter((l) => l.featured), ...shown.filter((l) => !l.featured)];
  const foldable = active === '全部' && ordered.length > FEATURED_N;
  const open = foldable && !!expanded[subjId];
  const visible = open || !foldable ? ordered : ordered.slice(0, FEATURED_N);

  const grid = el('div', { class: `lab-grid${shown.length === 1 ? ' solo' : ''}` });
  for (const lab of visible) grid.appendChild(labCard(lab));
  zone.appendChild(grid);

  if (foldable) {
    const rest = ordered.length - visible.length;
    zone.appendChild(el('div', { class: 'lab-more' }, [
      el('button', {
        type: 'button',
        class: 'more-btn',
        text: rest > 0 ? `展开全部 ${ordered.length} 个实验室 ▾` : '收起 ▴',
        onclick: () => {
          expanded[subjId] = rest > 0;
          rerender();
        },
      }),
    ]));
  }
  return zone;
}

/* ---------- ③-B 单科：系统闯关主线（按年级分层） ---------- */

function topicCard(subj, t) {
  const color = SUBJECT_COLOR[subj.id];
  const percent = Number(t.percent) || 0;
  return el('div', {
    class: 'topic-card',
    style: 'cursor:pointer',
    onclick: () => navigate(`#/topic/${t.id}`),
  }, [
    el('div', { class: 'accent', style: `background:${color}` }),
    el('div', { class: 'body' }, [
      el('div', { class: 'row', style: 'gap:7px' }, [
        el('div', { class: 'ttl', text: t.title }),
        t.complete ? el('span', {
          class: 'chip', style: 'font-size:10px;padding:1px 7px;background:#ecfdf5;border-color:#a7f3d0;color:#047857',
          text: '已完成',
        }) : null,
      ]),
      el('div', { class: 'dsc', text: studyLabel(t.study) || t.subtitle }),
      percent > 0 ? el('div', { class: 'bar' }, [
        el('i', { style: `width:${percent}%;background:${color}` }),
      ]) : null,
      el('div', { class: 'row', style: 'gap:6px;margin-top:9px' }, [
        el('span', { class: `chip ${SUBJECT_CLASS[subj.id]}`, style: 'font-size:10px;padding:2px 8px', text: t.grade }),
        el('span', { class: 'chip', style: 'font-size:10px;padding:2px 8px', text: `⏱ ${t.minutes} 分钟` }),
        el('span', { class: 'chip', style: 'font-size:10px;padding:2px 8px', text: `${t.done}/${t.total}` }),
      ]),
    ]),
    el('div', { style: 'font-size:18px;color:#d9c8b4;flex:0 0 auto', text: '›' }),
  ]);
}

function topicZone(subj) {
  const zone = el('section', { class: 'zone' }, [
    el('div', { class: 'zone-head' }, [
      el('div', { class: 'zt', text: '系统闯关主线' }),
      el('span', { class: 'zc', text: `${subj.items.length} 个主题` }),
      el('span', { class: 'zk', text: '按年级推进' }),
    ]),
  ]);

  const groups = new Map();
  for (const t of subj.items) {
    const key = (t.grade || '').trim();
    if (!groups.has(key)) groups.set(key, []);
    groups.get(key).push(t);
  }

  const keys = [...groups.keys()].sort((a, b) => gradeRank(a) - gradeRank(b));
  for (const key of keys) {
    const items = groups.get(key);
    const done = items.filter((t) => t.complete).length;
    zone.appendChild(el('div', { class: 'grade-group' }, [
      el('div', { class: 'grade-head' }, [
        el('div', { class: 'gh', text: gradeLabel(key) }),
        el('span', { class: 'gn', text: `${done}/${items.length} 完成` }),
      ]),
      el('div', { class: 'grade-list' }, items.map((t) => topicCard(subj, t))),
    ]));
  }
  return zone;
}

/* ---------- ② 中层：学科横幅 + Tab ---------- */

function banner(subj) {
  const art = SUBJECT_ART[subj.id];
  const doneCount = subj.items.filter((t) => t.complete).length;
  return el('section', {
    class: 'panel subject-banner',
    style: `--sc:${SUBJECT_COLOR[subj.id]}`,
  }, [
    art ? el('div', { class: 'sb-art' }, [
      el('img', { src: art, alt: '', loading: 'lazy' }),
    ]) : null,
    el('div', { class: 'sb-body' }, [
      el('div', { class: 'row', style: 'gap:7px' }, [
        el('span', { class: `chip ${SUBJECT_CLASS[subj.id]}`, text: subj.name }),
        el('span', { style: 'font-size:11px;color:#a3928a', text: `${doneCount}/${subj.items.length} 主题完成` }),
      ]),
      el('div', {
        style: 'font-size:12.5px;color:#6b5b52;line-height:1.55;margin-top:6px',
        text: SUBJECT_TAGLINE[subj.id] || '',
      }),
    ]),
  ]);
}

export async function renderSubjects(view) {
  const catalog = await api.getCatalog();
  const subjects = catalog.subjects || [];

  const root = el('div', { class: 'stack subj-page' });
  root.appendChild(el('div', { style: 'padding:2px 2px 0' }, [
    el('div', { style: 'font-size:11px;letter-spacing:.16em;color:#a3928a;font-weight:700;text-transform:uppercase', text: 'Subjects' }),
    el('div', { style: 'font-size:19px;font-weight:800;letter-spacing:-.01em;margin-top:2px', text: '三条探险路线' }),
    el('div', { style: 'font-size:12px;color:#a3928a;margin-top:3px', text: '每科一条线，挑你想走的那条' }),
  ]));

  root.appendChild(toolBar());
  root.appendChild(essayLine());

  if (!subjects.length) {
    root.appendChild(el('div', { class: 'panel', style: 'font-size:13px;color:#8a7a70', text: '还没有可探索的学科，稍后再来看看。' }));
    view.innerHTML = '';
    view.appendChild(root);
    return;
  }

  currentTab = readTab(subjects);

  const tabs = el('div', { class: 'subject-tabs', role: 'tablist', 'aria-label': '学科切换' });
  const stage = el('div', { class: 'subj-stage' });

  const renderPanel = () => {
    const subj = subjects.find((s) => s.id === currentTab);
    stage.replaceChildren();
    if (!subj) return;
    stage.appendChild(banner(subj));
    const labs = labZone(subj.id, renderPanel);
    if (labs) stage.appendChild(labs);
    stage.appendChild(topicZone(subj));
    for (const btn of tabs.children) {
      const on = btn.dataset.tab === currentTab;
      btn.classList.toggle('active', on);
      btn.setAttribute('aria-selected', on ? 'true' : 'false');
      btn.tabIndex = on ? 0 : -1;
    }
  };

  for (const subj of subjects) {
    const done = subj.items.filter((t) => t.complete).length;
    const btn = el('button', {
      type: 'button',
      class: 'st-tab',
      role: 'tab',
      'data-tab': subj.id,
      style: `--sc:${SUBJECT_COLOR[subj.id]}`,
      'aria-selected': 'false',
      onclick: () => {
        if (currentTab === subj.id) return;
        currentTab = subj.id;
        saveTab(subj.id);
        renderPanel();
        /* 已经滚到内容区时，把视口收回到 Tab 下沿，别让人停在半截 */
        const top = tabs.getBoundingClientRect().top + window.scrollY;
        if (window.scrollY > top + 4) window.scrollTo({ top: Math.max(0, top - 2) });
      },
    }, [
      el('span', { class: 'dot' }),
      el('span', { class: 'nm', text: subj.name }),
      el('span', { class: 'ct', text: `${done}/${subj.items.length}` }),
    ]);
    tabs.appendChild(btn);
  }

  root.appendChild(tabs);
  root.appendChild(stage);
  renderPanel();

  if (catalog.study_plan) root.appendChild(studyPlanCard(catalog.study_plan, true));

  view.innerHTML = '';
  view.appendChild(root);
}
