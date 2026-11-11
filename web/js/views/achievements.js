/* 成就卡：积分兑换、兑现码、核销 */

import * as api from '../api.js';
import { el, toast, openSheet } from '../ui.js';

let lastRedeemed = null;

export async function renderAchievements(view) {
  const data = await api.getAchievements();
  const st = data.stats;

  const root = el('div', { class: 'stack' });

  root.appendChild(el('div', { class: 'topbar' }, [
    el('button', { class: 'back', text: '‹', onclick: () => { location.hash = '#/me'; } }),
    el('div', { style: 'flex:1' }, [
      el('h1', { text: '成就卡' }),
      el('div', { class: 'sub', text: `${st.points_per_card} 积分 = 1 张 ${st.value_cny} 元卡` }),
    ]),
  ]));

  /* ---- 今日进度 ---- */
  const todayPct = Math.round((st.today_count / Math.max(1, st.daily_limit)) * 100);
  root.appendChild(el('section', { class: 'panel', style: 'background:linear-gradient(150deg,#fffbf0,#fff);border-color:#fbe6b8' }, [
    el('div', { class: 'row-between' }, [
      el('div', {}, [
        el('div', { style: 'font-size:11px;letter-spacing:.16em;color:#b08954;font-weight:700;text-transform:uppercase', text: 'Today' }),
        el('div', { style: 'font-size:19px;font-weight:800;margin-top:3px', text: `今天已兑 ${st.today_count} / ${st.daily_limit} 张` }),
      ]),
      el('div', { style: 'text-align:right' }, [
        el('div', { style: 'font-size:23px;font-weight:800;color:#b45309;font-variant-numeric:tabular-nums', text: `¥${st.today_value}` }),
        el('div', { style: 'font-size:10.5px;color:#b08954;margin-top:2px', text: '今日已获得' }),
      ]),
    ]),
    el('div', { style: 'height:6px;background:#f6ede0;border-radius:99px;margin-top:13px;overflow:hidden' }, [
      el('i', { style: `display:block;height:100%;width:${todayPct}%;border-radius:99px;background:linear-gradient(90deg,#fbbf24,#f59e0b)` }),
    ]),
    el('div', {
      style: 'display:flex;justify-content:space-between;margin-top:8px;font-size:11px;color:#a3928a',
    }, [
      el('span', { text: `剩余额度 ${st.today_left} 张` }),
      el('span', { text: `累计已兑 ¥${st.total_value}` }),
    ]),
  ]));

  /* ---- 兑换面板 ---- */
  const body = el('section', { class: 'panel stack', style: 'gap:13px' });
  const canCount = Math.min(st.today_left, Math.floor(data.points / st.points_per_card));
  const afford = data.points >= st.points_per_card;

  let count = Math.min(1, Math.max(0, canCount));

  const summaryLine = el('div', {
    style: 'font-size:12.5px;color:#6b5b52;line-height:1.7',
  });
  const btn = el('button', {
    class: 'btn full',
    text: '兑换',
    onclick: async () => {
      if (count < 1) return;
      btn.disabled = true;
      btn.textContent = '兑换中…';
      try {
        const res = await api.redeemAchievement(count);
        lastRedeemed = res.cards;
        toast(`成功兑换 ${res.count} 张，共 ${res.cards[0].value_cny * res.count} 元`);
        showRedeemedSheet(res.cards, res.points, async () => {
          const { render } = await import('../router.js');
          render();
        });
      } catch (err) {
        toast(err.message || '兑换失败');
        btn.disabled = false;
        btn.textContent = '兑换';
      }
    },
  });

  function paint() {
    body.innerHTML = '';

    body.appendChild(el('div', { class: 'row-between' }, [
      el('div', {}, [
        el('div', { style: 'font-size:13.5px;font-weight:800', text: '我的积分' }),
        el('div', { style: 'font-size:11px;color:#a3928a;margin-top:2px', text: '学习、签到、闯关都会累积' }),
      ]),
      el('div', { style: 'font-size:24px;font-weight:800;color:#b45309;font-variant-numeric:tabular-nums', text: `${data.points}` }),
    ]));

    // 数量选择
    if (canCount > 0) {
      const opts = el('div', { class: 'row', style: 'gap:7px' });
      for (let n = 1; n <= Math.min(canCount, 3); n++) {
        opts.appendChild(el('button', {
          class: `chip ${n === count ? 'solid' : ''}`,
          style: 'min-height:34px;font-size:12px;padding:0 14px;cursor:pointer',
          text: `${n} 张 · ¥${n * st.value_cny}`,
          onclick: () => { count = n; paint(); },
        }));
      }
      body.appendChild(el('div', {}, [
        el('div', { style: 'font-size:11.5px;color:#a3928a;margin-bottom:7px', text: '兑换张数' }),
        opts,
      ]));
    }

    summaryLine.innerHTML = '';
    if (!afford) {
      const need = st.points_per_card - data.points;
      summaryLine.appendChild(el('div', {
        text: `还差 ${need} 积分。完成一个主题约 115 分，或明天签到后再来。`,
      }));
    } else if (st.today_left <= 0) {
      summaryLine.appendChild(el('div', {
        text: `今天已兑满 ${st.daily_limit} 张（上限 ${st.daily_limit * st.value_cny} 元）。明天继续。`,
      }));
    } else {
      summaryLine.appendChild(el('div', {
        text: `将消耗 ${count * st.points_per_card} 积分，兑换 ${count * st.value_cny} 元。兑换后积分不退回。`,
      }));
    }
    body.appendChild(summaryLine);

    btn.disabled = canCount < 1;
    btn.textContent = canCount < 1
      ? (afford ? '今日额度已用完' : '积分不足')
      : `兑换 ${count} 张 · ¥${count * st.value_cny}`;
    body.appendChild(btn);
  }

  paint();
  root.appendChild(body);

  /* ---- 我的成就卡 ---- */
  root.appendChild(el('div', { class: 'section-head' }, [
    el('h3', { text: '我的成就卡' }),
    el('span', { class: 'hint', text: `共 ${st.total_count} 张 · ¥${st.total_value}` }),
  ]));

  if (!data.cards.length) {
    root.appendChild(el('div', {
      style: 'text-align:center;padding:30px 18px;color:#a3928a;font-size:12.5px',
      text: '还没有成就卡。攒够 100 积分就能换第一张。',
    }));
  } else {
    for (const c of data.cards) {
      const isRedeemed = c.status === 'redeemed';
      root.appendChild(el('div', {
        style: `border:1px solid ${isRedeemed ? '#f0e4d4' : '#fbe6b8'};background:${isRedeemed ? '#fffdf8' : 'linear-gradient(135deg,#fffbf0,#fff)'};border-radius:14px;padding:13px;opacity:${isRedeemed ? '.72' : '1'}`,
      }, [
        el('div', { class: 'row-between' }, [
          el('div', { class: 'row', style: 'gap:9px' }, [
            el('div', {
              style: `width:38px;height:38px;border-radius:11px;display:grid;place-items:center;font-size:16px;font-weight:800;background:${isRedeemed ? '#f6ede0' : '#fef3c7'};color:#b45309`,
              text: `¥${c.value_cny}`,
            }),
            el('div', {}, [
              el('div', {
                style: 'font-family:ui-monospace,Menlo,monospace;font-size:13.5px;font-weight:800;letter-spacing:.06em;color:#3b2f2a',
                text: c.code,
              }),
              el('div', { style: 'font-size:10.5px;color:#a3928a;margin-top:3px', text: c.created_at }),
            ]),
          ]),
          el('span', {
            class: 'chip',
            style: isRedeemed
              ? 'background:#f6ede0;border-color:#e8d9c4;color:#a3928a;font-size:10px'
              : 'background:#ecfdf5;border-color:#a7f3d0;color:#047857;font-size:10px',
            text: isRedeemed ? '已兑现' : '待兑现',
          }),
        ]),
      ]));
    }
  }

  /* ---- 说明 ---- */
  root.appendChild(el('section', { class: 'panel', style: 'padding:14px' }, [
    el('div', { style: 'font-size:12.5px;font-weight:800;margin-bottom:8px', text: '规则' }),
    ...[
      [`${st.points_per_card} 积分 = 1 张 ${st.value_cny} 元成就卡`],
      [`每天最多兑 ${st.daily_limit} 张（${st.daily_limit * st.value_cny} 元）`],
      ['兑换后积分立即扣除，不退回'],
      ['把兑现码交给家长/老师，对方付钱后标记已兑现'],
      ['同一个码只能核销一次'],
    ].map(([t]) => el('div', {
      style: 'font-size:12px;color:#6b5b52;line-height:1.85;display:flex;gap:7px',
    }, [el('span', { style: 'color:#f59e0b', text: '·' }), el('span', { text: t })])),
  ]));

  view.innerHTML = '';
  view.appendChild(root);
}

