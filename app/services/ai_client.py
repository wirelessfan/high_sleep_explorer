"""多路 AI 客户端：OpenAI 兼容协议，按任务路由到不同通道取性价比。

通道（价格/能力升序，回退链同序）：glm < deepseek < gpt。
通道的 base_url / key / 默认模型来自环境变量（密钥不入库、不回显）：

    LEARN_AI_GLM_BASE_URL / LEARN_AI_GLM_KEY / LEARN_AI_GLM_MODEL
    LEARN_AI_DEEPSEEK_*   （兼容旧部署：未设置时回落到 LEARN_AI_BASE_URL/_KEY/_MODEL）
    LEARN_AI_GPT_*
    LEARN_AI_TIMEOUT      单次请求超时秒数，默认 45
    LEARN_AI_STUB=1       演示模式：不调用外部服务，所有任务走本地占位实现

任务→通道的路由与每任务限额存 ai_config 表（管理员运行时可调，见 ai_config.py）。
Key 只在服务端环境，前端永远拿不到；config_public() 只回传非敏感信息。
"""
from __future__ import annotations

import json
import os

import httpx

from app.services import ai_config

TIMEOUT = float(os.environ.get("LEARN_AI_TIMEOUT", "45"))

LETTERS = ["A", "B", "C", "D", "E", "F"]


def _channel(cid: str, name: str, default_base: str, default_model: str,
             legacy: bool = False) -> dict:
    """从环境变量组装一个通道定义（模块导入时定格，测试可 monkeypatch CHANNELS）。"""
    p = f"LEARN_AI_{cid.upper()}_"
    base_url = os.environ.get(p + "BASE_URL", default_base)
    key = os.environ.get(p + "KEY", "")
    model = os.environ.get(p + "MODEL", default_model)
    if legacy:  # 老部署只配了 LEARN_AI_BASE_URL/_KEY/_MODEL，视作 deepseek 通道
        base_url = os.environ.get(p + "BASE_URL",
                                  os.environ.get("LEARN_AI_BASE_URL", default_base))
        key = os.environ.get(p + "KEY", os.environ.get("LEARN_AI_KEY", ""))
        model = os.environ.get(p + "MODEL", os.environ.get("LEARN_AI_MODEL", default_model))
    return {
        "id": cid,
        "name": name,
        "base_url": base_url,
        "key": key,
        "model": model,
        # 视觉通道标记：默认只有 gpt；中转站若把视觉能力放在别的通道，
        # 用 LEARN_AI_<CID>_VISION=1 显式声明（例如 GLM 也支持读图时）。
        "vision": os.environ.get(p + "VISION") == "1" or
                  (os.environ.get(p + "VISION") is None and cid == "gpt"),
    }


CHANNELS: dict[str, dict] = {
    c["id"]: c for c in (
        _channel("glm", "GLM", "https://open.bigmodel.cn/api/paas/v4", "glm-4.7-flash"),
        _channel("deepseek", "DeepSeek", "https://api.deepseek.com/v1",
                 "deepseek-v4-flash", legacy=True),
        _channel("gpt", "GPT", "https://api.openai.com/v1", "gpt-4o-mini"),
    )
}


def enabled() -> bool:
    """任一通道配了 Key（真实服务）或显式开启演示模式（LEARN_AI_STUB=1）时可用。"""
    return any(c["key"] for c in CHANNELS.values()) or os.environ.get("LEARN_AI_STUB") == "1"


def _stub_on() -> bool:
    return os.environ.get("LEARN_AI_STUB") == "1"


def _load_cfg(conn=None) -> dict:
    if conn is not None:
        return ai_config.load(conn)
    from app import db
    with db.ro() as c:
        return ai_config.load(c)


def candidates(task: str, cfg: dict, vision_only: bool = False) -> list[tuple[dict, str]]:
    """(通道, 模型) 候选序列：主路由优先，其余按能力升序兜底（跳过禁用通道）。"""
    primary = cfg["routing"].get(task)
    order = [primary] + [c for c in ai_config.CHANNEL_ORDER if c != primary]
    out = []
    for cid in order:
        ch = CHANNELS.get(cid)
        if not ch:
            continue
        if vision_only and not ch.get("vision"):
            continue
        over = cfg["channels"].get(cid, {})
        if not over.get("enabled", True):
            continue
        if not ch.get("key") and not _stub_on():
            continue
        out.append((ch, over.get("model") or ch["model"]))
    return out


# ---------------------------------------------------------------- 调用层

