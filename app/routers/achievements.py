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


class GiftIn(BaseModel):
    card_id: str = Field(min_length=1, max_length=40)
    to_username: str = Field(default="sunny", min_length=1, max_length=32)


@router.get("/achievements")
def list_achievements(user: sqlite3.Row = Depends(current_user)):
    with db.ro() as conn:
        st = achievements.stats(conn, user["id"])
        cards = achievements.list_cards(conn, user["id"])
    own = [c for c in cards if not c.get("gifted_from")]
    gifted_in = [c for c in cards if c.get("gifted_from")]
    return {
        "stats": st,
        # 「自己赚的」与「收到的」分开，前端两处各自展示，避免同一张卡出现两次
        "cards": own,
        "gifted_cards": gifted_in,
        "username": user["username"] if "username" in user.keys() else None,
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
    """核销兑换码。只能由家长账号操作（配置见 achievement.redeem_by）。"""
    if not achievements.can_redeem(user):
        raise HTTPException(status_code=403, detail=achievements.redeem_permission_error(user))

    with db.tx() as conn:
        try:
            res = achievements.mark_redeemed(conn, body.code, user["id"])
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc))
    # 补上操作人信息，便于家长核对
    res["redeemed_by"] = user["username"]
    return res


@router.post("/achievements/redeem-code")
def redeem_by_code(body: VerifyIn, user: sqlite3.Row = Depends(current_user)):
    """家长核销并立即给出结论（与 verify 等价，语义更贴家长操作）。"""
    return verify(body, user)


@router.get("/achievements/verify-permission")
def verify_permission(user: sqlite3.Row = Depends(current_user)):
    """前端判断是否显示「核销」入口。"""
    return {
        "can_verify": achievements.can_redeem(user),
        "allowed": achievements.allowed_verifiers(),
    }


# ---------- 每日随机卡 ----------

@router.get("/achievements/daily")
def daily_info(user: sqlite3.Row = Depends(current_user)):
    """今日抽卡状态与可赠予对象。"""
    with db.ro() as conn:
        st = achievements.daily_status(conn, user["id"])
    return st


@router.post("/achievements/daily/draw")
def daily_draw(user: sqlite3.Row = Depends(current_user)):
    """每人每天一次免费随机卡。"""
    with db.tx() as conn:
        try:
            res = achievements.draw_daily(conn, user)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc))
        st = achievements.daily_status(conn, user["id"])
    return {**res, "status": st}


@router.post("/achievements/gift")
def gift(body: GiftIn, user: sqlite3.Row = Depends(current_user)):
    """把卡赠送给家人（默认 sunny）。"""
    with db.tx() as conn:
        try:
            res = achievements.gift_card(conn, user, body.card_id, body.to_username)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc))
    return res


@router.get("/achievements/received")
def received(user: sqlite3.Row = Depends(current_user)):
    """收到的赠卡。"""
    with db.ro() as conn:
        items = achievements.received_cards(conn, user["id"])
    return {"cards": items, "total": len(items)}
