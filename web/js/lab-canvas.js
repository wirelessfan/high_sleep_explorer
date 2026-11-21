/* 画布内文字统一放大工具
 *
 * 这些实验页的画布都是 740×310 的逻辑坐标，在手机上会被 CSS 缩到约 330 CSS px，
 * 于是 12px 的字实际只剩 5～6px，基本看不清。做法统一为：
 *   1. 字号直接按「放大后」的像素写（18～22px），
 *   2. 信息板不再写死宽高，改成按 measureText 自动撑开，字号变大也不会顶出框。
 */

/** 画布内的常用字号（逻辑 px，显示时会乘 330/740 ≈ 0.45） */
export const FS = {
  hud: '800 24px sans-serif',      // 信息板主行
  hudSub: '800 21px sans-serif',   // 信息板次行
  label: '800 19px sans-serif',    // 图上的标注
  small: '700 17px sans-serif',    // 刻度、小字
};

/**
 * 自适应信息板：按最宽一行算宽度，矩形在右上角时用 align:'right' 自动往左靠。
 * lines: [{ text, font, color }]，按顺序自上而下排。
 */
export function canvasHud(ctx, opts) {
  const {
    x, y, lines,
    pad = 14, lh = 34, align = 'left',
    bg = 'rgba(15,23,42,0.86)', stroke = null, radius = 12,
    border = 1.5,
  } = opts;

  let textW = 0;
  for (const ln of lines) {
    ctx.font = ln.font;
    textW = Math.max(textW, ctx.measureText(ln.text).width);
  }
  const w = Math.ceil(textW + pad * 2 + 4);
  const h = Math.ceil(pad * 2 + lines.length * lh - (lh - 24));
  const bx = align === 'right' ? Math.round(x - w) : Math.round(x);
  const by = Math.round(y);

  ctx.save();
  ctx.beginPath();
  ctx.roundRect(bx, by, w, h, radius);
  ctx.fillStyle = bg;
  ctx.fill();
  if (stroke) {
    ctx.strokeStyle = stroke;
    ctx.lineWidth = border;
    ctx.stroke();
  }
  lines.forEach((ln, i) => {
    ctx.font = ln.font;
    ctx.fillStyle = ln.color;
    ctx.fillText(ln.text, bx + pad, by + pad + i * lh + lh * 0.58);
  });
  ctx.restore();
  return { x: bx, y: by, w, h };
}
