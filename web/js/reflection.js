import * as api from './api.js';
import { el, toast } from './ui.js';

export function mountReflection(host, context) {
  if (!context?.fingerprint || host.querySelector('[data-reflection]')) return;
  const saved = context.saved;
  const wrap = el('details', { 'data-reflection': context.fingerprint, open: !saved,
    style: 'margin-top:14px;padding:12px;border:1px solid #c6e4d8;border-radius:12px;background:#f5fbf7' });
  wrap.appendChild(el('summary', { style: 'font-weight:700;font-size:13px', text: '收好这个小发现 · 总结还能收惊喜' }));
  wrap.appendChild(el('p', { class: 'hint', text: '像讲给朋友听一样，说说你看到了什么、为什么成立、换个条件又会怎样。不用写标准作文，也不要求逐字一样。' }));
  const inputs = {};
  for (const [key,label,hint,max] of [
    ['concept','我发现了什么规律？','例如：绳子两边像在悄悄传递同一个拉力。',200],
    ['conditions','它在什么条件下成立？','哪些条件支持这个想法？换个条件还成立吗？',250],
    ['method','我会怎样讲给朋友听？','结合这道题讲讲你的方法，再提醒一个容易忽略的小细节。',450],
  ]) {
    const input = el('textarea', { rows: key==='method' ? 3 : 2, maxlength:max, 'aria-label':label,
      placeholder:hint, style:'width:100%;box-sizing:border-box;padding:9px;font:inherit;font-size:13px;border:1px solid #d5dfd6;border-radius:8px;margin-top:5px' });
    input.value = saved?.parts?.[key] || '';
    inputs[key] = input;
    wrap.appendChild(el('label', { style:'display:block;font-size:12px;margin-top:10px' }, [el('span',{text:label}),input]));
  }
  const output = el('div', { 'aria-live':'polite', style:'font-size:12px;line-height:1.7;margin-top:10px' });
  if (saved) output.appendChild(el('div',{text:`上次匹配 ${saved.score} 分 · 最佳 ${saved.best_score} 分${saved.rewarded ? ' · 本题积分已领' : ''}`}));
  let pending = null;
  const button = el('button',{class:'btn sm',style:'margin-top:10px',text:saved?'补充我的发现':'收好发现，看看奖励',onclick:async()=>{
    const parts = Object.fromEntries(Object.entries(inputs).map(([k,v])=>[k,v.value.trim()]));
    if (Object.values(parts).some(v=>v.length<4)) { toast('请分别写出考点、条件和方法，每部分至少4字'); return; }
    const signature = JSON.stringify(parts);
    if (!pending || pending.signature!==signature) pending={signature,requestId:crypto.randomUUID()};
    button.disabled=true;
    button.textContent='正在对照考点…';
    try {
      const result = await api.postReflection({fingerprint:context.fingerprint,request_id:pending.requestId,parts});
      pending=null;
      output.replaceChildren();
      output.appendChild(el('b',{text:`要点匹配 ${result.score} 分${result.points ? ` · +${result.points} 积分` : ''} · 灵感连连 ${result.streak}/3`}));
      for (const check of result.checks) output.appendChild(el('div',{text:`${check.matched?'✓':'待补充'} ${check.label}`}));
      if (result.contradictions.length) output.appendChild(el('div',{style:'color:#b91c1c',text:`请核对矛盾表述：${result.contradictions.join('；')}`}));
      output.appendChild(el('div',{text:result.advice}));
      output.appendChild(el('div',{text:result.reward_reason}));
      if (result.drop) {
        const prize = `${result.drop.amount}${result.drop.kind==='points'?'积分':'张学习卡包'}`;
        output.appendChild(el('div',{style:'font-weight:800;color:#9a5a00;padding:9px 0',text:`🎁 三个小发现连起来，收获 ${prize}！`}));
        toast(`连击奖励：${prize}`);
      }
      output.appendChild(el('div',{class:'hint',text:`今日掉落 ${result.drops_today}/${result.daily_drop_cap} · 总积分 ${result.total_points} · ${result.note}`}));
      output.appendChild(el('details',{},[el('summary',{text:'对照预设要点'}),el('p',{text:result.reference})]));
      window.dispatchEvent(new CustomEvent('reflection:update',{detail:result}));
      if (result.points || result.drop) {
        api.fetchMe().then(me=>window.dispatchEvent(new CustomEvent('me:update',{detail:me}))).catch(()=>{});
      }
    } catch (err) { toast(err.message || '检查失败，请重试'); }
    finally { button.disabled=false;button.textContent='补充我的发现'; }
  }});
  wrap.appendChild(button);
  wrap.appendChild(output);
  wrap.appendChild(el('p',{class:'hint',text:'当前使用预设规则/本题解析对照，未调用在线 AI。达标≥80分，高匹配≥90分；同题仅奖励一次，修改不重复攒连击。每日基础总结积分上限50分、掉落上限3次；Sunny备考内容按×2结算。'}));
  host.appendChild(wrap);
}
