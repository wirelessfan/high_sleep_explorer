/* 应用入口 */

import * as api from './api.js';
import { route, startRouter, render } from './router.js';
import { el, toast } from './ui.js';

import { renderHome } from './views/home.js';
import { renderSubjects } from './views/subjects.js';
import { renderTopic } from './views/topic.js';
import { renderSection } from './views/section.js';
import { renderAlbum } from './views/album.js';
import { renderMe, showAdoptSheet } from './views/me.js';

/* ---- 首次访问：自动建号 ---- */

async function boot() {
  try {
    await api.ensureSession();
  } catch (err) {
    document.getElementById('view').innerHTML = '';
    document.getElementById('view').appendChild(el('div', { class: 'panel', style: 'margin-top:40px' }, [
      el('div', { style: 'font-size:15px;font-weight:800;margin-bottom:6px', text: '连接失败' }),
      el('div', { style: 'font-size:13px;color:#8a7a70;line-height:1.7', text: err?.message || '无法连接到服务器，请稍后重试' }),
      el('button', {
        class: 'btn', style: 'margin-top:16px', text: '重试',
        onclick: () => location.reload(),
      }),
    ]));
    return;
  }

  route('/', renderHome);
  route('/subjects', renderSubjects);
  route('/topic/:id', renderTopic);
  route('/topic/:id/:sid', renderSection);
  route('/album', renderAlbum);
  route('/me', renderMe);

  startRouter();
}

/* ---- 全局：401 时自动重建身份 ---- */

window.addEventListener('unhandledrejection', (e) => {
  const msg = e.reason?.message || '';
  if (e.reason?.status === 401) {
    api.setToken('');
    api.setMeCache(null);
    toast('身份已失效，正在重新建立…');
    setTimeout(() => location.reload(), 900);
  }
});

window.addEventListener('album:refresh', () => render());

boot();
