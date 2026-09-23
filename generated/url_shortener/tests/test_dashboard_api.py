"""
test_dashboard_api.py — Tests for the read-only analytics dashboard API
(GET /analytics/dashboard) and the static dashboard UI mount (GET
/dashboard/). Exercises the aggregate summary end-to-end via FastAPI's
TestClient without altering or duplicating existing analytics-recording
logic (that remains covered by test_analytics_service.py / test_api.py).

Covers positive, negative, and edge-case scenarios for the new dashboard
feature only — it does not re-test existing endpoints.
"""

import pytest
from fastapi.testclient import TestClient

from app.main import create_app


@pytest.fixture
def client(tmp_path):
    db_path = str(tmp_path / "test_dashboard.db")
    app = create_app(db_path=db_path)
    return TestClient(app)


def test_dashboard_empty_state_returns_zeros(client):
    """Edge case: no URLs created yet — must not error; all aggregates
    should be zero/empty rather than raising."""
    resp = client.get("/analytics/dashboard")
    assert resp.status_code == 200
    body = resp.json()
    assert body["total_urls"] == 0
    assert body["total_redirects"] == 0
    assert body["top_urls"] == []
    assert body["clicks_over_time"] == []
    assert body["recent_events"] == []


def test_dashboard_reflects_created_urls_and_redirects(client):
    """Positive: after creating URLs and redirecting, totals/top/recent
    all reflect real data from the existing /urls and /{code} endpoints —
    no separate write path is used."""
    a = client.post("/urls", json={"url": "https://example.com/dash-a"}).json()
    b = client.post("/urls", json={"url": "https://example.com/dash-b"}).json()

    client.get(f"/{a['short_code']}", follow_redirects=False)
    client.get(f"/{a['short_code']}", follow_redirects=False)
    client.get(f"/{b['short_code']}", follow_redirects=False)

    resp = client.get("/analytics/dashboard")
    assert resp.status_code == 200
    body = resp.json()

    assert body["total_urls"] == 2
    assert body["total_redirects"] == 3

    # Top accessed: 'a' has 2 redirects, should rank above 'b' (1 redirect)
    assert body["top_urls"][0]["short_code"] == a["short_code"]
    assert body["top_urls"][0]["redirect_count"] == 2

    # Recent events: most recent 3 events present
    assert len(body["recent_events"]) == 3
    assert body["recent_events"][0]["short_code"] in {a["short_code"], b["short_code"]}

    # Clicks over time: at least one bucket, total count matches redirects
    assert len(body["clicks_over_time"]) >= 1
    assert sum(point["count"] for point in body["clicks_over_time"]) == 3


def test_dashboard_top_param_limits_results(client):
    """Edge case: ?top= query param bounds the top_urls list length."""
    for i in range(3):
        created = client.post("/urls", json={"url": f"https://example.com/limit-{i}"}).json()
        client.get(f"/{created['short_code']}", follow_redirects=False)

    resp = client.get("/analytics/dashboard?top=1")
    assert resp.status_code == 200
    assert len(resp.json()["top_urls"]) == 1


def test_dashboard_invalid_query_param_returns_422(client):
    """Negative: a non-integer query param must fail cleanly (422), not
    crash the server with a 500."""
    resp = client.get("/analytics/dashboard?top=not-an-int")
    assert resp.status_code == 422


def test_dashboard_unrelated_urls_do_not_cross_contaminate_totals(client):
    """Negative/edge: creating a URL without ever redirecting to it must
    not inflate total_redirects or appear with a nonzero count."""
    created = client.post("/urls", json={"url": "https://example.com/never-clicked"}).json()

    resp = client.get("/analytics/dashboard")
    body = resp.json()
    assert body["total_urls"] == 1
    assert body["total_redirects"] == 0
    assert body["top_urls"][0]["short_code"] == created["short_code"]
    assert body["top_urls"][0]["redirect_count"] == 0
    assert body["recent_events"] == []


def test_dashboard_ui_is_served_as_static_html(client):
    """The dashboard UI is served as a static page and only calls the
    real analytics API — verified here by confirming the mount responds
    with HTML that references the /analytics/dashboard endpoint."""
    resp = client.get("/dashboard/")
    assert resp.status_code == 200
    assert "text/html" in resp.headers["content-type"]
    assert "/analytics/dashboard" in resp.text

