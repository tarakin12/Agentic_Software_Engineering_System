"""
repositories/analytics_repository.py

All SQL for the `redirect_events` table (per-event history, per
architecture.md §6/§12).
"""

from __future__ import annotations

import sqlite3


class AnalyticsRepository:
    def __init__(self, conn: sqlite3.Connection):
        self._conn = conn

    def log_event(self, short_code: str, accessed_at: str) -> None:
        self._conn.execute(
            "INSERT INTO redirect_events (short_code, accessed_at) VALUES (?, ?)",
            (short_code, accessed_at),
        )
        self._conn.commit()

    def count_events(self, short_code: str) -> int:
        cur = self._conn.execute(
            "SELECT COUNT(*) AS cnt FROM redirect_events WHERE short_code = ?",
            (short_code,),
        )
        row = cur.fetchone()
        return int(row["cnt"]) if row else 0

    def list_recent_events(self, limit: int = 10) -> list:
        """Most recent redirect events, joined with the owning URL's
        original_url for display purposes. Read-only — does not alter the
        event log or the aggregate counters written by log_event()."""
        cur = self._conn.execute(
            "SELECT re.short_code AS short_code, re.accessed_at AS accessed_at, "
            "u.original_url AS original_url "
            "FROM redirect_events re "
            "JOIN urls u ON u.short_code = re.short_code "
            "ORDER BY re.accessed_at DESC, re.id DESC LIMIT ?",
            (limit,),
        )
        return [dict(row) for row in cur.fetchall()]

    def count_events_by_day(self, days: int = 7) -> list:
        """Redirect counts bucketed by UTC calendar day (from accessed_at's
        date portion), most recent `days` days that have at least one
        event. A plain GROUP BY over the existing redirect_events table —
        not a new analytics engine, just an aggregate read query."""
        cur = self._conn.execute(
            "SELECT substr(accessed_at, 1, 10) AS day, COUNT(*) AS count "
            "FROM redirect_events GROUP BY day ORDER BY day DESC LIMIT ?",
            (days,),
        )
        rows = [dict(row) for row in cur.fetchall()]
        return list(reversed(rows))  # chronological order for charting


