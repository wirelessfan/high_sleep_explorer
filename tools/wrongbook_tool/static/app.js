/* 错题录入工具前端：扫描 → 裁剪 → AI 识别 → 补错因 → 批量导入 */
"use strict";

const $ = (id) => document.getElementById(id);
const api = async (url, body, method) => {
  const r = await fetch(url, {
    method: method || (body ? "POST" : "GET"),
    headers: body ? { "Content-Type": "application/json" } : {},
    body: body ? JSON.stringify(body) : undefined,
  });
  const data = await r.json().catch(() => ({}));
  if (!r.ok) throw new Error(data.detail || `HTTP ${r.status}`);
  return data;
};
function toast(msg) {
  const t = document.createElement("div");
  t.className = "toast";
  t.textContent = msg;
  document.body.appendChild(t);
  setTimeout(() => t.remove(), 2600);
}
function toastErr(err) { toast(err.message || String(err)); }

const LETTERS = ["A", "B", "C", "D", "E", "F"];
const SUBJECTS = { physics: "物理", chemistry: "化学", math: "数学", biology: "生物", geography: "地理", cross: "跨学科", "": "未分类" };
const state = {
  taxonomy: null,          // {subjectId: {label, chapters:[[id,label]]}}
  files: [],               // 扫描结果
  done: new Set(),         // 已加入待导入的文件路径
  queue: [],               // 待导入条目
};

/* ---------------- 连接状态 ---------------- */
async function refreshState() {
  try {
    const s = await api("/api/state");
    state.info = s;
    const node = $("connState");
    const site = s.effective_site || s.site_url || "";
    if (s.logged_in) {
      node.textContent = `✅ ${s.username || "已登录"} @ ${site}`;
      node.style.color = ""; node.style.background = "";
    } else if (s.guest_sync) {
      node.textContent = `✅ 免登录同步 → ${site}（点此可登录家庭账号）`;
      node.style.color = "#0f766e"; node.style.background = "#f0fdfa";
    } else {
      node.textContent = `同步目标 ${site} · 点此登录家庭账号（不登录也能录）`;
      node.style.color = ""; node.style.background = "#f5f2ee";
    }
    node.style.cursor = "pointer";
    node.onclick = openSettings;
  } catch { $("connState").textContent = "工具服务未启动"; }
}

/* ---------------- 连接设置 ---------------- */
async function openSettings() {
  const s = await api("/api/state").catch(() => ({}));
  const sheet = $("sheet");
  sheet.innerHTML = `
    <h3 style="margin:0 0 4px">⚙️ 连接设置</h3>
    <label>网站地址</label>
    <input id="siteUrl" value="${s.site_url || s.default_site || "https://123-56-217-104.sslip.io:8090"}" placeholder="https://123-56-217-104.sslip.io:8090">
    <div class="hint" style="margin-top:4px">默认填的是线上网站：登录后录入的题会直接同步到线上错题本（全家可见）。填 127.0.0.1:8011 则只进本机数据库。</div>
    <label>网站账号 / 密码（可不填）</label>
    <div class="row" style="flex-wrap:nowrap">
      <input id="userName" placeholder="账号（如 sunny）" style="flex:1">
      <input id="userPass" type="password" placeholder="密码" style="flex:1">
    </div>
    <div class="hint" style="margin-top:4px">不登录也能同步：工具会用访客身份写入<b>家庭共享错题本</b>。登录只是让 AI 次数记在你自己账上，并能显示是谁录入的。</div>
    <div class="row" style="margin-top:10px">
      <button class="primary" id="btnLogin">登录网站</button>
      <button id="btnLogout">退出登录</button>
    </div>
    <hr style="border:none;border-top:1px solid var(--line);margin:16px 0">
    <b style="font-size:13px">本地 AI 端点（OpenAI 兼容视觉接口，推荐配置）</b>
    <div class="hint">配置后本机 AI 优先：题目识别与「补全解析」都走本地端点，<b>覆盖远端网站 AI</b>，不占网站每日限额；不配置则走网站站内 AI 通道。</div>
    <label>Base URL</label>
    <input id="cBase" value="${s.custom_base_url || ""}" placeholder="https://api.deepseek.com/v1">
    <label>API Key</label>
    <input id="cKey" type="password" placeholder="${s.custom_ready ? "已保存（输入则覆盖）" : "sk-..."}">
    <label>模型名</label>
    <input id="cModel" value="${s.custom_model || ""}" placeholder="如 qwen-vl-plus">
    <div class="row" style="margin-top:10px">
      <button class="primary" id="btnSaveCustom">保存本地 AI 端点</button>
      <button id="btnClearCustom">清除本地 AI 端点</button>
    </div>
    <div class="row" style="margin-top:16px"><button id="btnClose">关闭</button></div>`;
  $("overlay").hidden = false;
  $("btnClose").onclick = () => { $("overlay").hidden = true; };
  $("btnLogin").onclick = async () => {
    try {
      const r = await api("/api/login", {
        site_url: $("siteUrl").value.trim(),
        username: $("userName").value.trim(),
        password: $("userPass").value,
      });
      toast(`已登录 ${r.username} @ ${r.site_url}`);
      refreshState(); loadTaxonomy();
    } catch (err) { toastErr(err); }
  };
  $("btnLogout").onclick = async () => { await api("/api/logout", {}); toast("已退出"); refreshState(); };
  $("btnSaveCustom").onclick = async () => {
    try {
      await api("/api/custom", {
        base_url: $("cBase").value.trim(),
        api_key: $("cKey").value.trim(),
        model: $("cModel").value.trim(),
      });
      toast("自定义端点已保存"); refreshState();
    } catch (err) { toastErr(err); }
  };
  $("btnClearCustom").onclick = async () => { await api("/api/custom/clear", {}); toast("已清除"); refreshState(); };
}

