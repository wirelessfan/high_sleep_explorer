"""代码 Review 回归测试：锁住已修复的后端缺陷。

只用标准库 unittest，不引入额外依赖。运行：

    python -m unittest discover -s tests -v

TestClient 相关用例在缺少 httpx 时会自动跳过。
"""
from __future__ import annotations

import sqlite3
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app import content_loader, db
from app.services import events, gacha, ratelimit, scoring
from app.routers import progress as progress_router

try:
    from fastapi.testclient import TestClient
    HAS_CLIENT = True
except Exception:  # pragma: no cover - 取决于运行环境是否装了 httpx
    HAS_CLIENT = False


SECTION_IDS = ["quick", "basic", "summary", "hard", "practice", "boss"]
NOW = "2026-11-11"


class WithTempDb(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self._old_path = db.DB_PATH
        db.DB_PATH = Path(self._tmp.name) / "app.db"
        db.init_db()
        content_loader.clear_cache()
        ratelimit.reset()

    def tearDown(self):
        db.DB_PATH = self._old_path
        self._tmp.cleanup()

    def make_user(self, uid="u_test", tickets=0, shards=0) -> sqlite3.Row:
        with db.tx() as conn:
            conn.execute(
                "INSERT INTO users(id, token_hash, sync_code, created_at, last_seen, tickets, shards) "
                "VALUES (?,?,?,?,?,?,?)",
                (uid, f"hash-{uid}", f"code-{uid}", NOW, NOW, tickets, shards),
            )
            row = conn.execute("SELECT * FROM users WHERE id=?", (uid,)).fetchone()
        return row

    def mark_all_done(self, uid, topic_id="physics-induction"):
        """按「版块 × 已开放档位」逐单元标记完成，与全通判定同口径。"""
        pairs = content_loader.topic_pairs(topic_id)
        with db.tx() as conn:
            for sid, tier in pairs:
                conn.execute(
                    "INSERT OR REPLACE INTO progress"
                    "(user_id, topic_id, section_id, tier, status, best_score, attempts, awarded, updated_at) "
                    "VALUES (?,?,?,?,'done',100,1,1,?)",
                    (uid, topic_id, sid, tier, NOW),
                )


class TestEventScoping(WithTempDb):
    """events.key 曾全局唯一，导致第二个以后的用户领不到奖励。"""

    def test_two_users_both_get_topic_and_set_awards(self):
        for uid in ("u_A", "u_B"):
            self.make_user(uid)
            self.mark_all_done(uid)

        with db.tx() as conn:
            for uid in ("u_A", "u_B"):
                r = scoring.topic_complete(conn, uid, "physics-induction", SECTION_IDS)
                self.assertTrue(r["complete"], f"{uid} 未拿到主题全通券")
                self.assertEqual(r["tickets"], 2)
                self.assertEqual(scoring.award_set(conn, uid, "electromagnetic", 50), 50)
            rows = conn.execute("SELECT user_id, key FROM events ORDER BY user_id, key").fetchall()
            keys = [(r["user_id"], r["key"]) for r in rows]

        self.assertEqual(len(keys), 4)
        self.assertTrue(all(k.startswith(f"{u}:") for u, k in keys))
        for uid in ("u_A", "u_B"):
            row = self._user(uid)
            self.assertEqual(row["tickets"], 2)
            self.assertEqual(row["points"], 50)

    def test_topic_complete_is_idempotent_per_user(self):
        self.make_user("u_A")
        self.mark_all_done("u_A")
        with db.tx() as conn:
            first = scoring.topic_complete(conn, "u_A", "physics-induction", SECTION_IDS)
            second = scoring.topic_complete(conn, "u_A", "physics-induction", SECTION_IDS)
        self.assertEqual(first["tickets"], 2)
        self.assertEqual(second["tickets"], 0)
        self.assertEqual(self._user("u_A")["tickets"], 2)

    def test_award_section_does_not_double_pay(self):
        """_log_event 返回 False 时不能再加分。"""
        self.make_user("u_A")
        with db.tx() as conn:
            first = scoring.award_section(conn, "u_A", "physics-induction", "quick", 100, True, False)
            second = scoring.award_section(conn, "u_A", "physics-induction", "quick", 100, True, False)
        self.assertEqual(first["points"], 15)
        self.assertEqual(second["points"], 0)
        self.assertEqual(self._user("u_A")["points"], 15)

    def _user(self, uid):
        with db.ro() as conn:
            return conn.execute("SELECT * FROM users WHERE id=?", (uid,)).fetchone()


class TestSchemaAndTx(WithTempDb):
    def test_schema_version_and_composite_unique(self):
        with db.ro() as conn:
            version = conn.execute("SELECT version FROM schema_version WHERE id=1").fetchone()["version"]
            unique_indexes = []
            for idx in conn.execute("PRAGMA index_list('events')"):
                if not idx["unique"]:
                    continue
                cols = [r["name"] for r in conn.execute(f"PRAGMA index_info('{idx['name']}')")]
                unique_indexes.append(cols)
        self.assertEqual(version, db.SCHEMA_VERSION)
        self.assertIn(["user_id", "key"], unique_indexes,
                      "events 必须按 (user_id, key) 唯一，不能只按 key 全局唯一")
        self.assertNotIn(["key"], unique_indexes)

    def test_old_global_unique_db_is_migrated(self):
        """模拟 v1 旧库：key 全局 UNIQUE + 无 schema_version。"""
        with db.tx() as conn:
            conn.execute("DROP TABLE events")
            conn.execute(
                "CREATE TABLE events (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id TEXT NOT NULL, "
                "key TEXT NOT NULL UNIQUE, kind TEXT NOT NULL, payload TEXT, created_at TEXT NOT NULL)"
            )
            conn.execute("DELETE FROM schema_version")
            conn.execute(
                "INSERT INTO events(user_id, key, kind, payload, created_at) VALUES (?,?,?,?,?)",
                ("u_A", "legacy-key", "first", "{}", NOW),
            )
        db.init_db()
        with db.ro() as conn:
            version = conn.execute("SELECT version FROM schema_version WHERE id=1").fetchone()["version"]
            n = conn.execute("SELECT COUNT(*) AS n FROM events").fetchone()["n"]
        # 版本号会随 schema 演进增长，这里只要求「已迁移到最新」且旧数据还在
        self.assertEqual(version, db.SCHEMA_VERSION)
        self.assertEqual(n, 1, "迁移必须保留旧事件")
        # 迁移后同一业务键允许不同用户共存（旧库里会互相挡住）
        with db.tx() as conn:
            self.assertTrue(events.log(conn, "u_A", "legacy-key", "first", {}))
            self.assertTrue(events.log(conn, "u_B", "legacy-key", "first", {}))
            self.assertFalse(events.log(conn, "u_A", "legacy-key", "first", {}))

    def test_begin_failure_keeps_original_exception(self):
        class BrokenConn:
            in_transaction = False

            def execute(self, sql, *args):
                if sql == "BEGIN IMMEDIATE":
                    raise sqlite3.OperationalError("database is locked")
                raise AssertionError("不应执行 ROLLBACK")

            def close(self):
                pass

        original = db.connect
        db.connect = lambda: BrokenConn()
        try:
            with self.assertRaises(sqlite3.OperationalError) as ctx:
                with db.tx():
                    pass
            self.assertIn("database is locked", str(ctx.exception))
        finally:
            db.connect = original


class TestGacha(WithTempDb):
    def test_draw_replay_does_not_charge_twice(self):
        self.make_user("u_A", tickets=10)
        user = self._fresh("u_A")
        with db.tx() as conn:
            first = gacha.draw(conn, user, 1, "key-1")
            second = gacha.draw(conn, self._fresh_conn_user(conn, "u_A"), 1, "key-1")
        self.assertFalse(first["replayed"])
        self.assertTrue(second["replayed"])
        self.assertEqual(second["results"], first["results"])
        self.assertEqual(self._user("u_A")["tickets"], 9)

    def test_invalid_count_rejected_in_service_layer(self):
        self.make_user("u_A", tickets=10)
        for bad in (-1, 0, 11, "5", True):
            with db.tx() as conn:
                with self.assertRaises(ValueError):
                    gacha.draw(conn, self._fresh("u_A"), bad, f"bad-{bad}")

    def test_draw_key_is_user_scoped(self):
        """两个用户用同一个客户端 key 互不干扰。"""
        self.make_user("u_A", tickets=5)
        self.make_user("u_B", tickets=5)
        with db.tx() as conn:
            a = gacha.draw(conn, self._fresh("u_A"), 1, "same-key")
            b = gacha.draw(conn, self._fresh("u_B"), 1, "same-key")
        self.assertFalse(a["replayed"])
        self.assertFalse(b["replayed"])
        self.assertEqual(self._user("u_A")["tickets"], 4)
        self.assertEqual(self._user("u_B")["tickets"], 4)

    def _fresh(self, uid):
        with db.ro() as conn:
            return conn.execute("SELECT * FROM users WHERE id=?", (uid,)).fetchone()

    def _fresh_conn_user(self, conn, uid):
        return conn.execute("SELECT * FROM users WHERE id=?", (uid,)).fetchone()

    def _user(self, uid):
        return self._fresh(uid)


class TestGradingAndContent(WithTempDb):
    def test_steps_need_all_answers(self):
        section = {"type": "steps"}
        partial = {"details": [{"picked": 0}, {"picked": None}]}
        full = {"details": [{"picked": 0}, {"picked": 1}]}
        self.assertFalse(progress_router._is_passed(section, partial))
        self.assertTrue(progress_router._is_passed(section, full))

    def test_topic_id_rejects_traversal(self):
        with self.assertRaises(content_loader.ContentError):
            content_loader.topic("../cards/cards")
        self.assertIsInstance(content_loader.topic("physics-induction"), dict)

    def test_strip_answers_is_recursive(self):
        src = {"questions": [{"id": "q1", "options": ["a", "b"], "answer": 1,
                              "explain": "secret", "solution": "secret2"}]}
        safe = content_loader.strip_answers(src)
        dumped = repr(safe)
        for word in ("secret", "secret2", "'answer'", "'explain'", "'solution'"):
            self.assertNotIn(word, dumped)
        self.assertIn("options", dumped)
        self.assertEqual(src["questions"][0]["answer"], 1, "不得修改原对象")


class TestRateLimit(unittest.TestCase):
    def setUp(self):
        ratelimit.reset()

    def test_sliding_window(self):
        for _ in range(5):
            self.assertTrue(ratelimit.allow("adopt:1.2.3.4", 5, 600))
        self.assertFalse(ratelimit.allow("adopt:1.2.3.4", 5, 600))
        self.assertTrue(ratelimit.allow("adopt:5.6.7.8", 5, 600))


@unittest.skipUnless(HAS_CLIENT, "需要 httpx / fastapi.testclient")
class TestApiGuards(WithTempDb):
    def _client(self):
        from app.main import app
        return TestClient(app)

    def test_empty_submit_is_rejected(self):
        with self._client() as c:
            s = c.post("/api/v1/session").json()
            h = {"Authorization": "Bearer " + s["token"]}
            r = c.post("/api/v1/topics/physics-induction/sections/practice/submit",
                       json={"answers": {}}, headers=h)
            self.assertEqual(r.status_code, 400)

    def test_partial_steps_do_not_pass(self):
        with self._client() as c:
            s = c.post("/api/v1/session").json()
            h = {"Authorization": "Bearer " + s["token"]}
            r = c.post("/api/v1/topics/physics-induction/sections/practice/submit",
                       json={"answers": {"p0s0": 0}}, headers=h)
            self.assertEqual(r.status_code, 200)
            body = r.json()
            self.assertFalse(body["passed"])
            self.assertEqual(body["points"], 0)

    def test_draw_requires_idempotency_key(self):
        with self._client() as c:
            s = c.post("/api/v1/session").json()
            h = {"Authorization": "Bearer " + s["token"]}
            r = c.post("/api/v1/cards/draw", json={"count": 1}, headers=h)
            self.assertEqual(r.status_code, 422)

    def test_adopt_is_rate_limited(self):
        ratelimit.reset()
        with self._client() as c:
            for _ in range(5):
                c.post("/api/v1/session/adopt", json={"sync_code": "ABCD-EFGH-JKMN"})
            r = c.post("/api/v1/session/adopt", json={"sync_code": "ABCD-EFGH-JKMN"})
            self.assertEqual(r.status_code, 429)


if __name__ == "__main__":
    unittest.main(verbosity=2)
