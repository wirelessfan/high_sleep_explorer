"""Build a temporary browser regression page for every actual bank question.
Run the app locally, then open /_question-render-review.html; delete that page after review.
"""
import json
import sys
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from app import content_loader
from app.services.wrongbook import questions_of


def main():
    items=[]
    for topic in content_loader.catalog()['topics']:
        for section in content_loader.topic(topic['id'])['sections']:
            for tier,content in content_loader.section_tiers(section).items():
                for qid,q in questions_of(content).items():
                    items.append({'location':f"{topic['id']}/{section['id']}/{tier}/{qid}",'stem':q['stem']})
    payload=json.dumps(items,ensure_ascii=False).replace('<',r'\u003c')
    page=r"""<!doctype html><html lang="zh"><meta charset="utf-8"><title>题干显示回归验收</title>
<h1>题干显示回归验收</h1><pre id="result">检查中</pre><div id="proof"></div>
<script id="questions" type="application/json">PAYLOAD</script>
<script type="module">
import {questionContent,questionText} from '/js/question-content.js';
const rows=JSON.parse(document.getElementById('questions').textContent);
let math=0,rich=0;const errors=[];
for(const item of rows){
 const node=questionContent(item.stem);
 const hasNotes=/<(?:div|span|img)\b/i.test(item.stem);
 if(!hasNotes && node.textContent!==item.stem) errors.push(item.location+': text changed');
 if(!hasNotes && questionText(item.stem)!==item.stem.trim()) errors.push(item.location+': plain text changed');
 if(hasNotes){rich++;const expected=(item.stem.match(/<img\b/g)||[]).length;if(node.querySelectorAll('img').length!==expected)errors.push(item.location+': image missing');}
 if(/<(?!\s)/.test(item.stem)&&!hasNotes)math++;
 if(item.location==='chemistry-ionic/quick/advanced/aq1')document.getElementById('proof').append(node);
}
for(const stem of ['0<k<1，求上限，按Q≤Ksp不沉淀。','0<b<1且x>0','0<i<1，a>b','x<y，y<z，求x']){
 if(questionContent(stem).textContent!==stem)errors.push('boundary: '+stem);
}
const unsafe=questionContent('<img src="/assets/notes/intro-math-log.svg" onerror="alert(1)"><img src="https://example.com/private"><scr'+'ipt>alert(1)</scr'+'ipt>');
if(unsafe.querySelector('script,[onerror],img[src^="https:"]'))errors.push('unsafe markup retained');
document.getElementById('result').textContent=JSON.stringify({passed:errors.length===0,questions:rows.length,rich_notes:rich,math_conditions:math,errors},null,2);
</script></html>""".replace('PAYLOAD',payload)
    path=ROOT/'web/_question-render-review.html'
    path.write_text(page,encoding='utf-8')
    print(f'Prepared {len(items)} questions: {path}')


if __name__=='__main__':main()
