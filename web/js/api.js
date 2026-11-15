/* API 客户端 + 本地身份存储 */

const TOKEN_KEY = 'learn.token';
const ME_KEY = 'learn.me';
const EXPIRY_KEY = 'learn.session-expires-at';

export function getToken() {
  const expires = Number(localStorage.getItem(EXPIRY_KEY));
  if (expires && Date.now() >= expires * 1000) {
    logout();
    return '';
  }
  return localStorage.getItem(TOKEN_KEY) || '';
}

export function setToken(t) {
  if (t) localStorage.setItem(TOKEN_KEY, t);
  else {
    localStorage.removeItem(TOKEN_KEY);
    localStorage.removeItem(EXPIRY_KEY);
  }
}

export function getMeCache() {
  try { return JSON.parse(localStorage.getItem(ME_KEY) || 'null'); } catch { return null; }
}

export function setMeCache(me) {
  if (me?.session_expires_at) localStorage.setItem(EXPIRY_KEY, String(me.session_expires_at));
  if (me) localStorage.setItem(ME_KEY, JSON.stringify(me));
  else localStorage.removeItem(ME_KEY);
}

export class ApiError extends Error {
  constructor(status, detail) {
    super(detail || `请求失败 (${status})`);
    this.status = status;
    this.detail = detail;
  }
}

async function request(path, { method = 'GET', body, auth = true } = {}) {
  const headers = { 'Accept': 'application/json' };
  if (body !== undefined) headers['Content-Type'] = 'application/json';
  const token = getToken();
  if (auth && token) headers['Authorization'] = `Bearer ${token}`;

  let res;
  try {
    res = await fetch(`/api/v1${path}`, {
      method,
      headers,
      body: body === undefined ? undefined : JSON.stringify(body),
    });
  } catch (e) {
    throw new ApiError(0, '网络连接失败，请检查网络');
  }

  let data = null;
  const text = await res.text();
  if (text) {
    try { data = JSON.parse(text); } catch { /* 非 JSON */ }
  }

  if (!res.ok) {
    const detail = data?.error?.message || data?.detail || `请求失败 (${res.status})`;
    throw new ApiError(res.status, typeof detail === 'string' ? detail : JSON.stringify(detail));
  }
  return data;
}

/* ---------- 会话 ---------- */

export async function ensureSession() {
  if (getToken()) return getMeCache();
  const data = await request('/session', { method: 'POST', auth: false });
  setToken(data.token);
  setMeCache(data);
  return data;
}

/** 账号密码登录。成功后保存 token。 */
export async function login(username, password, accountType) {
  const data = await request('/session/login', {
    method: 'POST',
    body: { username, password, ...(accountType ? { account_type: accountType } : {}) },
    auth: false,
  });
  setToken(data.token);
  setMeCache(data);
  return data;
}

/** 访客免密一键体验登录（用于公开演示）。 */
export async function guestLogin() {
  const data = await request('/session/guest', {
    method: 'POST',
    auth: false,
  });
  setToken(data.token);
  setMeCache(data);
  return data;
}

/** 已登记账号（登录页展示，仅用户名与昵称）。 */
export const listUsers = () => request('/session/users', { auth: false });
export const createStudent = (body) => request('/admin/students', { method: 'POST', body });

/** 修改自己的密码。 */
export const changePassword = (oldPassword, newPassword) =>
  request('/session/password', {
    method: 'POST',
    body: { old_password: oldPassword, new_password: newPassword },
  });

/** 退出登录：清掉本地令牌。 */
export function logout() {
  setToken('');
  setMeCache(null);
}

/** 主动退出时撤销服务端会话。普通的本地清理不触发网络请求。 */
export async function signOut() {
  try {
    if (getToken()) await request('/session/logout', { method: 'POST' });
  } catch (err) {
    if (err.status !== 401) throw err;
  }
  logout();
}

export async function adoptByCode(code) {
  const data = await request('/session/adopt', { method: 'POST', body: { sync_code: code }, auth: false });
  setToken(data.token);
  setMeCache(data);
  return data;
}

export async function fetchMe() {
  const me = await request('/me');
  setMeCache(me);
  return me;
}

export async function rotateCode() {
  return request('/session/rotate-code', { method: 'POST' });
}

/* ---------- 内容 ---------- */

export const getCatalog = () => request('/catalog');
export const getDaily = (day) => request(day ? `/daily?date=${encodeURIComponent(day)}` : '/daily');
export const getHistory = (day) => request(day ? `/history?date=${encodeURIComponent(day)}` : '/history');
export const getTopic = (id) => request(`/topics/${id}`);
export const getSection = (id, sid, tier = 'basic') =>
  request(`/topics/${id}/sections/${sid}?tier=${encodeURIComponent(tier)}`);
export const submitSection = (id, sid, answers, tier = 'basic') =>
  request(`/topics/${id}/sections/${sid}/submit?tier=${encodeURIComponent(tier)}`,
    { method: 'POST', body: { answers } });
export const markRead = (id, sid, tier = 'basic') =>
  request(`/topics/${id}/sections/${sid}/read?tier=${encodeURIComponent(tier)}`,
    { method: 'POST', body: { confirmed: true } });
