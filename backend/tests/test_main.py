from __future__ import annotations


def test_health_endpoint(client):
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}


def test_security_headers_present_on_every_response(client):
    resp = client.get("/health")
    assert resp.headers["x-content-type-options"] == "nosniff"
    assert resp.headers["x-frame-options"] == "DENY"
    assert resp.headers["referrer-policy"] == "strict-origin-when-cross-origin"


def test_hsts_header_absent_outside_production(client):
    # The test app runs with ENV=development (see conftest) — HSTS over
    # plain HTTP would be a no-op at best, so it's only sent in production.
    resp = client.get("/health")
    assert "strict-transport-security" not in resp.headers
