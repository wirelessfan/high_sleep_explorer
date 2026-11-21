/* 科目 / 主题列表 */

import { studyPlanCard, studyLabel } from '../study-plan.js';
import * as api from '../api.js';
import { el, SUBJECT_LABEL, SUBJECT_CLASS, SUBJECT_COLOR } from '../ui.js';
import { navigate } from '../router.js';

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

export async function renderSubjects(view) {
  const catalog = await api.getCatalog();
  const root = el('div', { class: 'stack' });

  root.appendChild(el('div', { style: 'padding:2px 2px 0' }, [
    el('div', { style: 'font-size:11px;letter-spacing:.16em;color:#a3928a;font-weight:700;text-transform:uppercase', text: 'Subjects' }),
    el('div', { style: 'font-size:19px;font-weight:800;letter-spacing:-.01em;margin-top:2px', text: '三条探险路线' }),
    el('div', { style: 'font-size:12px;color:#a3928a;margin-top:3px', text: '每科一条线，挑你想走的那条' }),
  ]));

  /* ---- 吸顶学科跳转条：长页面里少滚几次 ---- */
  if (catalog.subjects.length) {
    const bar = el('div', { class: 'subject-jump', role: 'navigation', 'aria-label': '学科快捷跳转' });
    catalog.subjects.forEach((subj) => {
      bar.appendChild(el('button', {
        class: 'jump-chip',
        style: `--sc:${SUBJECT_COLOR[subj.id]}`,
        onclick: () => {
          const target = root.querySelector(`[data-subject="${subj.id}"]`);
          if (target) target.scrollIntoView({ behavior: 'smooth', block: 'start' });
        },
      }, [
        el('span', { class: 'dot' }),
        el('span', { text: subj.name }),
      ]));
    });
    root.appendChild(bar);
  }

  if (catalog.study_plan) root.appendChild(studyPlanCard(catalog.study_plan, true));

  root.appendChild(el('button', { class: 'btn ghost', text: '🔭 物理学实验简史 · 5 场互动探索实验室', onclick: () => navigate('#/experiments') }));
  root.appendChild(el('button', { class: 'btn ghost', text: '💥 动量守恒 & 机械能守恒 · 5 场互动实验室', onclick: () => navigate('#/momentum-energy') }));
  root.appendChild(el('button', { class: 'btn ghost', text: '⚡ 电磁宇宙加速器 · 回旋 / 轨道炮 / 极光实验室', onclick: () => navigate('#/em-cosmos') }));
  root.appendChild(el('button', { class: 'btn ghost', text: '🔦 光与波的魔法 · 激光光纤 / 音爆 / 降噪实验室', onclick: () => navigate('#/optics-waves') }));
  root.appendChild(el('button', { class: 'btn ghost', text: '🦋 混沌与量子脑洞 · 双摆 / 引力弹弓 / 光电效应', onclick: () => navigate('#/chaos-quantum') }));
  root.appendChild(el('button', { class: 'btn ghost', text: '🔥 热学与微观宇宙 · 布朗运动 / 麦克斯韦妖 / 绝热点火', onclick: () => navigate('#/thermal-micro') }));
  root.appendChild(el('button', { class: 'btn ghost', text: '🛫 风洞与流体奇观 · 机翼失速 / 香蕉球 / 安全线', onclick: () => navigate('#/fluid-windtunnel') }));
  root.appendChild(el('button', { class: 'btn ghost', text: '☢️ 相对论与核风暴 · 光钟 / 金箔散射 / 核裂变控制棒', onclick: () => navigate('#/relativity-nuclear') }));
  root.appendChild(el('button', { class: 'btn ghost', text: '📐 数学直觉实验室 · 函数图像 / 值域扫描 / 三角推导', onclick: () => navigate('#/math-trig-lab') }));
  root.appendChild(el('button',{class:'btn ghost',text:'看图找规律 · 抽着奖把题做了 🙂',onclick:()=>navigate('#/exam-training')}));

  for (const subj of catalog.subjects) {
    const art = SUBJECT_ART[subj.id];
    const doneCount = subj.items.filter((t) => t.complete).length;

    /* ---- 科目横幅 ---- */
    root.appendChild(el('section', {
      class: 'panel subject-banner',
      'data-subject': subj.id,
      style: `--sc:${SUBJECT_COLOR[subj.id]}`,
    }, [
      el('div', { class: 'sb-art' }, [
        art ? el('img', { src: art, alt: '', loading: 'lazy' }) : null,
      ]),
      el('div', { class: 'sb-body' }, [
        el('div', { class: 'row', style: 'gap:7px' }, [
          el('span', { class: `chip ${SUBJECT_CLASS[subj.id]}`, text: subj.name }),
          el('span', { style: 'font-size:11px;color:#a3928a', text: `${doneCount}/${subj.items.length} 主题完成` }),
        ]),
        el('div', {
          style: 'font-size:13px;color:#6b5b52;line-height:1.6;margin-top:7px',
          text: SUBJECT_TAGLINE[subj.id] || '',
        }),
      ]),
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
          el('div', { class: 'dsc', text: studyLabel(t.study) || t.subtitle }),
          el('div', { class: 'row', style: 'gap:6px;margin-top:9px' }, [
            el('span', { class: `chip ${SUBJECT_CLASS[subj.id]}`, style: 'font-size:10px;padding:2px 8px', text: t.grade }),
            el('span', { class: 'chip', style: 'font-size:10px;padding:2px 8px', text: `⏱ ${t.minutes} 分钟` }),
            el('span', { class: 'chip', style: 'font-size:10px;padding:2px 8px', text: `${t.done}/${t.total}` }),
          ]),
        ]),
        el('div', { style: 'font-size:18px;color:#d9c8b4;flex:0 0 auto', text: '›' }),
      ]));
    }
  }

  view.innerHTML = '';
  view.appendChild(root);
}
