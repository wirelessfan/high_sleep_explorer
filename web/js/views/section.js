/* 版块学习：六种类型的渲染与提交 */

import * as api from '../api.js';
import { el, toast, openSheet, biliEmbed, biliLink, previewImage } from '../ui.js';
import { navigate } from '../router.js';
import { questionContent } from '../question-content.js';
import { feedbackButton } from '../question-feedback.js';
import { bossBanner, bindBossProgress } from '../boss.js';

const LETTERS = ['A', 'B', 'C', 'D', 'E', 'F'];

let ACTIVE_TIER = 'basic';

export async function renderSection(view, { id, sid, tier }) {
  ACTIVE_TIER = tier || 'basic';
  const data = await api.getSection(id, sid, ACTIVE_TIER);

  // 该难度尚未建设：给一个明确的空状态，而不是白屏或 404
  if (!data.available) {
    const wrap = el('div', { class: 'stack' });
    wrap.appendChild(el('div', { class: 'topbar' }, [
      el('button', { class: 'back', text: '‹', onclick: () => navigate(`#/topic/${id}`) }),
      el('div', { style: 'flex:1' }, [
        el('h1', { text: '该难度还在建设中' }),
        el('div', { class: 'sub', text: `${data.tier?.name || ''} · ${data.tier?.score || ''}` }),
      ]),
    ]));
    wrap.appendChild(el('section', { class: 'panel' }, [
      el('div', { style: 'font-size:14px;font-weight:800', text: '这个主题的高阶档位还没开放' }),
      el('div', { style: 'font-size:12.5px;color:#8a7a70;margin-top:6px;line-height:1.7',
        text: '基础档覆盖课本常规题（70–80 分）。进阶（80–90）与高级（90–95）按主题逐个补齐，可以先走通当前主题的基础档，或到已开放高阶档的主题继续冲刺。' }),
      el('button', { class: 'btn sm', style: 'margin-top:14px', text: '回到基础档',
        onclick: () => navigate(`#/topic/${id}/${sid}/basic`) }),
    ]));
    view.innerHTML = '';
    view.appendChild(wrap);
    return;
  }

  const sec = data.section;

  const root = el('div', { class: 'stack' });

  root.appendChild(el('div', { class: 'topbar' }, [
    el('button', { class: 'back', text: '‹', onclick: () => navigate(`#/topic/${id}`) }),
    el('div', { style: 'flex:1' }, [
      el('h1', { text: sec.name || sec.id }),
      el('div', { class: 'sub', text: sec.intro || '' }),
    ]),
  ]));

  if (data.study) root.appendChild(el('section', { class: 'panel', text: data.study.active
    ? `必修 1 备考奖励：本单元首通、复习积分 ×2，Boss 首通卡包 ×2（至 ${data.study.ends_on}）。复习仍按原基础额度计入每日上限。`
    : `${data.study.label}。本单元当前按常规奖励发放。` }));

  // 难度开关：基础 / 进阶 / 高级
  root.appendChild(tierSwitcher(data.tiers || [], ACTIVE_TIER, id, sid));

  // 守关者横幅：每个版块一只小 boss，boss 版块是科学家大 boss
  const banner = bossBanner(data.boss, { status: data.status });
  if (banner) root.appendChild(banner);

  const body = el('div', { class: 'stack' });
  root.appendChild(body);

  if (sec.type === 'quiz') await renderQuiz(body, id, sid, sec);
  else if (sec.type === 'levels') await renderLevels(body, id, sid, sec);
  else if (sec.type === 'reading') await renderReading(body, id, sid, sec);
  else if (sec.type === 'myths') await renderMyths(body, id, sid, sec);
  else if (sec.type === 'steps') await renderSteps(body, id, sid, sec);
  else if (sec.type === 'boss') await renderBoss(body, id, sid, sec);
  else body.appendChild(el('div', { class: 'panel', text: '未知版块类型' }));

  view.innerHTML = '';
  view.appendChild(root);

  // 绑定状元草图/笔记图片点击放大预览
  root.addEventListener('click', (e) => {
    const target = e.target.closest('.scholar-sketch, img.zoomable');
    if (target && target.src) {
      previewImage(target.src, target.alt || '状元手写笔记草图');
    }
  });

  // 挂载完成后再绑定，避免渲染期的 DOM 变动干扰观察器
  if (banner) bindBossProgress(root, banner, data.boss);
}

