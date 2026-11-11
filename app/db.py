"""SQLite 访问层：连接、建表、迁移、事务。"""
from __future__ import annotations

import os
import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator

DB_PATH = Path(os.environ.get("LEARN_DB", Path(__file__).resolve().parent.parent / "data" / "app.db"))

# v1 = 初版（events.key 全局唯一）；v2 = events 改为按 (user_id, key) 唯一；
# v3 = users 增加 username / password_hash（账号登录）；
# v4 = progress 增加 tier（基础/进阶/高级三档难度），主键改为四元组。
SCHEMA_VERSION = 4

SCHEMA = """
CREATE TABLE IF NOT EXISTS schema_version (
    id INTEGER PRIMARY KEY CHECK (id = 1),
    version INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS users (
    id TEXT PRIMARY KEY,
    token_hash TEXT NOT NULL UNIQUE,
    sync_code TEXT NOT NULL UNIQUE,
    nickname TEXT NOT NULL DEFAULT 'sunny',
    username TEXT,
    password_hash TEXT,
    points INTEGER NOT NULL DEFAULT 0,
    streak INTEGER NOT NULL DEFAULT 0,
    last_checkin TEXT,
    tickets INTEGER NOT NULL DEFAULT 0,
    shards INTEGER NOT NULL DEFAULT 0,
    pity_sr INTEGER NOT NULL DEFAULT 0,
    pity_ssr INTEGER NOT NULL DEFAULT 0,
    makeup_used INTEGER NOT NULL DEFAULT 0,
    makeup_month TEXT,
    created_at TEXT NOT NULL,
    last_seen TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS progress (
    user_id TEXT NOT NULL,
    topic_id TEXT NOT NULL,
    section_id TEXT NOT NULL,
    tier TEXT NOT NULL DEFAULT 'basic',
    status TEXT NOT NULL DEFAULT 'open',
    best_score INTEGER NOT NULL DEFAULT 0,
    attempts INTEGER NOT NULL DEFAULT 0,
    awarded INTEGER NOT NULL DEFAULT 0,
    updated_at TEXT NOT NULL,
    PRIMARY KEY (user_id, topic_id, section_id, tier)
);

CREATE TABLE IF NOT EXISTS checkins (
    user_id TEXT NOT NULL,
    day TEXT NOT NULL,
    points INTEGER NOT NULL,
    streak INTEGER NOT NULL,
    makeup INTEGER NOT NULL DEFAULT 0,
    PRIMARY KEY (user_id, day)
);

CREATE TABLE IF NOT EXISTS card_owned (
    user_id TEXT NOT NULL,
    card_id TEXT NOT NULL,
    count INTEGER NOT NULL DEFAULT 1,
    first_at TEXT NOT NULL,
    PRIMARY KEY (user_id, card_id)
);

CREATE TABLE IF NOT EXISTS draws (
    id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL,
    card_id TEXT NOT NULL,
    rarity TEXT NOT NULL,
    is_new INTEGER NOT NULL DEFAULT 0,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id TEXT NOT NULL,
    key TEXT NOT NULL,
    kind TEXT NOT NULL,
    payload TEXT,
    created_at TEXT NOT NULL,
    UNIQUE (user_id, key)
);

-- 成就卡：积分兑换出的凭证，code 即兑现码
CREATE TABLE IF NOT EXISTS achievements (
    id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL,
    code TEXT NOT NULL UNIQUE,
    ymd TEXT NOT NULL,             -- 产出日 YYYY-MM-DD，用于日上限与每日抽卡
    points INTEGER NOT NULL,       -- 消耗积分（每日抽卡为 0）
    value_cny INTEGER NOT NULL,    -- 面值（元）
    status TEXT NOT NULL DEFAULT 'issued',  -- issued / redeemed / void
    source TEXT NOT NULL DEFAULT 'redeem',  -- redeem（积分兑换）/ daily（每日抽卡）
    gifted_from TEXT,              -- 赠予人 user_id；NULL 表示自己获得
    created_at TEXT NOT NULL,
    redeemed_at TEXT,
    gifted_at TEXT
);

CREATE INDEX IF NOT EXISTS idx_achv_user ON achievements(user_id, ymd);
CREATE INDEX IF NOT EXISTS idx_achv_code ON achievements(code);

-- progress / checkins 的复合主键已覆盖 (user_id, ...) 前缀，不需要重复索引。
CREATE INDEX IF NOT EXISTS idx_draws_user ON draws(user_id, created_at);
CREATE INDEX IF NOT EXISTS idx_events_user_kind ON events(user_id, kind, created_at);
"""


def connect() -> sqlite3.Connection:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH, timeout=15, isolation_level=None)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA synchronous=NORMAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


@contextmanager
def tx() -> Iterator[sqlite3.Connection]:
    """事务：正常提交，异常回滚。

    BEGIN IMMEDIATE 本身失败（例如拿不到写锁）时连接并不在事务中，
    直接 ROLLBACK 会抛出 "no transaction is active" 并掩盖原始异常。
    """
    conn = connect()
    try:
        conn.execute("BEGIN IMMEDIATE")
        yield conn
        conn.execute("COMMIT")
    except Exception:
        if getattr(conn, "in_transaction", False):
            conn.execute("ROLLBACK")
        raise
    finally:
        conn.close()


