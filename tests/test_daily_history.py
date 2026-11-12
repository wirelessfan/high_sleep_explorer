"""每日主题与「历史上的今天」回归测试。

覆盖：内容配置契约（rotation / special_days / quotes / history entries）、
轮转与回退语义、以及两个只读接口的响应契约。
"""

from __future__ import annotations

import sys
from datetime import date, timedelta
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from fastapi.testclient import TestClient  # noqa: E402

import app.db as db  # noqa: E402
from app import content_loader  # noqa: E402
from app.main import app  # noqa: E402


@pytest.fixture()
def client(tmp_path, monkeypatch):
    """每个用例一个独立数据库。"""
    monkeypatch.setattr(db, "DB_PATH", tmp_path / "test.db")
    content_loader.clear_cache()
    with TestClient(app) as c:
        yield c


@pytest.fixture()
def auth(client):
    r = client.post("/api/v1/session")
    assert r.status_code == 200
    return {"Authorization": f"Bearer {r.json()['token']}"}


def _doy(month: int, day: int) -> int:
    """年内序号（用闰年归一化，2 月 29 日也有唯一值）。"""
    return date(2000, month, day).timetuple().tm_yday


def _topic_ids() -> set[str]:
    return {t["id"] for t in content_loader.catalog()["topics"]}


# ---------------------------------------------------------------- 每日主题内容


class TestDailyContent:
    def test_rotation_length_and_topic_ids(self):
        data = content_loader.daily()
        rotation = data["rotation"]
        assert len(rotation) >= 5, "轮转池太短，一周就会重复"
        assert all(isinstance(t, str) for t in rotation)
        assert set(rotation) <= _topic_ids(), "轮转池引用了不存在的主题"

    def test_quotes_well_formed(self):
        quotes = content_loader.daily()["quotes"]
        assert quotes
        for q in quotes:
            assert q["text"].strip()
            assert q["by"].strip()

    def test_special_days_well_formed(self):
        specials = content_loader.daily()["special_days"]
        assert specials
        seen = set()
        for item in specials:
            assert item["id"] and item["title"]
            assert 1 <= item["month"] <= 12
            assert 1 <= item["day"] <= 31
            assert item.get("emoji")
            key = (item["month"], item["day"])
            assert key not in seen, f"节日日期重复：{key}"
            seen.add(key)
            assert item.get("topic") in _topic_ids(), "节日引用了不存在的主题"
            for d in item.get("digest") or []:
                assert d.get("q") and d.get("a")

    def test_double11_special(self):
        item = next((s for s in content_loader.daily()["special_days"]
                     if (s["month"], s["day"]) == (11, 11)), None)
        assert item is not None, "缺少双十一特辑"
        assert item["id"] == "double11"
        assert "双十一" in item["title"]
        assert len(item.get("digest") or []) >= 2, "双十一应带「算一算」小题"
        assert item.get("aside"), "双十一特辑应有一句提醒"

    def test_rotation_is_deterministic(self):
        day = date(2026, 11, 20)
        assert content_loader.daily_for(day) == content_loader.daily_for(day)

    def test_rotation_advances_across_days(self):
        start = date(2026, 11, 20)
        ids = [content_loader.daily_for(start + timedelta(days=i))["topic_id"]
               for i in range(10)]
        assert len(set(ids)) >= 5, "连续 10 天的今日主题重复过多"

    def test_special_overrides_rotation(self):
        info = content_loader.daily_for(date(2026, 11, 11))
        assert info["special"]["id"] == "double11"
        assert info["topic_id"] == info["special"]["topic"], "特辑应指定主题"

    def test_quote_always_available(self):
        for i in range(7):
            info = content_loader.daily_for(date(2026, 3, 1) + timedelta(days=i))
            assert info["quote"] and info["quote"]["text"]


# ------------------------------------------------------------ 历史上的今天内容