/* ---------- 难度档位切换 ---------- */

function tierSwitcher(tiers, active, topicId, sid) {
  if (!tiers.length) return el('div');
  const wrap = el('div', { class: 'tier-switch' });
  tiers.forEach((t) => {
    const locked = !t.available;
    wrap.appendChild(el('button', {
      class: `tier-pill${t.id === active ? ' on' : ''}${locked ? ' locked' : ''}`,
      type: 'button',
      title: locked ? '该难度正在建设中' : (t.desc || ''),
      onclick: () => {
        if (locked) return;
        if (t.id === active) return;
        navigate(`#/topic/${topicId}/${sid}/${t.id}`);
      },
    }, [
      el('span', { class: 'tp-name', text: t.name }),
      el('span', { class: 'tp-score', text: locked ? '建设中' : t.score }),
      t.status === 'done' ? el('span', { class: 'tp-done', text: '✓' }) : null,
    ]));
  });
  return wrap;
}

/* ---------- 通用：选项组 ---------- */

function optionsBlock(questions, getSelection, onChange, { disabled = false, showResult = null, feedback = null } = {}) {
  const wrap = el('div', { class: 'stack', style: 'gap:18px' });

  questions.forEach((q, qi) => {
    const block = el('div', { class: 'q-block' });
    block.appendChild(el('div', { class: 'q-stem' }, [
      el('span', { style: 'color:#a3928a;font-weight:800;margin-right:6px', text: `${qi + 1}.` }),
      questionContent(q.stem),
    ]));

    const opts = el('div', { class: 'q-options' });
    q.options.forEach((opt, oi) => {
      const btn = el('button', {
        class: 'opt',
        type: 'button',
        onclick: () => {
          if (disabled) return;
          if (showResult && showResult.locked) return;
          getSelection()[q.id] = oi;
          opts.querySelectorAll('.opt').forEach((b, bi) => {
            b.classList.toggle('sel', bi === oi);
          });
          onChange?.();
        },
      }, [
        el('span', { class: 'key', text: LETTERS[oi] }),
        el('span', { class: 'txt', text: opt }),
      ]);
      btn.dataset.qid = q.id;
      btn.dataset.oi = String(oi);
      opts.appendChild(btn);
    });
    block.appendChild(opts);
    if (feedback) block.appendChild(feedbackButton({ ...feedback, question_id: q.id }, q));
    wrap.appendChild(block);
  });

  return wrap;
}

function applyResults(wrapEl, details) {
  const map = new Map(details.map((d) => [String(d.id), d]));
  wrapEl.querySelectorAll('.q-block').forEach((block, qi) => {
    const opts = block.querySelector('.q-options');
    const first = opts.querySelector('.opt');
    if (!first) return;
    const qid = first.dataset.qid;
    const d = map.get(qid);
    if (!d) return;

    opts.querySelectorAll('.opt').forEach((btn) => {
      const oi = Number(btn.dataset.oi);
      btn.disabled = true;
      btn.classList.remove('sel');
      if (oi === d.answer) btn.classList.add('right');
      else if (oi === d.picked) btn.classList.add('wrong');
    });

    if (d.explain) {
      const ok = d.correct;
      block.appendChild(el('div', { class: `explain ${ok ? 'ok' : 'bad'}` }, [
        el('span', { class: 'tag', text: ok ? '答对了' : `正确答案 ${LETTERS[d.answer]}` }),
        el('div', { text: d.explain }),
      ]));
    }
  });
}

function resultHero({ score, correct, total, message, rewards = [], reading = false }) {
  return el('section', { class: 'panel result-hero' }, [
    el('div', { class: 'num' }, [
      reading ? '✓' : String(score),
      reading ? null : el('small', { text: '分' }),
    ]),
    el('div', { class: 'lbl', text: reading ? '阅读已完成' : `答对 ${correct} / ${total} 题` }),
    el('div', { class: 'msg', text: message }),
    rewards.length ? el('div', { class: 'reward-row' }, rewards.map((r) =>
      el('span', { class: 'reward-pill', text: r })
    )) : null,
  ]);
}

function submitBar(label, onClick, enabled = true) {
  const btn = el('button', {
    class: 'btn full', text: label, disabled: !enabled,
    onclick: onClick,
  });
  return { wrap: el('div', { style: 'margin-top:18px' }, [btn]), btn };
}

