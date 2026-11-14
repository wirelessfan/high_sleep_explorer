"""许愿墙接口：公开浏览 + 提交意见（带盲盒券奖励）。"""
from __future__ import annotations

import sqlite3

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from app import db
from app.routers.session import current_user
from app.services import wishes

router = APIRouter(tags=["wishes"])


class WishIn(BaseModel):
    content: str = Field(min_length=1, max_length=600)


@router.get("/wishes")
def get_wall(user: sqlite3.Row = Depends(current_user)):
    with db.ro() as conn:
        return wishes.wall(conn, user["id"])


@router.post("/wishes")
def post_wish(body: WishIn, user: sqlite3.Row = Depends(current_user)):
    with db.tx() as conn:
        try:
            res = wishes.submit(conn, user, body.content)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc))
        data = wishes.wall(conn, user["id"])
        snap = conn.execute(
            "SELECT blindbox_tickets FROM users WHERE id=?", (user["id"],)
        ).fetchone()
    return {
        **res,
        "blindbox_tickets": snap["blindbox_tickets"],
        "left_today": data["left_today"],
        "items": data["items"],
    }