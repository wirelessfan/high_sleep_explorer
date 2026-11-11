/* 路由与视图调度 */

import { el, spinner } from './ui.js';

const routes = [];
let currentCleanup = null;

export function route(pattern, handler) {
  const keys = [];
  const re = new RegExp('^' + pattern.replace(/:([a-zA-Z]+)/g, (_, k) => {
    keys.push(k);
    return '([^/]+)';
  }) + '$');
  routes.push({ re, keys, handler });
}

export function navigate(hash) {
  if (location.hash === hash) render();
  else location.hash = hash;
}

export function currentPath() {
  const h = location.hash.replace(/^#/, '');
  return h || '/';
}

export async function render() {
  const path = currentPath();
  const view = document.getElementById('view');

  for (const r of routes) {
    const m = path.match(r.re);
    if (!m) continue;
    const params = {};
    r.keys.forEach((k, i) => { params[k] = decodeURIComponent(m[i + 1]); });

    if (typeof currentCleanup === 'function') {
      try { currentCleanup(); } catch { /* ignore */ }
      currentCleanup = null;
    }

    view.innerHTML = '';
    view.appendChild(spinner());
    try {
      const cleanup = await r.handler(view, params);
      currentCleanup = typeof cleanup === 'function' ? cleanup : null;
    } catch (err) {
      console.error(err);
      view.innerHTML = '';
      view.appendChild(el('div', { class: 'panel' }, [
        el('div', { style: 'font-size:15px;font-weight:800;margin-bottom:6px', text: '页面加载失败' }),
        el('div', { style: 'font-size:13px;color:#8a7a70', text: err?.message || '未知错误' }),
        el('button', {
          class: 'btn ghost sm', style: 'margin-top:14px',
          text: '重新加载', onclick: () => render(),
        }),
      ]));
    }
    updateTabs(path);
    window.scrollTo(0, 0);
    return;
  }

  view.innerHTML = '';
  view.appendChild(el('div', { class: 'empty' }, [
    el('div', { class: 'ico', text: '🧭' }),
    el('div', { class: 't', text: '页面不存在' }),
    el('div', { class: 'd', text: '返回首页继续学习' }),
  ]));
}

function updateTabs(path) {
  const tabbar = document.getElementById('tabbar');
  const view = document.getElementById('view');
  const hide = path.startsWith('/topic/') || path === '/login' || path === '/welcome';
  tabbar.hidden = hide;
  view.classList.toggle('no-tab', hide);

  const active = path === '/' ? '#/' :
    path.startsWith('/subjects') ? '#/subjects' :
    path.startsWith('/album') ? '#/album' :
    path.startsWith('/me') ? '#/me' : null;

  tabbar.querySelectorAll('.tab').forEach((t) => {
    t.classList.toggle('active', t.dataset.route === active);
  });
}

export function startRouter() {
  window.addEventListener('hashchange', render);
  render();
}
