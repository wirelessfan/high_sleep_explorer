"""怪人军团回归测试：角色表、SVG 立绘与 API 契约。

只依赖标准库 unittest（TestClient 用例在缺少 httpx 时自动跳过）。运行：

    python -m unittest discover -s tests -v
"""
from __future__ import annotations

import json
import sys
import tempfile
import unittest
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app import content_loader, db  # noqa: E402

try:
    from fastapi.testclient import TestClient  # noqa: E402
    HAS_CLIENT = True
except Exception:  # pragma: no cover
    HAS_CLIENT = False

ASSETS = ROOT / "assets" / "bosses"
TOPICS = {
    "physics-induction": "physics",
    "chemistry-equilibrium": "chemistry",
    "math-derivative": "math",
}
SECTION_IDS = ["quick", "basic", "summary", "hard", "practice", "boss"]
SCIENTIST = {
    "physics-induction": "faraday",
    "chemistry-equilibrium": "curie",
    "math-derivative": "gauss",
}


def load_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def real_hp(topic_id: str, section_id: str) -> int:
    """按内容文件真实题量计算 HP，与生成器口径一致。"""
    sec = next(s for s in load_json(ROOT / "content" / "topics" / f"{topic_id}.json")["sections"]
               if s["id"] == section_id)
    t = sec["type"]
    if t in ("quiz", "boss"):
        return len(sec.get("questions", [])) or 1
    if t == "levels":
        return sum(len(l["questions"]) for l in sec.get("levels", [])) or 1
    if t == "myths":
        return len(sec.get("myths", [])) or 1
    if t == "steps":
        return sum(len(p["steps"]) for p in sec.get("problems", [])) or 1
    return 1  # reading


class BossCatalogTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.data = load_json(ROOT / "content" / "bosses.json")
        cls.bosses = cls.data["bosses"]
        cls.cards = {c["id"]: c for c in
                     load_json(ROOT / "content" / "cards" / "cards.json")["cards"]}

    def test_series_setting(self):
        series = self.data["series"]
        self.assertEqual(self.data["version"], 1)
        self.assertEqual(series["name"], "谬误研究所")
        self.assertEqual(len(series["art_style"]), 7)
        self.assertIn("原创", series["license"])
        self.assertIn("公有领域", series["license"])

    def test_every_section_has_exactly_one_boss(self):
        self.assertEqual(len(self.bosses), 18)
        seen = set()
        for b in self.bosses:
            key = (b["topic_id"], b["section_id"])
            self.assertNotIn(key, seen, f"重复守关者: {key}")
            seen.add(key)
            self.assertIn(b["topic_id"], TOPICS)
            self.assertIn(b["section_id"], SECTION_IDS)
        self.assertEqual(seen, {(t, s) for t in TOPICS for s in SECTION_IDS})

    def test_scientists_are_the_big_bosses(self):
        big = [b for b in self.bosses if b["tier"] == "big"]
        self.assertEqual(len(big), 3)
        for b in big:
            self.assertEqual(b["section_id"], "boss")
            card_id = b["card_id"]
            self.assertEqual(card_id, SCIENTIST[b["topic_id"]])
            self.assertIn(card_id, self.cards)
            self.assertEqual(b["name"], self.cards[card_id]["name"])
            self.assertEqual(b["code"], "BOSS")
        for b in self.bosses:
            if b["tier"] == "mini":
                self.assertIsNone(b["card_id"])
                self.assertNotEqual(b["section_id"], "boss")
                self.assertTrue(b["code"].startswith("No."))

    def test_hp_matches_real_question_count(self):
        for b in self.bosses:
            with self.subTest(boss=b["id"]):
                self.assertEqual(b["hp"], real_hp(b["topic_id"], b["section_id"]))
                self.assertGreaterEqual(b["hp"], 1)

    def test_metadata_complete(self):
        for b in self.bosses:
            with self.subTest(boss=b["id"]):
                for key in ("id", "name", "en", "code", "element", "skill",
                            "taunt", "purified", "svg", "colors", "hp"):
                    self.assertTrue(b.get(key), f"{b['id']} 缺 {key}")
                self.assertIn(b["colors"]["main"], ("#6366f1", "#10b981", "#f59e0b"))
                self.assertEqual(b["svg"], f"/assets/bosses/{b['id']}.svg")
        # 角色表不应夹带答案类字段
        blob = json.dumps(self.data, ensure_ascii=False)
        for hidden in ('"answer"', '"explain"', '"solution"'):
            self.assertNotIn(hidden, blob)

    def test_svg_assets_valid(self):
        files = sorted(ASSETS.glob("*.svg"))
        self.assertEqual(len(files), 18)
        for b in self.bosses:
            path = ASSETS / Path(b["svg"]).name
            self.assertTrue(path.is_file(), f"缺立绘: {path}")
            root = ET.parse(path).getroot()
            self.assertEqual(root.tag, "{http://www.w3.org/2000/svg}svg")
            self.assertEqual(root.attrib.get("viewBox"), "0 0 240 280")
            self.assertTrue(root.attrib.get("aria-label"))
            self.assertGreater(len(list(root.iter())), 20, f"{path.name} 内容过少")

    def test_generator_outputs_are_reproducible(self):
        """生成器重跑不应改变角色表内容（防止手改 JSON 与脚本脱节）。"""
        import subprocess
        before = (ROOT / "content" / "bosses.json").read_bytes()
        r = subprocess.run([sys.executable, str(ROOT / "tools" / "generate_bosses.py")],
                           cwd=ROOT, capture_output=True, text=True)
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual((ROOT / "content" / "bosses.json").read_bytes(), before)