function afterSubmit(root, res, topicId, sectionId) {
  if (res.weak_skills?.length) {
    root.appendChild(el('section', { class: 'panel', style: 'padding:14px' }, [
      el('div', { style: 'font-size:12.5px;font-weight:800;margin-bottom:6px;color:#92400e', text: '⚠ 需要加强' }),
      el('div', { style: 'font-size:12.5px;color:#6b5b52;line-height:1.7', text: res.weak_skills.join(' · ') }),
    ]));
  }

  const nav = el('div', { class: 'row', style: 'margin-top:16px;gap:9px' }, [
    el('button', { class: 'btn ghost', style: 'flex:1', text: '返回主题', onclick: () => navigate(`#/topic/${topicId}`) }),
  ]);
  if (res.next_section) {
    nav.appendChild(el('button', {
      class: 'btn', style: 'flex:1', text: '下一版块 ›',
      onclick: () => {
        const { render } = window.__router || {};
        location.hash = `#/topic/${topicId}/${res.next_section}/${res.next_tier || ACTIVE_TIER}`;
      },
    }));
  }
  root.appendChild(nav);
}

function rewardPills(res) {
  const out = [];
  if (res.study_reward?.active && res.points > 0) out.push('已含备考 ×2');
  if (res.points > 0) out.push(`+${res.points} 积分`);
  if (res.topic_reward?.tickets) out.push(`+${res.topic_reward.tickets} 卡包`);
  if (res.total_points !== undefined) out.push(`总积分 ${res.total_points}`);
  return out;
}

/* ---------- 快速测试 / Boss：单选题 ---------- */

async function renderQuiz(body, topicId, sectionId, sec) {
  const answers = {};
  const questions = sec.questions;
  let submitted = false;

  const optWrap = optionsBlock(questions, () => answers, () => {
    const filled = questions.every((q) => answers[q.id] !== undefined);
    submit.btn.disabled = !filled;
    submit.wrap.querySelector('.btn').textContent = filled ? '提交答案' : `还有 ${questions.filter(q=>answers[q.id]===undefined).length} 题未答`;
  }, { feedback: { topic_id: topicId, section_id: sectionId, tier: ACTIVE_TIER } });

  body.appendChild(el('section', { class: 'panel' }, [optWrap]));

  const submit = submitBar('提交答案', async () => {
    submit.btn.disabled = true;
    submit.btn.textContent = '判分中…';
    try {
      const res = await api.submitSection(topicId, sectionId, answers, ACTIVE_TIER);
      submitted = true;
      applyResults(optWrap, res.details);

      const hero = resultHero({
        score: res.score, correct: res.correct, total: res.total,
        message: res.passed ? '通过了！' : '再复习一下会更稳',
        rewards: rewardPills(res),
      });
      body.insertBefore(hero, body.firstChild);
      submit.wrap.remove();
      afterSubmit(body, res, topicId, sectionId);
      hero.scrollIntoView({ behavior: 'smooth', block: 'start' });
    } catch (err) {
      toast(err.message || '提交失败');
      submit.btn.disabled = false;
      submit.btn.textContent = '提交答案';
    }
  }, false);

  body.appendChild(submit.wrap);
}

/* ---------- 基础闯关：分关 ---------- */

