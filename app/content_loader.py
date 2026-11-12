"""内容加载、校验与答案剥离。"""
from __future__ import annotations

import json
import re
from datetime import date
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


@lru_cache(maxsize=1)
def daily() -> dict:
    """每日主题配置：轮转池、每日一句、节日特辑。"""
    return _read_json(CONTENT_DIR / "daily.json")


@lru_cache(maxsize=1)
def history() -> dict:
    """「历史上的今天」：科学/技术/医学领域的日期事件。"""
    return _read_json(CONTENT_DIR / "history.json")


def history_for(day: date) -> dict:
    """取当天的科学史上事件。

    当天没有条目时，退回到「日期上最近」的一条，并返回带符号的偏移天数
    （负数表示发生在几天前），前端据此提示「11 月 8 日」而不是假装是今天。
    """
    entries = history().get("entries") or []
    if not entries:
        return {"entry": None, "fallback": False, "offset": 0, "total": 0}

    for item in entries:
        if item.get("month") == day.month and item.get("day") == day.day:
            return {"entry": dict(item), "fallback": False, "offset": 0, "total": len(entries)}

    def doy(month: int, day_of_month: int) -> int:
        # 用闰年 2000 归一化，这样 2 月 29 日也能算出唯一序号
        return date(2000, month, day_of_month).timetuple().tm_yday

    today = doy(day.month, day.day)
    best = None
    for item in entries:
        raw = (doy(item["month"], item["day"]) - today) % 366
        signed = raw if raw <= 183 else raw - 366
        if best is None or abs(signed) < abs(best[0]):
            best = (signed, item)
    signed, item = best
    return {"entry": dict(item), "fallback": True, "offset": signed, "total": len(entries)}


def daily_for(day: date) -> dict:
    """按日期挑选每日主题。

    规则：当天的节日特辑优先，否则在 rotation 里按「日期序数取模」轮转——
    同一日期结果恒定，跨天自然推进，无需定时任务落库。
    """
    data = daily()
    special = None
    for item in data.get("special_days", []):
        if item.get("month") == day.month and item.get("day") == day.day:
            special = dict(item)
            break

    rotation = [t for t in data.get("rotation", []) if isinstance(t, str)]
    topic_id = (special or {}).get("topic")
    if not topic_id and rotation:
        topic_id = rotation[day.toordinal() % len(rotation)]

    quotes = data.get("quotes") or []
    quote = dict(quotes[day.toordinal() % len(quotes)]) if quotes else None
    return {"special": special, "topic_id": topic_id, "quote": quote}


def boss_for(topic_id: str, section_id: str) -> dict | None:
    """取某个版块的守关者；未配置时返回 None，调用方应优雅降级。"""
    if not _TOPIC_ID_RE.fullmatch(topic_id) or not _TOPIC_ID_RE.fullmatch(section_id):
        return None
    for boss in bosses()["bosses"]:
        if boss["topic_id"] == topic_id and boss["section_id"] == section_id:
            return dict(boss)  # 只读副本，避免调用方污染 lru_cache
    return None


# ---------------------------------------------------------------- 难度档位
#
# 每个版块可细分为「基础 / 进阶 / 高级」三档，对应 70–80 / 80–90 / 90–95 分水平。
# 老内容没有 tiers 字段时，整块内容视为 basic，另外两档显示为「建设中」，
# 因此新增档位是纯增量改动，不会让存量主题失效。

DEFAULT_TIERS = [
    {"id": "basic", "name": "基础", "score": "70–80 分", "multiplier": 1.0,
     "desc": "课本原文难度：概念、公式、常规例题。"},
    {"id": "advanced", "name": "进阶", "score": "80–90 分", "multiplier": 1.3,
     "desc": "综合与易错：多步推理、情境题、常见陷阱。"},
    {"id": "expert", "name": "高级", "score": "90–95 分", "multiplier": 1.6,
     "desc": "压轴与联动：多知识点交叉、边界条件。"},
]

# 版块里属于「某一档的具体内容」的字段，切档时被替换；其余字段由各档共享。
_CONTENT_KEYS = ("questions", "levels", "blocks", "videos", "myths", "problems", "egg")


def tier_meta() -> list[dict]:
    return catalog().get("tiers") or DEFAULT_TIERS


def tier_ids() -> list[str]:
    return [t["id"] for t in tier_meta()]


def tier_meta_of(tier: str) -> dict | None:
    return next((t for t in tier_meta() if t["id"] == tier), None)


def section_tiers(sec: dict) -> dict[str, dict]:
    """把版块拆成 {tier_id: 该档完整内容}。

    顶层内容天然就是「基础档」；tiers 里可以显式覆盖 basic，也可以只写
    advanced / expert（这是最常见的写作方式：基础留在顶层，高阶放 tiers）。
    """
    out: dict[str, dict] = {}
    if any(k in sec for k in _CONTENT_KEYS):
        out["basic"] = {k: v for k, v in sec.items() if k != "tiers"}
    tiers = sec.get("tiers")
    if isinstance(tiers, dict):
        for tid, payload in tiers.items():
            item = {k: v for k, v in sec.items() if k not in _CONTENT_KEYS and k != "tiers"}
            item.update(payload or {})
            out[tid] = item
    return out


def tier_content(sec: dict, tier: str) -> dict | None:
    return section_tiers(sec).get(tier)


def count_questions(sec: dict) -> int:
    t = sec.get("type")
    if t in ("quiz", "boss"):
        return len(sec.get("questions") or [])
    if t == "levels":
        return sum(len(lv.get("questions") or []) for lv in sec.get("levels") or [])
    if t == "myths":
        return len(sec.get("myths") or [])
    if t == "steps":
        return sum(len(p.get("steps") or []) for p in sec.get("problems") or [])
    return 1 if sec.get("blocks") else 0


def section_tier_list(sec: dict) -> list[dict]:
    """给前端的档位清单：名称、分数段、是否已开放、题量。"""
    have = section_tiers(sec)
    out = []
    for meta in tier_meta():
        content = have.get(meta["id"])
        out.append({
            "id": meta["id"],
            "name": meta["name"],
            "score": meta.get("score", ""),
            "desc": meta.get("desc", ""),
            "multiplier": meta.get("multiplier", 1.0),
            "available": content is not None,
            "questions": count_questions(content) if content else 0,
            "minutes": (content or {}).get("minutes", sec.get("minutes", 0)),
        })
    return out


def topic_pairs(topic_id: str) -> list[tuple[str, str]]:
    """该主题所有可学单元 (section_id, tier)，按「基础全通 → 进阶 → 高级」排列。"""
    data = topic(topic_id)
    pairs: list[tuple[str, str]] = []
    for tier in tier_ids():
        for sec in data["sections"]:
            if tier in section_tiers(sec):
                pairs.append((sec["id"], tier))
    return pairs


@lru_cache(maxsize=None)
def topic_minutes(topic_id: str) -> int:
    """主题全程预计分钟数：逐「已开放单元」累加，与主题页展示口径一致。

    catalog.json / 主题文件顶层的 `minutes` 是历史遗留的单档估值，扩到三档后
    会严重偏低。这里直接以 section_tier_list 为准，新增档位自动计入，无需手工维护。
    """
    data = topic(topic_id)
    return sum(
        item["minutes"]
        for sec in data["sections"]
        for item in section_tier_list(sec)
        if item["available"]
    )


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
    topic_minutes.cache_clear()
    cards.cache_clear()
    rewards.cache_clear()
    media.cache_clear()
    bosses.cache_clear()
    daily.cache_clear()
    history.cache_clear()
