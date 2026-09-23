"""
test_url_service.py — Unit tests (TASK-008)

Covers AC-001, AC-002 (validation is API-layer, see test_api.py), AC-003
(idempotent creation), AC-004..AC-006 (resolve_for_redirect), and boundary
conditions (unknown code, expired code) at the service layer, isolated
from HTTP concerns.
"""

from datetime import datetime, timedelta, timezone

import pytest

from app.analytics.analytics_service import AnalyticsService
from app.db import get_connection, init_db
from app.models.exceptions import ShortCodeExpiredError, ShortCodeNotFoundError
from app.repositories.analytics_repository import AnalyticsRepository
from app.repositories.url_repository import UrlRepository
from app.services.url_service import UrlService


@pytest.fixture
def service():
    conn = get_connection(":memory:")
    init_db(conn)
    url_repo = UrlRepository(conn)
    analytics_repo = AnalyticsRepository(conn)
    analytics_service = AnalyticsService(analytics_repo, url_repo)
    return UrlService(url_repo, analytics_service)


def test_create_short_url_returns_new_code(service):
    record, created = service.create_short_url("https://example.com/a")
    assert created is True
    assert len(record.short_code) == 7
    assert record.original_url == "https://example.com/a"
    assert record.redirect_count == 0


def test_create_short_url_is_idempotent_for_same_url(service):
    """AC-003 / ASM-005: resubmitting the same original_url reuses the code."""
    first, created_first = service.create_short_url("https://example.com/b")
    second, created_second = service.create_short_url("https://example.com/b")
    assert created_first is True
    assert created_second is False
    assert first.short_code == second.short_code


def test_create_short_url_different_urls_get_different_codes(service):
    first, _ = service.create_short_url("https://example.com/x")
    second, _ = service.create_short_url("https://example.com/y")
    assert first.short_code != second.short_code


def test_resolve_for_redirect_unknown_code_raises(service):
    """AC-005."""
    with pytest.raises(ShortCodeNotFoundError):
        service.resolve_for_redirect("doesnotexist")


def test_resolve_for_redirect_increments_count(service):
    """AC-008: redirect increments count and updates last_accessed_at."""
    record, _ = service.create_short_url("https://example.com/c")
    resolved = service.resolve_for_redirect(record.short_code)
    assert resolved.redirect_count == 1
    assert resolved.last_accessed_at is not None
    resolved_again = service.resolve_for_redirect(record.short_code)
    assert resolved_again.redirect_count == 2


def test_resolve_for_redirect_expired_code_raises(service):
    """AC-006: expired short codes raise ShortCodeExpiredError, not a redirect."""
    past = (datetime.now(timezone.utc) - timedelta(days=1)).isoformat()
    record = service._url_repo.insert(
        "expired1", "https://example.com/d", past, expires_at=past
    )
    with pytest.raises(ShortCodeExpiredError):
        service.resolve_for_redirect(record.short_code)


def test_resolve_for_redirect_future_expiry_still_redirects(service):
    """Boundary condition: a not-yet-expired code must still redirect."""
    now = datetime.now(timezone.utc)
    future = (now + timedelta(days=1)).isoformat()
    record = service._url_repo.insert(
        "future01", "https://example.com/future", now.isoformat(), expires_at=future
    )
    resolved = service.resolve_for_redirect(record.short_code)
    assert resolved.short_code == "future01"


def test_get_analytics_unknown_code_raises(service):
    with pytest.raises(ShortCodeNotFoundError):
        service.get_analytics("nope")


def test_get_analytics_returns_expected_fields(service):
    """AC-007."""
    record, _ = service.create_short_url("https://example.com/e")
    service.resolve_for_redirect(record.short_code)
    analytics = service.get_analytics(record.short_code)
    assert analytics.redirect_count == 1
    assert analytics.last_accessed_at is not None
    assert analytics.original_url == "https://example.com/e"

