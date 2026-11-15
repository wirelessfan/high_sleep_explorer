/* Per-question report captures its location and the exact displayed version. */
import * as api from './api.js';
import { el, toast, openSheet } from './ui.js';
import { questionText } from './question-content.js';

const CATEGORIES = { incomplete: '题目不完整/显示异常', answer: '答案可能有误', explanation: '解析有误/不清楚', diagram: '图解问题', other: '其他问题' };

export function feedbackButton(context, question) {
  return el('button', {
    type: 'button', class: 'question-feedback btn ghost sm',
    style: 'margin-top:10px;font-size:11.5px', text: '题目有问题？反馈',
    onclick: () => {
      const category = el('select', { 'aria-label': '问题类型', style: 'width:100%;padding:9px;border:1px solid #eaddc9;border-radius:9px' },
        Object.entries(CATEGORIES).map(([value, label]) => el('option', { value, text: label })));
      const detail = el('textarea', { rows: 4, maxlength: 1000, 'aria-label': '问题描述', placeholder: '请描述缺少的条件、显示异常或你认为有误的地方（至少 5 字）',
        style: 'box-sizing:border-box;width:100%;padding:10px;font:inherit;font-size:13px;line-height:1.7;border:1px solid #eaddc9;border-radius:9px;margin-top:10px' });
      const send = el('button', { class: 'btn full', style: 'margin-top:12px', text: '提交反馈', onclick: async () => {
        if (detail.value.trim().length < 5) { toast('请至少写 5 个字描述问题'); return; }
        send.disabled = true;
        try {
          const res = await api.postQuestionFeedback({ ...context, category: category.value, detail: detail.value.trim(),
            displayed_stem: question.stem || '', displayed_options: question.options });
          document.getElementById('overlay').hidden = true;
          toast(res.duplicate ? '这道题已反馈，可在「我的反馈」查看进度' : '已提交，审核通过后奖励 50 积分');
        } catch (err) { toast(err.message || '提交失败'); send.disabled = false; }
      } });
      openSheet(el('div', {}, [
        el('div', { style: 'font-size:12px;line-height:1.7;color:#6b5b52;margin-bottom:10px;white-space:pre-wrap', text: questionText(question.stem).slice(0, 240) }),
        category, detail, send,
        el('div', { class: 'hint', style: 'margin-top:10px', text: '管理员审核通过奖励 50 积分，同一题目版本只奖励一次。' }),
        el('a', { href: '#/feedback', style: 'display:block;margin-top:9px;font-size:12px', text: '查看我的反馈', onclick: () => { document.getElementById('overlay').hidden = true; } }),
      ]), { title: '反馈题目问题' });
    },
  });
}
