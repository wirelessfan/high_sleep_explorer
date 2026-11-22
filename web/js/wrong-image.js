/* 错题配图：公开图直接当 src 用；拍照题的私有图要先带 token 取成 blob，再转成 objectURL。
 *
 * 错题本弹窗与打印试卷共用，避免两处各写一份鉴权逻辑。
 */

import * as api from './api.js';
import { el } from './ui.js';

const PRIVATE_PREFIX = '/api/v1/wrongbook/photo/image/';

export function wrongImage(path, { className, style, alt = '题目配图' } = {}) {
  const isPrivate = path.startsWith(PRIVATE_PREFIX);
  const attrs = { alt, loading: 'lazy' };
  if (className) attrs.class = className;
  if (style) attrs.style = style;
  if (!isPrivate) attrs.src = path;
  const img = el('img', attrs);

  // 兜底：极小/损坏的图直接不显示，避免页面里出现一个孤零零的小点
  img.addEventListener('load', () => {
    if (img.naturalWidth < 4 || img.naturalHeight < 4) img.remove();
  });

  if (isPrivate) {
    fetch(path, { headers: { Authorization: `Bearer ${api.getToken()}` } })
      .then((r) => { if (!r.ok) throw new Error('图片读取失败'); return r.blob(); })
      .then((blob) => {
        const url = URL.createObjectURL(blob);
        img.onload = () => URL.revokeObjectURL(url);
        img.src = url;
      })
      .catch(() => { img.alt = '图片读取失败，请重新登录后重试'; });
  }
  return img;
}
