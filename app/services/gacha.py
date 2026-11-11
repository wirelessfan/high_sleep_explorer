"""抽卡：概率、保底、重复转碎片、碎片兑换。"""
from __future__ import annotations

import random
import sqlite3
import uuid
from datetime import datetime

from app import content_loader
from app.services import events

RARITY_ORDER = ["N", "R", "SR", "SSR"]


def _pools() -> dict[str, list[dict]]:
    pools: dict[str, list[dict]] = {r: [] for r in RARITY_ORDER}
    for card in content_loader.cards()["cards"]:
        pools.setdefault(card["rarity"], []).append(card)
    return pools


def _cfg() -> dict:
    return content_loader.rewards()["gacha"]


def _roll_rarity(pity_sr: int, pity_ssr: int) -> str:
    cfg = _cfg()
    if pity_ssr + 1 >= cfg["pity_ssr"]:
        return "SSR"
    if pity_sr + 1 >= cfg["pity_sr"]:
        # 保底只保 SR 及以上，按 SSR/SR 的相对概率分布挑
        r = random.random()
        ssr_share = cfg["rarity"]["SSR"] / (cfg["rarity"]["SSR"] + cfg["rarity"]["SR"])
        return "SSR" if r < ssr_share else "SR"
    total = sum(cfg["rarity"].values())
    roll = random.uniform(0, total)
    acc = 0.0
    for rarity in ("SSR", "SR", "R", "N"):
        acc += cfg["rarity"][rarity]
        if roll <= acc:
            return rarity
    return "N"


def draw(conn: sqlite3.Connection, user: sqlite3.Row, count: int,
         idempotency_key: str) -> dict:
    """抽卡主流程。"""
    cfg = _cfg()
    user_id = user["id"]

    # service 层自保：路由层已用 Pydantic 限定 1..10，内部调用同样不能绕过。
    # 负数 count 会让 cost 为负、tickets 不减反增。
    if not isinstance(count, int) or isinstance(count, bool) or not 1 <= count <= 10:
        raise ValueError("抽卡次数必须为 1–10")

    # 幂等：同 key 直接返回上次结果
    if idempotency_key:
        prev = events.find(conn, user_id, f"draw:{idempotency_key}", "draw")
        if prev:
            import json as _json
            return {"replayed": True, **_json.loads(prev["payload"])}

    # 计划 §6.3：单用户 1 秒内二次抽卡直接拒绝（重放请求已在上面返回，不受影响）。
    last = conn.execute(
        "SELECT created_at FROM events WHERE user_id=? AND kind='draw' ORDER BY id DESC LIMIT 1",
        (user_id,),
    ).fetchone()
    if last:
        try:
            elapsed = (datetime.now() - datetime.fromisoformat(last["created_at"])).total_seconds()
        except (TypeError, ValueError):
            elapsed = float("inf")
        if 0 <= elapsed < 1:
            raise ValueError("操作太快，请稍后再试")

    cost = cfg["ten_cost"] if count == 10 else cfg["single_cost"] * count
    if user["tickets"] < cost:
        raise ValueError(f"卡包不足，需要 {cost} 个，当前 {user['tickets']} 个")

    pools = _pools()
    all_cards = content_loader.cards()["cards"]
    pity_sr = user["pity_sr"]
    pity_ssr = user["pity_ssr"]
    results = []
    new_cards = []
    shards_gained = 0
    drawn_in_batch: set[str] = set()

    for _ in range(count):
        rarity = _roll_rarity(pity_sr, pity_ssr)
        if rarity == "SSR":
            pity_sr, pity_ssr = 0, 0
        elif rarity == "SR":
            pity_sr, pity_ssr = 0, pity_ssr + 1
        else:
            pity_sr, pity_ssr = pity_sr + 1, pity_ssr + 1

        pool = pools[rarity] or pools["N"]
        # 在同一稀有度内避免本次连抽重复；稀有度本身完全由概率决定，
        # 绝不能为了去重而跨稀有度换卡，否则会破坏保底与概率分布。
        fresh = [c for c in pool if c["id"] not in drawn_in_batch]
        card = random.choice(fresh or pool)
        drawn_in_batch.add(card["id"])
        draw_id = "d_" + uuid.uuid4().hex[:12]

        owned = conn.execute(
            "SELECT count FROM card_owned WHERE user_id=? AND card_id=?",
            (user_id, card["id"]),
        ).fetchone()

        is_new = owned is None
        if is_new:
            conn.execute(
                "INSERT INTO card_owned(user_id, card_id, count, first_at) VALUES (?,?,1,?)",
                (user_id, card["id"], _now()),
            )
            new_cards.append(card["id"])
            shards = 0
        else:
            conn.execute(
                "UPDATE card_owned SET count = count + 1 WHERE user_id=? AND card_id=?",
                (user_id, card["id"]),
            )
            shards = cfg["duplicate_shards"][rarity]
            shards_gained += shards

        conn.execute(
            "INSERT INTO draws(id, user_id, card_id, rarity, is_new, created_at) VALUES (?,?,?,?,?,?)",
            (draw_id, user_id, card["id"], rarity, int(is_new), _now()),
        )
        results.append({
            "draw_id": draw_id,
            "card_id": card["id"],
            "name": card["name"],
            "rarity": rarity,
            "is_new": is_new,
            "shards": shards,
        })

    conn.execute(
        "UPDATE users SET tickets = tickets - ?, shards = shards + ?, "
        "pity_sr = ?, pity_ssr = ?, last_seen = ? WHERE id = ?",
        (cost, shards_gained, pity_sr, pity_ssr, today_str(), user_id),
    )

    payload = {
        "results": results,
        "new_cards": new_cards,
        "shards_gained": shards_gained,
        "cost": cost,
        "tickets_left": user["tickets"] - cost,
        "shards_total": user["shards"] + shards_gained,
        "pity_sr": pity_sr,
        "pity_ssr": pity_ssr,
    }

    if idempotency_key and not _log(conn, user_id, f"draw:{idempotency_key}", "draw", payload):
        # 写不进幂等记录说明并发下已有同键抽卡完成；回滚本次，避免重复扣券。
        raise ValueError("同一抽卡请求已在处理中，请重试")

    return {"replayed": False, **payload}


