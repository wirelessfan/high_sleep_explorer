"""创建/重置家庭账号：dad、mom、sunny。

用法（在服务器上执行，或本地指定 LEARN_DB）：

    python tools/seed_users.py
    python tools/seed_users.py --password <初始密码>
    python tools/seed_users.py --password <新密码> --reset-password

默认只初始化缺失的家庭账号；重置已有密码需显式 --reset-password。
"""

import argparse
import sqlite3
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from app import auth  # noqa: E402
from app import db as dbmod  # noqa: E402
from app.services import blindbox  # noqa: E402

ACCOUNTS = [
    ("sunny", "sunny", "sunny"),
    ("dad", "dad", "爸爸"),
    ("mom", "mom", "妈妈"),
]


def upsert_user(conn: sqlite3.Connection, username: str, password: str, nickname: str, *, reset_password=False) -> tuple[str, str]:
    """返回 (user_id, 动作说明)。"""
    existing = conn.execute(
        "SELECT * FROM users WHERE username = ?", (username,)
    ).fetchone()

    if existing and not reset_password:
        return existing['id'], '已存在，保留密码、会话和数据'
    if not password or len(password)<8:
        raise ValueError('创建或重置家庭账号时请指定至少8位的密码')
    pwd_hash = auth.hash_password(password)

    if existing:
        conn.execute("DELETE FROM sessions WHERE user_id=?", (existing["id"],))
        conn.execute(
            "UPDATE users SET password_hash = ?, nickname = ? WHERE id = ?",
            (pwd_hash, nickname, existing["id"]),
        )
        if username.lower() == "dad":
            # 管理员 = 爸爸：对已有账号幂等提升，重置密码不清 role
            conn.execute(
                "UPDATE users SET role='admin' WHERE id=? AND (role IS NULL OR role='')",
                (existing["id"],),
            )
        return existing["id"], "已存在，重置密码"

    uid = auth.new_id()
    token = auth.new_token()
    code = auth.normalize_sync_code(auth.new_sync_code())
    now = datetime.now().isoformat(timespec="seconds")
    points = 0
    tickets = 0

    for _ in range(5):
        clash = conn.execute("SELECT 1 FROM users WHERE sync_code = ?", (code,)).fetchone()
        if not clash:
            break
        code = auth.normalize_sync_code(auth.new_sync_code())

    conn.execute(
        "INSERT INTO users(id, token_hash, sync_code, nickname, username, password_hash, "
        "points, tickets, role, created_at, last_seen) VALUES (?,?,?,?,?,?,?,?,?,?,?)",
        (uid, auth.hash_token(token), code, nickname, username,
         pwd_hash, points, tickets,
         "admin" if username.lower() == "dad" else None, now, now),
    )
    blindbox.grant_daily_tickets(conn, uid, initial=True)
    return uid, "已创建"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--password", default=None, help="创建缺失账号的初始密码，至少8位")
    ap.add_argument("--reset-password", action='store_true', help="显式重置已有家庭账号密码并撤销会话")
    args = ap.parse_args()

    dbmod.init_db()
    with dbmod.tx() as conn:
        ids = {}
        for username, nickname, display in ACCOUNTS:
            uid, action = upsert_user(conn, username, args.password, display, reset_password=args.reset_password)
            ids[username] = uid
            print(f"  {username:6s} {display:4s}  {action}  id={uid}")

    print('\n完成。未修改学习数据；同学账号请通过管理页面开通。')
    return 0


if __name__ == "__main__":
    sys.exit(main())
