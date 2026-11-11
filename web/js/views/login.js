/* 登录页：选择账号 + 密码 */

import * as api from '../api.js';
import { el, toast } from '../ui.js';

let selected = '';

export async function renderLogin(view) {
  view.classList.add('no-tab');
  document.getElementById('tabbar').hidden = true;

  let users = [];
  try {
    const res = await api.listUsers();
    users = res.users || [];
  } catch { /* 首次部署可能还没有账号 */ }

  const root = el('div', { class: 'login-wrap' });

  /* ---- 头图 ---- */
  root.appendChild(el('div', { class: 'login-hero' }, [
    el('img', { src: '/assets/art/hero-journey.svg', alt: '' }),
    el('div', { class: 'lh-text' }, [
      el('div', { class: 'lh-title', text: 'Sunny 的高中探索旅程' }),
      el('div', { class: 'lh-sub', text: '选一个账号，继续今天的探险' }),
    ]),
  ]));

  /* ---- 表单 ---- */
  const card = el('section', { class: 'panel login-card' });

  if (!users.length) {
    card.appendChild(el('div', {
      style: 'font-size:13px;color:#8a7a70;text-align:center;padding:20px 0',
      text: '还没有创建账号。请联系管理员初始化。',
    }));
  } else {
    if (!selected) selected = users[0].username;

    const avatarOf = { sunny: '☀️', dad: '👨', mom: '👩' };
    const chips = el('div', { class: 'login-users' });
    users.forEach((u) => {
      chips.appendChild(el('button', {
        class: `login-user ${u.username === selected ? 'on' : ''}`,
        type: 'button',
        onclick: () => { selected = u.username; renderLogin(view); },
      }, [
        el('span', { class: 'lu-avatar', text: avatarOf[u.username] || '🙂' }),
        el('span', { class: 'lu-name', text: u.nickname }),
        el('span', { class: 'lu-id', text: u.username }),
      ]));
    });
    card.appendChild(chips);

    const pwd = el('input', {
      type: 'password',
      placeholder: '请输入密码',
      autocomplete: 'current-password',
      style: 'width:100%;min-height:48px;border:1.5px solid #efe2ce;border-radius:12px;padding:0 14px;font-size:15px;outline:none;background:#fffdf8;margin-top:16px;box-sizing:border-box',
    });
    pwd.addEventListener('focus', () => { pwd.style.borderColor = '#fbbf24'; });
    pwd.addEventListener('blur', () => { pwd.style.borderColor = '#efe2ce'; });

    const btn = el('button', { class: 'btn full', style: 'margin-top:12px', text: '进入' });

    const submit = async () => {
      const password = pwd.value.trim();
      if (!password) { toast('请输入密码'); pwd.focus(); return; }
      btn.disabled = true;
      btn.textContent = '登录中…';
      try {
        await api.login(selected, password);
        toast('欢迎回来');
        location.hash = '#/';
        location.reload();
      } catch (err) {
        toast(err.message || '登录失败');
        btn.disabled = false;
        btn.textContent = '进入';
        pwd.select();
      }
    };

    pwd.addEventListener('keydown', (e) => { if (e.key === 'Enter') submit(); });
    btn.addEventListener('click', submit);

    card.appendChild(pwd);
    card.appendChild(btn);
    card.appendChild(el('div', {
      style: 'font-size:11px;color:#b6a498;text-align:center;margin-top:12px',
      text: '首次登录后可在「我的」页修改密码',
    }));

    /* ---- 访客免密演示通道 ---- */
    const guestDivider = el('div', {
      style: 'display:flex;align-items:center;gap:10px;margin:20px 0 12px;color:#a3928a;font-size:12px',
    }, [
      el('div', { style: 'flex:1;height:1px;background:#f0e4d4' }),
      el('span', { text: '或 免密码体验' }),
      el('div', { style: 'flex:1;height:1px;background:#f0e4d4' }),
    ]);
    card.appendChild(guestDivider);

    const guestBtn = el('button', {
      class: 'btn ghost full',
      style: 'background:#fdfaf3;border:1.5px solid #ebd9b8;color:#92400e;font-weight:800;border-radius:12px',
      text: '✨ 访客一键体验（免密演示）',
      onclick: async () => {
        guestBtn.disabled = true;
        guestBtn.textContent = '正在进入演示环境…';
        try {
          await api.guestLogin();
          toast('已以演示访客身份进入');
          location.hash = '#/';
          location.reload();
        } catch (err) {
          toast(err.message || '访客模式进入失败');
          guestBtn.disabled = false;
          guestBtn.textContent = '✨ 访客一键体验（免密演示）';
        }
      },
    });
    card.appendChild(guestBtn);
    card.appendChild(el('div', {
      style: 'font-size:11px;color:#8a7a70;text-align:center;margin-top:8px;line-height:1.5',
      text: '演示模式：可自由浏览全学科知识图解、SVG 动效及做题体验，管理权限受限',
    }));
  }

  root.appendChild(card);

  view.innerHTML = '';
  view.appendChild(root);
  if (users.length) setTimeout(() => document.querySelector('.login-card input')?.focus(), 120);
}
