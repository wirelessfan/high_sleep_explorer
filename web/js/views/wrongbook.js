/* 错题本：按主题清零 + AI 错误分析 */

import { mountReflection } from '../reflection.js';
import * as api from '../api.js';
import { el, toast, openSheet, SUBJECT_LABEL, SUBJECT_CLASS } from '../ui.js';

import { questionText } from '../question-content.js';
import { feedbackButton } from '../question-feedback.js';

const LETTERS = ['A', 'B', 'C', 'D', 'E', 'F'];

/* 导入错题的学科/章节友好标签（SUBJECT_LABEL 未覆盖的补齐） */
const SUBJECT_FALLBACK = { biology: '生物', geography: '地理', cross: '跨学科' };
function subjectLabel(s) {
  return SUBJECT_LABEL[s] || SUBJECT_FALLBACK[s] || s || '未分类';
}
function imageList(it) {
  return (it.images || []).map((p) => {
    const privatePhoto = p.startsWith('/api/v1/wrongbook/photo/image/');
    const img = el('img', {
      ...(privatePhoto ? {} : { src: p }),
      alt: '题目配图',
      style: 'max-width:100%;border-radius:10px;border:1px solid #f0e4d5;margin-top:8px;display:block',
      loading: 'lazy',
    });
    if (privatePhoto) {
      fetch(p, { headers: { Authorization: `Bearer ${api.getToken()}` } })
        .then(r => { if (!r.ok) throw new Error('图片读取失败'); return r.blob(); })
        .then(blob => { const url = URL.createObjectURL(blob); img.onload = () => URL.revokeObjectURL(url); img.src = url; })
        .catch(() => { img.alt = '图片读取失败，请重新登录后重试'; });
    }
    return img;
  });
}
function reasonBlock(it) {
  const frag = [];
  if (it.wrong_reason) {
    frag.push(el('div', {
      style: 'font-size:12px;color:#b45309;background:#fffbeb;border-radius:9px;padding:8px 10px;margin-top:8px;line-height:1.7',
      text: `🎯 我的错因：${it.wrong_reason}`,
    }));
  }
  if (it.derivation) {
    frag.push(el('div', {
      style: 'font-size:12px;color:#1e3a5f;background:#f0f6ff;border-radius:9px;padding:9px 11px;margin-top:7px;line-height:1.8;white-space:pre-line',
      text: `✍️ 正确推导：${it.derivation}`,
    }));
  }
  return frag;
}


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

/* AI 任务按钮：点击 → 失败恢复原状，成功由 task() 自己重挂内容 */
function aiTaskButton(label, task) {
  const btn = el('button', { class: 'btn soft sm', style: 'width:100%', text: label });
  btn.addEventListener('click', async () => {
    btn.disabled = true;
    btn.textContent = '生成中…';
    try {
      await task();
    } catch (err) {
      toast(err.message || 'AI 任务失败');
      btn.disabled = false;
      btn.textContent = label;
    }
  });
  return btn;
}

/* AI 独立解题：AI 答案与标准答案并排 + 分步过程 */
function paintSolve(holder, value, it) {
  holder.innerHTML = '';
  const aiLetter = value.answer_letter || '?';
    const stdLetter = it.qtype === 'multi_choice'
      ? (it.answer_indices || []).map(i => LETTERS[i]).join('、') : (LETTERS[it.answer] ?? '?');
    const agree = aiLetter === stdLetter;
  holder.appendChild(el('div', { style: 'display:flex;gap:6px;align-items:center;margin-top:8px;flex-wrap:wrap' }, [
    el('span', { style: 'font-size:10px;font-weight:800;color:#1d4ed8;background:#eff6ff;border-radius:8px;padding:3px 8px',
      text: `🧠 AI 解答 ${aiLetter}` }),
    el('span', { style: `font-size:10px;font-weight:800;border-radius:8px;padding:3px 8px;${
      agree ? 'color:#047857;background:#f0fdf4' : 'color:#b45309;background:#fffbeb'}`,
      text: agree ? `与标准答案 ${stdLetter} 一致` : `标准答案 ${stdLetter}，AI 有分歧` }),
    value.stub ? el('span', { style: 'font-size:10px;color:#a3928a', text: '演示' }) : null,
  ]));
  (value.steps || []).forEach((s, i) => {
    holder.appendChild(el('div', { style: 'font-size:12px;color:#5c4b42;line-height:1.7;background:#fdf8f0;border-radius:9px;padding:8px 10px;margin-top:6px;display:flex;gap:7px' }, [
      el('span', { style: 'color:#14b8a6;font-weight:800;flex-shrink:0', text: `${i + 1}` }),
      el('span', { text: s }),
    ]));
  });
  if (value.key_point) {
    holder.appendChild(el('div', { style: 'font-size:11.5px;color:#0f766e;margin-top:7px', text: `💡 ${value.key_point}` }));
  }
}

