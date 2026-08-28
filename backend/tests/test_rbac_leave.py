from __future__ import annotations

from tests.conftest import grant_balance, login


def _create_request(
    client, db, csrf, employee_id, leave_type_id, date_debut="2026-09-07", date_fin="2026-09-11"
):
    # Fund a generous balance first: these tests are about RBAC/workflow, not
    # balance sufficiency (that has its own tests in test_leave_service.py) —
    # without this, leave_service._check_solde_suffisant would reject almost
    # every one of these requests outright.
    grant_balance(db, employee_id, leave_type_id, int(date_debut[:4]))
    return client.post(
        "/api/leave-requests",
        json={
            "employee_id": employee_id,
            "leave_type_id": leave_type_id,
            "date_debut": date_debut,
            "date_fin": date_fin,
            "commentaire": None,
        },
        headers={"X-CSRF-Token": csrf},
    )


# ------------------------------------------------------------------ DG ----


def test_dg_cannot_create_leave_request(client, db, dg_user, employee_a, leave_type):
    csrf = login(client, dg_user.email)
    resp = _create_request(client, db, csrf, employee_a.id, leave_type.id)
    assert resp.status_code == 403


def test_dg_cannot_approve_or_reject(client, db, hr_user, dg_user, employee_a, leave_type):
    hr_csrf = login(client, hr_user.email)
    request_id = _create_request(client, db, hr_csrf, employee_a.id, leave_type.id).json()["id"]

    dg_csrf = login(client, dg_user.email)
    assert (
        client.post(
            f"/api/leave-requests/{request_id}/approve", json={}, headers={"X-CSRF-Token": dg_csrf}
        ).status_code
        == 403
    )
    assert (
        client.post(
            f"/api/leave-requests/{request_id}/reject",
            json={"comment": "x"},
            headers={"X-CSRF-Token": dg_csrf},
        ).status_code
        == 403
    )


def test_dg_can_read_all_requests_company_wide(
    client, db, hr_user, dg_user, employee_a, employee_b, leave_type
):
    hr_csrf = login(client, hr_user.email)
    _create_request(client, db, hr_csrf, employee_a.id, leave_type.id, "2026-09-07", "2026-09-11")
    _create_request(client, db, hr_csrf, employee_b.id, leave_type.id, "2026-10-05", "2026-10-06")

    login(client, dg_user.email)
    resp = client.get("/api/leave-requests")
    assert resp.status_code == 200
    employee_ids = {r["employee_id"] for r in resp.json()}
    assert employee_ids == {employee_a.id, employee_b.id}


# ----------------------------------------------------------------- HR ----


