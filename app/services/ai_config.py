"""AI 策略配置：ai_config 单行表，管理员运行时可调，改完即生效（无需重启）。

职责
- 默认策略（任务路由 / 每任务限额）在此定义，与 ai_client.CHANNELS 对齐；
- load() 把库里的覆盖项合并到默认之上，永远返回完整可用配置；
- save() 做白名单校验后整体落库（只存管理员设置过的覆盖项，默认项不落库，
  未来新增任务/通道时老配置自动回落到新默认）。
- API Key 不在本模块视野内：通道密钥只来自环境变量，这里只存非敏感策略面。
"""
from __future__ import annotations

import json
import sqlite3

# 任务清单：analyze=错因分析（现有）solve=AI 解题 variants=举一反三
# recognize=拍照识别（通道与协议已就位，调用方随拍照流程接入）
TASKS = ("analyze", "solve", "variants", "recognize", "review", "photo_confirm")
LEGACY_TASKS = ("analyze", "solve", "variants", "recognize")
REVIEW_CHANNEL_ORDER = ("review91", "reviewugq")

TASK_LABELS = {
    "analyze": "错因分析",
    "solve": "AI 解题",
    "variants": "举一反三",
    "recognize": "拍照识别",
    "review": "题库审校",
    "photo_confirm": "原图转录确认",
}

# 通道 id；按能力/价格升序（glm 最便宜，gpt 最强最贵），也是回退链的顺序
CHANNEL_ORDER = ("glm", "deepseek", "gpt")
ALL_CHANNELS = CHANNEL_ORDER + REVIEW_CHANNEL_ORDER

DEFAULT_ROUTING = {
    "analyze": "glm",
    "solve": "deepseek",
    "variants": "glm",
    # 识图专用通道：部署前必须用真实图片验证并显式打开 vision 标记。
    "recognize": "glm",
    "photo_confirm": "review91",
    "review": "review91",
}

DEFAULT_LIMITS = {
    "analyze": 20,
    "solve": 10,
    "variants": 5,
    "recognize": 10,
    "review": 10,
    "photo_confirm": 10,
}


def load(conn: sqlite3.Connection) -> dict:
    """读全量配置：默认 + 库内覆盖。非法项（手改库）静默丢弃，不让路由崩。"""
    row = conn.execute("SELECT config FROM ai_config WHERE id = 1").fetchone()
    saved: dict = {}
    if row:
        try:
            saved = json.loads(row["config"])
        except (json.JSONDecodeError, TypeError):
            saved = {}
        if not isinstance(saved, dict):
            saved = {}

    routing = dict(DEFAULT_ROUTING)
    for t, cid in _object(saved.get("routing")).items():
        allowed = REVIEW_CHANNEL_ORDER if t in ("review", "photo_confirm") else CHANNEL_ORDER
        if t in TASKS and cid in allowed:
            routing[t] = cid

    limits = {t: DEFAULT_LIMITS[t] for t in TASKS}
    for t, n in _object(saved.get("limits")).items():
        if t in TASKS and type(n) is int and 1 <= n <= 200:
            limits[t] = n

    channels: dict[str, dict] = {}
    for cid in ALL_CHANNELS:
        over = _object(_object(saved.get("channels")).get(cid))
        channels[cid] = {
            "enabled": over.get("enabled") if type(over.get("enabled")) is bool else True,
            "model": over["model"].strip()[:80] or None if isinstance(over.get("model"), str) else None,
        }

    return {"routing": routing, "limits": limits, "channels": channels}


def _object(value) -> dict:
    return value if isinstance(value, dict) else {}


def save(conn: sqlite3.Connection, patch: dict, by_user_id: str) -> dict:
    """校验并落库覆盖项，返回合并后的全量配置。

    patch 允许的字段：routing / limits / channels；其余忽略。
    校验失败抛 ValueError（路由层转 400）。
    """
    if not isinstance(patch, dict):
        raise ValueError("配置格式不正确")

    out: dict = {}

    if "routing" in patch:
        routing_in = patch.get("routing")
        if not isinstance(routing_in, dict):
            raise ValueError("routing 必须是对象")
        routing = {}
        for t, cid in routing_in.items():
            if t not in TASKS:
                raise ValueError(f"未知任务：{t}")
            allowed = REVIEW_CHANNEL_ORDER if t in ("review", "photo_confirm") else CHANNEL_ORDER
            if cid not in allowed:
                raise ValueError(f"未知通道：{cid}")
            routing[t] = cid
        if routing:
            out["routing"] = routing

    if "limits" in patch:
        limits_in = patch.get("limits")
        if not isinstance(limits_in, dict):
            raise ValueError("limits 必须是对象")
        limits = {}
        for t, n in limits_in.items():
            if t not in TASKS:
                raise ValueError(f"未知任务：{t}")
            if type(n) is not int or not 1 <= n <= 200:
                raise ValueError(f"限额必须是 1-200 的整数：{t}")
            limits[t] = n
        if limits:
            out["limits"] = limits

    if "channels" in patch:
        channels_in = patch.get("channels")
        if not isinstance(channels_in, dict):
            raise ValueError("channels 必须是对象")
        channels = {}
        for cid, over in channels_in.items():
            if cid not in ALL_CHANNELS:
                raise ValueError(f"未知通道：{cid}")
            if not isinstance(over, dict):
                raise ValueError(f"通道配置格式不正确：{cid}")
            entry: dict = {}
            if "enabled" in over:
                if type(over["enabled"]) is not bool:
                    raise ValueError("enabled 必须是布尔值")
                entry["enabled"] = over["enabled"]
            if "model" in over:
                if over["model"] is not None and not isinstance(over["model"], str):
                    raise ValueError("model 必须是字符串或 null")
                if len(over.get("model") or "") > 80:
                    raise ValueError("model 不能超过 80 字符")
                entry["model"] = (over.get("model") or "").strip() or None
            channels[cid] = entry
        if channels:
            out["channels"] = channels

    if not out:
        raise ValueError("没有可保存的配置项")

    merged = load(conn)
    for key, values in out.items():
        if key == "channels":
            for cid, entry in values.items():
                merged[key][cid].update(entry)
        else:
            merged[key].update(values)

    conn.execute(
        "INSERT INTO ai_config(id, config, updated_at, updated_by) VALUES (1,?,?,?) "
        "ON CONFLICT(id) DO UPDATE SET config=excluded.config, "
        "updated_at=excluded.updated_at, updated_by=excluded.updated_by",
        (json.dumps(merged, ensure_ascii=False), _now(), by_user_id),
    )
    return load(conn)


def reset(conn: sqlite3.Connection) -> dict:
    """清空覆盖项，回到内置默认。"""
    conn.execute("DELETE FROM ai_config WHERE id = 1")
    return load(conn)


def _now() -> str:
    from datetime import datetime
    return datetime.now().isoformat(timespec="seconds")
