from __future__ import annotations

from tests.conftest import login


def _upload_csv(client, csrf, content=b"Nom,01\nSara Alami,P\n"):
    return client.post(
        "/api/attendance/upload",
        files={"file": ("pointage.csv", content, "text/csv")},
        headers={"X-CSRF-Token": csrf},
    )


def test_hr_can_upload_and_import_and_export(client, db, hr_user, employee_a):
    from app.models import AttendanceCode

    db.add(AttendanceCode(libelle="Présent", code_court="P", couleur="#43A047"))
    db.flush()

    csrf = login(client, hr_user.email)
    upload_resp = _upload_csv(
        client, csrf, f"Nom,01\n{employee_a.prenom} {employee_a.nom},P\n".encode()
    )
    assert upload_resp.status_code == 200
    body = upload_resp.json()
    assert body["guessed_identifier_column"] == "Nom"
    assert body["guessed_day_columns"] == ["01"]

    import_resp = client.post(
        "/api/attendance/import",
        json={
            "token": body["token"],
            "identifier_column": "Nom",
            "day_columns": ["01"],
            "mois": 9,
            "annee": 2026,
        },
        headers={"X-CSRF-Token": csrf},
    )
    assert import_resp.status_code == 200
    assert import_resp.json()["nb_lignes_importees"] == 1
    assert import_resp.json()["nb_lignes_non_reconnues"] == 0

    imports_resp = client.get("/api/attendance/imports")
    assert imports_resp.status_code == 200
    assert len(imports_resp.json()) == 1

    export_resp = client.get("/api/attendance/export?mois=9&annee=2026")
    assert export_resp.status_code == 200
    assert (
        export_resp.headers["content-type"]
        == "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
    assert "attachment" in export_resp.headers["content-disposition"]
    assert export_resp.content[:2] == b"PK"


def test_import_reports_unmatched_rows(client, hr_user):
    csrf = login(client, hr_user.email)
    upload_resp = _upload_csv(client, csrf, b"Nom,01\nPersonne Inconnue,P\n")
    token = upload_resp.json()["token"]

    import_resp = client.post(
        "/api/attendance/import",
        json={
            "token": token,
            "identifier_column": "Nom",
            "day_columns": ["01"],
            "mois": 9,
            "annee": 2026,
        },
        headers={"X-CSRF-Token": csrf},
    )
    assert import_resp.status_code == 200
    assert import_resp.json()["nb_lignes_importees"] == 0
    assert import_resp.json()["nb_lignes_non_reconnues"] == 1
    assert import_resp.json()["noms_non_reconnus"] == ["Personne Inconnue"]


def test_import_rejects_unknown_or_expired_token(client, hr_user):
    csrf = login(client, hr_user.email)
    resp = client.post(
        "/api/attendance/import",
        json={
            "token": "not-a-real-token",
            "identifier_column": "Nom",
            "day_columns": ["01"],
            "mois": 9,
            "annee": 2026,
        },
        headers={"X-CSRF-Token": csrf},
    )
    assert resp.status_code == 400


def test_non_hr_cannot_upload_import_or_export(client, dg_user, employee_a_user):
    for user in (dg_user, employee_a_user):
        csrf = login(client, user.email)
        assert _upload_csv(client, csrf).status_code == 403
        assert (
            client.post(
                "/api/attendance/import",
                json={
                    "token": "x",
                    "identifier_column": "Nom",
                    "day_columns": ["01"],
                    "mois": 9,
                    "annee": 2026,
                },
                headers={"X-CSRF-Token": csrf},
            ).status_code
            == 403
        )
        assert client.get("/api/attendance/export?mois=9&annee=2026").status_code == 403
        assert client.get("/api/attendance/imports").status_code == 403


def test_hr_can_manage_attendance_codes(client, hr_user):
    csrf = login(client, hr_user.email)
    resp = client.post(
        "/api/attendance/codes",
        json={"libelle": "Mission (test)", "code_court": "MIS", "couleur": "#1E88E5"},
        headers={"X-CSRF-Token": csrf},
    )
    assert resp.status_code == 201
    code_id = resp.json()["id"]

    resp = client.put(
        f"/api/attendance/codes/{code_id}",
        json={
            "libelle": "Mission renommée",
            "code_court": "MIS",
            "couleur": "#1E88E5",
            "compte_absence": False,
            "is_active": False,
        },
        headers={"X-CSRF-Token": csrf},
    )
    assert resp.status_code == 200
    assert resp.json()["is_active"] is False


def test_non_hr_cannot_manage_attendance_codes(client, dg_user):
    csrf = login(client, dg_user.email)
    resp = client.post(
        "/api/attendance/codes",
        json={"libelle": "Interdit", "code_court": "X", "couleur": "#000000"},
        headers={"X-CSRF-Token": csrf},
    )
    assert resp.status_code == 403
