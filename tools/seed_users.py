"""创建/重置家庭账号：dad、mom、sunny。

用法（在服务器上执行，或本地指定 LEARN_DB）：

    python tools/seed_users.py
    python tools/seed_users.py --password 123456
    python tools/seed_users.py --claim-progress u_5NhEuKbHeerohMD4   # 把某匿名账号的进度归给 sunny

幂等：账号已存在则只重置密码，不新建、不清进度。
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

ACCOUNTS = [
    ("sunny", "sunny", "sunny"),
    ("dad", "dad", "爸爸"),
    ("mom", "mom", "妈妈"),
    ("guest", "guest", "演示访客"),
]


def upsert_user(conn: sqlite3.Connection, username: str, password: str, nickname: str) -> tuple[str, str]:
    """返回 (user_id, 动作说明)。"""
    existing = conn.execute(
        "SELECT * FROM users WHERE username = ?", (username,)
    ).fetchone()

    is_guest = username.lower() == "guest"
    pwd_hash = "" if is_guest else auth.hash_password(password)

    if existing:
        conn.execute(
            "UPDATE users SET password_hash = ?, nickname = ? WHERE id = ?",
            (pwd_hash, nickname, existing["id"]),
        )
        return existing["id"], "已存在，更新演示信息" if is_guest else "已存在，重置密码"

    uid = "u_guest_demo" if is_guest else auth.new_id()
    token = auth.new_token()
    code = "GUEST-DEMO-01" if is_guest else auth.normalize_sync_code(auth.new_sync_code())
    now = datetime.now().isoformat(timespec="seconds")
    points = 300 if is_guest else 0
    tickets = 8 if is_guest else 0

    for _ in range(5):
        clash = conn.execute("SELECT 1 FROM users WHERE sync_code = ?", (code,)).fetchone()
        if not clash:
            break
        code = auth.normalize_sync_code(auth.new_sync_code())

    conn.execute(
        "INSERT INTO users(id, token_hash, sync_code, nickname, username, password_hash, "
        "points, tickets, created_at, last_seen) VALUES (?,?,?,?,?,?,?,?,?,?)",
        (uid, auth.hash_token(token), code, nickname, username,
         pwd_hash, points, tickets, now, now),
    )
    return uid, "已创建演示账号" if is_guest else "已创建"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--password", default="123456", help="统一初始密码")
    ap.add_argument("--claim-progress", default="", help="把该 user_id 的进度并入 sunny")
    args = ap.parse_args()

    dbmod.init_db()
    with dbmod.tx() as conn:
        ids = {}
        for username, nickname, display in ACCOUNTS:
            uid, action = upsert_user(conn, username, args.password, display)
            ids[username] = uid
            print(f"  {username:6s} {display:4s}  {action}  id={uid}")

        if args.claim_progress:
            src = args.claim_progress.strip()
            dst = ids["sunny"]
            if src == dst:
                print("  进度已在 sunny 名下，跳过归并")
            else:
                # progress 主键 (user_id, topic_id, section_id)，直接搬会被冲突挡，
                # 用 INSERT OR IGNORE 保留两侧较优记录
                moved = conn.execute(
                    "INSERT OR IGNORE INTO progress(user_id, topic_id, section_id, status, "
                    "best_score, attempts, awarded, updated_at) "
                    "SELECT ?, topic_id, section_id, status, best_score, attempts, awarded, updated_at "
                    "FROM progress WHERE user_id = ?",
                    (dst, src),
                ).rowcount
                conn.execute(
                    "UPDATE progress SET status='done', best_score=MAX(best_score, 0) "
                    "WHERE user_id=? AND awarded=1", (dst,),
                )
                print(f"  归并进度：{moved} 条 {src} -> sunny")

    print("\n完成。三个账号均可登录，初始密码：", args.password)
    return 0


if __name__ == "__main__":
    sys.exit(main())
