"""
models/exceptions.py

Domain exceptions raised by the service layer. The API layer translates
these into HTTP status codes (see app/api/urls.py, app/api/redirect.py).
"""

from __future__ import annotations


class ShortCodeNotFoundError(Exception):
    """Raised when a short_code does not exist."""


class ShortCodeExpiredError(Exception):
    """Raised when a short_code exists but its expires_at has passed."""

