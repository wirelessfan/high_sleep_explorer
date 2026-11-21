/* 放松抽卡：原创动物卡池 + 实体奖励心愿券；无消耗、无付款，存档只在本机浏览器
 * 实体券只是记录，真实奖品由家长线下决定与兑现 */

import * as api from '../api.js';
import { el, toast, openSheet } from '../ui.js';
import { loadStudyBonus, effectivePrizeRate, bonusPanel } from './study-bonus.js';
import { loadQuota, useQuota, usePrizeQuota, quotaPanel } from './daily-quota.js';

const STORAGE_PREFIX = 'learn.relax-gacha.v1.';
const RARITY_ORDER = { N: 0, R: 1, SR: 2, SSR: 3 };
const RARITY_LABEL = { N: '普通', R: '稀有', SR: '超稀有', SSR: '传说' };
const RATES = [
  { rarity: 'SSR', weight: 3 },
  { rarity: 'SR', weight: 12 },
  { rarity: 'R', weight: 30 },
  { rarity: 'N', weight: 55 },
];
const PITY_R = 10;
const PITY_SR = 40;
const HISTORY_LIMIT = 30;

/* 实体奖励券：仅作“心愿券”记录，真实奖品由爸爸妈妈线下决定与兑现。
 * 单抽掉率 6%，十连按 10 次独立判定；抽到后在“我的实体券”里可标记已兑换。 */
const PRIZE_DROP_RATE = 0.06;
export const PHYSICAL_PRIZES = [
  { id: 'p-mai-dong', name: '脉动饮料', emoji: '🥤', rarity: 'N', weight: 20, note: '运动完来一瓶，补充能量' },
  { id: 'p-an-mu-xi', name: '安慕希牛奶', emoji: '🥛', rarity: 'N', weight: 20, note: '早餐好搭档' },
  { id: 'p-tang-hu-lu', name: '糖葫芦一串', emoji: '🍡', rarity: 'N', weight: 18, note: '酸酸甜甜的童年味道' },
  { id: 'p-hershey', name: '好时巧克力', emoji: '🍫', rarity: 'R', weight: 12, note: '小小一块，甜到心里' },
  { id: 'p-ferrero', name: '费列罗巧克力', emoji: '🍬', rarity: 'R', weight: 10, note: '金灿灿的，舍不得吃' },
  { id: 'p-kao-yu', name: '烤鱼套餐', emoji: '🐟', rarity: 'SR', weight: 8, note: '今晚加个鸡腿……哦不，加条鱼' },
  { id: 'p-hai-di-lao', name: '海底捞火锅', emoji: '🍲', rarity: 'SR', weight: 7, note: '热气腾腾，全家人一起涮' },
  { id: 'p-mystery', name: '神秘心愿', emoji: '🌟', rarity: 'SSR', weight: 5, note: '抽中了，告诉爸爸妈妈你的心愿吧' },
];
const PRIZE_BY_ID = {};
PHYSICAL_PRIZES.forEach((p) => { PRIZE_BY_ID[p.id] = p; });

/* 16 张原创动物卡：只用 emoji 展示，不引用任何外部素材或 IP */
export const ANIMAL_CARDS = [
  { id: 'cotton-rabbit', name: '棉花兔', emoji: '🐰', rarity: 'N', quote: '软乎乎的一天，从发呆开始。' },
  { id: 'orange-cat', name: '橘子猫', emoji: '🐱', rarity: 'N', quote: '晒到太阳的尾巴尖，是甜的。' },
  { id: 'bean-dog', name: '豆包狗', emoji: '🐶', rarity: 'N', quote: '你走到哪儿，它就跟到哪儿。' },
  { id: 'glutinous-hamster', name: '糯米仓鼠', emoji: '🐹', rarity: 'N', quote: '腮帮子鼓鼓的，装着小小快乐。' },
  { id: 'chirp-chick', name: '小鸡啾', emoji: '🐥', rarity: 'N', quote: '啾一声，就算打过招呼啦。' },
  { id: 'bamboo-panda', name: '竹子熊', emoji: '🐼', rarity: 'N', quote: '慢慢啃竹子，慢慢长大。' },
  { id: 'sleepy-koala', name: '瞌睡考拉', emoji: '🐨', rarity: 'N', quote: '困了就抱紧树干，睡一会儿。' },
  { id: 'bubble-fish', name: '泡泡鱼', emoji: '🐠', rarity: 'N', quote: '把烦恼吹成泡泡，看着它飘走。' },
  { id: 'little-fox', name: '小狐狸', emoji: '🦊', rarity: 'R', quote: '机灵的小主意，一箩筐。' },
  { id: 'slow-sloth', name: '树懒慢慢', emoji: '🦥', rarity: 'R', quote: '慢一点也没关系，树会等你。' },
  { id: 'penguin-puff', name: '企鹅噗噗', emoji: '🐧', rarity: 'R', quote: '排队跳进海里，扑通！' },
  { id: 'dango-dog', name: '柴犬团子', emoji: '🐕', rarity: 'R', quote: '笑起来像一团刚蒸好的馒头。' },
  { id: 'shiny-otter', name: '水獭闪闪', emoji: '🦦', rarity: 'R', quote: '石头上敲贝壳，叮叮当当。' },
  { id: 'rainbow-unicorn', name: '彩虹独角兽', emoji: '🦄', rarity: 'SR', quote: '雨停之后，它踩着颜色过来。' },
  { id: 'tiny-dino', name: '小恐龙喷喷', emoji: '🦖', rarity: 'SR', quote: '吼一声，其实只是想玩。' },
  { id: 'cloud-whale', name: '云朵鲸鱼', emoji: '🐋', rarity: 'SSR', quote: '游过夜空，把好梦撒下来。' },
];

