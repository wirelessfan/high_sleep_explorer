"""会话相关：建号、同步码、我的信息、鉴权依赖。"""
from __future__ import annotations

import sqlite3
from datetime import datetime

from fastapi import APIRouter, Depends, Header, HTTPException, Request
from pydantic import BaseModel, Field

from app import auth, db
from app.services import ratelimit

router = APIRouter(tags=["session"])


class AdoptIn(BaseModel):
    sync_code: str = Field(min_length=4, max_length=24)


class NicknameIn(BaseModel):
    nickname: str = Field(min_length=1, max_length=20)


class LoginIn(BaseModel):
    username: str = Field(min_length=1, max_length=32)
    password: str = Field(min_length=1, max_length=128)


class PasswordIn(BaseModel):
    old_password: str = Field(min_length=1, max_length=128)
    new_password: str = Field(min_length=6, max_length=128)


def _now() -> str:
    return datetime.now().isoformat(timespec="seconds")


def current_user(authorization: str | None = Header(default=None)) -> sqlite3.Row:
    """Bearer token → user 行。"""
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="缺少身份令牌")
    token = authorization[7:].strip()
    if not token:
        raise HTTPException(status_code=401, detail="身份令牌为空")

    with db.ro() as conn:
        row = conn.execute(
            "SELECT * FROM users WHERE token_hash = ?", (auth.hash_token(token),)
        ).fetchone()
    if not row:
        raise HTTPException(status_code=401, detail="身份令牌无效")
    return row


def _user_payload(row: sqlite3.Row, token: str | None = None) -> dict:
    keys = row.keys()
    data = {
        "id": row["id"],
        "nickname": row["nickname"],
        "username": row["username"] if "username" in keys else None,
        "has_password": bool(row["password_hash"]) if "password_hash" in keys else False,
        "points": row["points"],
        "streak": row["streak"],
        "tickets": row["tickets"],
        "shards": row["shards"],
        "last_checkin": row["last_checkin"],
        "sync_code": auth.format_sync_code(row["sync_code"]),
        "pity_sr": row["pity_sr"],
        "pity_ssr": row["pity_ssr"],
    }
    if token:
        data["token"] = token
    return data


@router.post("/session")
def create_session():
    """首次访问建号，返回令牌与同步码。"""
    token = auth.new_token()
    user_id = auth.new_id()
    sync_code = auth.normalize_sync_code(auth.new_sync_code())
    now = _now()

    with db.tx() as conn:
        for _ in range(5):
            exists = conn.execute(
                "SELECT 1 FROM users WHERE sync_code = ?", (sync_code,)
            ).fetchone()
            if not exists:
                break
            sync_code = auth.normalize_sync_code(auth.new_sync_code())
        conn.execute(
            "INSERT INTO users(id, token_hash, sync_code, created_at, last_seen) "
            "VALUES (?,?,?,?,?)",
            (user_id, auth.hash_token(token), sync_code, now, now),
        )
        row = conn.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()

    return _user_payload(row, token=token)


@router.post("/session/login")
def login(body: LoginIn, request: Request):
    """账号 + 密码登录。"""
    if not ratelimit.allow(f"login:{ratelimit.client_ip(request)}", limit=10, window_seconds=600):
        raise HTTPException(status_code=429, detail="登录尝试过多，请稍后再试")

    username = auth.normalize_username(body.username)
    with db.tx() as conn:
        row = conn.execute("SELECT * FROM users WHERE username = ?", (username,)).fetchone()
        if not row or not auth.verify_password(body.password, row["password_hash"]):
            # 不区分「账号不存在」和「密码错误」，避免枚举账号
            raise HTTPException(status_code=401, detail="账号或密码不正确")

        token = auth.new_token()
        conn.execute(
            "UPDATE users SET token_hash = ?, last_seen = ? WHERE id = ?",
            (auth.hash_token(token), _now(), row["id"]),
        )
        row = conn.execute("SELECT * FROM users WHERE id = ?", (row["id"],)).fetchone()

    return _user_payload(row, token=token)


