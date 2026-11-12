/* API 客户端 + 本地身份存储 */

const TOKEN_KEY = 'learn.token';
const ME_KEY = 'learn.me';

export function getToken() {
  return localStorage.getItem(TOKEN_KEY) || '';
}

export function setToken(t) {
  if (t) localStorage.setItem(TOKEN_KEY, t);
  else localStorage.removeItem(TOKEN_KEY);
}

export function getMeCache() {
  try { return JSON.parse(localStorage.getItem(ME_KEY) || 'null'); } catch { return null; }
}

export function setMeCache(me) {
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
export async function login(username, password) {
  const data = await request('/session/login', {
    method: 'POST',
    body: { username, password },
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
