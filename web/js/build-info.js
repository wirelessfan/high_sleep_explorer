/* 构建信息（版本号）：管理中心、首页、「我的」页脚共用一套。

   版本来源是后端的 /api/v1/version —— 部署时由 deploy.sh 写入 BUILD_INFO.json，
   所以页面上看到的号就是线上真正在跑的那一份代码。 */

import * as api from './api.js';
import { el, openSheet } from './ui.js';

let pending = null;

/** 读一次构建信息，进程内缓存；失败返回 null，不阻塞页面渲染。 */
export function loadBuild() {
  if (!pending) pending = api.getVersion().catch(() => null);
  return pending;
}

/** ISO 时间 → 「2026-11-21 19:07」，按本地时区。 */
export function fmtTime(iso) {
  if (!iso) return '—';
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return String(iso).replace('T', ' ').slice(0, 16);
  const p = (n) => String(n).padStart(2, '0');
  return `${d.getFullYear()}-${p(d.getMonth() + 1)}-${p(d.getDate())} ${p(d.getHours())}:${p(d.getMinutes())}`;
}

/** 版本卡片右下角的详细信息弹层。 */
export function showBuildSheet(build) {
  if (!build) return;
  const rows = [
    ['版本', build.label || `v${build.version}`],
    ['提交', build.commit || 'unknown'],
    ['分支', build.branch || 'unknown'],
    ['部署时间', fmtTime(build.built_at)],
    ['提交时间', fmtTime(build.commit_date)],
    ['数据版本', `schema v${build.schema_version ?? '?'}`],
    ['审核引擎', build.wrongbook_review_version || '—'],
  ];
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
}

/** 页面底部一行灰色版本号，点了开详情。 */
export function versionLine(build, hint) {
  const kids = [];
  if (hint) kids.push(el('div', { text: hint }));
  if (build) {
    kids.push(el('button', {
      style: 'margin-top:3px;background:none;border:0;padding:0;cursor:pointer;font-size:10.5px;'
        + 'color:#c0b3a8;font-family:ui-monospace,Menlo,Consolas,monospace;text-decoration:underline dotted',
      text: build.label || `v${build.version}`,
      onclick: () => showBuildSheet(build),
    }));
  }
  return el('div', { style: 'text-align:center;font-size:10.5px;color:#b6c2d2;padding:10px 0 6px' }, kids);
}