@contextmanager
def ro() -> Iterator[sqlite3.Connection]:
    conn = connect()
    try:
        yield conn
    finally:
        conn.close()


def _migrate_events(conn: sqlite3.Connection) -> None:
    """把 v1 的 events.key 全局唯一结构重建为 v2 的 (user_id, key) 唯一。

    数据全量保留；幂等，重复执行安全。
    """
    conn.executescript("""
    CREATE TABLE IF NOT EXISTS events_v2 (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id TEXT NOT NULL,
        key TEXT NOT NULL,
        kind TEXT NOT NULL,
        payload TEXT,
        created_at TEXT NOT NULL,
        UNIQUE (user_id, key)
    );
    INSERT OR IGNORE INTO events_v2(id, user_id, key, kind, payload, created_at)
        SELECT id, user_id, key, kind, payload, created_at FROM events;
    DROP TABLE events;
    ALTER TABLE events_v2 RENAME TO events;
    CREATE INDEX IF NOT EXISTS idx_events_user_kind ON events(user_id, kind, created_at);
    """)


def _migrate_users_credentials(conn: sqlite3.Connection) -> None:
    """v3：给 users 补账号与口令字段。

    老库（v2 及以前）的 users 表没有 username/password_hash，
    直接用 ALTER TABLE 添加，保留全部存量数据。
    """
    cols = {r["name"] for r in conn.execute("PRAGMA table_info(users)").fetchall()}
    if "username" not in cols:
        conn.execute("ALTER TABLE users ADD COLUMN username TEXT")
    if "password_hash" not in cols:
        conn.execute("ALTER TABLE users ADD COLUMN password_hash TEXT")
    conn.execute(
        "CREATE UNIQUE INDEX IF NOT EXISTS idx_users_username ON users(username) "
        "WHERE username IS NOT NULL"
    )


def _migrate_progress_tiers(conn: sqlite3.Connection) -> None:
    """v4：progress 增加 tier 维度，主键由三元组扩为四元组。

    SQLite 不能改主键，只能重建表；存量记录一律落到 basic 档，数据不丢。
    幂等：已经是 v4 结构时直接跳过。
    """
    cols = {r["name"] for r in conn.execute("PRAGMA table_info(progress)").fetchall()}
    if "tier" in cols:
        return
    conn.executescript("""
    CREATE TABLE IF NOT EXISTS progress_v4 (
        user_id TEXT NOT NULL,
        topic_id TEXT NOT NULL,
        section_id TEXT NOT NULL,
        tier TEXT NOT NULL DEFAULT 'basic',
        status TEXT NOT NULL DEFAULT 'open',
        best_score INTEGER NOT NULL DEFAULT 0,
        attempts INTEGER NOT NULL DEFAULT 0,
        awarded INTEGER NOT NULL DEFAULT 0,
        updated_at TEXT NOT NULL,
        PRIMARY KEY (user_id, topic_id, section_id, tier)
    );
    INSERT OR IGNORE INTO progress_v4
        (user_id, topic_id, section_id, tier, status, best_score, attempts, awarded, updated_at)
        SELECT user_id, topic_id, section_id, 'basic', status, best_score, attempts, awarded, updated_at
        FROM progress;
    DROP TABLE progress;
    ALTER TABLE progress_v4 RENAME TO progress;
    """)


def _migrate_achievements_gift(conn: sqlite3.Connection) -> None:
    """v4：成就卡增加 source（来源）与赠予字段。"""
    cols = {r["name"] for r in conn.execute("PRAGMA table_info(achievements)").fetchall()}
    if "source" not in cols:
        conn.execute("ALTER TABLE achievements ADD COLUMN source TEXT NOT NULL DEFAULT 'redeem'")
    if "gifted_from" not in cols:
        conn.execute("ALTER TABLE achievements ADD COLUMN gifted_from TEXT")
    if "gifted_at" not in cols:
        conn.execute("ALTER TABLE achievements ADD COLUMN gifted_at TEXT")


def init_db() -> None:
    conn = connect()
    try:
        conn.executescript(SCHEMA)
        row = conn.execute("SELECT version FROM schema_version WHERE id = 1").fetchone()
        current = int(row["version"]) if row else 1  # 有表但无版本行 = v1 旧库
        if current < 2:
            _migrate_events(conn)
        if current < 3:
            _migrate_users_credentials(conn)
        # 迁移函数自身按「列是否存在」判断，幂等；
        # 不依赖版本号比较，避免两个迁移撞同一个版本号时被跳过。
        _migrate_achievements_gift(conn)
        _migrate_progress_tiers(conn)
        conn.execute(
            "INSERT INTO schema_version(id, version) VALUES (1, ?) "
            "ON CONFLICT(id) DO UPDATE SET version = excluded.version",
            (SCHEMA_VERSION,),
        )
    finally:
        conn.close()
