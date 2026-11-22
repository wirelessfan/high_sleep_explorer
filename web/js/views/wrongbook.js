/* 错题本：按主题清零 + AI 错误分析 */

import { mountReflection } from '../reflection.js';
import * as api from '../api.js';
import { el, toast, openSheet, SUBJECT_LABEL, SUBJECT_CLASS } from '../ui.js';

import { questionText, prettyMath } from '../question-content.js';
import { feedbackButton } from '../question-feedback.js';
import { wrongImage } from '../wrong-image.js';

const LETTERS = ['A', 'B', 'C', 'D', 'E', 'F'];

/* 导入错题的学科/章节友好标签（SUBJECT_LABEL 未覆盖的补齐） */
const SUBJECT_FALLBACK = { biology: '生物', geography: '地理', cross: '跨学科' };
function subjectLabel(s) {
  return SUBJECT_LABEL[s] || SUBJECT_FALLBACK[s] || s || '未分类';
}
function imageList(it) {
  return (it.images || []).map((p) => wrongImage(p, {
    style: 'max-width:100%;border-radius:10px;border:1px solid #f0e4d5;margin-top:8px;display:block',
  }));
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

  /* ---- 拍照录入入口（演示页）+ 打印试卷 ---- */
  root.appendChild(el('div', { class: 'row', style: 'gap:8px;flex-wrap:wrap' }, [
    el('button', {
      class: 'btn soft', style: 'flex:1;min-width:150px',
      text: '📷 拍照录入',
      onclick: () => { location.href = '/demo/photo.html'; },
    }),
    el('button', {
      class: 'btn', style: 'flex:1;min-width:150px',
      text: '🖨️ 错题回顾试卷',
      onclick: () => navigate('#/wrongbook/paper'),
    }),
  ]));

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
        it.can_edit === false
          ? el('div', { class: 'hint', style: 'margin-top:6px', text: `${it.owner_name || '其他用户'} 的个人错题 · 共享只读` })
          : el('button', {
              class: 'btn ghost sm', style: 'margin-top:7px',
              text: '✍️ 补录文字（AI 提取 / 手填）',
              onclick: () => openPendingEditor(it, view),
            }),
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


/* ---------- 题目文字校对器（错题本弹窗与「待补录」共用） ---------- */

const FIELD_STYLE = 'width:100%;box-sizing:border-box;font:inherit;font-size:12px;line-height:1.6;padding:7px 9px;border:1px solid #dfd2be;border-radius:8px;background:#fff';

/** 去掉识别结果自带的 "A." "B、" 前缀，避免与前端字母重复 */
function stripOptionLead(text) {
  return String(text || '').replace(/^[A-Fa-f][.、)．:：\s]+/, '').trim();
}

/**
 * 编辑一道错题的题干 / 选项 / 答案。
 * - it: 题目对象（保存后就地更新，调用方负责重绘）
 * - onSaved: 保存成功后的回调
 * - visible: 是否默认展开
 * - includeTranscribe: 是否在编辑器里自带「AI 提取」按钮（独立弹窗用）
 */
