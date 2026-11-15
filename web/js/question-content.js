/* Mathematical '<' is text; only explicitly supported note markup is HTML. */
const NOTE_TAG = /^<\/?(?:div|span|p|br|strong|em|b|i|sup|sub|img|small|ul|ol|li)(?:\s+[^<>]*)?\s*\/?>/i;

export function questionContent(value) {
  const text = String(value ?? '');
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
