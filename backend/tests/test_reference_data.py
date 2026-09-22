from __future__ import annotations

from tests.conftest import login


def test_hr_can_create_update_and_deactivate_department(client, hr_user):
    csrf = login(client, hr_user.email)
    create_resp = client.post(
        "/api/departments",
        json={"nom": "Qualité", "description": "Contrôle qualité produits"},
        headers={"X-CSRF-Token": csrf},
    )
    assert create_resp.status_code == 201, create_resp.text
    dept = create_resp.json()
    assert dept["is_active"] is True

    update_resp = client.put(
        f"/api/departments/{dept['id']}",
        json={"nom": "Qualité & Conformité", "description": None, "is_active": True},
        headers={"X-CSRF-Token": csrf},
    )
    assert update_resp.status_code == 200
    assert update_resp.json()["nom"] == "Qualité & Conformité"

    # Deactivating removes it from the default (active-only) list...
    deactivate_resp = client.put(
        f"/api/departments/{dept['id']}",
        json={"nom": "Qualité & Conformité", "description": None, "is_active": False},
        headers={"X-CSRF-Token": csrf},
    )
    assert deactivate_resp.status_code == 200
    listed = client.get("/api/departments").json()
    assert dept["id"] not in {d["id"] for d in listed}

    # ...but HR can still see it via include_inactive.
    listed_all = client.get("/api/departments?include_inactive=true").json()
    assert dept["id"] in {d["id"] for d in listed_all}


def test_department_name_must_be_unique(client, hr_user):
    csrf = login(client, hr_user.email)
    client.post("/api/departments", json={"nom": "Doublon Test"}, headers={"X-CSRF-Token": csrf})
    resp = client.post(
        "/api/departments", json={"nom": "Doublon Test"}, headers={"X-CSRF-Token": csrf}
    )
    assert resp.status_code == 400


def test_dg_and_employee_cannot_write_departments(client, hr_user, dg_user, employee_a_user):
    csrf = login(client, hr_user.email)
    dept_id = client.post(
        "/api/departments", json={"nom": "RBAC Dept Test"}, headers={"X-CSRF-Token": csrf}
    ).json()["id"]

    for user in (dg_user, employee_a_user):
        user_csrf = login(client, user.email)
        assert (
            client.post(
                "/api/departments",
                json={"nom": "Should Fail"},
                headers={"X-CSRF-Token": user_csrf},
            ).status_code
            == 403
        )
        assert (
            client.put(
                f"/api/departments/{dept_id}",
                json={"nom": "Should Fail", "is_active": True},
                headers={"X-CSRF-Token": user_csrf},
            ).status_code
            == 403
        )


def test_hr_can_create_update_and_deactivate_position(client, hr_user, department_no_responsable):
    csrf = login(client, hr_user.email)
    create_resp = client.post(
        "/api/positions",
        json={"intitule": "Contrôleur Qualité", "department_id": department_no_responsable.id},
        headers={"X-CSRF-Token": csrf},
    )
    assert create_resp.status_code == 201, create_resp.text
    position = create_resp.json()
    assert position["is_active"] is True

    update_resp = client.put(
        f"/api/positions/{position['id']}",
        json={"intitule": "Contrôleur Qualité Senior", "department_id": None, "is_active": True},
        headers={"X-CSRF-Token": csrf},
    )
    assert update_resp.status_code == 200
    assert update_resp.json()["intitule"] == "Contrôleur Qualité Senior"
    assert update_resp.json()["department_id"] is None

    deactivate_resp = client.put(
        f"/api/positions/{position['id']}",
        json={"intitule": "Contrôleur Qualité Senior", "department_id": None, "is_active": False},
        headers={"X-CSRF-Token": csrf},
    )
    assert deactivate_resp.status_code == 200
    listed = client.get("/api/positions").json()
    assert position["id"] not in {p["id"] for p in listed}

    listed_all = client.get("/api/positions?include_inactive=true").json()
    assert position["id"] in {p["id"] for p in listed_all}


def test_dg_and_employee_cannot_write_positions(client, hr_user, dg_user, employee_a_user):
    for user in (dg_user, employee_a_user):
        csrf = login(client, user.email)
        assert (
            client.post(
                "/api/positions",
                json={"intitule": "Should Fail"},
                headers={"X-CSRF-Token": csrf},
            ).status_code
            == 403
        )