def _post(ch: dict, model: str, messages: list[dict], json_mode: bool,
          max_tokens: int) -> str:
    """单次真实调用，失败抛 RuntimeError（错误信息面向学生展示）。"""
    body: dict = {
        "model": model,
        "messages": messages,
        "temperature": 0.4,
        "max_tokens": max_tokens,
    }
    if json_mode:
        body["response_format"] = {"type": "json_object"}
    try:
        with httpx.Client(timeout=TIMEOUT) as client:
            resp = client.post(
                f"{ch['base_url'].rstrip('/')}/chat/completions",
                headers={"Authorization": f"Bearer {ch['key']}",
                         "Content-Type": "application/json"},
                json=body,
            )
    except httpx.TimeoutException:
        raise RuntimeError("AI 响应超时，请稍后重试") from None
    except httpx.RequestError:
        raise RuntimeError("AI 网络连接失败，请稍后重试") from None
    if resp.status_code == 401:
        raise RuntimeError(f"{ch['name']} Key 无效")
    if resp.status_code == 402:
        raise RuntimeError(f"{ch['name']} 账户余额不足")
    if resp.status_code == 429:
        raise RuntimeError("AI 请求过于频繁，请稍后再试")
    if resp.status_code >= 400:
        raise RuntimeError(f"AI 服务返回 {resp.status_code}")
    try:
        content = resp.json()["choices"][0]["message"]["content"]
        if not isinstance(content, str) or not content.strip():
            raise ValueError("empty content")
        if json_mode:
            _parse(content)
        return content
    except (ValueError, TypeError, KeyError, IndexError):
        raise RuntimeError("AI 返回格式不完整，请稍后重试") from None


def chat(task: str, system: str, user_msg: str, *, conn=None, json_mode: bool = True,
         max_tokens: int = 800, vision_only: bool = False,
         images: list[str] | None = None) -> dict:
    """按任务路由调用 AI，主通道失败自动按能力序回退。

    返回 {text, channel, model}；全部候选失败抛最后一次的 RuntimeError。
    images：base64 图片（不带 data: 前缀），仅视觉通道接受，拍照识别用。
    """
    if not enabled():
        raise RuntimeError("AI 服务未配置")
    if _stub_on():
        raise RuntimeError("STUB 模式不走真实调用")

    messages: list[dict] = [{"role": "system", "content": system}]
    if images:
        content = [{"type": "image_url",
                    "image_url": {"url": "data:image/jpeg;base64," + b64}}
                   for b64 in images]
        content.append({"type": "text", "text": user_msg})
        messages.append({"role": "user", "content": content})
    else:
        messages.append({"role": "user", "content": user_msg})

    cfg = _load_cfg(conn)
    last_err: RuntimeError | None = None
    for ch, model in candidates(task, cfg, vision_only=vision_only):
        # 中转站的 5xx 多为瞬时抖动：同一通道重试一次，再走回退链。
        for attempt in range(2):
            try:
                text = _post(ch, model, messages, json_mode, max_tokens)
                return {"text": text, "channel": ch["id"], "model": model}
            except RuntimeError as exc:
                last_err = exc
                transient = "返回 5" in str(exc) or "过于频繁" in str(exc)
                if not transient or attempt == 1:
                    break
    raise last_err or RuntimeError("没有可用的 AI 通道")


def _parse(content: str) -> dict:
    """尽量稳健地从回复里抠出 JSON。"""
    result = None
    try:
        result = json.loads(content)
    except json.JSONDecodeError:
        start = content.find("{")
        end = content.rfind("}")
        if start != -1 and end > start:
            try:
                result = json.loads(content[start:end + 1])
            except json.JSONDecodeError:
                result = None
    if not isinstance(result, dict) or not result:
        raise RuntimeError("AI 返回的 JSON 格式无效，请重试")
    return _normalize_keys(result)


# 中转/国产模型偶尔会把 JSON 键名翻译成中文，这里做一层兜底映射。
_KEY_ALIASES = {
    "变式题": "variants", "变式": "variants", "题目": "variants",
    "题干": "stem", "题目内容": "stem",
    "选项": "options",
    "答案": "answer", "正确答案": "answer",
    "解析": "explain", "解答": "explain",
    "答案字母": "answer", "选项字母": "answer",
    "误区": "misconception", "错误分析": "analysis", "分析": "analysis",
    "建议": "suggestions",
    "解题步骤": "steps", "步骤": "steps", "核心考点": "key_point", "考点": "key_point",
    "科目": "subject", "学科": "subject",
}