const POOL = {};
ANIMAL_CARDS.forEach((c) => { (POOL[c.rarity] = POOL[c.rarity] || []).push(c); });

/* 合成阶梯（与服务端 EXCHANGE_RULES 保持一致）：3 张 N 券换 1 张自选 R 券，2 张 R 券换 1 张自选 SR 券。 */
const EXCHANGE_RULES = { R: { cost: 3, from: 'N' }, SR: { cost: 2, from: 'R' } };

function freshState() {
  return { counts: {}, history: [], pityR: 0, pitySr: 0, total: 0,
    prizes: {}, prizeHistory: [] };
}

function stateKey(who) {
  return STORAGE_PREFIX + who;
}

function normalize(raw) {
  if (!raw || typeof raw !== 'object') return freshState();
  return {
    counts: raw.counts && typeof raw.counts === 'object' ? raw.counts : {},
    history: Array.isArray(raw.history) ? raw.history.slice(0, HISTORY_LIMIT) : [],
    pityR: Number.isInteger(raw.pityR) && raw.pityR >= 0 ? raw.pityR : 0,
    pitySr: Number.isInteger(raw.pitySr) && raw.pitySr >= 0 ? raw.pitySr : 0,
    total: Number.isInteger(raw.total) && raw.total >= 0 ? raw.total : 0,
    prizes: raw.prizes && typeof raw.prizes === 'object' ? raw.prizes : {},
    prizeHistory: Array.isArray(raw.prizeHistory) ? raw.prizeHistory.slice(0, HISTORY_LIMIT) : [],
  };
}

function loadState(who) {
  try {
    return normalize(JSON.parse(localStorage.getItem(stateKey(who)) || 'null'));
  } catch {
    return freshState();
  }
}

function saveState(who, state) {
  try { localStorage.setItem(stateKey(who), JSON.stringify(state)); } catch { /* 隐私模式忽略 */ }
}

function rollRarity(state, mult = 1) {
  // 学习加成只抬 R/SR/SSR 权重，N 固定不动：加成越高，稀有伙伴越容易出现。
  const k = mult - 1;
  const scaled = RATES.map((row) => row.rarity === 'R' ? row.weight * (1 + k * 0.25)
    : row.rarity === 'SR' ? row.weight * (1 + k * 0.5)
    : row.rarity === 'SSR' ? row.weight * (1 + k * 0.8) : row.weight);
  const hit = Math.random() * scaled.reduce((a, b) => a + b, 0);
  let acc = 0;
  let rarity = 'N';
  for (let i = 0; i < RATES.length; i++) {
    acc += scaled[i];
    if (hit < acc) { rarity = RATES[i].rarity; break; }
  }
  if (state.pitySr + 1 >= PITY_SR && RARITY_ORDER[rarity] < 2) rarity = 'SR';
  else if (state.pityR + 1 >= PITY_R && RARITY_ORDER[rarity] < 1) rarity = 'R';
  return rarity;
}

function pickCard(rarity, exclude) {
  const pool = POOL[rarity] || POOL.N;
  let card = pool[Math.floor(Math.random() * pool.length)];
  for (let i = 0; i < 5 && exclude.has(card.id) && pool.length > 1; i++) {
    card = pool[Math.floor(Math.random() * pool.length)];
  }
  return card;
}

function rollPrize(rate = PRIZE_DROP_RATE) {
  if (Math.random() >= rate) return null;
  const total = PHYSICAL_PRIZES.reduce((a, p) => a + p.weight, 0);
  let hit = Math.random() * total;
  for (const p of PHYSICAL_PRIZES) {
    hit -= p.weight;
    if (hit <= 0) return p;
  }
  return PHYSICAL_PRIZES[PHYSICAL_PRIZES.length - 1];
}

