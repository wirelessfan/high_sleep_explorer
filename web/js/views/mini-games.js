/* 小游戏厅：砸金蛋 / 幸运转盘 / 扑克对决的玩法与视觉节奏
 * 安全版：不花券、不计分、无真钱、无排行榜；奖励只是动物贴纸 */

import * as api from '../api.js';
import { el, openSheet, toast } from '../ui.js';
import { ANIMAL_CARDS, pickPhysicalPrize, awardPhysicalPrize } from './relax-gacha.js';
import { loadStudyBonus, effectiveSrWeight, effectivePrizeRate, bonusPanel } from './study-bonus.js';
import { loadQuota, useQuota, quotaPanel } from './daily-quota.js';

const STORAGE_PREFIX = 'learn.mini-games.v1.';
const RARITY_WEIGHT = { N: 70, R: 28, SR: 2 };

/* 扑克牌对决：只比较牌型，不涉及金钱；游戏积分只存在本机，不加学习积分。 */
const POKER_VALUES = [2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14];
const POKER_SUITS = ['♠', '♥', '♣', '♦'];
const RANK_TEXT = { 11: 'J', 12: 'Q', 13: 'K', 14: 'A' };
const HAND_NAMES = ['单个', '对子', '顺子', '豹子'];
const HAND_POINTS = [10, 20, 100, 300];  // 赢到的「开心积分」，与学习积分无关

/* 砸金蛋的小鸡：普通/银色/金色三档，5 进制进位。
 * 5 普通 → 1 银色；5 银色 → 1 金色。金色每次出现（直接砸出或进位得到）都送一次实体奖券抽奖。
 * 直接砸出金色的概率复用学习加成后的实体券爆率（基础 6%，封顶 30%），银色 18%，其余普通。 */
const CHICKS = [
  { id: 'chick-gold', name: '金色小鸡', emoji: '🐥', rarity: 'SSR', note: '传说中的金色小鸡，附赠一张实体奖券！', tier: 'gold' },
  { id: 'chick-silver', name: '银色小鸡', emoji: '🐤', rarity: 'SR', note: '闪着银光，超级幸运！', tier: 'silver' },
  { id: 'chick-normal', name: '普通小鸡', emoji: '🐣', rarity: 'N', note: '毛茸茸的小可爱，今天也要开心。', tier: 'normal' },
];
const CHICK_SILVER_RATE = 0.18;
const TIER_CARRY = 5;  // 5 只低一档进位成 1 只高一档（小鸡、小老虎通用）

/* 幸运转盘：四档小老虎，按扇区份数计分；进位仍按 5 普通→银、5 银→金。 */
const TIGERS = [
  { id: 'tiger-gold', name: '金色小老虎', emoji: '🐯', rarity: 'SSR', note: '威风凛凛的金色小老虎，附赠一张实体奖券！', tier: 'gold', score: 20, color: '#fcd34d', labelColor: '#78350f' },
  { id: 'tiger-silver', name: '银色小老虎', emoji: '🐯', rarity: 'SR', note: '闪着银光的小老虎，超级幸运！', tier: 'silver', score: 5, color: '#cbd5e1', labelColor: '#334155' },
  { id: 'tiger-bronze', name: '铜色小老虎', emoji: '🐯', rarity: 'R', note: '铜光闪闪，也很可爱！', tier: 'bronze', score: 2, color: '#c2703d', labelColor: '#fff' },
  { id: 'tiger-normal', name: '普通小老虎', emoji: '🐯', rarity: 'N', note: '毛茸茸的小老虎，今天也要开心。', tier: 'normal', score: 1, color: '#fdba74', labelColor: '#7c2d12' },
];
/* 16 份穿插排列：普通5 / 铜5 / 银4 / 金2；相邻档位不重复。 */
const WHEEL_LAYOUT = [
  'bronze', 'normal', 'silver', 'bronze',
  'normal', 'gold', 'silver', 'bronze',
  'normal', 'bronze', 'silver', 'normal',
  'gold', 'bronze', 'silver', 'normal',
];

function freshState() {
  return {
    collection: {}, chicks: {}, tigers: {}, points: 0,
    plays: { egg: 0, wheel: 0, slot: 0 }, history: [],
  };
}

