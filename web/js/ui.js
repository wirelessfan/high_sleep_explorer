/* 工具函数：DOM、格式化、提示 */

export function el(tag, attrs = {}, children = []) {
  const node = document.createElement(tag);
  for (const [k, v] of Object.entries(attrs)) {
    if (v === null || v === undefined || v === false) continue;
    if (k === 'class') node.className = v;
    else if (k === 'html') node.innerHTML = v;
    else if (k === 'text') node.textContent = v;
    else if (k.startsWith('on') && typeof v === 'function') {
      node.addEventListener(k.slice(2).toLowerCase(), v);
    } else if (v === true) node.setAttribute(k, '');
    else node.setAttribute(k, v);
  }
  for (const c of [].concat(children)) {
    if (c === null || c === undefined || c === false) continue;
    node.appendChild(typeof c === 'string' ? document.createTextNode(c) : c);
  }
  return node;
}

export function escapeHtml(s) {
  return String(s ?? '').replace(/[&<>"']/g, (m) => ({
    '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;',
  }[m]));
}

export function toast(msg, ms = 2000) {
  const node = document.getElementById('toast');
  if (!node) return;
  node.textContent = msg;
  node.hidden = false;
  clearTimeout(toast._t);
  toast._t = setTimeout(() => { node.hidden = true; }, ms);
}

export function openSheet(content, { title, sub } = {}) {
  const overlay = document.getElementById('overlay');
  const sheet = el('div', { class: 'sheet' });
  if (title) sheet.appendChild(el('h3', { text: title }));
  if (sub) sheet.appendChild(el('div', { class: 'sub', text: sub }));
  if (typeof content === 'string') {
    const wrap = el('div', { html: content });
    sheet.appendChild(wrap);
  } else if (content) {
    sheet.appendChild(content);
  }
  overlay.innerHTML = '';
  overlay.appendChild(sheet);
  overlay.hidden = false;

  const close = () => { overlay.hidden = true; overlay.innerHTML = ''; document.removeEventListener('keydown', onKey); };
  overlay.addEventListener('click', (e) => { if (e.target === overlay) close(); }, { once: true });
  const onKey = (e) => { if (e.key === 'Escape') close(); };
  document.addEventListener('keydown', onKey);
  return { close, sheet };
}

export function spinner() {
  return el('div', { class: 'stack' }, [
    el('div', { class: 'skeleton sk-card' }),
    el('div', { class: 'skeleton sk-card' }),
    el('div', { class: 'skeleton sk-card' }),
  ]);
}

export function emptyState(icon, title, desc) {
  return el('div', { class: 'empty' }, [
    el('div', { class: 'ico', text: icon }),
    el('div', { class: 't', text: title }),
    desc ? el('div', { class: 'd', text: desc }) : null,
  ]);
}

export const SUBJECT_LABEL = { physics: '物理', chemistry: '化学', math: '数学' };
export const SUBJECT_CLASS = { physics: 'phys', chemistry: 'chem', math: 'math' };
export const SUBJECT_COLOR = { physics: '#3b82f6', chemistry: '#10b981', math: '#f59e0b' };

export function rarityClass(r) {
  return `rar-${r}`;
}

export function biliEmbed(bvid) {
  return `https://player.bilibili.com/player.html?bvid=${encodeURIComponent(bvid)}&autoplay=0&danmaku=0&high_quality=1`;
}

export function biliLink(bvid) {
  return `https://www.bilibili.com/video/${encodeURIComponent(bvid)}`;
}

export function fmtScore(n) {
  return Number.isFinite(n) ? Math.round(n) : 0;
}
