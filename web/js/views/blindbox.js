/* 盲盒：独立盲盒券抽盒、图鉴、积分换券、实物兑换 */

import * as api from '../api.js';
import { el, toast, openSheet, rarityClass } from '../ui.js';

const RARITY_LABEL = { N: 'N', R: 'R', SR: 'SR', SSR: 'SSR' };

function badge(text, cls = '') {
  return el('span', { class: `chip ${cls}`, style: 'font-size:10px;padding:2px 8px', text });
}

export async function renderBlindbox(view) {
  const data = await api.getBlindbox();
  const me = await api.fetchMe();

  const root = el('div', { class: 'stack' });

  root.appendChild(el('div', { class: 'topbar' }, [
    el('button', { class: 'back', text: '‹', onclick: () => { location.hash = '#/me'; } }),
    el('div', { style: 'flex:1' }, [
      el('h1', { text: '盲盒' }),
      el('div', { class: 'sub', text: '开出拉布布小伙伴 · 集齐可兑实物' }),
    ]),
  ]));

  /* ---- 顶部：盲盒主体 + 开盒按钮 ---- */
  const boxImg = el('img', {
    src: '/assets/blindbox/box.svg', alt: '盲盒', class: 'bb-float',
    style: 'width:150px;display:block;margin:0 auto;transition:transform .18s',
  });

  const drawBtn = el('button', { class: 'btn full', style: 'margin-top:14px', text: `🎁 开一个盲盒（${data.costs.single} 张券）` });
  const tenBtn = el('button', {
    class: 'btn ghost full', style: 'margin-top:8px',
    text: `十连开（${data.costs.ten} 张券）`,
    disabled: data.tickets < data.costs.ten,
  });

  const heroPanel = el('section', { class: 'panel', style: 'padding:18px 15px;text-align:center' }, [
    el('div', { class: 'row-between', style: 'margin-bottom:10px' }, [
      el('div', { style: 'font-size:12px;color:#a3928a', text: `盲盒券 ${data.tickets} 张` }),
      el('div', { style: 'font-size:12px;color:#a3928a', text: `已解锁 ${data.unlocked} / ${data.total}` }),
    ]),
    boxImg,
    el('div', { style: 'font-size:12px;color:#6b5b52;margin-top:10px;line-height:1.7',
      text: `距保底 SR 还需 ${data.pity.sr_left} 次 · 距 SSR 还需 ${data.pity.ssr_left} 次` }),
    drawBtn,
    tenBtn,
    el('div', { style: 'font-size:11px;color:#b6a498;margin-top:9px;line-height:1.6',
      text: `每开一次消耗 ${data.costs.single} 张盲盒券；重复角色返还盲盒券` }),
  ]);
  root.appendChild(heroPanel);

  /* ---- 券不足引导 ---- */
  if (data.tickets < data.costs.single) {
    root.appendChild(el('section', { class: 'panel', style: 'padding:13px;background:#fffbeb;border-color:#fcd34d' }, [
      el('div', { style: 'font-size:12.5px;color:#92400e;line-height:1.7',
        text: `盲盒券不够啦。去「许愿墙」提改进意见，每条 +${data.wish_bonus} 张；或用 ${data.exchange.points} 积分换 1 张。` }),
      el('div', { class: 'row', style: 'gap:8px;margin-top:10px' }, [
        el('button', { class: 'btn soft sm', style: 'flex:1', text: '💌 去许愿墙',
          onclick: () => { location.hash = '#/wishes'; } }),
        el('button', { class: 'btn sm', style: 'flex:1', text: `🔄 ${data.exchange.points} 积分换券`,
          onclick: doExchange }),
      ]),
    ]));
  }

  /* ---- 图鉴 ---- */
  root.appendChild(el('div', { class: 'section-head' }, [
    el('h3', { text: '图鉴' }),
    el('span', { class: 'hint', text: '开出过的角色永久留在图鉴里' }),
  ]));

  const grid = el('div', { class: 'bb-grid' });
  data.gallery.forEach((c) => {
    const card = el('div', { class: `bb-card ${c.unlocked ? '' : 'locked'}`, onclick: () => showCharacter(c) });
    card.appendChild(el('img', {
      src: c.image, alt: c.name, loading: 'lazy',
      style: c.unlocked ? '' : 'filter:grayscale(1) brightness(.72);opacity:.42',
    }));
    // SVG 内已自带名字：图鉴格子只补稀有度与副本数，避免重复
    if (c.unlocked) {
      card.appendChild(el('div', { class: `bb-rar ${rarityClass(c.rarity)}`, text: RARITY_LABEL[c.rarity] }));
      if (c.count > 0) card.appendChild(el('div', { class: 'bb-cnt', text: `副本 ×${c.count}` }));
    } else {
      card.appendChild(el('div', { class: 'bb-rar', style: 'background:#f1f5f9;color:#94a3b8', text: '未解锁' }));
    }
    grid.appendChild(card);
  });
  root.appendChild(grid);

  /* ---- 实物兑换区 ---- */
  const redeemables = data.gallery.filter((c) => c.count > 0);
  root.appendChild(el('div', { class: 'section-head' }, [
    el('h3', { text: '实物兑换' }),
    el('span', { class: 'hint', text: '消耗 1 个副本，得到兑现码，家长核销' }),
  ]));
  const redeemPanel = el('section', { class: 'panel', style: 'padding:13px' });
  if (!redeemables.length) {
    redeemPanel.appendChild(el('div', { style: 'font-size:12px;color:#a3928a;line-height:1.7',
      text: '还没有可兑换的副本。开出重复角色后，可在这里换成实物奖励。' }));
  } else {
    redeemables.forEach((c) => {
      redeemPanel.appendChild(el('div', { class: 'row-between', style: 'padding:8px 0;border-top:1px solid #f6ede0' }, [
        el('div', { class: 'row', style: 'gap:9px;min-width:0' }, [
          el('img', { src: c.image, alt: c.name, style: 'width:34px;height:41px;border-radius:8px;background:#fdf8f0' }),
          el('div', { style: 'min-width:0' }, [
            el('div', { style: 'font-size:12.5px;font-weight:800', text: `${c.name} ×${c.count}` }),
            el('div', { style: 'font-size:10.5px;color:#a3928a', text: `可兑 ¥${c.value_cny} · 每月每角色 1 次` }),
          ]),
        ]),
        el('button', { class: 'btn soft sm', text: '兑换', onclick: () => doRedeem(c) }),
      ]));
    });
  }
  root.appendChild(redeemPanel);

  /* ---- 玩法说明 ---- */
  root.appendChild(el('section', { class: 'panel', style: 'padding:13px' }, [
    el('div', { style: 'font-size:12px;font-weight:800;margin-bottom:6px', text: '玩法' }),
    ...[
      `开盒消耗盲盒券：单开 ${data.costs.single} 张，十连 ${data.costs.ten} 张。`,
      `概率：${Object.entries(data.rates).map(([r, v]) => `${r} ${v}%`).join(' · ')}。`,
      '重复角色按稀有度返还盲盒券；SR 与 SSR 可换实物。',
      `积分兑换：${data.exchange.points} 积分 = 1 张盲盒券，每天限 ${data.exchange.daily_limit} 次。`,
    ].map((t) => el('div', { style: 'font-size:11.5px;color:#6b5b52;line-height:1.8', text: `· ${t}` })),
  ]));

  root.appendChild(el('button', {
    class: 'btn ghost full', style: 'margin-top:4px', text: '💌 去许愿墙提意见（得盲盒券）',
    onclick: () => { location.hash = '#/wishes'; },
  }));

  view.innerHTML = '';
  view.appendChild(root);

  /* ---------- 交互 ---------- */

  async function doDraw(count) {
    drawBtn.disabled = true;
    tenBtn.disabled = true;
    boxImg.style.transform = 'rotate(-6deg) scale(1.04)';
    try {
      const res = await api.drawBlindbox(count, `${Date.now()}-${count}`);
      showDrawResult(res, () => renderBlindbox(view));
    } catch (err) {
      toast(err.message || '开盒失败');
      drawBtn.disabled = false;
      tenBtn.disabled = false;
      boxImg.style.transform = '';
    }
  }

  drawBtn.addEventListener('click', () => doDraw(1));
  tenBtn.addEventListener('click', () => doDraw(10));

  async function doExchange() {
    try {
      const res = await api.exchangeBlindbox(1);
      toast(`兑换成功，获得 1 张盲盒券`);
      renderBlindbox(view);
    } catch (err) {
      toast(err.message || '兑换失败');
    }
  }

  async function doRedeem(c) {
    openSheet(el('div', {}, [
      el('div', { style: 'font-size:12.5px;color:#5c4b42;line-height:1.8',
        text: `用 1 个「${c.name}」副本兑换 ¥${c.value_cny} 实物奖励？兑换后副本减少，图鉴仍保留。` }),
      el('button', { class: 'btn full', style: 'margin-top:14px', text: '确认兑换',
        onclick: async () => {
          try {
            const res = await api.redeemBlindbox(c.id);
            document.getElementById('overlay').hidden = true;
            showRedeemResult(res);
          } catch (err) {
            toast(err.message || '兑换失败');
          }
        } }),
      el('button', { class: 'btn ghost full', style: 'margin-top:8px', text: '取消',
        onclick: () => { document.getElementById('overlay').hidden = true; } }),
    ]), { title: '兑换实物' });
  }

  function showRedeemResult(res) {
    openSheet(el('div', { style: 'text-align:center' }, [
      el('div', { style: 'font-size:34px', text: '🎉' }),
      el('div', { style: 'font-size:14px;font-weight:800;margin-top:6px', text: `${res.name} 兑换成功` }),
      el('div', { style: 'font-size:12px;color:#6b5b52;margin-top:6px', text: `面值 ¥${res.value_cny} · 剩余副本 ${res.copies_left}` }),
      el('div', {
        style: 'font-family:ui-monospace,monospace;font-size:19px;font-weight:800;letter-spacing:.08em;' +
          'background:#f0fdf4;color:#047857;border-radius:11px;padding:13px;margin-top:14px',
        text: res.code,
      }),
      el('div', { style: 'font-size:11.5px;color:#a3928a;margin-top:9px;line-height:1.7', text: res.note }),
      el('button', { class: 'btn full', style: 'margin-top:15px', text: '知道了',
        onclick: () => { document.getElementById('overlay').hidden = true; renderBlindbox(view); } }),
    ]), { title: '兑现码' });
  }
}

