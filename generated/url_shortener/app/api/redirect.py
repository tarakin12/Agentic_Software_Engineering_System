"""
api/redirect.py

GET /{short_code} — redirects to the original URL, or returns 404/410.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import RedirectResponse

from ..models.exceptions import ShortCodeExpiredError, ShortCodeNotFoundError
from ..services.url_service import UrlService

router = APIRouter()


def get_url_service(request: Request) -> UrlService:
    return request.app.state.url_service


@router.get("/{short_code}")
def redirect_short_code(
    short_code: str,
    service: UrlService = Depends(get_url_service),
) -> RedirectResponse:
    try:
        record = service.resolve_for_redirect(short_code)
    except ShortCodeNotFoundError as exc:
        raise HTTPException(status_code=404, detail="Unknown short code") from exc
    except ShortCodeExpiredError as exc:
        raise HTTPException(status_code=410, detail="Short code has expired") from exc
    return RedirectResponse(url=record.original_url, status_code=302)

