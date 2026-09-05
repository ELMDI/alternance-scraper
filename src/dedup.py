"""SQLite-backed deduplication store.

Tracks every job offer that has been sent to the user so the same offer
is never notified twice across successive GitHub Actions runs.
"""

from __future__ import annotations

import logging
import sqlite3
from datetime import datetime, timezone
from typing import List, Sequence

from src.models import Job
from src import config

logger = logging.getLogger(__name__)


_CREATE_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS seen_jobs (
    job_id       TEXT PRIMARY KEY,
    url          TEXT,
    title        TEXT,
    company      TEXT,
    source       TEXT,
    first_seen   TEXT,
    notified_at  TEXT
);
"""


class DedupStore:
    """Thin wrapper around a SQLite database for job deduplication."""

    def __init__(self, db_path: str | None = None) -> None:
        self._db_path = db_path or config.DB_PATH
        self._conn: sqlite3.Connection | None = None

    # ------------------------------------------------------------------
    # Context-manager support
    # ------------------------------------------------------------------

    def open(self) -> None:
        """Open (or create) the database and ensure the schema exists."""
        logger.debug("Opening dedup database at %s", self._db_path)
        self._conn = sqlite3.connect(self._db_path)
        self._conn.execute(_CREATE_TABLE_SQL)
        self._conn.commit()

    def close(self) -> None:
        """Close the database connection."""
        if self._conn:
            self._conn.close()
            self._conn = None

    def __enter__(self) -> "DedupStore":
        self.open()
        return self

    def __exit__(self, *exc) -> None:  # noqa: ANN002
        self.close()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def is_new(self, job: Job) -> bool:
        """Return ``True`` if *job* has never been seen before."""
        assert self._conn is not None, "DedupStore is not open"
        cursor = self._conn.execute(
            "SELECT 1 FROM seen_jobs WHERE job_id = ?", (job.dedup_key,)
        )
        return cursor.fetchone() is None

    def filter_new(self, jobs: Sequence[Job]) -> List[Job]:
        """Return only jobs that have never been seen before."""
        return [j for j in jobs if self.is_new(j)]

    def mark_seen(self, jobs: Sequence[Job]) -> None:
        """Insert *jobs* into the seen-jobs table (idempotent)."""
        assert self._conn is not None, "DedupStore is not open"
        now = datetime.now(timezone.utc).isoformat()
        rows = [
            (j.dedup_key, j.url, j.title, j.company, j.source, now, now)
            for j in jobs
        ]
        self._conn.executemany(
            """
            INSERT OR IGNORE INTO seen_jobs
                (job_id, url, title, company, source, first_seen, notified_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            rows,
        )
        self._conn.commit()
        logger.info("Marked %d job(s) as seen.", len(rows))

    def count(self) -> int:
        """Return total number of seen jobs."""
        assert self._conn is not None, "DedupStore is not open"
        cursor = self._conn.execute("SELECT COUNT(*) FROM seen_jobs")
        return cursor.fetchone()[0]
