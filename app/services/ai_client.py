"""AI 分析客户端：OpenAI 兼容协议（DeepSeek 官方或任意中转站均可）。

配置全部来自环境变量，密钥不入库、不进 git：
    LEARN_AI_BASE_URL   默认 https://api.deepseek.com/v1（官方）
                        中转站示例：https://your-relay.example.com/v1
    LEARN_AI_KEY        API Key（未配置时 AI 功能返回 503）
    LEARN_AI_MODEL      默认 deepseek-chat
    LEARN_AI_TIMEOUT    单次请求超时秒数，默认 45
    LEARN_AI_DAILY_LIMIT  每用户每天分析次数上限，默认 20

错误分析走服务端：Key 只存在于服务器环境，前端永远拿不到。
"""
from __future__ import annotations

import json
import os

import httpx

BASE_URL = os.environ.get("LEARN_AI_BASE_URL", "https://api.deepseek.com/v1")
API_KEY = os.environ.get("LEARN_AI_KEY", "")
MODEL = os.environ.get("LEARN_AI_MODEL", "deepseek-chat")
TIMEOUT = float(os.environ.get("LEARN_AI_TIMEOUT", "45"))
DAILY_LIMIT = int(os.environ.get("LEARN_AI_DAILY_LIMIT", "20"))

SYSTEM_PROMPT = (
    "你是一名严谨的高中理科教研老师。学生会给你一道他做错的选择题："
    "题干、选项、他的选择、正确答案、以及题目自带的解析。"
    "请分析他错在哪里，并给出改进建议。要求：\n"
    "1. 不要复述题目；直接指出他可能的思维误区（结合他所选的选项推断）。\n"
    "2. 分析不超过 120 字，直说要点。\n"
    "3. 给出 2-3 条具体可执行的改进建议，每条不超过 40 字。\n"
    "4. 语言严谨但亲切，面向高中生，不用 markdown 格式符号。\n"
    "5. 只输出 JSON，格式："
    '{"misconception": "一句话误区", "analysis": "错误分析", '
    '"suggestions": ["建议1", "建议2"]}'
)


def enabled() -> bool:
    return bool(API_KEY)


def config_public() -> dict:
    """给前端的状态信息（不含密钥）。"""
    return {
        "enabled": enabled(),
        "model": MODEL if enabled() else None,
        "daily_limit": DAILY_LIMIT,
    }


def _build_messages(q: dict, picked: int) -> list[dict]:
    letters = ["A", "B", "C", "D", "E", "F"]
    options = q.get("options", [])
    opt_lines = "\n".join(f"{letters[i]}. {o}" for i, o in enumerate(options))
    picked_letter = letters[picked] if isinstance(picked, int) and 0 <= picked < len(letters) else picked
    answer_letter = letters[q.get("answer", 0)]
    user_msg = (
        f"题目：{q.get('stem', '')}\n"
        f"选项：\n{opt_lines}\n"
        f"学生的选择：{picked_letter}\n"
        f"正确答案：{answer_letter}\n"
        f"题目解析：{q.get('explain', '')}\n"
        f"知识点标签：{q.get('skill', '')}\n\n"
        "请按系统要求输出 JSON。"
    )
    return [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": user_msg},
    ]


def _parse(content: str) -> dict:
    """尽量稳健地从回复里抠出 JSON。"""
    try:
        return json.loads(content)
    except json.JSONDecodeError:
        pass
    start = content.find("{")
    end = content.rfind("}")
    if start != -1 and end > start:
        try:
            return json.loads(content[start:end + 1])
        except json.JSONDecodeError:
            pass
    # 兜底：把整段回复当作分析文本
    return {"misconception": "", "analysis": content.strip()[:400], "suggestions": []}


def analyze(q: dict, picked: int) -> dict:
    """调用 AI 生成 {misconception, analysis, suggestions}。

    抛出 RuntimeError 表示调用失败（网络/HTTP 错误）。
    """
    if not enabled():
        raise RuntimeError("AI 服务未配置（缺少 LEARN_AI_KEY）")

    messages = _build_messages(q, picked)
    with httpx.Client(timeout=TIMEOUT) as client:
        resp = client.post(
            f"{BASE_URL.rstrip('/')}/chat/completions",
            headers={"Authorization": f"Bearer {API_KEY}",
                     "Content-Type": "application/json"},
            json={
                "model": MODEL,
                "messages": messages,
                "temperature": 0.4,
                "max_tokens": 800,
                "response_format": {"type": "json_object"},
            },
        )
    if resp.status_code == 401:
        raise RuntimeError("AI Key 无效")
    if resp.status_code == 402:
        raise RuntimeError("AI 账户余额不足")
    if resp.status_code == 429:
        raise RuntimeError("AI 请求过于频繁，请稍后再试")
    if resp.status_code >= 400:
        raise RuntimeError(f"AI 服务返回 {resp.status_code}")

    content = resp.json()["choices"][0]["message"]["content"]
    parsed = _parse(content)
    return {
        "misconception": str(parsed.get("misconception", ""))[:120],
        "analysis": str(parsed.get("analysis", ""))[:800],
        "suggestions": [str(x)[:120] for x in (parsed.get("suggestions") or [])][:4],
    }


def analyze_stub(q: dict, picked: int) -> dict:
    """无 Key 时的占位实现：用于本地演示与测试（不调用外部服务）。"""
    letters = ["A", "B", "C", "D", "E", "F"]
    picked_letter = letters[picked] if isinstance(picked, int) and 0 <= picked < 6 else "?"
    answer_letter = letters[q.get("answer", 0)]
    return {
        "misconception": "演示模式（未配置 LEARN_AI_KEY）",
        "analysis": (
            f"你选择了 {picked_letter}，正确答案是 {answer_letter}。"
            "配置 AI 服务后，这里会给出针对你错误选项的个性化分析。"
        ),
        "suggestions": [
            "回看该知识点的「知识点总结」版块",
            "在「难点剖析」里检查这道题对应的常见误区",
            "明天的错题重做里再试一次",
        ],
        "stub": True,
    }
