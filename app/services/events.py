"""事件表读写：幂等键按用户隔离，时间格式统一。

`events.key` 在库层面是唯一的，而业务键（如 ``first:physics:quick``、
``set:electromagnetic``、``draw:<client-key>``）本身不含用户标识。
直接在库里用裸业务键会导致「第一个用户领到奖励后，后面所有用户都领不到」。
所有读写都必须经过本模块的 :func:`scope`，由它统一加上 ``user_id`` 前缀。
"""
from __future__ import annotations

import json
import sqlite3
from datetime import datetime
from typing import Any

# 与 db.SCHEMA_VERSION 对应；用于提示调用方当前事件键格式。
KEY_FORMAT_VERSION = 2


def now() -> str:
    """统一的事件时间戳（秒级 ISO），替换原先 scoring 只写日期、gacha 写完整时间的两种情况。"""
    return datetime.now().isoformat(timespec="seconds")


def scope(user_id: str, raw_key: str) -> str:
    """把业务键限定在用户命名空间内。"""
    return f"{user_id}:{raw_key}"


def log(conn: sqlite3.Connection, user_id: str, raw_key: str,
        kind: str, payload: Any) -> bool:
    """写入事件并返回是否真的插入。

    返回 False 表示同一用户已处理过该键；**调用方必须据此放弃发奖**，
    不能像旧实现那样忽略返回值。
    """
    cur = conn.execute(
        "INSERT OR IGNORE INTO events(user_id, key, kind, payload, created_at) "
        "VALUES (?,?,?,?,?)",
        (
            user_id,
            scope(user_id, raw_key),
            kind,
            json.dumps(payload, ensure_ascii=False),
            now(),
        ),
    )
    return cur.rowcount == 1


def find(conn: sqlite3.Connection, user_id: str, raw_key: str,
         kind: str | None = None) -> sqlite3.Row | None:
    """按用户 + 业务键取回事件（抽卡重放用）。"""
    sql = "SELECT * FROM events WHERE user_id = ? AND key = ?"
    args: list[Any] = [user_id, scope(user_id, raw_key)]
    if kind is not None:
        sql += " AND kind = ?"
        args.append(kind)
    return conn.execute(sql, args).fetchone()