/* SR/SSR 大餐券每日首张保真：同日再出的自动降级为 R 级券，家长预算节奏可控。 */
const SR_PRIZE_DAILY_CAP = 1;

function srPrizesToday(state) {
  const start = new Date();
  start.setHours(0, 0, 0, 0);
  return state.prizeHistory.filter((h) =>
    (h.rarity === 'SR' || h.rarity === 'SSR') && Number(h.at) >= start.getTime()).length;
}

function downgradeIfCapped(prize, state) {
  if (!prize) return null;
  if ((prize.rarity === 'SR' || prize.rarity === 'SSR') && srPrizesToday(state) >= SR_PRIZE_DAILY_CAP) {
    const pool = PHYSICAL_PRIZES.filter((p) => p.rarity === 'R');
    return pool[Math.floor(Math.random() * pool.length)];
  }
  return prize;
}

/* 实体奖专属抽卡：必出一张券。学习加成越高，稀有券权重越高。 */
function pickGuaranteedPrize(bonus) {
  const mult = Math.max(1, Number(bonus?.total) || 1);
  const weights = PHYSICAL_PRIZES.map((p) => {
    const k = p.rarity === 'SSR' ? 1 + (mult - 1) * 0.8
      : p.rarity === 'SR' ? 1 + (mult - 1) * 0.5
      : p.rarity === 'R' ? 1 + (mult - 1) * 0.25 : 1;
    return Math.max(0.01, p.weight * k);
  });
  const total = weights.reduce((a, b) => a + b, 0);
  let hit = Math.random() * total;
  for (let i = 0; i < PHYSICAL_PRIZES.length; i++) {
    hit -= weights[i];
    if (hit <= 0) return PHYSICAL_PRIZES[i];
  }
  return PHYSICAL_PRIZES[PHYSICAL_PRIZES.length - 1];
}

/* 供游戏广场（金色小鸡）调用：按权重随机抽一张实体券，并写入抽卡页同一份存档。
 * 这样砸出的金色小鸡真正「等效实体卡奖项」，在 #/relax 的实体券图鉴里能看到。 */
export function pickPhysicalPrize() {
  return rollPrize(1);
}

export function awardPhysicalPrize(who, prize) {
  if (!prize) return null;
  const state = loadState(who);
  prize = downgradeIfCapped(prize, state);
  if (!prize) return null;
  const at = Date.now();
  const first = !state.prizes[prize.id];
  state.prizes[prize.id] = (state.prizes[prize.id] || 0) + 1;
  state.prizeHistory.unshift({
    id: prize.id, name: prize.name, emoji: prize.emoji,
    rarity: prize.rarity, isNew: first, at,
  });
  state.prizeHistory = state.prizeHistory.slice(0, HISTORY_LIMIT);
  try { localStorage.setItem(stateKey(who), JSON.stringify(state)); } catch { /* 隐私模式忽略 */ }
  // 服务端回写：存档快照 + 台账（client_key 用奖品 id + 时间戳，天然幂等）。
  try {
    api.putGachaState(JSON.stringify(state)).catch(() => {});
    api.postPrizeLedger([{ prize_id: prize.id, client_key: `p:${prize.id}:${at}` }]).catch(() => {});
  } catch { /* 离线忽略，本机记录仍在 */ }
  return { ...prize, isNew: first, at };
}

function draw(state, count, prizeRate = PRIZE_DROP_RATE, mult = 1) {
  const results = [];
  const prizes = [];
  const exclude = new Set();
  for (let i = 0; i < count; i++) {
    const rarity = rollRarity(state, mult);
    const card = pickCard(rarity, exclude);
    exclude.add(card.id);
    const isNew = !state.counts[card.id];
    state.counts[card.id] = (state.counts[card.id] || 0) + 1;
    state.total += 1;
    state.pityR = RARITY_ORDER[rarity] >= 1 ? 0 : state.pityR + 1;
    state.pitySr = RARITY_ORDER[rarity] >= 2 ? 0 : state.pitySr + 1;
    const at = Date.now() + i;
    results.push({ ...card, isNew, at });

    // 实体券：独立判定，与动物卡的稀有度/保底互不影响
    const prize = downgradeIfCapped(rollPrize(prizeRate), state);
    if (prize) {
      const first = !state.prizes[prize.id];
      state.prizes[prize.id] = (state.prizes[prize.id] || 0) + 1;
      prizes.push({ ...prize, isNew: first, at });
      state.prizeHistory.unshift({
        id: prize.id, name: prize.name, emoji: prize.emoji,
        rarity: prize.rarity, isNew: first, at,
      });
    }
  }
  state.history = state.history.slice(0, HISTORY_LIMIT);
  state.prizeHistory = state.prizeHistory.slice(0, HISTORY_LIMIT);
  return { cards: results, prizes };
}

