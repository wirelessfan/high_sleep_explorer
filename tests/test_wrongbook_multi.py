import json
import sqlite3

import pytest

from app import db
from app.services import grading, wrongbook


def test_multi_choice_requires_exact_set_and_valid_indices():
    q = {"id": "q", "qtype": "multi_choice", "options": ["A", "B", "C"],
         "answer_indices": [0, 2]}
    assert grading.grade_quiz([q], {}, {"q": [2, 0]})["correct"] == 1
    for selected in ([0], [0, 1, 2], [0, 0], [0, 3], [True, 2], "0,2"):
        assert grading.grade_quiz([q], {}, {"q": selected})["correct"] == 0
    assert grading.grade_quiz([q], {}, {})["correct"] == 0
    assert grading.grade_quiz([{**q, "answer_indices": []}], {}, {"q": [0, 2]})["correct"] == 0


def test_fill_answer_normalization_is_limited_and_directional():
    assert wrongbook.answer_matches(" f(x) = −18/5 ", "-18/5")
    assert wrongbook.answer_matches("√3", "sqrt3")
    assert wrongbook.answer_matches("y=sqrt(3)", "√(3)")
    assert wrongbook.answer_matches("y=2*sin(2*x+pi/3)", "f(x)=2 sin(2x+π/3)")
    assert wrongbook.answer_matches("(sqrt(3)-1)/2", "(√3-1)/2")
    assert not wrongbook.answer_matches("2sin(2*(x+pi/3))", "2sin(2x+π/3)")
    assert not wrongbook.answer_matches("sqrt(3)+evil", "√(3)")
    assert not wrongbook.answer_matches("3/5", "5/3")
    assert not wrongbook.answer_matches("", "0")
    assert not wrongbook.answer_matches(3, "3")


def test_multi_choice_import_and_redo_do_not_clear_pending_or_mutate_foreign_rows(tmp_path, monkeypatch):
    monkeypatch.setattr(db, "DB_PATH", tmp_path / "redo.db")
    db.init_db()
    user = {"id": "u_owner"}
    with db.tx() as conn:
        conn.execute("INSERT INTO users(id,token_hash,sync_code,created_at,last_seen) VALUES('u_owner','h','c','2026','2026')")
        conn.execute("INSERT INTO users(id,token_hash,sync_code,created_at,last_seen) VALUES('u_other','h2','c2','2026','2026')")
        rows = [
            ("ready", "multi_choice", "ready", "", "[0,2]"),
            ("pending", "multi_choice", "needs_transcription", "原图缺选项", "[]"),
            ("foreign", "multi_choice", "ready", "", "[0,2]"),
            ("legacy", "choice", "ready", "", "[1]"),
        ]
        for rid, qtype, review, reason, answers in rows:
            conn.execute(
                "INSERT INTO wrong_questions(id,user_id,topic_id,section_id,tier,question_id,stem,options_json,answer,picked,status,source,qtype,answer_indices_json,review_status,review_reason,created_at,last_wrong_at) "
                "VALUES(?,?,'wb-math-trigonometry','import','import',?,'stem','[\"A\",\"B\",\"C\"]',?,?, 'open','import',?,?,?,?, '2026','2026')",
                (rid, "u_other" if rid == "foreign" else "u_family", rid, 1 if rid == "legacy" else -1, 0, qtype, answers, review, reason),
            )
        res = wrongbook.redo(conn, user, "wb-math-trigonometry", {"legacy": 1}, {"pending": "anything"}, {"ready": [2, 0]})
        assert res["cleared"] == 2
        assert res["remaining"] == 0
        pending = conn.execute("SELECT status,wrong_count FROM wrong_questions WHERE id='pending'").fetchone()
        assert tuple(pending) == ("open", 1)
        foreign = conn.execute("SELECT status FROM wrong_questions WHERE id='foreign'").fetchone()[0]
        assert foreign == "open"
        summary = wrongbook.summary(conn, wrongbook.book_owner("u_owner"))
        assert summary["open_total"] == 0
        assert summary["pending_total"] == 1


def test_ai_solve_preserves_all_multi_choice_answers(monkeypatch):
    from app.services import ai_client
    monkeypatch.setattr(ai_client, 'enabled', lambda: True)
    monkeypatch.setattr(ai_client, '_stub_on', lambda: False)
    monkeypatch.setattr(ai_client, 'chat', lambda *a, **k: {
        'text': json.dumps({'answer': 'D、A、B', 'steps': ['逐项判断'], 'key_point': '多选'}),
        'channel': 'test', 'model': 'test',
    })
    result = ai_client.solve({'qtype': 'multi_choice', 'stem': '多选', 'options': ['a', 'b', 'c', 'd']})
    assert result['answer'] == -1
    assert result['answer_indices'] == [0, 1, 3]
    assert result['answer_letter'] == 'A、B、D'


def test_schema_migration_keeps_legacy_single_choice_answer(tmp_path, monkeypatch):
    from app import db
    monkeypatch.setattr(db, "DB_PATH", tmp_path / "test.db")
    db.init_db()
    with db.ro() as conn:
        cols = {row["name"] for row in conn.execute("PRAGMA table_info(wrong_questions)")}
        assert {"answer_indices_json", "picked_indices_json", "review_status", "review_reason", "content_version"} <= cols
        assert conn.execute("SELECT version FROM schema_version WHERE id=1").fetchone()[0] == db.SCHEMA_VERSION
