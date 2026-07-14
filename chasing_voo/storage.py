"""SQLite storage for daily portfolio snapshots and benchmark closes.

Two tables:
* ``snapshots``  — one row per day: portfolio equity + net external cash flow.
* ``benchmarks`` — one row per (day, ticker): that index's closing price.

Splitting benchmarks into their own table lets you track any number of indices
(S&P 500 / Dow / Nasdaq / …) without schema changes. Standard-library
``sqlite3`` only — the database is a single local file.
"""

from __future__ import annotations

import sqlite3
from datetime import date
from pathlib import Path
from typing import Dict, Iterable, List, Mapping, Optional

from .models import BenchmarkClose, Snapshot

_SCHEMA = """
CREATE TABLE IF NOT EXISTS snapshots (
    day       TEXT PRIMARY KEY,
    equity    REAL NOT NULL,
    net_flow  REAL NOT NULL DEFAULT 0
);
CREATE TABLE IF NOT EXISTS benchmarks (
    day     TEXT NOT NULL,
    ticker  TEXT NOT NULL,
    close   REAL NOT NULL,
    PRIMARY KEY (day, ticker)
);
"""


class Storage:
    """Persistence wrapper around a single SQLite file."""

    def __init__(self, db_path: Path):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(str(self.db_path))
        self._conn.row_factory = sqlite3.Row
        self._conn.executescript(_SCHEMA)
        self._migrate_legacy_schema()
        self._conn.commit()

    # -- migration ------------------------------------------------------------
    def _migrate_legacy_schema(self) -> None:
        """Migrate an old single-benchmark ``snapshots`` table if present.

        Older versions stored a ``benchmark_close`` column on ``snapshots``.
        Move those values into the ``benchmarks`` table (as VOO) and drop the
        column so both old and new databases converge on the new schema.
        """
        cols = {r["name"] for r in self._conn.execute("PRAGMA table_info(snapshots)")}
        if "benchmark_close" not in cols:
            return
        self._conn.execute(
            "INSERT OR IGNORE INTO benchmarks (day, ticker, close) "
            "SELECT day, 'VOO', benchmark_close FROM snapshots "
            "WHERE benchmark_close IS NOT NULL"
        )
        try:
            self._conn.execute("ALTER TABLE snapshots DROP COLUMN benchmark_close")
        except sqlite3.OperationalError:  # pragma: no cover - very old sqlite
            self._conn.executescript(
                "CREATE TABLE _snap_new (day TEXT PRIMARY KEY, equity REAL NOT NULL, "
                "net_flow REAL NOT NULL DEFAULT 0);"
                "INSERT INTO _snap_new (day, equity, net_flow) "
                "SELECT day, equity, net_flow FROM snapshots;"
                "DROP TABLE snapshots;"
                "ALTER TABLE _snap_new RENAME TO snapshots;"
            )

    # -- writes ---------------------------------------------------------------
    def upsert_snapshot(self, snapshot: Snapshot) -> None:
        self._conn.execute(
            "INSERT INTO snapshots (day, equity, net_flow) VALUES (?, ?, ?) "
            "ON CONFLICT(day) DO UPDATE SET equity=excluded.equity, net_flow=excluded.net_flow",
            (snapshot.day.isoformat(), float(snapshot.equity), float(snapshot.net_flow)),
        )
        self._conn.commit()

    def upsert_benchmark(self, day: date, ticker: str, close: float) -> None:
        self._conn.execute(
            "INSERT INTO benchmarks (day, ticker, close) VALUES (?, ?, ?) "
            "ON CONFLICT(day, ticker) DO UPDATE SET close=excluded.close",
            (day.isoformat(), ticker.upper(), float(close)),
        )
        self._conn.commit()

    def record_day(
        self,
        day: date,
        equity: float,
        benchmarks: Mapping[str, float],
        net_flow: float = 0.0,
    ) -> None:
        """Record a full day: portfolio equity + a set of benchmark closes."""
        self.upsert_snapshot(Snapshot(day=day, equity=equity, net_flow=net_flow))
        for ticker, close in benchmarks.items():
            if close is not None:
                self.upsert_benchmark(day, ticker, close)

    def delete_day(self, day: date) -> None:
        self._conn.execute("DELETE FROM snapshots WHERE day = ?", (day.isoformat(),))
        self._conn.execute("DELETE FROM benchmarks WHERE day = ?", (day.isoformat(),))
        self._conn.commit()

    # -- reads ----------------------------------------------------------------
    def snapshots(self) -> List[Snapshot]:
        rows = self._conn.execute("SELECT * FROM snapshots ORDER BY day ASC").fetchall()
        return [Snapshot(date.fromisoformat(r["day"]), r["equity"], r["net_flow"]) for r in rows]

    def benchmark_closes(self) -> List[BenchmarkClose]:
        rows = self._conn.execute(
            "SELECT * FROM benchmarks ORDER BY day ASC, ticker ASC"
        ).fetchall()
        return [
            BenchmarkClose(date.fromisoformat(r["day"]), r["ticker"], r["close"]) for r in rows
        ]

    def tickers(self) -> List[str]:
        rows = self._conn.execute(
            "SELECT DISTINCT ticker FROM benchmarks ORDER BY ticker"
        ).fetchall()
        return [r["ticker"] for r in rows]

    def latest_snapshot(self) -> Optional[Snapshot]:
        r = self._conn.execute("SELECT * FROM snapshots ORDER BY day DESC LIMIT 1").fetchone()
        return Snapshot(date.fromisoformat(r["day"]), r["equity"], r["net_flow"]) if r else None

    def close(self) -> None:
        self._conn.close()

    def __enter__(self) -> "Storage":
        return self

    def __exit__(self, *_exc) -> None:
        self.close()
