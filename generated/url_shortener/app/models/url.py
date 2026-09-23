"""
models/url.py

Pydantic request/response schemas (API boundary, matches artifacts/openapi.yaml)
and the internal UrlRecord representation of a row in the `urls` table.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from pydantic import AnyHttpUrl, BaseModel


class CreateUrlRequest(BaseModel):
    url: AnyHttpUrl


class CreateUrlResponse(BaseModel):
    short_code: str
    short_url: str


class AnalyticsResponse(BaseModel):
    short_code: str
    original_url: str
    created_at: str
    redirect_count: int
    last_accessed_at: Optional[str] = None


@dataclass
class UrlRecord:
    """Internal representation of a row in the `urls` table."""

    id: int
    short_code: str
    original_url: str
    created_at: str
    expires_at: Optional[str]
    redirect_count: int
    last_accessed_at: Optional[str]

