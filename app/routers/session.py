"""会话相关：建号、同步码、我的信息、鉴权依赖。"""
from __future__ import annotations

import sqlite3
import time
from datetime import datetime
from typing import Literal

from fastapi import APIRouter, Depends, Header, HTTPException, Request
from pydantic import BaseModel, Field

from app import auth, db
from app.services import accounts, blindbox, ratelimit

router = APIRouter(tags=["session"])
SESSION_SECONDS = 7 * 24 * 60 * 60


def _issue_session(conn: sqlite3.Connection, user_id: str, token: str) -> None:
    now = time.time()
    conn.execute("DELETE FROM sessions WHERE expires_at <= ?", (now,))
    conn.execute(
        "INSERT INTO sessions(token_hash,user_id,created_at,expires_at) VALUES(?,?,?,?)",
        (auth.hash_token(token), user_id, now, now + SESSION_SECONDS),
    )


def _session_user(conn, token: str):
    return conn.execute(
        "SELECT users.*, sessions.expires_at AS session_expires_at FROM sessions "
        "JOIN users ON users.id=sessions.user_id "
        "WHERE sessions.token_hash=? AND sessions.expires_at>?",
        (auth.hash_token(token), time.time()),
    ).fetchone()


class AdoptIn(BaseModel):
    sync_code: str = Field(min_length=4, max_length=24)


class NicknameIn(BaseModel):
    nickname: str = Field(min_length=1, max_length=20)


class LoginIn(BaseModel):
    username: str = Field(min_length=1, max_length=32)
    password: str = Field(min_length=1, max_length=128)
    account_type: Literal['dad','mom','sunny','student'] | None = None


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
        row = _session_user(conn, token)
    if not row:
        raise HTTPException(status_code=401, detail="登录已失效，请重新登录（登录状态保留 7 天）")
    return row


def require_admin(user: sqlite3.Row = Depends(current_user)) -> sqlite3.Row:
    """管理员守卫：非管理员一律 403（管理接口与管理界面专用）。"""
    role = user["role"] if "role" in user.keys() else None
    if role != "admin":
        raise HTTPException(status_code=403, detail="需要管理员身份")
    return user


def _user_payload(row: sqlite3.Row, token: str | None = None) -> dict:
    keys = row.keys()
    username = row["username"] if "username" in keys else None
    account_type = accounts.kind(row)
    is_guest = account_type == 'guest'
    data = {
        "id": row["id"],
        "nickname": row["nickname"],
        "username": username,
        "is_guest": is_guest,
        "account_type": account_type,
        "account_label": dict(accounts.CATEGORIES)[account_type],
        "is_historical": accounts.historical(row),
        "is_admin": bool(row["role"] == "admin" if "role" in keys else False),
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
    if "session_expires_at" in keys:
        data["session_expires_at"] = row["session_expires_at"]
    return data


def _create_visitor(*, demo=False):
    """访客按访问者隔离；临时记录永不冒充 Sunny 或正式同学。"""
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
            "INSERT INTO users(id, token_hash, sync_code, nickname, points, tickets, created_at, last_seen) "
            "VALUES (?,?,?,?,?,?,?,?)",
            (user_id, auth.hash_token(token), sync_code, '访客', 260 if demo else 0, 6 if demo else 0, now, now),
        )
        blindbox.grant_daily_tickets(conn, user_id, initial=True)
        _issue_session(conn, user_id, token)
        row = _session_user(conn, token)

    return _user_payload(row, token=token)


@router.post("/session")
def create_session(request: Request):
    """兼容旧客户端的临时会话入口；新访客不进入正式账号列表。"""
    if not ratelimit.allow(f"visitor:{ratelimit.client_ip(request)}",limit=30,window_seconds=60):
        raise HTTPException(status_code=429,detail='请求过于频繁，请稍后再试')
    return _create_visitor()


@router.post("/session/login")
def login(body: LoginIn, request: Request):
    """账号 + 密码登录。"""
    if not ratelimit.allow(f"login:{ratelimit.client_ip(request)}", limit=10, window_seconds=600):
        raise HTTPException(status_code=429, detail="登录尝试过多，请稍后再试")

    username = auth.normalize_username(body.username)
    with db.tx() as conn:
        row = conn.execute("SELECT * FROM users WHERE username = ?", (username,)).fetchone()
        if (not row or accounts.historical(row) or accounts.kind(row)=='guest'
            or (body.account_type and accounts.kind(row)!=body.account_type)
            or not auth.verify_password(body.password, row["password_hash"])):
            # 不区分「账号不存在」和「密码错误」，避免枚举账号
            raise HTTPException(status_code=401, detail="账号或密码不正确")

        token = auth.new_token()
        conn.execute(
            "UPDATE users SET token_hash = ?, last_seen = ? WHERE id = ?",
            (auth.hash_token(token), _now(), row["id"]),
        )
        _issue_session(conn, row["id"], token)
        row = _session_user(conn, token)

    return _user_payload(row, token=token)


@router.post("/session/guest")
def guest_session(request: Request):
    """访客免密一键体验通道（用于演示，权限受限）。"""
    if not ratelimit.allow(f"guest:{ratelimit.client_ip(request)}", limit=30, window_seconds=60):
        raise HTTPException(status_code=429, detail="请求过于频繁，请稍后再试")

    return _create_visitor(demo=True)


@router.get("/session/users")
def list_public_users():
    """只展示固定家庭入口；同学通过自己的账号密码登录，不公开同学名单。"""
    with db.ro() as conn:
        rows = conn.execute(
            "SELECT nickname, username FROM users "
            "WHERE username IN ('dad','mom','sunny') AND account_status='active' "
            "ORDER BY CASE username WHEN 'dad' THEN 0 WHEN 'mom' THEN 1 ELSE 2 END"
        ).fetchall()
    return {"users": [{"username": r["username"], "nickname": r["nickname"]} for r in rows]}


@router.post("/session/password")
def change_password(body: PasswordIn, user: sqlite3.Row = Depends(current_user),
                    authorization: str = Header()):
    """修改自己的密码，需验证旧密码（访客账号禁止修改）。"""
    if accounts.kind(user) == 'guest':
        raise HTTPException(status_code=403, detail="演示访客账号不支持修改密码")

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
        conn.execute("DELETE FROM sessions WHERE user_id=? AND token_hash<>?",
                     (user["id"], auth.hash_token(authorization[7:].strip())))
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
        _issue_session(conn, row["id"], token)
        row = _session_user(conn, token)

    return _user_payload(row, token=token)


@router.post("/session/logout")
def logout(user: sqlite3.Row = Depends(current_user), authorization: str = Header()):
    """退出仅撤销本设备的会话，其他设备保持登录。"""
    with db.tx() as conn:
        conn.execute("DELETE FROM sessions WHERE user_id=? AND token_hash=?",
                     (user["id"], auth.hash_token(authorization[7:].strip())))
    return {"ok": True}


@router.post("/session/rotate-code")
def rotate_code(user: sqlite3.Row = Depends(current_user)):
    """重置同步码，旧码立即失效（访客账号禁止操作）。"""
    if (user['username'] or '').lower() == 'guest':
        raise HTTPException(status_code=403, detail="演示访客账号不支持重置同步码")

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
