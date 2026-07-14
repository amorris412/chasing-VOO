import sqlite3
from datetime import date

from chasing_voo.models import Snapshot
from chasing_voo.storage import Storage


def test_record_and_read_back(tmp_path):
    db = tmp_path / "test.sqlite3"
    with Storage(db) as store:
        store.record_day(date(2026, 1, 1), 1000.0, {"VOO": 400.0, "DIA": 300.0})
        store.record_day(date(2026, 1, 2), 1100.0, {"VOO": 420.0}, net_flow=50.0)
        snaps = store.snapshots()
        closes = store.benchmark_closes()
        assert store.tickers() == ["DIA", "VOO"]
    assert len(snaps) == 2
    assert snaps[1].net_flow == 50.0
    assert len(closes) == 3  # 2 VOO + 1 DIA


def test_upsert_replaces_same_day(tmp_path):
    db = tmp_path / "test.sqlite3"
    with Storage(db) as store:
        store.record_day(date(2026, 1, 1), 1000.0, {"VOO": 400.0})
        store.record_day(date(2026, 1, 1), 1234.0, {"VOO": 401.0})
        assert len(store.snapshots()) == 1
        assert store.latest_snapshot().equity == 1234.0
        assert len(store.benchmark_closes()) == 1


def test_legacy_schema_migrates(tmp_path):
    """An old snapshots table with benchmark_close migrates into benchmarks."""
    db = tmp_path / "legacy.sqlite3"
    conn = sqlite3.connect(str(db))
    conn.executescript(
        "CREATE TABLE snapshots (day TEXT PRIMARY KEY, equity REAL NOT NULL, "
        "benchmark_close REAL NOT NULL, net_flow REAL NOT NULL DEFAULT 0);"
        "INSERT INTO snapshots VALUES ('2026-01-01', 1000.0, 400.0, 0.0);"
    )
    conn.commit()
    conn.close()

    with Storage(db) as store:
        snaps = store.snapshots()
        closes = store.benchmark_closes()
    assert len(snaps) == 1 and snaps[0].equity == 1000.0
    assert len(closes) == 1 and closes[0].ticker == "VOO" and closes[0].close == 400.0
