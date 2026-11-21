/* 管理中心：AI 通道、任务路由、限额、用量（仅管理员可见入口，非管理员接口返回 403） */

import * as api from '../api.js';
import { el, toast, openSheet } from '../ui.js';

function badge(text, cls = '') {
  return el('span', { class: `chip ${cls}`, style: 'font-size:10px;padding:2px 8px', text });
}

function keyBadge(ok) {
  return ok ? badge('Key ✓', 'solid') : badge('未配置 Key');
}

/** ISO 时间 → 「2026-11-21 18:52」，本地时区。 */
function fmtTime(iso) {
  if (!iso) return '—';
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return String(iso).replace('T', ' ').slice(0, 16);
  const p = (n) => String(n).padStart(2, '0');
  return `${d.getFullYear()}-${p(d.getMonth() + 1)}-${p(d.getDate())} ${p(d.getHours())}:${p(d.getMinutes())}`;
}

async function renderAdmin(view) {
  /* 配置/用量/账号并行读取，403 时回「我的」。 */
    let cfg;
    let usageDays = 1;
    let usage;
    let users;
    let build = null;
    try {
      [cfg, usage, users] = await Promise.all([
        api.getAdminAiConfig(),
        api.adminAiUsage(usageDays),
        api.adminUsers(),
      ]);
    } catch (err) {
      toast(err.status === 403 ? '需要管理员身份' : (err.message || '加载失败'));
      location.hash = '#/me';
      return;
    }
    try { build = await api.getVersion(); } catch { build = null; }

    const root = el('div', { class: 'stack' });

    root.appendChild(el('div', { class: 'topbar' }, [
      el('button', { class: 'back', text: '‹', onclick: () => { location.hash = '#/me'; } }),
      el('div', { style: 'flex:1' }, [
        el('h1', { text: '管理中心' }),
        el('div', { class: 'sub', text: 'AI 通道 · 任务路由 · 用量' }),
      ]),
    ]));

    if (build) {
      const rows = [
        ['版本', build.label || `v${build.version}`],
        ['提交', build.commit || 'unknown'],
        ['分支', build.branch || 'unknown'],
        ['部署时间', fmtTime(build.built_at)],
        ['提交时间', fmtTime(build.commit_date)],
        ['数据版本', `schema v${build.schema_version ?? '?'}`],
        ['审核引擎', build.wrongbook_review_version || '—'],
      ];
      const openDetail = () => {
        openSheet(el('div', { class: 'stack' }, [
          el('div', { style: 'font-size:11px;color:#a3928a', text: '线上服务当前运行的代码版本' }),
          el('div', { class: 'panel', style: 'padding:4px 13px' }, rows.map(([k, v]) => el('div', {
            class: 'row-between', style: 'gap:12px;padding:9px 0;border-top:1px solid #f6ede0',
          }, [
            el('span', { style: 'font-size:11.5px;color:#8a7a70;flex-shrink:0', text: k }),
            el('span', { style: 'font-size:12px;font-weight:700;text-align:right;word-break:break-all', text: v }),
          ]))),
          el('div', { style: 'font-size:10.5px;color:#b6a498;line-height:1.7',
            text: build.dirty
              ? '注意：该版本的部署包含未提交改动（dirty），与仓库 HEAD 不完全一致。'
              : '与仓库 HEAD 一致，可直接对照提交记录。' }),
        ]), { title: '版本信息', sub: build.label || '' });
      };
      root.appendChild(el('section', {
        class: 'panel', style: 'padding:11px 13px;display:flex;gap:10px;align-items:center',
      }, [
        el('div', { style: 'flex:1;min-width:0' }, [
          el('div', { style: 'display:flex;gap:6px;align-items:center;flex-wrap:wrap' }, [
            el('span', {
              style: 'font-size:13px;font-weight:800;font-family:ui-monospace,Menlo,Consolas,monospace',
              text: build.label || `v${build.version}`,
            }),
            build.dirty ? badge('含未提交改动') : badge('已发布', 'solid'),
          ]),
          el('div', { style: 'font-size:10.5px;color:#a3928a;margin-top:2px',
            text: `部署于 ${fmtTime(build.built_at)}` }),
        ]),
        el('button', { class: 'btn ghost sm', text: '详情', onclick: openDetail }),
      ]));
    }

    if (cfg.stub) {
      root.appendChild(el('section', { class: 'panel', style: 'padding:11px 13px' }, [
        el('div', { style: 'font-size:12px;color:#92400e;background:#fffbeb;border-radius:9px;padding:8px 10px;line-height:1.6',
          text: '🧪 演示模式（LEARN_AI_STUB=1）：所有 AI 任务走本地占位实现，不产生真实调用与费用。' }),
      ]));
    }
    if (cfg.updated_at) {
      root.appendChild(el('div', { style: 'font-size:11px;color:#a3928a;padding:0 2px',
        text: `策略上次调整：${cfg.updated_at.replace('T', ' ').slice(0, 16)}` }));
    }

    /* ---- 通道 ---- */
    const channelInputs = {};   // cid -> {enabled: checkbox, model: input}
    root.appendChild(el('div', { class: 'section-head' }, [
      el('h3', { text: 'AI 通道' }),
      el('span', { class: 'hint', text: 'Key 只在服务器环境配置，这里只管开关与模型' }),
    ]));

    const channelPanel = el('section', { class: 'panel', style: 'padding:13px' });
    for (const cid of cfg.channel_order) {
      const ch = cfg.channels[cid];
      if (!ch) continue;
      const enabled = el('input', {
        type: 'checkbox', ...(ch.enabled ? { checked: true } : {}),
        style: 'width:18px;height:18px;accent-color:#14b8a6',
      });
      const model = el('input', {
        type: 'text',
        value: ch.model_override || '',
        placeholder: ch.default_model,
        style: 'flex:1;min-width:120px;font-size:12px;padding:7px 9px;border:1px solid #eaddc9;border-radius:9px;background:#fffdf9;color:#3b2f2a',
      });
      channelInputs[cid] = { enabled, model };

      channelPanel.appendChild(el('div', {
        style: 'display:flex;gap:10px;align-items:center;padding:9px 0;border-top:1px solid #f6ede0',
      }, [
        enabled,
        el('div', { style: 'flex:1;min-width:0' }, [
          el('div', { style: 'display:flex;gap:6px;align-items:center;flex-wrap:wrap' }, [
            el('span', { style: 'font-size:13px;font-weight:800', text: `${ch.name} · ${cid}` }),
            keyBadge(ch.key_ok),
            ch.vision ? badge('视觉') : null,
            ch.enabled ? null : badge('已停用'),
          ]),
          el('div', { style: 'font-size:10.5px;color:#a3928a;margin-top:2px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap',
            text: ch.base_url }),
        ]),
        model,
      ]));
    }
    if (!Object.keys(channelInputs).length) {
      channelPanel.appendChild(el('div', { style: 'font-size:12px;color:#a3928a', text: '没有可用通道' }));
    }
    root.appendChild(channelPanel);

    /* ---- 任务路由 + 限额 ---- */
    const routingSelects = {};
    const limitInputs = {};
    root.appendChild(el('div', { class: 'section-head' }, [
      el('h3', { text: '任务路由' }),
      el('span', { class: 'hint', text: '不同任务派给不同通道；主通道失败自动按能力序回退' }),
    ]));

    const routePanel = el('section', { class: 'panel', style: 'padding:13px' });
    for (const t of cfg.tasks) {
      const sel = el('select', {
        style: 'font-size:12px;padding:7px 9px;border:1px solid #eaddc9;border-radius:9px;background:#fffdf9;color:#3b2f2a;max-width:46%',
      }, Object.keys(cfg.channels).filter((cid) => ['review', 'photo_confirm'].includes(t.id) ? cid.startsWith('review') : (t.id === 'recognize' ? cid === 'glm' : !cid.startsWith('review'))).map((cid) => {
        const ch = cfg.channels[cid];
        return el('option', {
          value: cid,
          ...(cfg.routing[t.id] === cid ? { selected: true } : {}),
          text: `${ch.name}（${ch.model}）${ch.enabled ? '' : ' · 已停用'}`,
        });
      }));
      routingSelects[t.id] = sel;

      const limit = el('input', {
        type: 'number', min: 1, max: 200, value: String(cfg.limits[t.id] ?? 10),
        style: 'width:58px;font-size:12px;padding:7px 6px;border:1px solid #eaddc9;border-radius:9px;background:#fffdf9;color:#3b2f2a;text-align:center',
      });
      limitInputs[t.id] = limit;

      routePanel.appendChild(el('div', {
        style: 'display:flex;gap:8px;align-items:center;padding:9px 0;border-top:1px solid #f6ede0',
      }, [
        el('div', { style: 'flex:1;min-width:0' }, [
          el('div', { style: 'font-size:13px;font-weight:800', text: t.label }),
          el('div', { style: 'font-size:10.5px;color:#a3928a;margin-top:2px', text: `任务标识 ${t.id} · 限额 次/天` }),
        ]),
        sel,
        limit,
      ]));
    }
    root.appendChild(routePanel);

    /* ---- 保存 / 恢复默认 ---- */
    const saveBtn = el('button', {
      class: 'btn full',
      text: '💾 保存策略',
      onclick: async () => {
        saveBtn.disabled = true;
        saveBtn.textContent = '保存中…';
        try {
          const patch = { routing: {}, channels: {}, limits: {} };
          for (const [tid, sel] of Object.entries(routingSelects)) patch.routing[tid] = sel.value;
          for (const [cid, pair] of Object.entries(channelInputs)) {
            patch.channels[cid] = { enabled: pair.enabled.checked, model: pair.model.value.trim() };
          }
          for (const [tid, input] of Object.entries(limitInputs)) {
            const n = parseInt(input.value, 10);
            if (Number.isFinite(n)) patch.limits[tid] = n;
          }
          cfg = await api.putAdminAiConfig(patch);
          toast('策略已保存，立即生效');
          renderAdmin(view);
        } catch (err) {
          toast(err.message || '保存失败');
          saveBtn.disabled = false;
          saveBtn.textContent = '💾 保存策略';
        }
      },
    });

    const resetBtn = el('button', {
      class: 'btn ghost full', style: 'margin-top:8px',
      text: '↺ 恢复内置默认',
      onclick: () => {
        openSheet(el('div', {}, [
          el('div', { style: 'font-size:12.5px;color:#5c4b42;line-height:1.7',
            text: '会清空所有在线调整（路由/开关/模型覆盖/限额），回到代码内置默认。确定吗？' }),
          el('button', { class: 'btn full', style: 'margin-top:14px', text: '确认恢复默认',
            onclick: async () => {
              try {
                cfg = await api.resetAdminAi();
                toast('已恢复默认策略');
                document.getElementById('overlay').hidden = true;
                renderAdmin(view);
              } catch (err) { toast(err.message || '重置失败'); }
            } }),
          el('button', { class: 'btn ghost full', style: 'margin-top:8px', text: '取消',
            onclick: () => { document.getElementById('overlay').hidden = true; } }),
        ]), { title: '恢复默认' });
      },
    });

    root.appendChild(el('div', { style: 'margin-top:4px' }, [saveBtn, resetBtn]));

    /* ---- 连通性测试 ---- */
    root.appendChild(el('div', { class: 'section-head' }, [
      el('h3', { text: '连通性测试' }),
      el('span', { class: 'hint', text: '按当前路由发一次最小请求' }),
    ]));
    const testPanel = el('section', { class: 'panel', style: 'padding:13px' });
    for (const t of cfg.tasks) {
      const out = el('div', { style: 'font-size:11px;color:#6b5b52;margin-top:6px;min-height:14px',
        text: cfg.stub ? '演示模式：不会发起真实请求' : '' });
      testPanel.appendChild(el('div', { style: 'padding:9px 0;border-top:1px solid #f6ede0' }, [
        el('div', { class: 'row-between' }, [
          el('span', { style: 'font-size:13px;font-weight:800', text: t.label }),
          el('button', {
            class: 'btn soft sm', text: '测试',
            onclick: async (e) => {
              const btn = e.currentTarget;
              btn.disabled = true; btn.textContent = '测试中…';
              out.textContent = '';
              try {
                const r = await api.adminAiTest(t.id);
                out.textContent = r.ok
                  ? `✓ ${r.channel} · ${r.model} · ${r.latency_ms}ms${r.reply ? ` · 回复「${r.reply}」` : ''}`
                  : `✗ ${r.error}（${r.latency_ms}ms）`;
              } catch (err) {
                out.textContent = `✗ ${err.message || '测试失败'}`;
              }
              btn.disabled = false; btn.textContent = '测试';
            },
          }),
        ]),
        out,
      ]));
    }
    root.appendChild(testPanel);

    /* ---- 用量 ---- */
    const usageBox = el('section', { class: 'panel', style: 'padding:13px' });
    function paintUsage() {
      usageBox.innerHTML = '';
      const tabs = el('div', { class: 'row', style: 'gap:6px;margin-bottom:6px' });
      [[1, '今日'], [7, '近 7 日']].forEach(([d, label]) => {
        tabs.appendChild(el('button', {
          class: `chip ${usageDays === d ? 'solid' : ''}`,
          style: 'font-size:11px;padding:4px 10px',
          text: label,
          onclick: async () => {
            usageDays = d;
            try { usage = await api.adminAiUsage(d); paintUsage(); } catch (err) { toast(err.message); }
          },
        }));
      });
      usageBox.appendChild(tabs);
      if (!usage.rows.length) {
        usageBox.appendChild(el('div', { style: 'font-size:12px;color:#a3928a', text: '这段时间没有 AI 调用' }));
      }
      for (const r of usage.rows) {
        const chName = cfg.channels[r.channel]?.name || r.channel;
        const taskLabel = cfg.task_labels[r.task] || r.task;
        usageBox.appendChild(el('div', { class: 'row-between', style: 'padding:5px 0;font-size:12px' }, [
          el('span', { style: 'color:#6b5b52', text: `${chName} · ${taskLabel}` }),
          el('span', { style: 'font-weight:800', text: `${r.count} 次` }),
        ]));
      }
      usageBox.appendChild(el('div', { class: 'row-between', style: 'padding:6px 0 0;border-top:1px solid #f6ede0;margin-top:6px;font-size:12px' }, [
        el('span', { style: 'color:#a3928a', text: '合计' }),
        el('span', { style: 'font-weight:800', text: `${usage.total} 次` }),
      ]));
    }
    paintUsage();
    root.appendChild(el('div', { class: 'section-head' }, [el('h3', { text: 'AI 用量' })]));
    root.appendChild(usageBox);

    root.appendChild(el('a', { href: '#/feedback/review', class: 'btn full', text: '审核题目反馈 · 通过奖励 50 积分' }));

    root.appendChild(el('section', { class: 'panel stack' }, [
      el('strong', { text: `账号管理 · ${users.registered_count} 个正式账号` }),
      el('div', { class: 'hint', text: '爸爸 / 妈妈 / Sunny / 同学 / 访客；历史临时记录独立保留。' }),
      el('a', { href: '#/admin/accounts', class: 'btn ghost', text: '进入账号管理' }),
    ]));

    /* ---- 休闲广场赠送次数（仅管理员；写入服务端 7 天赠送池） ---- */
    root.appendChild(el('div', { class: 'section-head' }, [
      el('h3', { text: '休闲广场 · 赠送抽奖次数' }),
      el('span', { class: 'hint', text: '仅 dad 可用 · 7 天内有效、用完即止' }),
    ]));
    const grantPanel = el('section', { class: 'panel stack', style: 'padding:13px' });
    const grantAccount = el('select', {
      style: 'font-size:12px;padding:8px 9px;border:1px solid #eaddc9;border-radius:9px;background:#fffdf9;color:#3b2f2a',
    }, (users.users || []).map((u) => el('option', {
      value: u.id,
      ...(u.username === 'sunny' ? { selected: true } : {}),
      text: `${u.nickname || u.username} @${u.username || u.id}`,
    })));
    const grantRegular = el('input', {
      type: 'number', min: 0, max: 1000, value: '20', 'aria-label': '赠送普通抽奖次数',
      style: 'width:76px;font-size:12px;padding:8px 6px;border:1px solid #eaddc9;border-radius:9px;background:#fffdf9;color:#3b2f2a;text-align:center',
    });
    const grantPrize = el('input', {
      type: 'number', min: 0, max: 1000, value: '2', 'aria-label': '赠送实体奖次数',
      style: 'width:76px;font-size:12px;padding:8px 6px;border:1px solid #eaddc9;border-radius:9px;background:#fffdf9;color:#3b2f2a;text-align:center',
    });
    const grantDays = el('input', {
      type: 'number', min: 1, max: 90, value: '7', 'aria-label': '有效天数',
      style: 'width:76px;font-size:12px;padding:8px 6px;border:1px solid #eaddc9;border-radius:9px;background:#fffdf9;color:#3b2f2a;text-align:center',
    });
    const grantResult = el('div', { class: 'hint', style: 'min-height:16px;line-height:1.6' });
    const grantField = (label, input, note) => el('div', { class: 'row-between', style: 'gap:8px;padding:5px 0' }, [
      el('span', { style: 'font-size:12px;color:#5c4b42', text: label }),
      el('span', { class: 'row', style: 'gap:6px;align-items:center' }, [
        input,
        note ? el('span', { style: 'font-size:10.5px;color:#a3928a', text: note }) : null,
      ]),
    ]);
    grantPanel.appendChild(grantField('赠送给', grantAccount));
    grantPanel.appendChild(grantField('普通抽奖（次）', grantRegular));
    grantPanel.appendChild(grantField('实体奖（次）', grantPrize));
    grantPanel.appendChild(grantField('有效期（天）', grantDays));
    grantPanel.appendChild(el('button', {
      class: 'btn full', style: 'margin-top:6px', text: '🎁 确认赠送',
      onclick: async (e) => {
        const btn = e.currentTarget;
        const uid = grantAccount.value;
        const regular = Number(grantRegular.value) || 0;
        const prize = Number(grantPrize.value) || 0;
        const days = Number(grantDays.value) || 7;
        if (!uid) { toast('没有可赠送的账号'); return; }
        if (!regular && !prize) { toast('请至少填写一种赠送次数'); return; }
        const target = (users.users || []).find((u) => u.id === uid);
        const label = target ? `${target.nickname || ''} @${target.username || ''}` : '该账号';
        if (!window.confirm(`确认给 ${label} 赠送：普通 ${regular} 次、实体奖 ${prize} 次，${days} 天内有效？`)) return;
        btn.disabled = true; btn.textContent = '赠送中…';
        try {
          const q = await api.adminGrantQuota({ user_id: uid, regular, prize, days });
          toast('已赠送，立即生效');
          grantResult.textContent = `✅ ${label} 当前可用 ${q.remaining} 次（当日 ${q.day_total} + 赠送池 ${q.granted}）· 实体奖 ${q.prize.remaining} 次 · 赠送有效期至 ${q.grant_end}`;
        } catch (err) {
          toast(err.message || '赠送失败');
        } finally {
          btn.disabled = false; btn.textContent = '🎁 确认赠送';
        }
      },
    }));
    grantPanel.appendChild(grantResult);
    root.appendChild(grantPanel);

    /* ---- 许愿墙管理 ---- */
    root.appendChild(el('div', { class: 'section-head' }, [
      el('h3', { text: '许愿墙' }),
      el('span', { class: 'hint', text: '改状态 + 官方回复' }),
    ]));
    const wishPanel = el('section', { class: 'panel', style: 'padding:13px' });
    root.appendChild(wishPanel);

    /* ---- 实体券台账（核销） ---- */
    root.appendChild(el('div', { class: 'section-head' }, [
      el('h3', { text: '实体券台账' }),
      el('span', { class: 'hint', text: '抽卡站同步 · 核销后 Sunny 那边显示「已兑现」' }),
    ]));
    const prizePanel = el('section', { class: 'panel', style: 'padding:6px 13px' });
    root.appendChild(prizePanel);

    view.innerHTML = '';
    view.appendChild(root);

    try {
      const wishes = await api.adminWishes();
      wishPanel.innerHTML = '';
      if (!wishes.items.length) {
        wishPanel.appendChild(el('div', { style: 'font-size:12px;color:#a3928a', text: '还没有人许愿' }));
      }
      const STATUS = { open: '待处理', planned: '已采纳', done: '已实现' };
      wishes.items.forEach((w) => {
        const reply = el('input', {
          type: 'text', value: w.reply || '', placeholder: '写一条回复（可选）',
          style: 'flex:1;min-width:100px;font-size:11.5px;padding:6px 8px;border:1px solid #eaddc9;border-radius:8px;background:#fffdf9;color:#3b2f2a',
        });
        const select = el('select', {
          style: 'font-size:11.5px;padding:6px 7px;border:1px solid #eaddc9;border-radius:8px;background:#fffdf9;color:#3b2f2a',
        }, Object.entries(STATUS).map(([k, label]) => el('option', {
          value: k, ...(w.status === k ? { selected: true } : {}), text: label,
        })));

        wishPanel.appendChild(el('div', { style: 'padding:10px 0;border-top:1px solid #f6ede0' }, [
          el('div', { class: 'row-between', style: 'margin-bottom:5px' }, [
            el('span', { style: 'font-size:11.5px;font-weight:800', text: w.nickname + (w.username ? ` @${w.username}` : '') }),
            el('span', { style: 'font-size:10px;color:#b6a498', text: (w.created_at || '').slice(5, 16).replace('T', ' ') }),
          ]),
          el('div', { style: 'font-size:12px;color:#3b2f2a;line-height:1.7;margin-bottom:7px;white-space:pre-wrap', text: w.content }),
          el('div', { class: 'row', style: 'gap:6px;align-items:center;flex-wrap:wrap' }, [
            select, reply,
            el('button', {
              class: 'btn soft sm', text: '保存',
              onclick: async (e) => {
                const btn = e.currentTarget;
                btn.disabled = true; btn.textContent = '…';
                try {
                  await api.adminModerateWish(w.id, select.value, reply.value.trim());
                  toast('已保存');
                } catch (err) { toast(err.message || '保存失败'); }
                btn.disabled = false; btn.textContent = '保存';
              },
            }),
          ]),
        ]));
      });
    } catch (err) {
      wishPanel.innerHTML = '';
      wishPanel.appendChild(el('div', { style: 'font-size:12px;color:#b91c1c', text: err.message || '加载许愿墙失败' }));
    }

    try {
      const res = await api.adminPrizeLedger();
      prizePanel.innerHTML = '';
      const items = res?.items || [];
      if (!items.length) {
        prizePanel.appendChild(el('div', { style: 'font-size:12px;color:#a3928a;padding:10px 0',
          text: '还没有实体券记录。Sunny 在抽卡站抽到券后会自动记到这里。' }));
      }
      items.forEach((t) => {
        const time = (t.created_at || '').slice(5, 16).replace('T', ' ');
        const who = [t.nickname, t.username ? `@${t.username}` : ''].filter(Boolean).join(' ');
        const held = t.status === 'held';
        prizePanel.appendChild(el('div', { style: 'padding:9px 0;border-top:1px solid #f6ede0' }, [
          el('div', { class: 'row-between', style: 'gap:8px;align-items:center' }, [
            el('span', { style: 'font-size:12px;min-width:0', text: `${t.emoji} ${t.name} · ${t.rarity}` }),
            held ? el('button', {
              class: 'btn soft sm', text: '标记已兑现',
              onclick: async (e) => {
                const b = e.currentTarget;
                b.disabled = true; b.textContent = '…';
                try {
                  await api.adminRedeemPrize(t.id);
                  toast('已核销');
                  b.textContent = '已兑现 ✓';
                } catch (err2) {
                  toast(err2.message || '核销失败');
                  b.disabled = false; b.textContent = '标记已兑现';
                }
              },
            }) : el('span', {
              style: `font-size:10.5px;font-weight:800;color:${t.status === 'redeemed' ? '#059669' : '#a3928a'}`,
              text: t.status === 'redeemed' ? '已兑现 ✓' : '已合成',
            }),
          ]),
          el('div', { style: 'font-size:10px;color:#b6a498;margin-top:3px',
            text: `${who} · ${time}` }),
        ]));
      });
    } catch (err) {
      prizePanel.innerHTML = '';
      prizePanel.appendChild(el('div', { style: 'font-size:12px;color:#b91c1c;padding:10px 0',
        text: err.message || '加载实体券台账失败' }));
    }
}

export { renderAdmin };