async function renderLevels(body, topicId, sectionId, sec) {
  const answers = {};
  const levels = sec.levels;
  let active = 0;

  const header = el('section', { class: 'panel', style: 'padding:13px' }, [
    el('div', { class: 'row-between' }, [
      el('div', { style: 'font-size:13px;font-weight:800', text: '三个关卡' }),
      el('div', { style: 'font-size:11.5px;color:#a3928a', text: '每关 80% 解锁下一关' }),
    ]),
    el('div', { class: 'row', style: 'gap:6px;margin-top:10px' }, levels.map((lv, i) =>
      el('div', {
        class: 'chip', 'data-lv': String(i),
        style: 'flex:1;justify-content:center;font-size:11px',
        text: lv.name.replace(/^第 \d 关 · /, ''),
      })
    )),
  ]);
  body.appendChild(header);

  const holder = el('div');
  body.appendChild(holder);

  function renderLevel(idx) {
    active = idx;
    const lv = levels[idx];
    holder.innerHTML = '';

    header.querySelectorAll('.chip').forEach((c, i) => {
      c.style.background = i === idx ? '#3b2f2a' : '';
      c.style.color = i === idx ? '#fff' : '';
      c.style.borderColor = i === idx ? '#3b2f2a' : '';
    });

    const optWrap = optionsBlock(lv.questions, () => answers, () => {
      const filled = lv.questions.every((q) => answers[q.id] !== undefined);
      btn.disabled = !filled;
      btn.textContent = filled ? '提交本关' : `还有 ${lv.questions.filter(q=>answers[q.id]===undefined).length} 题`;
    }, { feedback: { topic_id: topicId, section_id: sectionId, tier: ACTIVE_TIER } });

    holder.appendChild(el('section', { class: 'panel' }, [
      el('div', { style: 'font-size:13px;font-weight:800;margin-bottom:12px', text: lv.name }),
      optWrap,
    ]));

    const btn = el('button', {
      class: 'btn full', style: 'margin-top:16px', text: '请先作答', disabled: true,
      onclick: async () => {
        btn.disabled = true;
        btn.textContent = '判分中…';
        try {
          const res = await api.submitSection(topicId, sectionId, answers, ACTIVE_TIER);
          const lvRes = res.levels.find((l) => l.id === lv.id);
          applyResults(optWrap, lvRes.details);

          holder.appendChild(el('div', { style: 'margin-top:14px' }, [
            el('div', {
              class: `explain ${lvRes.passed ? 'ok' : 'bad'}`,
              style: 'margin-top:0',
            }, [
              el('span', { class: 'tag', text: lvRes.passed ? '本关通过' : '未达标' }),
              el('div', { text: `本关得分 ${lvRes.score} 分${lvRes.passed ? '，已解锁下一关' : '，需要 80 分才能过关，可以重做'}` }),
            ]),
          ]));

          if (lvRes.passed) {
            if (idx + 1 < levels.length) {
              holder.appendChild(el('button', {
                class: 'btn full', style: 'margin-top:12px', text: `进入${levels[idx + 1].name}`,
                onclick: () => { renderLevel(idx + 1); window.scrollTo({ top: 0, behavior: 'smooth' }); },
              }));
            } else {
              const hero = resultHero({
                score: res.score, correct: res.correct, total: res.total,
                message: '三关全通！',
                rewards: rewardPills(res),
              });
              body.insertBefore(hero, body.firstChild);
              hero.scrollIntoView({ behavior: 'smooth', block: 'start' });
              afterSubmit(body, res, topicId, sectionId);
            }
          } else {
            holder.appendChild(el('button', {
              class: 'btn ghost full', style: 'margin-top:12px', text: '重做本关',
              onclick: () => {
                lv.questions.forEach((q) => delete answers[q.id]);
                renderLevel(idx);
              },
            }));
          }
          btn.remove();
        } catch (err) {
          toast(err.message || '提交失败');
          btn.disabled = false;
          btn.textContent = '提交本关';
        }
      },
    });
    holder.appendChild(btn);
  }

  renderLevel(0);
}

/* ---------- 知识点总结：阅读 ---------- */

async function renderReading(body, topicId, sectionId, sec) {
  const blocks = el('section', { class: 'panel' });
  (sec.blocks || []).forEach((b) => {
    const children = [
      el('h4', { text: b.h }),
      el('p', { html: b.p }),
    ];
    if (b.image || b.diagram) {
      const src = b.image || b.diagram;
      const fig = el('div', { class: 'read-figure' }, [
        el('img', {
          src,
          class: 'scholar-sketch',
          alt: b.caption || b.h || '知识点图解',
          loading: 'lazy',
        }),
        el('div', {
          class: 'sketch-caption',
          html: `🔍 ${b.caption || '点击图片可放大查看高清图解'}`,
        }),
      ]);
      children.push(fig);
    }
    if (b.formula) children.push(el('div', { class: 'formula', text: b.formula }));
    blocks.appendChild(el('div', { class: 'read-block' }, children));
  });
  body.appendChild(blocks);

  if (sec.videos?.length) {
    body.appendChild(el('div', { class: 'section-head' }, [
      el('h3', { text: '配套视频' }),
      el('span', { class: 'hint', text: '点击播放' }),
    ]));
    sec.videos.forEach((v) => body.appendChild(videoCard(v)));
  }

  const btn = el('button', {
    class: 'btn full', style: 'margin-top:18px', text: '我记住了 ✓',
    onclick: async () => {
      btn.disabled = true;
      btn.textContent = '记录中…';
      try {
        const res = await api.markRead(topicId, sectionId, ACTIVE_TIER);
        toast(res.points ? `+${res.points} 积分` : '已记录');
        const hero = resultHero({
          reading: true,
          message: res.is_review ? '复习完成' : '读完啦',
          rewards: rewardPills({ ...res, total_points: res.total_points }),
        });
        body.insertBefore(hero, body.firstChild);
        btn.remove();
        afterSubmit(body, res, topicId, sectionId);
        hero.scrollIntoView({ behavior: 'smooth', block: 'start' });
      } catch (err) {
        toast(err.message || '操作失败');
        btn.disabled = false;
        btn.textContent = '我记住了 ✓';
      }
    },
  });
  body.appendChild(btn);
}