async function loadTaxonomy() {
  try {
    const raw = await api("/api/taxonomy");
    state.taxonomy = {};
    for (const s of raw.subjects || []) {
      state.taxonomy[s.id] = { label: s.label, chapters: (s.chapters || []).map((c) => [c.id, c.label]) };
    }
  } catch { /* 未登录时静默，编辑表单里用默认学科 */ }
}

/* ---------------- 扫描 ---------------- */
$("btnScan").onclick = async () => {
  const folder = $("folder").value.trim();
  if (!folder) { toast("请填写文件夹路径"); return; }
  $("btnScan").disabled = true; $("btnScan").textContent = "扫描中…";
  try {
    const r = await api("/api/scan", { folder });
    state.files = r.files;
    $("scanInfo").textContent = `共 ${r.count} 张（去重后）`;
    $("gridPanel").style.display = "";
    renderGrid();
  } catch (err) { toastErr(err); }
  $("btnScan").disabled = false; $("btnScan").textContent = "扫描";
};

function renderGrid() {
  const grid = $("grid");
  grid.innerHTML = "";
  for (const f of state.files) {
    const card = document.createElement("div");
    card.className = "thumb";
    card.innerHTML = `<img src="/api/image?path=${encodeURIComponent(f.path)}" loading="lazy" alt="">
      ${state.done.has(f.path) ? '<span class="done">已录入</span>' : ""}
      <button class="auto-btn" title="一键自动识别这道题">⚡</button>`;
    card.title = f.path;
    card.onclick = () => openCrop(f);
    card.querySelector(".auto-btn").onclick = (e) => {
      e.stopPropagation();
      autoProcess([f]);
    };
    grid.appendChild(card);
  }
}

/* ---------------- 裁剪 ---------------- */
function openCrop(file) {
  const sheet = $("sheet");
  sheet.innerHTML = `
    <div class="tag" style="word-break:break-all">${file.path}</div>
    <div id="cropWrap" style="margin-top:10px">
      <canvas id="cropCanvas"></canvas>
      <div id="cropBox" style="display:none"></div>
    </div>
    <div class="hint" style="margin-top:8px">在图上拖出矩形，框住一道完整题目（题干+选项）。双击重选。</div>
    <div class="row" style="margin-top:12px">
      <button class="primary" id="btnRecognize" disabled>🤖 AI 识别所选区域</button>
      <span id="cropInfo" class="tag"></span>
      <div class="grow"></div>
      <button id="btnCropClose">关闭</button>
    </div>
    <div id="editArea"></div>`;
  $("overlay").hidden = false;
  $("btnCropClose").onclick = () => { $("overlay").hidden = true; };

  const img = new Image();
  img.crossOrigin = "anonymous";
  img.onload = () => {
    const canvas = $("cropCanvas");
    const MAXW = 900;
    const scale = Math.min(1, MAXW / img.naturalWidth);
    canvas.width = Math.round(img.naturalWidth * scale);
    canvas.height = Math.round(img.naturalHeight * scale);
    canvas.getContext("2d").drawImage(img, 0, 0, canvas.width, canvas.height);
    setupDrag(canvas, file, img);
  };
  img.onerror = () => toast("图片加载失败");
  img.src = `/api/image?path=${encodeURIComponent(file.path)}`;
}

