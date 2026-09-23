"""
analytics/analytics_service.py

Records a redirect event (per-event log) and keeps the aggregate counter on
the `urls` row in sync. Kept as its own component (not folded into
UrlService) so it can be swapped for an async/queued implementation later
(architecture.md §13 Future Evolution) without touching URL creation or
redirect-resolution logic.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

from ..models.dashboard import ClicksOverTimePoint, DashboardSummary, RecentEventEntry, TopUrlEntry
from ..repositories.analytics_repository import AnalyticsRepository
from ..repositories.url_repository import UrlRepository


class AnalyticsService:
    def __init__(self, analytics_repo: AnalyticsRepository, url_repo: UrlRepository):
        self._analytics_repo = analytics_repo
        self._url_repo = url_repo

    def record_redirect(self, short_code: str, accessed_at: Optional[str] = None) -> None:
        timestamp = accessed_at or datetime.now(timezone.utc).isoformat()
        self._analytics_repo.log_event(short_code, timestamp)
        self._url_repo.increment_redirect(short_code, timestamp)

    def get_dashboard_summary(
        self, top_n: int = 5, recent_n: int = 10, days: int = 7
    ) -> DashboardSummary:
        """Composes existing repository reads into a single read-only
        summary for the dashboard UI. Reuses UrlRepository.list_all() and
        AnalyticsRepository's event-log queries — no new counters, no new
        tables, no duplicated increment/record logic (that stays solely
        in record_redirect() above)."""
        urls = self._url_repo.list_all()
        total_urls = len(urls)
        total_redirects = sum(u.redirect_count for u in urls)

        top_sorted = sorted(urls, key=lambda u: u.redirect_count, reverse=True)[:top_n]
        top_urls = [
            TopUrlEntry(
                short_code=u.short_code,
                original_url=u.original_url,
                redirect_count=u.redirect_count,
                last_accessed_at=u.last_accessed_at,
            )
            for u in top_sorted
        ]

        clicks_over_time = [
            ClicksOverTimePoint(date=row["day"], count=row["count"])
            for row in self._analytics_repo.count_events_by_day(days)
        ]

        recent_events = [
            RecentEventEntry(
                short_code=row["short_code"],
                original_url=row["original_url"],
                accessed_at=row["accessed_at"],
            )
            for row in self._analytics_repo.list_recent_events(recent_n)
        ]

        return DashboardSummary(
            total_urls=total_urls,
            total_redirects=total_redirects,
            top_urls=top_urls,
            clicks_over_time=clicks_over_time,
            recent_events=recent_events,
        )



