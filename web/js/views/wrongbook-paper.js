/* 错题回顾试卷：按学科/状态筛选并一键排版为 A4 可打印试卷（支持纯做题版与尾页参考答案） */

import * as api from '../api.js';
import { el, toast, SUBJECT_LABEL } from '../ui.js';
import { navigate } from '../router.js';
import { wrongImage } from '../wrong-image.js';
import { prettyMath, questionText } from '../question-content.js';

const PAPER_CSS = `
.wbp-wrap{display:flex;flex-direction:column;gap:12px}
.wbp-bar{display:flex;flex-wrap:wrap;align-items:center;gap:10px 14px;padding:12px 14px;background:#fff;border:1px solid var(--line);border-radius:14px}
.wbp-bar select{padding:6px 10px;border:1px solid #dfd2be;border-radius:9px;background:#fffdf9;font-size:12.5px;color:var(--ink)}
.wbp-bar label{display:inline-flex;align-items:center;gap:6px;font-size:12.5px;font-weight:700;color:var(--ink-2);cursor:pointer}
.wbp-sheet{background:#fff;border:1px solid var(--line);border-radius:16px;padding:26px 24px 32px;color:#111827;line-height:1.75;font-size:14.5px}
.wbp-head{text-align:center;padding-bottom:14px;border-bottom:2px solid #111827;margin-bottom:18px}
.wbp-head h2{margin:0 0 6px;font-size:21px;font-weight:900}
.wbp-meta{font-size:12.5px;color:#4b5563;display:flex;justify-content:center;flex-wrap:wrap;gap:16px}
.wbp-q{padding:12px 0 14px;border-bottom:1px dashed #d1d5db;break-inside:avoid}
.wbp-q:last-child{border-bottom:none}
.wbp-q-title{font-weight:700;white-space:pre-line}
.wbp-opts{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:6px 18px;margin-top:8px;padding-left:18px;font-size:13.5px}
.wbp-img{max-width:280px;max-height:180px;border:1px solid #e5e7eb;border-radius:8px;margin-top:8px;display:block}
.wbp-blank{height:66px;border:1px dashed #e5e7eb;border-radius:8px;margin-top:8px}
.wbp-ans-sec{margin-top:26px;padding-top:16px;border-top:2px solid #111827;page-break-before:always;break-before:page}
.wbp-ans-sec h3{margin:0 0 12px;font-size:17px;font-weight:900}
.wbp-ans-item{margin-bottom:8px;font-size:13px;line-height:1.65;break-inside:avoid}
@media (max-width:400px){.wbp-opts{grid-template-columns:1fr}}
@media print{
  @page{size:A4;margin:14mm}
  /* 按纸宽排两列，手机预览的单列规则不影响打印 */
  .wbp-opts{grid-template-columns:repeat(2,minmax(0,1fr))}
  body{background:#fff !important}
  .tabbar,.topbar,.wbp-noprint{display:none !important}
  .view{max-width:none !important;padding:0 !important;margin:0 !important}
  .wbp-sheet{border:none !important;border-radius:0 !important;padding:0 !important;font-size:11pt}
  .wbp-blank{border-color:#d1d5db}
}
`;

function fmtAns(it) {
  const letters = ['A', 'B', 'C', 'D', 'E', 'F'];
  if (Array.isArray(it.answer_indices) && it.answer_indices.length) {
    return it.answer_indices.map((i) => letters[i] || String(i + 1)).join('、');
  }
  if (typeof it.answer === 'number' && it.answer >= 0 && letters[it.answer]) return letters[it.answer];
  return it.answer_text || '（待核对）';
}