function cardTile(card, { locked = false, showCount = false, pop = false } = {}) {
  const shownRarity = locked ? 'N' : card.rarity;
  const cls = ['rg-card', `rar-${shownRarity}`];
  if (locked) cls.push('locked');
  if (pop) cls.push('pop');
  const children = [
    el('div', { class: 'rg-emoji', text: locked ? '❔' : card.emoji }),
    el('div', { class: 'rg-name', text: locked ? '还没遇见' : card.name }),
    el('span', { class: `rg-rar rar-${shownRarity}`, text: locked ? '???' : card.rarity }),
  ];
  if (!locked && card.isNew) children.push(el('span', { class: 'rg-new', text: 'NEW' }));
  if (!locked && showCount) children.push(el('div', { class: 'rg-count', text: `已有 ×${card.counts || 0}` }));
  return el('div', { class: cls.join(' ') }, children);
}

function prizeTile(prize, { locked = false, count = 0, pop = false } = {}) {
  const cls = ['pg-tile', `rar-${prize.rarity}`];
  if (locked) cls.push('locked');
  if (pop) cls.push('pop');
  return el('div', { class: cls.join(' ') }, [
    el('div', { class: 'pg-emoji', text: locked ? '🎁' : prize.emoji }),
    el('div', { class: 'pg-name', text: locked ? '还没抽到' : prize.name }),
    locked ? null : el('div', { class: 'pg-count', text: `×${count}` }),
  ]);
}

