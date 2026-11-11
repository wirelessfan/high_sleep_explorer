/* 集卡册：图鉴、抽卡、套装 */

import * as api from '../api.js';
import { el, toast, openSheet, rarityClass } from '../ui.js';
import { navigate } from '../router.js';

const RARITY_ORDER = { SSR: 0, SR: 1, R: 2, N: 3 };

export async function renderAlbum(view) {
  const data = await api.getCards();
  const me = await api.fetchMe();

  const root = el('div', { class: 'stack' });

  root.appendChild(el('div', { style: 'padding:2px 2px 0' }, [
    el('div', { style: 'font-size:11px;letter-spacing:.16em;color:#94a3b8;font-weight:700;text-transform:uppercase', text: 'Collection' }),
    el('div', { style: 'font-size:19px;font-weight:800;letter-spacing:-.01em;margin-top:2px', text: '理科名人集卡册' }),
    el('div', { style: 'font-size:12px;color:#94a3b8;margin-top:3px', text: `已收集 ${data.owned_total} / ${data.total} · 碎片 ${data.shards}` }),
  ]));

  /* ---- 主打卡 ---- */
  const featured = data.cards.filter((c) => c.owned).sort((a, b) => RARITY_ORDER[a.rarity] - RARITY_ORDER[b.rarity])[0]
    || data.cards.find((c) => c.rarity === 'SSR');

  root.appendChild(el('section', { class: 'panel', style: 'padding:15px' }, [
    el('div', { class: 'row', style: 'gap:13px;align-items:flex-start' }, [
      featured ? el('div', {
        style: 'width:76px;flex:0 0 auto;border-radius:11px;overflow:hidden;border:1px solid #fde68a;box-shadow:0 0 0 3px #fef3c7',
      }, [
        el('img', { src: featured.image, alt: featured.name, style: 'width:100%;display:block' }),
      ]) : null,
      el('div', { style: 'flex:1;min-width:0' }, [
        el('div', { class: 'row', style: 'gap:6px;flex-wrap:wrap' }, [
          el('span', { style: 'font-size:16px;font-weight:800', text: featured ? featured.name : '还没有卡' }),
          featured ? el('span', {
            class: 'chip', style: `font-size:9.5px;padding:1px 6px;background:#fef3c7;border-color:#fcd34d;color:#92400e`,
            text: featured.rarity,
          }) : null,
        ]),
        el('div', { style: 'font-size:11px;color:#94a3b8;margin-top:3px', text: featured ? featured.en : '' }),
        el('div', { style: 'font-size:11.5px;color:#475569;line-height:1.6;margin-top:7px', text: featured ? featured.quote : '完成任务攒卡包，开出你的第一张卡' }),
      ]),
    ]),
    el('div', { class: 'row', style: 'margin-top:14px;gap:8px' }, [
      el('button', {
        class: 'btn', style: 'flex:1', text: `🎁 开卡包 (${data.tickets})`,
        onclick: () => openDrawModal(data.tickets, () => { window.dispatchEvent(new Event('album:refresh')); }),
      }),
      el('button', {
        class: 'btn ghost', text: '概率',
        onclick: () => showRates(data),
      }),
    ]),
  ]));

  /* ---- 保底条 ---- */
  root.appendChild(el('section', { class: 'panel', style: 'padding:13px' }, [
    el('div', { class: 'row-between' }, [
      el('div', {}, [
        el('div', { style: 'font-size:12px;color:#475569', text: `距保底 SR 还需 ${data.pity.sr_left} 抽` }),
        el('div', { style: 'font-size:12px;color:#475569;margin-top:3px', text: `距保底 SSR 还需 ${data.pity.ssr_left} 抽` }),
      ]),
      el('div', { class: 'row', style: 'gap:6px' }, [
        el('span', { class: 'chip', text: `碎片 ${data.shards}` }),
      ]),
    ]),
  ]));

  /* ---- 图鉴 ---- */
  root.appendChild(el('div', { class: 'section-head' }, [
    el('h3', { text: '图鉴' }),
    el('span', { class: 'hint', text: '点击卡片看详情' }),
  ]));

  const grid = el('div', { class: 'album-grid' });
  data.cards.forEach((c) => {
    const card = el('div', {
      class: `card ${c.owned ? '' : 'locked'}`,
      style: 'cursor:pointer',
      onclick: () => showCardDetail(c, data),
    }, [
      el('div', { class: 'art' }, [
        el('span', { class: `rar ${rarityClass(c.rarity)}`, text: c.rarity }),
        c.owned ? el('img', { src: c.image, alt: c.name, loading: 'lazy' }) : el('div', { class: 'q', text: '?' }),
      ]),
      el('div', { class: 'meta' }, [
        el('div', { class: 'nm', text: c.owned ? c.name : '？？？' }),
        el('div', { class: 'en', text: c.owned ? c.en : 'locked' }),
        el('div', { class: 'cnt', text: c.owned ? (c.count > 1 ? `×${c.count}` : '已收录') : `碎片 ${data.craft_cost[c.rarity]} 可兑换` }),
      ]),
    ]);
    grid.appendChild(card);
  });
  root.appendChild(grid);

  /* ---- 套装 ---- */
  root.appendChild(el('div', { class: 'section-head' }, [
    el('h3', { text: '套装' }),
    el('span', { class: 'hint', text: '集齐发徽章 + 50 积分' }),
  ]));

  for (const s of data.sets) {
    root.appendChild(el('div', { class: `set-row ${s.done ? 'done' : ''}`, style: 'margin-bottom:8px' }, [
      el('div', { class: 'row-between' }, [
        el('div', { class: 't', text: s.name }),
        el('div', { style: 'font-size:10.5px;font-weight:800;color:#94a3b8', text: `${s.count}/${s.total}${s.done ? ' ✓' : ''}` }),
      ]),
      el('div', { class: 'bar' }, [
        el('i', { style: `width:${Math.round(s.count / s.total * 100)}%` }),
      ]),
      el('div', { class: 'p', text: s.cards.map((cid) => {
        const c = data.cards.find((x) => x.id === cid);
        return c?.name || cid;
      }).join(' + ') }),
    ]));
  }

  view.innerHTML = '';
  view.appendChild(root);
}

