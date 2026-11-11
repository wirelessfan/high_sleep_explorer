/* 守关者展示组件（谬误研究所 · 怪人军团）
 *
 * 只消费接口里新增的 boss 字段，boss 缺失时静默降级为原样渲染。
 * 提交后的 HP 联动用 MutationObserver 监听既有的 .result-hero 出现，
 * 不改动任何判分 / 提交 / 发奖逻辑。
 */
import { el } from './ui.js';

let _activeObserver = null;

/** 版块列表左侧的小立绘；没有 boss 时返回原来的图标方块。 */
export function bossThumb(boss, { done = false, fallback = '' } = {}) {
  if (!boss || !boss.svg) return el('div', { class: 'ico', text: fallback });
  const wrap = el('div', {
    class: `ico boss-ico${boss.tier === 'big' ? ' is-big' : ''}${done ? ' is-done' : ''}`,
  });
  wrap.appendChild(el('img', {
    src: boss.svg,
    alt: `${boss.name}（${boss.tier === 'big' ? '大 BOSS' : '小 BOSS'}）`,
    loading: 'lazy',
  }));
  return wrap;
}

/** 守关者横幅：立绘 + 身份 + 台词 + HP 条。 */
export function bossBanner(boss, {
  status = 'open', compact = false, kicker = '本关守关者',
} = {}) {
  if (!boss || !boss.svg) return null;
  const big = boss.tier === 'big';
  const done = status === 'done';
  const hp = Math.max(1, Number(boss.hp) || 1);
  const left = done ? 0 : hp;

  const state = el('span', {
    class: 'boss-state',
    text: done ? '✓ 已净化' : `HP ${left}/${hp}`,
  });
  const say = el('div', {
    class: 'boss-say',
    text: done ? (boss.purified || '已净化') : (boss.taunt || ''),
  });
  const hpBar = el('div', { class: 'boss-hp' }, [
    el('i', { style: `width:${Math.round(left / hp * 100)}%` }),
  ]);

  const info = el('div', { class: 'boss-info' }, [
    el('div', { class: 'boss-line' }, [
      el('span', {
        class: 'boss-kicker',
        text: big ? '研究所所长 · 关底守关者' : kicker,
      }),
      el('span', {
        class: `boss-tier${big ? ' big' : ''}`,
        text: big ? '大 BOSS' : '小 BOSS',
      }),
    ]),
    el('div', { class: 'boss-line boss-name-line' }, [
      el('strong', { class: 'boss-name', text: boss.name || '???' }),
      el('span', { class: 'boss-en', text: boss.en || '' }),
    ]),
    el('div', { class: 'boss-tags' }, [
      el('span', { class: 'boss-tag', text: boss.code || '' }),
      el('span', { class: 'boss-tag', text: boss.element || '' }),
      state,
    ]),
    say,
    hpBar,
  ]);

  const banner = el('section', {
    class: `boss-banner${big ? ' big' : ''}${compact ? ' compact' : ''}${done ? ' cleared' : ''}`,
    'data-boss-id': boss.id || '',
  }, [
    el('div', { class: 'boss-art' }, [
      el('img', { src: boss.svg, alt: boss.name || '守关者' }),
    ]),
    info,
  ]);
  return banner;
}

/** 版块列表里的一行小字：守关者名字，纯新增 DOM。 */
export function bossInline(boss) {
  if (!boss || !boss.name) return null;
  return el('div', {
    class: 'boss-inline',
    text: `${boss.tier === 'big' ? '👑' : '👾'} ${boss.name} · ${boss.element || ''}`,
  });
}

/** 结果面板出现时按答对题数扣 HP；整页只保留一个 observer，避免泄漏。 */
export function bindBossProgress(rootEl, bannerEl, boss) {
  if (!rootEl || !bannerEl || !boss) return;
  if (_activeObserver) _activeObserver.disconnect();

  const hp = Math.max(1, Number(boss.hp) || 1);
  const hpFill = bannerEl.querySelector('.boss-hp i');
  const state = bannerEl.querySelector('.boss-state');
  const say = bannerEl.querySelector('.boss-say');

  const apply = (correct, total) => {
    const t = Math.max(1, Number(total) || 1);
    const left = Math.max(0, hp - Math.round(Math.min(correct, t) / t * hp));
    if (hpFill) hpFill.style.width = `${Math.round(left / hp * 100)}%`;
    if (state) state.textContent = left === 0 ? '✓ 已净化' : `HP ${left}/${hp}`;
    if (left === 0) {
      bannerEl.classList.add('cleared');
      if (say) say.textContent = boss.purified || '已净化';
    } else if (say && left < hp) {
      say.textContent = `还剩 ${left} 格 HP，继续净化！`;
    }
  };

  const scan = () => {
    // 版块渲染期间 root 可能尚未挂到 document（await 让出了控制权），
    // 此时只是暂时不处理，绝不能断开观察器，否则后续提交再也收不到。
    if (!rootEl.isConnected) return;
    const heroes = rootEl.querySelectorAll('.result-hero');
    if (!heroes.length) return;
    const lbl = heroes[heroes.length - 1].querySelector('.lbl')?.textContent || '';
    const m = lbl.match(/答对\s*(\d+)\s*\/\s*(\d+)/);
    if (m) apply(Number(m[1]), Number(m[2]));
  };

  const obs = new MutationObserver(scan);
  obs.observe(rootEl, { childList: true, subtree: true });
  _activeObserver = obs;
}
