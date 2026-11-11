/* 我的：积分、签到、同步码、统计 */

import * as api from '../api.js';
import { el, toast, openSheet } from '../ui.js';

export async function renderMe(view) {
  const [me, checkin] = await Promise.all([api.fetchMe(), api.getCheckin()]);

  const root = el('div', { class: 'stack' });

  root.appendChild(el('div', { style: 'padding:2px 2px 0' }, [
    el('div', { style: 'font-size:11px;letter-spacing:.16em;color:#94a3b8;font-weight:700;text-transform:uppercase', text: 'Profile' }),
    el('div', { style: 'font-size:19px;font-weight:800;letter-spacing:-.01em;margin-top:2px', text: me.nickname }),
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
        el('div', { style: 'font-size:11.5px;color:#94a3b8;margin-top:2px', text: `连签 ${me.streak} 天 · 连签第 3 天得卡包` }),
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

  /* ---- 卡包 / 碎片 ---- */
  root.appendChild(el('section', { class: 'panel' }, [
    el('div', { class: 'row-between' }, [
      el('div', {}, [
        el('div', { style: 'font-size:13.5px;font-weight:800', text: '卡包与碎片' }),
        el('div', { style: 'font-size:11.5px;color:#94a3b8;margin-top:3px', text: `卡包 ${me.tickets} 张 · 碎片 ${me.shards} 个` }),
      ]),
      el('button', {
        class: 'btn ghost sm', text: '去图鉴',
        onclick: () => { location.hash = '#/album'; },
      }),
    ]),
  ]));

  /* ---- 同步码 ---- */
  root.appendChild(el('section', { class: 'panel' }, [
    el('div', { style: 'font-size:13.5px;font-weight:800', text: '跨设备同步' }),
    el('div', { style: 'font-size:11.5px;color:#94a3b8;margin-top:3px;line-height:1.7', text: '在新设备输入这串码，就能接着原来的进度' }),
    el('div', {
      style: 'margin-top:12px;background:#f8fafc;border:1px dashed #cbd5e1;border-radius:11px;padding:13px;text-align:center;font-family:ui-monospace,Menlo,monospace;font-size:17px;letter-spacing:.14em;font-weight:800;color:#0f172a',
      text: me.sync_code,
    }),
    el('div', { class: 'row', style: 'margin-top:11px;gap:8px' }, [
      el('button', {
        class: 'btn ghost sm', style: 'flex:1', text: '复制同步码',
        onclick: async () => {
          try {
            await navigator.clipboard.writeText(me.sync_code);
            toast('已复制');
          } catch {
            toast('复制失败，请手动记录');
          }
        },
      }),
      el('button', {
        class: 'btn ghost sm', style: 'flex:1', text: '重置同步码',
        onclick: () => {
          openSheet(el('div', {}, [
            el('div', { style: 'font-size:13px;color:#475569;line-height:1.75', text: '重置后旧码立即失效，其他设备需要重新输入新码。' }),
            el('button', {
              class: 'btn full', style: 'margin-top:16px', text: '确认重置',
              onclick: async (e) => {
                e.currentTarget.disabled = true;
                try {
                  const r = await api.rotateCode();
                  toast(`新同步码：${r.sync_code}`, 3600);
                  document.getElementById('overlay').hidden = true;
                  const { render } = await import('../router.js');
                  render();
                } catch (err) {
                  toast(err.message || '重置失败');
                }
              },
            }),
          ]), { title: '重置同步码' });
        },
      }),
    ]),
  ]));

  /* ---- 切换账号 ---- */
  root.appendChild(el('section', { class: 'panel' }, [
    el('div', { style: 'font-size:13.5px;font-weight:800', text: '切换同步码' }),
    el('div', { style: 'font-size:11.5px;color:#94a3b8;margin-top:3px', text: '输入另一台设备的同步码，把当前设备切过去' }),
    el('button', {
      class: 'btn ghost full', style: 'margin-top:12px', text: '输入同步码',
      onclick: () => showAdoptSheet(),
    }),
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
    el('div', { style: 'font-size:10.5px;color:#94a3b8;margin-top:3px', text: label }),
  ]);
}

function ruleRows(rows) {
  return rows.map(([k, v]) => el('div', {
    style: 'display:flex;justify-content:space-between;gap:12px;padding:8px 0;border-top:1px solid #f8fafc;font-size:12px',
  }, [
    el('span', { style: 'color:#475569;font-weight:600;flex:0 0 auto', text: k }),
    el('span', { style: 'color:#94a3b8;text-align:right', text: v }),
  ]));
}

export function showAdoptSheet() {
  const input = el('input', {
    type: 'text',
    placeholder: 'XXXX-XXXX-XXXX',
    autocomplete: 'off',
    spellcheck: 'false',
    style: 'width:100%;min-height:48px;border:1.5px solid #e2e8f0;border-radius:12px;padding:0 14px;font-family:ui-monospace,Menlo,monospace;font-size:15px;letter-spacing:.1em;text-align:center;outline:none',
  });
  input.addEventListener('focus', () => { input.style.borderColor = '#93c5fd'; });
  input.addEventListener('blur', () => { input.style.borderColor = '#e2e8f0'; });

  const btn = el('button', {
    class: 'btn full', style: 'margin-top:14px', text: '切换',
    onclick: async () => {
      const code = input.value.trim();
      if (!code) { toast('请输入同步码'); return; }
      btn.disabled = true;
      btn.textContent = '验证中…';
      try {
        await api.adoptByCode(code);
        toast('已切换');
        document.getElementById('overlay').hidden = true;
        const { render } = await import('../router.js');
        render();
      } catch (err) {
        toast(err.message || '同步码无效');
        btn.disabled = false;
        btn.textContent = '切换';
      }
    },
  });

  openSheet(el('div', {}, [input, btn]), {
    title: '输入同步码',
    sub: '在原设备的「我的」页面可以找到',
  });
  setTimeout(() => input.focus(), 150);
}