function videoCard(v) {
  const card = el('div', { class: 'video-card' });
  const frame = el('div', { class: 'video-frame' });
  const cover = el('div', { class: 'cover' }, [
    el('div', { class: 'play', text: '▶' }),
    el('div', { class: 't', text: '点击加载 B 站播放器' }),
  ]);
  cover.addEventListener('click', () => {
    const iframe = el('iframe', {
      src: biliEmbed(v.bvid),
      allow: 'accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture',
      allowfullscreen: 'true',
      referrerpolicy: 'no-referrer',
    });
    frame.innerHTML = '';
    frame.appendChild(iframe);
  });
  frame.appendChild(cover);
  card.appendChild(frame);
  card.appendChild(el('div', { class: 'video-info' }, [
    el('div', { class: 't', text: v.title }),
    el('div', { class: 'm', text: `${v.up} · ${v.duration}` }),
    v.why ? el('div', { class: 'why', text: v.why }) : null,
    el('a', { href: biliLink(v.bvid), target: '_blank', rel: 'noopener noreferrer', text: '在 B 站打开 ↗' }),
  ]));
  return card;
}

/* ---------- 难点剖析 ---------- */

async function renderMyths(body, topicId, sectionId, sec) {
  const answers = {};
  const myths = sec.myths;

  myths.forEach((m, mi) => {
    const block = el('section', { class: 'panel stack', style: 'gap:12px' });

    block.appendChild(el('div', { style: 'font-size:14.5px;font-weight:800;color:#3b2f2a', text: m.title }));

    block.appendChild(el('div', {
      style: 'background:#fef2f2;border:1px solid #fecaca;border-radius:11px;padding:12px',
    }, [
      el('div', { style: 'font-size:10.5px;font-weight:800;color:#991b1b;letter-spacing:.05em;margin-bottom:5px', text: '常见错误想法' }),
      el('div', { style: 'font-size:13px;color:#7f1d1d;line-height:1.7', text: m.wrong }),
    ]));

    block.appendChild(el('div', {
      style: 'background:#fdf8f0;border:1px solid #efe2ce;border-radius:11px;padding:12px',
    }, [
      el('div', { style: 'font-size:10.5px;font-weight:800;color:#6b5b52;letter-spacing:.05em;margin-bottom:5px', text: '为什么错' }),
      el('div', { style: 'font-size:13px;color:#5c4b42;line-height:1.7', text: m.why }),
    ]));

    block.appendChild(el('div', {
      style: 'background:#f0fdf4;border:1px solid #bbf7d0;border-radius:11px;padding:12px',
    }, [
      el('div', { style: 'font-size:10.5px;font-weight:800;color:#166534;letter-spacing:.05em;margin-bottom:5px', text: '正确理解' }),
      el('div', { style: 'font-size:13px;color:#14532d;line-height:1.7;font-weight:600', text: m.right }),
    ]));

    const qid = `m${mi}`;
    block.appendChild(el('div', { class: 'q-block', style: 'margin-top:2px' }, [
      el('div', { class: 'q-stem', style: 'font-size:14px', text: m.check.stem }),
    ]));

    const opts = el('div', { class: 'q-options' });
    m.check.options.forEach((opt, oi) => {
      opts.appendChild(el('button', {
        class: 'opt', type: 'button',
        onclick: () => {
          answers[qid] = oi;
          opts.querySelectorAll('.opt').forEach((b, bi) => b.classList.toggle('sel', bi === oi));
          submit.btn.disabled = !myths.every((_, i) => answers[`m${i}`] !== undefined);
        },
      }, [
        el('span', { class: 'key', text: LETTERS[oi] }),
        el('span', { class: 'txt', text: opt }),
      ]));
    });
    block.appendChild(opts);

    block.appendChild(feedbackButton({ topic_id: topicId, section_id: sectionId, tier: ACTIVE_TIER, question_id: qid }, m.check));
    block.dataset.mythIndex = String(mi);
    body.appendChild(block);
  });

  const submit = submitBar('提交小测', async () => {
    submit.btn.disabled = true;
    submit.btn.textContent = '判分中…';
    try {
      const res = await api.submitSection(topicId, sectionId, answers, ACTIVE_TIER);
      // 逐块回填
      body.querySelectorAll('[data-myth-index]').forEach((block, mi) => {
        const d = res.details[mi];
        const opts = block.querySelector('.q-options');
        if (!opts || !d) return;
        opts.querySelectorAll('.opt').forEach((btn, oi) => {
          btn.disabled = true;
          btn.classList.remove('sel');
          if (oi === d.answer) btn.classList.add('right');
          else if (oi === d.picked) btn.classList.add('wrong');
        });
        block.appendChild(el('div', { class: `explain ${d.correct ? 'ok' : 'bad'}` }, [
          el('span', { class: 'tag', text: d.correct ? '答对了' : `正确答案 ${LETTERS[d.answer]}` }),
          el('div', { text: d.explain }),
        ]));
      });

      const hero = resultHero({
        score: res.score, correct: res.correct, total: res.total,
        message: res.passed ? '误区都识别出来了' : '再回看一遍「为什么错」',
        rewards: rewardPills(res),
      });
      body.insertBefore(hero, body.firstChild);
      submit.wrap.remove();
      afterSubmit(body, res, topicId, sectionId);
      hero.scrollIntoView({ behavior: 'smooth', block: 'start' });
    } catch (err) {
      toast(err.message || '提交失败');
      submit.btn.disabled = false;
      submit.btn.textContent = '提交小测';
    }
  }, false);

  body.appendChild(submit.wrap);
}