@router.get("/session/users")
def list_public_users():
    """登录页展示已有账号名（不含任何敏感信息）。"""
    with db.ro() as conn:
        rows = conn.execute(
            "SELECT nickname, username FROM users WHERE username IS NOT NULL ORDER BY username"
        ).fetchall()
    return {"users": [{"username": r["username"], "nickname": r["nickname"]} for r in rows]}


@router.post("/session/password")
def change_password(body: PasswordIn, user: sqlite3.Row = Depends(current_user)):
    """修改自己的密码，需验证旧密码。"""
    with db.tx() as conn:
        row = conn.execute("SELECT * FROM users WHERE id = ?", (user["id"],)).fetchone()
        if row["password_hash"] and not auth.verify_password(body.old_password, row["password_hash"]):
            raise HTTPException(status_code=400, detail="原密码不正确")
        if auth.verify_password(body.new_password, row["password_hash"]):
            raise HTTPException(status_code=400, detail="新密码不能与原密码相同")

        conn.execute(
            "UPDATE users SET password_hash = ? WHERE id = ?",
            (auth.hash_password(body.new_password), user["id"]),
        )
    return {"ok": True}


@router.post("/session/adopt")
def adopt_session(body: AdoptIn, request: Request):
    """用同步码把当前设备切换到该账号，签发新令牌。"""
    # 计划 §8：同一 IP 10 分钟内最多 5 次，防止把同步码当口令爆破。
    if not ratelimit.allow(f"adopt:{ratelimit.client_ip(request)}", limit=5, window_seconds=600):
        raise HTTPException(status_code=429, detail="尝试过于频繁，请 10 分钟后再试")

    code = auth.normalize_sync_code(body.sync_code)
    if len(code) != 12:
        raise HTTPException(status_code=400, detail="同步码应为 12 位")

    with db.tx() as conn:
        row = conn.execute("SELECT * FROM users WHERE sync_code = ?", (code,)).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="同步码不存在")

        token = auth.new_token()
        conn.execute(
            "UPDATE users SET token_hash = ?, last_seen = ? WHERE id = ?",
            (auth.hash_token(token), _now(), row["id"]),
        )
        row = conn.execute("SELECT * FROM users WHERE id = ?", (row["id"],)).fetchone()

    return _user_payload(row, token=token)


@router.post("/session/rotate-code")
def rotate_code(user: sqlite3.Row = Depends(current_user)):
    """重置同步码，旧码立即失效。"""
    with db.tx() as conn:
        for _ in range(5):
            code = auth.normalize_sync_code(auth.new_sync_code())
            exists = conn.execute("SELECT 1 FROM users WHERE sync_code = ?", (code,)).fetchone()
            if not exists:
                break
        conn.execute("UPDATE users SET sync_code = ? WHERE id = ?", (code, user["id"]))

    return {"sync_code": auth.format_sync_code(code)}


@router.get("/me")
def me(user: sqlite3.Row = Depends(current_user)):
    with db.ro() as conn:
        cards = conn.execute(
            "SELECT COUNT(*) AS n FROM card_owned WHERE user_id = ?", (user["id"],)
        ).fetchone()["n"]
        done = conn.execute(
            "SELECT COUNT(*) AS n FROM progress WHERE user_id = ? AND status = 'done'",
            (user["id"],),
        ).fetchone()["n"]
    data = _user_payload(user)
    data["stats"] = {"cards": cards, "sections_done": done}
    return data


@router.patch("/me")
def update_me(body: NicknameIn, user: sqlite3.Row = Depends(current_user)):
    with db.tx() as conn:
        conn.execute("UPDATE users SET nickname = ? WHERE id = ?", (body.nickname.strip(), user["id"]))
        row = conn.execute("SELECT * FROM users WHERE id = ?", (user["id"],)).fetchone()
    return _user_payload(row)