export const getProgress = () => request('/progress');

/* ---------- 签到 ---------- */

export const getCheckin = () => request('/checkin');
export const doCheckin = () => request('/checkin', { method: 'POST' });

/* ---------- 卡册 ---------- */

export const getCards = () => request('/cards');
export const drawCards = (count, key) =>
  request('/cards/draw', { method: 'POST', body: { count, idempotency_key: key } });
export const craftCard = (cardId) =>
  request('/cards/craft', { method: 'POST', body: { card_id: cardId } });

/* ---------- 成就卡 ---------- */

export const getAchievements = () => request('/achievements');
export const redeemAchievement = (count = 1) =>
  request('/achievements/redeem', { method: 'POST', body: { count } });
export const verifyAchievement = (code) =>
  request('/achievements/verify', { method: 'POST', body: { code } });

/* ---------- 每日随机卡 / 赠送 ---------- */

export const getDailyDraw = () => request('/achievements/daily');
export const drawDaily = () => request('/achievements/daily/draw', { method: 'POST' });
export const giftCard = (cardId, toUsername = 'sunny') =>
  request('/achievements/gift', { method: 'POST', body: { card_id: cardId, to_username: toUsername } });
export const getReceivedCards = () => request('/achievements/received');

/* ---------- 核销权限 ---------- */

export const getVerifyPermission = () => request('/achievements/verify-permission');


/* ---------- 错题本 ---------- */

export const getWrongbook = () => request('/wrongbook');
export const getWrongTopic = (tid) => request(`/wrongbook/${tid}`);
export const redoWrongbook = (tid, answers) =>
  request(`/wrongbook/${tid}/redo`, { method: 'POST', body: { answers } });
export const analyzeWrong = (ids) =>
  request('/wrongbook/ai', { method: 'POST', body: { ids } });
export const solveWrong = (ids) =>
  request('/wrongbook/ai/solve', { method: 'POST', body: { ids } });
export const variantsWrong = (id, n = 2) =>
  request('/wrongbook/ai/variants', { method: 'POST', body: { id, n } });

/* ---------- 管理中心（仅管理员） ---------- */

export const getAdminAiConfig = () => request('/admin/ai/config');
export const putAdminAiConfig = (patch) =>
  request('/admin/ai/config', { method: 'PUT', body: patch });
export const resetAdminAi = () => request('/admin/ai/reset', { method: 'POST' });
export const adminAiTest = (task) =>
  request('/admin/ai/test', { method: 'POST', body: { task } });
export const adminAiUsage = (days = 1) => request(`/admin/ai/usage?days=${days}`);
export const adminUsers = () => request('/admin/users');

/* ---------- 盲盒 ---------- */

export const getBlindbox = () => request('/blindbox');
export const drawBlindbox = (count, key) =>
  request('/blindbox/draw', { method: 'POST', body: { count, idempotency_key: key } });
export const exchangeBlindbox = (count = 1) =>
  request('/blindbox/exchange', { method: 'POST', body: { count } });
export const redeemBlindbox = (characterId) =>
  request('/blindbox/redeem', { method: 'POST', body: { character_id: characterId } });

/* ---------- 许愿墙 ---------- */

export const getWishes = () => request('/wishes');
export const postWish = (content) => request('/wishes', { method: 'POST', body: { content } });
export const adminWishes = () => request('/admin/wishes');
export const adminModerateWish = (id, status, reply) =>
  request(`/admin/wishes/${id}`, { method: 'PATCH', body: { status, reply } });

/* ---------- 拍照错题（演示） ---------- */

export const photoRecognize = (image) =>
  request('/wrongbook/photo/recognize', { method: 'POST', body: { image } });
export const photoAnalyze = (stem, options, picked) =>
  request('/wrongbook/photo/analyze', { method: 'POST', body: { stem, options, picked } });
export const photoSave = (payload) =>
  request('/wrongbook/photo/save', { method: 'POST', body: payload });

/* ---------- 题目问题反馈 ---------- */
export const postQuestionFeedback = (payload) => request('/question-feedback', { method: 'POST', body: payload });
export const getQuestionFeedback = () => request('/question-feedback');
export const adminQuestionFeedback = () => request('/admin/question-feedback');
export const reviewQuestionFeedback = (id, status, note) => request(`/admin/question-feedback/${id}`, { method: 'PATCH', body: { status, note } });

/* 考点专项与逐题总结 */
export const getExamTraining = () => request('/exam-training');
export const getExamModel = (id) => request(`/exam-training/${encodeURIComponent(id)}`);
export const answerExamQuestion = (id, question_id, picked) => request(`/exam-training/${encodeURIComponent(id)}/answer`, {method:'POST',body:{question_id,picked}});
export const postReflection = (body) => request('/reflections', {method:'POST',body});
export const getSectionReflections = (id,sid,tier='basic') => request(`/topics/${encodeURIComponent(id)}/sections/${encodeURIComponent(sid)}/reflections?tier=${encodeURIComponent(tier)}`);
