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

export function previewImage(src, title = '状元手写笔记图解') {
  const img = el('img', {
    src,
    alt: title,
    style: 'width:100%;height:auto;border-radius:12px;display:block;margin:0 auto;box-shadow:0 8px 30px rgba(0,0,0,0.15)',
  });
  const wrap = el('div', { class: 'stack', style: 'padding:8px 0;text-align:center' }, [
    img,
    el('div', { style: 'font-size:12px;color:#8a7a70;margin-top:10px', text: '💡 点击遮罩或按 ESC 可关闭大图' }),
  ]);
  openSheet(wrap, { title });
}

/** 多图左右翻页查看；支持键盘方向键与触屏滑动。 */
export function previewGallery(items, start = 0, title = '图解补充') {
  let index = Math.min(Math.max(start, 0), items.length - 1);
  const img = el('img', {
    alt: '',
    style: 'width:100%;height:auto;border-radius:12px;display:block;margin:0 auto;box-shadow:0 8px 30px rgba(0,0,0,.15)',
  });
  const caption = el('div', { style: 'font-size:12.5px;color:#6b5b52;margin-top:10px;line-height:1.6' });
  const counter = el('div', { style: 'font-size:11.5px;color:#a3928a;margin-top:6px' });
  const prev = el('button', {
    class: 'btn ghost sm', style: 'flex:0 0 auto', text: '‹ 上一张',
    onclick: () => show(index - 1),
  });
  const next = el('button', {
    class: 'btn ghost sm', style: 'flex:0 0 auto', text: '下一张 ›',
    onclick: () => show(index + 1),
  });

  function show(i) {
    index = (i + items.length) % items.length;
    const item = items[index];
    img.src = item.src;
    img.alt = item.title || '';
    caption.textContent = item.caption || '';
    counter.textContent = `${index + 1} / ${items.length}`;
  }

  const wrap = el('div', { class: 'stack', style: 'padding:6px 0' }, [
    img,
    caption,
    counter,
    el('div', { class: 'row', style: 'justify-content:space-between;margin-top:4px' }, [prev, next]),
    el('div', { style: 'font-size:11.5px;color:#a3928a;text-align:center', text: '← → 方向键或轻扫切换 · 点击遮罩关闭' }),
  ]);

  const sheet = openSheet(wrap, { title });
  const onKey = (e) => {
    if (e.key === 'ArrowLeft') { show(index - 1); e.preventDefault(); }
    if (e.key === 'ArrowRight') { show(index + 1); e.preventDefault(); }
  };
  document.addEventListener('keydown', onKey);
  const overlay = document.getElementById('overlay');
  const observer = new MutationObserver(() => {
    if (overlay.hidden) { document.removeEventListener('keydown', onKey); observer.disconnect(); }
  });
  observer.observe(overlay, { attributes: true, attributeFilter: ['hidden'] });

  let startX = null;
  sheet.addEventListener('touchstart', (e) => { startX = e.touches[0].clientX; }, { passive: true });
  sheet.addEventListener('touchend', (e) => {
    if (startX === null) return;
    const dx = e.changedTouches[0].clientX - startX;
    if (Math.abs(dx) > 45) show(index + (dx < 0 ? 1 : -1));
    startX = null;
  }, { passive: true });

  show(index);
  return { show };
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