def _normalize_keys(data):
    """递归把已知的中文键名映射成英文；未知键保持原样。"""
    if isinstance(data, list):
        return [_normalize_keys(v) for v in data]
    if not isinstance(data, dict):
        return data
    out = {}
    for k, v in data.items():
        key = _KEY_ALIASES.get(k.strip(), k)
        out[key] = _normalize_keys(v)
    return out


def _strings(value, name: str, maximum: int = 8) -> list[str]:
    if not isinstance(value, list) or not value or len(value) > maximum:
        raise RuntimeError(f"AI 返回的{name}不完整，请重试")
    if any(not isinstance(x, str) or not x.strip() for x in value):
        raise RuntimeError(f"AI 返回的{name}格式无效，请重试")
    return [x.strip() for x in value]


def _meta(channel: str, model: str) -> dict:
    return {"channel": channel, "model": model}


# ---------------------------------------------------------------- 错因分析

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


def _build_messages(q: dict, picked: int) -> str:
    options = q.get("options", [])
    opt_lines = "\n".join(f"{LETTERS[i]}. {o}" for i, o in enumerate(options))
    picked_letter = (LETTERS[picked] if isinstance(picked, int)
                     and 0 <= picked < len(LETTERS) else picked)
    answer_letter = LETTERS[q.get("answer", 0)]
    return (
        f"题目：{q.get('stem', '')}\n"
        f"选项：\n{opt_lines}\n"
        f"学生的选择：{picked_letter}\n"
        f"正确答案：{answer_letter}\n"
        f"题目解析：{q.get('explain', '')}\n"
        f"知识点标签：{q.get('skill', '')}\n\n"
        "请按系统要求输出 JSON。"
    )


def analyze(q: dict, picked: int, conn=None) -> dict:
    """错因分析：{misconception, analysis, suggestions}（结果含实际生效的通道/模型）。

    抛出 RuntimeError 表示调用失败（网络/HTTP 错误）。
    """
    if not enabled():
        raise RuntimeError("AI 服务未配置")
    if _stub_on():
        return analyze_stub(q, picked)

    r = chat("analyze", SYSTEM_PROMPT, _build_messages(q, picked), conn=conn)
    parsed = _parse(r["text"])
    if not isinstance(parsed.get("analysis"), str) or not parsed["analysis"].strip():
        raise RuntimeError("AI 未返回有效的错误分析，请重试")
    suggestions = _strings(parsed.get("suggestions"), "改进建议", 4)
    return {
        "misconception": str(parsed.get("misconception", ""))[:120],
        "analysis": str(parsed.get("analysis", ""))[:800],
        "suggestions": [x[:120] for x in suggestions],
        **_meta(r["channel"], r["model"]),
    }


def analyze_stub(q: dict, picked: int, conn=None) -> dict:
    """无 Key 时的占位实现：用于本地演示与测试（不调用外部服务）。"""
    picked_letter = (LETTERS[picked] if isinstance(picked, int) and 0 <= picked < 6 else "?")
    answer_letter = LETTERS[q.get("answer", 0)]
    return {
        "misconception": "演示模式（未配置 AI Key）",
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
        **_meta("stub", "stub"),
    }


# ---------------------------------------------------------------- AI 解题

SOLVE_PROMPT = (
    "你是一名严谨的高中理科老师。请独立解答学生给出的这道选择题"
    "（不会告诉你标准答案，请凭自己的解题过程得出结论）。要求：\n"
    "1. 解题步骤分步给出，每步不超过 80 字，直击关键推导。\n"
    "2. key_point 一句话点出这道题考查的核心，不超过 60 字。\n"
    "3. 语言面向高中生，不用 markdown 格式符号。\n"
    "4. 只输出 JSON，格式："
    '{"answer": "A", "steps": ["步骤1", "步骤2"], "key_point": "核心考点"}'
    "，answer 是选项字母。"
)


def solve(q: dict, conn=None) -> dict:
    """AI 独立解题：{answer(选项序号), answer_letter, steps, key_point}。

    不把标准答案喂给模型，产出「AI 判定」的答案基准（拍照题无标准答案时用它）。
    """
    if not enabled():
        raise RuntimeError("AI 服务未配置")
    if _stub_on():
        return solve_stub(q)

    options = q.get("options", [])
    opt_lines = "\n".join(f"{LETTERS[i]}. {o}" for i, o in enumerate(options))
    user_msg = (
        f"题目：{q.get('stem', '')}\n"
        f"选项：\n{opt_lines}\n"
        f"知识点标签：{q.get('skill', '')}\n\n"
        "请独立解题并按系统要求输出 JSON。"
    )
    r = chat("solve", SOLVE_PROMPT, user_msg, conn=conn, max_tokens=1000)
    parsed = _parse(r["text"])

    letter = str(parsed.get("answer", "")).strip().upper()
    answer = LETTERS.index(letter) if letter in LETTERS else -1
    if not 0 <= answer < len(options):
        raise RuntimeError("AI 答案不在题目选项范围内，请重试")
    steps = [x[:160] for x in _strings(parsed.get("steps"), "解题步骤")]
    return {
        "answer": answer,
        "answer_letter": letter if answer >= 0 else "?",
        "steps": steps,
        "key_point": str(parsed.get("key_point", "")).strip()[:120],
        **_meta(r["channel"], r["model"]),
    }


