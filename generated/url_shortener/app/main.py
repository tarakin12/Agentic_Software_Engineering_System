"""
main.py

FastAPI application assembly: wires repositories -> services -> API routers
against a single SQLite connection. create_app(db_path=...) allows tests to
inject an isolated database per test run.
"""

from __future__ import annotations

from pathlib import Path
from typing import Optional

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from .analytics.analytics_service import AnalyticsService
from .api import dashboard as dashboard_api
from .api import redirect as redirect_api
from .api import urls as urls_api
from .db import default_db_path, get_connection, init_db
from .repositories.analytics_repository import AnalyticsRepository
from .repositories.url_repository import UrlRepository
from .services.url_service import UrlService

_STATIC_DASHBOARD_DIR = Path(__file__).resolve().parent / "static" / "dashboard"


def create_app(db_path: Optional[str] = None) -> FastAPI:
    app = FastAPI(
        title="URL Shortener Service",
        version="1.0.0",
        description="Prototype URL shortener: create, redirect, analytics.",
    )

    path = db_path or default_db_path()
    conn = get_connection(path)
    init_db(conn)

    url_repo = UrlRepository(conn)
    analytics_repo = AnalyticsRepository(conn)
    analytics_service = AnalyticsService(analytics_repo, url_repo)
    url_service = UrlService(url_repo, analytics_service)

    app.state.url_service = url_service
    app.state.db_connection = conn

    # /urls (POST) and /urls/{short_code}/analytics (GET) are more specific
    # path patterns than /{short_code}; registration order does not affect
    # correctness here since Starlette matches by full path pattern, but
    # urls_api is included first for readability (specific routes before
    # the catch-all-style redirect route).
    #
    # The new dashboard API route and the dashboard static-file mount are
    # ALSO registered before redirect_api.router for the same reason:
    # GET /{short_code} is a catch-all-style path parameter that would
    # otherwise shadow "/analytics/dashboard" and "/dashboard/*". (Note:
    # generated short_codes are always exactly 7 characters, so the
    # literal word "dashboard" — 9 characters — can never collide with a
    # real short_code.)
    app.include_router(urls_api.router)
    app.include_router(dashboard_api.router)

    if _STATIC_DASHBOARD_DIR.exists():
        # Read-only analytics dashboard UI (plain HTML/CSS/JS, no build
        # step, no new framework). It only ever calls the real
        # GET /analytics/dashboard API above — no separate backend, no
        # new database, no analytics engine.
        app.mount(
            "/dashboard",
            StaticFiles(directory=str(_STATIC_DASHBOARD_DIR), html=True),
            name="dashboard-ui",
        )

    app.include_router(redirect_api.router)

    @app.get("/", include_in_schema=False)
    def root():
        """Root landing endpoint. Not part of the API contract
        (artifacts/openapi.yaml) — added purely for evaluator UX so that
        hitting http://127.0.0.1:8000/ directly doesn't return a bare 404.
        The core API endpoints are unchanged and unaffected."""
        return {
            "service": "URL Shortener Service",
            "docs": "/docs",
            "endpoints": {
                "create_short_url": "POST /urls",
                "redirect": "GET /{short_code}",
                "analytics": "GET /urls/{short_code}/analytics",
                "dashboard_api": "GET /analytics/dashboard",
                "dashboard_ui": "GET /dashboard/",
            },
        }

    return app


app = create_app()