export async function renderWrongbookPaper(view) {
  const data = await api.getWrongbook();
  const allItems = data.items || [];

  const root = el('div', { class: 'wbp-wrap' });
  const st = document.createElement('style'); st.textContent = PAPER_CSS; root.appendChild(st);

  root.appendChild(el('div', { class: 'topbar wbp-noprint' }, [
    el('button', { class: 'back', text: '‹', onclick: () => { if (history.length > 1) history.back(); else navigate('#/wrongbook'); } }),
    el('div', { style: 'flex:1;min-width:0' }, [
      el('h1', { text: '错题回顾试卷' }),
      el('div', { class: 'sub', text: 'A4 卷面 · 可隐藏答案打印' }),
    ]),
    el('button', { class: 'btn sm', text: '🖨️ 打印 / 存 PDF', onclick: () => window.print() }),
  ]));

  const printable = allItems.filter((i) => i.review_status !== 'needs_transcription');
  const skipped = allItems.length - printable.length;
  const subjectLabel = (id) => (id === 'ALL' ? '综合' : (SUBJECT_LABEL[id] || id || '未分类'));
  const subjects = [...new Set(printable.map((i) => i.subject || '未分类'))];
  const subjSel = el('select', {}, [
    el('option', { value: 'ALL', text: `全部学科（${printable.length} 题）` }),
    ...subjects.map((s) => el('option', {
      value: s,
      text: `${subjectLabel(s)}（${printable.filter((i) => (i.subject || '未分类') === s).length} 题）`,
    })),
  ]);
  const chkAns = el('input', { type: 'checkbox', checked: true });
  const chkImg = el('input', { type: 'checkbox', checked: true });
  const chkBlank = el('input', { type: 'checkbox', checked: true });

  const copyAllBtn = el('button', {
    class: 'btn sm ghost', text: '📋 复制纯文本',
    onclick: async () => {
      const list = filtered();
      const txt = list.map((it, idx) => {
        const opts = (it.options || []).map((o, j) => `  ${String.fromCharCode(65 + j)}. ${o}`).join('\n');
        return `${idx + 1}. ${it.stem || ''}${opts ? '\n' + opts : ''}`;
      }).join('\n\n');
      try { await navigator.clipboard.writeText(txt); toast(`已复制 ${list.length} 道错题文本`); }
      catch { toast('复制失败，请手动选中复制'); }
    },
  });

  root.appendChild(el('div', { class: 'wbp-bar wbp-noprint' }, [
    subjSel,
    el('label', {}, [chkAns, el('span', { text: '尾页附参考答案' })]),
    el('label', {}, [chkImg, el('span', { text: '附原图配图' })]),
    el('label', {}, [chkBlank, el('span', { text: '留作答空白区' })]),
    copyAllBtn,
  ]));

  if (skipped) {
    root.appendChild(el('div', {
      class: 'wbp-noprint',
      style: 'font-size:11.5px;line-height:1.7;color:#92400e;background:#fffbeb;border:1px solid #fde68a;border-radius:11px;padding:9px 11px',
      text: `还有 ${skipped} 道题只有图片、没有文字版，已自动跳过。回到错题本点「✨ AI 提取原图文字」补全后，它们就会出现在试卷里。`,
    }));
  }

  const sheetHost = el('div');
  root.appendChild(sheetHost);

  function filtered() {
    const s = subjSel.value;
    return allItems.filter((it) => (s === 'ALL' || (it.subject || '未分类') === s) && it.review_status !== 'needs_transcription');
  }

  function paintPaper() {
    const items = filtered();
    const today = new Date().toISOString().slice(0, 10);
    const titleSubj = subjectLabel(subjSel.value);
    sheetHost.innerHTML = '';

    if (!items.length) {
      sheetHost.appendChild(el('section', { class: 'wbp-sheet', style: 'text-align:center;color:#6b7280' }, [
        el('div', { text: '当前筛选条件下暂无已文字化的可打印错题。' }),
      ]));
      return;
    }

    const sheet = el('section', { class: 'wbp-sheet' });
    sheet.appendChild(el('header', { class: 'wbp-head' }, [
      el('h2', { text: `Sunny 错题回顾试卷（${titleSubj}）` }),
      el('div', { class: 'wbp-meta' }, [
        el('span', { text: `日期：${today}` }),
        el('span', { text: `共 ${items.length} 题` }),
        el('span', { text: '姓名：__________' }),
        el('span', { text: '得分：______' }),
      ]),
    ]));

    items.forEach((it, idx) => {
      const qBox = el('div', { class: 'wbp-q' });
      const tag = it.skill ? `【${it.skill}】` : '';
      const typeHint = it.qtype === 'fill' ? '（填空题）' : it.qtype === 'solution' ? '（解答题）' : '';
      const stemText = it.stem ? questionText(it.stem) : '（题干待补充）';
      qBox.appendChild(el('div', { class: 'wbp-q-title', text: `${idx + 1}. ${tag}${stemText}${typeHint}` }));
      const opts = Array.isArray(it.options) ? it.options : [];
      if (opts.length) {
        qBox.appendChild(el('div', { class: 'wbp-opts' }, opts.map((o, j) => {
          const body = prettyMath(o.trim());
          const clean = /^[A-F][\.、\s]/.test(body) ? body : `${String.fromCharCode(65 + j)}. ${body}`;
          return el('div', { text: clean });
        })));
      }
      if (chkImg.checked) {
        const imgs = Array.isArray(it.images) && it.images.length ? it.images : (it.image_path ? [it.image_path] : []);
        imgs.forEach((src, k) => {
          qBox.appendChild(wrongImage(src, {
            className: 'wbp-img',
            alt: `第 ${idx + 1} 题配图${imgs.length > 1 ? ` ${k + 1}` : ''}`,
          }));
        });
      }
      if (chkBlank.checked && !opts.length) {
        qBox.appendChild(el('div', { class: 'wbp-blank' }));
      }
      sheet.appendChild(qBox);
    });

    if (chkAns.checked) {
      const ansSec = el('section', { class: 'wbp-ans-sec' }, [
        el('h3', { text: '参考答案与错因提示（核对用）' }),
      ]);
      items.forEach((it, idx) => {
        const reason = it.wrong_reason || it.explain || '';
        ansSec.appendChild(el('div', { class: 'wbp-ans-item' }, [
          el('strong', { text: `${idx + 1}. 答案：${prettyMath(fmtAns(it))}` }),
          reason ? el('span', { style: 'color:#4b5563', text: `  —  ${reason}` }) : null,
        ]));
      });
      sheet.appendChild(ansSec);
    }

    sheetHost.appendChild(sheet);
  }

  [subjSel, chkAns, chkImg, chkBlank].forEach((c) => c.addEventListener('change', paintPaper));
  paintPaper();

  view.innerHTML = '';
  view.appendChild(root);
}