function buildTextEditor(it, onSaved, { visible = false, includeTranscribe = false } = {}) {
  const node = el('div', {
    style: `display:${visible ? '' : 'none'};margin-top:8px;padding:10px;background:#faf7f2;border:1px solid #efe4d3;border-radius:11px`,
  });
  const stemArea = el('textarea', { rows: '3', style: FIELD_STYLE, placeholder: '题干文字，公式可写成 f(x)=2cos(2x+π/3) 这样' });
  const optArea = el('textarea', { rows: '4', style: `${FIELD_STYLE};margin-top:6px`, placeholder: '选项，一行一个（A/B/C/D 前缀可省略）' });
  const ansInput = el('input', { type: 'text', style: `${FIELD_STYLE};margin-top:6px`, placeholder: '正确答案（选择题填 A/B/C/D，填空解答题直接写答案）' });
  const saveBtn = el('button', { class: 'btn sm', style: 'margin-top:7px', text: '保存文字' });
  const cancelBtn = el('button', {
    class: 'btn ghost sm', style: 'margin-top:7px;margin-left:6px', text: '取消',
    onclick: () => { node.style.display = 'none'; },
  });
  const canTranscribe = !!(it.image_path || (Array.isArray(it.images) && it.images.length));

  function fillFromItem() {
    stemArea.value = it.stem || '';
    optArea.value = (Array.isArray(it.options) ? it.options : []).map(stripOptionLead).join('\n');
    ansInput.value = it.answer_text || '';
  }

  async function transcribe() {
    try {
      const res = await api.transcribeWrong(it.id);
      stemArea.value = res.stem || '';
      optArea.value = (res.options || []).map(stripOptionLead).join('\n');
      ansInput.value = res.answer_text || '';
      toast('已提取文字，核对后点「保存文字」');
      return true;
    } catch (err) {
      toast(err.message || '提取失败');
      return false;
    }
  }

  saveBtn.addEventListener('click', async () => {
    const stem = stemArea.value.trim();
    if (!stem) { toast('题干不能为空'); return; }
    const options = optArea.value.split('\n').map(stripOptionLead).filter(Boolean);
    saveBtn.disabled = true;
    try {
      const res = await api.updateWrongText(it.id, { stem, options, answer_text: ansInput.value.trim() });
      it.stem = res.stem;
      it.options = res.options || [];
      it.answer_text = res.answer_text || '';
      it.review_status = res.review_status || it.review_status;
      const letter = (it.answer_text || '').trim().toUpperCase();
      const idx = LETTERS.indexOf(letter);
      if (['choice', 'multi_choice'].includes(it.qtype) && idx >= 0 && idx < it.options.length) {
        if (it.qtype === 'multi_choice') it.answer_indices = [idx];
        else it.answer = idx;
      }
      node.style.display = 'none';
      toast('错题文字已保存');
      onSaved?.(res);
    } catch (err) { toast(err.message || '保存失败'); }
    saveBtn.disabled = false;
  });

  node.appendChild(el('div', { style: 'font-size:11px;font-weight:800;color:#8a6d3b;margin-bottom:6px', text: '校对文字 · 保存后重做与打印都用这份文字' }));
  node.appendChild(stemArea);
  node.appendChild(optArea);
  node.appendChild(ansInput);
  const actions = el('div', {});
  if (includeTranscribe && canTranscribe) {
    actions.appendChild(el('button', {
      class: 'btn ghost sm', style: 'margin-top:7px;margin-right:6px', text: '✨ AI 提取原图文字',
      onclick: async (e) => {
        const tBtn = e.currentTarget;
        tBtn.disabled = true; tBtn.textContent = '识别中…';
        await transcribe();
        tBtn.disabled = false; tBtn.textContent = '✨ AI 提取原图文字';
      },
    }));
  }
  actions.appendChild(saveBtn);
  actions.appendChild(cancelBtn);
  node.appendChild(actions);

  return {
    node,
    canTranscribe,
    transcribe,
    show() { fillFromItem(); node.style.display = ''; stemArea.focus(); },
  };
}

/** 「待补录」题目：弹出补录弹窗，保存后整页刷新进入正式错题 */
function openPendingEditor(it, view) {
  let handle = null;
  const editor = buildTextEditor(it, () => {
    handle?.close();
    renderWrongbook(view).catch((err) => toast(err.message || '刷新失败'));
  }, { visible: true, includeTranscribe: true });
  const box = el('div', {}, [
    el('div', { style: 'font-size:11.5px;color:#a3928a;margin-bottom:6px', text: '原图（对照着改字，数学公式可用 √2、x²、π/3 这类字符）' }),
    ...imageList(it),
    editor.node,
  ]);
  handle = openSheet(box, {
    title: '补录这道错题的文字',
    sub: '保存后这道题就会进入可打印、可重做的正式错题',
  });
}

/* ---------- 纠错环节：错因 → 重做 → 订正，完成自动补偿抽奖 ---------- */
const CORRECT_REASONS = ['概念没弄清', '审题看漏条件', '公式/定理记混', '计算或单位出错', '思路没找到', '粗心笔误'];

function correctStep(text) {
  return el('div', { style: 'font-size:11.5px;font-weight:800;color:#8a6d3b;margin:2px 0 6px', text });
}

