/* 学习心得体会专栏：列表页 + 文章路由分发 */

import { el } from '../ui.js';
import { navigate } from '../router.js';
import { COLUMN, ESSAYS, essayBySlug } from '../essays.js';

const LIST_CSS = `
.es-hero{position:relative;overflow:hidden;padding:20px 18px 18px;border-radius:20px;
  background:linear-gradient(140deg,#fff7e6 0%,#fffdf8 46%,#eef6ff 100%);
  border:1px solid #f3e3c9;box-shadow:0 12px 30px -22px rgba(120,80,30,.5)}
.es-hero::after{content:"";position:absolute;right:-46px;top:-52px;width:168px;height:168px;border-radius:50%;
  background:radial-gradient(circle at 40% 40%,rgba(251,191,36,.32),rgba(251,191,36,0) 68%)}
.es-kicker{font-size:10.5px;font-weight:800;letter-spacing:.18em;color:#b45309;text-transform:uppercase}
.es-title{font-size:24px;font-weight:900;letter-spacing:-.02em;color:#2b1f18;margin:6px 0 8px;line-height:1.2}
.es-intro{font-size:12.8px;line-height:1.75;color:#6b5b52;margin:0}
.es-stats{display:flex;gap:6px;flex-wrap:wrap;margin-top:12px}
.es-stat{font-size:11px;font-weight:800;color:#92400e;background:#fff;border:1px solid #f5dfbc;
  border-radius:999px;padding:3px 9px}
.es-card{display:block;position:relative;padding:16px 16px 14px;border-radius:18px;background:#fff;
  border:1px solid var(--line);cursor:pointer;transition:transform .12s ease,box-shadow .12s ease,border-color .12s ease}
.es-card:active{transform:scale(.988)}
.es-card .ico{width:38px;height:38px;border-radius:12px;display:grid;place-items:center;font-size:18px;
  background:#eff6ff;border:1px solid #bfdbfe;flex:0 0 auto}
.es-card h3{font-size:15.5px;font-weight:900;line-height:1.42;letter-spacing:-.01em;color:#1f2937;margin:0}
.es-card .lead{font-size:12px;line-height:1.7;color:#8a7a70;margin-top:6px;
  display:-webkit-box;-webkit-line-clamp:3;-webkit-box-orient:vertical;overflow:hidden}
.es-tags{display:flex;gap:5px;flex-wrap:wrap;margin-top:9px}
.es-tag{font-size:10.5px;font-weight:700;color:#7c6a5e;background:#faf4ea;border:1px solid #f0e4d4;
  border-radius:999px;padding:2px 7px}
.es-meta{font-size:11px;color:#a3928a;margin-top:9px;display:flex;gap:8px;flex-wrap:wrap;align-items:center}
.es-dot{width:3px;height:3px;border-radius:50%;background:#d9c8b4}
.es-more{font-size:12px;font-weight:800;color:#2563eb;margin-top:10px;display:inline-flex;align-items:center;gap:4px}
`;

function articleCard(essay) {
  return el('article', {
    class: 'es-card',
    onclick: () => { if (essay.ready) navigate(essay.route); },
  }, [
    el('div', { class: 'row-between', style: 'align-items:flex-start;gap:10px' }, [
      el('div', { class: 'ico', text: essay.emoji || '📖' }),
      essay.featured
        ? el('span', {
          style: 'font-size:10px;font-weight:900;color:#b45309;background:#fffbeb;border:1px solid #fcd34d;border-radius:999px;padding:2px 8px',
          text: '专栏首篇',
        })
        : null,
    ]),
    el('h3', { style: 'margin-top:11px', text: essay.title }),
    el('div', { class: 'lead', text: essay.lead }),
    el('div', { class: 'es-tags' }, (essay.tags || []).map((t) => el('span', { class: 'es-tag', text: t }))),
    el('div', { class: 'es-meta' }, [
      el('span', { text: essay.date }),
      el('span', { class: 'es-dot' }),
      el('span', { text: `${(essay.sections || []).length} 章 · 可打印` }),
    ]),
    el('div', { class: 'es-more', text: '开始阅读 →' }),
  ]);
}

