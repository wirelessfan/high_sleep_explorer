/* 应用入口 */

import * as api from './api.js';
import { route, startRouter, render } from './router.js';
import { el, toast } from './ui.js';

import { renderHome } from './views/home.js';
import { renderSubjects } from './views/subjects.js';
import { renderTopic } from './views/topic.js';
import { renderSection } from './views/section.js';
import { renderAlbum } from './views/album.js';
import { renderMe } from './views/me.js';
import { renderAchievements } from './views/achievements.js';
import { renderWrongbook } from './views/wrongbook.js';
import { renderAdmin } from './views/admin.js';
import { renderBlindbox } from './views/blindbox.js';
import { renderRelaxGacha } from './views/relax-gacha.js';
import { renderMiniGames } from './views/mini-games.js';
import { renderWishes } from './views/wishes.js';
import { renderLogin } from './views/login.js';
import { renderFeedback } from './views/feedback.js';
import { renderExamTraining } from './views/exam-training.js';
import { renderAccounts } from './views/accounts.js';

function registerRoutes() {
  route('/', renderHome);
  route('/subjects', renderSubjects);
  route('/exam-training', renderExamTraining);
  route('/exam-training/:id', renderExamTraining);
  route('/topic/:id', renderTopic);
  route('/topic/:id/:sid', renderSection);
  route('/topic/:id/:sid/:tier', renderSection);
  route('/album', renderAlbum);
  route('/me', renderMe);
  route('/achievements', renderAchievements);
  route('/wrongbook', renderWrongbook);
  route('/blindbox', renderBlindbox);
  route('/relax', renderRelaxGacha);
  route('/games', renderMiniGames);
  route('/wishes', renderWishes);
  route('/admin', renderAdmin);
  route('/admin/accounts', renderAccounts);
  route('/login', renderLogin);
  route('/feedback', renderFeedback);
  route('/feedback/review', (view) => renderFeedback(view, { review: true }));
}

function showFatal(message) {
  const view = document.getElementById('view');
  view.innerHTML = '';
  view.appendChild(el('div', { class: 'panel', style: 'margin-top:40px' }, [
    el('div', { style: 'font-size:15px;font-weight:800;margin-bottom:6px', text: '连接失败' }),
    el('div', { style: 'font-size:13px;color:#8a7a70;line-height:1.7', text: message }),
    el('button', {
      class: 'btn', style: 'margin-top:16px', text: '重试',
      onclick: () => location.reload(),
    }),
  ]));
}

/* ---- 启动：有令牌则校验，无令牌进登录页 ---- */

async function boot() {
  registerRoutes();

  const token = api.getToken();
  if (!token) {
    // 没有登录态：直接进登录页，不自动建匿名号
    if (location.hash !== '#/login') location.replace('#/login');
    startRouter();
    return;
  }

  // 有令牌：确认仍然有效
  try {
    await api.fetchMe();
  } catch (err) {
    if (err?.status === 401) {
      api.logout();
      location.replace('#/login');
      startRouter();
      return;
    }
    showFatal(err?.message || '无法连接到服务器，请稍后重试');
    return;
  }

  startRouter();
}

/* ---- 全局：401 时回登录页 ---- */

window.addEventListener('unhandledrejection', (e) => {
  if (e.reason?.status === 401) {
    api.logout();
    toast('登录已失效，请重新登录');
    setTimeout(() => {
      location.hash = '#/login';
      location.reload();
    }, 700);
  }
});

window.addEventListener('album:refresh', () => render());

boot();