function setupDrag(canvas, file, img) {
  const box = $("cropBox");
  let sx = 0, sy = 0, dragging = false;
  const start = (e) => {
    const r = canvas.getBoundingClientRect();
    const p = e.touches ? e.touches[0] : e;
    sx = p.clientX - r.left; sy = p.clientY - r.top;
    dragging = true; box.style.display = "block";
    moveBox(sx, sy, sx, sy);
  };
  const move = (e) => {
    if (!dragging) return;
    e.preventDefault?.();
    const r = canvas.getBoundingClientRect();
    const p = e.touches ? e.touches[0] : e;
    moveBox(sx, sy, p.clientX - r.left, p.clientY - r.top);
  };
  const end = (e) => {
    if (!dragging) return;
    dragging = false;
    const r = canvas.getBoundingClientRect();
    const p = e.changedTouches ? e.changedTouches[0] : e;
    const [x1, y1, x2, y2] = norm(sx, sy, p.clientX - r.left, p.clientY - r.top);
    if ((x2 - x1) * (y2 - y1) > 1000) {
      $("btnRecognize").disabled = false;
      $("cropInfo").textContent = "已选区域 ✓";
    }
  };
  function norm(x1, y1, x2, y2) {
    return [Math.min(x1, x2), Math.min(y1, y2), Math.max(x1, x2), Math.max(y1, y2)];
  }
  function moveBox(x1, y1, x2, y2) {
    const [a, b, c, d] = norm(x1, y1, x2, y2);
    box.style.left = a + "px"; box.style.top = b + "px";
    box.style.width = (c - a) + "px"; box.style.height = (d - b) + "px";
  }
  canvas.onpointerdown = start; canvas.onpointermove = move;
  canvas.onpointerup = end; canvas.onpointerleave = end;
  canvas.ondblclick = () => { box.style.display = "none"; $("btnRecognize").disabled = true; $("cropInfo").textContent = ""; };
  // 保存当前裁剪为 base64（含放大回原图坐标）
  window.__cropToB64 = () => {
    const r = canvas.getBoundingClientRect();
    // 用最后一次 box 位置
    const [a, b, c, d] = [parseFloat(box.style.left), parseFloat(box.style.top),
      parseFloat(box.style.left) + parseFloat(box.style.width),
      parseFloat(box.style.top) + parseFloat(box.style.height)];
    const k = img.naturalWidth / canvas.width;
    const cw = Math.round((c - a) * k), ch = Math.round((d - b) * k);
    const off = document.createElement("canvas");
    const MAXSIDE = 1600;                       // 识别用图限制在 1600px 内
    const ks = Math.min(1, MAXSIDE / Math.max(cw, ch));
    off.width = Math.round(cw * ks); off.height = Math.round(ch * ks);
    off.getContext("2d").drawImage(img,
      a * k, b * k, (c - a) * k, (d - b) * k,
      0, 0, off.width, off.height);
    return off.toDataURL("image/jpeg", 0.9);
  };
}

/* ---------------- 识别 + 编辑表单 ---------------- */
function bindRecognize(file) {
  $("btnRecognize").onclick = async () => {
    const btn = $("btnRecognize");
    btn.disabled = true; btn.textContent = "识别中…";
    try {
      const image = window.__cropToB64();
      const r = await api("/api/recognize", { image });
      openEditor(file, r.result);
    } catch (err) {
      toastErr(err);
      // 识别失败也允许手工录入
      openEditor(file, {});
    }
    btn.textContent = "🤖 AI 识别所选区域";
  };
}

function subjectOptions(sel) {
  const entries = Object.entries(SUBJECTS);
  return entries.map(([id, label]) =>
    `<option value="${id}" ${sel === id ? "selected" : ""}>${label}</option>`).join("");
}

