from __future__ import annotations

from tests.conftest import login


def test_hr_can_create_a_login_and_the_new_user_can_sign_in(client, hr_user, employee_a):
    csrf = login(client, hr_user.email)

    create_resp = client.post(
        "/api/users",
        json={
            "email": "sara.new@example.com",
            "password": "NewPass123!",
            "role": "employee",
            "employee_id": employee_a.id,
        },
        headers={"X-CSRF-Token": csrf},
    )
    assert create_resp.status_code == 201, create_resp.text
    body = create_resp.json()
    assert body["employee_id"] == employee_a.id
    assert body["employee_nom"] == employee_a.full_name
    assert body["is_active"] is True

    # The freshly created account can actually log in.
    login_resp = client.post(
        "/api/auth/login", json={"email": "sara.new@example.com", "password": "NewPass123!"}
    )
    assert login_resp.status_code == 200


def test_dg_and_employee_have_no_access_to_user_management(
    client, dg_user, employee_a_user, hr_user
):
    for user in (dg_user, employee_a_user):
        csrf = login(client, user.email)
        assert client.get("/api/users").status_code == 403
        assert client.get("/api/users/employees-sans-compte").status_code == 403
        assert (
            client.post(
                "/api/users",
                json={
                    "email": "someone@example.com",
                    "password": "TestPass123!",
                    "role": "employee",
                    "employee_id": None,
                },
                headers={"X-CSRF-Token": csrf},
            ).status_code
            == 403
        )


def test_duplicate_email_rejected_cleanly(client, hr_user):
    csrf = login(client, hr_user.email)
    payload = {
        "email": "dup@example.com",
        "password": "TestPass123!",
        "role": "employee",
        "employee_id": None,
    }
    first = client.post("/api/users", json=payload, headers={"X-CSRF-Token": csrf})
    assert first.status_code == 201
    second = client.post("/api/users", json=payload, headers={"X-CSRF-Token": csrf})
    assert second.status_code == 400


def test_cannot_link_employee_that_already_has_an_account(client, hr_user, employee_a_user):
    csrf = login(client, hr_user.email)
    resp = client.post(
        "/api/users",
        json={
            "email": "second-account@example.com",
            "password": "TestPass123!",
            "role": "employee",
            "employee_id": employee_a_user.employee_id,
        },
        headers={"X-CSRF-Token": csrf},
    )
    assert resp.status_code == 400


def test_employees_sans_compte_excludes_already_linked_employees(
    client, hr_user, employee_a, employee_a_user, employee_b
):
    login(client, hr_user.email)
    resp = client.get("/api/users/employees-sans-compte")
    assert resp.status_code == 200
    body = resp.json()
    ids = {e["id"] for e in body}
    assert employee_a.id not in ids
    assert employee_b.id in ids
    # Full EmployeeLite shape, not just id/full_name/department_id — this
    # endpoint once 500'd by constructing EmployeeLite with only 3 of its
    # fields after the schema grew matricule/department_nom/etc.
    entry = next(e for e in body if e["id"] == employee_b.id)
    assert set(entry.keys()) == {
        "id",
        "full_name",
        "matricule",
        "department_id",
        "department_nom",
        "position_intitule",
        "status_libelle",
        "status_couleur",
    }


def test_self_lockout_guard_blocks_deactivating_the_last_active_hr(client, hr_user):
    csrf = login(client, hr_user.email)
    resp = client.put(
        f"/api/users/{hr_user.id}",
        json={"role": "hr", "employee_id": None, "is_active": False},
        headers={"X-CSRF-Token": csrf},
    )
    assert resp.status_code == 400
    assert "dernier compte RH" in resp.json()["detail"]


def test_self_lockout_guard_blocks_demoting_the_last_active_hr(client, hr_user):
    csrf = login(client, hr_user.email)
    resp = client.put(
        f"/api/users/{hr_user.id}",
        json={"role": "employee", "employee_id": None, "is_active": True},
        headers={"X-CSRF-Token": csrf},
    )
    assert resp.status_code == 400


def test_deactivating_hr_succeeds_when_another_active_hr_exists(client, hr_user):
    csrf = login(client, hr_user.email)
    second_hr = client.post(
        "/api/users",
        json={
            "email": "second-hr@example.com",
            "password": "TestPass123!",
            "role": "hr",
            "employee_id": None,
        },
        headers={"X-CSRF-Token": csrf},
    ).json()

    resp = client.put(
        f"/api/users/{hr_user.id}",
        json={"role": "hr", "employee_id": None, "is_active": False},
        headers={"X-CSRF-Token": csrf},
    )
    assert resp.status_code == 200
    assert resp.json()["is_active"] is False
    assert second_hr["is_active"] is True


def test_hr_can_reset_a_password_and_old_password_stops_working(client, hr_user, employee_a):
    csrf = login(client, hr_user.email)
    created = client.post(
        "/api/users",
        json={
            "email": "reset-me@example.com",
            "password": "OldPass123!",
            "role": "employee",
            "employee_id": employee_a.id,
        },
        headers={"X-CSRF-Token": csrf},
    ).json()

    reset_resp = client.post(
        f"/api/users/{created['id']}/reset-password",
        json={"password": "BrandNewPass456!"},
        headers={"X-CSRF-Token": csrf},
    )
    assert reset_resp.status_code == 200

    assert (
        client.post(
            "/api/auth/login", json={"email": "reset-me@example.com", "password": "OldPass123!"}
        ).status_code
        == 401
    )
    assert (
        client.post(
            "/api/auth/login",
            json={"email": "reset-me@example.com", "password": "BrandNewPass456!"},
        ).status_code
        == 200
    )