/* ---------- 概率说明 ---------- */

function showRates(data) {
  const rows = Object.entries(data.rates).map(([r, p]) =>
    el('div', { class: 'row-between', style: 'padding:9px 0;border-bottom:1px solid #f1f5f9' }, [
      el('span', { class: `chip ${rarityClass(r)}`, style: 'color:#fff;border:0;font-size:10.5px', text: r }),
      el('span', { style: 'font-size:13px;font-weight:700', text: `${p}%` }),
      el('span', { style: 'font-size:11.5px;color:#94a3b8', text: `重复转 ${data.craft_cost[r] === 10 ? 1 : data.craft_cost[r] === 25 ? 2 : data.craft_cost[r] === 60 ? 4 : 8} 碎片` }),
    ])
  );

  openSheet(el('div', {}, [
    ...rows,
    el('div', {
      style: 'margin-top:14px;font-size:12px;color:#475569;line-height:1.8;background:#f8fafc;border-radius:10px;padding:12px',
    }, [
      el('div', { text: `· 单抽消耗 1 张卡包，十连消耗 9 张（9 折）` }),
      el('div', { text: `· 累计 ${data.pity.pity_sr} 抽未出 SR，下一抽必出 SR 及以上` }),
      el('div', { text: `· 累计 ${data.pity.pity_ssr} 抽未出 SSR，下一抽必出 SSR` }),
      el('div', { text: '· 重复卡自动转碎片，碎片可定向兑换' }),
    ]),
  ]), { title: '抽卡概率', sub: '保底计数在抽到对应稀有度后重置' });
}

/* ---------- 卡片详情 ---------- */

