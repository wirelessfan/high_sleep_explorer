"""对已启动服务检查全部公开题面、答案剥离和版本；--submit仅用于独立预发布库。"""
import argparse
import json
from pathlib import Path
import sys
from urllib.request import Request,urlopen

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from tools.check_content import questions_of,section_tiers


def run(base,submit=False):
    def call(path,payload=None,token=None):
        headers={'Content-Type':'application/json'}
        if token:headers['Authorization']='Bearer '+token
        req=Request(base+path,data=json.dumps(payload).encode() if payload is not None else None,headers=headers)
        with urlopen(req,timeout=30) as r:return json.load(r)
    assert call('/api/v1/healthz')['ok']
    token=call('/api/v1/session',{})['token']
    count=units=reads=0
    for path in (ROOT/'content/topics').glob('*.json'):
        data=json.loads(path.read_text('utf8'))
        for sec in data['sections']:
            for tier,content in section_tiers(sec).items():
                url=f"/api/v1/topics/{data['id']}/sections/{sec['id']}"
                query='?tier='+tier
                public=call(url+query,token=token)
                assert public['available'],(url,tier)
                serialized=json.dumps(public)
                assert '"answer"' not in serialized and '"explain"' not in serialized
                visible=public['section'];local=questions_of(content);remote=questions_of(visible)
                assert len(local)==len(remote),(url,tier)
                for (qid,q),(rqid,rq) in zip(local,remote):
                    assert qid==rqid and q['options']==rq['options'] and q.get('stem',q.get('ask'))==rq.get('stem',rq.get('ask'))
                    assert q.get('revision')==rq.get('revision')
                if content['type']=='reading':
                    assert content['blocks']==visible['blocks']
                    if submit:assert call(url+'/read'+query,{'confirmed':True},token)['ok']
                    reads+=1;continue
                if submit:
                    answers={qid:q['answer'] for qid,q in local}
                    result=call(url+'/submit'+query,{'answers':answers},token)
                    assert result['score']==100 and result['total']==len(local) and result['passed'],(url,tier,result)
                units+=1;count+=len(local)
    assert (count,units,reads)==(907,190,38)
    print(json.dumps({'base':base,'questions':count,'graded_units':units if submit else 0,'public_units':units,'reading_units':reads,'passed':True}))


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('base');parser.add_argument('--submit',action='store_true')
    args=parser.parse_args();run(args.base.rstrip('/'),args.submit)