/* ---------- 开盒结果（含开盒动画） ---------- */

function showDrawResult(res, onClose) {
  const grid = el('div', { class: 'bb-draw-grid' + (res.results.length > 1 ? ' ten' : '') });

  res.results.forEach((r, i) => {
    const item = el('div', { class: `bb-draw-item ${rarityClass(r.rarity)}` });
    item.style.animationDelay = `${i * 90}ms`;
    item.appendChild(el('div', { class: 'bb-spark' }));
    item.appendChild(el('img', { src: r.image, alt: r.name }));
    if (r.is_new) item.appendChild(el('div', { class: 'new-tag', text: 'NEW' }));
    item.appendChild(el('div', { class: 'bb-nm', text: r.name }));
    item.appendChild(el('div', { class: 'bb-rar ' + rarityClass(r.rarity), text: r.rarity }));
    grid.appendChild(item);
  });

  const summary = el('div', { class: 'reward-row', style: 'justify-content:center;margin-top:14px' }, [
    el('span', { class: 'reward-pill', text: `剩余盲盒券 ${res.tickets_left}` }),
    res.tickets_back > 0 ? el('span', { class: 'reward-pill', text: `重复返还 +${res.tickets_back} 券` }) : null,
    el('span', { class: 'reward-pill', text: `已解锁 ${res.unlocked}/${res.total}` }),
  ]);

  const actions = el('div', { class: 'row', style: 'gap:8px;margin-top:15px' }, [
    el('button', { class: 'btn', style: 'flex:1', text: '再开一次',
      onclick: () => { document.getElementById('overlay').hidden = true; onClose?.(); } }),
    el('button', { class: 'btn ghost', style: 'flex:1', text: '看图鉴',
      onclick: () => { document.getElementById('overlay').hidden = true; onClose?.(); } }),
  ]);

  openSheet(el('div', {}, [grid, summary, actions]), {
    title: res.results.length > 1 ? `开盒结果 · ${res.results.length} 个` : '开盒结果',
    sub: res.new_unlocks.length ? `🎉 新解锁 ${res.new_unlocks.length} 个角色` : '都是老朋友啦',
  });
}