function showCardDetail(c, data) {
  if (!c.owned) {
    openSheet(el('div', {}, [
      el('div', { style: 'text-align:center;padding:10px 0 4px' }, [
        el('div', { style: 'font-size:40px;opacity:.3', text: '🔒' }),
        el('div', { style: 'font-size:14px;font-weight:800;margin-top:8px', text: '尚未解锁' }),
        el('div', { style: 'font-size:12px;color:#94a3b8;margin-top:5px', text: `稀有度 ${c.rarity} · 可通过开卡包或碎片兑换获得` }),
      ]),
      el('button', {
        class: 'btn full', style: 'margin-top:16px',
        text: `用碎片兑换（${data.craft_cost[c.rarity]}）`,
        disabled: data.shards < data.craft_cost[c.rarity],
        onclick: async (e) => {
          const btn = e.currentTarget;
          btn.disabled = true;
          try {
            const res = await api.craftCard(c.id);
            toast(`兑换成功：${res.name}`);
            document.getElementById('overlay').hidden = true;
            const { render } = await import('../router.js');
            render();
          } catch (err) {
            toast(err.message || '兑换失败');
            btn.disabled = false;
          }
        },
      }),
    ]), { title: '未解锁', sub: c.rarity });
    return;
  }

  openSheet(el('div', {}, [
    el('div', { class: 'row', style: 'gap:13px;align-items:flex-start' }, [
      el('div', {
        style: 'width:96px;flex:0 0 auto;border-radius:11px;overflow:hidden;border:1px solid #e8edf3',
      }, [el('img', { src: c.image, alt: c.name })]),
      el('div', { style: 'flex:1;min-width:0' }, [
        el('div', { class: 'row', style: 'gap:6px;flex-wrap:wrap' }, [
          el('span', { style: 'font-size:17px;font-weight:800', text: c.name }),
          el('span', { class: `rar ${rarityClass(c.rarity)}`, style: 'position:static;font-size:9px', text: c.rarity }),
        ]),
        el('div', { style: 'font-size:10.5px;color:#94a3b8;letter-spacing:.08em;text-transform:uppercase;margin-top:3px', text: c.en }),
        el('div', { style: 'font-size:11px;color:#94a3b8;margin-top:3px', text: c.life }),
        el('div', { style: 'font-size:12px;color:#475569;line-height:1.65;margin-top:8px;border-left:2px solid #f59e0b;padding-left:9px', text: c.quote }),
      ]),
    ]),
    detailRow('关键贡献', c.contribution),
    detailRow('课本对应', c.textbook),
    detailRow('冷知识', c.trivia),
    el('button', {
      class: 'btn soft full', style: 'margin-top:14px', text: '去学对应知识点 →',
      onclick: () => {
        document.getElementById('overlay').hidden = true;
        navigate(`#/topic/${c.topic}/${c.section}`);
      },
    }),
  ]), { title: '人物卡详情', sub: `已收录 ×${c.count}` });
}

function detailRow(k, v) {
  return el('div', { style: 'display:flex;gap:10px;padding:10px 0;border-top:1px solid #f1f5f9;font-size:12.5px;line-height:1.65' }, [
    el('div', { style: 'flex:0 0 58px;color:#94a3b8;font-size:11.5px', text: k }),
    el('div', { style: 'color:#334155;flex:1', text: v }),
  ]);
}

/* ---------- 抽卡 ---------- */

