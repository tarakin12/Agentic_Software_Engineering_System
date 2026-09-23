"""
api/dashboard.py

GET /analytics/dashboard — read-only aggregate view over existing
analytics data (urls + redirect_events). Thin HTTP adapter only: no
business logic, no direct SQL — mirrors api/urls.py's layering.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, Request

from ..models.dashboard import (
    ClicksOverTimePointResponse,
    DashboardSummaryResponse,
    RecentEventItem,
    TopUrlItem,
)
from ..services.url_service import UrlService

router = APIRouter()


def get_url_service(request: Request) -> UrlService:
    return request.app.state.url_service


@router.get("/analytics/dashboard", response_model=DashboardSummaryResponse)
def get_dashboard(
    top: int = 5,
    recent: int = 10,
    days: int = 7,
    service: UrlService = Depends(get_url_service),
) -> DashboardSummaryResponse:
    summary = service.get_dashboard_summary(top_n=top, recent_n=recent, days=days)
    return DashboardSummaryResponse(
        total_urls=summary.total_urls,
        total_redirects=summary.total_redirects,
        top_urls=[TopUrlItem(**vars(u)) for u in summary.top_urls],
        clicks_over_time=[ClicksOverTimePointResponse(**vars(p)) for p in summary.clicks_over_time],
        recent_events=[RecentEventItem(**vars(e)) for e in summary.recent_events],
    )

