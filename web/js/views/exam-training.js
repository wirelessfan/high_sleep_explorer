import * as api from '../api.js';
import { el, toast, SUBJECT_LABEL, SUBJECT_CLASS } from '../ui.js';
import { navigate } from '../router.js';
import { mountReflection } from '../reflection.js';
import { feedbackButton } from '../question-feedback.js';

function streakPanel(data) {
  const panel = el('section',{class:'panel'});
  const status = el('b',{text:`连续高匹配 ${data.streak}/3 · 今日掉落 ${data.drops_today}/3`});
  panel.appendChild(status);
  panel.appendChild(el('p',{class:'hint',text:'每题总结达到80分，基准+5积分；连续3道不同题首次总结≥90分，掉落10积分（50%）、20积分（35%）或1张学习卡包（15%）。Sunny备考奖励额外×2。'}));
  panel.appendChild(el('p',{class:'hint',text:'每日基础总结积分最多50分（备考内容实得最多100分），掉落最多3次，掉落另计。低匹配会断连；修改旧总结可补领该题一次积分，但不重复攒连击。连击按北京时间每天重置。体验/历史账号可练习，不领取奖励。'}));
  panel.appendChild(el('p',{class:'hint',text:'专项选择题用于诊断，不单独发分；完成考点总结后按上述规则发奖。'}));
  const listener = e => { status.textContent=`连续高匹配 ${e.detail.streak}/3 · 今日掉落 ${e.detail.drops_today}/3`; };
  window.addEventListener('reflection:update',listener);
  return {panel,cleanup:()=>window.removeEventListener('reflection:update',listener)};
}

export async function renderExamTraining(view, { id } = {}) {
  const data = await api.getExamTraining();
  const root = el('div',{class:'stack'});
  root.appendChild(el('div',{class:'topbar'},[
    el('button',{class:'back',text:'‹',onclick:()=>navigate(id?'#/exam-training':'#/')}),
    el('div',{},[el('h1',{text:id?'考点雷达 · 专项自测':data.title}),el('div',{class:'sub',text:data.scope})]),
  ]));
  const streak = streakPanel(data);
  root.appendChild(streak.panel);
  root.appendChild(el('p',{class:'hint',text:data.evaluator_note}));
  if (!id) {
    root.appendChild(el('section',{class:'panel'},[
      el('h2',{text:'一眼看出考点，先问条件再套方法'}),
      el('p',{text:data.intro}),
      el('p',{class:'hint',text:'18类套路，每类1道辨识、1道迁移。建议每天选2–3类，先自测，再用自己的话归纳；不要把速解口诀当成无条件结论。'}),
    ]));
    for (const subject of ['physics','math','chemistry']) {
      root.appendChild(el('h3',{text:SUBJECT_LABEL[subject]}));
      for (const m of data.models.filter(m=>m.subject===subject)) root.appendChild(el('button',{
        class:'panel',style:'text-align:left;width:100%;cursor:pointer',onclick:()=>navigate(`#/exam-training/${m.id}`),
      },[
        el('div',{style:'font-weight:800',text:m.title}),el('p',{text:m.cues}),
        el('span',{class:`chip ${SUBJECT_CLASS[subject]}`,text:`已自测 ${m.attempted}/${m.questions} · 进入专项 →`}),
      ]));
    }
  } else {
    let model;
    try { model=await api.getExamModel(id); }
    catch(err) { streak.cleanup();throw err; }
    root.appendChild(el('section',{class:'panel'},[
      el('h2',{text:model.title}),el('p',{text:model.cues}),
      el('details',{},[
        el('summary',{text:'先学模型：条件、速解与反例'}),
        el('p',{text:`适用条件：${model.conditions}`}),el('p',{text:`速解路径：${model.route}`}),
        el('p',{text:`不要误套：${model.counterexample}`}),
      ]),
    ]));
    for (const q of model.questions) root.appendChild(questionCard(model,q));
  }
  view.replaceChildren(root);
  return streak.cleanup;
}

function questionCard(model,q) {
  const host=el('section',{class:'panel'});
  host.appendChild(el('h3',{text:`${q.level} · 目标 ${q.target_seconds} 秒`}));
  const content=el('div');
  let started=0,picked=null;
  const begin=el('button',{class:'btn ghost sm',text:'开始自测',onclick:()=>{
    begin.remove();started=performance.now();content.hidden=false;
  }});
  host.appendChild(begin);
  content.hidden=true;
  content.appendChild(el('p',{style:'font-size:14px;line-height:1.8',text:q.stem}));
  const opts=el('div',{class:'q-options'});
  q.options.forEach((option,index)=>opts.appendChild(el('button',{
    class:'opt',type:'button',text:`${'ABCD'[index]}. ${option}`,onclick:()=>{
      picked=index;Array.from(opts.children).forEach((n,i)=>n.classList.toggle('sel',i===index));submit.disabled=false;
    },
  })));
  content.appendChild(opts);
  const resultHost=el('div');
  const submit=el('button',{class:'btn sm',style:'margin-top:12px',text:'提交自测',disabled:true,onclick:async()=>{
    submit.disabled=true;
    try {
      const res=await api.answerExamQuestion(model.id,q.id,picked);
      const elapsed=Math.round((performance.now()-started)/1000);
      Array.from(opts.children).forEach((n,i)=>{n.disabled=true;n.classList.toggle('right',i===res.answer);n.classList.toggle('wrong',i===picked&&!res.correct);});
      resultHost.appendChild(el('p',{text:`${res.correct?'✓ 答对':'请回看条件'} · 用时约 ${elapsed} 秒（仅供自查，不影响奖励）`}));
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