function openDrawModal(tickets, onDone) {
  if (tickets < 1) {
    openSheet(el('div', {}, [
      el('div', { style: 'text-align:center;padding:16px 0' }, [
        el('div', { style: 'font-size:36px', text: '🎟' }),
        el('div', { style: 'font-size:14px;font-weight:800;margin-top:8px', text: '卡包不够了' }),
        el('div', { style: 'font-size:12px;color:#94a3b8;margin-top:6px;line-height:1.7', text: '完成主题可获 2 张卡包，通关 Boss 再得 1 张' }),
      ]),
      el('button', {
        class: 'btn full', style: 'margin-top:10px', text: '去学习',
        onclick: () => {
          document.getElementById('overlay').hidden = true;
          navigate('#/subjects');
        },
      }),
    ]), { title: '开卡包' });
    return;
  }

  const holder = el('div');
  const { close } = openSheet(holder, {
    title: `开卡包 · 剩余 ${tickets} 张`,
    sub: '单抽 1 张，十连 9 张',
  });

  function renderChoice() {
    holder.innerHTML = '';
    holder.appendChild(el('div', { class: 'row', style: 'gap:9px' }, [
      el('button', {
        class: 'btn', style: 'flex:1',
        text: '单抽 (1)',
        onclick: () => doDraw(1),
      }),
      el('button', {
        class: 'btn ghost', style: 'flex:1',
        text: `十连 (9)`,
        disabled: tickets < 9,
        onclick: () => doDraw(10),
      }),
    ]));
    holder.appendChild(el('div', {
      style: 'margin-top:14px;font-size:11.5px;color:#94a3b8;line-height:1.7;text-align:center',
      text: 'SR 12% · SSR 3% · 10 抽保底 SR · 40 抽保底 SSR',
    }));
  }

  async function doDraw(count) {
    holder.innerHTML = '';
    holder.appendChild(el('div', { style: 'text-align:center;padding:30px 0' }, [
      el('div', { style: 'font-size:34px', text: '🎁' }),
      el('div', { style: 'font-size:13px;color:#94a3b8;margin-top:10px', text: '开启中…' }),
    ]));

    try {
      const key = `${Date.now()}-${count}`;
      const res = await api.drawCards(count, key);
      showDrawResult(holder, res, close, onDone, count);
    } catch (err) {
      toast(err.message || '抽卡失败');
      renderChoice();
    }
  }

  renderChoice();
}

function showDrawResult(holder, res, close, onDone, count) {
  holder.innerHTML = '';

  const grid = el('div', { class: `draw-grid ${count === 10 ? 'ten' : ''}` });
  const cardsData = res.results;

  // 需要卡面图：从图鉴数据拿。这里用已知路径约定
  cardsData.forEach((r) => {
    grid.appendChild(el('div', { class: 'draw-item card', style: 'position:relative' }, [
      el('div', { class: 'art' }, [
        el('span', { class: `rar ${rarityClass(r.rarity)}`, text: r.rarity }),
        r.is_new ? el('span', { class: 'new-tag', text: 'NEW' }) : null,
        el('img', { src: `/assets/cards/${r.card_id}.jpg`, alt: r.name }),
      ]),
      el('div', { class: 'meta' }, [
        el('div', { class: 'nm', text: r.name }),
        el('div', { class: 'cnt', text: r.is_new ? '首次收录' : `+${r.shards} 碎片` }),
      ]),
    ]));
  });

  holder.appendChild(grid);

  const summary = el('div', {
    style: 'margin-top:14px;font-size:12px;color:#475569;text-align:center;line-height:1.8',
  }, [
    el('div', { text: `新卡 ${res.new_cards.length} 张${res.shards_gained ? ` · 碎片 +${res.shards_gained}` : ''}` }),
    el('div', { style: 'color:#94a3b8;font-size:11px', text: `剩余卡包 ${res.tickets_left} · 碎片 ${res.shards_total}` }),
  ]);
  holder.appendChild(summary);

  if (res.set_awards?.length) {
    res.set_awards.forEach((a) => {
      holder.appendChild(el('div', {
        class: 'reward-pill', style: 'margin:10px auto 0;display:flex;justify-content:center',
        text: `🏅 套装达成：${a.set} +${a.points} 积分`,
      }));
    });
  }

  const action = el('div', { class: 'row', style: 'gap:9px;margin-top:16px' }, [
    el('button', {
      class: 'btn ghost', style: 'flex:1', text: '看图鉴',
      onclick: () => { close(); onDone?.(); },
    }),
    el('button', {
      class: 'btn', style: 'flex:1', text: '再开一次',
      disabled: res.tickets_left < 1,
      onclick: () => { close(); onDone?.(); setTimeout(() => openDrawModal(res.tickets_left, onDone), 120); },
    }),
  ]);
  holder.appendChild(action);
}
