/* 错题本：按主题清零 + AI 错误分析 */

import * as api from '../api.js';
import { el, toast, openSheet, SUBJECT_LABEL, SUBJECT_CLASS } from '../ui.js';

const LETTERS = ['A', 'B', 'C', 'D', 'E', 'F'];

function paintAi(holder, value) {
  holder.innerHTML = '';
  if (value.misconception) {
    holder.appendChild(el('div', {
      style: 'font-size:12px;font-weight:800;color:#b45309;background:#fffbeb;border-radius:9px;padding:8px 10px;margin-top:8px',
      text: `🎯 ${value.misconception}`,
    }));
  }
  if (value.analysis) {
    holder.appendChild(el('div', {
      style: 'font-size:12px;color:#5c4b42;line-height:1.7;background:#fdf8f0;border-radius:9px;padding:9px 11px;margin-top:7px',
      text: value.analysis,
    }));
  }
  (value.suggestions || []).forEach((sg) => {
    holder.appendChild(el('div', {
      style: 'font-size:11.5px;color:#0f766e;display:flex;gap:6px;margin-top:5px',
    }, [
      el('span', { style: 'color:#14b8a6', text: '▸' }),
      el('span', { text: sg }),
    ]));
  });
}

export async function renderWrongbook(view) {
  const data = await api.getWrongbook();
  const root = el('div', { class: 'stack' });

  root.appendChild(el('div', { class: 'topbar' }, [
    el('button', { class: 'back', text: '‹', onclick: () => { location.hash = '#/me'; } }),
    el('div', { style: 'flex:1' }, [
      el('h1', { text: '错题本' }),
      el('div', { class: 'sub', text: '做错的题会自动收进来，重做清零有奖励' }),
    ]),
  ]));

  if (!data.items.length) {
    root.appendChild(el('section', { class: 'panel', style: 'text-align:center;padding:34px 18px' }, [
      el('div', { style: 'font-size:40px', text: '🎉' }),
      el('div', { style: 'font-size:15px;font-weight:800;margin-top:10px', text: '错题本是空的' }),
      el('div', { style: 'font-size:12.5px;color:#a3928a;margin-top:6px;line-height:1.8', text: '做错的选择题会自动收进这里。' }),
    ]));
    view.innerHTML = '';
    view.appendChild(root);
    return;
  }

  /* ---- AI 状态条 ---- */
  const ai = data.ai || {};
  if (ai.enabled) {
    root.appendChild(el('section', { class: 'panel', style: 'padding:13px' }, [
      el('div', { class: 'row-between' }, [
        el('div', { class: 'row', style: 'gap:10px' }, [
          el('div', { style: 'width:36px;height:36px;border-radius:11px;background:#eff6ff;display:grid;place-items:center;font-size:16px', text: '🤖' }),
          el('div', {}, [
            el('div', { style: 'font-size:13px;font-weight:800', text: `AI 错误分析 · ${ai.model}` }),
            el('div', { style: 'font-size:11px;color:#a3928a;margin-top:2px', text: `今天已用 ${ai.used_today}/${ai.daily_limit} 次，选错题点「AI 分析」` }),
          ]),
        ]),
      ]),
    ]));
  } else {
    root.appendChild(el('section', { class: 'panel', style: 'padding:13px' }, [
      el('div', { style: 'font-size:12.5px;color:#a3928a', text: 'AI 分析未开放（服务端未配置 LEARN_AI_KEY）。清零与重做不受影响。' }),
    ]));
  }

  /* ---- 按主题分组 ---- */
  const byTopic = {};
  data.items.forEach((it) => {
    const key = it.topic_id;
    (byTopic[key] = byTopic[key] || { title: it.topic_title, subject: it.subject, items: [] }).items.push(it);
  });

  function showAi(it, holder) {
    if (it.ai) { paintAi(holder, it.ai); return; }
    holder.innerHTML = '';
    holder.appendChild(el('button', {
      class: 'btn soft sm', style: 'width:100%',
      text: data.ai?.enabled ? '🤖 AI 分析这道错题' : 'AI 分析未开放',
      disabled: !data.ai?.enabled,
      onclick: async () => {
        btn.disabled = true;
        btn.textContent = '分析中…';
        try {
          const res = await api.analyzeWrong([it.id]);
          const r = res.results[0];
          if (r.error) { toast(r.error); btn.textContent = 'AI 分析这道错题'; btn.disabled = false; return; }
          paintAi(holder, r.value);
          it.ai = r.value;
        } catch (err) {
          toast(err.message || 'AI 分析失败');
          btn.textContent = 'AI 分析这道错题';
          btn.disabled = false;
        }
      },
    }));
    const btn = holder.querySelector('button');
  }

  // paintAi 已提升到模块级（showTopicSheet 也用它）

  const summary = data.summary;
  root.appendChild(el('div', { class: 'section-head' }, [
    el('h3', { text: '待清零' }),
    el('span', { class: 'hint', text: `${summary.open_total} 题 · 清零一个主题 +${summary.clear_bonus} 分` }),
  ]));

  for (const [tid, group] of Object.entries(byTopic)) {
    const items = group.items;
    const card = el('section', { class: 'panel', style: 'padding:14px' });

    card.appendChild(el('div', { class: 'row-between', style: 'margin-bottom:10px' }, [
      el('div', { class: 'row', style: 'gap:8px' }, [
        el('span', { class: `chip ${SUBJECT_CLASS[group.subject] || ''}`, text: SUBJECT_LABEL[group.subject] || group.subject }),
        el('span', { style: 'font-size:13px;font-weight:800', text: group.title }),
      ]),
      el('span', { style: 'font-size:12px;font-weight:800;color:#b45309', text: `${items.length} 题待清` }),
    ]));

    const preview = el('div', { class: 'stack', style: 'gap:7px' });
    items.slice(0, 3).forEach((it) => {
      preview.appendChild(el('div', {
        style: 'font-size:11.5px;color:#6b5b52;background:#fdf8f0;border-radius:9px;padding:8px 10px;' +
          'overflow:hidden;text-overflow:ellipsis;white-space:nowrap',
        text: `${it.skill || '未分类'} · ${it.stem.slice(0, 40)}`,
      }));
    });
    if (items.length > 3) {
      preview.appendChild(el('div', { style: 'font-size:11px;color:#b6a498', text: `… 共 ${items.length} 题` }));
    }
    card.appendChild(preview);

    card.appendChild(el('button', {
      class: 'btn full', style: 'margin-top:12px',
      text: `重做这 ${items.length} 题`,
      onclick: () => renderRedo(view, tid, group.title, items),
    }));

    card.appendChild(el('button', {
      class: 'btn ghost full', style: 'margin-top:8px',
      text: '逐题查看 · AI 分析',
      onclick: () => showTopicSheet(tid, group.title, items),
    }));

    root.appendChild(card);
  }

  /* ---- 已清零统计 ---- */
  if (summary.total_count > summary.open_total) {
    root.appendChild(el('div', {
      style: 'text-align:center;font-size:11.5px;color:#a3928a;padding:10px',
      text: `已清零 ${summary.total_count - summary.open_total} 题 · 累计 ${summary.total_count} 题入本`,
    }));
  }

  view.innerHTML = '';
  view.appendChild(root);
}

