"""内容加载、校验与答案剥离。"""
from __future__ import annotations

import json
import re
from functools import lru_cache
from pathlib import Path
from typing import Any

CONTENT_DIR = Path(__file__).resolve().parent.parent / "content"

# 答案类字段统一剥离。新增内容若换用别的字段名，务必同步加到这里。
_HIDDEN_KEYS = frozenset((
    "answer", "explain", "solution", "answer_index", "accept",
    "answer_key", "correct_index", "right_answer", "rubric", "solution_steps",
))

# 主题 id 直接参与文件路径拼接，必须收窄到安全字符集，避免路径穿越。
_TOPIC_ID_RE = re.compile(r"^[a-z0-9][a-z0-9_-]{0,63}$")


class ContentError(Exception):
    pass


def _read_json(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        raise ContentError(f"内容文件不存在: {path.name}")
    except json.JSONDecodeError as exc:
        raise ContentError(f"内容文件 JSON 解析失败: {path.name} -> {exc}")


@lru_cache(maxsize=1)
def catalog() -> dict:
    return _read_json(CONTENT_DIR / "catalog.json")


@lru_cache(maxsize=32)
def topic(topic_id: str) -> dict:
    if not _TOPIC_ID_RE.fullmatch(topic_id):
        raise ContentError("主题 id 不合法")
    path = CONTENT_DIR / "topics" / f"{topic_id}.json"
    data = _read_json(path)
    if data.get("id") != topic_id:
        raise ContentError(f"主题 id 不匹配: {path.name}")
    return data


@lru_cache(maxsize=1)
def cards() -> dict:
    return _read_json(CONTENT_DIR / "cards" / "cards.json")


@lru_cache(maxsize=1)
def rewards() -> dict:
    return _read_json(CONTENT_DIR / "rewards.json")


@lru_cache(maxsize=1)
def media() -> dict:
    return _read_json(CONTENT_DIR / "media" / "media.json")


@lru_cache(maxsize=1)
def bosses() -> dict:
    """怪人军团角色表（含系列设定），由 tools/generate_bosses.py 生成。"""
    return _read_json(CONTENT_DIR / "bosses.json")


def boss_for(topic_id: str, section_id: str) -> dict | None:
    """取某个版块的守关者；未配置时返回 None，调用方应优雅降级。"""
    if not _TOPIC_ID_RE.fullmatch(topic_id) or not _TOPIC_ID_RE.fullmatch(section_id):
        return None
    for boss in bosses()["bosses"]:
        if boss["topic_id"] == topic_id and boss["section_id"] == section_id:
            return dict(boss)  # 只读副本，避免调用方污染 lru_cache
    return None


def strip_answers(obj: Any) -> Any:
    """递归移除答案类字段，返回可安全下发给前端的副本。"""
    if isinstance(obj, dict):
        return {k: strip_answers(v) for k, v in obj.items() if k not in _HIDDEN_KEYS}
    if isinstance(obj, list):
        return [strip_answers(v) for v in obj]
    return obj


def clear_cache() -> None:
    catalog.cache_clear()
    topic.cache_clear()
    cards.cache_clear()
    rewards.cache_clear()
    media.cache_clear()
    bosses.cache_clear()
