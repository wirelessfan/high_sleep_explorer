"""怪人军团图鉴：每关一只小 boss，科学家是关底大 boss。

角色表由 tools/generate_bosses.py 生成，立绘通过 /assets/bosses/ 静态提供。
这里只做只读下发，不参与判分与发奖，与既有接口完全正交。
"""
from __future__ import annotations

import sqlite3

from fastapi import APIRouter, Depends

from app import content_loader
from app.routers.session import current_user

router = APIRouter(tags=["bosses"])


@router.get("/bosses")
def list_bosses(user: sqlite3.Row = Depends(current_user)):
    """返回系列设定与全部守关者；前端可按 topic_id/section_id 自行索引。"""
    data = content_loader.bosses()
    bosses = [dict(b) for b in data["bosses"]]
    return {
        "series": data["series"],
        "total": len(bosses),
        "mini": sum(1 for b in bosses if b["tier"] == "mini"),
        "big": sum(1 for b in bosses if b["tier"] == "big"),
        "bosses": bosses,
    }