/* ---------- 重做流程 ---------- */

async function renderRedo(view, topicId, title, items) {
  const answers = {};
  let idx = 0;

  const root = el('div', { class: 'stack' });
  root.appendChild(el('div', { class: 'topbar' }, [
    el('button', { class: 'back', text: '‹', onclick: () => { location.hash = '#/wrongbook'; } }),
    el('div', { style: 'flex:1' }, [
      el('h1', { text: '错题重做' }),
      el('div', { class: 'sub', text: title }),
    ]),
  ]));

  const body = el('div', { class: 'stack' });
  root.appendChild(body);
  view.innerHTML = '';
  view.appendChild(root);

  function paint() {
    const it = items[idx];
    body.innerHTML = '';

    body.appendChild(el('div', { style: 'font-size:11.5px;color:#a3928a', text: `第 ${idx + 1} / ${items.length} 题 · 曾错 ${it.wrong_count} 次` }));
    body.appendChild(el('section', { class: 'panel' }, [
      el('div', { class: 'q-stem', text: it.stem }),
      el('div', { class: 'q-options' }, it.options.map((o, oi) =>
        el('button', {
          class: `opt ${answers[it.id] === oi ? 'sel' : ''}`,
          type: 'button',
          onclick: () => {
            answers[it.id] = oi;
            paint();
          },
        }, [
          el('span', { class: 'key', text: LETTERS[oi] }),
          el('span', { class: 'txt', text: o }),
        ])
      )),
    ]));

    body.appendChild(el('button', {
      class: 'btn full',
      style: 'margin-top:14px',
      text: idx < items.length - 1 ? '下一题' : '提交清零',
      disabled: answers[it.id] === undefined,
      onclick: () => { if (idx < items.length - 1) { idx += 1; paint(); } else { submit(); } },
    }));
  }

  async function submit() {
    try {
      const res = await api.redoWrongbook(topicId, answers);
      showRedoResult(res, () => { location.hash = '#/wrongbook'; });
    } catch (err) {
      toast(err.message || '提交失败');
    }
  }

  paint();
}