class BossLoaderTests(unittest.TestCase):
    def setUp(self):
        content_loader.clear_cache()

    def test_boss_for_lookup_and_fallback(self):
        b = content_loader.boss_for("physics-induction", "boss")
        self.assertEqual(b["name"], "法拉第")
        self.assertEqual(b["tier"], "big")
        self.assertEqual(content_loader.boss_for("physics-induction", "nope"), None)
        self.assertIsNone(content_loader.boss_for("../evil", "quick"))

    def test_boss_for_returns_a_copy(self):
        b = content_loader.boss_for("math-derivative", "quick")
        b["name"] = "被篡改"
        self.assertNotEqual(content_loader.boss_for("math-derivative", "quick")["name"],
                            "被篡改")

    def test_clear_cache_covers_bosses(self):
        self.assertTrue(hasattr(content_loader.bosses(), "__getitem__"))
        content_loader.clear_cache()
        self.assertEqual(content_loader.bosses()["version"], 1)


@unittest.skipUnless(HAS_CLIENT, "需要 httpx")
class BossApiTests(unittest.TestCase):
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

    def test_bosses_endpoint(self):
        r = self.ctx.get("/api/v1/bosses", headers=self.headers)
        self.assertEqual(r.status_code, 200)
        d = r.json()
        self.assertEqual((d["total"], d["mini"], d["big"]), (18, 15, 3))
        self.assertEqual(len(d["bosses"]), 18)
        self.assertEqual(d["series"]["name"], "谬误研究所")

    def test_topic_and_section_embed_boss(self):
        t = self.ctx.get("/api/v1/topics/physics-induction", headers=self.headers).json()
        self.assertEqual(len(t["sections"]), 6)
        self.assertTrue(all(s.get("boss") for s in t["sections"]))
        self.assertEqual(t["sections"][-1]["boss"]["tier"], "big")

        s = self.ctx.get("/api/v1/topics/physics-induction/sections/quick",
                         headers=self.headers).json()
        self.assertEqual(s["boss"]["name"], "火花豆")
        self.assertNotIn("answer", json.dumps(s, ensure_ascii=False),
                         "boss 字段不得夹带答案")

    def test_static_svg_is_served(self):
        r = self.ctx.get("/assets/bosses/math-derivative-boss.svg")
        self.assertEqual(r.status_code, 200)
        self.assertIn("svg+xml", r.headers["content-type"])


if __name__ == "__main__":
    unittest.main()
