"""
test_api.py — Integration / API tests (TASK-009)

Exercises the full HTTP stack via FastAPI's TestClient, covering AC-001
through AC-010 at the API boundary, including persistence-across-restart
(AC-008/NFR persistence) and failure paths (invalid input, unknown codes,
expired codes).
"""

import pytest
from fastapi.testclient import TestClient

from app.main import create_app


@pytest.fixture
def client(tmp_path):
    db_path = str(tmp_path / "test_api.db")
    app = create_app(db_path=db_path)
    return TestClient(app)


def test_create_url_valid_returns_201(client):
    """AC-001."""
    resp = client.post("/urls", json={"url": "https://example.com/valid"})
    assert resp.status_code == 201
    body = resp.json()
    assert "short_code" in body
    assert body["short_url"] == f"/{body['short_code']}"


def test_create_url_invalid_returns_422(client):
    """AC-002."""
    resp = client.post("/urls", json={"url": "not-a-valid-url"})
    assert resp.status_code == 422


def test_create_url_missing_field_returns_422(client):
    resp = client.post("/urls", json={})
    assert resp.status_code == 422


def test_create_url_duplicate_returns_200_same_code(client):
    """AC-003: idempotent creation."""
    first = client.post("/urls", json={"url": "https://example.com/dup"})
    second = client.post("/urls", json={"url": "https://example.com/dup"})
    assert first.status_code == 201
    assert second.status_code == 200
    assert first.json()["short_code"] == second.json()["short_code"]


def test_redirect_known_code_returns_302(client):
    """AC-004."""
    created = client.post("/urls", json={"url": "https://example.com/redirect-me"})
    short_code = created.json()["short_code"]
    resp = client.get(f"/{short_code}", follow_redirects=False)
    assert resp.status_code == 302
    assert resp.headers["location"] == "https://example.com/redirect-me"


def test_redirect_unknown_code_returns_404(client):
    """AC-005."""
    resp = client.get("/doesnotexist", follow_redirects=False)
    assert resp.status_code == 404


def test_redirect_expired_code_returns_410(client):
    """AC-006, verified at the HTTP layer (not just the service layer)."""
    from datetime import datetime, timedelta, timezone

    url_service = client.app.state.url_service
    past = (datetime.now(timezone.utc) - timedelta(days=1)).isoformat()
    record = url_service._url_repo.insert(
        "expapi1", "https://example.com/expired-via-api", past, expires_at=past
    )
    resp = client.get(f"/{record.short_code}", follow_redirects=False)
    assert resp.status_code == 410


def test_analytics_unknown_code_returns_404(client):
    resp = client.get("/urls/doesnotexist/analytics")
    assert resp.status_code == 404


def test_analytics_reflects_redirect_count(client):
    """AC-007 + AC-008."""
    created = client.post("/urls", json={"url": "https://example.com/track-me"})
    short_code = created.json()["short_code"]

    client.get(f"/{short_code}", follow_redirects=False)
    client.get(f"/{short_code}", follow_redirects=False)

    analytics = client.get(f"/urls/{short_code}/analytics")
    assert analytics.status_code == 200
    body = analytics.json()
    assert body["redirect_count"] == 2
    assert body["short_code"] == short_code
    assert body["last_accessed_at"] is not None


def test_persistence_across_new_connection(tmp_path):
    """AC-008 / NFR-004: mapping and analytics survive a simulated process
    restart (new create_app() call against the same on-disk database file)."""
    db_path = str(tmp_path / "persist_test.db")

    app1 = create_app(db_path=db_path)
    client1 = TestClient(app1)
    created = client1.post("/urls", json={"url": "https://example.com/persisted"})
    short_code = created.json()["short_code"]
    client1.get(f"/{short_code}", follow_redirects=False)  # one redirect before "restart"

    # Simulate a process restart: brand-new app/connection, same DB file.
    app2 = create_app(db_path=db_path)
    client2 = TestClient(app2)

    resp = client2.get(f"/{short_code}", follow_redirects=False)
    assert resp.status_code == 302
    assert resp.headers["location"] == "https://example.com/persisted"

    analytics = client2.get(f"/urls/{short_code}/analytics")
    assert analytics.json()["redirect_count"] == 2  # 1 before + 1 after restart


def test_error_response_has_detail_field(client):
    """Error handling: 404 responses expose a `detail` field (ErrorResponse schema)."""
    resp = client.get("/doesnotexist", follow_redirects=False)
    body = resp.json()
    assert "detail" in body


