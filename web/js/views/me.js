/* 我的：账号、积分、签到、统计 */

import * as api from '../api.js';
import { el, toast, openSheet } from '../ui.js';

export async function renderMe(view) {
  const [me, checkin] = await Promise.all([api.fetchMe(), api.getCheckin()]);

  const root = el('div', { class: 'stack' });

  root.appendChild(el('div', { style: 'padding:2px 2px 0' }, [
    el('div', { style: 'font-size:11px;letter-spacing:.16em;color:#a3928a;font-weight:700;text-transform:uppercase', text: 'Profile' }),
    el('div', { class: 'row', style: 'gap:8px;align-items:center;margin-top:2px' }, [
      el('div', { style: 'font-size:19px;font-weight:800;letter-spacing:-.01em', text: me.nickname }),
      me.is_guest ? el('span', {
        class: 'chip',
        style: 'background:#fef3c7;border-color:#fcd34d;color:#92400e;font-size:11px;font-weight:800;padding:2px 8px',
        text: '演示访客',
      }) : null,
    ]),
    el('div', { style: 'font-size:11.5px;color:#b6a498;margin-top:2px', text: `账号 ${me.username || '—'}` }),
  ]));

  /* ---- 演示访客专用提示卡 ---- */
  if (me.is_guest) {
    root.appendChild(el('section', {
      class: 'panel',
      style: 'background:#fefce8;border:1.5px dashed #facc15;padding:12px 14px',
    }, [
      el('div', { style: 'font-size:13px;font-weight:800;color:#854d0e;margin-bottom:4px', text: '💡 当前处于演示访客体验模式' }),
      el('div', { style: 'font-size:12px;color:#713f12;line-height:1.6',
        text: '本模式用于展示全站数理化核心功能、板书图解与分步动画演示。无需密码，管理权限受限（不支持修改密码、真实礼品核销）。' }),
    ]));
  }

  /* ---- 账号与安全 ---- */
  root.appendChild(el('section', { class: 'panel' }, [
    el('div', { style: 'font-size:13.5px;font-weight:800', text: '账号与安全' }),
    el('div', {
      style: 'font-size:11.5px;color:#a3928a;margin-top:3px;line-height:1.7',
      text: me.is_guest ? '当前为免密公开演示账号，所有功能即开即用' : `当前登录：${me.username || '—'}（${me.nickname}）`,
    }),
    el('div', { class: 'row', style: 'margin-top:12px;gap:8px' }, [
      me.is_guest ? el('button', {
        class: 'btn ghost sm', style: 'flex:1;opacity:.65', text: '免密账号',
        onclick: () => toast('演示访客账号无需修改密码'),
      }) : el('button', {
        class: 'btn ghost sm', style: 'flex:1', text: '修改密码',
        onclick: () => showPasswordSheet(),
      }),
      el('button', {
        class: 'btn ghost sm', style: 'flex:1;color:#b45309;border-color:#fbe6b8', text: '退出登录',
        onclick: () => {
          api.logout();
          location.hash = '#/login';
          location.reload();
        },
      }),
    ]),
  ]));

  /* ---- 数据卡 ---- */
  root.appendChild(el('section', { class: 'panel' }, [
    el('div', { class: 'row', style: 'gap:0' }, [
      statCell(String(me.points), '积分'),
      statCell(String(me.streak), '连签天数'),
      statCell(String(me.stats?.cards ?? 0), '收集卡'),
    ]),
  ]));

  /* ---- 签到日历 ---- */
  const weekHead = ['日', '一', '二', '三', '四', '五', '六'];
  const cal = el('div', { class: 'cal' });
  weekHead.forEach((w) => cal.appendChild(el('div', { class: 'head', text: w })));
  const first = checkin.days[0];
  if (first) {
    const idx = new Date(first.day + 'T00:00:00').getDay();
    for (let i = 0; i < idx; i++) cal.appendChild(el('div'));
  }
  checkin.days.forEach((d) => {
    const n = Number(d.day.slice(-2));
    cal.appendChild(el('div', {
      class: `d ${d.checked ? 'checked' : ''} ${d.is_today ? 'today' : ''} ${d.future ? 'future' : ''}`,
      text: String(n),
    }));
  });

  root.appendChild(el('section', { class: 'panel stack', style: 'gap:12px' }, [
    el('div', { class: 'row-between' }, [
      el('div', {}, [
        el('div', { style: 'font-size:14px;font-weight:800', text: '每日签到' }),
        el('div', { style: 'font-size:11.5px;color:#a3928a;margin-top:2px', text: `连签 ${me.streak} 天 · 连签第 3 天得卡包` }),
      ]),
      checkin.checked_today
        ? el('span', { class: 'chip', text: '今天已签' })
        : el('button', {
          class: 'btn sm', text: '签到',
          onclick: async (e) => {
            e.currentTarget.disabled = true;
            try {
              const r = await api.doCheckin();
              toast(`+${r.points} 积分${r.tickets ? ` · +${r.tickets} 卡包` : ''}`);
              const { render } = await import('../router.js');
              render();
            } catch (err) {
              toast(err.message || '签到失败');
              e.currentTarget.disabled = false;
            }
          },
        }),
    ]),
    cal,
  ]));

  /* ---- 错题本入口 ---- */
  root.appendChild(el('section', {
    class: 'panel',
    style: 'cursor:pointer;background:linear-gradient(135deg,#fef5f5,#fff);border-color:#f5cfcf',
    onclick: () => { location.hash = '#/wrongbook'; },
  }, [
    el('div', { class: 'row-between' }, [
      el('div', { class: 'row', style: 'gap:11px' }, [
        el('div', {
          style: 'width:40px;height:40px;border-radius:12px;background:#fee2e2;display:grid;place-items:center;font-size:17px',
          text: '📕',
        }),
        el('div', {}, [
          el('div', { style: 'font-size:13.5px;font-weight:800', text: '错题本' }),
          el('div', { style: 'font-size:11.5px;color:#a3928a;margin-top:3px', text: '按主题重做清零 · AI 错误分析与改进建议' }),
        ]),
      ]),
      el('div', { style: 'font-size:18px;color:#d9c8b4', text: '›' }),
    ]),
  ]));

  /* ---- 每日抽卡入口 ---- */
  root.appendChild(el('section', {
    class: 'panel',
    style: 'cursor:pointer;background:linear-gradient(135deg,#fff8e8,#fffdf6);border-color:#f7dfae',
    onclick: () => { location.hash = '#/achievements'; },
  }, [
    el('div', { class: 'row-between' }, [
      el('div', { class: 'row', style: 'gap:11px' }, [
        el('div', {
          style: 'width:40px;height:40px;border-radius:12px;background:#fef3c7;display:grid;place-items:center;font-size:18px',
          text: '🎁',
        }),
        el('div', {}, [
          el('div', { style: 'font-size:13.5px;font-weight:800', text: '每日随机卡' }),
          el('div', { style: 'font-size:11.5px;color:#a3928a;margin-top:3px', text: '每天 1 次 · ¥5 / ¥10 / ¥20 / ¥50' }),
        ]),
      ]),
      el('div', { style: 'font-size:18px;color:#d9c8b4', text: '›' }),
    ]),
  ]));

  /* ---- 成就卡入口 ---- */
  root.appendChild(el('section', {
    class: 'panel',
    style: 'cursor:pointer;background:linear-gradient(135deg,#fffbf0,#fff);border-color:#fbe6b8',
    onclick: () => { location.hash = '#/achievements'; },
  }, [
    el('div', { class: 'row-between' }, [
      el('div', { class: 'row', style: 'gap:11px' }, [
        el('div', {
          style: 'width:40px;height:40px;border-radius:12px;background:#fef3c7;display:grid;place-items:center;font-size:17px;font-weight:800;color:#b45309',
          text: '¥',
        }),
        el('div', {}, [
          el('div', { style: 'font-size:13.5px;font-weight:800', text: '成就卡' }),
          el('div', { style: 'font-size:11.5px;color:#a3928a;margin-top:3px', text: '100 积分 = 1 张 50 元卡 · 每天最多 2 张' }),
        ]),
      ]),
      el('div', { style: 'font-size:18px;color:#d9c8b4', text: '›' }),
    ]),
  ]));

  /* ---- 卡包 / 碎片 ---- */
  root.appendChild(el('section', { class: 'panel' }, [
    el('div', { class: 'row-between' }, [
      el('div', {}, [
        el('div', { style: 'font-size:13.5px;font-weight:800', text: '卡包与碎片' }),
        el('div', { style: 'font-size:11.5px;color:#a3928a;margin-top:3px', text: `卡包 ${me.tickets} 张 · 碎片 ${me.shards} 个` }),
      ]),
      el('button', {
        class: 'btn ghost sm', text: '去图鉴',
        onclick: () => { location.hash = '#/album'; },
      }),
    ]),
  ]));

  /* ---- 多设备说明 ---- */
  root.appendChild(el('section', { class: 'panel', style: 'padding:14px' }, [
    el('div', { class: 'row', style: 'gap:10px;align-items:flex-start' }, [
      el('div', {
        style: 'width:34px;height:34px;border-radius:10px;flex:0 0 auto;display:grid;place-items:center;font-size:15px;background:#fdf7ee;border:1px solid var(--line)',
        text: '💡',
      }),
      el('div', {}, [
        el('div', { style: 'font-size:12.5px;font-weight:800', text: '换设备怎么办' }),
        el('div', {
          style: 'font-size:11.5px;color:#a3928a;margin-top:4px;line-height:1.75',
          text: '在另一台设备上打开本站，直接选同一个账号登录即可，进度会自动同步。',
        }),
      ]),
    ]),
  ]));

  /* ---- 规则说明 ---- */
  root.appendChild(el('section', { class: 'panel' }, [
    el('div', { style: 'font-size:13.5px;font-weight:800;margin-bottom:9px', text: '积分规则' }),
    ...ruleRows([
      ['每日签到', '+10 分，连签每天多 +2，单日封顶 +20'],
      ['快速测试', '15 分'],
      ['基础闯关', '每关 10 分'],
      ['知识点总结', '5 分'],
      ['难点剖析', '15 分'],
      ['实战巩固', '20 分'],
      ['Boss', '50 分 + 1 卡包'],
      ['主题全通', '2 张卡包'],
      ['复习', '3 分/次，每日上限 20 分'],
    ]),
  ]));

  root.appendChild(el('div', {
    style: 'text-align:center;font-size:10.5px;color:#b6c2d2;padding:10px 0 4px',
    text: '数据仅保存在本站，昵称可随时修改',
  }));

  view.innerHTML = '';
  view.appendChild(root);
}

