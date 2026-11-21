/* Own reports and admin review share the same immutable question snapshot. */
import * as api from '../api.js';
import { el, toast } from '../ui.js';
import { questionContent } from '../question-content.js';

const STATUS = { pending: '待审核', approved: '已通过', rejected: '未通过' };
const TIER = { basic: '基础', advanced: '进阶', expert: '高级' };

export async function renderFeedback(view, { review = false } = {}) {
  const me = await api.fetchMe();
  if (review && !me.is_admin) { toast('需要管理员身份'); location.hash = '#/feedback'; return; }
  const data = await (review ? api.adminQuestionFeedback() : api.getQuestionFeedback());
  const root = el('div', { class: 'stack' });
  root.appendChild(el('div', { class: 'topbar' }, [
    el('button', { class: 'back', text: '‹', onclick: () => { location.hash = '#/me'; } }),
    el('div', {}, [el('h1', { text: review ? '题目反馈审核' : '我的题目反馈' }),
      el('div', { class: 'sub', text: '发现题目问题，审核通过奖励 50 积分' })]),
  ]));
  if (me.is_admin) root.appendChild(el('a', { class: 'btn ghost', href: review ? '#/feedback' : '#/feedback/review', text: review ? '查看我的反馈' : '进入反馈审核' }));
  root.appendChild(el('div', { class: 'hint', text: review
    ? '核对下方原题快照后审核；通过后自动向提交者发放 50 积分。'
    : '做题时点击「题目有问题？反馈」。提交不立即发奖，通过后到账；同一题目版本只奖励一次。' }));
  if (!data.items.length) root.appendChild(el('section', { class: 'panel', text: review ? '暂时没有题目反馈' : '还没有反馈记录，做题时可以直接反馈具体题目。' }));
  for (const item of data.items) {
    const card = el('section', { class: 'panel stack', style: 'gap:10px' });
    card.appendChild(el('div', { class: 'row-between' }, [
      el('strong', { text: `${STATUS[item.status]}${item.reward_points ? ` · +${item.reward_points} 积分已到账` : ''}` }),
      el('span', { class: 'hint', text: (item.created_at || '').slice(0, 16).replace('T', ' ') }),
    ]));
    if (review) card.appendChild(el('div', { class: 'hint', text: `提交者：${item.nickname || item.username || '同学'} ${item.username ? '@'+item.username : ''}` }));
    card.appendChild(el('div', { class: 'hint', text: `${item.topic_id} · ${item.section_id} · ${TIER[item.tier]} · ${item.question_id}` }));
    card.appendChild(questionContent(item.question.stem));
    item.question.options.forEach((text, i) => card.appendChild(el('div', { style: 'font-size:12px;line-height:1.6', text: `${String.fromCharCode(65+i)}. ${text}` })));
    if (review) card.appendChild(el('div', { style: 'font-size:12px;background:#f0fdf4;padding:9px;border-radius:9px', text: `标准答案 ${String.fromCharCode(65+item.question.answer)} · ${item.question.explain || ''}` }));
    card.appendChild(el('div', { style: 'white-space:pre-wrap;font-size:13px;line-height:1.7', text: `${data.categories[item.category] || item.category}：${item.detail}` }));
    if (review) {
      const result = el('div', { class: 'hint', style: 'white-space:pre-wrap;line-height:1.7' });
      card.appendChild(el('button', { class: 'btn soft sm', text: 'AI 审校此题', onclick: async (event) => {
        const button = event.currentTarget;
        button.disabled = true; button.textContent = '审校中…'; result.textContent = '';
        try {
          const checked = await api.adminAiReview({
            stem: item.question.stem,
            options: item.question.options,
            answer: `${String.fromCharCode(65 + item.question.answer)}. ${item.question.options[item.question.answer]}`,
            explain: item.question.explain || '',
          });
          result.textContent = `审校建议（${checked.channel} · ${checked.model}）\\n正确性：${checked.correctness}\\n推导：${checked.reasoning}\\n问题：${checked.issues.join('；') || '未发现'}\\n修改建议：${checked.revision_suggestions.join('；') || '无'}\\n仅供参考，不会自动修改题库。`;
        } catch (err) { result.textContent = err.message || '审校失败'; }
        button.disabled = false; button.textContent = 'AI 审校此题';
      } }));
      card.appendChild(result);
    }
    card.appendChild(el('a', { href: `#/topic/${encodeURIComponent(item.topic_id)}/${encodeURIComponent(item.section_id)}/${item.tier}`, text: '打开当前题目所在版块', style: 'font-size:12px' }));
    if (item.review_note) card.appendChild(el('div', { style: 'font-size:12px;color:#0f766e;white-space:pre-wrap', text: `审核回复：${item.review_note}` }));
    if (review && item.status === 'pending') {
      const note = el('textarea', { rows: 3, maxlength: 500, 'aria-label': '审核说明', placeholder: '说明核验结果或修订内容（至少 2 字）', style: 'width:100%;box-sizing:border-box;padding:9px;font:inherit;font-size:13px;border:1px solid #eaddc9;border-radius:9px' });
      const actions = el('div', { class: 'row', style: 'gap:8px;flex-wrap:wrap' });
      for (const [status, label] of [['approved', '通过并奖励 50 积分'], ['rejected', '不通过']]) {
        actions.appendChild(el('button', { class: `btn sm${status === 'rejected' ? ' ghost' : ''}`, text: label, onclick: async () => {
          if (note.value.trim().length < 2) { toast('请填写审核说明'); return; }
          actions.querySelectorAll('button').forEach((b) => { b.disabled = true; });
          try {
            const result = await api.reviewQuestionFeedback(item.id, status, note.value.trim());
            toast(result.rewarded_now ? '已通过，50 积分已到账' : '审核已保存');
            await renderFeedback(view, { review });
          } catch (err) { toast(err.message || '审核失败'); actions.querySelectorAll('button').forEach((b) => { b.disabled = false; }); }
        } }));
      }
      card.appendChild(note); card.appendChild(actions);
    }
    root.appendChild(card);
  }
  view.replaceChildren(root);
}