function openCorrectSheet(it, onDone) {
  const box = el('div', { class: 'stack', style: 'gap:12px' });

  box.appendChild(el('div', {
    style: 'font-size:11.5px;line-height:1.7;color:#6b5b52;background:#faf7f2;border:1px solid #efe4d3;border-radius:11px;padding:9px 11px',
    text: '把这道题真正弄懂：选错因 → 不看答案重做 → 写一句订正。完成后自动补偿 10 次普通抽奖 + 1 次实体奖（30 天有效，同一题只发一次）。',
  }));
  if (it.corrected_by_me) {
    box.appendChild(el('div', {
      style: 'font-size:12px;line-height:1.7;color:#047857;background:#ecfdf5;border:1px solid #a7f3d0;border-radius:11px;padding:9px 11px',
      text: '✅ 这道题你已经完成过纠错，奖励已经领过啦。下面可以再复盘一遍，不会重复发奖。',
    }));
  }

  box.appendChild(el('div', {
    style: 'font-size:13px;line-height:1.7;color:#3b2f2a;white-space:pre-line',
    text: questionText(it.stem),
  }));
  for (const node of imageList(it)) box.appendChild(node);

  /* ① 错因 */
  let reason = '';
  const reasonRow = el('div', { class: 'row', style: 'gap:6px;flex-wrap:wrap' });
  CORRECT_REASONS.forEach((r) => {
    const b = el('button', { class: 'btn ghost sm', text: r });
    b.addEventListener('click', () => {
      reason = r;
      for (const x of reasonRow.children) {
        const on = x === b;
        x.style.background = on ? '#eff6ff' : '';
        x.style.borderColor = on ? '#2563eb' : '';
        x.style.color = on ? '#2563eb' : '';
      }
    });
    reasonRow.appendChild(b);
  });
  box.appendChild(correctStep('① 这次错在哪？（点一个）'));
  box.appendChild(reasonRow);

  /* ② 重做 */
  const qtype = it.qtype || 'choice';
  const options = Array.isArray(it.options) ? it.options : [];
  let redoIndex = null;
  const redoIndices = new Set();
  let redoText = '';
  const redoBox = el('div');
  if ((qtype === 'choice' || qtype === 'multi_choice') && options.length) {
    const opts = el('div', { style: 'display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:7px' });
    options.forEach((o, oi) => {
      const b = el('button', {
        class: 'btn ghost sm', style: 'text-align:left;white-space:normal;line-height:1.5',
        text: `${LETTERS[oi]}. ${prettyMath(o)}`,
      });
      b.addEventListener('click', () => {
        if (qtype === 'multi_choice') {
          if (redoIndices.has(oi)) redoIndices.delete(oi); else redoIndices.add(oi);
        } else {
          redoIndex = oi;
        }
        for (const [k, x] of [...opts.children].entries()) {
          const on = qtype === 'multi_choice' ? redoIndices.has(k) : k === redoIndex;
          x.style.background = on ? '#eff6ff' : '';
          x.style.borderColor = on ? '#2563eb' : '';
          x.style.color = on ? '#2563eb' : '';
        }
      });
      opts.appendChild(b);
    });
    redoBox.appendChild(opts);
  } else {
    const inp = el('input', { type: 'text', style: FIELD_STYLE, placeholder: '把答案再写一遍' });
    inp.addEventListener('input', () => { redoText = inp.value; });
    redoBox.appendChild(inp);
    redoBox.appendChild(el('div', {
      class: 'hint', style: 'margin-top:5px',
      text: '填空 / 解答题没有唯一写法，主要看下面的订正笔记。',
    }));
  }
  box.appendChild(correctStep('② 不看答案，重新做一遍'));
  box.appendChild(redoBox);

  /* ③ 订正笔记 */
  const note = el('textarea', {
    rows: '3', style: FIELD_STYLE,
    placeholder: '关键一步是……；下次我要先……（至少 6 个字）',
  });
  box.appendChild(correctStep('③ 写一句订正（关键一步 + 下次怎么避免）'));
  box.appendChild(note);
  if (it.correct_note) {
    box.appendChild(el('div', {
      style: 'font-size:11.5px;line-height:1.7;color:#6b5b52;background:#f0f6ff;border-radius:9px;padding:8px 10px',
      text: `上次写的订正：${it.correct_note}`,
    }));
  }

  const result = el('div');
  const submit = el('button', { class: 'btn', text: '提交纠错 · 领补偿' });
  submit.addEventListener('click', async () => {
    if (!reason) { toast('先选一个错因'); return; }
    if (note.value.trim().length < 6) { toast('订正笔记至少写 6 个字'); return; }
    if (qtype === 'choice' && options.length && redoIndex === null) { toast('先重新选一个答案'); return; }
    submit.disabled = true; submit.textContent = '提交中…';
    try {
      const res = await api.correctWrong(it.id, {
        reason, note: note.value.trim(),
        redo_index: redoIndex, redo_indices: [...redoIndices], redo_text: redoText,
      });
      result.innerHTML = '';
      result.appendChild(el('div', {
        style: 'margin-top:10px;padding:12px;border-radius:13px;background:linear-gradient(135deg,#ecfdf5 0%,#eff6ff 100%);border:1px solid #a7f3d0',
      }, [
        el('div', { style: 'font-size:13px;font-weight:900;color:#047857', text: '🎉 纠错完成' }),
        el('div', { style: 'font-size:12px;line-height:1.8;color:#1e3a5f;margin-top:6px', text: res.message }),
        res.reward.regular
          ? el('div', { style: 'font-size:11.5px;color:#6b5b52;margin-top:4px', text: `有效期至 ${res.reward.end_day}，可在「休闲广场」里使用。同一道题只发一次。` })
          : el('div', { style: 'font-size:11.5px;color:#6b5b52;margin-top:4px', text: '复盘很棒，这道题的奖励之前已经领过了。' }),
      ]));
      submit.style.display = 'none';
      if (res.corrected_at) onDone?.(res);
      // 弹窗里有原图，内容很长；提交后把奖励卡滚到眼前，别让孩子以为没反应
      requestAnimationFrame(() => result.scrollIntoView({ behavior: 'smooth', block: 'center' }));
      toast(res.message);
    } catch (err) {
      toast(err.message || '提交失败');
      submit.disabled = false; submit.textContent = '提交纠错 · 领补偿';
    }
  });
  box.appendChild(submit);
  box.appendChild(result);

  openSheet(box, {
    title: '🔧 纠错 · 把这道题真正弄懂',
    sub: '错因 → 重做 → 订正，完成自动补偿 10 次普通抽奖 + 1 次实体奖',
  });
}

