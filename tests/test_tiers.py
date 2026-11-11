"""三档难度（基础/进阶/高级）回归测试。

覆盖：目录契约、内容切档、按档计分与进度隔离、旧库迁移。
"""
from __future__ import annotations

import json
import sqlite3
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app import content_loader, db  # noqa: E402

try:
    from fastapi.testclient import TestClient
    HAS_CLIENT = True
except Exception:  # pragma: no cover
    HAS_CLIENT = False

def _pick_topic(predicate, label: str) -> str:
    """按内容形态挑一个主题，避免硬编码主题名后一扩档测试就过期。"""
    for meta in content_loader.catalog()["topics"]:
        data = content_loader.topic(meta["id"])
        if predicate(data):
            return meta["id"]
    raise AssertionError(f"找不到满足条件的主题：{label}")


def _all_tiered(data) -> bool:
    return all(
        {"advanced", "expert"} <= set(sec.get("tiers") or {})
        for sec in data["sections"]
    )


def _none_tiered(data) -> bool:
    return all(not sec.get("tiers") for sec in data["sections"])


TIERED_TOPIC = _pick_topic(_all_tiered, "三档齐全")   # 例如 physics-electric
PLAIN_TOPIC = _pick_topic(_none_tiered, "仅有基础档")  # 例如 physics-energy


class TierLoaderTests(unittest.TestCase):
    def setUp(self):
        content_loader.clear_cache()

    def test_catalog_declares_three_tiers(self):
        tiers = content_loader.tier_meta()
        self.assertEqual([t["id"] for t in tiers], ["basic", "advanced", "expert"])
        self.assertEqual([t["name"] for t in tiers], ["基础", "进阶", "高级"])
        self.assertGreater(tiers[1]["multiplier"], tiers[0]["multiplier"])
        self.assertGreater(tiers[2]["multiplier"], tiers[1]["multiplier"])

    def test_plain_topic_only_has_basic(self):
        data = content_loader.topic(PLAIN_TOPIC)
        for sec in data["sections"]:
            tiers = content_loader.section_tiers(sec)
            self.assertEqual(list(tiers), ["basic"], sec["id"])
            listed = content_loader.section_tier_list(sec)
            self.assertEqual([t["available"] for t in listed], [True, False, False])

    def test_tiered_topic_has_all_tiers_on_every_section(self):
        data = content_loader.topic(TIERED_TOPIC)
        for sec in data["sections"]:
            listed = content_loader.section_tier_list(sec)
            with self.subTest(section=sec["id"]):
                self.assertTrue(all(t["available"] for t in listed))
                self.assertTrue(all(t["questions"] > 0 for t in listed))

    def test_tiers_do_not_leak_answers_via_api_shape(self):
        """strip_answers 必须对每一档都生效。"""
        data = content_loader.topic(TIERED_TOPIC)
        for sec in data["sections"]:
            for content in content_loader.section_tiers(sec).values():
                blob = json.dumps(content_loader.strip_answers(content), ensure_ascii=False)
                self.assertNotIn('"answer"', blob)
                self.assertNotIn('"explain"', blob)

    def test_topic_pairs_order_is_basic_first(self):
        pairs = content_loader.topic_pairs(TIERED_TOPIC)
        tiers = [t for _, t in pairs]
        self.assertEqual(tiers[:6], ["basic"] * 6)
        self.assertEqual(len(pairs), 18)  # 6 版块 × 3 档

    def test_content_volume_supports_multiple_weeks(self):
        """一个主题的题量应撑得住 1–2 周（每天 20–30 分钟）。"""
        data = content_loader.topic(TIERED_TOPIC)
        total = sum(
            content_loader.count_questions(c)
            for sec in data["sections"]
            for c in content_loader.section_tiers(sec).values()
        )
        self.assertGreaterEqual(total, 55, f"{TIERED_TOPIC} 题量偏少：{total}")


