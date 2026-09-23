"""
api/urls.py

POST /urls, GET /urls/{short_code}/analytics — thin HTTP adapters over
UrlService. No business logic here.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request, Response

from ..models.exceptions import ShortCodeNotFoundError
from ..models.url import AnalyticsResponse, CreateUrlRequest, CreateUrlResponse
from ..services.url_service import UrlService

router = APIRouter()


def get_url_service(request: Request) -> UrlService:
    return request.app.state.url_service


@router.post("/urls", response_model=CreateUrlResponse)
def create_url(
    payload: CreateUrlRequest,
    response: Response,
    service: UrlService = Depends(get_url_service),
) -> CreateUrlResponse:
    record, created = service.create_short_url(str(payload.url))
    response.status_code = 201 if created else 200
    return CreateUrlResponse(short_code=record.short_code, short_url=f"/{record.short_code}")


@router.get("/urls/{short_code}/analytics", response_model=AnalyticsResponse)
def get_analytics(
    short_code: str,
    service: UrlService = Depends(get_url_service),
) -> AnalyticsResponse:
    try:
        record = service.get_analytics(short_code)
    except ShortCodeNotFoundError as exc:
        raise HTTPException(status_code=404, detail="Unknown short code") from exc
    return AnalyticsResponse(
        short_code=record.short_code,
        original_url=record.original_url,
        created_at=record.created_at,
        redirect_count=record.redirect_count,
        last_accessed_at=record.last_accessed_at,
    )

