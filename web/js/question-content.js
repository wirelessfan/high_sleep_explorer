/* Mathematical '<' is text; only explicitly supported note markup is HTML. */
const NOTE_TAG = /^<\/?(?:div|span|p|br|strong|em|b|i|sup|sub|img|small|ul|ol|li)(?:\s+[^<>]*)?\s*\/?>/i;

/* ---------- 公式美化：把 ASCII 的 x^2 / a_1 换成上标下标，纯显示层，不改存储 ---------- */
const SUP_MAP = { '0': '⁰', '1': '¹', '2': '²', '3': '³', '4': '⁴', '5': '⁵', '6': '⁶', '7': '⁷', '8': '⁸', '9': '⁹', '-': '⁻', '+': '⁺' };
const SUB_MAP = { '0': '₀', '1': '₁', '2': '₂', '3': '₃', '4': '₄', '5': '₅', '6': '₆', '7': '₇', '8': '₈', '9': '₉', '-': '₋', '+': '₊' };

function mapAllChars(str, table) {
  let out = '';
  for (const ch of str) {
    if (!table[ch]) return null;
    out += table[ch];
  }
  return out;
}

/** x^2 → x²，a_1 → a₁；遇到没有对应字符的写法原样保留 */
export function prettyMath(value) {
  return String(value ?? '')
    .replace(/\^\{?([-+]?\d{1,3})\}?/g, (m, digits) => mapAllChars(digits, SUP_MAP) ?? m)
    .replace(/_\{?([-+]?\d{1,2})\}?/g, (m, digits) => mapAllChars(digits, SUB_MAP) ?? m);
}

/* 只处理标签外的文本，避免动到 class/属性里的下划线 */
function prettifyOutsideTags(raw) {
  return raw.split(/(<[^>]*>)/).map((seg, i) => (i % 2 ? seg : prettyMath(seg))).join('');
}

export function questionContent(value) {
  const text = prettifyOutsideTags(String(value ?? ''));
  const prepared = text.replace(/</g, (match, offset) => NOTE_TAG.test(text.slice(offset)) ? '<' : '&lt;');
  const template = document.createElement('template');
  template.innerHTML = prepared;
  template.content.querySelectorAll('*').forEach((node) => {
    for (const attr of [...node.attributes]) {
      const allowed = ['class', 'style', 'alt', 'title', 'width', 'height', 'loading'].includes(attr.name)
        || (node.tagName === 'IMG' && attr.name === 'src' && /^\/assets\//.test(attr.value));
      if (!allowed || (attr.name === 'style' && /url\s*\(|expression|@import/i.test(attr.value))) node.removeAttribute(attr.name);
    }
  });
  const node = document.createElement('div');
  node.className = 'question-content';
  node.style.whiteSpace = 'pre-line';
  node.style.display = 'inline';
  node.appendChild(template.content);
  return node;
}

export function questionText(value) {
  const node = questionContent(String(value ?? '').replace(/<br\s*\/?\s*>|<\/(div|p|li)>/gi, '\n'));
  return node.textContent.trim();
}