function loadState(who) {
  try {
    const raw = JSON.parse(localStorage.getItem(STORAGE_PREFIX + who) || 'null');
    if (!raw || typeof raw !== 'object') return freshState();
    return {
      collection: raw.collection && typeof raw.collection === 'object' ? raw.collection : {},
      chicks: raw.chicks && typeof raw.chicks === 'object' ? raw.chicks : {},
      tigers: raw.tigers && typeof raw.tigers === 'object' ? raw.tigers : {},
      points: Number(raw.points) || 0,
      plays: Object.assign(freshState().plays, raw.plays && typeof raw.plays === 'object' ? raw.plays : {}),
      history: Array.isArray(raw.history) ? raw.history.slice(0, 30) : [],
    };
  } catch {
    return freshState();
  }
}

function saveState(who, state) {
  try { localStorage.setItem(STORAGE_PREFIX + who, JSON.stringify(state)); } catch { /* 隐私模式忽略 */ }
}

function pickReward(boost = false, srWeight = RARITY_WEIGHT.SR) {
  const rarities = boost ? ['SR', 'SSR'] : ['N', 'R', 'SR'];
  const weights = boost ? [80, 20] : [RARITY_WEIGHT.N, RARITY_WEIGHT.R, srWeight];
  let hit = Math.random() * weights.reduce((a, b) => a + b, 0);
  let rarity = rarities[rarities.length - 1];
  for (let i = 0; i < rarities.length; i++) {
    hit -= weights[i];
    if (hit <= 0) { rarity = rarities[i]; break; }
  }
  const pool = ANIMAL_CARDS.filter((c) => c.rarity === rarity);
  return pool[Math.floor(Math.random() * pool.length)];
}

/* ---- 扑克牌牌型：豹子 > 顺子 > 对子 > 单个 ---- */
function randomCard() {
  const value = POKER_VALUES[Math.floor(Math.random() * POKER_VALUES.length)];
  const suit = POKER_SUITS[Math.floor(Math.random() * POKER_SUITS.length)];
  return { value, suit, label: `${RANK_TEXT[value] || value}${suit}` };
}

function isStraight(values) {
  if (values[0] === 2 && values[1] === 3 && values[2] === 14) return true;  // A-2-3
  return values[1] === values[0] + 1 && values[2] === values[1] + 1;
}

function handInfo(cards) {
  const values = cards.map((c) => c.value).sort((a, b) => a - b);
  const counts = {};
  values.forEach((v) => { counts[v] = (counts[v] || 0) + 1; });
  const triple = Number(Object.keys(counts).find((v) => counts[v] === 3) || 0);
  const pairs = Object.keys(counts).filter((v) => counts[v] === 2).map(Number);
  let category = 0;
  let key = [...values].sort((a, b) => b - a);
  if (triple) {
    category = 3; key = [triple];
  } else if (isStraight(values)) {
    category = 2; key = [values[0] === 2 ? 3 : values[2]];
  } else if (pairs.length) {
    category = 1; key = [pairs[0], ...values.filter((v) => v !== pairs[0]).sort((a, b) => b - a)];
  }
  return { category, name: HAND_NAMES[category], key, cards };
}

/** >0 玩家赢，<0 AI 赢，0 平局。 */
function compareHands(a, b) {
  if (a.category !== b.category) return a.category - b.category;
  for (let i = 0; i < Math.max(a.key.length, b.key.length); i++) {
    const x = a.key[i] || 0, y = b.key[i] || 0;
    if (x !== y) return x - y;
  }
  return 0;
}