/* ---------- 实战巩固：分步大题 ---------- */

async function renderSteps(body, topicId, sectionId, sec) {
  const answers = {};
  const problems = sec.problems;

  problems.forEach((p, pi) => {
    body.appendChild(el('section', { class: 'panel' }, [
      el('div', { style: 'font-size:11px;font-weight:800;color:#a3928a;letter-spacing:.06em;margin-bottom:7px', text: `第 ${pi + 1} 题` }),
      el('div', { style: 'font-size:14px;line-height:1.75;color:#4a3b33', text: p.stem }),
    ]));

    p.steps.forEach((step, si) => {
      const qid = `p${pi}s${si}`;
      const block = el('section', { class: 'panel', style: 'padding:14px' }, [
        el('div', { style: 'font-size:13.5px;font-weight:700;margin-bottom:10px', text: step.ask }),
      ]);
      const opts = el('div', { class: 'q-options' });
      step.options.forEach((opt, oi) => {
        opts.appendChild(el('button', {
          class: 'opt', type: 'button',
          onclick: () => {
            answers[qid] = oi;
            opts.querySelectorAll('.opt').forEach((b, bi) => b.classList.toggle('sel', bi === oi));
            check();
          },
        }, [
          el('span', { class: 'key', text: LETTERS[oi] }),
          el('span', { class: 'txt', text: opt }),
        ]));
      });
      block.appendChild(opts);
      block.appendChild(feedbackButton({ topic_id: topicId, section_id: sectionId, tier: ACTIVE_TIER, question_id: qid }, { stem: `${p.stem}\n${step.ask}`, options: step.options }));
      block.dataset.stepKey = qid;
      body.appendChild(block);
    });

    if (p.note) {
      body.appendChild(el('div', {
        style: 'font-size:12px;color:#8a7a70;line-height:1.7;padding:0 4px 4px',
        text: `💡 ${p.note}`,
      }));
    }
  });

  const totalSteps = problems.reduce((a, p) => a + p.steps.length, 0);
  const submit = submitBar(`提交（共 ${totalSteps} 步）`, async () => {
    submit.btn.disabled = true;
    submit.btn.textContent = '判分中…';
    try {
      const res = await api.submitSection(topicId, sectionId, answers, ACTIVE_TIER);
      let di = 0;
      problems.forEach((p) => {
        p.steps.forEach(() => {
          const d = res.details[di++];
          const block = body.querySelector(`[data-step-key="${d.id}"]`);
          if (!block) return;
          const opts = block.querySelector('.q-options');
          opts.querySelectorAll('.opt').forEach((btn, oi) => {
            btn.disabled = true;
            btn.classList.remove('sel');
            if (oi === d.answer) btn.classList.add('right');
            else if (oi === d.picked) btn.classList.add('wrong');
          });
          block.appendChild(el('div', { class: `explain ${d.correct ? 'ok' : 'bad'}` }, [
            el('span', { class: 'tag', text: d.correct ? '这一步对了' : `正确应为 ${LETTERS[d.answer]}` }),
            el('div', { text: d.explain }),
          ]));
        });
      });

      const hero = resultHero({
        score: res.score, correct: res.correct, total: res.total,
        message: '完整走完了一遍解题链',
        rewards: rewardPills(res),
      });
      body.insertBefore(hero, body.firstChild);
      submit.wrap.remove();
      afterSubmit(body, res, topicId, sectionId);
      hero.scrollIntoView({ behavior: 'smooth', block: 'start' });
    } catch (err) {
      toast(err.message || '提交失败');
      submit.btn.disabled = false;
      submit.btn.textContent = '提交';
    }
  }, false);

  function check() {
    const filled = problems.reduce((a, p) => a + p.steps.filter((_, si) => {
      const qid = `p${problems.indexOf(p)}s${si}`;
      return answers[qid] !== undefined;
    }).length, 0);
    submit.btn.disabled = filled < totalSteps;
    submit.btn.textContent = filled < totalSteps ? `已完成 ${filled}/${totalSteps} 步` : '提交答案';
  }

  body.appendChild(submit.wrap);
}