function statCell(value, label) {
  return el('div', { style: 'flex:1;text-align:center' }, [
    el('div', { style: 'font-size:21px;font-weight:800;letter-spacing:-.02em;font-variant-numeric:tabular-nums', text: value }),
    el('div', { style: 'font-size:10.5px;color:#a3928a;margin-top:3px', text: label }),
  ]);
}

function ruleRows(rows) {
  return rows.map(([k, v]) => el('div', {
    style: 'display:flex;justify-content:space-between;gap:12px;padding:8px 0;border-top:1px solid #fdf8f0;font-size:12px',
  }, [
    el('span', { style: 'color:#6b5b52;font-weight:600;flex:0 0 auto', text: k }),
    el('span', { style: 'color:#a3928a;text-align:right', text: v }),
  ]));
}

/* ---------- 修改密码 ---------- */

export function showPasswordSheet() {
  const mkInput = (placeholder, autocomplete) => {
    const i = el('input', {
      type: 'password',
      placeholder,
      autocomplete,
      style: 'width:100%;min-height:48px;border:1.5px solid #efe2ce;border-radius:12px;padding:0 14px;font-size:15px;outline:none;background:#fffdf8;margin-top:10px;box-sizing:border-box',
    });
    i.addEventListener('focus', () => { i.style.borderColor = '#fbbf24'; });
    i.addEventListener('blur', () => { i.style.borderColor = '#efe2ce'; });
    return i;
  };

  const oldPwd = mkInput('当前密码', 'current-password');
  const newPwd = mkInput('新密码（至少 6 位）', 'new-password');
  const again = mkInput('再输一次新密码', 'new-password');

  const btn = el('button', {
    class: 'btn full', style: 'margin-top:16px;width:100%', text: '保存新密码',
    onclick: async () => {
      const o = oldPwd.value.trim();
      const n = newPwd.value.trim();
      const a = again.value.trim();

      if (!o) { toast('请输入当前密码'); oldPwd.focus(); return; }
      if (n.length < 6) { toast('新密码至少 6 位'); newPwd.focus(); return; }
      if (n !== a) { toast('两次输入的新密码不一致'); again.focus(); return; }

      btn.disabled = true;
      btn.textContent = '保存中…';
      try {
        await api.changePassword(o, n);
        document.getElementById('overlay').hidden = true;
        toast('密码已更新');
      } catch (err) {
        toast(err.message || '修改失败');
        btn.disabled = false;
        btn.textContent = '保存新密码';
      }
    },
  });

  openSheet(el('div', {}, [oldPwd, newPwd, again, btn]), {
    title: '修改密码',
    sub: '三个账号的密码互相独立',
  });
  setTimeout(() => oldPwd.focus(), 150);
}
