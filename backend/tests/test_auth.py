from __future__ import annotations

from tests.conftest import login


def test_login_success_sets_cookies(client, hr_user):
    resp = client.post("/api/auth/login", json={"email": hr_user.email, "password": "TestPass123!"})
    assert resp.status_code == 200
    assert resp.json()["role"] == "hr"
    assert client.cookies.get("ariha_session") is not None
    assert client.cookies.get("csrf_token") is not None


def test_login_wrong_password_fails(client, hr_user):
    resp = client.post("/api/auth/login", json={"email": hr_user.email, "password": "wrong"})
    assert resp.status_code == 401


def test_login_unknown_email_fails(client):
    resp = client.post(
        "/api/auth/login", json={"email": "nobody@test.example", "password": "whatever"}
    )
    assert resp.status_code == 401


def test_me_requires_session(client):
    resp = client.get("/api/auth/me")
    assert resp.status_code == 401


def test_me_returns_current_user_after_login(client, hr_user):
    login(client, hr_user.email)
    resp = client.get("/api/auth/me")
    assert resp.status_code == 200
    assert resp.json()["email"] == hr_user.email


def test_logout_invalidates_session(client, hr_user):
    csrf = login(client, hr_user.email)
    resp = client.post("/api/auth/logout", headers={"X-CSRF-Token": csrf})
    assert resp.status_code == 200

    resp = client.get("/api/auth/me")
    assert resp.status_code == 401


def test_mutating_request_without_csrf_header_is_rejected(client, hr_user):
    login(client, hr_user.email)
    resp = client.post("/api/holidays", json={"date": "2026-12-25", "libelle": "Test"})
    assert resp.status_code == 403


def test_mutating_request_with_wrong_csrf_header_is_rejected(client, hr_user):
    login(client, hr_user.email)
    resp = client.post(
        "/api/holidays",
        json={"date": "2026-12-25", "libelle": "Test"},
        headers={"X-CSRF-Token": "not-the-real-token"},
    )
    assert resp.status_code == 403