class TestHistoryContent:
    def test_entries_well_formed(self):
        entries = content_loader.history()["entries"]
        assert len(entries) >= 20, "事件库太薄，一年里大半时间要靠回退"
        for e in entries:
            assert 1 <= e["month"] <= 12
            assert 1 <= e["day"] <= 31
            # 允许古代事件（如公元 79 年维苏威火山），上限留到 2100
            assert isinstance(e["year"], int) and 1 <= e["year"] <= 2100
            assert e["title"].strip()
            assert len(e["story"]) >= 40, "故事太短，撑不起一张卡片"
            assert e["learn"].strip()

    def test_no_duplicate_calendar_days(self):
        keys = [(e["month"], e["day"]) for e in content_loader.history()["entries"]]
        assert len(keys) == len(set(keys))

    def test_topics_resolve(self):
        for e in content_loader.history()["entries"]:
            if e.get("topic"):
                assert e["topic"] in _topic_ids(), f"{e['title']} 关联了不存在的主题"

    def test_exact_match_has_zero_offset(self):
        info = content_loader.history_for(date(2026, 11, 11))
        assert info["fallback"] is False
        assert info["offset"] == 0
        assert (info["entry"]["month"], info["entry"]["day"]) == (11, 11)
        assert info["total"] == len(content_loader.history()["entries"])

    def test_fallback_picks_nearest_day_with_sign(self):
        entries = content_loader.history()["entries"]
        days = {(e["month"], e["day"]) for e in entries}
        # 找一个当天没有条目的日期
        probe = date(2026, 7, 2)
        while (probe.month, probe.day) in days:
            probe += timedelta(days=1)

        info = content_loader.history_for(probe)
        assert info["fallback"] is True
        assert info["offset"] != 0
        assert (info["entry"]["month"], info["entry"]["day"]) in days

        # 偏移量必须真的等于「条目在探针日期之后/之前几天」
        diff = _doy(info["entry"]["month"], info["entry"]["day"]) - _doy(probe.month, probe.day)
        if diff > 183:
            diff -= 366
        elif diff < -183:
            diff += 366
        assert diff == info["offset"]

    def test_fallback_stays_close(self):
        """事件库够密时，任何一天回退都不应超过一个月。"""
        days = {(e["month"], e["day"]) for e in content_loader.history()["entries"]}
        probe = date(2026, 1, 1)
        while probe.year == 2026:
            info = content_loader.history_for(probe)
            assert info["entry"] is not None
            assert abs(info["offset"]) <= 31, f"{probe} 回退了 {info['offset']} 天"
            if not info["fallback"]:
                assert (probe.month, probe.day) in days
            probe += timedelta(days=1)


# ---------------------------------------------------------------------- 接口


class TestDailyApi:
    def test_requires_auth(self, client):
        assert client.get("/api/v1/daily").status_code == 401

    def test_double11_payload(self, client, auth):
        r = client.get("/api/v1/daily", params={"date": "2026-11-11"}, headers=auth)
        assert r.status_code == 200
        data = r.json()
        assert data["special"]["id"] == "double11"
        assert len(data["special"]["digest"]) >= 2
        assert data["weekday"] == "周三"

    def test_double11_topic_matches_special(self, client, auth):
        r = client.get("/api/v1/daily", params={"date": "2026-11-11"}, headers=auth)
        data = r.json()
        special = next(s for s in content_loader.daily()["special_days"]
                       if s["id"] == "double11")
        assert data["topic"]["id"] == special["topic"]

    def test_plain_day_has_no_special(self, client, auth):
        r = client.get("/api/v1/daily", params={"date": "2026-11-12"}, headers=auth)
        assert r.status_code == 200
        data = r.json()
        assert data["special"] is None
        assert data["quote"]["text"]
        assert data["topic"]["title"]

    def test_topic_total_counts_units(self, client, auth):
        """total 必须等于「版块 × 已开放档位」，与目录页口径一致。"""
        r = client.get("/api/v1/daily", params={"date": "2026-11-11"}, headers=auth)
        data = r.json()
        pairs = content_loader.topic_pairs(data["topic"]["id"])
        assert data["topic"]["total"] == len(pairs)
        assert data["topic"]["percent"] == 0

    def test_bad_date_rejected(self, client, auth):
        r = client.get("/api/v1/daily", params={"date": "2026-11-31"}, headers=auth)
        assert r.status_code == 400


class TestHistoryApi:
    def test_requires_auth(self, client):
        assert client.get("/api/v1/history").status_code == 401

    def test_exact_day_payload(self, client, auth):
        r = client.get("/api/v1/history", params={"date": "2026-11-11"}, headers=auth)
        assert r.status_code == 200
        data = r.json()
        assert data["fallback"] is False
        assert data["offset_days"] == 0
        assert data["entry_date"] == "11 月 11 日"
        entry = data["entry"]
        assert entry["year"] == 1572
        for key in ("field", "person", "title", "story", "learn"):
            assert entry[key].strip()
        assert data["topic"] and data["topic"]["title"] == "电磁感应"

    def test_fallback_flag_is_reported(self, client, auth):
        r = client.get("/api/v1/history", params={"date": "2026-11-13"}, headers=auth)
        assert r.status_code == 200
        data = r.json()
        assert data["fallback"] is True
        assert data["offset_days"] < 0, "过去的事件偏移应为负数"
        assert data["entry"]["title"]

    def test_defaults_to_today(self, client, auth):
        r = client.get("/api/v1/history", headers=auth)
        assert r.status_code == 200
        data = r.json()
        assert data["date"] == date.today().isoformat()
        assert data["entry"]["title"]

    def test_bad_date_rejected(self, client, auth):
        r = client.get("/api/v1/history", params={"date": "13-11-2026"}, headers=auth)
        assert r.status_code == 400