@unittest.skipUnless(HAS_CLIENT, "需要 httpx")
class TierApiTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self._old = db.DB_PATH
        db.DB_PATH = Path(self._tmp.name) / "app.db"
        db.init_db()
        content_loader.clear_cache()
        from app.main import app
        self.client = TestClient(app)
        self.ctx = self.client.__enter__()
        sess = self.ctx.post("/api/v1/session").json()
        self.headers = {"Authorization": "Bearer " + sess["token"]}

    def tearDown(self):
        self.client.__exit__(None, None, None)
        db.DB_PATH = self._old
        self._tmp.cleanup()

    @staticmethod
    def _answers(tier):
        """答案不在接口里下发，从内容文件直接取。"""
        data = content_loader.topic(TIERED_TOPIC)
        sec = next(x for x in data["sections"] if x["id"] == "quick")
        content = content_loader.tier_content(sec, tier)
        return {q["id"]: q["answer"] for q in content["questions"]}

    @staticmethod
    def _answers(tier):
        """答案不在接口里下发，从内容文件直接取。"""
        data = content_loader.topic(TIERED_TOPIC)
        sec = next(x for x in data["sections"] if x["id"] == "quick")
        content = content_loader.tier_content(sec, tier)
        return {q["id"]: q["answer"] for q in content["questions"]}

    def _section(self, tier):
        r = self.ctx.get(f"/api/v1/topics/{TIERED_TOPIC}/sections/quick?tier={tier}",
                         headers=self.headers)
        self.assertEqual(r.status_code, 200)
        return r.json()

    def test_topic_payload_exposes_tiers(self):
        d = self.ctx.get(f"/api/v1/topics/{TIERED_TOPIC}", headers=self.headers).json()
        self.assertEqual(len(d["tiers"]), 3)
        for sec in d["sections"]:
            self.assertEqual(len(sec["tiers"]), 3)
            self.assertTrue(all("status" in t for t in sec["tiers"]))

    def test_each_tier_serves_different_questions(self):
        stems = {}
        for tier in ("basic", "advanced", "expert"):
            sec = self._section(tier)["section"]
            stems[tier] = tuple(q["stem"] for q in sec["questions"])
        self.assertNotEqual(stems["basic"], stems["advanced"])
        self.assertNotEqual(stems["advanced"], stems["expert"])

    def test_unavailable_tier_reports_available_false(self):
        r = self.ctx.get(f"/api/v1/topics/{PLAIN_TOPIC}/sections/quick?tier=expert",
                         headers=self.headers)
        self.assertEqual(r.status_code, 200)
        self.assertFalse(r.json()["available"])
        self.assertIsNone(r.json()["section"])

    def test_unknown_tier_rejected(self):
        r = self.ctx.get(f"/api/v1/topics/{TIERED_TOPIC}/sections/quick?tier=god",
                         headers=self.headers)
        self.assertEqual(r.status_code, 400)

    def test_advanced_points_are_multiplied(self):
        # quick 基础分 15，进阶系数 1.3 → 20
        answers = self._answers("advanced")
        r = self.ctx.post(f"/api/v1/topics/{TIERED_TOPIC}/sections/quick/submit?tier=advanced",
                          json={"answers": answers}, headers=self.headers)
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.json()["points"], 20)
        self.assertEqual(r.json()["tier"], "advanced")

    def test_progress_isolated_between_tiers(self):
        for tier, expect in (("basic", 15), ("advanced", 20)):
            answers = self._answers(tier)
            r = self.ctx.post(f"/api/v1/topics/{TIERED_TOPIC}/sections/quick/submit?tier={tier}",
                              json={"answers": answers}, headers=self.headers)
            self.assertEqual(r.json()["points"], expect, tier)
            self.assertFalse(r.json()["is_review"], f"{tier} 不该被判成复习")

        items = self.ctx.get("/api/v1/progress", headers=self.headers).json()["items"]
        quick = {(i["section_id"], i["tier"]) for i in items if i["section_id"] == "quick"}
        self.assertEqual(quick, {("quick", "basic"), ("quick", "advanced")})

    def test_topics_without_upper_tiers_keep_old_total(self):
        d = self.ctx.get("/api/v1/catalog", headers=self.headers).json()
        items = {t["id"]: t for s in d["subjects"] for t in s["items"]}
        self.assertEqual(items[PLAIN_TOPIC]["total"], 6)
        self.assertEqual(items[TIERED_TOPIC]["total"], 18)
        self.assertEqual(set(items[TIERED_TOPIC]["tiers"]), {"basic", "advanced", "expert"})


class TierMigrationTests(unittest.TestCase):
    def test_v3_database_is_upgraded_in_place(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "old.db"
            conn = sqlite3.connect(path)
            conn.executescript("""
            CREATE TABLE schema_version (id INTEGER PRIMARY KEY CHECK (id = 1), version INTEGER NOT NULL);
            INSERT INTO schema_version(id, version) VALUES (1, 3);
            CREATE TABLE progress (
                user_id TEXT NOT NULL, topic_id TEXT NOT NULL, section_id TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'open', best_score INTEGER NOT NULL DEFAULT 0,
                attempts INTEGER NOT NULL DEFAULT 0, awarded INTEGER NOT NULL DEFAULT 0,
                updated_at TEXT NOT NULL,
                PRIMARY KEY (user_id, topic_id, section_id)
            );
            INSERT INTO progress VALUES ('u1','physics-newton','quick','done',100,1,1,'2026-11-11T10:00:00');
            """)
            conn.commit()
            conn.close()

            old = db.DB_PATH
            db.DB_PATH = path
            try:
                db.init_db()
                db.init_db()  # 幂等
                with db.ro() as c:
                    rows = c.execute("SELECT * FROM progress").fetchall()
                    version = c.execute("SELECT version FROM schema_version").fetchone()["version"]
                self.assertEqual(version, db.SCHEMA_VERSION)
                self.assertEqual(len(rows), 1)
                self.assertEqual(rows[0]["tier"], "basic")
                self.assertEqual(rows[0]["best_score"], 100)
            finally:
                db.DB_PATH = old


if __name__ == "__main__":
    unittest.main()