function openEditor(file, recog) {
  const sheet = $("sheet");
  const subjects = state.taxonomy || {};
  const subjId = recog.subject && subjects[recog.subject] ? recog.subject : "";
  const chapters = subjects[subjId]?.chapters || [];
  sheet.innerHTML = `
    <div class="row"><b>✏️ 核对题目并补充错因</b><div class="grow"></div>
      <span class="tag">${recog.model ? "识别模型：" + recog.model : "手工录入"}</span></div>
    <label>题干（必填）</label>
    <textarea id="fStem" rows="4" placeholder="AI 识别结果，或手工输入题干">${recog.stem || ""}</textarea>
    <label>题型</label>
    <select id="fQtype">
      <option value="choice">单选题（有 A/B/C/D）</option>
      <option value="multi_choice">多选题（有 A/B/C/D）</option>
      <option value="fill">填空题（横线填答案）</option>
      <option value="solution">解答题（写过程）</option>
    </select>
    <div id="choiceBox">
      <label>选项（每行一个）</label>
      <textarea id="fOptions" rows="4">${(recog.options || []).join("\n")}</textarea>
      <div class="row" id="singleChoiceFields">
        <div style="flex:1;min-width:120px"><label>我的错选</label><select id="fPicked"></select></div>
        <div style="flex:1;min-width:120px"><label>正确答案</label><select id="fAnswer"></select></div>
      </div>
      <div id="multiChoiceFields" style="display:none">
        <label>我的错选（可多选）</label><div id="fPickedMulti" class="row"></div>
        <label>正确答案（可多选，未知时留空待补录）</label><div id="fAnswerMulti" class="row"></div>
      </div>
    </div>
    <div id="fillBox" style="display:none">
      <label>正确答案（填空/解答题）</label>
      <input id="fAnsText" placeholder="如：2 或 (−∞,3−2√2]">
      <div class="hint" style="margin-top:4px">重做时按文本比对判分；可点下方「AI 补全解析」自动生成。</div>
    </div>
    <div class="row">
      <div style="flex:1;min-width:130px"><label>学科</label>
        <select id="fSubject">${subjectOptions(subjId)}</select></div>
      <div style="flex:1;min-width:130px"><label>章节</label>
        <select id="fChapter"></select></div>
      <div style="flex:1;min-width:130px"><label>考点标签</label>
        <input id="fSkill" placeholder="如：平均速度"></div>
    </div>
    <label>解析 / 正确答案依据（可选）</label>
    <textarea id="fExplain" rows="2"></textarea>
    <label>🎯 为什么会错（错因记录）</label>
    <textarea id="fReason" rows="2" placeholder="如：把平均速度当成 vB 的瞬时速度；公式适用条件记错"></textarea>
    <label>✍️ 正确解法过程推导（可选，支持换行）</label>
    <textarea id="fDerivation" rows="4" placeholder="逐步写清推导过程…"></textarea>
    <div class="row" style="margin-top:14px">
      <button class="primary" id="btnAiFill">🤖 本地 AI 补全解析</button>
      <span id="aiFillInfo" class="tag"></span>
    </div>
    <div class="hint" id="aiFillHint" style="margin-top:6px">配置了本地 AI 端点时可用：独立解题 → 填正确答案/推导/错因提示，不占用网站 AI 限额。</div>
    <div class="row" style="margin-top:12px">
      <button class="ok" id="btnQueue">✅ 加入待导入清单</button>
      <button id="btnEditorClose">取消</button>
    </div>`;
  const optsText = $("fOptions");
  const qtypeSel = $("fQtype");
  qtypeSel.value = recog.qtype || ((recog.options || []).filter((o) => String(o).trim()).length >= 2 ? "choice" : "fill");
  if ($("fAnsText")) $("fAnsText").value = recog.answer_text || "";
  const syncChoice = () => {
    const isChoice = ["choice", "multi_choice"].includes(qtypeSel.value);
    const isMulti = qtypeSel.value === "multi_choice";
    $("choiceBox").style.display = isChoice ? "" : "none";
    $("singleChoiceFields").style.display = isMulti ? "none" : "";
    $("multiChoiceFields").style.display = isMulti ? "" : "none";
    $("fillBox").style.display = isChoice ? "none" : "";
    if (!isChoice) return;
    const opts = optsText.value.split("\n").map((s) => s.trim()).filter(Boolean);
    const n = Math.min(opts.length, 8);
    const mk = (name) => Array.from({ length: n }, (_, i) =>
      `<label style="display:flex;gap:4px;align-items:center"><input type="checkbox" data-set="${name}" value="${i}">${LETTERS[i] || i + 1}</label>`).join("");
    if (isMulti) {
      $("fPickedMulti").innerHTML = mk("picked");
      $("fAnswerMulti").innerHTML = mk("answer");
    } else {
      const select = (sel) => Array.from({ length: n }, (_, i) =>
        `<option value="${i}" ${sel === i ? "selected" : ""}>${LETTERS[i] || i + 1}</option>`).join("");
      $("fPicked").innerHTML = select(0);
      $("fAnswer").innerHTML = `<option value="-1">?（未知）</option>` + select(-1);
    }
  };
  qtypeSel.onchange = syncChoice;
  optsText.addEventListener("input", syncChoice);
  syncChoice();
  const fillChapters = () => {
    const sid = $("fSubject").value;
    const chs = (state.taxonomy?.[sid]?.chapters) || chapters;
    $("fChapter").innerHTML = '<option value="">未分类</option>' +
      chs.map(([id, label]) => `<option value="${id}">${label}</option>`).join("");
  };
  $("fSubject").innerHTML = subjects && Object.keys(subjects).length
    ? Object.entries(subjects).map(([id, s]) =>
        `<option value="${id}" ${subjId === id ? "selected" : ""}>${s.label}</option>`).join("")
    : subjectOptions(subjId);
  $("fSubject").onchange = fillChapters;
  fillChapters();
  // 本地 AI 补全：独立解题 → 自动填答案/解析/推导/错因提示（覆盖远端 AI，不占网站限额）
  $("btnAiFill").onclick = async () => {
    const btn = $("btnAiFill");
    const stem = $("fStem").value.trim();
    if (!stem) { toast("请先填写或识别题干"); return; }
    btn.disabled = true; btn.textContent = "解题中…";
    try {
      const image = (state.__currentFile && window.__cropToB64) ? window.__cropToB64() : "";
      const r = await api("/api/ai/complete", {
        image, stem,
        qtype: qtypeSel.value,
        options: qtypeSel.value === "choice"
          ? optsText.value.split("\n").map((s) => s.trim()).filter(Boolean) : [],
      });
      if (r.answer_index >= 0) $("fAnswer").value = String(r.answer_index);
      if (qtypeSel.value !== "choice" && r.answer_text) $("fAnsText").value = r.answer_text;
      if (r.explain && !$("fExplain").value.trim()) $("fExplain").value = r.explain;
      if (r.derivation) $("fDerivation").value = r.derivation;
      if (r.mistake_hint && !$("fReason").value.trim()) $("fReason").value = r.mistake_hint;
      $("aiFillInfo").textContent = `✓ 已填入（${r.model}）`;
    } catch (err) {
      toastErr(err);
      $("aiFillInfo").textContent = "补全失败，可手工填写";
    }
    btn.disabled = false; btn.textContent = "🤖 本地 AI 补全解析";
  };
  $("btnEditorClose").onclick = () => openCrop(file);
  $("btnQueue").onclick = () => {
    const stem = $("fStem").value.trim();
    if (!stem) { toast("题干不能为空"); return; }
    const opts = optsText.value.split("\n").map((s) => s.trim()).filter(Boolean);
    const qtype = qtypeSel.value;
    const ansText = ($("fAnsText")?.value || "").trim();
    if (["choice", "multi_choice"].includes(qtype) && opts.length < 2) { toast("选择题至少两个选项"); return; }
    if (!(["choice", "multi_choice"].includes(qtype)) && !ansText) { toast("填空题请填写正确答案（可点「AI 补全解析」）"); return; }
    const checked = (name) => [...document.querySelectorAll(`#choiceBox input[data-set="${name}"]:checked`)].map(x => Number(x.value));
    const answerIndices = qtype === "multi_choice" ? checked("answer") : [];
    const pickedIndices = qtype === "multi_choice" ? checked("picked") : [];
    const singleAnswer = qtype === "choice" ? parseInt($("fAnswer").value, 10) : -1;
    state.queue.push({
      stem,
      qtype,
      answer_text: ["choice", "multi_choice"].includes(qtype) ? "" : ansText,
      options: ["choice", "multi_choice"].includes(qtype) ? opts : [],
      answer_indices: answerIndices,
      picked_indices: pickedIndices,
      review_status: qtype === "multi_choice" && !answerIndices.length || qtype === "choice" && singleAnswer < 0 ? "needs_transcription" : "ready",
      review_reason: "标准答案待核对",
      picked: qtype === "multi_choice" ? (pickedIndices[0] ?? -1) : qtype === "choice" ? parseInt($("fPicked").value, 10) : -1,
      answer: singleAnswer,
      subject: $("fSubject").value,
      chapter: $("fChapter").value,
      skill: $("fSkill").value.trim(),
      explain: $("fExplain").value.trim(),
      wrong_reason: $("fReason").value.trim(),
      derivation: $("fDerivation").value.trim(),
      __src: file.path,
    });
    state.done.add(file.path);
    toast("已加入待导入清单");
    renderGrid(); renderQueue();
    loadMobileList();
    $("overlay").hidden = true;
  };
}

