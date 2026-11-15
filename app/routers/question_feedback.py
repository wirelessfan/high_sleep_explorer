"""题目反馈与管理员审核。"""
import sqlite3
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, ConfigDict, Field

from app import db
from app.routers.session import current_user, require_admin
from app.services import question_feedback as service

router = APIRouter(tags=['question-feedback'])


class FeedbackIn(BaseModel):
    model_config = ConfigDict(extra='forbid')
    topic_id: str = Field(min_length=1,max_length=100)
    section_id: str = Field(min_length=1,max_length=100)
    tier: Literal['basic','advanced','expert']
    question_id: str = Field(min_length=1,max_length=100)
    wrong_question_id: str | None = Field(default=None,max_length=100)
    category: Literal['incomplete','answer','explanation','diagram','other']
    detail: str = Field(min_length=5,max_length=1000)
    displayed_stem: str = Field(max_length=20000)
    displayed_options: list[str] = Field(min_length=2,max_length=8)


class ReviewIn(BaseModel):
    model_config = ConfigDict(extra='forbid')
    status: Literal['approved','rejected']
    note: str = Field(min_length=2,max_length=500)


@router.post('/question-feedback')
def submit(body:FeedbackIn,user:sqlite3.Row=Depends(current_user)):
    with db.tx() as conn:
        try:
            return service.submit(conn,user,body.model_dump())
        except service.FeedbackError as exc:
            raise HTTPException(status_code=exc.status,detail=str(exc))


@router.get('/question-feedback')
def mine(user:sqlite3.Row=Depends(current_user)):
    with db.ro() as conn:
        return service.list_items(conn,user['id'])


@router.get('/admin/question-feedback')
def review_list(user:sqlite3.Row=Depends(require_admin)):
    with db.ro() as conn:
        return service.list_items(conn)


@router.patch('/admin/question-feedback/{report_id}')
def review(report_id:str,body:ReviewIn,user:sqlite3.Row=Depends(require_admin)):
    with db.tx() as conn:
        try:
            return service.moderate(conn,report_id,body.status,body.note,user['id'])
        except service.FeedbackError as exc:
            raise HTTPException(status_code=exc.status,detail=str(exc))
