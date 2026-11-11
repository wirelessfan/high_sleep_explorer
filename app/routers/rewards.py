"""签到与积分。"""
from __future__ import annotations

import sqlite3
from datetime import date, timedelta

from fastapi import APIRouter, Depends, HTTPException

from app import db
from app.routers.session import current_user
from app.services import scoring

router = APIRouter(tags=["rewards"])


@router.get("/checkin")
def checkin_status(user: sqlite3.Row = Depends(current_user)):
    today = date.today()
    month_start = today.replace(day=1)
    with db.ro() as conn:
        rows = conn.execute(
            "SELECT day, points, makeup FROM checkins WHERE user_id=? AND day >= ? ORDER BY day",
            (user["id"], month_start.isoformat()),
        ).fetchall()

    checked = {r["day"] for r in rows}
    days = []
    d = month_start
    while d.month == today.month:
        key = d.isoformat()
        days.append({
            "day": key,
            "checked": key in checked,
            "is_today": key == today.isoformat(),
            "future": d > today,
        })
        d += timedelta(days=1)

    return {
        "today": today.isoformat(),
        "checked_today": today.isoformat() in checked,
        "streak": user["streak"],
        "points": user["points"],
        "days": days,
    }


@router.post("/checkin")
def do_checkin(user: sqlite3.Row = Depends(current_user)):
    with db.tx() as conn:
        fresh = conn.execute("SELECT * FROM users WHERE id=?", (user["id"],)).fetchone()
        result = scoring.checkin(conn, fresh)
    return result