/* ---------------- 待导入清单 ---------------- */
function renderQueue() {
  $("queuePanel").style.display = state.queue.length ? "" : "none";
  $("queueCount").textContent = `${state.queue.length} 题`;
  const q = $("queue");
  q.innerHTML = "";
  state.queue.forEach((it, i) => {
    const div = document.createElement("div");
    div.className = "qitem";
    const subj = state.taxonomy?.[it.subject]?.label || SUBJECTS[it.subject] || "未分类";
    const chap = state.taxonomy?.[it.subject]?.chapters?.find(([id]) => id === it.chapter)?.[1] || "";
    const typeLabel = { choice: "选择", fill: "填空", solution: "解答" }[it.qtype || "choice"] || "选择";
    const ansLabel = (it.qtype || "choice") === "choice"
      ? `答案 ${LETTERS[it.answer] ?? "?"} / 错选 ${LETTERS[it.picked] ?? "?"}`
      : `答案：${it.answer_text || "（缺）"}`;
    div.innerHTML = `<div class="stem">${ansLabel} · ${it.stem.slice(0, 50)}…</div>
      <div class="tag">${typeLabel} · ${subj}${chap ? " · " + chap : ""} ${it.wrong_reason ? "· 错因已记" : "· ⚠️ 缺错因"}</div>
      <div class="row" style="margin-top:6px"><button data-i="${i}" class="btn-del">移除</button></div>`;
    div.querySelector(".btn-del").onclick = () => {
      state.done.delete(it.__src);
      state.queue.splice(i, 1);
      renderQueue(); renderGrid();
    };
    q.appendChild(div);
  });
}