def test_hr_can_create_on_anyones_behalf_and_approve(client, db, hr_user, employee_a, leave_type):
    hr_csrf = login(client, hr_user.email)
    resp = _create_request(client, db, hr_csrf, employee_a.id, leave_type.id)
    assert resp.status_code == 201
    request_id = resp.json()["id"]

    resp = client.post(
        f"/api/leave-requests/{request_id}/approve",
        json={"comment": "OK"},
        headers={"X-CSRF-Token": hr_csrf},
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "approved"


def test_hr_full_write_access_on_holidays(client, hr_user):
    csrf = login(client, hr_user.email)
    resp = client.post(
        "/api/holidays",
        json={"date": "2026-11-06", "libelle": "Marche Verte"},
        headers={"X-CSRF-Token": csrf},
    )
    assert resp.status_code == 201


def test_non_hr_cannot_write_holidays(client, dg_user, employee_a_user):
    for user in (dg_user, employee_a_user):
        csrf = login(client, user.email)
        resp = client.post(
            "/api/holidays",
            json={"date": "2026-11-06", "libelle": "Marche Verte"},
            headers={"X-CSRF-Token": csrf},
        )
        assert resp.status_code == 403


def test_hr_can_generate_fixed_holidays_idempotently(client, hr_user):
    csrf = login(client, hr_user.email)
    resp = client.post("/api/holidays/generate-fixed?annee=2030", headers={"X-CSRF-Token": csrf})
    assert resp.status_code == 200
    first_count = len(resp.json())
    assert first_count == 9

    # Calling again must not create duplicates.
    resp = client.post("/api/holidays/generate-fixed?annee=2030", headers={"X-CSRF-Token": csrf})
    assert resp.status_code == 200
    assert len(resp.json()) == first_count


def test_non_hr_cannot_generate_fixed_holidays(client, dg_user):
    csrf = login(client, dg_user.email)
    resp = client.post("/api/holidays/generate-fixed?annee=2030", headers={"X-CSRF-Token": csrf})
    assert resp.status_code == 403


# ----------------------------------------------------------- Employee ----


def test_employee_cannot_view_another_employees_leave_request(
    client, db, hr_user, employee_a, employee_b_user, leave_type
):
    hr_csrf = login(client, hr_user.email)
    request_id = _create_request(client, db, hr_csrf, employee_a.id, leave_type.id).json()["id"]

    login(client, employee_b_user.email)
    resp = client.get(f"/api/leave-requests/{request_id}")
    assert resp.status_code == 404


def test_employee_cannot_view_another_employees_balance(
    client, hr_user, employee_a, employee_b_user, leave_type
):
    hr_csrf = login(client, hr_user.email)
    client.put(
        "/api/leave-balances",
        json={
            "employee_id": employee_a.id,
            "leave_type_id": leave_type.id,
            "annee": 2026,
            "jours_acquis": 18,
        },
        headers={"X-CSRF-Token": hr_csrf},
    )

    login(client, employee_b_user.email)
    # Employee role has no employee_id query param override capability at all
    # for another employee's data — balances endpoint forces self.
    resp = client.get(f"/api/leave-balances?annee=2026&employee_id={employee_a.id}")
    assert resp.status_code == 200
    returned_employee_ids = {b["employee_id"] for b in resp.json()}
    assert returned_employee_ids == {employee_b_user.employee_id}


def test_employee_list_endpoint_forces_own_employee_id(
    client, db, hr_user, employee_a, employee_b, employee_b_user, leave_type
):
    hr_csrf = login(client, hr_user.email)
    _create_request(client, db, hr_csrf, employee_a.id, leave_type.id)
    _create_request(client, db, hr_csrf, employee_b.id, leave_type.id)

    login(client, employee_b_user.email)
    resp = client.get(f"/api/leave-requests?employee_id={employee_a.id}")
    assert resp.status_code == 200
    employee_ids = {r["employee_id"] for r in resp.json()}
    assert employee_ids == {employee_b.id}


def test_employee_without_responsable_can_self_submit(client, db, employee_a_user, leave_type):
    csrf = login(client, employee_a_user.email)
    resp = _create_request(client, db, csrf, employee_a_user.employee_id, leave_type.id)
    assert resp.status_code == 201


def test_employee_cannot_submit_for_a_colleague_without_responsable_capability(
    client, db, employee_a_user, employee_b, leave_type
):
    csrf = login(client, employee_a_user.email)
    resp = _create_request(client, db, csrf, employee_b.id, leave_type.id)
    assert resp.status_code == 403


def test_employee_in_department_with_responsable_cannot_self_submit(
    client, db, colleague_under_responsable_user, leave_type
):
    csrf = login(client, colleague_under_responsable_user.email)
    resp = _create_request(
        client, db, csrf, colleague_under_responsable_user.employee_id, leave_type.id
    )
    assert resp.status_code == 403


def test_leave_responsable_can_submit_for_own_department_colleague(
    client, db, responsable_user, colleague_under_responsable, leave_type
):
    csrf = login(client, responsable_user.email)
    resp = _create_request(client, db, csrf, colleague_under_responsable.id, leave_type.id)
    assert resp.status_code == 201


def test_leave_responsable_can_submit_for_self(client, db, responsable_user, leave_type):
    csrf = login(client, responsable_user.email)
    resp = _create_request(client, db, csrf, responsable_user.employee_id, leave_type.id)
    assert resp.status_code == 201


def test_leave_responsable_cannot_submit_for_other_department(
    client, db, responsable_user, employee_other_dept, leave_type
):
    csrf = login(client, responsable_user.email)
    resp = _create_request(client, db, csrf, employee_other_dept.id, leave_type.id)
    assert resp.status_code == 403


def test_leave_responsable_cannot_approve_or_reject(
    client, db, hr_user, responsable_user, colleague_under_responsable, leave_type
):
    resp_csrf = login(client, responsable_user.email)
    request_id = _create_request(
        client, db, resp_csrf, colleague_under_responsable.id, leave_type.id
    ).json()["id"]

    # still logged in as the responsable, not HR
    resp = client.post(
        f"/api/leave-requests/{request_id}/approve", json={}, headers={"X-CSRF-Token": resp_csrf}
    )
    assert resp.status_code == 403


def test_only_hr_can_approve_regardless_of_who_submitted(
    client, db, hr_user, responsable_user, colleague_under_responsable, leave_type
):
    resp_csrf = login(client, responsable_user.email)
    request_id = _create_request(
        client, db, resp_csrf, colleague_under_responsable.id, leave_type.id
    ).json()["id"]

    hr_csrf = login(client, hr_user.email)
    resp = client.post(
        f"/api/leave-requests/{request_id}/approve",
        json={"comment": "OK"},
        headers={"X-CSRF-Token": hr_csrf},
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "approved"


def test_certificate_forbidden_before_approval_ok_after_for_owner(
    client, db, hr_user, employee_a_user, leave_type
):
    csrf = login(client, employee_a_user.email)
    request_id = _create_request(
        client, db, csrf, employee_a_user.employee_id, leave_type.id
    ).json()["id"]

    resp = client.get(f"/api/leave-requests/{request_id}/certificate")
    assert resp.status_code == 403

    hr_csrf = login(client, hr_user.email)
    client.post(
        f"/api/leave-requests/{request_id}/approve",
        json={"comment": "OK"},
        headers={"X-CSRF-Token": hr_csrf},
    )

    login(client, employee_a_user.email)
    resp = client.get(f"/api/leave-requests/{request_id}/certificate")
    assert resp.status_code == 200


def test_notification_created_only_for_leave_owner_on_approve(
    client, db, hr_user, responsable_user, colleague_under_responsable, leave_type
):
    resp_csrf = login(client, responsable_user.email)
    request_id = _create_request(
        client, db, resp_csrf, colleague_under_responsable.id, leave_type.id
    ).json()["id"]

    hr_csrf = login(client, hr_user.email)
    client.post(
        f"/api/leave-requests/{request_id}/approve",
        json={"comment": "OK"},
        headers={"X-CSRF-Token": hr_csrf},
    )

    # The submitter (responsable) gets nothing; only the leave owner does.
    login(client, responsable_user.email)
    assert client.get("/api/notifications").json() == []


# --------------------------------------------------------- solde checks --


def test_cannot_submit_request_exceeding_solde(client, db, employee_a_user, leave_type):
    grant_balance(db, employee_a_user.employee_id, leave_type.id, 2026, jours=3)
    csrf = login(client, employee_a_user.email)
    # Mon 2026-09-07 .. Fri 2026-09-11 = 5 jours ouvrés, only 3 available.
    resp = client.post(
        "/api/leave-requests",
        json={
            "employee_id": employee_a_user.employee_id,
            "leave_type_id": leave_type.id,
            "date_debut": "2026-09-07",
            "date_fin": "2026-09-11",
            "commentaire": None,
        },
        headers={"X-CSRF-Token": csrf},
    )
    assert resp.status_code == 400
    assert "Solde insuffisant" in resp.json()["detail"]


def test_can_submit_request_exactly_matching_solde(client, db, employee_a_user, leave_type):
    grant_balance(db, employee_a_user.employee_id, leave_type.id, 2026, jours=5)
    csrf = login(client, employee_a_user.email)
    resp = client.post(
        "/api/leave-requests",
        json={
            "employee_id": employee_a_user.employee_id,
            "leave_type_id": leave_type.id,
            "date_debut": "2026-09-07",
            "date_fin": "2026-09-11",
            "commentaire": None,
        },
        headers={"X-CSRF-Token": csrf},
    )
    assert resp.status_code == 201


def test_solde_check_skipped_for_non_deductible_leave_type(client, db, employee_a_user):
    from app.models import LeaveType

    sans_solde = LeaveType(libelle="Sans solde (test)", couleur="#000000", deduit_du_solde=False)
    db.add(sans_solde)
    db.flush()
    # No balance funded at all — should still succeed since this type never
    # draws from any solde.
    csrf = login(client, employee_a_user.email)
    resp = client.post(
        "/api/leave-requests",
        json={
            "employee_id": employee_a_user.employee_id,
            "leave_type_id": sans_solde.id,
            "date_debut": "2026-09-07",
            "date_fin": "2026-09-11",
            "commentaire": None,
        },
        headers={"X-CSRF-Token": csrf},
    )
    assert resp.status_code == 201


def test_hr_cannot_manually_set_balance_for_accrual_legal_type(client, db, hr_user, employee_a):
    from app.models import LeaveType

    # `db` is the exact session the API's get_db override yields (see the
    # `client` fixture), so a row added here is visible to the request below.
    conge_paye = LeaveType(
        libelle="Congé payé (test)", couleur="#000000", deduit_du_solde=True, accrual_legal=True
    )
    db.add(conge_paye)
    db.flush()

    csrf = login(client, hr_user.email)
    resp = client.put(
        "/api/leave-balances",
        json={
            "employee_id": employee_a.id,
            "leave_type_id": conge_paye.id,
            "annee": 2026,
            "jours_acquis": 30,
        },
        headers={"X-CSRF-Token": csrf},
    )
    assert resp.status_code == 400


# ------------------------------------------------------------- /employees --


def test_hr_can_list_any_department_employees(client, hr_user, colleague_under_responsable):
    login(client, hr_user.email)
    resp = client.get(f"/api/employees?department_id={colleague_under_responsable.department_id}")
    assert resp.status_code == 200
    assert any(e["id"] == colleague_under_responsable.id for e in resp.json())


def test_responsable_can_list_own_department_employees(
    client, responsable_user, colleague_under_responsable
):
    login(client, responsable_user.email)
    resp = client.get(f"/api/employees?department_id={colleague_under_responsable.department_id}")
    assert resp.status_code == 200


def test_regular_employee_cannot_list_department_employees(client, employee_a_user, employee_b):
    login(client, employee_a_user.email)
    resp = client.get(f"/api/employees?department_id={employee_b.department_id}")
    assert resp.status_code == 403


# ------------------------------------------------------ leave-responsable --


def test_hr_can_set_and_clear_department_leave_responsable(
    client, hr_user, colleague_under_responsable, department_with_responsable
):
    csrf = login(client, hr_user.email)

    resp = client.patch(
        f"/api/departments/{department_with_responsable.id}/leave-responsable",
        json={"employee_id": colleague_under_responsable.id},
        headers={"X-CSRF-Token": csrf},
    )
    assert resp.status_code == 200
    assert resp.json()["leave_responsable_employee_id"] == colleague_under_responsable.id

    resp = client.patch(
        f"/api/departments/{department_with_responsable.id}/leave-responsable",
        json={"employee_id": None},
        headers={"X-CSRF-Token": csrf},
    )
    assert resp.status_code == 200
    assert resp.json()["leave_responsable_employee_id"] is None


def test_cannot_set_responsable_to_employee_outside_department(
    client, hr_user, department_with_responsable, employee_other_dept
):
    csrf = login(client, hr_user.email)
    resp = client.patch(
        f"/api/departments/{department_with_responsable.id}/leave-responsable",
        json={"employee_id": employee_other_dept.id},
        headers={"X-CSRF-Token": csrf},
    )
    assert resp.status_code == 400


def test_non_hr_cannot_set_leave_responsable(
    client, dg_user, department_with_responsable, colleague_under_responsable
):
    csrf = login(client, dg_user.email)
    resp = client.patch(
        f"/api/departments/{department_with_responsable.id}/leave-responsable",
        json={"employee_id": colleague_under_responsable.id},
        headers={"X-CSRF-Token": csrf},
    )
    assert resp.status_code == 403
