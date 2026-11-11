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
export const getTopic = (id) => request(`/topics/${id}`);
export const getSection = (id, sid) => request(`/topics/${id}/sections/${sid}`);
export const submitSection = (id, sid, answers) =>
  request(`/topics/${id}/sections/${sid}/submit`, { method: 'POST', body: { answers } });
export const markRead = (id, sid) =>
  request(`/topics/${id}/sections/${sid}/read`, { method: 'POST', body: { confirmed: true } });
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