/* ---------- 逐题查看 + AI 分析 ---------- */
function showTopicSheet(topicId, title, items, ai, onUsage) {
  const holder = el('div', { class: 'stack', style: 'gap:14px' });

  items.forEach((it, i) => {
    /* 题干 / 配图 / 选项放进可重绘容器：AI 提取或人工校对后能立刻刷新版面 */
    const qBody = el('div');
    const correctedSlot = el('span');
    function paintBadge() {
      correctedSlot.innerHTML = '';
      if (it.corrected_by_me || it.corrected_at) {
        correctedSlot.appendChild(el('span', {
          class: 'chip',
          style: 'font-size:10px;padding:2px 8px;background:#ecfdf5;border-color:#a7f3d0;color:#047857',
          text: it.corrected_by_me ? '✅ 我已纠错' : '✅ 已纠错',
        }));
      }
    }
    paintBadge();
    const block = el('div', { style: 'border-top:1px solid #f6ede0;padding-top:12px' }, [
      el('div', { style: 'display:flex;gap:6px;align-items:center;flex-wrap:wrap' }, [
        el('span', { class: 'chip', style: 'font-size:10px;padding:2px 8px', text: `第 ${i + 1} 题` }),
        it.skill ? el('span', { class: 'chip', style: 'font-size:10px;padding:2px 8px', text: it.skill }) : null,
        el('span', { style: 'font-size:10px;color:#a3928a', text: `曾错 ${it.wrong_count} 次` }),
        it.review_status === 'needs_transcription'
          ? el('span', { class: 'chip', style: 'font-size:10px;padding:2px 8px;background:#fffbeb;border-color:#fde68a;color:#b45309', text: '待文字化' })
          : null,
        correctedSlot,
      ]),
      qBody,
      el('div', { style: 'font-size:11.5px;color:#6b5b52;line-height:1.7;margin-top:7px', text: it.explain }),
      ...reasonBlock(it),
      el('div', { class: 'ai-slot', style: 'margin-top:8px' }),
    ]);

    function paintQuestion() {
      qBody.innerHTML = '';
      qBody.appendChild(el('div', { style: 'font-size:13px;line-height:1.65;color:#3b2f2a;margin-top:8px;white-space:pre-line', text: questionText(it.stem) }));
      for (const node of imageList(it)) qBody.appendChild(node);

      if (it.review_status === 'needs_transcription') {
        qBody.appendChild(el('div', {
          style: 'margin-top:8px;font-size:11.5px;line-height:1.7;background:#fffbeb;border:1px solid #fde68a;color:#92400e;border-radius:9px;padding:8px 10px',
          text: '这道题目前只有图片：打印试卷会跳过它。点下面的「✨ AI 提取原图文字」生成可编辑的文字版，公式会转成可直接朗读的字符。',
        }));
      }

      if (it.qtype && !['choice', 'multi_choice'].includes(it.qtype)) {
        qBody.appendChild(el('div', {
          style: 'margin-top:8px;font-size:12px;line-height:1.7;background:#f0f6ff;color:#1e3a5f;border-radius:9px;padding:8px 10px',
          text: it.answer_text ? `✅ 正确答案：${it.answer_text}` : '（这道题还没有填写正确答案）',
        }));
        return;
      }

      const options = Array.isArray(it.options) ? it.options : [];
      if (!options.length) {
        qBody.appendChild(el('div', { class: 'hint', style: 'margin-top:6px', text: '还没有选项文字，可用下方「AI 提取原图文字」或手动补录。' }));
        return;
      }
      const answers = it.qtype === 'multi_choice' ? (it.answer_indices || []) : [it.answer];
      const picks = it.qtype === 'multi_choice' ? (it.picked_indices || []) : [it.picked];
      qBody.appendChild(el('div', { style: 'margin-top:8px;display:flex;flex-direction:column;gap:4px' },
        options.map((o, oi) => el('div', {
          style: `font-size:12px;padding:5px 9px;border-radius:8px;${
            answers.includes(oi) ? 'background:#f0fdf4;color:#047857;font-weight:700'
            : picks.includes(oi) ? 'background:#fef2f2;color:#b91c1c' : 'color:#6b5b52'}`,
          text: `${LETTERS[oi]}. ${prettyMath(o)}${picks.includes(oi) ? ' ← 你的选择' : ''}${answers.includes(oi) ? ' ✓' : ''}`,
        }))));
      if (it.qtype === 'multi_choice') {
        qBody.appendChild(el('div', { class: 'hint', style: 'margin-top:6px', text: `正确答案：${(it.answer_indices || []).map((n) => LETTERS[n]).join('、') || '待补录'}` }));
      }
    }
    paintQuestion();

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

    /* ---- 题目文字：AI 提取 / 人工校对 / 复制 ---- */
    const editor = buildTextEditor(it, () => paintQuestion());
    const textTools = el('div', { class: 'row', style: 'gap:7px;margin-top:8px;flex-wrap:wrap' });
    if (editor.canTranscribe) {
      const ocrBtn = el('button', {
        class: 'btn ghost sm', text: '✨ AI 提取原图文字',
        onclick: async () => {
          ocrBtn.disabled = true; ocrBtn.textContent = '识别中…';
          const ok = await editor.transcribe();
          ocrBtn.disabled = false; ocrBtn.textContent = '✨ AI 提取原图文字';
          if (ok) editor.show();
        },
      });
      textTools.appendChild(ocrBtn);
    }
    textTools.appendChild(el('button', { class: 'btn ghost sm', text: '✏️ 编辑文字', onclick: () => editor.show() }));
    const correctBtn = el('button', {
      class: 'btn sm', text: it.corrected_by_me ? '✅ 已纠错 · 查看' : '🔧 纠错 · 领补偿',
    });
    correctBtn.addEventListener('click', () => openCorrectSheet(it, (res) => {
      it.corrected_by_me = true;
      it.corrected_at = res.corrected_at;
      it.correct_note = res.correct_note;
      paintBadge();
      correctBtn.textContent = '✅ 已纠错 · 查看';
    }));
    textTools.appendChild(correctBtn);
    textTools.appendChild(el('button', {
      class: 'btn ghost sm', text: '📋 复制题干',
      onclick: async () => {
        try { await navigator.clipboard.writeText(it.stem || ''); toast('已复制题干文字'); }
        catch { toast('复制失败，请手动选中复制'); }
      },
    }));
    block.appendChild(textTools);
    block.appendChild(editor.node);

    mountSolve();
    mountVariants();
    holder.appendChild(block);
  });

  openSheet(el('div', {}, [holder]), { title, sub: '红=你的选择，绿=正确答案' });
}