/* 举一反三：变式题卡，先自选再翻答案 */
function paintVariants(holder, value) {
  holder.innerHTML = '';
  holder.appendChild(el('div', { class: 'hint', text: 'AI 生成练习 · 不计积分，答案请结合原题解析核对' }));
  (value.variants || []).forEach((v, vi) => {
    const card = el('div', { style: 'background:#f0f9ff;border-radius:11px;padding:10px 11px;margin-top:8px' });
    card.appendChild(el('div', { style: 'font-size:10px;font-weight:800;color:#0369a1;margin-bottom:5px',
      text: `🌱 变式 ${vi + 1}（先选一个答案再看解析）` }));
    card.appendChild(el('div', { style: 'font-size:12.5px;line-height:1.65;color:#3b2f2a', text: v.stem }));
    const reveal = el('div', { style: 'display:none' });
    v.options.forEach((o, oi) => {
      card.appendChild(el('button', {
        type: 'button',
        style: 'display:block;width:100%;text-align:left;font-size:12px;padding:6px 9px;border-radius:8px;margin-top:5px;background:#fff;color:#6b5b52;border:1px solid #e3f0fb;cursor:pointer',
        text: `${LETTERS[oi]}. ${o}`,
        onclick: (e) => {
          const btn = e.currentTarget;
          const picked = oi;
          card.querySelectorAll('button').forEach((b) => { b.disabled = true; });
          btn.style.fontWeight = '800';
          btn.style.color = picked === v.answer ? '#047857' : '#b91c1c';
          btn.style.background = picked === v.answer ? '#f0fdf4' : '#fef2f2';
          reveal.innerHTML = '';
          reveal.style.display = 'block';
          reveal.appendChild(el('div', {
            style: `font-size:11.5px;font-weight:800;margin-top:7px;color:${picked === v.answer ? '#047857' : '#b91c1c'}`,
            text: picked === v.answer
              ? `✓ 答对了，正确答案 ${LETTERS[v.answer]}`
              : `✗ 正确答案是 ${LETTERS[v.answer]}`,
          }));
          if (v.explain) {
            reveal.appendChild(el('div', { style: 'font-size:11.5px;color:#6b5b52;line-height:1.7;margin-top:3px', text: v.explain }));
          }
        },
      }));
    });
    card.appendChild(reveal);
    holder.appendChild(card);
  });
}


