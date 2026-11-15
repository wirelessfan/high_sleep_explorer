/* Registered identities and anonymous history have different ownership semantics. */
import * as api from '../api.js';
import { el, toast, openSheet } from '../ui.js';

export async function renderAccounts(view) {
  const data = await api.adminUsers();
  const root = el('div', { class: 'stack' }, [
    el('div', { class: 'topbar' }, [
      el('button', { class: 'back', text: '‹', onclick: () => { location.hash = '#/me'; } }),
      el('div', {}, [el('h1', { text: '账号管理' }), el('div', { class: 'sub', text: '五类身份 · 同学各自独立' })]),
    ]),
    el('section', { class: 'panel', text: `正式账号 ${data.registered_count} 个。家庭成员按固定账号识别；每位同学拥有自己的账号、积分、错题和进度。` }),
    el('button', { class: 'btn full', text: '开通同学账号', onclick: () => studentSheet() }),
  ]);
  for (const group of data.groups) {
    const panel = el('section', { class: 'panel stack', style: 'gap:10px' }, [
      el('div', { class: 'row-between' }, [el('strong', { text: group.label }),
        el('span', { class: 'hint', text: group.type === 'guest' ? '独立体验' : `${group.count} 个账号` })]),
    ]);
    if (group.type === 'guest') {
      panel.append(el('div', { class: 'hint', text: '访客免密体验，各自保存临时进度，不计入正式账号数量。' }));
    } else if (!group.users.length) {
      panel.append(el('div', { class: 'hint', text: group.type === 'student' ? '还没有独立同学账号，可在上方开通。' : '该家庭账号尚未初始化。' }));
    }
    for (const user of group.users) panel.append(el('div', { style: 'border-top:1px solid #f0e4d4;padding-top:10px' }, [
      el('div', { class: 'row-between' }, [
        el('strong', { text: `${user.nickname} @${user.username}` }),
        el('span', { class: 'chip', text: user.is_admin ? '管理员' : '学习账号' }),
      ]),
      el('div', { class: 'hint', style: 'margin-top:6px', text: `${user.points} 积分 · ${user.progress_count} 条学习进度 · 最近 ${user.last_seen || '—'}` }),
    ]));
    root.append(panel);
  }
  const history = el('details', { class: 'panel' }, [
    el('summary', { style: 'cursor:pointer;font-weight:800', text: `历史临时记录（${data.historical_count} 条）` }),
    el('p', { class: 'hint', style: 'line-height:1.8', text: '以下是旧版自动创建的记录，昵称可能重复。数据已保留，不计为正式账号。请先核实归属，再转为独立同学账号；不会自动合并积分或进度。' }),
  ]);
  for (const user of data.historical_users) history.append(el('div', { style: 'padding:12px 0;border-top:1px solid #f0e4d4' }, [
    el('strong', { text: `旧昵称：${user.nickname}` }),
    el('div', { class: 'hint', style: 'overflow-wrap:anywhere;margin-top:5px', text: `记录 ${user.id} · 创建 ${(user.created_at || '').slice(0, 16).replace('T', ' ')}` }),
    el('div', { class: 'hint', style: 'margin:5px 0 8px', text: `${user.points} 积分 · ${user.progress_count} 条学习进度 · 最近 ${user.last_seen || '—'}` }),
    el('button', { class: 'btn ghost sm', text: '核实后转为同学账号', onclick: () => studentSheet(user) }),
  ]));
  root.append(history); view.replaceChildren(root);

  function studentSheet(legacy) {
    const style = 'width:100%;box-sizing:border-box;padding:10px;border:1px solid #eaddc9;border-radius:10px;margin-top:8px;font:inherit';
    const username = el('input', { 'aria-label': '新同学账号', placeholder: '账号，如 classmate01', autocomplete: 'off', style });
    const nickname = el('input', { 'aria-label': '同学昵称', placeholder: '同学昵称', maxlength: 20, style });
    const password = el('input', { type: 'password', 'aria-label': '初始密码', placeholder: '初始密码，至少8位', autocomplete: 'new-password', style });
    const verified = legacy ? el('input', { type: 'checkbox', 'aria-label': '已核实历史记录归属' }) : null;
    const button = el('button', { class: 'btn full', style: 'margin-top:14px', text: legacy ? '保留原数据并开通' : '创建同学账号', onclick: async () => {
      if (legacy && !verified.checked) { toast('请先核实该记录归属'); return; }
      button.disabled = true;
      try {
        await api.createStudent({ username: username.value.trim(), nickname: nickname.value.trim(), password: password.value,
          ...(legacy ? { legacy_user_id: legacy.id } : {}) });
        document.getElementById('overlay').hidden = true;
        password.value = ''; toast('已开通独立同学账号'); await renderAccounts(view);
      } catch (err) { toast(err.message || '开通失败'); button.disabled = false; }
    } });
    openSheet(el('div', {}, [
      el('p', { class: 'hint', style: 'line-height:1.7', text: legacy
        ? `将记录 ${legacy.id} 登记为独立账号，保留该记录所有进度、积分和奖励。旧设备需使用新账号密码重新登录。`
        : '为一位同学创建独立账号。账号为3–32位，以字母开头，可含数字、下划线和短横线。初始密码请交给本人，登录后可修改。' }),
      username, nickname, password,
      legacy ? el('label', { class: 'row', style: 'gap:8px;margin-top:12px' }, [verified, '我已核实这条历史记录属于该同学']) : null,
      button,
    ]), { title: legacy ? '登记历史同学记录' : '开通同学账号' });
  }
}
