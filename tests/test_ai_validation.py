"""Untrusted model output and provider failures must not become cached answers."""
import json

import httpx
import pytest

from app.services import ai_client
from deploy.configure_caddy import render


Q = {"stem": "A particle travels 10m in 2s. Average speed?", "options": ["5", "20", "12", "8"],
     "answer": 0, "skill": "average speed", "explain": "10/2=5"}


def mock_reply(monkeypatch, value):
    monkeypatch.delenv("LEARN_AI_STUB", raising=False)
    monkeypatch.setattr(ai_client, "enabled", lambda: True)
    monkeypatch.setattr(ai_client, "chat", lambda *a, **k: {
        "text": json.dumps(value), "channel": "test", "model": "test"})


@pytest.mark.parametrize("value", [[], "text", None, {}, {"answer": "Z", "steps": ["step"]},
                                  {"answer": "F", "steps": ["step"]},
                                  {"answer": "A", "steps": "not a list"},
                                  {"answer": "AB", "steps": ["step"]}])
def test_solve_rejects_malformed_or_out_of_range(monkeypatch, value):
    mock_reply(monkeypatch, value)
    with pytest.raises(RuntimeError):
        ai_client.solve(Q)


@pytest.mark.parametrize("answer", [-1, 4, True, "0", None])
def test_variants_never_default_bad_answer_to_a(monkeypatch, answer):
    mock_reply(monkeypatch, {"variants": [{"stem": "different question", "options": Q["options"],
                                          "answer": answer, "explain": "reason"}]})
    with pytest.raises(RuntimeError):
        ai_client.variants(Q, 1)


def test_analysis_rejects_string_suggestions(monkeypatch):
    mock_reply(monkeypatch, {"analysis": "reason", "suggestions": "not a list"})
    with pytest.raises(RuntimeError):
        ai_client.analyze(Q, 1)


@pytest.mark.parametrize("failure", ["timeout", "network", "empty", "json", "shape"])
def test_provider_failure_is_safe_runtime_error(monkeypatch, failure):
    class FakeClient:
        def __init__(self, **kwargs): pass
        def __enter__(self): return self
        def __exit__(self, *args): pass
        def post(self, *args, **kwargs):
            if failure == "timeout":
                raise httpx.ReadTimeout("secret-key-in-url")
            if failure == "network":
                raise httpx.ConnectError("secret-key-in-url")
            if failure == "json":
                return httpx.Response(200, text="not json")
            if failure == "shape":
                return httpx.Response(200, json={"choices": []})
            return httpx.Response(200, json={"choices": [{"message": {"content": ""}}]})
    monkeypatch.setattr(httpx, "Client", FakeClient)
    with pytest.raises(RuntimeError) as exc:
        ai_client._post({"base_url": "https://test.invalid", "key": "secret", "name": "test"},
                        "test", [], True, 10)
    assert "secret" not in str(exc.value)


def test_provider_network_failure_falls_back(monkeypatch):
    monkeypatch.delenv("LEARN_AI_STUB", raising=False)
    monkeypatch.setattr(ai_client, "CHANNELS", {cid: {**ch, "key": "test"}
                                              for cid, ch in ai_client.CHANNELS.items()})
    from app.services import ai_config
    cfg = {"routing": ai_config.DEFAULT_ROUTING, "channels": {}, "limits": ai_config.DEFAULT_LIMITS}
    monkeypatch.setattr(ai_client, "_load_cfg", lambda conn: cfg)
    calls = []
    def post(ch, *args):
        calls.append(ch["id"])
        if ch["id"] == "glm":
            raise RuntimeError("network unavailable")
        return '{"analysis":"ok"}'
    monkeypatch.setattr(ai_client, "_post", post)
    assert ai_client.chat("analyze", "system", "question")["channel"] == "deepseek"
    assert calls == ["glm", "deepseek"]


def test_caddy_ports_and_idempotency_preserve_other_sites():
    other = ':80 {\n    root * /blog\n    file_server\n}\n\n:8091 {\n    reverse_proxy 127.0.0.1:8001\n}\n'
    original = other + '\n# 高中理科学习助手\n\n# 高中理科学习助手\none.sslip.io, two.sslip.io:8090 {\n log {\n output file /tmp/log\n }\n reverse_proxy 127.0.0.1:8000\n}\n'
    first = render(original, 'one.sslip.io, two.sslip.io')
    assert other.strip() in first
    assert 'one.sslip.io:8090' in first and 'two.sslip.io:8090' in first
    assert first.count('reverse_proxy 127.0.0.1:8000') == 1
    assert first.count('# 高中理科学习助手') == 1
    assert render(first, 'one.sslip.io, two.sslip.io') == first
