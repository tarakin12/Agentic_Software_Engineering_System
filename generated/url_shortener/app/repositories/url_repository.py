"""
repositories/url_repository.py

All SQL for the `urls` table. No business logic lives here — only
persistence I/O (per architecture.md's layering rationale).
"""

from __future__ import annotations

import sqlite3
from typing import List, Optional

from ..models.url import UrlRecord


class UrlRepository:
    def __init__(self, conn: sqlite3.Connection):
        self._conn = conn

    @staticmethod
    def _row_to_record(row: sqlite3.Row) -> UrlRecord:
        return UrlRecord(
            id=row["id"],
            short_code=row["short_code"],
            original_url=row["original_url"],
            created_at=row["created_at"],
            expires_at=row["expires_at"],
            redirect_count=row["redirect_count"],
            last_accessed_at=row["last_accessed_at"],
        )

    def find_by_code(self, short_code: str) -> Optional[UrlRecord]:
        cur = self._conn.execute("SELECT * FROM urls WHERE short_code = ?", (short_code,))
        row = cur.fetchone()
        return self._row_to_record(row) if row else None

    def find_active_by_original_url(self, original_url: str, now_iso: str) -> Optional[UrlRecord]:
        """Return the most recent non-expired mapping for original_url, if any.

        Backs the idempotent-creation behavior (AC-003 / ASM-005)."""
        cur = self._conn.execute(
            "SELECT * FROM urls WHERE original_url = ? "
            "AND (expires_at IS NULL OR expires_at > ?) "
            "ORDER BY id DESC LIMIT 1",
            (original_url, now_iso),
        )
        row = cur.fetchone()
        return self._row_to_record(row) if row else None

    def code_exists(self, short_code: str) -> bool:
        cur = self._conn.execute("SELECT 1 FROM urls WHERE short_code = ?", (short_code,))
        return cur.fetchone() is not None

    def insert(
        self,
        short_code: str,
        original_url: str,
        created_at: str,
        expires_at: Optional[str] = None,
    ) -> UrlRecord:
        self._conn.execute(
            "INSERT INTO urls (short_code, original_url, created_at, expires_at, "
            "redirect_count, last_accessed_at) VALUES (?, ?, ?, ?, 0, NULL)",
            (short_code, original_url, created_at, expires_at),
        )
        self._conn.commit()
        record = self.find_by_code(short_code)
        assert record is not None  # just inserted; must exist
        return record

    def increment_redirect(self, short_code: str, accessed_at: str) -> None:
        self._conn.execute(
            "UPDATE urls SET redirect_count = redirect_count + 1, last_accessed_at = ? "
            "WHERE short_code = ?",
            (accessed_at, short_code),
        )
        self._conn.commit()

    def list_all(self) -> List[UrlRecord]:
        """Return every row in `urls`, most recently created first.

        Read-only listing used by the dashboard summary (see
        analytics/analytics_service.py::get_dashboard_summary). Does not
        duplicate any business logic — a plain SELECT * over the same
        table every other method here already uses."""
        cur = self._conn.execute("SELECT * FROM urls ORDER BY id DESC")
        return [self._row_to_record(row) for row in cur.fetchall()]



