"""盲盒接口：抽盒、积分换券、实物兑换、图鉴。"""
from __future__ import annotations

import sqlite3

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from app import db
from app.routers.session import current_user
from app.services import blindbox

router = APIRouter(tags=["blindbox"])


class DrawIn(BaseModel):
    count: int = Field(default=1, ge=1, le=10)
    idempotency_key: str = Field(min_length=1, max_length=64)


class ExchangeIn(BaseModel):
    count: int = Field(default=1, ge=1, le=5)


class RedeemIn(BaseModel):
    character_id: str = Field(min_length=1, max_length=64)


def _cfg() -> dict:
    from app import content_loader
    return content_loader.rewards()["blindbox"]


def _wall_cfg() -> dict:
    from app import content_loader
    return content_loader.rewards()["wishes"]


def _snapshot(conn: sqlite3.Connection, user: sqlite3.Row) -> dict:
    cfg = _cfg()
    daily = blindbox.grant_daily_tickets(conn, user["id"])
    row = conn.execute(
        "SELECT blindbox_tickets, bb_pity_sr, bb_pity_ssr FROM users WHERE id=?",
        (user["id"],),
    ).fetchone()
    return {
        "tickets": row["blindbox_tickets"],
        "daily": daily,
        "pity": {
            "sr_left": max(0, cfg["pity_sr"] - row["bb_pity_sr"]),
            "ssr_left": max(0, cfg["pity_ssr"] - row["bb_pity_ssr"]),
            "pity_sr": row["bb_pity_sr"],
            "pity_ssr": row["bb_pity_ssr"],
        },
        "costs": {"single": cfg["single_cost"], "ten": cfg["ten_cost"]},
        "rates": cfg["rarity"],
        "value_cny": cfg["value_cny"],
        "exchange": {
            "points": cfg.get("exchange_points", 100),
            "daily_limit": cfg.get("exchange_daily_limit", 1),
        },
        "wish_bonus": _wall_cfg().get("ticket_reward", 1),
    }


@router.get("/blindbox")
def get_blindbox(user: sqlite3.Row = Depends(current_user)):
    with db.tx() as conn:
        snap = _snapshot(conn, user)
        gallery = blindbox.gallery(conn, user["id"])
    unlocked = sum(1 for g in gallery if g["unlocked"])
    snap.update({
        "gallery": gallery,
        "unlocked": unlocked,
        "total": len(gallery),
    })
    return snap


@router.post("/blindbox/draw")
def draw(body: DrawIn, user: sqlite3.Row = Depends(current_user)):
    with db.tx() as conn:
        fresh = conn.execute("SELECT * FROM users WHERE id=?", (user["id"],)).fetchone()
        try:
            res = blindbox.draw(conn, fresh, body.count, body.idempotency_key)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc))
        snap = _snapshot(conn, fresh)
        gallery = blindbox.gallery(conn, fresh["id"])
    res.update(snap)
    res["unlocked"] = sum(1 for g in gallery if g["unlocked"])
    res["total"] = len(gallery)
    return res


@router.post("/blindbox/exchange")
def exchange(body: ExchangeIn, user: sqlite3.Row = Depends(current_user)):
    with db.tx() as conn:
        fresh = conn.execute("SELECT * FROM users WHERE id=?", (user["id"],)).fetchone()
        try:
            res = blindbox.exchange_points(conn, fresh, body.count)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc))
        res.update(_snapshot(conn, fresh))
    return res


@router.post("/blindbox/redeem")
def redeem(body: RedeemIn, user: sqlite3.Row = Depends(current_user)):
    with db.tx() as conn:
        fresh = conn.execute("SELECT * FROM users WHERE id=?", (user["id"],)).fetchone()
        try:
            res = blindbox.redeem_character(conn, fresh, body.character_id)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc))
        gallery = blindbox.gallery(conn, fresh["id"])
    res["gallery"] = gallery
    return res