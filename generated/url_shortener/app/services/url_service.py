"""
services/url_service.py

Business logic for URL creation, redirect resolution, and analytics
retrieval. This is the only layer that knows about short-code generation,
idempotent-creation semantics (ASM-005), and expiration rules (ASM-003) —
API and repository layers stay dumb by design.
"""

from __future__ import annotations

import secrets
import string
from datetime import datetime, timezone
from typing import Tuple

from ..analytics.analytics_service import AnalyticsService
from ..models.exceptions import ShortCodeExpiredError, ShortCodeNotFoundError
from ..models.url import UrlRecord
from ..repositories.url_repository import UrlRepository

_ALPHABET = string.ascii_letters + string.digits
_CODE_LENGTH = 7
_MAX_GENERATION_ATTEMPTS = 5


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


class UrlService:
    def __init__(self, url_repo: UrlRepository, analytics_service: AnalyticsService):
        self._url_repo = url_repo
        self._analytics_service = analytics_service

    def _generate_unique_code(self) -> str:
        for _ in range(_MAX_GENERATION_ATTEMPTS):
            code = "".join(secrets.choice(_ALPHABET) for _ in range(_CODE_LENGTH))
            if not self._url_repo.code_exists(code):
                return code
        raise RuntimeError("Unable to generate a unique short code after multiple attempts")

    def create_short_url(self, original_url: str) -> Tuple[UrlRecord, bool]:
        """Returns (record, created). created=False means an existing,
        non-expired mapping was reused (idempotent creation, AC-003)."""
        now = _now_iso()
        existing = self._url_repo.find_active_by_original_url(original_url, now)
        if existing is not None:
            return existing, False
        code = self._generate_unique_code()
        record = self._url_repo.insert(code, original_url, now)
        return record, True

    def resolve_for_redirect(self, short_code: str) -> UrlRecord:
        """Returns the record to redirect to, recording the redirect event.
        Raises ShortCodeNotFoundError / ShortCodeExpiredError (AC-005/AC-006)."""
        record = self._url_repo.find_by_code(short_code)
        if record is None:
            raise ShortCodeNotFoundError(short_code)
        if record.expires_at is not None and record.expires_at <= _now_iso():
            raise ShortCodeExpiredError(short_code)
        self._analytics_service.record_redirect(short_code)
        updated = self._url_repo.find_by_code(short_code)
        return updated or record

    def get_analytics(self, short_code: str) -> UrlRecord:
        record = self._url_repo.find_by_code(short_code)
        if record is None:
            raise ShortCodeNotFoundError(short_code)
        return record

    def get_dashboard_summary(self, top_n: int = 5, recent_n: int = 10, days: int = 7):
        """Thin passthrough to the Analytics component — keeps the API
        layer dependent only on UrlService, consistent with every other
        endpoint (see api/urls.py, api/redirect.py). Adds no logic."""
        return self._analytics_service.get_dashboard_summary(top_n, recent_n, days)


