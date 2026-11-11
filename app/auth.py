"""匿名设备身份：判别令牌、同步码、常用工具。"""
from __future__ import annotations

import hashlib
import secrets
import string

# 去掉易混淆字符 0/O/1/I/L
_SYNC_ALPHABET = "ABCDEFGHJKMNPQRSTUVWXYZ23456789"


def new_id() -> str:
    return "u_" + secrets.token_urlsafe(12)


def new_token() -> str:
    return secrets.token_urlsafe(32)


def hash_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def new_sync_code() -> str:
    """12 位同步码，4-4-4 分组，便于手抄。"""
    chars = "".join(secrets.choice(_SYNC_ALPHABET) for _ in range(12))
    return "-".join(chars[i:i + 4] for i in range(0, 12, 4))


def normalize_sync_code(code: str) -> str:
    """忽略大小写、空格、连字符，统一成 12 位裸串。"""
    cleaned = "".join(c for c in code.upper() if c in _SYNC_ALPHABET)
    return cleaned


def format_sync_code(raw: str) -> str:
    return "-".join(raw[i:i + 4] for i in range(0, len(raw), 4))


# 用于展示的字母表（保留，方便前端提示）
SYNC_ALPHABET = string.digits + _SYNC_ALPHABET