/* ---------- 角色详情 ---------- */

function showCharacter(c) {
  if (!c.unlocked) {
    openSheet(el('div', { style: 'text-align:center;padding:10px 0' }, [
      el('img', { src: c.image, style: 'width:110px;filter:grayscale(1) brightness(.7);opacity:.4;margin:0 auto;display:block' }),
      el('div', { style: 'font-size:13px;font-weight:800;margin-top:10px', text: '还未解锁' }),
      el('div', { style: 'font-size:12px;color:#a3928a;margin-top:5px;line-height:1.7', text: '开盲盒有机会遇到它。' }),
    ]), { title: '？？？' });
    return;
  }
  openSheet(el('div', { style: 'text-align:center' }, [
    el('img', { src: c.image, style: 'width:140px;margin:0 auto;display:block' }),
    el('div', { class: 'row', style: 'justify-content:center;gap:6px;margin-top:10px' }, [
      el('span', { class: `chip ${rarityClass(c.rarity)}`, text: c.rarity }),
      el('span', { class: 'chip', text: c.accessory }),
      el('span', { class: 'chip', text: `副本 ×${c.count}` }),
    ]),
    el('div', { style: 'font-size:13px;font-weight:800;margin-top:11px', text: c.en || '' }),
    el('div', { style: 'font-size:12px;color:#0f766e;margin-top:6px', text: `「${c.quote}」` }),
    el('div', { style: 'font-size:12px;color:#6b5b52;line-height:1.8;margin-top:9px;text-align:left', text: c.story }),
    el('div', { style: 'font-size:11.5px;color:#a3928a;margin-top:10px', text: `实物兑换面值 ¥${c.value_cny}` }),
  ]), { title: c.name });
}