export async function renderWrongbook(view) {
  const data = await api.getWrongbook();
  const root = el('div', { class: 'stack' });

  root.appendChild(el('div', { class: 'topbar' }, [
    el('button', { class: 'back', text: '‹', onclick: () => { location.hash = '#/me'; } }),
    el('div', { style: 'flex:1' }, [
      el('h1', { text: '错题本' }),
      el('div', { class: 'sub', text: '全家共用一本错题账本 · 重做清零有奖励' }),
    ]),
  ]));

  /* ---- 家庭共享说明（所有账号看到的是同一本错题本） ---- */
  root.appendChild(el('section', {
    class: 'panel',
    style: 'padding:11px 13px;background:#f5f9ff;border:1px solid #e2edfb',
  }, [
    el('div', { style: 'font-size:12px;color:#1e3a5f;line-height:1.75' },
      [el('b', { text: '👨‍👩‍👧 家庭共享：' }),
       el('span', { text: '家庭题库按原规则共享；个人拍照题保留录入者归属，明确共享的照片供其他站内用户只读查看，重做及修改仅限所有者。' })]),
  ]));

  /* ---- 拍照录入入口（演示页） ---- */
  root.appendChild(el('button', {
    class: 'btn soft full',
    text: '📷 拍照录入错题（演示）',
    onclick: () => { location.href = '/demo/photo.html'; },
  }));

  if (!data.items.length) {
    root.appendChild(el('section', { class: 'panel', style: 'text-align:center;padding:34px 18px' }, [
      el('div', { style: 'font-size:40px', text: '🎉' }),
      el('div', { style: 'font-size:15px;font-weight:800;margin-top:10px', text: '错题本是空的' }),
      el('div', { style: 'font-size:12.5px;color:#a3928a;margin-top:6px;line-height:1.8', text: '做错的选择题会自动收进这里；用电脑上的「错题本一键启动」录入，或点上面拍照录入。' }),
    ]));
    view.innerHTML = '';
    view.appendChild(root);
    return;
  }

  /* ---- AI 状态条 ---- */
  const ai = data.ai || {};
  if (ai.enabled) {
    const t = ai.tasks?.analyze || {};
    root.appendChild(el('section', { class: 'panel', style: 'padding:13px' }, [
      el('div', { class: 'row-between' }, [
        el('div', { class: 'row', style: 'gap:10px' }, [
          el('div', { style: 'width:36px;height:36px;border-radius:11px;background:#eff6ff;display:grid;place-items:center;font-size:16px', text: '🤖' }),
          el('div', {}, [
            el('div', { style: 'font-size:13px;font-weight:800', text: `AI 多通道${ai.stub ? ' · 演示模式' : ''}` }),
            el('div', { class: 'ai-usage', style: 'font-size:11px;color:#a3928a;margin-top:2px',
              text: `今天已用 ${ai.used_today || 0} 次 · 错因分析走 ${t.model || '?'}（${ai.used_by_task?.analyze || 0}/${t.limit || '?'}）` }),
          ]),
        ]),
      ]),
    ]));
  } else {
    root.appendChild(el('section', { class: 'panel', style: 'padding:13px' }, [
      el('div', { style: 'font-size:12.5px;color:#a3928a', text: 'AI 分析未开放（服务端未配置通道 Key）。清零与重做不受影响。' }),
    ]));
  }

  /* ---- 按主题分组 ---- */
  const byTopic = {};
  data.items.forEach((it) => {
    const key = it.topic_id;
    const group = byTopic[key] = byTopic[key] || { title: it.topic_title, subject: it.subject, items: [], pending: [] };
    (it.review_status === 'ready' ? group.items : group.pending).push(it);
  });

  function updateUsage(task, result) {
    ai.used_by_task ||= {};
    ai.used_by_task[task] = result.ai_used_today;
    ai.used_today = Object.values(ai.used_by_task).reduce((sum, n) => sum + n, 0);
    const node = root.querySelector('.ai-usage');
    const t = ai.tasks?.analyze || {};
    if (node) node.textContent = `今天已用 ${ai.used_today} 次 · 错因分析走 ${t.model || '?'}（${ai.used_by_task.analyze || 0}/${t.limit || '?'}）`;
  }

  // paintAi 已提升到模块级（showTopicSheet 也用它）

  const summary = data.summary;
  root.appendChild(el('div', { class: 'section-head' }, [
    el('h3', { text: '待清零' }),
    el('span', { class: 'hint', text: `${summary.open_total} 题 · 清零一个主题 +${summary.clear_bonus} 分` }),
  ]));

  for (const [tid, group] of Object.entries(byTopic)) {
    const items = group.items;
    const pendingItems = group.pending;
    const card = el('section', { class: 'panel', style: 'padding:14px' });

    card.appendChild(el('div', { class: 'row-between', style: 'margin-bottom:10px' }, [
      el('div', { class: 'row', style: 'gap:8px' }, [
        el('span', { class: `chip ${SUBJECT_CLASS[group.subject] || ''}`, text: subjectLabel(group.subject) }),
        el('span', { style: 'font-size:13px;font-weight:800', text: group.title }),
      ]),
      el('span', { style: 'font-size:12px;font-weight:800;color:#b45309', text: `${items.length} 题待清${pendingItems.length ? ` · ${pendingItems.length} 题待补录` : ''}` }),
    ]));

    const preview = el('div', { class: 'stack', style: 'gap:7px' });
    items.slice(0, 3).forEach((it) => {
      preview.appendChild(el('div', {
        style: 'font-size:11.5px;color:#6b5b52;background:#fdf8f0;border-radius:9px;padding:8px 10px;' +
          'overflow:hidden;text-overflow:ellipsis;white-space:nowrap',
        text: `${it.review_status === 'ready' ? it.skill || '未分类' : '待补录'} · ${questionText(it.stem).slice(0, 40)}`,
      }));
    });
    if (items.length > 3) {
      preview.appendChild(el('div', { style: 'font-size:11px;color:#b6a498', text: `… 共 ${items.length} 题` }));
    }
    card.appendChild(preview);

    const editable = items.filter(it => it.can_edit !== false);
    if (editable.length) card.appendChild(el('button', {
      class: 'btn full', style: 'margin-top:12px',
      text: `重做这 ${editable.length} 题`,
      onclick: () => renderRedo(view, tid, group.title, editable),
    }));

    if (items.length) card.appendChild(el('button', {
      class: 'btn ghost full', style: 'margin-top:8px',
      text: '逐题查看 · AI 分析',
      onclick: () => showTopicSheet(tid, group.title, items, ai, updateUsage),
    }));
    pendingItems.forEach((it) => {
      card.appendChild(el('div', { style: 'margin-top:9px;padding:9px 10px;border-left:3px solid #d97706;background:#fffbeb;font-size:12px;line-height:1.65' }, [
        el('strong', { text: `待补录 · ${it.review_reason || '原题信息待核对'}` }),
        el('div', { style: 'margin-top:4px;white-space:pre-line', text: questionText(it.stem) }),
        ...imageList(it),
      ]));
    });

    root.appendChild(card);
  }

  /* ---- 已清零统计 ---- */
  const clearedCount = summary.total_count - summary.open_total - (summary.pending_total || 0);
  if (clearedCount > 0) {
    root.appendChild(el('div', {
      style: 'text-align:center;font-size:11.5px;color:#a3928a;padding:10px',
      text: `已清零 ${clearedCount} 题 · 累计 ${summary.total_count} 题入本`,
    }));
  }

  view.innerHTML = '';
  view.appendChild(root);
}