export async function renderMiniGames(view) {
  const me = await api.fetchMe();
  const who = String(me.username || me.nickname || 'guest').toLowerCase();
  let state = loadState(who);
  const bonus = await loadStudyBonus();
  const srWeight = effectiveSrWeight(bonus);
  const goldRate = effectivePrizeRate(bonus);  // 金色小鸡 = 实体券级大奖概率
  let quota = await loadQuota();
  let current = 'egg';
  let timers = [];
  let intervals = [];

  /** 玩一次前先消耗额度；失败返回 false 并刷新页面提示。 */
  async function takeTurn() {
    if (!quota || quota.remaining < 1) {
      toast('今天的抽奖次数用完了，明天再来吧');
      return false;
    }
    const used = await useQuota(1);
    if (used.quota) quota = used.quota;
    if (!used.ok) { paint(current); return false; }
    return true;
  }

  function clearJobs() {
    timers.forEach(clearTimeout);
    intervals.forEach(clearInterval);
    timers = [];
    intervals = [];
  }
  function later(fn, ms) { const id = setTimeout(fn, ms); timers.push(id); return id; }

  function reward(card, game) {
    state.collection[card.id] = (state.collection[card.id] || 0) + 1;
    if (game) state.plays[game] = (state.plays[game] || 0) + 1;
    state.history.unshift({ id: card.id, name: card.name, emoji: card.emoji, rarity: card.rarity, at: Date.now() });
    state.history = state.history.slice(0, 30);
    saveState(who, state);
  }

  /** 小鸡 / 小老虎同款概率；转盘可覆盖为更低的金/银命中率。 */
  function pickTier(tiers, { gold = goldRate, silver = CHICK_SILVER_RATE } = {}) {
    const r = Math.random();
    if (r < gold) return tiers[0];
    if (r < gold + silver) return tiers[1];
    return tiers[2];
  }

  /** 通用 5 进制进位；返回最终档位、进位步骤、金色出现次数。 */
  function rewardTier(collectionKey, tiers, picked, game) {
    const bag = state[collectionKey];
    bag[picked.id] = (bag[picked.id] || 0) + 1;
    state.plays[game] = (state.plays[game] || 0) + 1;
    state.history.unshift({ id: picked.id, name: picked.name, emoji: picked.emoji, rarity: picked.rarity, at: Date.now() });

    const gold = tiers.find((t) => t.tier === 'gold');
    const silver = tiers.find((t) => t.tier === 'silver');
    const normal = tiers.find((t) => t.tier === 'normal');
    const steps = [];
    let golds = picked.tier === 'gold' ? 1 : 0;

    while ((bag[normal.id] || 0) >= TIER_CARRY) {
      bag[normal.id] -= TIER_CARRY;
      bag[silver.id] = (bag[silver.id] || 0) + 1;
      steps.push(`${normal.emoji} ×${TIER_CARRY} → ${silver.emoji} ${silver.name}`);
      state.history.unshift({ id: silver.id, name: silver.name, emoji: silver.emoji, rarity: silver.rarity, at: Date.now() });
    }
    while ((bag[silver.id] || 0) >= TIER_CARRY) {
      bag[silver.id] -= TIER_CARRY;
      bag[gold.id] = (bag[gold.id] || 0) + 1;
      steps.push(`${silver.emoji} ×${TIER_CARRY} → ${gold.emoji} ${gold.name}`);
      state.history.unshift({ id: gold.id, name: gold.name, emoji: gold.emoji, rarity: gold.rarity, at: Date.now() });
      golds += 1;
    }

    state.history = state.history.slice(0, 30);
    saveState(who, state);
    return { base: picked, golds, steps, final: golds ? gold : (steps.length ? silver : picked) };
  }

  /** 小鸡/小老虎通用的开奖弹窗；金色每次出现都展示实体奖券。 */
  function showTierReward(got, prizes, { label = '小鸡', goldTitle = '🎉 金色小鸡！', againText = '再玩一次', extraText = '' } = {}) {
    let dismiss = () => {};
    const againBtn = el('button', { class: 'btn', text: againText, onclick: () => { dismiss(); clearJobs(); paint(current); } });
    const closeBtn = el('button', { class: 'btn ghost', text: '收好啦', onclick: () => dismiss() });
    const item = got.final;
    const gold = item.tier === 'gold';
    const children = [
      el('div', { class: `mg-chick mg-chick-${item.tier}`, text: item.emoji }),
      el('div', { style: 'font-size:16px;font-weight:800;margin-top:2px', text: item.name }),
      el('span', { class: `rg-rar rar-${item.rarity}`, style: 'margin-top:8px', text: `${item.rarity} · ${gold ? `大奖${label}` : `${label}收藏`}` }),
      el('div', { style: 'font-size:12.5px;color:#6b5b52;line-height:1.8;margin-top:12px', text: item.note }),
    ];
    if (got.steps.length) {
      children.push(el('div', {
        style: 'margin-top:10px;padding:8px 10px;border-radius:10px;background:#fff7ed;color:#9a3412;font-size:11.5px;font-weight:700;line-height:1.8',
      }, got.steps.map((s) => el('div', { text: `✨ ${s}` }))));
    }
    if (extraText) {
      children.push(el('div', { style: 'font-size:11.5px;color:#6b5b52;margin-top:10px', text: extraText }));
    }
    if (gold && prizes.length) {
      children.push(el('div', { class: 'pg-drop-banner', style: 'margin-top:14px' }, [
        el('div', { class: 'pg-drop-title', text: '🎉 附赠实体奖券！' }),
        el('div', { class: 'pg-drop-sub', text: `${prizes.map((p) => `${p.emoji} ${p.name}`).join(' · ')} · 已存入抽卡站` }),
        el('div', { class: 'pg-drop-note', text: '快去「动物抽卡站」查看，找爸爸妈妈兑换' }),
      ]));
    }
    children.push(el('div', { class: 'row', style: 'gap:9px;margin-top:16px' }, [againBtn, closeBtn]));
    dismiss = openSheet(el('div', { style: 'text-align:center' }, children), {
      title: gold ? goldTitle : (got.steps.length ? `✨ ${label}进位啦！` : '开到啦！'),
      sub: gold ? '金色出现就送实体奖券，手气太棒啦' : (got.steps.length ? `攒够 ${TIER_CARRY} 只，成功进位` : `收进${label}收藏册`),
    }).close;
  }

  function showReward(card, { title = '收获一张贴纸', sub = '收进贴纸册啦' } = {}) {
    let dismiss = () => {};
    const againBtn = el('button', { class: 'btn', text: '再玩一次', onclick: () => { dismiss(); clearJobs(); paint(current); } });
    const closeBtn = el('button', { class: 'btn ghost', text: '收好啦', onclick: () => dismiss() });
    dismiss = openSheet(el('div', { style: 'text-align:center' }, [
      el('div', { class: 'mg-reward-emoji', text: card.emoji }),
      el('div', { style: 'font-size:16px;font-weight:800;margin-top:2px', text: card.name }),
      el('span', { class: `rg-rar rar-${card.rarity}`, style: 'margin-top:8px', text: `${card.rarity} · 动物贴纸` }),
      el('div', { style: 'font-size:12.5px;color:#6b5b52;line-height:1.8;margin-top:12px', text: card.quote }),
      el('div', { class: 'row', style: 'gap:9px;margin-top:16px' }, [againBtn, closeBtn]),
    ]), { title, sub }).close;
  }

  function collectedPanel() {
    const owned = ANIMAL_CARDS.filter((c) => state.collection[c.id]);
    return el('section', { class: 'panel', style: 'padding:13px;margin-top:18px' }, [
      el('div', { class: 'row-between' }, [
        el('div', { style: 'font-size:12.5px;font-weight:800', text: '我的贴纸册' }),
        el('span', { class: 'hint', text: `${owned.length}/${ANIMAL_CARDS.length}` }),
      ]),
      el('div', { class: 'mg-collected' }, owned.length
        ? owned.map((c) => el('span', {
            class: 'mg-owned', title: `${c.name} ×${state.collection[c.id]}`,
            text: `${c.emoji} ×${state.collection[c.id]}`,
          }))
        : [el('span', { class: 'hint', text: '玩一局，第一张贴纸就来了' })]),
    ]);
  }

  function tierPanel(collectionKey, tiers, heading) {
    const bag = state[collectionKey];
    const owned = tiers.reduce((n, c) => n + (bag[c.id] || 0), 0);
    const normal = tiers.find((t) => t.tier === 'normal');
    const silver = tiers.find((t) => t.tier === 'silver');
    const gold = tiers.find((t) => t.tier === 'gold');
    return el('section', { class: 'panel', style: 'padding:13px;margin-top:10px' }, [
      el('div', { class: 'row-between' }, [
        el('div', { style: 'font-size:12.5px;font-weight:800', text: heading }),
        el('span', { class: 'hint', text: `当前持有 ${owned} 只` }),
      ]),
      el('div', { class: 'mg-chick-collection' }, tiers.map((c) => {
        const count = bag[c.id] || 0;
        return el('div', { class: `mg-chick-item ${count ? '' : 'locked'} mg-chick-${c.tier}` }, [
          el('div', { class: 'mg-chick-item-emoji', text: count ? c.emoji : '❔' }),
          el('div', { class: 'mg-chick-item-name', text: count ? c.name : '还没转到' }),
          el('div', { class: 'mg-chick-item-count', text: count ? `×${count}` : '—' }),
        ]);
      })),
      el('div', { style: 'font-size:10.5px;color:#a3928a;margin-top:9px;line-height:1.7',
        text: `${TIER_CARRY} 进制进位：${normal.emoji} ×${TIER_CARRY} → ${silver.name}；${silver.emoji} ×${TIER_CARRY} → ${gold.name}。金色每次出现都附赠一张实体奖券。` }),
    ]);
  }
  const chickPanel = () => tierPanel('chicks', CHICKS, '🐥 小鸡收藏册');
  const tigerPanel = () => tierPanel('tigers', TIGERS, '🐯 小老虎收藏册');

  function eggPanel() {
    const eggs = [];
    const row = el('div', { class: 'mg-egg-row' });
    for (let i = 0; i < 3; i++) {
      const egg = el('div', { class: 'mg-egg', role: 'button', tabindex: '0', 'aria-label': `砸第 ${i + 1} 个蛋` }, [
        el('div', { class: 'mg-egg-body' }),
        el('div', { class: 'mg-egg-face', text: '?' }),
      ]);
      egg.addEventListener('click', () => smash(egg));
      egg.addEventListener('keydown', (e) => { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); smash(egg); } });
      eggs.push(egg);
      row.appendChild(egg);
    }

    async function smash(egg) {
      if (eggs.some((e) => e.classList.contains('busy'))) return;
      if (!await takeTurn()) return;
      eggs.forEach((e) => e.classList.add('busy'));
      egg.classList.add('crack');
      later(() => {
        const got = rewardTier('chicks', CHICKS, pickTier(CHICKS), 'egg');
        const face = egg.querySelector('.mg-egg-face');
        face.textContent = got.final.emoji;
        face.className = `mg-egg-face mg-chick-${got.final.tier}`;
        egg.classList.remove('crack');
        egg.classList.add('opened');
        // 每次金色出现（直接砸出或进位得到）都伴随一次实体奖券抽奖。
        const prizes = [];
        for (let i = 0; i < got.golds; i++) {
          const prize = awardPhysicalPrize(who, pickPhysicalPrize());
          if (prize) prizes.push(prize);
        }
        showTierReward(got, prizes, { label: '小鸡', goldTitle: '🎉 金色小鸡！', againText: '再砸一次' });
        later(() => paint('egg'), prizes.length ? 2200 : 1600);
      }, 600);
    }

    return el('section', { class: 'panel', style: 'padding:16px 15px;text-align:center' }, [
      el('div', { class: 'row-between' }, [
        el('span', { class: 'chip', text: '🥚 砸金蛋' }),
        el('span', { class: 'hint', text: `已玩 ${state.plays.egg || 0} 次` }),
      ]),
      el('div', { style: 'font-size:19px;font-weight:800;margin:14px 0 2px', text: '选一个蛋砸开！' }),
      el('div', { style: 'font-size:11.5px;color:#d97706;font-weight:700', text: '🐥 金色小鸡是大奖，附赠一张实体奖券' }),
      el('div', { style: 'font-size:11px;color:#a3928a;margin-top:3px', text: '三个蛋都一样，随便挑一个 · 🐣×5→🐤 · 🐤×5→🐥' }),
      row,
      el('div', { style: 'font-size:11px;color:#b6a498;margin-top:12px;line-height:1.7',
        text: (!quota || quota.remaining < 1)
          ? '今天的抽奖次数用完啦，明天再来砸蛋吧。'
          : '每次砸消耗 1 次今日额度；金 🐥 / 银 🐤 / 普通 🐣 三种小鸡，攒够 5 只自动进位；金色每次出现都送实体奖券。' }),
    ]);
  }

  function wheelPanel() {
    const step = 360 / WHEEL_LAYOUT.length;
    const gradient = `conic-gradient(from -90deg, ${WHEEL_LAYOUT
      .map((tier, i) => {
        const t = TIGERS.find((x) => x.tier === tier);
        return `${t.color} ${i * step}deg ${(i + 1) * step}deg`;
      }).join(',')})`;
    const rotor = el('div', { class: 'mg-wheel-rotor', style: `background:${gradient}` });
    WHEEL_LAYOUT.forEach((tier, i) => {
      const t = TIGERS.find((x) => x.tier === tier);
      const angle = i * step + step / 2;
      rotor.appendChild(el('span', {
        class: `mg-wheel-label mg-chick-${t.tier}`,
        style: `color:${t.labelColor};text-shadow:${t.labelColor === '#fff' ? '0 1px 2px rgba(0,0,0,.45)' : 'none'};transform:translate(-50%,-50%) rotate(${angle}deg) translateY(-68px) rotate(${-angle}deg)`,
        text: t.emoji,
      }));
    });

    const goBtn = el('button', {
      class: 'mg-wheel-center', text: 'GO', 'aria-label': '转动转盘',
      disabled: !quota || quota.remaining < 1,
    });
    goBtn.addEventListener('click', spin);

    const wheel = el('div', { class: 'mg-wheel' }, [
      el('div', { class: 'mg-pointer' }),
      rotor,
      goBtn,
    ]);

    async function spin() {
      if (goBtn.disabled) return;
      if (!await takeTurn()) return;
      goBtn.disabled = true;
      const index = Math.floor(Math.random() * WHEEL_LAYOUT.length);
      const picked = TIGERS.find((t) => t.tier === WHEEL_LAYOUT[index]);
      rotor.style.transform = `rotate(${360 * 8 - (index * step + step / 2)}deg)`;
      later(() => {
        state.points = (state.points || 0) + (picked.score || 0);
        const got = rewardTier('tigers', TIGERS, picked, 'wheel');
        // 金色每次出现（直接转到或进位得到）都送一次实体奖券抽奖。
        const prizes = [];
        for (let i = 0; i < got.golds; i++) {
          const prize = awardPhysicalPrize(who, pickPhysicalPrize());
          if (prize) prizes.push(prize);
        }
        const card = pickReward(picked.tier === 'gold', srWeight);
        reward(card, null);  // 次数已由 rewardTier 计入，这里只收贴纸
        showTierReward(got, prizes, {
          label: '小老虎', goldTitle: '🎉 金色小老虎！', againText: '再转一次',
          extraText: `⭐ 开心积分 +${picked.score}（当前 ${state.points}） · 🎁 动物贴纸：${card.emoji} ${card.name}`,
        });
        later(() => paint('wheel'), prizes.length ? 2200 : 1600);
      }, 3250);
    }

    return el('section', { class: 'panel', style: 'padding:16px 15px;text-align:center' }, [
      el('div', { class: 'row-between' }, [
        el('span', { class: 'chip', text: '🎡 幸运转盘' }),
        el('span', { class: 'hint', text: `开心积分 ${state.points || 0}` }),
      ]),
      el('div', { style: 'font-size:11px;color:#a3928a;margin-top:4px', text: `已玩 ${state.plays.wheel || 0} 次 · 16 格穿插排列` }),
      el('div', { style: 'font-size:19px;font-weight:800;margin:14px 0 2px', text: '转到一只小老虎！' }),
      el('div', { style: 'font-size:11.5px;color:#b45309;font-weight:800', text: '普通 1 分 · 铜 2 分 · 银 5 分 · 金 20 分' }),
      el('div', { style: 'font-size:11px;color:#a3928a;margin-top:3px', text: `🐯×${TIER_CARRY}→银色 · 银×${TIER_CARRY}→金色；金色还送实体奖券` }),
      wheel,
      el('button', {
        class: 'btn full', style: 'margin-top:14px', text: '🎡 转动转盘',
        disabled: !quota || quota.remaining < 1, onclick: spin,
      }),
      el('div', { style: 'font-size:11px;color:#b6a498;margin-top:10px;line-height:1.7',
        text: '16 格按份数穿插：普通 5、铜 5、银 4、金 2。每次按落点加开心积分（只存本机，不影响学习积分），并送一张动物贴纸；金色每次出现都送实体奖券。' }),
    ]);
  }

  function pokerHandRow(title, cards, info, winner) {
    return el('div', {
      style: `margin-top:9px;padding:8px;border-radius:12px;border:1px solid ${winner ? '#fde68a' : '#ede9fe'};background:${winner ? '#fffbeb' : '#faf5ff'}`,
    }, [
      el('div', { style: `font-size:11.5px;font-weight:900;color:${winner ? '#b45309' : '#6d28d9'}`, text: title }),
      el('div', { class: 'mg-reels', style: 'margin:6px 0 3px' }, cards.map((c) => el('div', {
        class: 'mg-reel mg-card',
        style: (c.suit === '♥' || c.suit === '♦') ? 'color:#dc2626' : '',
        text: c.label,
      }))),
      el('div', { style: 'font-size:10.5px;color:#a3928a', text: `${info.name} · ${cards.map((c) => c.label).join(' ')}` }),
    ]);
  }

  function showPokerResult({ myCards, aiCards, myInfo, aiInfo, outcome, gained, card, prize, points }) {
    let dismiss = () => {};
    const againBtn = el('button', { class: 'btn', text: '再来一局', onclick: () => { dismiss(); clearJobs(); paint('slot'); } });
    const closeBtn = el('button', { class: 'btn ghost', text: '收好啦', onclick: () => dismiss() });
    const win = outcome === 'win';
    const children = [
      pokerHandRow('🙂 我', myCards, myInfo, win),
      pokerHandRow('🤖 AI 小助手', aiCards, aiInfo, outcome === 'lose'),
      el('div', { style: 'font-size:10.5px;color:#a3928a;margin-top:9px', text: '牌型大小：豹子 > 顺子 > 对子 > 单个' }),
      el('div', { style: 'font-size:12px;font-weight:800;color:#7c2d12;margin-top:7px',
        text: win
          ? `你赢了！开心积分 +${gained}（当前 ${points}）`
          : (outcome === 'lose' ? `AI 赢了，你的牌型是${myInfo.name}，下次再来！` : `平局，都是${myInfo.name}，开心积分不变`) }),
      el('div', { style: 'font-size:11.5px;color:#6b5b52;margin-top:7px', text: `🎁 同时获得动物贴纸：${card.emoji} ${card.name}` }),
    ];
    if (prize) {
      children.push(el('div', { class: 'pg-drop-banner', style: 'margin-top:12px' }, [
        el('div', { class: 'pg-drop-title', text: '🎉 大奖触发实体抽奖！' }),
        el('div', { class: 'pg-drop-sub', text: `${prize.emoji} ${prize.name} · 已存入抽卡站` }),
        el('div', { class: 'pg-drop-note', text: '快去「动物抽卡站」查看，找爸爸妈妈兑换' }),
      ]));
    }
    children.push(el('div', { class: 'row', style: 'gap:9px;margin-top:15px' }, [againBtn, closeBtn]));
    dismiss = openSheet(el('div', { style: 'text-align:center' }, children), {
      title: win ? '🎉 你赢啦！' : (outcome === 'lose' ? '🤖 AI 这局更厉害' : '🤝 平局'),
      sub: `你的${myInfo.name} VS AI 的${aiInfo.name} · 同时开牌`,
    }).close;
  }

  function slotPanel() {
    const myReels = [0, 1, 2].map(() => el('div', { class: 'mg-reel', text: '🃏' }));
    const aiReels = [0, 1, 2].map(() => el('div', { class: 'mg-reel', text: '🃏' }));
    const spinBtn = el('button', {
      class: 'btn full', style: 'margin-top:14px', text: '🃏 同时开牌',
      disabled: !quota || quota.remaining < 1,
    });
    const pointChip = el('span', { class: 'hint', text: `开心积分 ${state.points || 0}` });
    const hint = el('div', { style: 'font-size:11px;color:#b6a498;margin-top:10px;line-height:1.7',
      text: '每次开牌消耗 1 次今日额度；你和 AI 同时亮牌，豹子 > 顺子 > 对子 > 单个。赢到顺子或豹子，开心积分大增并立即抽一张实体奖券。' });

    async function spin() {
      if (spinBtn.disabled) return;
      if (!await takeTurn()) return;
      spinBtn.disabled = true;
      const allReels = [...myReels, ...aiReels];
      allReels.forEach((r) => r.classList.add('spinning'));
      const localIntervals = allReels.map((r) => {
        const id = setInterval(() => {
          const c = randomCard();
          r.textContent = c.label;
          r.style.color = (c.suit === '♥' || c.suit === '♦') ? '#dc2626' : '';
        }, 80);
        intervals.push(id);
        return id;
      });

      // 两行同一时刻停牌，做到「同时开奖」。
      [700, 1000, 1300].forEach((ms, i) => {
        later(() => {
          [myReels[i], aiReels[i]].forEach((r) => {
            clearInterval(localIntervals[allReels.indexOf(r)]);
            r.classList.remove('spinning');
          });
        }, ms);
      });

      later(() => {
        const myCards = [randomCard(), randomCard(), randomCard()];
        const aiCards = [randomCard(), randomCard(), randomCard()];
        [myReels, aiReels].forEach((reels, row) => {
          const cards = row === 0 ? myCards : aiCards;
          cards.forEach((c, i) => {
            reels[i].textContent = c.label;
            reels[i].style.color = (c.suit === '♥' || c.suit === '♦') ? '#dc2626' : '';
          });
        });
        const myInfo = handInfo(myCards);
        const aiInfo = handInfo(aiCards);
        const cmp = compareHands(myInfo, aiInfo);
        const outcome = cmp > 0 ? 'win' : (cmp < 0 ? 'lose' : 'draw');
        let gained = 0;
        let prize = null;
        if (outcome === 'win') {
          gained = HAND_POINTS[myInfo.category];
          state.points = (state.points || 0) + gained;
          // 顺子 / 豹子赢：积分大增 + 直接实体抽奖（中性记录，不消耗额度）。
          if (myInfo.category >= 2) prize = awardPhysicalPrize(who, pickPhysicalPrize());
        }
        state.plays.slot = (state.plays.slot || 0) + 1;
        const card = pickReward(myInfo.category === 3, srWeight);
        reward(card, null);
        showPokerResult({ myCards, aiCards, myInfo, aiInfo, outcome, gained, card, prize, points: state.points });
        later(() => paint('slot'), prize ? 2600 : 1800);
      }, 1450);
    }
    spinBtn.addEventListener('click', spin);

    return el('section', { class: 'panel', style: 'padding:16px 15px;text-align:center' }, [
      el('div', { class: 'row-between' }, [
        el('span', { class: 'chip', text: '🃏 扑克对决' }),
        pointChip,
      ]),
      el('div', { style: 'font-size:11px;color:#a3928a;margin-top:4px', text: `已玩 ${state.plays.slot || 0} 次 · 豹子 > 顺子 > 对子 > 单个` }),
      el('div', { style: 'font-size:19px;font-weight:800;margin:14px 0 2px', text: '你和 AI 同时亮三张牌！' }),
      el('div', { style: 'font-size:11.5px;color:#d97706;font-weight:700', text: '顺子 / 豹子赢 → 积分大增 + 实体奖券' }),
      el('div', { style: 'font-size:11.5px;font-weight:800;margin-top:12px', text: '🙂 我' }),
      el('div', { class: 'mg-reels', style: 'margin-top:5px' }, myReels),
      el('div', { style: 'font-size:11.5px;font-weight:800;margin-top:10px', text: '🤖 AI 小助手（同时开牌）' }),
      el('div', { class: 'mg-reels', style: 'margin-top:5px' }, aiReels),
      spinBtn,
      hint,
    ]);
  }

  function paint(game = current) {
    current = game;
    clearJobs();
    const root = el('div', { class: 'stack' });

    root.appendChild(el('div', { class: 'topbar' }, [
      el('button', { class: 'back', text: '‹', onclick: () => { if (history.length > 1) history.back(); else location.hash = '#/me'; } }),
      el('div', { style: 'flex:1' }, [
        el('h1', { text: '休闲游戏广场' }),
        el('div', { class: 'sub', text: '放松一下 · 想玩就玩' }),
      ]),
    ]));

    root.appendChild(quotaPanel(quota));

    root.appendChild(bonusPanel(bonus, {
      note: `学习越活跃、成就卡越多，越容易抽到稀有贴纸（当前 SR 权重 ${srWeight}）。加成不消耗积分。`,
    }));

    root.appendChild(el('div', { class: 'mg-tabs' }, [
      ...[
        { id: 'egg', text: '🥚 砸金蛋' },
        { id: 'wheel', text: '🎡 幸运转盘' },
        { id: 'slot', text: '🃏 扑克对决' },
      ].map((t) => el('button', {
        class: `mg-tab ${t.id === game ? 'active' : ''}`,
        text: t.text,
        onclick: () => paint(t.id),
      })),
      el('button', { class: 'mg-tab link', text: '🐾 动物抽卡', onclick: () => { location.hash = '#/relax'; } }),
    ]));

    root.appendChild(game === 'egg' ? eggPanel() : game === 'wheel' ? wheelPanel() : slotPanel());
    if (game === 'egg') root.appendChild(chickPanel());
    if (game === 'wheel') root.appendChild(tigerPanel());
    root.appendChild(collectedPanel());

    root.appendChild(el('section', { class: 'panel', style: 'padding:13px;margin-top:10px' }, [
      el('div', { style: 'font-size:12px;font-weight:800;margin-bottom:6px', text: '关于这里' }),
      el('div', { class: 'hint', style: 'line-height:1.8',
        text: '这里的游戏只借用视觉和玩法：没有筹码、充值、提现、输赢金额，也不计入学习积分。收获的动物贴纸、小鸡/小老虎收藏册和「开心积分」只保存在当前浏览器。' }),
      el('div', { class: 'hint', style: 'line-height:1.8;margin-top:4px',
        text: '每次玩消耗 1 次抽奖额度，与动物抽卡共用；平日 10 次，疯狂星期六、周日和节假日 20 次，当日学习积分每 10 分再送 1 次。次数由服务端记录，清缓存不会重置。' }),
      el('div', { class: 'hint', style: 'line-height:1.8;margin-top:4px',
        text: '砸金蛋出小鸡；幸运转盘 16 格穿插四档小老虎（普通 1 分 / 铜 2 分 / 银 5 分 / 金 20 分），5 普通→银、5 银→金；金色每次出现都附赠实体奖券。扑克对决和 AI 同时亮牌，按豹子 > 顺子 > 对子 > 单个比较，顺子/豹子赢时开心积分大增并立即抽实体奖券。开心积分只存本机；实体奖券记在「动物抽卡站」，真实奖品由爸爸妈妈决定兑现。' }),
    ]));

    view.innerHTML = '';
    view.appendChild(root);
  }

  paint();
  return clearJobs;
}
