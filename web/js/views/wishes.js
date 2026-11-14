/* 许愿墙：提改进意见，每条 +1 盲盒券，每天最多 3 条 */

import * as api from '../api.js';
import { el, toast } from '../ui.js';

const STATUS_LABEL = { open: '待处理', planned: '已采纳', done: '已实现' };
const STATUS_STYLE = {
  open: 'background:#f1f5f9;color:#475569',
  planned: 'background:#fef3c7;color:#92400e',
  done: 'background:#dcfce7;color:#047857',
};

function fmtTime(iso) {
  if (!iso) return '';
  return iso.slice(5, 16).replace('T', ' ');
}

export async function renderWishes(view) {
  const data = await api.getWishes();
  const root = el('div', { class: 'stack' });

  root.appendChild(el('div', { class: 'topbar' }, [
    el('button', { class: 'back', text: '‹', onclick: () => { location.hash = '#/me'; } }),
    el('div', { style: 'flex:1' }, [
      el('h1', { text: '许愿墙' }),
      el('div', { class: 'sub', text: '留言就是帮我们改进 · 每条得盲盒券' }),
    ]),
  ]));

  /* ---- 提交区 ---- */
  const input = el('textarea', {
    rows: '3',
    placeholder: '想加什么功能？哪里不好用？说说你的想法…',
    style: 'width:100%;box-sizing:border-box;font-size:13px;line-height:1.7;padding:11px 12px;' +
      'border:1px solid #eaddc9;border-radius:12px;background:#fffdf9;color:#3b2f2a;resize:vertical;' +
      'font-family:inherit',
  });
  const counter = el('div', { style: 'font-size:11px;color:#b6a498;text-align:right;margin-top:3px', text: '0 字' });
  input.addEventListener('input', () => { counter.textContent = `${input.value.trim().length} 字`; });

  const submitBtn = el('button', { class: 'btn full', style: 'margin-top:9px' });
  function paintSubmit() {
    const left = data.left_today;
    submitBtn.textContent = left > 0
      ? `提交意见（+${data.ticket_reward} 张盲盒券）`
      : '今天已经提满 3 条啦';
    submitBtn.disabled = left <= 0;
  }
  paintSubmit();

  root.appendChild(el('section', { class: 'panel', style: 'padding:14px' }, [
    el('div', { class: 'row-between', style: 'margin-bottom:8px' }, [
      el('div', { style: 'font-size:13px;font-weight:800', text: '我想说…' }),
      el('div', { class: 'row', style: 'gap:6px' }, [
        el('span', { class: 'chip', style: `font-size:10px;padding:2px 8px;${STATUS_STYLE.open}`, text: '待处理' }),
        el('span', { style: 'font-size:11px;color:#a3928a', text: `今日 ${data.mine_today}/${data.per_day} 条` }),
      ]),
    ]),
    input,
    counter,
    submitBtn,
    el('div', { style: 'font-size:11px;color:#a3928a;margin-top:8px;line-height:1.7',
      text: `每人每天最多 ${data.per_day} 条，每条 +${data.ticket_reward} 张盲盒券；同一条意见不要重复提交。` }),
  ]));

  /* ---- 墙 ---- */
  root.appendChild(el('div', { class: 'section-head' }, [
    el('h3', { text: '大家的心愿' }),
    el('span', { class: 'hint', text: `${data.items.length} 条` }),
  ]));

  const list = el('div', { class: 'stack', style: 'gap:9px' });
  if (!data.items.length) {
    list.appendChild(el('div', { class: 'empty' }, [
      el('div', { style: 'font-size:34px', text: '💌' }),
      el('div', { style: 'font-size:14px;font-weight:800;margin-top:8px', text: '还没有人许愿' }),
      el('div', { style: 'font-size:12px;color:#a3928a;margin-top:5px', text: '你可以是第一个' }),
    ]));
  }
  data.items.forEach((w) => {
    const card = el('section', { class: 'panel', style: 'padding:12px 13px' });
    card.appendChild(el('div', { class: 'row-between', style: 'margin-bottom:7px' }, [
      el('div', { class: 'row', style: 'gap:7px;min-width:0' }, [
        el('span', { style: 'font-size:12px;font-weight:800;color:#3b2f2a', text: w.mine ? '我' : w.nickname }),
        el('span', { style: `font-size:9.5px;font-weight:800;border-radius:6px;padding:1px 7px;${STATUS_STYLE[w.status] || STATUS_STYLE.open}`,
          text: STATUS_LABEL[w.status] || w.status }),
      ]),
      el('span', { style: 'font-size:10.5px;color:#b6a498', text: fmtTime(w.created_at) }),
    ]));
    card.appendChild(el('div', {
      style: 'font-size:13px;color:#3b2f2a;line-height:1.75;white-space:pre-wrap;word-break:break-word',
      text: w.content,
    }));
    if (w.reply) {
      card.appendChild(el('div', {
        style: 'margin-top:9px;background:#f0fdf4;border-left:3px solid #34d399;border-radius:0 9px 9px 0;' +
          'padding:8px 10px;font-size:12px;color:#065f46;line-height:1.7',
      }, [
        el('div', { style: 'font-size:10px;font-weight:800;color:#047857;margin-bottom:3px', text: '官方回复' }),
        el('div', { text: w.reply, style: 'white-space:pre-wrap' }),
      ]));
    }

    /* ---- 管理员：就在墙上回复 / 改状态 ---- */
    if (data.is_admin) {
      const replyInput = el('textarea', {
        rows: '2', placeholder: '写一条官方回复…',
        style: 'width:100%;box-sizing:border-box;font-size:12px;line-height:1.6;padding:8px 10px;' +
          'border:1px solid #bfe3de;border-radius:9px;background:#f8fffd;color:#2f2a26;' +
          'resize:vertical;font-family:inherit;margin-top:8px',
      });
      replyInput.value = w.reply || '';
      const statusSel = el('select', {
        style: 'font-size:11.5px;padding:6px 8px;border:1px solid #bfe3de;border-radius:8px;' +
          'background:#f8fffd;color:#2f2a26',
      }, Object.entries(STATUS_LABEL).map(([k, label]) => el('option', {
        value: k, ...(w.status === k ? { selected: true } : {}), text: label,
      })));

      const saveBtn = el('button', {
        class: 'btn sm', text: '回复',
        onclick: async () => {
          const text = replyInput.value.trim();
          if (!text && statusSel.value === w.status) { toast('写点回复内容或改个状态'); return; }
          saveBtn.disabled = true;
          saveBtn.textContent = '发送中…';
          try {
            await api.adminModerateWish(w.id, statusSel.value, text);
            toast('已回复，对方刷新就能看到');
            renderWishes(view);
          } catch (err) {
            toast(err.message || '回复失败');
            saveBtn.disabled = false;
            saveBtn.textContent = '回复';
          }
        },
      });

      card.appendChild(el('div', {
        style: 'margin-top:9px;padding-top:9px;border-top:1px dashed #cfe9e4',
      }, [
        el('div', { style: 'font-size:10px;font-weight:800;color:#0f766e;margin-bottom:5px',
          text: '👨‍👦 管理员回复' }),
        replyInput,
        el('div', { class: 'row', style: 'gap:7px;margin-top:6px;align-items:center' }, [
          statusSel,
          saveBtn,
          w.mine ? null : el('span', { style: 'font-size:10px;color:#b6a498',
            text: `提交者：${w.nickname}` }),
        ]),
      ]));
    }

    list.appendChild(card);
  });
  root.appendChild(list);

  view.innerHTML = '';
  view.appendChild(root);

  /* ---- 提交 ---- */
  submitBtn.addEventListener('click', async () => {
    const text = input.value.trim();
    if (text.length < 5) { toast('多说几个字吧（至少 5 个字）'); return; }
    submitBtn.disabled = true;
    submitBtn.textContent = '提交中…';
    try {
      const res = await api.postWish(text);
      toast(`收到！+${res.bonus} 张盲盒券 🎁`);
      renderWishes(view);
    } catch (err) {
      toast(err.message || '提交失败');
      paintSubmit();
    }
  });
}