export async function renderRelaxGacha(view) {
  const me = await api.fetchMe();
  const who = String(me.username || me.nickname || 'guest').toLowerCase();
  let state = loadState(who);
  let bonus = await loadStudyBonus();
  let quota = await loadQuota();
  let drawing = false;
  let ledger = [];        // 服务端台账（含核销状态）；拉取失败时退回本机记录
  let ledgerReady = false;

  /* 服务端存档优先：清缓存/换设备不丢收集进度；服务端还没有时回填本机存档。 */
  async function syncServerState() {
    try {
      const remote = await api.getGachaState();
      if (remote?.data) {
        state = normalize(JSON.parse(remote.data));
        saveState(who, state);
      } else {
        await api.putGachaState(JSON.stringify(state));
      }
      paint();
    } catch { /* 离线或未登录：继续用本机存档 */ }
  }

  async function loadLedger() {
    try {
      const res = await api.getMyLedger();
      ledger = Array.isArray(res?.items) ? res.items : [];
      ledgerReady = true;
      paint();
    } catch { ledgerReady = false; }
  }

  function saveAndSync(newPrizes = []) {
    saveState(who, state);
    try { api.putGachaState(JSON.stringify(state)).catch(() => {}); } catch { /* 忽略 */ }
    if (newPrizes.length) {
      try {
        const entries = newPrizes
          .filter((p) => p && p.id)
          .map((p) => ({ prize_id: p.id, client_key: `p:${p.id}:${p.at}` }));
        if (entries.length) api.postPrizeLedger(entries).then(() => loadLedger()).catch(() => {});
      } catch { /* 忽略 */ }
    }
  }

  syncServerState();
  loadLedger();

  function paint() {
    const unlocked = ANIMAL_CARDS.filter((c) => state.counts[c.id]).length;
    const prizeOwned = PHYSICAL_PRIZES.filter((p) => state.prizes[p.id]).length;
    const prizeTotal = Object.values(state.prizes).reduce((a, n) => a + (Number(n) || 0), 0);
    const root = el('div', { class: 'stack' });

    root.appendChild(el('div', { class: 'topbar' }, [
      el('button', { class: 'back', text: '‹', onclick: () => { location.hash = '#/'; } }),
      el('div', { style: 'flex:1' }, [
        el('h1', { text: '动物抽卡站' }),
        el('div', { class: 'sub', text: '放松一下 · 想抽就抽' }),
      ]),
    ]));

    root.appendChild(el('section', { class: 'panel rg-hero', style: 'padding:16px 15px;text-align:center' }, [
      el('div', { class: 'rg-stats' }, [
        el('span', { text: `图鉴 ${unlocked}/${ANIMAL_CARDS.length}` }),
        el('span', { text: `实体券 ${prizeOwned}/${PHYSICAL_PRIZES.length} · 共 ${prizeTotal} 张` }),
        el('span', { text: `累计 ${state.total} 抽` }),
      ]),
      el('div', { class: 'rg-box', 'aria-hidden': 'true' }, [
        el('div', { class: 'rg-box-emoji', text: '🎁' }),
        el('div', { class: 'rg-box-hint', text: '今天想遇见谁？' }),
      ]),
      el('div', { style: 'font-size:11.5px;color:#0f766e;line-height:1.7',
        text: `距 R 及以上保底 ${Math.max(0, PITY_R - state.pityR)} 抽 · 距 SR 及以上保底 ${Math.max(0, PITY_SR - state.pitySr)} 抽` }),
      el('div', { class: 'rg-actions' }, [
        el('button', {
          class: 'btn', text: '✨ 抽 1 次',
          disabled: !quota || quota.remaining < 1,
          onclick: () => doDraw(1),
        }),
        el('button', {
          class: 'btn ghost', text: '🎊 抽 10 次',
          disabled: !quota || quota.remaining < 10,
          onclick: () => doDraw(10),
        }),
      ]),
      el('div', { style: 'font-size:11px;color:#b6a498;margin-top:9px;line-height:1.6',
        text: (!quota || quota.remaining < 10)
          ? '今日剩余次数不足 10 次，十连已关闭；点数用完请明天再来。'
          : '不花券、不计分，每天有固定次数，抽到什么都开心。' }),
      el('button', {
        class: 'btn soft full', style: 'margin-top:10px',
        text: '🎁 实体奖抽卡（必出实体券）',
        disabled: !quota || !quota.prize || quota.prize.remaining < 1,
        onclick: () => doPrizeDraw(),
      }),
      el('div', { style: 'font-size:10.5px;color:#b45309;line-height:1.6;margin-top:6px',
        text: `实体奖免费机会今日剩 ${quota?.prize?.remaining || 0} 次：周一/三/五/日各 1 次，当日积分满 ${quota?.prize?.points_threshold || 100} 分再 +1 次。不占用上面的抽卡次数。` }),
    ]));

    root.appendChild(quotaPanel(quota));

    root.appendChild(bonusPanel(bonus, {
      rate: effectivePrizeRate(bonus),
      note: '学习越活跃、成就卡越多，实体券爆率越高。连续打卡最多 ×2，成就卡最多 ×3，最高封顶 30%。加成不消耗积分。',
    }));

    root.appendChild(el('div', { class: 'section-head' }, [
      el('h3', { text: '动物图鉴' }),
      el('span', { class: 'hint', text: `已遇见 ${unlocked}/${ANIMAL_CARDS.length}` }),
    ]));
    const grid = el('div', { class: 'rg-grid' });
    ANIMAL_CARDS.forEach((c) => {
      const count = state.counts[c.id] || 0;
      const tile = cardTile({ ...c, counts: count }, { locked: !count, showCount: true });
      tile.addEventListener('click', () => showCard(c, count));
      grid.appendChild(tile);
    });
    root.appendChild(grid);

    /* ---- 实体奖励图鉴 ---- */
    root.appendChild(el('div', { class: 'section-head' }, [
      el('h3', { text: '实体奖励' }),
      el('span', { class: 'hint', text: `已获得 ${prizeOwned}/${PHYSICAL_PRIZES.length}` }),
    ]));
    const prizeGrid = el('div', { class: 'pg-grid' });
    PHYSICAL_PRIZES.forEach((p) => {
      const count = state.prizes[p.id] || 0;
      const tile = prizeTile(p, { locked: !count, count });
      tile.addEventListener('click', () => showPrizeDetail(p, count));
      prizeGrid.appendChild(tile);
    });
    root.appendChild(prizeGrid);

    /* ---- 我的实体券（获得记录） ---- */
    root.appendChild(el('div', { class: 'section-head' }, [
      el('h3', { text: '我的实体券' }),
      el('span', { class: 'hint', text: '已同步家庭台账 · 爸爸妈妈可核销' }),
    ]));
    const prizePanel = el('section', { class: 'panel', style: 'padding:6px 13px' });
    const emptyHint = () => prizePanel.appendChild(el('div', { class: 'hint', style: 'padding:10px 0',
      text: '还没抽到实体券。抽卡时有机会爆出饮料、零食或大餐券。' }));
    if (!ledgerReady && !state.prizeHistory.length) {
      emptyHint();
    } else {
      const rows = ledgerReady ? ledger.slice(0, 10) : state.prizeHistory.slice(0, 10);
      if (!rows.length) emptyHint();
      rows.forEach((h) => {
        const time = new Date(h.created_at || h.at);
        const label = Number.isNaN(time.getTime()) ? '' :
          time.toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit' });
        const statusTag = h.status === 'redeemed'
          ? el('span', { class: 'rg-new-inline', style: 'color:#059669', text: '已兑现 ✓' })
          : h.status === 'spent'
            ? el('span', { class: 'rg-new-inline', style: 'color:#a3928a', text: '已合成' })
            : null;
        prizePanel.appendChild(el('div', { class: 'rg-hist' }, [
          el('span', { class: 'e', text: h.emoji || '🎁' }),
          el('span', { text: h.name || '实体券' }),
          el('span', { class: `rg-rar rar-${h.rarity || 'N'}`, text: h.rarity || 'N' }),
          h.isNew ? el('span', { class: 'rg-new-inline', text: 'NEW' }) : null,
          statusTag,
          el('span', { class: 't', text: label }),
        ]));
      });
      if (ledgerReady && ledger.length) {
        prizePanel.appendChild(el('div', { class: 'hint', style: 'padding:8px 0 6px',
          text: '台账已同步到家庭管理中心，爸爸妈妈核销后这里会显示「已兑现」。' }));
      }
    }
    root.appendChild(prizePanel);

    root.appendChild(el('div', { class: 'section-head' }, [
      el('h3', { text: '最近的相遇' }),
      el('span', { class: 'hint', text: '只留最近 30 次' }),
    ]));
    const historyPanel = el('section', { class: 'panel', style: 'padding:6px 13px' });
    if (!state.history.length) {
      historyPanel.appendChild(el('div', { class: 'hint', style: 'padding:10px 0', text: '还没有抽过，点上面的按钮试试。' }));
    } else {
      state.history.slice(0, 8).forEach((h) => {
        const time = new Date(h.at);
        const label = Number.isNaN(time.getTime()) ? '' :
          time.toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit' });
        historyPanel.appendChild(el('div', { class: 'rg-hist' }, [
          el('span', { class: 'e', text: h.emoji || '🐾' }),
          el('span', { text: h.name || '小伙伴' }),
          el('span', { class: `rg-rar rar-${h.rarity || 'N'}`, text: h.rarity || 'N' }),
          h.isNew ? el('span', { class: 'rg-new-inline', text: 'NEW' }) : null,
          el('span', { class: 't', text: label }),
        ]));
      });
    }
    root.appendChild(historyPanel);

    root.appendChild(el('section', { class: 'panel', style: 'padding:13px;margin-top:18px' }, [
      el('div', { style: 'font-size:12px;font-weight:800;margin-bottom:6px', text: '玩法说明' }),
      el('div', { class: 'hint', style: 'line-height:1.8', text: '概率：N 55% · R 30% · SR 12% · SSR 3%。连续 10 抽没出 R 及以上，下一抽保底 R；连续 40 抽没出 SR 及以上，下一抽保底 SR。学习加成越高，R/SR/SSR 权重越大。' }),
      el('div', { class: 'hint', style: 'line-height:1.8;margin-top:4px', text: '每抽基础 6% 机会爆出「实体奖励券」（脉动、牛奶、糖葫芦、巧克力、烤鱼套餐、海底捞火锅、神秘心愿），并随上方的学习加成提高，最高 30%。SR/SSR 大餐券每天首张保真，同日再出的会自动换成 R 级小奖券，大餐节奏可控。它只是一张心愿记录，真实奖品由爸爸妈妈决定和兑现，不涉及任何付款。' }),
      el('div', { class: 'hint', style: 'line-height:1.8;margin-top:4px', text: '每天有抽奖次数：平日 10 次，疯狂星期六、周日和节假日 20 次；当日学习积分每 10 分再送 1 次。次数由服务端记录，换设备或清缓存也不会重置。' }),
      el('div', { class: 'hint', style: 'line-height:1.8;margin-top:4px', text: '「实体奖抽卡」是独立机会：周一/三/五/日各免费 1 次，当日学习积分满 100 分再 +1 次，必出一张实体券，不占用上面的抽卡次数。学习加成越高，越容易抽到稀有券。' }),
      el('div', { class: 'hint', style: 'line-height:1.8;margin-top:4px', text: '这里没有真实货币、不影响学习积分。收集进度和实体券台账都同步到服务端：清缓存、换设备都不会丢，爸爸妈妈核销后会显示「已兑现」。' }),
      el('div', { class: 'hint', style: 'line-height:1.8;margin-top:4px', text: '攒小券换大券：3 张 N 级券可以换 1 张自选 R 级券，2 张 R 级券换 1 张自选 SR 级券。点「实体奖励」图鉴里的券就能看到合成按钮。' }),
    ]));

    root.appendChild(el('button', {
      class: 'btn ghost full', style: 'margin-top:10px', text: '清空本机的抽卡记录',
      onclick: askReset,
    }));
    root.appendChild(el('button', {
      class: 'btn soft full', style: 'margin-top:8px', text: '🎡 更多小游戏',
      onclick: () => { location.hash = '#/games'; },
    }));

    view.innerHTML = '';
    view.appendChild(root);
  }

  async function doDraw(count) {
    if (drawing) return;
    drawing = true;
    try {
      const used = await useQuota(count);
      if (used.quota) quota = used.quota;
      if (!used.ok) { paint(); return; }
      const { cards, prizes } = draw(state, count, effectivePrizeRate(bonus), bonus?.total || 1);
      saveAndSync(prizes);
      paint();
      showResult(cards, prizes);
    } finally {
      drawing = false;
    }
  }

  async function doPrizeDraw() {
    if (drawing) return;
    drawing = true;
    try {
      const used = await usePrizeQuota();
      if (used.quota) quota = used.quota;
      if (!used.ok) { paint(); return; }
      const prize = downgradeIfCapped(pickGuaranteedPrize(bonus), state);
      const at = Date.now();
      const first = !state.prizes[prize.id];
      state.prizes[prize.id] = (state.prizes[prize.id] || 0) + 1;
      state.prizeHistory.unshift({
        id: prize.id, name: prize.name, emoji: prize.emoji,
        rarity: prize.rarity, isNew: first, at,
      });
      state.prizeHistory = state.prizeHistory.slice(0, HISTORY_LIMIT);
      saveAndSync([{ id: prize.id, at }]);
      paint();
      showPrizeDrawResult(prize, first);
    } finally {
      drawing = false;
    }
  }

  function showPrizeDrawResult(prize, isNew) {
    let dismiss = () => {};
    const againBtn = el('button', {
      class: 'btn', text: '再抽实体奖',
      disabled: !quota || !quota.prize || quota.prize.remaining < 1,
      onclick: () => { dismiss(); doPrizeDraw(); },
    });
    const closeBtn = el('button', { class: 'btn ghost', text: '收好啦', onclick: () => dismiss() });
    const content = el('div', {}, [
      el('div', { class: 'pg-drop-banner' }, [
        el('div', { class: 'pg-drop-title', text: '🎉 恭喜获得实体奖券！' }),
        el('div', { class: 'pg-drop-sub', text: '这次是专门的实体奖抽卡' }),
        el('div', { class: 'pg-drop' }, [
          prizeTile(prize, { pop: true, count: state.prizes[prize.id] || 1 }),
        ]),
        el('div', { class: 'pg-drop-note', text: '这是一张心愿券，真实奖品由爸爸妈妈决定和兑现' }),
      ]),
      el('div', { style: 'text-align:center;font-size:12px;color:#6b5b52;line-height:1.8;margin-top:12px',
        text: `${prize.name} · ${RARITY_LABEL[prize.rarity]}${isNew ? ' · 新收集！' : ''}` }),
      el('div', { class: 'row', style: 'gap:9px;margin-top:14px' }, [againBtn, closeBtn]),
    ]);
    dismiss = openSheet(content, { title: '实体奖抽卡', sub: '快去告诉爸爸妈妈' }).close;
  }

  function showResult(results, prizes) {
    const best = results.reduce((a, b) =>
      RARITY_ORDER[b.rarity] > RARITY_ORDER[a.rarity] ? b : a, results[0]);
    const grid = el('div', { class: results.length > 1 ? 'rg-result ten' : 'rg-result' });
    results.forEach((c, i) => {
      const tile = cardTile(c, { pop: true });
      tile.style.animationDelay = `${i * 45}ms`;
      grid.appendChild(tile);
    });

    let dismiss = () => {};
    const againBtn = el('button', { class: 'btn', text: '再抽一次', onclick: () => { dismiss(); doDraw(1); } });
    const closeBtn = el('button', { class: 'btn ghost', text: '收好啦', onclick: () => dismiss() });
    const content = el('div', {});

    if (prizes.length) {
      const prizeRow = el('div', { class: 'pg-drop' });
      prizes.forEach((p, i) => {
        const tile = prizeTile(p, { pop: true, count: state.prizes[p.id] || 1 });
        tile.style.animationDelay = `${i * 90}ms`;
        prizeRow.appendChild(tile);
      });
      content.appendChild(el('div', { class: 'pg-drop-banner' }, [
        el('div', { class: 'pg-drop-title', text: '🎉 哇！爆出实体奖励券！' }),
        el('div', { class: 'pg-drop-sub', text: '快去告诉爸爸妈妈' }),
        prizeRow,
        el('div', { class: 'pg-drop-note', text: '这是一张心愿券，真实奖品由爸爸妈妈决定和兑现' }),
      ]));
    }

    content.appendChild(el('div', { class: 'rg-headline' }, [
      el('div', { class: 'rg-big', text: best.emoji }),
      el('div', {}, [
        el('div', { style: 'font-size:14px;font-weight:800', text: results.length > 1 ? '十连结果来啦' : '抽到了！' }),
        el('div', { style: 'font-size:11.5px;color:#a3928a;line-height:1.7',
          text: `本次最稀有：${best.name} · ${RARITY_LABEL[best.rarity]}` }),
      ]),
    ]));
    content.appendChild(grid);
    content.appendChild(el('div', { class: 'row', style: 'gap:9px;margin-top:14px' }, [againBtn, closeBtn]));
    dismiss = openSheet(content, {
      title: prizes.length ? '抽到实体券啦' : '动物抽卡',
      sub: prizes.length ? '这份惊喜要跟家人分享' : '抽到什么都开心',
    }).close;
  }

  function showPrizeDetail(p, count) {
    const rule = EXCHANGE_RULES[p.rarity];
    const heldFeed = rule && ledgerReady
      ? ledger.filter((r) => r.status === 'held' && r.rarity === rule.from)
      : [];
    const canExchange = !!(rule && heldFeed.length >= rule.cost);

    const body = [
      el('div', { style: 'font-size:56px;line-height:1.3', text: count ? p.emoji : '🎁' }),
      el('div', { style: 'font-size:15px;font-weight:800;margin-top:4px', text: p.name }),
      el('span', { class: `rg-rar rar-${p.rarity}`, style: 'margin-top:8px', text: `${p.rarity} · ${RARITY_LABEL[p.rarity]}` }),
      el('div', { style: 'font-size:12.5px;color:#6b5b52;line-height:1.8;margin-top:12px', text: p.note }),
    ];
    if (!count) {
      body.push(el('div', { class: 'hint', style: 'margin-top:10px',
        text: canExchange ? '还没抽到过这张券，但小券攒够了可以直接合成它！'
          : '还没抽到，抽卡时有机会获得这张券' }));
    } else {
      body.push(el('div', { class: 'hint', style: 'margin-top:10px',
        text: `已经抽到 ${count} 张，可以找爸爸妈妈兑换啦` }));
    }
    if (canExchange) {
      body.push(el('div', { class: 'hint', style: 'margin-top:8px',
        text: `${rule.from} 级券还剩 ${heldFeed.length} 张待用` }));
      body.push(el('button', {
        class: 'btn soft full', style: 'margin-top:10px',
        text: `🔀 用 ${rule.cost} 张 ${rule.from} 级券换这张`,
        onclick: async (e) => {
          const btn = e.currentTarget;
          btn.disabled = true; btn.textContent = '合成中…';
          try {
            const keys = heldFeed.slice(0, rule.cost).map((r) => r.id);
            await api.exchangePrize(p.rarity, p.id, keys);
            toast(`已合成：${p.name}！去找爸爸妈妈兑换吧`);
            dismiss();
            await loadLedger();
          } catch (err) {
            toast(err.message || '合成失败，稍后再试');
            btn.disabled = false;
            btn.textContent = `🔀 用 ${rule.cost} 张 ${rule.from} 级券换这张`;
          }
        },
      }));
    }
    let dismiss = () => {};
    dismiss = openSheet(el('div', { style: 'text-align:center' }, body),
      { title: count ? '我的实体券' : '实体奖励' }).close;
  }

  function showCard(c, count) {
    openSheet(el('div', { style: 'text-align:center' }, [
      el('div', { style: 'font-size:60px;line-height:1.3', text: count ? c.emoji : '❔' }),
      el('div', { style: 'font-size:16px;font-weight:800;margin-top:4px', text: count ? c.name : '还没遇见的伙伴' }),
      count ? el('span', { class: `rg-rar rar-${c.rarity}`, style: 'margin-top:8px', text: `${c.rarity} · ${RARITY_LABEL[c.rarity]}` }) : null,
      el('div', { style: 'font-size:12.5px;color:#6b5b52;line-height:1.8;margin-top:12px', text: count ? c.quote : '抽到它之后，这里会显示它的名字和一句话。' }),
      el('div', { class: 'hint', style: 'margin-top:10px', text: count ? `已经遇见 ${count} 次` : '还没有遇到过它' }),
    ]), { title: '动物卡片' });
  }

  function askReset() {
    let dismiss = () => {};
    const confirmBtn = el('button', {
      class: 'btn warn', text: '确认清空',
      onclick: () => {
        dismiss();
        try { localStorage.removeItem(stateKey(who)); } catch { /* 忽略 */ }
        state = freshState();
        saveAndSync();          // 同步清空服务端存档，避免下次抽奖把空档回写覆盖备份
        paint();
        toast('已清空，从零开始收集');
      },
    });
    const cancelBtn = el('button', { class: 'btn ghost', text: '再想想', onclick: () => dismiss() });
    const content = el('div', {}, [
      el('div', { class: 'hint', style: 'line-height:1.8', text: '图鉴、抽卡次数、保底在本机与服务端存档都会清零（家庭台账的历史记录保留），无法恢复。确定吗？' }),
      el('div', { class: 'row', style: 'gap:9px;margin-top:14px' }, [confirmBtn, cancelBtn]),
    ]);
    dismiss = openSheet(content, { title: '清空抽卡记录' }).close;
  }

  paint();
}