def craft(conn: sqlite3.Connection, user: sqlite3.Row, card_id: str) -> dict:
    """碎片兑换指定卡。"""
    cfg = _cfg()
    card = next((c for c in content_loader.cards()["cards"] if c["id"] == card_id), None)
    if not card:
        raise ValueError("卡片不存在")

    owned = conn.execute(
        "SELECT count FROM card_owned WHERE user_id=? AND card_id=?", (user["id"], card_id)
    ).fetchone()
    if owned:
        raise ValueError("已经拥有这张卡了")

    cost = cfg["craft_cost"][card["rarity"]]
    if user["shards"] < cost:
        raise ValueError(f"碎片不足，需要 {cost}，当前 {user['shards']}")

    conn.execute(
        "INSERT INTO card_owned(user_id, card_id, count, first_at) VALUES (?,?,1,?)",
        (user["id"], card_id, _now()),
    )
    conn.execute("UPDATE users SET shards = shards - ?, last_seen = ? WHERE id = ?",
                 (cost, today_str(), user["id"]))

    return {"card_id": card_id, "name": card["name"], "rarity": card["rarity"],
            "cost": cost, "shards_left": user["shards"] - cost}


def owned_map(conn: sqlite3.Connection, user_id: str) -> dict[str, int]:
    rows = conn.execute("SELECT card_id, count FROM card_owned WHERE user_id=?", (user_id,)).fetchall()
    return {r["card_id"]: r["count"] for r in rows}


def set_progress(owned: dict[str, int]) -> list[dict]:
    sets = content_loader.rewards()["sets"]
    out = []
    for set_id, cfg in sets.items():
        have = [c for c in cfg["cards"] if c in owned]
        out.append({
            "id": set_id,
            "name": cfg["name"],
            "cards": cfg["cards"],
            "owned": have,
            "count": len(have),
            "total": len(cfg["cards"]),
            "done": len(have) == len(cfg["cards"]),
            "points": cfg["points"],
        })
    return out


def _now() -> str:
    return datetime.now().isoformat(timespec="seconds")


def today_str() -> str:
    return datetime.now().date().isoformat()


def _log(conn: sqlite3.Connection, user_id: str, key: str, kind: str, payload: dict) -> bool:
    """与 scoring 共用按用户隔离的幂等键。"""
    return events.log(conn, user_id, key, kind, payload)
