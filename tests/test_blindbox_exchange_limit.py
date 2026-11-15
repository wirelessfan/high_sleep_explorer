"""Ticket quantity limits, old events, Beijing rollover and concurrent exchanges."""
from concurrent.futures import ThreadPoolExecutor

import pytest

from app import db
from app.services import blindbox, events


@pytest.fixture()
def account(tmp_path,monkeypatch):
    monkeypatch.setattr(db,'DB_PATH',tmp_path/'exchange.db')
    monkeypatch.setattr(blindbox,'_today',lambda:'2099-01-01')
    db.init_db()
    with db.tx() as conn:
        conn.execute("INSERT INTO users(id,token_hash,sync_code,points,created_at,last_seen) VALUES ('u','th','sc',2000,'2099-01-01','2099-01-01')")
        blindbox.grant_daily_tickets(conn,'u',initial=True)


def exchange(count):
    with db.tx() as conn:
        return blindbox.exchange_points(conn,conn.execute("SELECT * FROM users WHERE id='u'").fetchone(),count)


def balance():
    with db.ro() as conn:
        return tuple(conn.execute("SELECT points,blindbox_tickets FROM users WHERE id='u'").fetchone())


def test_one_batch_nine_and_tenth_rejected_without_deducting(account):
    assert exchange(9)['left_today']==0
    assert balance()==(1100,12)
    with pytest.raises(ValueError,match='每天最多兑换'):
        exchange(1)
    assert balance()==(1100,12)


def test_batch_cannot_exceed_remaining_and_old_count_is_honored(account):
    with db.tx() as conn:
        events.log(conn,'u','old-key','bbox_exchange',{'count':5,'points':500})
        conn.execute("UPDATE events SET created_at='2099-01-01T10:00:00' WHERE kind='bbox_exchange'")
    with pytest.raises(ValueError,match='还可兑换 4 张'):
        exchange(5)
    assert balance()==(2000,3)
    assert exchange(4)['left_today']==0


def test_explicit_beijing_date_survives_machine_timestamp_and_rolls_over(account,monkeypatch):
    exchange(9)
    with db.tx() as conn:
        conn.execute("UPDATE events SET created_at='2098-12-31T16:00:00' WHERE kind='bbox_exchange'")
    with pytest.raises(ValueError,match='每天最多兑换'):
        exchange(1)
    monkeypatch.setattr(blindbox,'_today',lambda:'2099-01-02')
    assert exchange(9)['left_today']==0
    assert balance()==(200,24)  # includes next day's three free tickets


def test_concurrent_devices_cannot_exceed_nine(account):
    def attempt(_):
        try:
            exchange(1)
            return 1
        except ValueError:
            return 0
    with ThreadPoolExecutor(max_workers=4) as pool:
        assert sum(pool.map(attempt,range(16)))==9
    assert balance()==(1100,12)
