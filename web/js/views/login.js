/* Five identity entrances; classmates use individual private credentials. */
import * as api from '../api.js';
import { el, toast } from '../ui.js';

let selected = 'sunny';
const TYPES = [
  ['dad', '👨', '爸爸', 'dad'], ['mom', '👩', '妈妈', 'mom'],
  ['sunny', '☀️', 'Sunny', 'sunny'], ['student', '🎒', '同学', '独立账号'],
  ['guest', '✨', '访客', '免密体验'],
];
const INPUT_STYLE = 'width:100%;min-height:48px;border:1.5px solid #efe2ce;border-radius:12px;padding:0 14px;font-size:15px;background:#fffdf8;box-sizing:border-box';

export async function renderLogin(view) {
  if (api.getToken()) {
    try { await api.fetchMe(); location.hash = '#/'; return; }
    catch (err) { if (err.status !== 401) throw err; api.logout(); }
  }
  const { users } = await api.listUsers();
  view.classList.add('no-tab');
  document.getElementById('tabbar').hidden = true;
  const root = el('div', { class: 'login-wrap' }, [
    el('div', { class: 'login-hero' }, [
      el('img', { src: '/assets/art/hero-journey.svg', alt: '' }),
      el('div', { class: 'lh-text' }, [
        el('div', { class: 'lh-title', text: 'Sunny 的高中探索旅程' }),
        el('div', { class: 'lh-sub', text: '选择身份，继续今天的探险' }),
      ]),
    ]),
  ]);
  const card = el('section', { class: 'panel login-card' });
  const chips = el('div', { class: 'login-users', 'aria-label': '选择账号类别' });
  const formArea = el('div', { style: 'margin-top:16px' });
  let busy = false;
  function paint() {
    chips.replaceChildren(...TYPES.map(([key, avatar, name, subtitle]) => el('button', {
      type: 'button', class: `login-user${selected === key ? ' on' : ''}`, 'aria-pressed': String(selected === key),
      onclick: () => { if (!busy) { selected = key; paint(); } },
    }, [el('span', { class: 'lu-avatar', text: avatar }), el('span', { class: 'lu-name', text: name }), el('span', { class: 'lu-id', text: subtitle })])));
    formArea.replaceChildren();
    if (selected === 'guest') {
      const button = el('button', { class: 'btn full', text: '访客一键体验', onclick: async () => {
        if (busy) return;
        busy = true; button.disabled = true;
        try { await api.guestLogin(); location.hash = '#/'; location.reload(); }
        catch (err) { toast(err.message || '暂时无法进入'); busy = false; button.disabled = false; }
      } });
      formArea.append(el('p', { class: 'hint', text: '无需密码。每位访客的体验进度独立；需要长期学习请联系管理员开通同学账号。' }), button);
      return;
    }
    const student = selected === 'student';
    if (!student && !users.some((u) => u.username === selected)) {
      formArea.append(el('p', { class: 'hint', text: '该家庭账号尚未初始化，请联系管理员。' })); return;
    }
    const user = el('input', { type: student ? 'text' : 'hidden', autocomplete: 'username', value: student ? '' : selected,
      'aria-label': '同学账号', placeholder: '输入你的同学账号', autocapitalize: 'none', spellcheck: 'false', style: INPUT_STYLE });
    const password = el('input', { type: 'password', autocomplete: 'current-password', 'aria-label': '密码', placeholder: '请输入密码', style: INPUT_STYLE + ';margin-top:12px' });
    const submit = el('button', { type: 'submit', class: 'btn full', style: 'margin-top:12px', text: '进入' });
    const form = el('form', { onsubmit: async (event) => {
      event.preventDefault();
      if (busy) return;
      if (!user.value.trim() || !password.value) { toast('请输入账号和密码'); return; }
      busy = true; submit.disabled = true; submit.textContent = '登录中…';
      try { await api.login(user.value.trim(), password.value, selected); location.hash = '#/'; location.reload(); }
      catch (err) { toast(err.message || '登录失败'); busy = false; submit.disabled = false; submit.textContent = '进入'; }
    } }, [user, password, submit]);
    formArea.append(form, el('p', { class: 'hint', style: 'line-height:1.7', text: student
      ? '每位同学使用独立账号，积分、错题和学习进度各自保存。账号由管理员开通。'
      : '使用该家庭成员原有的账号密码登录。' }),
    el('p', { class: 'hint', text: '登录后，此浏览器 7 天内免密；主动退出后需重新登录。' }));
  }
  card.append(chips, formArea); root.append(card); view.replaceChildren(root); paint();
}
