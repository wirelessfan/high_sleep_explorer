/* 路由与视图调度 */

import { el, spinner } from './ui.js';

const routes = [];
let currentCleanup = null;
let renderToken = 0;
let renderedPath = null;
const scrollMemo = new Map();

if ('scrollRestoration' in history) history.scrollRestoration = 'manual';

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
  const token = ++renderToken;

  for (const r of routes) {
    const m = path.match(r.re);
    if (!m) continue;
    const params = {};
    r.keys.forEach((k, i) => { params[k] = decodeURIComponent(m[i + 1]); });

    if (typeof currentCleanup === 'function') {
      try { currentCleanup(); } catch { /* ignore */ }
      currentCleanup = null;
    }
    if (renderedPath !== null && renderedPath !== path) {
      scrollMemo.set(renderedPath, window.scrollY);
    }

    // 渲染到游离 stage：旧内容保留到新内容就绪，不整屏白闪；过期结果整块丢弃，防串页
    const stage = el('div', { class: 'stack-render' });
    view.classList.add('is-loading');
    const placeholder = setTimeout(() => {
      if (token !== renderToken) return;
      view.replaceChildren(spinner());
    }, 180);

    try {
      const cleanup = await r.handler(stage, params);
      clearTimeout(placeholder);
      if (token !== renderToken) {
        // 已被更新的路由取代：丢弃本次结果
        if (typeof cleanup === 'function') { try { cleanup(); } catch { /* ignore */ } }
        return;
      }
      currentCleanup = typeof cleanup === 'function' ? cleanup : null;
    } catch (err) {
      clearTimeout(placeholder);
      if (token !== renderToken) return;
      console.error(err);
      stage.replaceChildren(el('div', { class: 'panel' }, [
        el('div', { style: 'font-size:15px;font-weight:800;margin-bottom:6px', text: '页面加载失败' }),
        el('div', { style: 'font-size:13px;color:#8a7a70', text: err?.message || '未知错误' }),
        el('button', {
          class: 'btn ghost sm', style: 'margin-top:14px',
          text: '重新加载', onclick: () => render(),
        }),
      ]));
    }
    // stage 直接挂进去（display:contents 不产生额外盒子），而不是搬它的子节点：
    // 视图持有的是这个 stage 引用，切页后它们自己再 paint()/replaceChildren 才不会写到游离节点上
    view.replaceChildren(stage);
    renderedPath = path;
    view.classList.remove('is-loading');
    updateTabs(path);
    window.scrollTo(0, scrollMemo.get(path) ?? 0);
    return;
  }

  if (token !== renderToken) return;
  view.classList.remove('is-loading');
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
