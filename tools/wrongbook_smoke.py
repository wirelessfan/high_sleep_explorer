"""Exercise wrongbook writes and AI stubs against an explicitly isolated server."""
import argparse
import json
import sys
from pathlib import Path
from urllib.request import Request, urlopen

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app import content_loader


def run(base):
    def call(path, payload=None, token=None):
        headers = {'Content-Type': 'application/json'}
        if token:
            headers['Authorization'] = 'Bearer ' + token
        request = Request(base + '/api/v1' + path, headers=headers,
                          data=json.dumps(payload).encode() if payload is not None else None)
        with urlopen(request, timeout=30) as response:
            return json.load(response)

    token = call('/session', {})['token']
    state = call('/wrongbook', token=token)
    assert state['ai']['stub'] and state['ai']['enabled'], 'Use an isolated STUB server only'
    section = next(s for s in content_loader.topic('physics-induction')['sections'] if s['id'] == 'quick')
    q = section['questions'][0]
    answers = {item['id']: item['answer'] for item in section['questions']}
    answers[q['id']] = (q['answer'] + 1) % len(q['options'])
    call('/topics/physics-induction/sections/quick/submit', {'answers': answers}, token)
    item = call('/wrongbook', token=token)['items'][0]
    for task in ['ai', 'ai/solve']:
        result = call('/wrongbook/' + task, {'ids': [item['id']]}, token)
        assert result['results'][0]['value']['stub']
        assert call('/wrongbook/' + task, {'ids': [item['id']]}, token)['results'][0]['cached']
    result = call('/wrongbook/ai/variants', {'id': item['id'], 'n': 2}, token)
    assert len(result['result']['variants']) == 2
    other = call('/session', {})['token']
    assert not call('/wrongbook', token=other)['items']
    assert 'error' in call('/wrongbook/ai', {'ids': [item['id']]}, other)['results'][0]
    before = call('/me', token=token)['points']
    result = call('/wrongbook/physics-induction/redo', {'answers': {item['id']: item['answer']}}, token)
    assert result['cleared'] == 1 and result['remaining'] == 0
    assert result['points'] == before + result['bonus']
    assert not call('/wrongbook', token=token)['items']
    print(json.dumps({'wrongbook': 'passed', 'AI': 'stub only; no external model validation',
                      'cached_tasks': 2, 'variants': 2, 'user_isolation': True, 'redo_bonus': result['bonus']}))


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('base')
    parser.add_argument('--isolated', action='store_true', required=True,
                        help='Required acknowledgement: this server uses a disposable test DB')
    args = parser.parse_args()
    run(args.base.rstrip('/'))
