"""卡册：图鉴、抽卡、碎片兑换。"""
from __future__ import annotations

import sqlite3

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from app import content_loader, db
from app.routers.session import current_user
from app.services import gacha, scoring

router = APIRouter(tags=["cards"])


class DrawIn(BaseModel):
    count: int = Field(default=1, ge=1, le=10)
    # 必填：缺省会让重复提交/超时重试重复扣券（前端 album.js 已带 key）。
    idempotency_key: str = Field(min_length=1, max_length=64)


class CraftIn(BaseModel):
    card_id: str = Field(min_length=1, max_length=32)


@router.get("/cards")
def list_cards(user: sqlite3.Row = Depends(current_user)):
    all_cards = content_loader.cards()["cards"]
    with db.ro() as conn:
        owned = gacha.owned_map(conn, user["id"])

    items = []
    for c in all_cards:
        items.append({
            "id": c["id"],
            "name": c["name"],
            "en": c["en"],
            "life": c["life"],
            "subject": c["subject"],
            "rarity": c["rarity"],
            "image": f"/assets/cards/{c['image']}",
            "set": c["set"],
            "quote": c["quote"],
            "contribution": c["contribution"],
            "textbook": c["textbook"],
            "trivia": c["trivia"],
            "topic": c["topic"],
            "section": c["section"],
            "owned": c["id"] in owned,
            "count": owned.get(c["id"], 0),
        })

    cfg = content_loader.rewards()["gacha"]
    return {
        "cards": items,
        "owned_total": len(owned),
        "total": len(all_cards),
        "shards": user["shards"],
        "tickets": user["tickets"],
        "sets": gacha.set_progress(owned),
        "pity": {
            "sr_left": max(0, cfg["pity_sr"] - user["pity_sr"]),
            "ssr_left": max(0, cfg["pity_ssr"] - user["pity_ssr"]),
            "pity_sr": cfg["pity_sr"],
            "pity_ssr": cfg["pity_ssr"],
        },
        "rates": cfg["rarity"],
        "craft_cost": cfg["craft_cost"],
    }


@router.post("/cards/draw")
def draw_cards(body: DrawIn, user: sqlite3.Row = Depends(current_user)):
    with db.tx() as conn:
        fresh = conn.execute("SELECT * FROM users WHERE id=?", (user["id"],)).fetchone()
        try:
            result = gacha.draw(conn, fresh, body.count, body.idempotency_key)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc))

        # 抽到新卡后检查套装
        owned = gacha.owned_map(conn, user["id"])
        sets = gacha.set_progress(owned)
        set_awards = []
        for s in sets:
            if s["done"]:
                gained = scoring.award_set(conn, user["id"], s["id"], s["points"])
                if gained:
                    set_awards.append({"set": s["name"], "points": gained})

        row = conn.execute("SELECT * FROM users WHERE id=?", (user["id"],)).fetchone()

    result["sets"] = sets
    result["set_awards"] = set_awards
    result["points"] = row["points"]
    result["tickets"] = row["tickets"]
    result["shards"] = row["shards"]
    return result


@router.post("/cards/craft")
def craft_card(body: CraftIn, user: sqlite3.Row = Depends(current_user)):
    with db.tx() as conn:
        fresh = conn.execute("SELECT * FROM users WHERE id=?", (user["id"],)).fetchone()
        try:
            result = gacha.craft(conn, fresh, body.card_id)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc))

        owned = gacha.owned_map(conn, user["id"])
        sets = gacha.set_progress(owned)
        set_awards = []
        for s in sets:
            if s["done"]:
                gained = scoring.award_set(conn, user["id"], s["id"], s["points"])
                if gained:
                    set_awards.append({"set": s["name"], "points": gained})

        row = conn.execute("SELECT * FROM users WHERE id=?", (user["id"],)).fetchone()

    result["sets"] = sets
    result["set_awards"] = set_awards
    result["points"] = row["points"]
    return result