/* ---------- Boss ---------- */

async function renderBoss(body, topicId, sectionId, sec) {
  const answers = {};
  const questions = sec.questions;

  body.appendChild(el('section', { class: 'panel', style: 'background:linear-gradient(150deg,#4a3b33,#3b2f2a);border-color:#4a3b33' }, [
    el('div', { style: 'font-size:11px;letter-spacing:.18em;color:#a3928a;font-weight:700;text-transform:uppercase', text: 'Boss' }),
    el('div', { style: 'font-size:17px;font-weight:800;color:#fff;margin-top:6px', text: '最后一关' }),
    el('div', { style: 'font-size:12.5px;color:#d9c8b4;margin-top:6px', text: '答对可得 50 积分 + 1 张卡包' }),
  ]));

  const optWrap = optionsBlock(questions, () => answers, () => {
    const filled = questions.every((q) => answers[q.id] !== undefined);
    submit.btn.disabled = !filled;
    submit.btn.textContent = filled ? '提交答案' : '请先作答';
  }, { feedback: { topic_id: topicId, section_id: sectionId, tier: ACTIVE_TIER } });

  body.appendChild(el('section', { class: 'panel' }, [optWrap]));

  const submit = submitBar('提交答案', async () => {
    submit.btn.disabled = true;
    submit.btn.textContent = '判分中…';
    try {
      const res = await api.submitSection(topicId, sectionId, answers, ACTIVE_TIER);
      applyResults(optWrap, res.details);

      const hero = resultHero({
        score: res.score, correct: res.correct, total: res.total,
        message: res.passed ? '🎉 Boss 击败！' : '差一点，再来一次',
        rewards: rewardPills(res),
      });
      body.insertBefore(hero, body.firstChild);
      submit.wrap.remove();

      if (sec.egg) {
        body.appendChild(el('section', { class: 'panel', style: 'background:#fffbeb;border-color:#fde68a' }, [
          el('div', { style: 'font-size:14.5px;font-weight:800;color:#92400e', text: `🥚 ${sec.egg.title}` }),
          el('div', { style: 'font-size:13px;color:#78350f;line-height:1.75;margin-top:8px', text: sec.egg.text }),
          sec.egg.video ? videoCard(sec.egg.video) : null,
        ]));
      }

      afterSubmit(body, res, topicId, sectionId);
      hero.scrollIntoView({ behavior: 'smooth', block: 'start' });
    } catch (err) {
      toast(err.message || '提交失败');
      submit.btn.disabled = false;
      submit.btn.textContent = '提交答案';
    }
  }, false);

  body.appendChild(submit.wrap);
}
