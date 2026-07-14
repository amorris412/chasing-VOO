"""SQLite storage for daily snapshots.

Uses only the Python standard library (``sqlite3``) so there are no extra
dependencies for the storage layer. The database is a single local file
(git-ignored) — it never leaves your machine.
"""

from __future__ import annotations

import sqlite3
from datetime import date
from pathlib import Path
from typing import Iterable, List, Optional

from .models import Snapshot

_SCHEMA = """
CREATE TABLE IF NOT EXISTS snapshots (
    day             TEXT    PRIMARY KEY,   -- ISO date, one row per day
    equity          REAL    NOT NULL,
    benchmark_close REAL    NOT NULL,
    net_flow        REAL    NOT NULL DEFAULT 0
);
"""


class Storage:
    """Thin persistence wrapper around a single SQLite file."""

    def __init__(self, db_path: Path):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(str(self.db_path))
        self._conn.row_factory = sqlite3.Row
        self._conn.execute(_SCHEMA)
        self._conn.commit()

    # -- writes ---------------------------------------------------------------
    def upsert(self, snapshot: Snapshot) -> None:
        """Insert or replace the snapshot for a given day."""
        self._conn.execute(
            """
            INSERT INTO snapshots (day, equity, benchmark_close, net_flow)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(day) DO UPDATE SET
                equity = excluded.equity,
                benchmark_close = excluded.benchmark_close,
                net_flow = excluded.net_flow
            """,
            (
                snapshot.day.isoformat(),
                float(snapshot.equity),
                float(snapshot.benchmark_close),
                float(snapshot.net_flow),
            ),
        )
        self._conn.commit()

    def upsert_many(self, snapshots: Iterable[Snapshot]) -> None:
        for snap in snapshots:
            self.upsert(snap)

    def delete(self, day: date) -> None:
        self._conn.execute("DELETE FROM snapshots WHERE day = ?", (day.isoformat(),))
        self._conn.commit()

    # -- reads ----------------------------------------------------------------
    def get(self, day: date) -> Optional[Snapshot]:
        row = self._conn.execute(
            "SELECT * FROM snapshots WHERE day = ?", (day.isoformat(),)
        ).fetchone()
        return _row_to_snapshot(row) if row else None

    def all(self) -> List[Snapshot]:
        """Return every snapshot ordered oldest-first."""
        rows = self._conn.execute(
            "SELECT * FROM snapshots ORDER BY day ASC"
        ).fetchall()
        return [_row_to_snapshot(r) for r in rows]

    def latest(self) -> Optional[Snapshot]:
        row = self._conn.execute(
            "SELECT * FROM snapshots ORDER BY day DESC LIMIT 1"
        ).fetchone()
        return _row_to_snapshot(row) if row else None

    def close(self) -> None:
        self._conn.close()

    def __enter__(self) -> "Storage":
        return self

    def __exit__(self, *_exc) -> None:
        self.close()


def _row_to_snapshot(row: sqlite3.Row) -> Snapshot:
    return Snapshot(
        day=date.fromisoformat(row["day"]),
        equity=row["equity"],
        benchmark_close=row["benchmark_close"],
        net_flow=row["net_flow"],
    )
