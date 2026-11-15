import * as api from '../api.js';
import { el, toast, previewImage, SUBJECT_LABEL, SUBJECT_CLASS } from '../ui.js';
import { navigate } from '../router.js';
import { mountReflection } from '../reflection.js';
import { feedbackButton } from '../question-feedback.js';

function streakPanel(data) {
  const panel = el('section',{class:'panel'});
  const statusText = d => `灵感连连 ${d.streak}/3 · 今天收到 ${d.drops_today} 份惊喜`;
  const status = el('b',{text:statusText(data)});
  panel.appendChild(status);
  panel.appendChild(el('p',{text:'轻松备考，抽着奖把题做了 🙂'}));
  panel.appendChild(el('p',{class:'hint',text:'看图、猜一猜，再说说你的发现。没有计时，想多久都可以；总结攒够三次高匹配，会有一份随机惊喜。'}));
  panel.appendChild(el('details',{},[
    el('summary',{text:'好奇奖励怎么算？点开看看'}),
    el('p',{class:'hint',text:'每题总结达到80分，基准+5积分；连续3道不同题首次总结≥90分，掉落10积分（50%）、20积分（35%）或1张学习卡包（15%）。Sunny活动范围内额外×2。'}),
    el('p',{class:'hint',text:'每日基础总结积分最多50分（双倍内容实得最多100分），随机惊喜另计、每天最多3份。首次总结不足90分时连击重新开始，可以慢慢补充；修改旧总结可补领该题一次积分，不重复攒连击。连击按北京时间每天重置。访客/历史账号可练习，不领取奖励。选择题不单独发分，总结按规则领奖。'}),
    el('p',{class:'hint',text:data.evaluator_note}),
  ]));
  const listener = e => { status.textContent=statusText(e.detail); };
  window.addEventListener('reflection:update',listener);
  return {panel,cleanup:()=>window.removeEventListener('reflection:update',listener)};
}

export async function renderExamTraining(view, { id } = {}) {
  const data = await api.getExamTraining();
  const root = el('div',{class:'stack'});
  root.appendChild(el('div',{class:'topbar'},[
    el('button',{class:'back',text:'‹',onclick:()=>navigate(id?'#/exam-training':'#/')}),
    el('div',{},[el('h1',{text:id?'看图找规律 · 发现小站':data.title}),el('div',{class:'sub',text:data.scope})]),
  ]));
  const streak = streakPanel(data);
  root.appendChild(streak.panel);
  if (!id) {
    root.appendChild(el('section',{class:'panel'},[
      el('h2',{text:'一个小发现，点亮一道题'}),
      el('p',{text:data.intro}),
      el('p',{class:'hint',text:'18个发现小站，每站两道小问题。挑喜欢的逛，随时可以停；记得留意“这个规律什么时候成立”。'}),
    ]));
    for (const subject of ['physics','math','chemistry']) {
      root.appendChild(el('h3',{text:SUBJECT_LABEL[subject]}));
      for (const m of data.models.filter(m=>m.subject===subject)) root.appendChild(el('button',{
        class:'panel',style:'text-align:left;width:100%;cursor:pointer',onclick:()=>navigate(`#/exam-training/${m.id}`),
      },[
        el('div',{style:'font-weight:800',text:m.title}),el('p',{text:m.cues}),
        el('span',{class:`chip ${SUBJECT_CLASS[subject]}`,text:`已有 ${m.attempted} 个发现 · 进去看看 →`}),
      ]));
    }
  } else {
    let model;
    try { model=await api.getExamModel(id); }
    catch(err) { streak.cleanup();throw err; }
    root.appendChild(el('section',{class:'panel'},[
      el('h2',{text:model.title}),el('p',{text:model.cues}),
      el('details',{},[
        el('summary',{text:'翻开一张灵感小纸条'}),
        el('p',{text:`什么时候成立：${model.conditions}`}),el('p',{text:`可以这样想：${model.route}`}),
        el('p',{text:`换个条件会怎样：${model.counterexample}`}),
      ]),
    ]));
    for (const q of model.questions) root.appendChild(questionCard(model,q));
  }
  view.replaceChildren(root);
  return streak.cleanup;
}

function questionCard(model,q) {
  const host=el('section',{class:'panel'});
  host.appendChild(el('h3',{text:q.level==='辨识'?'发现一条规律':'换个角度玩一玩'}));
  const content=el('div');
  let picked=null;
  content.appendChild(el('p',{style:'font-size:14px;line-height:1.8',text:q.stem}));
  if (q.diagram) content.appendChild(el('figure',{style:'margin:12px 0'},[
    el('button',{type:'button','aria-label':`放大图解：${q.diagram.title}`,
      style:'display:block;width:100%;padding:0;border:0;background:transparent;cursor:zoom-in',
      onclick:()=>previewImage(q.diagram.src,q.diagram.title)},[
      el('img',{src:q.diagram.src,alt:q.diagram.alt,width:640,height:360,loading:'lazy',
        style:'display:block;width:100%;height:auto;border-radius:14px;background:#f5faf7'}),
    ]),
    el('figcaption',{class:'hint',style:'margin-top:6px',text:q.diagram.caption}),
  ]));
  const opts=el('div',{class:'q-options'});
  q.options.forEach((option,index)=>opts.appendChild(el('button',{
    class:'opt',type:'button',text:`${'ABCD'[index]}. ${option}`,onclick:()=>{
      picked=index;Array.from(opts.children).forEach((n,i)=>n.classList.toggle('sel',i===index));submit.disabled=false;
    },
  })));
  content.appendChild(opts);
  const resultHost=el('div');
  const submit=el('button',{class:'btn sm',style:'margin-top:12px',text:'看看我的想法',disabled:true,onclick:async()=>{
    submit.disabled=true;
    try {
      const res=await api.answerExamQuestion(model.id,q.id,picked);
      Array.from(opts.children).forEach((n,i)=>{n.disabled=true;n.classList.toggle('right',i===res.answer);n.classList.toggle('wrong',i===picked&&!res.correct);});
      resultHost.appendChild(el('p',{text:res.correct?'✨ 这个规律被你发现啦！':'🌱 换个角度看看，新的发现就在这里。'}));
      resultHost.appendChild(el('p',{text:res.explain}));
      mountReflection(host,res.reflection);
      submit.remove();
    } catch(err) { toast(err.message||'提交失败');submit.disabled=false; }
  }});
  content.appendChild(submit);
  content.appendChild(resultHost);
  content.appendChild(feedbackButton({topic_id:model.topic_id,section_id:`drill-${model.id}`,tier:'basic',question_id:q.id},q));
  host.appendChild(content);
  mountReflection(host,q.reflection);
  return host;
}
