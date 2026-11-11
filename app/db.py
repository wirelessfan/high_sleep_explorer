"""SQLite 访问层：连接、建表、迁移、事务。"""
from __future__ import annotations

import os
import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator

DB_PATH = Path(os.environ.get("LEARN_DB", Path(__file__).resolve().parent.parent / "data" / "app.db"))

# v1 = 初版（events.key 全局唯一）；v2 = events 改为按 (user_id, key) 唯一。
SCHEMA_VERSION = 2

SCHEMA = """
CREATE TABLE IF NOT EXISTS schema_version (
    id INTEGER PRIMARY KEY CHECK (id = 1),
    version INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS users (
    id TEXT PRIMARY KEY,
    token_hash TEXT NOT NULL UNIQUE,
    sync_code TEXT NOT NULL UNIQUE,
    nickname TEXT NOT NULL DEFAULT '同学',
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
    status TEXT NOT NULL DEFAULT 'open',
    best_score INTEGER NOT NULL DEFAULT 0,
    attempts INTEGER NOT NULL DEFAULT 0,
    awarded INTEGER NOT NULL DEFAULT 0,
    updated_at TEXT NOT NULL,
    PRIMARY KEY (user_id, topic_id, section_id)
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


def init_db() -> None:
    conn = connect()
    try:
        conn.executescript(SCHEMA)
        row = conn.execute("SELECT version FROM schema_version WHERE id = 1").fetchone()
        current = int(row["version"]) if row else 1  # 有表但无版本行 = v1 旧库
        if current < SCHEMA_VERSION:
            _migrate_events(conn)
        conn.execute(
            "INSERT INTO schema_version(id, version) VALUES (1, ?) "
            "ON CONFLICT(id) DO UPDATE SET version = excluded.version",
            (SCHEMA_VERSION,),
        )
    finally:
        conn.close()