async function importQueue(opts = {}) {
  if (!state.queue.length) {
    if (!opts.silent) toast("清单为空");
    return false;
  }
  const btn = $("btnImport");
  if (btn) { btn.disabled = true; btn.textContent = "同步中…"; }
  try {
    // 只传业务字段；overwrite=false 让网站按题干去重（重复录入不会重复累加）
    const items = state.queue.map(({ __src, ...rest }) => rest);
    const r = await api("/api/import", { items });
    const n = (r.imported || []).length, u = (r.updated || []).length, s = (r.skipped || []).length;
    const site = r.site_url || (state.info && (state.info.effective_site || state.info.site_url)) || "";
    $("importResult").textContent = n + u
      ? `✅ 已同步 ${n + u} 题到 ${site}（新增 ${n} · 更新 ${u} · 重复跳过 ${s}），打开网站「错题本」全家可见。`
      : `没有新题：${s} 题与网站上已有的重复（可到网站错题本查看）。`;
    state.queue = [];
    renderQueue(); refreshState();
    return true;
  } catch (err) {
    const msg = /401|登录/.test(err.message || "") ? "未登录网站：请点右上角「连接设置」登录后再导入" : err.message;
    toastErr({ message: msg });
    $("importResult").textContent = `❌ 同步失败：${msg}`;
    return false;
  } finally {
    if (btn) { btn.disabled = false; btn.textContent = "批量导入到网站错题本"; }
  }
}

$("btnImport").onclick = () => importQueue();

/* ---------------- 一键全自动 ---------------- */
function loadImg(src) {
  return new Promise((resolve, reject) => {
    const img = new Image();
    img.crossOrigin = "anonymous";
    img.onload = () => resolve(img);
    img.onerror = () => reject(new Error("图片加载失败"));
    img.src = src;
  });
}