/* ---------- 兑换成功弹层 ---------- */

export function showRedeemedSheet(cards, pointsLeft, onClose) {
  const list = el('div', { class: 'stack', style: 'gap:9px' });
  cards.forEach((c) => {
    list.appendChild(el('div', {
      style: 'border:1.5px dashed #fbbf24;background:linear-gradient(135deg,#fffbeb,#fff);border-radius:13px;padding:15px;text-align:center',
    }, [
      el('div', { style: 'font-size:11px;color:#b08954;letter-spacing:.14em;font-weight:700', text: 'ACHIEVEMENT CARD' }),
      el('div', { style: 'font-size:30px;font-weight:800;color:#b45309;margin-top:7px', text: `¥${c.value_cny}` }),
      el('div', {
        style: 'font-family:ui-monospace,Menlo,monospace;font-size:16px;font-weight:800;letter-spacing:.1em;color:#3b2f2a;margin-top:9px',
        text: c.code,
      }),
      el('div', { style: 'font-size:11px;color:#a3928a;margin-top:7px', text: '把这个码交给家长/老师兑现' }),
    ]));
  });

  const close = el('button', {
    class: 'btn full', style: 'margin-top:15px', text: '收好了',
    onclick: () => {
      document.getElementById('overlay').hidden = true;
      onClose?.();
    },
  });

  openSheet(el('div', {}, [
    el('div', { style: 'text-align:center;font-size:13px;color:#047857;font-weight:700;margin-bottom:13px', text: `兑换成功 · 剩余 ${pointsLeft} 积分` }),
    list,
    close,
  ]), { title: '你获得了成就卡', sub: '同一个码只能核销一次' });
}
