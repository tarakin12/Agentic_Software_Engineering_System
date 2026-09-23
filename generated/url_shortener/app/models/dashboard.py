"""
models/dashboard.py

Domain dataclasses + Pydantic response schemas for the read-only
analytics dashboard. Mirrors the existing models/url.py pattern: the
service/analytics layer returns plain dataclasses, and the API layer
(app/api/dashboard.py) maps them onto Pydantic response models matching
artifacts/openapi.yaml.

Introduces no new persistence, no new analytics engine, no new business
rules — only shapes data already produced by UrlRepository /
AnalyticsRepository for presentation.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional

from pydantic import BaseModel


@dataclass
class TopUrlEntry:
    short_code: str
    original_url: str
    redirect_count: int
    last_accessed_at: Optional[str]


@dataclass
class ClicksOverTimePoint:
    date: str
    count: int


@dataclass
class RecentEventEntry:
    short_code: str
    original_url: str
    accessed_at: str


@dataclass
class DashboardSummary:
    total_urls: int
    total_redirects: int
    top_urls: List[TopUrlEntry] = field(default_factory=list)
    clicks_over_time: List[ClicksOverTimePoint] = field(default_factory=list)
    recent_events: List[RecentEventEntry] = field(default_factory=list)


class TopUrlItem(BaseModel):
    short_code: str
    original_url: str
    redirect_count: int
    last_accessed_at: Optional[str] = None


class ClicksOverTimePointResponse(BaseModel):
    date: str
    count: int


class RecentEventItem(BaseModel):
    short_code: str
    original_url: str
    accessed_at: str


class DashboardSummaryResponse(BaseModel):
    total_urls: int
    total_redirects: int
    top_urls: List[TopUrlItem]
    clicks_over_time: List[ClicksOverTimePointResponse]
    recent_events: List[RecentEventItem]

