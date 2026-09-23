"""
test_analytics_service.py — Unit tests (TASK-008)

Covers AC-007/AC-008 at the analytics-component level, isolated from
UrlService, to confirm the event log and aggregate counter stay in sync
independent of how they are invoked.
"""

from app.analytics.analytics_service import AnalyticsService
from app.db import get_connection, init_db
from app.repositories.analytics_repository import AnalyticsRepository
from app.repositories.url_repository import UrlRepository


def _setup():
    conn = get_connection(":memory:")
    init_db(conn)
    url_repo = UrlRepository(conn)
    analytics_repo = AnalyticsRepository(conn)
    return url_repo, analytics_repo, AnalyticsService(analytics_repo, url_repo)


def test_record_redirect_logs_event_and_increments_counter():
    url_repo, analytics_repo, analytics_service = _setup()
    record = url_repo.insert("code123", "https://example.com/x", "2026-01-01T00:00:00+00:00")

    analytics_service.record_redirect(record.short_code)

    updated = url_repo.find_by_code(record.short_code)
    assert updated.redirect_count == 1
    assert updated.last_accessed_at is not None
    assert analytics_repo.count_events(record.short_code) == 1


def test_record_redirect_multiple_times_accumulates():
    url_repo, analytics_repo, analytics_service = _setup()
    record = url_repo.insert("code456", "https://example.com/y", "2026-01-01T00:00:00+00:00")

    analytics_service.record_redirect(record.short_code)
    analytics_service.record_redirect(record.short_code)
    analytics_service.record_redirect(record.short_code)

    assert analytics_repo.count_events(record.short_code) == 3
    updated = url_repo.find_by_code(record.short_code)
    assert updated.redirect_count == 3


def test_record_redirect_for_unrelated_codes_does_not_cross_contaminate():
    url_repo, analytics_repo, analytics_service = _setup()
    a = url_repo.insert("codeAAA", "https://example.com/a", "2026-01-01T00:00:00+00:00")
    b = url_repo.insert("codeBBB", "https://example.com/b", "2026-01-01T00:00:00+00:00")

    analytics_service.record_redirect(a.short_code)

    assert analytics_repo.count_events(a.short_code) == 1
    assert analytics_repo.count_events(b.short_code) == 0
    assert url_repo.find_by_code(b.short_code).redirect_count == 0


def test_get_dashboard_summary_aggregates_across_urls():
    """Unit-level coverage for the dashboard aggregation (HTTP-level
    coverage lives in test_dashboard_api.py). Verifies totals, top-N
    ordering by redirect_count, and recent-event composition — all
    derived from existing repository reads, no new write path."""
    url_repo, analytics_repo, analytics_service = _setup()
    a = url_repo.insert("dashA01", "https://example.com/dashA", "2026-01-01T00:00:00+00:00")
    b = url_repo.insert("dashB01", "https://example.com/dashB", "2026-01-01T00:00:00+00:00")

    analytics_service.record_redirect(a.short_code)
    analytics_service.record_redirect(a.short_code)
    analytics_service.record_redirect(b.short_code)

    summary = analytics_service.get_dashboard_summary(top_n=2, recent_n=5, days=7)

    assert summary.total_urls == 2
    assert summary.total_redirects == 3
    assert summary.top_urls[0].short_code == "dashA01"
    assert summary.top_urls[0].redirect_count == 2
    assert len(summary.recent_events) == 3


def test_get_dashboard_summary_empty_when_no_urls():
    """Edge case: dashboard summary on a fresh database must return
    empty/zeroed results, not raise."""
    _url_repo, _analytics_repo, analytics_service = _setup()

    summary = analytics_service.get_dashboard_summary()

    assert summary.total_urls == 0
    assert summary.total_redirects == 0
    assert summary.top_urls == []
    assert summary.clicks_over_time == []
    assert summary.recent_events == []