function toB64(img, maxSide = 1600, quality = 0.88) {
  const k = Math.min(1, maxSide / Math.max(img.naturalWidth, img.naturalHeight));
  const c = document.createElement("canvas");
  c.width = Math.round(img.naturalWidth * k);
  c.height = Math.round(img.naturalHeight * k);
  c.getContext("2d").drawImage(img, 0, 0, c.width, c.height);
  return c.toDataURL("image/jpeg", quality);
}

function cropB64(img, bbox) {
  // bbox 归一化 [x,y,w,h]，裁出来再放大一点余量
  const [x, y, w, h] = bbox;
  const pad = 0.01;
  const x0 = Math.max(0, (x - pad)) * img.naturalWidth;
  const y0 = Math.max(0, (y - pad)) * img.naturalHeight;
  const x1 = Math.min(1, (x + w + pad)) * img.naturalWidth;
  const y1 = Math.min(1, (y + h + pad)) * img.naturalHeight;
  if (x1 - x0 < 20 || y1 - y0 < 20) return null;
  const c = document.createElement("canvas");
  c.width = Math.round(x1 - x0);
  c.height = Math.round(y1 - y0);
  c.getContext("2d").drawImage(img, x0, y0, c.width, c.height, 0, 0, c.width, c.height);
  return c.toDataURL("image/jpeg", 0.9);
}

function normalizeItem(it) {
  const options = (it.options || []).filter((o) => String(o).trim());
  let qtype = String(it.qtype || "").toLowerCase();
  if (!["choice", "fill", "solution"].includes(qtype)) qtype = options.length >= 2 ? "choice" : "fill";
  if (qtype === "choice" && options.length < 2) qtype = "fill";
  const n = Math.max(options.length, 2);
  const clamp = (v, d) => (qtype === "choice" && Number.isInteger(v) && v >= 0 && v < n ? v : d);
  return {
    stem: it.stem,
    qtype,
    answer_text: qtype === "choice" ? "" : (it.answer_text || ""),
    options: qtype === "choice" ? options : [],
    picked: qtype === "choice" ? clamp(it.picked, 0) : -1,
    answer: qtype === "choice" ? clamp(it.answer, 0) : -1,
    subject: it.subject || "",
    chapter: it.chapter || "",
    skill: it.skill || "",
    explain: it.explain || "",
    wrong_reason: it.wrong_reason || "",
    derivation: it.derivation || "",
    image_path: it.image_path || "",
  };
}

let autoBusy = false;
async function autoProcess(files) {
  if (autoBusy) { toast("正在处理中，请稍候"); return; }
  if (!files.length) { toast("没有可处理的图片"); return; }
  autoBusy = true;
  const info = $("autoInfo");
  let total = 0, imgCount = 0, usedChannel = "", imgFail = 0;
  for (let i = 0; i < files.length; i += 1) {
    const f = files[i];
    if (state.done.has(f.path)) continue;
    info.textContent = `处理中 ${i + 1}/${files.length}…（约每题 10–30 秒）`;
    try {
      const img = await loadImg(`/api/image?path=${encodeURIComponent(f.path)}`);
      const full = toB64(img);
      const r = await api("/api/ai/auto", { image: full });
      usedChannel = r.channel || usedChannel;
      const items = r.items || [];
      if (!items.length) { toast("这张图没找到题目"); continue; }
      for (const raw of items) {
        const it = normalizeItem(raw);
        let crop = raw.bbox ? cropB64(img, raw.bbox) : null;
        let imagePath = "";
        try {
          imagePath = (await api("/api/import-image", { image: crop || full })).path;
        } catch (err) {
          // 未登录网站时不阻塞：先入清单，导入时仍可只存文字
          imagePath = "";
          imgFail += 1;
        }
        it.image_path = imagePath;
        state.queue.push({ ...it, __src: f.path });
        total += 1;
      }
      state.done.add(f.path);
      imgCount += 1;
      renderGrid(); renderQueue(); loadMobileList();
    } catch (err) {
      toast(`第 ${i + 1} 张失败：${err.message || err}`);
    }
  }
  const chLabel = { "workbuddy-local": "WorkBuddy 本地 AI", "local-custom": "本地自定义 AI", site: "网站 AI（兜底）" }[usedChannel] || usedChannel;
  info.textContent = total ? `✓ ${imgCount} 张图 → ${total} 题（${chLabel}）` : "未识别到题目";
  if (total) toast(`已自动整理 ${total} 题，检查后点「批量导入」`);
  if (imgFail) toast(`有 ${imgFail} 题配图上传失败（可能未登录网站），文字部分仍可导入`);
  autoBusy = false;

  // 处理完自动同步：否则会出现「AI 整理完了，网站错题本还是空的」
  const autoSync = $("chkAutoImport");
  if (total && autoSync && autoSync.checked) {
    info.textContent += " · 正在同步到网站…";
    const ok = await importQueue({ silent: true });
    info.textContent = info.textContent.replace(" · 正在同步到网站…", ok ? " · ✅ 已同步到网站" : " · ⚠️ 同步失败，见下方提示");
  }
}