def solve_stub(q: dict, conn=None) -> dict:
    answer = q.get("answer", 0)
    letter = LETTERS[answer] if isinstance(answer, int) and 0 <= answer < 6 else "?"
    return {
        "answer": answer,
        "answer_letter": letter,
        "steps": [
            "演示模式：这里会展示第一步的分析（审题、提取已知量）。",
            "演示模式：第二步会展示核心推导过程。",
            "演示模式：最后一步落回选项比较，得出答案。",
        ],
        "key_point": "演示模式（未配置 AI Key），配置后展示真实解题步骤。",
        "stub": True,
        **_meta("stub", "stub"),
    }


# ---------------------------------------------------------------- 举一反三

VARIANTS_PROMPT = (
    "你是一名严谨的高中理科命题老师。学生会给你一道他做错的选择题，"
    "请围绕同一知识点与同一考法原创变式题（举一反三）。要求：\n"
    "1. 完全原创：必须更换情境、对象与数据，不得照抄原题文字或原题数字。\n"
    "2. 最关键：每道变式题的题干必须与原题题干完全不同（不得原样复用、"
    "不得只改标点或语序），否则视为无效输出。\n"
    "3. 变式题与原题选项数量一致，难度相当，答案分布不要都落在同一个选项上。\n"
    "4. 每道变式给一句话解析（不超过 80 字），讲清答案怎么来的。\n"
    "5. 语言面向高中生，不用 markdown 格式符号。\n"
    "6. JSON 的键名必须严格使用下面给出的英文键（variants / stem / options / "
    "answer / explain），不要翻译成中文键名。\n"
    "7. 只输出 JSON，格式："
    '{"variants": [{"stem": "题干", "options": ["A内容", "B内容", "C内容", "D内容"], '
    '"answer": 0, "explain": "解析"}]}，answer 是正确选项的序号（从 0 开始）。'
)


def variants(q: dict, n: int = 2, conn=None) -> dict:
    """举一反三：{variants: [{stem, options, answer, explain}]}。"""
    if not enabled():
        raise RuntimeError("AI 服务未配置")
    if _stub_on():
        return variants_stub(q, n)

    n = max(1, min(int(n), 3))
    options = q.get("options", [])
    opt_lines = "\n".join(f"{LETTERS[i]}. {o}" for i, o in enumerate(options))
    user_msg = (
        f"原题：{q.get('stem', '')}\n"
        f"选项：\n{opt_lines}\n"
        f"知识点标签：{q.get('skill', '')}\n\n"
        f"请原创 {n} 道变式题，按系统要求输出 JSON。"
    )
    r = chat("variants", VARIANTS_PROMPT, user_msg, conn=conn, max_tokens=1600)
    parsed = _parse(r["text"])

    generated = parsed.get("variants")
    if not isinstance(generated, list) or not generated:
        raise RuntimeError("AI 生成的变式题数量不完整，请重试")
    out = []
    rejected = []
    stems = {q.get("stem", "").strip()}
    for v in generated:
        if not isinstance(v, dict):
            rejected.append("结构无效")
            continue
        stem = v.get("stem")
        opts = _strings(v.get("options"), "变式选项", 6)
        ans = v.get("answer")
        if not isinstance(stem, str) or not stem.strip() or len(stem) > 2000:
            rejected.append("题干为空")
            continue
        if stem.strip() in stems:
            rejected.append("题干与原题或其它变式重复")
            continue
        if len(opts) != len(options) or len(set(opts)) != len(opts):
            rejected.append("选项数量或内容不合规")
            continue
        if type(ans) is not int or not 0 <= ans < len(opts):
            rejected.append("答案越界")
            continue
        if not isinstance(v.get("explain"), str) or not v["explain"].strip():
            rejected.append("缺少解析")
            continue
        stem = stem.strip()
        stems.add(stem)
        out.append({
            "stem": stem,
            "options": opts,
            "answer": ans,
            "explain": str(v.get("explain", "")).strip()[:200],
        })
    if not out:
        detail = "、".join(dict.fromkeys(rejected)) or "格式不符"
        raise RuntimeError(f"AI 变式题无效（{detail}），请重试")
    out = out[:n]
    return {"variants": out, **_meta(r["channel"], r["model"])}


