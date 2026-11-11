"""成就卡：积分兑换、兑现码、核销。"""
from __future__ import annotations

import sqlite3

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from app import db
from app.routers.session import current_user
from app.services import achievements

router = APIRouter(tags=["achievements"])


class RedeemIn(BaseModel):
    count: int = Field(default=1, ge=1, le=10)


class VerifyIn(BaseModel):
    code: str = Field(min_length=4, max_length=40)


@router.get("/achievements")
def list_achievements(user: sqlite3.Row = Depends(current_user)):
    with db.ro() as conn:
        st = achievements.stats(conn, user["id"])
        cards = achievements.list_cards(conn, user["id"])
    return {
        "stats": st,
        "cards": cards,
        "points": user["points"],
        "can_redeem": user["points"] >= st["points_per_card"] and st["today_left"] > 0,
    }


@router.post("/achievements/redeem")
def redeem(body: RedeemIn, user: sqlite3.Row = Depends(current_user)):
    with db.tx() as conn:
        fresh = conn.execute("SELECT * FROM users WHERE id=?", (user["id"],)).fetchone()
        try:
            res = achievements.redeem_points(conn, fresh, body.count)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc))
        st = achievements.stats(conn, user["id"])
        row = conn.execute("SELECT points FROM users WHERE id=?", (user["id"],)).fetchone()

    return {**res, "stats": st, "points": row["points"]}


@router.post("/achievements/verify")
def verify(body: VerifyIn, user: sqlite3.Row = Depends(current_user)):
    """核销兑换码。线下给钱后调用，防止同一张卡被兑现两次。"""
    with db.tx() as conn:
        try:
            res = achievements.mark_redeemed(conn, body.code)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc))
    return res