function showRedoResult(res, onClose) {
  const correct = res.results.filter((r) => r.correct).length;
  const box = el('div', { class: 'stack', style: 'gap:11px;text-align:center' });

  box.appendChild(el('div', {}, [
    el('div', { style: 'font-size:38px;font-weight:800;color:#047857', text: `${correct}/${res.results.length}` }),
    el('div', { style: 'font-size:12.5px;color:#a3928a;margin-top:5px', text: '清零进度' }),
  ]));

  const rewards = el('div', { class: 'reward-row' });
  if (res.bonus > 0) {
    rewards.appendChild(el('span', { class: 'reward-pill', text: `🏅 错题清零 +${res.bonus} 积分` }));
  }
  if (res.remaining > 0) {
    rewards.appendChild(el('span', { class: 'reward-pill', text: `还剩 ${res.remaining} 题待清` }));
  }
  if (rewards.children.length) box.appendChild(rewards);

  res.results.forEach((r) => {
    box.appendChild(el('div', {
      style: `text-align:left;border:1px solid ${r.correct ? '#a7f3d0' : '#fecaca'};border-radius:11px;padding:10px 12px;background:${r.correct ? '#f0fdf4' : '#fef2f2'}`,
    }, [
      el('div', { style: 'font-size:12px;line-height:1.6;color:#334155', text: r.stem.slice(0, 60) + (r.stem.length > 60 ? '…' : '') }),
      el('div', { style: `font-size:11px;font-weight:800;margin-top:4px;color:${r.correct ? '#047857' : '#b91c1c'}`,
        text: r.skipped ? '未作答' : (r.correct ? '✓ 答对，已清零' : '✗ 又错了，答对再清') }),
    ]));
  });

  openSheet(el('div', {}, [
    box,
    el('button', { class: 'btn full', style: 'margin-top:15px', text: '完成',
      onclick: () => { document.getElementById('overlay').hidden = true; onClose?.(); } }),
  ]), { title: '重做结果' });
}


/* ---------- 逐题查看 + AI 分析 ---------- */

function showTopicSheet(topicId, title, items) {
  const holder = el('div', { class: 'stack', style: 'gap:14px' });

  items.forEach((it, i) => {
    const block = el('div', { style: 'border-top:1px solid #f6ede0;padding-top:12px' }, [
      el('div', { style: 'display:flex;gap:6px;align-items:center;flex-wrap:wrap' }, [
        el('span', { class: 'chip', style: 'font-size:10px;padding:2px 8px', text: `第 ${i + 1} 题` }),
        it.skill ? el('span', { class: 'chip', style: 'font-size:10px;padding:2px 8px', text: it.skill }) : null,
        el('span', { style: 'font-size:10px;color:#a3928a', text: `曾错 ${it.wrong_count} 次` }),
      ]),
      el('div', { style: 'font-size:13px;line-height:1.65;color:#3b2f2a;margin-top:8px', text: it.stem }),
      el('div', { style: 'margin-top:8px;display:flex;flex-direction:column;gap:4px' },
        it.options.map((o, oi) => el('div', {
          style: `font-size:12px;padding:5px 9px;border-radius:8px;${
            oi === it.answer ? 'background:#f0fdf4;color:#047857;font-weight:700'
            : oi === it.picked ? 'background:#fef2f2;color:#b91c1c' : 'color:#6b5b52'}`,
          text: `${LETTERS[oi]}. ${o}${oi === it.picked ? ' ← 你的选择' : ''}${oi === it.answer ? ' ✓' : ''}`,
        }))),
      el('div', { style: 'font-size:11.5px;color:#6b5b52;line-height:1.7;margin-top:7px', text: it.explain }),
      el('div', { class: 'ai-slot', style: 'margin-top:8px' }),
    ]);

    if (it.ai) paintAi(block.querySelector('.ai-slot'), it.ai);
    else {
      block.querySelector('.ai-slot').appendChild(el('button', {
        class: 'btn soft sm', text: '🤖 AI 分析',
        onclick: async (e) => {
          const btn = e.currentTarget;
          btn.disabled = true;
          btn.textContent = '分析中…';
          try {
            const res = await api.analyzeWrong([it.id]);
            const r = res.results[0];
            if (r.error) { toast(r.error); btn.disabled = false; btn.textContent = '🤖 AI 分析'; return; }
            it.ai = r.value;
            const slot = block.querySelector('.ai-slot');
            slot.innerHTML = '';
            paintAi(slot, r.value);
          } catch (err) {
            toast(err.message || 'AI 分析失败');
            btn.disabled = false;
            btn.textContent = '🤖 AI 分析';
          }
        },
      }));
    }
    holder.appendChild(block);
  });

  openSheet(el('div', {}, [holder]), { title, sub: '红=你的选择，绿=正确答案' });
}
