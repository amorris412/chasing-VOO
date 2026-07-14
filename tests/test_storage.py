from datetime import date

from chasing_voo.models import Snapshot
from chasing_voo.storage import Storage


def test_upsert_and_read_back(tmp_path):
    db = tmp_path / "test.sqlite3"
    with Storage(db) as store:
        store.upsert(Snapshot(date(2026, 1, 1), 1000.0, 400.0))
        store.upsert(Snapshot(date(2026, 1, 2), 1100.0, 420.0, net_flow=50.0))
        rows = store.all()
    assert len(rows) == 2
    assert rows[0].day == date(2026, 1, 1)
    assert rows[1].net_flow == 50.0


def test_upsert_replaces_same_day(tmp_path):
    db = tmp_path / "test.sqlite3"
    with Storage(db) as store:
        store.upsert(Snapshot(date(2026, 1, 1), 1000.0, 400.0))
        store.upsert(Snapshot(date(2026, 1, 1), 1234.0, 400.0))
        assert len(store.all()) == 1
        assert store.get(date(2026, 1, 1)).equity == 1234.0


def test_latest_returns_most_recent(tmp_path):
    db = tmp_path / "test.sqlite3"
    with Storage(db) as store:
        store.upsert(Snapshot(date(2026, 1, 1), 1000.0, 400.0))
        store.upsert(Snapshot(date(2026, 1, 3), 1200.0, 410.0))
        store.upsert(Snapshot(date(2026, 1, 2), 1100.0, 405.0))
        assert store.latest().day == date(2026, 1, 3)