/* ---------- 重做流程 ---------- */

async function renderRedo(view, topicId, title, items) {
  const answers = {};
  const multiAnswers = {};
  const fillAnswers = {};
  let idx = 0;
  let busy = false;
  const returnToList = () => renderWrongbook(view).catch((err) => toast(err.message || '刷新失败'));

  const root = el('div', { class: 'stack' });
  root.appendChild(el('div', { class: 'topbar' }, [
    el('button', { class: 'back', text: '‹', onclick: returnToList }),
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
    const isChoice = ['choice', 'multi_choice'].includes(it.qtype || 'choice');
    const answered = isChoice
      ? (it.qtype === 'multi_choice' ? (multiAnswers[it.id] || []).length > 0 : answers[it.id] !== undefined)
      : (fillAnswers[it.id] || '').trim() !== '';
    body.innerHTML = '';

    body.appendChild(el('div', { style: 'font-size:11.5px;color:#a3928a', text: `第 ${idx + 1} / ${items.length} 题 · 曾错 ${it.wrong_count} 次 · ${it.qtype === 'multi_choice' ? '多选题 · 全部选对才清零' : (isChoice ? '选择题' : (it.qtype === 'solution' ? '解答题' : '填空题'))}` }));
    body.appendChild(el('section', { class: 'panel' }, [
      el('div', { class: 'q-stem', text: questionText(it.stem), style: 'white-space:pre-line' }),
      ...imageList(it),
      isChoice
        ? el('div', { class: 'q-options' }, it.options.map((o, oi) =>
          el('button', {
            class: `opt ${(it.qtype === 'multi_choice' ? (multiAnswers[it.id] || []).includes(oi) : answers[it.id] === oi) ? 'sel' : ''}`,
            type: 'button',
            onclick: () => {
              if (it.qtype === 'multi_choice') {
                const selected = new Set(multiAnswers[it.id] || []);
                selected.has(oi) ? selected.delete(oi) : selected.add(oi);
                multiAnswers[it.id] = [...selected].sort((a, b) => a - b);
              } else answers[it.id] = oi;
              paint();
            },
          }, [
            el('span', { class: 'key', text: LETTERS[oi] }),
            el('span', { class: 'txt', text: o }),
          ])
        ))
        : el('div', { style: 'margin-top:10px' }, [
          el('div', { style: 'font-size:11.5px;color:#a3928a;margin-bottom:6px', text: '把你的答案写在下面（与正确答案比对后自动判分）' }),
          el('input', {
            type: 'text',
            value: fillAnswers[it.id] || '',
            placeholder: '例如：2 或 (−∞,3−2√2]',
            style: 'width:100%;font:inherit;font-size:13px;padding:10px 12px;border:1px solid #eadfd3;border-radius:10px;background:#fffdf9',
            oninput: (e) => { fillAnswers[it.id] = e.target.value; },
            onchange: () => paint(),
          }),
        ]),
    ]));

    if (it.source === 'practice') body.appendChild(feedbackButton({ topic_id: it.topic_id, section_id: it.section_id, tier: it.tier, question_id: it.question_id, wrong_question_id: it.id }, it));
    body.appendChild(el('button', {
      class: 'btn full',
      style: 'margin-top:14px',
      text: idx < items.length - 1 ? '下一题' : '提交清零',
      disabled: busy || !answered,
      onclick: () => { if (idx < items.length - 1) { idx += 1; paint(); } else { submit(); } },
    }));
  }

  async function submit() {
    if (busy) return;
    busy = true;
    paint();
    try {
      const res = await api.redoWrongbook(topicId, answers, fillAnswers, multiAnswers);
      await returnToList();
      showRedoResult(res, returnToList);
    } catch (err) {
      toast(err.message || '提交失败');
      busy = false;
      paint();
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
    const item = el('div', {
      style: `text-align:left;border:1px solid ${r.correct ? '#a7f3d0' : '#fecaca'};border-radius:11px;padding:10px 12px;background:${r.correct ? '#f0fdf4' : '#fef2f2'}`,
    }, [
      el('div', { style: 'font-size:12px;line-height:1.6;color:#334155', text: r.stem.slice(0, 60) + (r.stem.length > 60 ? '…' : '') }),
      el('div', { style: `font-size:11px;font-weight:800;margin-top:4px;color:${r.correct ? '#047857' : '#b91c1c'}`,
        text: r.skipped ? '未作答' : (r.correct ? '✓ 答对，已清零' : '✗ 又错了，答对再清') }),
      r.answer_text || r.qtype === 'multi_choice'
        ? el('div', { style: 'font-size:11.5px;color:#1e3a5f;margin-top:3px', text: `正确答案：${r.answer_text || (r.answer_indices || []).map(i => LETTERS[i]).join('、')}` })
        : null,
    ]);
    mountReflection(item,r.reflection);
    box.appendChild(item);
  });

  openSheet(el('div', {}, [
    box,
    el('button', { class: 'btn full', style: 'margin-top:15px', text: '完成',
      onclick: () => { document.getElementById('overlay').hidden = true; onClose?.(); } }),
  ]), { title: '重做结果' });
}


/* ---------- 逐题查看 + AI 分析 ---------- */

function showTopicSheet(topicId, title, items, ai, onUsage) {
  const holder = el('div', { class: 'stack', style: 'gap:14px' });

  items.forEach((it, i) => {
    const block = el('div', { style: 'border-top:1px solid #f6ede0;padding-top:12px' }, [
      el('div', { style: 'display:flex;gap:6px;align-items:center;flex-wrap:wrap' }, [
        el('span', { class: 'chip', style: 'font-size:10px;padding:2px 8px', text: `第 ${i + 1} 题` }),
        it.skill ? el('span', { class: 'chip', style: 'font-size:10px;padding:2px 8px', text: it.skill }) : null,
        el('span', { style: 'font-size:10px;color:#a3928a', text: `曾错 ${it.wrong_count} 次` }),
      ]),
      el('div', { style: 'font-size:13px;line-height:1.65;color:#3b2f2a;margin-top:8px;white-space:pre-line', text: questionText(it.stem) }),
      ...imageList(it),
      ...((it.qtype && !['choice', 'multi_choice'].includes(it.qtype))
        ? [el('div', {
            style: 'margin-top:8px;font-size:12px;line-height:1.7;background:#f0f6ff;color:#1e3a5f;border-radius:9px;padding:8px 10px',
            text: it.answer_text ? `✅ 正确答案：${it.answer_text}` : '（这道题还没有填写正确答案）',
          })]
        : [el('div', { style: 'margin-top:8px;display:flex;flex-direction:column;gap:4px' },
          it.options.map((o, oi) => {
            const answers = it.qtype === 'multi_choice' ? (it.answer_indices || []) : [it.answer];
            const picks = it.qtype === 'multi_choice' ? (it.picked_indices || []) : [it.picked];
            return el('div', {
              style: `font-size:12px;padding:5px 9px;border-radius:8px;${
                answers.includes(oi) ? 'background:#f0fdf4;color:#047857;font-weight:700'
                : picks.includes(oi) ? 'background:#fef2f2;color:#b91c1c' : 'color:#6b5b52'}`,
              text: `${LETTERS[oi]}. ${o}${picks.includes(oi) ? ' ← 你的选择' : ''}${answers.includes(oi) ? ' ✓' : ''}`,
            });
          }))]),
      it.qtype === 'multi_choice' ? el('div', { class: 'hint', style: 'margin-top:6px', text: `正确答案：${(it.answer_indices || []).map(i => LETTERS[i]).join('、') || '待补录'}` }) : null,
      el('div', { style: 'font-size:11.5px;color:#6b5b52;line-height:1.7;margin-top:7px', text: it.explain }),
      ...reasonBlock(it),
      el('div', { class: 'ai-slot', style: 'margin-top:8px' }),
    ]);

    if (it.can_edit === false) {
      block.appendChild(el('div', { class: 'hint', text: `${it.owner_name || '其他用户'} 的个人错题 · 共享只读` }));
      if (it.ai) paintAi(block.querySelector('.ai-slot'), it.ai);
      holder.appendChild(block);
      return;
    }
    if (it.source === 'practice') block.appendChild(feedbackButton({ topic_id: it.topic_id, section_id: it.section_id, tier: it.tier, question_id: it.question_id, wrong_question_id: it.id }, it));
    if (it.ai) paintAi(block.querySelector('.ai-slot'), it.ai);
    else {
      block.querySelector('.ai-slot').appendChild(el('button', {
        class: 'btn soft sm', text: ai.tasks?.analyze?.enabled ? '🤖 AI 分析' : 'AI 分析未开放',
        disabled: !ai.tasks?.analyze?.enabled,
        onclick: async (e) => {
          const btn = e.currentTarget;
          btn.disabled = true;
          btn.textContent = '分析中…';
          try {
            const res = await api.analyzeWrong([it.id]);
            onUsage('analyze', res);
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

    /* ---- AI 解题 / 举一反三 ---- */
    const solveSlot = el('div', { style: 'margin-top:8px' });
    const varSlot = el('div', { style: 'margin-top:8px' });
    block.appendChild(solveSlot);
    block.appendChild(varSlot);

    function mountSolve() {
      solveSlot.innerHTML = '';
      if (it.ai_solve) { paintSolve(solveSlot, it.ai_solve, it); return; }
      if (!ai.tasks?.solve?.enabled) { solveSlot.appendChild(el('div', { text: 'AI 解题未开放', class: 'hint' })); return; }
      solveSlot.appendChild(aiTaskButton('🧠 AI 解题（AI 先独立作答）', async () => {
        const res = await api.solveWrong([it.id]);
        onUsage('solve', res);
        const r = res.results[0];
        if (r.error) throw new Error(r.error);
        it.ai_solve = r.value;
        mountSolve();
      }));
    }

    function mountVariants() {
      varSlot.innerHTML = '';
      if (it.variants) { paintVariants(varSlot, it.variants); return; }
      if (!ai.tasks?.variants?.enabled) { varSlot.appendChild(el('div', { text: '举一反三未开放', class: 'hint' })); return; }
      varSlot.appendChild(aiTaskButton('🌱 举一反三 · 生成变式题', async () => {
        const res = await api.variantsWrong(it.id, 2);
        onUsage('variants', res);
        it.variants = res.result;
        mountVariants();
      }));
    }

    mountSolve();
    mountVariants();
    holder.appendChild(block);
  });

  openSheet(el('div', {}, [holder]), { title, sub: '红=你的选择，绿=正确答案' });
}
