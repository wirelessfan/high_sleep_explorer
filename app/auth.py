"""身份与口令：设备令牌、同步码、密码哈希。"""
from __future__ import annotations

import hashlib
import hmac
import secrets
import string

# 去掉易混淆字符 0/O/1/I/L
_SYNC_ALPHABET = "ABCDEFGHJKMNPQRSTUVWXYZ23456789"

PBKDF2_ROUNDS = 200_000


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


# ---------- 口令 ----------

def hash_password(password: str) -> str:
    """PBKDF2-HMAC-SHA256，格式 pbkdf2_sha256$轮数$盐$摘要。"""
    salt = secrets.token_bytes(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, PBKDF2_ROUNDS)
    return f"pbkdf2_sha256${PBKDF2_ROUNDS}${salt.hex()}${digest.hex()}"


def verify_password(password: str, stored: str | None) -> bool:
    """常量时间比较，避免时序侧信道。"""
    if not stored:
        return False
    try:
        algo, rounds, salt_hex, digest_hex = stored.split("$")
        if algo != "pbkdf2_sha256":
            return False
        expected = hashlib.pbkdf2_hmac(
            "sha256", password.encode("utf-8"), bytes.fromhex(salt_hex), int(rounds)
        )
        return hmac.compare_digest(expected.hex(), digest_hex)
    except (ValueError, TypeError):
        return False


def normalize_username(name: str) -> str:
    """账号统一小写、去空格。"""
    return name.strip().lower()

