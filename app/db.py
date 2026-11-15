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
# v4 = progress 增加 tier（基础/进阶/高级三档难度），主键改为四元组；
#     achievements 增加 source / gifted_from / gifted_at（每日抽卡与赠予）；
# v5 = achievements 增加 redeemed_by（只有家长可核销）；
# v6 = 新增 wrong_questions 错题本。
# v7 = 多路 AI：users.role（管理员）、ai_config 策略单行表、
#     wrong_questions 增加 source / ai_solve / variants。
# v8 = 错题本 AI 并发/缓存/校验加固（与 v7 同批，兼容旧库）。
# v9 = 盲盒系统：users 增加 blindbox_tickets / bb_pity_sr / bb_pity_ssr，
#     新增 blindbox_owned 图鉴表；许愿墙新增 wishes 表。
# v10 = 每台设备独立的七天登录会话。
# v11 = 题目反馈、审核与一次性积分奖励。
# v12 = 正式账号、独立访客与历史临时记录分离。
SCHEMA_VERSION = 12

SCHEMA = """
CREATE TABLE IF NOT EXISTS sessions (
    token_hash TEXT PRIMARY KEY,
    user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    created_at REAL NOT NULL,
    expires_at REAL NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_sessions_user ON sessions(user_id);

CREATE TABLE IF NOT EXISTS schema_version (
    id INTEGER PRIMARY KEY CHECK (id = 1),
    version INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS users (
    id TEXT PRIMARY KEY,
    token_hash TEXT NOT NULL UNIQUE,
    sync_code TEXT NOT NULL UNIQUE,
    nickname TEXT NOT NULL DEFAULT '访客',
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
    blindbox_tickets INTEGER NOT NULL DEFAULT 3,  -- 盲盒券：与卡片 tickets 独立
    bb_pity_sr INTEGER NOT NULL DEFAULT 0,        -- 盲盒保底计数（独立于卡片保底）
    bb_pity_ssr INTEGER NOT NULL DEFAULT 0,
    role TEXT,                     -- NULL=普通用户；'admin'=管理员（管理界面/接口）
    account_status TEXT NOT NULL DEFAULT 'active' CHECK(account_status IN ('active','historical')),
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
    redeemed_by TEXT,              -- 核销人 user_id（只能是家长账号）
    gifted_at TEXT
);

CREATE INDEX IF NOT EXISTS idx_achv_user ON achievements(user_id, ymd);
-- 错题本：按 (user, 主题, 版块, 档位, 题目) 唯一，重复答错累加次数
CREATE TABLE IF NOT EXISTS wrong_questions (
    id TEXT PRIMARY KEY,           -- wq_<sha1(复合键)[:12]>
    user_id TEXT NOT NULL,
    topic_id TEXT NOT NULL,
    section_id TEXT NOT NULL,
    tier TEXT NOT NULL DEFAULT 'basic',
    question_id TEXT NOT NULL,
    skill TEXT,
    stem TEXT NOT NULL,            -- 答错时快照
    options_json TEXT NOT NULL,
    answer INTEGER NOT NULL,
    explain TEXT,
    picked INTEGER NOT NULL,       -- 最近一次的错误选项
    wrong_count INTEGER NOT NULL DEFAULT 1,
    status TEXT NOT NULL DEFAULT 'open',   -- open / cleared
    source TEXT NOT NULL DEFAULT 'practice',  -- practice=练习判分入本 / photo=拍照录入（预留）
    ai_analysis TEXT,              -- AI 生成 JSON：{misconception, analysis, suggestions}
    ai_model TEXT,
    ai_at TEXT,
    ai_solve TEXT,                 -- AI 独立解题缓存 JSON：{answer, steps, key_point, channel, model}
    variants TEXT,                 -- AI 举一反三缓存 JSON：{variants:[{stem, options, answer, explain}]}
    created_at TEXT NOT NULL,
    last_wrong_at TEXT NOT NULL,
    cleared_at TEXT
);

CREATE INDEX IF NOT EXISTS idx_wq_user ON wrong_questions(user_id, topic_id, status);

-- AI 策略单行表：任务路由 / 通道开关与模型覆盖 / 每任务限额。
-- API Key 永不入库（只存环境变量），这里只存非敏感的策略面。
CREATE TABLE IF NOT EXISTS ai_config (
    id INTEGER PRIMARY KEY CHECK (id = 1),
    config TEXT NOT NULL,          -- JSON：{routing, channels, limits}
    updated_at TEXT,
    updated_by TEXT
);

-- Short-lived reservations protect daily quotas without holding a write lock over HTTP.
CREATE TABLE IF NOT EXISTS ai_requests (
    id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL,
    wq_id TEXT NOT NULL,
    task TEXT NOT NULL,
    day TEXT NOT NULL,
    expires_at REAL NOT NULL,
    UNIQUE(user_id, wq_id, task)
);

CREATE INDEX IF NOT EXISTS idx_achv_code ON achievements(code);

-- 盲盒图鉴：count=0 的行表示「曾开出过但已兑换成实物」，图鉴永久解锁。
CREATE TABLE IF NOT EXISTS blindbox_owned (
    user_id TEXT NOT NULL,
    character_id TEXT NOT NULL,
    count INTEGER NOT NULL DEFAULT 1,
    first_at TEXT NOT NULL,
    PRIMARY KEY (user_id, character_id)
);

-- 许愿墙：用户改进意见；status = open（待处理）/ planned（已采纳）/ done（已实现）
CREATE TABLE IF NOT EXISTS wishes (
    id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL,
    content TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'open',
    reply TEXT,
    reply_at TEXT,
    created_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_wishes_time ON wishes(created_at);
CREATE INDEX IF NOT EXISTS idx_wishes_user ON wishes(user_id, created_at);

-- 题目问题反馈：快照版本去重，审核与积分在同一事务提交。
CREATE TABLE IF NOT EXISTS question_feedback (
    id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL REFERENCES users(id),
    topic_id TEXT NOT NULL,
    section_id TEXT NOT NULL,
    tier TEXT NOT NULL,
    question_id TEXT NOT NULL,
    question_version TEXT NOT NULL,
    snapshot_json TEXT NOT NULL,
    category TEXT NOT NULL,
    detail TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'pending' CHECK(status IN ('pending','approved','rejected')),
    reward_points INTEGER NOT NULL DEFAULT 0 CHECK(reward_points IN (0,50)),
    review_note TEXT,
    reviewed_by TEXT,
    reviewed_at TEXT,
    created_at TEXT NOT NULL,
    UNIQUE(user_id,topic_id,section_id,tier,question_id,question_version)
);
CREATE INDEX IF NOT EXISTS idx_feedback_status ON question_feedback(status,created_at);
CREATE INDEX IF NOT EXISTS idx_feedback_user ON question_feedback(user_id,created_at);

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
    if "redeemed_by" not in cols:
        conn.execute("ALTER TABLE achievements ADD COLUMN redeemed_by TEXT")


def _migrate_ai_admin(conn: sqlite3.Connection) -> None:
    """v7：users 增加 role（dad 即管理员），wrong_questions 增加来源与 AI 缓存列。

    ai_config 表由 SCHEMA 的 CREATE TABLE IF NOT EXISTS 兜底，
    这里只处理老库的 ALTER TABLE；按列探测，幂等，重复执行安全。
    """
    user_cols = {r["name"] for r in conn.execute("PRAGMA table_info(users)").fetchall()}
    if "role" not in user_cols:
        conn.execute("ALTER TABLE users ADD COLUMN role TEXT")
    # 管理员 = 爸爸：对已有账号幂等提升（新装库走 seed_users.py 同样会提升）
    conn.execute(
        "UPDATE users SET role='admin' WHERE LOWER(username)='dad' "
        "AND (role IS NULL OR role='')"
    )

    wq_cols = {r["name"] for r in conn.execute("PRAGMA table_info(wrong_questions)").fetchall()}
    if "source" not in wq_cols:
        conn.execute(
            "ALTER TABLE wrong_questions ADD COLUMN source TEXT NOT NULL DEFAULT 'practice'"
        )
    if "ai_solve" not in wq_cols:
        conn.execute("ALTER TABLE wrong_questions ADD COLUMN ai_solve TEXT")
    if "variants" not in wq_cols:
        conn.execute("ALTER TABLE wrong_questions ADD COLUMN variants TEXT")


def _migrate_blindbox(conn: sqlite3.Connection) -> None:
    """v9：users 增加盲盒字段；blindbox_owned / wishes 由 SCHEMA 兜底建表。

    老用户补 3 张体验券（列不存在时才 ALTER，ALTER 后默认值即生效）。
    """
    cols = {r["name"] for r in conn.execute("PRAGMA table_info(users)").fetchall()}
    if "blindbox_tickets" not in cols:
        conn.execute(
            "ALTER TABLE users ADD COLUMN blindbox_tickets INTEGER NOT NULL DEFAULT 3"
        )
    if "bb_pity_sr" not in cols:
        conn.execute("ALTER TABLE users ADD COLUMN bb_pity_sr INTEGER NOT NULL DEFAULT 0")
    if "bb_pity_ssr" not in cols:
        conn.execute("ALTER TABLE users ADD COLUMN bb_pity_ssr INTEGER NOT NULL DEFAULT 0")

    # v9.1：角色形象换成正版 Labubu 后 id 变了，把老图鉴记录迁到新 id。
    # 幂等：迁移后旧 id 不再存在，重复执行是空操作。
    remap = {
        "bubu-mint": "labubu-mint",
        "bubu-peach": "labubu-peach",
        "bubu-sky": "labubu-sky",
        "bubu-lemon": "labubu-lemon",
        "bubu-lilac": "labubu-lilac",
        "bubu-coral": "labubu-rose",
        "bubu-galaxy": "labubu-rose",
        "bubu-aurora": "labubu-aurora",
    }
    for old_id, new_id in remap.items():
        rows = conn.execute(
            "SELECT user_id, count, first_at FROM blindbox_owned WHERE character_id=?",
            (old_id,),
        ).fetchall()
        for r in rows:
            # 目标已存在时累加副本数，保留更早的获取时间
            conn.execute(
                "INSERT INTO blindbox_owned(user_id, character_id, count, first_at) "
                "VALUES (?,?,?,?) "
                "ON CONFLICT(user_id, character_id) DO UPDATE SET "
                "count = count + excluded.count, "
                "first_at = MIN(first_at, excluded.first_at)",
                (r["user_id"], new_id, r["count"], r["first_at"]),
            )
            conn.execute(
                "DELETE FROM blindbox_owned WHERE user_id=? AND character_id=?",
                (r["user_id"], old_id),
            )


def _migrate_account_categories(conn: sqlite3.Connection, current: int) -> None:
    cols = {r['name'] for r in conn.execute('PRAGMA table_info(users)')}
    if 'account_status' not in cols:
        conn.execute("ALTER TABLE users ADD COLUMN account_status TEXT NOT NULL DEFAULT 'active' CHECK(account_status IN ('active','historical'))")
    if current < 12:
        # 昵称不能证明账号归属。保留原ID、余额、进度与会话，仅标记历史匿名数据。
        conn.execute("UPDATE users SET account_status='historical' WHERE username IS NULL OR trim(username)=''")
    conn.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_users_username_normalized ON users(lower(trim(username))) WHERE username IS NOT NULL AND trim(username)<>''")


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
        _migrate_ai_admin(conn)
        _migrate_blindbox(conn)
        _migrate_account_categories(conn, current)
        if current < 10:
            # Existing browsers retain their current token for one bounded grace
            # period; repeated application restarts must not extend the deadline.
            import time
            now = time.time()
            conn.execute(
                "INSERT OR IGNORE INTO sessions(token_hash,user_id,created_at,expires_at) "
                "SELECT token_hash,id,?,? FROM users", (now, now + 7 * 24 * 60 * 60)
            )
        conn.execute(
            "INSERT INTO schema_version(id, version) VALUES (1, ?) "
            "ON CONFLICT(id) DO UPDATE SET version = excluded.version",
            (SCHEMA_VERSION,),
        )
    finally:
        conn.close()