export async function renderEssays(view) {
  const root = el('div', { class: 'stack' });
  const st = document.createElement('style');
  st.textContent = LIST_CSS;
  root.appendChild(st);

  root.appendChild(el('div', { class: 'topbar' }, [
    el('button', {
      class: 'back', text: '‹',
      onclick: () => { if (history.length > 1) history.back(); else navigate('#/me'); },
    }),
    el('div', { style: 'flex:1;min-width:0' }, [
      el('h1', { text: COLUMN.title }),
      el('div', { class: 'sub', text: `${ESSAYS.filter((e) => e.ready).length} 篇文章 · 手机上可读，也能打印成 A4` }),
    ]),
  ]));

  root.appendChild(el('section', { class: 'es-hero' }, [
    el('div', { class: 'es-kicker', text: 'Reading · 陪读手账' }),
    el('h2', { class: 'es-title', text: '比刷题更值得花时间的，是想清楚怎么学' }),
    el('p', { class: 'es-intro', text: COLUMN.intro }),
    el('div', { class: 'es-stats' }, [
      el('span', { class: 'es-stat', text: '🖨️ 一键打印 / 存 PDF' }),
      el('span', { class: 'es-stat', text: '👨‍👩‍👧 适合亲子共读' }),
      el('span', { class: 'es-stat', text: '📐 与互动实验室配套' }),
    ]),
  ]));

  for (const essay of ESSAYS) {
    if (!essay.ready) continue;
    root.appendChild(articleCard(essay));
  }

  root.appendChild(el('section', {
    class: 'panel',
    style: 'background:linear-gradient(135deg,#f8fafc,#fff);border-color:#dbe6f0;padding:14px',
  }, [
    el('div', { style: 'font-size:13px;font-weight:800;color:#334155', text: '✍️ 这个专栏还在长' }),
    el('div', {
      class: 'hint', style: 'margin-top:5px',
      text: '想看的主题（怎么看懂函数图像、物理实验怎么复盘、考前一周怎么安排）都可以直接说。下一批文章会接着写。',
    }),
    el('div', { class: 'row', style: 'gap:8px;margin-top:11px;flex-wrap:wrap' }, [
      el('button', { class: 'btn sm ghost', text: '💌 去许愿墙点题', onclick: () => navigate('#/wishes') }),
      el('button', { class: 'btn sm ghost', text: '📝 反馈一段心得', onclick: () => navigate('#/feedback') }),
    ]),
  ]));

  root.appendChild(el('section', {
    class: 'panel', style: 'cursor:pointer;background:linear-gradient(135deg,#eff6ff,#fff);border-color:#bfdbfe',
    onclick: () => navigate('#/math-trig-lab'),
  }, [
    el('div', { class: 'row-between' }, [
      el('div', { class: 'row', style: 'gap:11px' }, [
        el('div', {
          style: 'width:40px;height:40px;border-radius:12px;background:#dbeafe;display:grid;place-items:center;font-size:17px',
          text: '📐',
        }),
        el('div', {}, [
          el('div', { style: 'font-size:13.5px;font-weight:800', text: '看完就去动手：数学直觉实验室' }),
          el('div', { style: 'font-size:11.5px;color:#a3928a;margin-top:3px', text: '平移穿轴 · 值域扫描 · 降幂辅助角 · 诱导公式' }),
        ]),
      ]),
      el('div', { style: 'font-size:18px;color:#d9c8b4', text: '›' }),
    ]),
  ]));

  view.innerHTML = '';
  view.appendChild(root);
}

/* #/essays/:slug 分发；未知 slug 给一张友好的空卡 */
export async function renderEssay(view, params) {
  const essay = essayBySlug(params?.slug);
  if (essay && essay.slug === 'intuition') {
    const { renderIntuitionArticle } = await import('./intuition-article.js');
    return renderIntuitionArticle(view);
  }
  const root = el('div', { class: 'stack' });
  root.appendChild(el('div', { class: 'topbar' }, [
    el('button', { class: 'back', text: '‹', onclick: () => navigate(COLUMN.route) }),
    el('div', { style: 'flex:1;min-width:0' }, [
      el('h1', { text: '这篇文章还在写' }),
      el('div', { class: 'sub', text: '先看专栏里已经上线的文章' }),
    ]),
  ]));
  root.appendChild(el('section', { class: 'panel' }, [
    el('div', { style: 'font-size:13.5px;font-weight:800', text: '没找到这篇' }),
    el('div', { class: 'hint', style: 'margin-top:6px', text: '链接可能过期了，或者文章还没发布。' }),
    el('button', {
      class: 'btn sm', style: 'margin-top:12px', text: '回到专栏首页',
      onclick: () => navigate(COLUMN.route),
    }),
  ]));
  view.innerHTML = '';
  view.appendChild(root);
}