def variants_stub(q: dict, n: int = 2, conn=None) -> dict:
    n = max(1, min(int(n), 3))
    skill = q.get("skill", "") or "同知识点"
    n_opts = len(q.get("options", [])) or 4
    out = []
    for i in range(n):
        out.append({
            "stem": f"【演示变式 {i + 1}】配置 AI 服务后，这里会是一道围绕「{skill}」"
                    f"的原创变式选择题（与原题同考法、不同情境与数据）。",
            "options": [f"演示选项 {LETTERS[j]}" for j in range(n_opts)],
            "answer": i % n_opts,
            "explain": "演示模式（未配置 AI Key），配置后展示真实解析。",
        })
    return {"variants": out, "stub": True, **_meta("stub", "stub")}


# ---------------------------------------------------------------- 拍照识别（预留）

RECOGNIZE_PROMPT = (
    "你是题目录入助手。用户会给你一张手机拍摄的高中理科题目照片，"
    "请把照片里的题目完整转录成结构化文本。要求：\n"
    "1. 数学公式用纯文本表述（如 x^2、√3、分数写成 a/b），不要用 LaTeX。\n"
    "2. 只转录题目本身，不要作答、不要添加照片里没有的内容。\n"
    "3. 照片里有多道题时，只转录最完整的一道；文字看不清用〔?〕标注。\n"
    "4. 只输出 JSON，格式："
    '{"stem": "题干", "options": ["A内容", "B内容", "C内容", "D内容"], '
    '"subject": "physics|chemistry|math"}'
    "；不是选择题时 options 给空数组，subject 按学科判断。"
)


def recognize(image_b64: str, conn=None) -> dict:
    """拍照识别：照片 → {stem, options, subject}。

    只接受视觉通道（vision 标记）；调用方随拍照流程接入（预留接口）。
    """
    if not enabled():
        raise RuntimeError("AI 服务未配置")
    if _stub_on():
        return recognize_stub()

    r = chat("recognize", RECOGNIZE_PROMPT, "请转录照片里的题目。",
             conn=conn, max_tokens=1200, vision_only=True, images=[image_b64])
    parsed = _parse(r["text"])
    stem = str(parsed.get("stem", "")).strip()
    if not stem:
        raise RuntimeError("AI 没能从照片中识别出题目，请拍得更清晰些")
    subject = str(parsed.get("subject", "")).strip()
    subject = subject if subject in ("physics", "chemistry", "math") else ""
    return {
        "stem": stem[:2000],
        "options": [str(o).strip()[:200] for o in (parsed.get("options") or [])
                    if str(o).strip()][:6],
        "subject": subject,
        **_meta(r["channel"], r["model"]),
    }


def recognize_stub(conn=None) -> dict:
    return {
        "stem": "【演示识别】把质量 m=2kg 的物体从高处静止释放，忽略空气阻力，"
                "求下落 3s 内重力做的功（g 取 10 m/s²）。",
        "options": ["90 J", "180 J", "270 J", "360 J"],
        "subject": "physics",
        "stub": True,
        **_meta("stub", "stub"),
    }


# ---------------------------------------------------------------- 状态与用量

def config_public(conn=None) -> dict:
    """给前端的状态信息（不含密钥）：通道概况 + 任务路由 + 每任务限额。"""
    cfg = _load_cfg(conn)
    channels = {}
    for cid in ai_config.CHANNEL_ORDER:
        ch = CHANNELS.get(cid)
        if not ch:
            continue
        over = cfg["channels"].get(cid, {})
        channels[cid] = {
            "name": ch["name"],
            "model": over.get("model") or ch["model"],
            "enabled": bool(over.get("enabled", True)),
            "vision": bool(ch.get("vision")),
            "key_ok": bool(ch["key"]),
        }
    tasks = {}
    for t in ai_config.TASKS:
        options = candidates(t, cfg, vision_only=t == "recognize")
        channel, model = (options[0][0]["id"], options[0][1]) if options else (None, None)
        tasks[t] = {
            "label": ai_config.TASK_LABELS[t],
            "channel": channel,
            "model": model,
            "enabled": bool(options),
            "limit": cfg["limits"][t],
        }
    return {
        "enabled": any(t["enabled"] for t in tasks.values()),
        "stub": _stub_on(),
        "tasks": tasks,
        "channels": channels,
    }