$("btnAutoAll").onclick = () => {
  const files = [...(state.files || [])];
  if (!files.length) { toast("先扫描文件夹"); return; }
  autoProcess(files);
};

/* ---------------- 手机上传 ---------------- */
let mobileSeen = new Set();   // 已见过的手机上传文件（避免重复自动处理）

async function pollMobileAuto() {
  const box = $("autoAfterUpload");
  if (!box || !box.checked || autoBusy) return;
  try {
    const r = await api("/api/mobile/list");
    const fresh = (r.files || []).filter((f) => !mobileSeen.has(f.path) && !state.done.has(f.path));
    for (const f of r.files || []) mobileSeen.add(f.path);
    if (fresh.length) {
      loadMobileList();
      autoProcess(fresh);       // 手机一拍完 → 自动切题+识别+解析
    }
  } catch { /* 静默 */ }
}

async function loadLanInfo() {
  try {
    const info = await api("/api/lan-info");
    $("mobilePanel").style.display = "";
    $("lanUrl").textContent = info.mobile_page;
    if (info.qr) {
      $("qrImg").src = "data:image/svg+xml;base64," + info.qr;
      $("qrImg").style.display = "block";
    }
  } catch { /* 工具未启动时静默 */ }
}

async function loadMobileList() {
  try {
    const r = await api("/api/mobile/list");
    const grid = $("mobileGrid");
    grid.innerHTML = "";
    $("mobilePanel").style.display = "";
    for (const f of r.files) mobileSeen.add(f.path);   // 已列出的不再自动处理
    if (!r.files.length) {
      grid.innerHTML = '<div class="hint">暂无手机上传的图片。手机打开上面地址拍一张试试。</div>';
      return;
    }
    for (const f of r.files) {
      const card = document.createElement("div");
      card.className = "thumb";
      card.innerHTML = `<img src="/api/image?path=${encodeURIComponent(f.path)}" loading="lazy" alt="">
        ${state.done.has(f.path) ? '<span class="done">已录入</span>' : ""}
        <button class="auto-btn" title="一键自动识别这道题">⚡</button>`;
      card.onclick = () => openCrop(f);
      card.querySelector(".auto-btn").onclick = (e) => {
        e.stopPropagation();
        autoProcess([f]);
      };
      const del = document.createElement("button");
      del.textContent = "删除";
      del.style.cssText = "margin-top:4px;font-size:11px;padding:3px 8px";
      del.onclick = async (e) => {
        e.stopPropagation();
        await api("/api/mobile/delete", { path: f.path });
        state.done.delete(f.path);
        loadMobileList();
      };
      card.appendChild(del);
      grid.appendChild(card);
    }
  } catch { /* 静默 */ }
}

/* ---------------- 启动 ---------------- */
$("btnSettings").onclick = openSettings;
$("btnMobileRefresh").onclick = loadMobileList;
// 识别按钮在 sheet 动态生成后绑定（MutationObserver 兜底）
new MutationObserver(() => {
  const btn = $("btnRecognize");
  if (btn && !btn.dataset.bound && state.__currentFile) {
    btn.dataset.bound = "1";
    bindRecognize(state.__currentFile);
  }
}).observe($("sheet"), { childList: true, subtree: true });
// 记录当前编辑的文件
const _openCrop = openCrop;
openCrop = function (file) { state.__currentFile = file; _openCrop(file); };

refreshState();
loadTaxonomy();
loadLanInfo();
loadMobileList().then(() => setInterval(pollMobileAuto, 6000));
