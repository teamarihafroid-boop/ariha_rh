from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal

from markupsafe import escape

from app.models import Employee
from app.models.enums import UserRole
from app.routers.employees import FICHE_DOCUMENT_CHECKLIST
from app.routers.employees import templates as employee_templates
from tests.conftest import _make_user, login

MINIMAL_EMPLOYEE_PAYLOAD = {
    "matricule": None,
    "nom": "Nouveau",
    "prenom": "Employe",
    "nom_arabe": None,
    "prenom_arabe": None,
    "date_naissance": None,
    "date_embauche": "2024-01-15",
    "date_sortie": None,
    "date_fin_periode_essai": None,
    "email": None,
    "telephone": None,
    "ville": None,
    "adresse": None,
    "cin": None,
    "cnss": None,
    "type_contrat": None,
    "categorie_professionnelle": None,
    "salaire_base": None,
    "salaire_net": None,
    "notes": None,
    "department_id": None,
    "position_id": None,
    "status_id": None,
    "manager_id": None,
}


def test_hr_can_create_update_and_deactivate_employee(
    client, db, hr_user, department_no_responsable, active_status, inactive_status
):
    csrf = login(client, hr_user.email)
    payload = {
        **MINIMAL_EMPLOYEE_PAYLOAD,
        "department_id": department_no_responsable.id,
        "status_id": active_status.id,
        "matricule": "M-100",
    }
    create_resp = client.post("/api/employees", json=payload, headers={"X-CSRF-Token": csrf})
    assert create_resp.status_code == 201, create_resp.text
    employee_id = create_resp.json()["id"]
    assert create_resp.json()["matricule"] == "M-100"
    assert create_resp.json()["status_libelle"] == "Actif"

    update_payload = {**payload, "matricule": "M-100", "ville": "Casablanca"}
    update_resp = client.put(
        f"/api/employees/{employee_id}", json=update_payload, headers={"X-CSRF-Token": csrf}
    )
    assert update_resp.status_code == 200
    assert update_resp.json()["ville"] == "Casablanca"

    deactivate_resp = client.delete(
        f"/api/employees/{employee_id}?date_sortie=2026-09-05", headers={"X-CSRF-Token": csrf}
    )
    assert deactivate_resp.status_code == 200
    body = deactivate_resp.json()
    assert body["date_sortie"] == "2026-09-05"
    assert body["status_libelle"] == "Sorti"

    # Nothing is physically deleted: the row is still fetchable.
    still_there = client.get(f"/api/employees/{employee_id}")
    assert still_there.status_code == 200


def test_matricule_collision_returns_clean_400(client, hr_user, employee_a):
    csrf = login(client, hr_user.email)
    client.put(
        f"/api/employees/{employee_a.id}",
        json={**MINIMAL_EMPLOYEE_PAYLOAD, "matricule": "DUPLICATE"},
        headers={"X-CSRF-Token": csrf},
    )
    resp = client.post(
        "/api/employees",
        json={**MINIMAL_EMPLOYEE_PAYLOAD, "matricule": "DUPLICATE"},
        headers={"X-CSRF-Token": csrf},
    )
    assert resp.status_code == 400
    assert "matricule" in resp.json()["detail"].lower()


def test_cannot_be_own_manager(client, hr_user, employee_a):
    csrf = login(client, hr_user.email)
    resp = client.put(
        f"/api/employees/{employee_a.id}",
        json={**MINIMAL_EMPLOYEE_PAYLOAD, "manager_id": employee_a.id},
        headers={"X-CSRF-Token": csrf},
    )
    assert resp.status_code == 400


def test_list_employees_includes_scan_context(
    client, hr_user, employee_a, department_no_responsable, active_status
):
    """The roster list needs to be scannable without opening each fiche —
    department/poste/statut must ride along, not just the name."""
    csrf = login(client, hr_user.email)
    resp = client.put(
        f"/api/employees/{employee_a.id}",
        json={
            **MINIMAL_EMPLOYEE_PAYLOAD,
            "matricule": "SCAN-001",
            "department_id": department_no_responsable.id,
            "status_id": active_status.id,
        },
        headers={"X-CSRF-Token": csrf},
    )
    assert resp.status_code == 200

    resp = client.get("/api/employees")
    assert resp.status_code == 200
    row = next(e for e in resp.json() if e["id"] == employee_a.id)
    assert row["matricule"] == "SCAN-001"
    assert row["department_nom"] == department_no_responsable.nom
    assert row["status_libelle"] == active_status.libelle
    assert row["status_couleur"] == active_status.couleur


def test_dg_is_read_only_on_employees(client, dg_user, employee_a):
    csrf = login(client, dg_user.email)
    assert client.get("/api/employees").status_code == 200
    assert client.get(f"/api/employees/{employee_a.id}").status_code == 200
    assert client.get("/api/employees/orgchart").status_code == 200

    assert (
        client.post(
            "/api/employees", json=MINIMAL_EMPLOYEE_PAYLOAD, headers={"X-CSRF-Token": csrf}
        ).status_code
        == 403
    )
    assert (
        client.put(
            f"/api/employees/{employee_a.id}",
            json=MINIMAL_EMPLOYEE_PAYLOAD,
            headers={"X-CSRF-Token": csrf},
        ).status_code
        == 403
    )
    assert (
        client.delete(f"/api/employees/{employee_a.id}", headers={"X-CSRF-Token": csrf}).status_code
        == 403
    )
    assert (
        client.post(
            f"/api/employees/{employee_a.id}/contacts-urgence",
            json={"nom": "X", "lien": None, "telephone": "0600000000"},
            headers={"X-CSRF-Token": csrf},
        ).status_code
        == 403
    )
    assert (
        client.post(
            f"/api/employees/{employee_a.id}/periode-essai/evaluations",
            json={"date_evaluation": "2026-09-05"},
            headers={"X-CSRF-Token": csrf},
        ).status_code
        == 403
    )


def test_employee_sees_only_own_record(
    client, employee_a_user, employee_b_user, employee_a, employee_b
):
    login(client, employee_a_user.email)

    me_resp = client.get("/api/employees/me")
    assert me_resp.status_code == 200
    assert me_resp.json()["id"] == employee_a.id

    own_resp = client.get(f"/api/employees/{employee_a.id}")
    assert own_resp.status_code == 200

    other_resp = client.get(f"/api/employees/{employee_b.id}")
    assert other_resp.status_code == 404

    own_pdf = client.get("/api/employees/me/fiche")
    assert own_pdf.status_code == 200
    assert own_pdf.headers["content-type"] == "application/pdf"
    assert own_pdf.content.startswith(b"%PDF")

    other_pdf = client.get(f"/api/employees/{employee_b.id}/fiche")
    assert other_pdf.status_code == 404


def test_employee_role_without_linked_record_gets_404_on_me(client, db):
    orphan_user = _make_user(db, "orphan@test.example", UserRole.EMPLOYEE, employee=None)
    login(client, orphan_user.email)
    resp = client.get("/api/employees/me")
    assert resp.status_code == 404


def test_orgchart_reachable_by_all_three_roles(client, hr_user, dg_user, employee_a_user):
    for email in (hr_user.email, dg_user.email, employee_a_user.email):
        login(client, email)
        assert client.get("/api/employees/orgchart").status_code == 200


def test_emergency_contact_write_is_hr_only(client, hr_user, employee_a_user, employee_a):
    csrf = login(client, employee_a_user.email)
    resp = client.post(
        f"/api/employees/{employee_a.id}/contacts-urgence",
        json={"nom": "Contact", "lien": "Conjoint", "telephone": "0600000000"},
        headers={"X-CSRF-Token": csrf},
    )
    assert resp.status_code == 403

    csrf = login(client, hr_user.email)
    resp = client.post(
        f"/api/employees/{employee_a.id}/contacts-urgence",
        json={"nom": "Contact", "lien": "Conjoint", "telephone": "0600000000"},
        headers={"X-CSRF-Token": csrf},
    )
    assert resp.status_code == 201
    contact_id = resp.json()["emergency_contacts"][0]["id"]

    delete_resp = client.delete(
        f"/api/employees/{employee_a.id}/contacts-urgence/{contact_id}",
        headers={"X-CSRF-Token": csrf},
    )
    assert delete_resp.status_code == 200
    assert delete_resp.json()["emergency_contacts"] == []


def test_equipment_write_is_hr_only(client, hr_user, employee_a_user, employee_a):
    csrf = login(client, employee_a_user.email)
    resp = client.post(
        f"/api/employees/{employee_a.id}/equipement",
        json={"libelle": "Téléphone"},
        headers={"X-CSRF-Token": csrf},
    )
    assert resp.status_code == 403

    csrf = login(client, hr_user.email)
    resp = client.post(
        f"/api/employees/{employee_a.id}/equipement",
        json={"libelle": "Téléphone"},
        headers={"X-CSRF-Token": csrf},
    )
    assert resp.status_code == 201
    assert [e["libelle"] for e in resp.json()["equipements"]] == ["Téléphone"]

    # Custom items not on the frontend's standard list work the same way —
    # the backend has no fixed vocabulary, it just stores whatever RH sends.
    resp = client.post(
        f"/api/employees/{employee_a.id}/equipement",
        json={"libelle": "Perceuse sans fil"},
        headers={"X-CSRF-Token": csrf},
    )
    assert resp.status_code == 201
    item_ids = {e["id"]: e["libelle"] for e in resp.json()["equipements"]}
    assert set(item_ids.values()) == {"Téléphone", "Perceuse sans fil"}

    telephone_id = next(i for i, libelle in item_ids.items() if libelle == "Téléphone")
    delete_resp = client.delete(
        f"/api/employees/{employee_a.id}/equipement/{telephone_id}",
        headers={"X-CSRF-Token": csrf},
    )
    assert delete_resp.status_code == 200
    assert [e["libelle"] for e in delete_resp.json()["equipements"]] == ["Perceuse sans fil"]


def test_probation_evaluation_write_is_hr_only_and_updates_date_fin(
    client, hr_user, employee_a_user, employee_a
):
    csrf = login(client, employee_a_user.email)
    resp = client.post(
        f"/api/employees/{employee_a.id}/periode-essai/evaluations",
        json={"date_evaluation": "2026-09-05", "decision": "Confirmé"},
        headers={"X-CSRF-Token": csrf},
    )
    assert resp.status_code == 403

    csrf = login(client, hr_user.email)
    resp = client.post(
        f"/api/employees/{employee_a.id}/periode-essai/evaluations",
        json={
            "date_evaluation": "2026-09-05",
            "decision": "Prolongé",
            "nouvelle_date_fin": "2026-12-01",
            "avis_rh": "Prolongation de 3 mois",
            "evaluateur_rh": "Responsable RH",
        },
        headers={"X-CSRF-Token": csrf},
    )
    assert resp.status_code == 201
    body = resp.json()
    assert body["date_fin_periode_essai"] == "2026-12-01"
    assert len(body["probation_evaluations"]) == 1
    assert body["probation_evaluations"][0]["avis_dg"] is None


def test_employee_sheet_template_matches_paper_fiche_layout(
    db, department_no_responsable, active_status
):
    employee = Employee(
        nom="Sensible",
        prenom="Fiche",
        department_id=department_no_responsable.id,
        status_id=active_status.id,
        cin="AB123456",
        cnss="9988776",
        salaire_base=Decimal("8000.00"),
    )
    db.add(employee)
    db.flush()

    template = employee_templates.env.get_template("employee_sheet.html")
    html = template.render(
        employee=employee,
        logo_data_uri="",
        generated_at="01/01/2026",
        document_checklist=FICHE_DOCUMENT_CHECKLIST,
        uploaded_types={"CIN"},
    )

    # CIN is part of the physical fiche's "Informations générales" box, but
    # CNSS/salaire never appeared on the paper form and are no longer part
    # of this document at all.
    assert "AB123456" in html
    assert "9988776" not in html
    assert "8000.00" not in html

    # Every checklist item renders its own box; only the uploaded type is
    # marked. Jinja autoescapes apostrophes to "&#39;", so compare escaped.
    for doc_type in FICHE_DOCUMENT_CHECKLIST:
        assert str(escape(doc_type)) in html
    assert html.count('class="checkbox"><span>X</span>') == 1


def test_hr_sees_probation_alert_before_deadline(client, db, hr_user, employee_a):
    employee_a.date_fin_periode_essai = datetime.now(UTC).date() + timedelta(days=5)
    db.flush()
    login(client, hr_user.email)
    resp = client.get("/api/employees/periode-essai/alertes")
    assert resp.status_code == 200
    alert = next(a for a in resp.json() if a["employee_id"] == employee_a.id)
    assert alert["urgence"] == "semaine"
    assert alert["a_evaluation_complete"] is False


def test_hr_can_upload_download_and_delete_employee_document(client, hr_user, employee_a):
    csrf = login(client, hr_user.email)

    upload_resp = client.post(
        f"/api/employees/{employee_a.id}/documents?type_document=Contrat",
        files={"file": ("contrat.pdf", b"%PDF-fake-contract", "application/pdf")},
        headers={"X-CSRF-Token": csrf},
    )
    assert upload_resp.status_code == 201, upload_resp.text
    documents = upload_resp.json()["documents"]
    assert len(documents) == 1
    document_id = documents[0]["id"]
    assert documents[0]["type_document"] == "Contrat"
    assert documents[0]["uploaded_by_email"] == hr_user.email

    download_resp = client.get(f"/api/employees/{employee_a.id}/documents/{document_id}/download")
    assert download_resp.status_code == 200
    assert download_resp.content == b"%PDF-fake-contract"

    delete_resp = client.delete(
        f"/api/employees/{employee_a.id}/documents/{document_id}",
        headers={"X-CSRF-Token": csrf},
    )
    assert delete_resp.status_code == 200
    assert delete_resp.json()["documents"] == []


def test_dg_can_download_employee_document_but_not_upload_or_delete(
    client, hr_user, dg_user, employee_a
):
    hr_csrf = login(client, hr_user.email)
    upload_resp = client.post(
        f"/api/employees/{employee_a.id}/documents?type_document=CV",
        files={"file": ("cv.pdf", b"cv-bytes", "application/pdf")},
        headers={"X-CSRF-Token": hr_csrf},
    )
    document_id = upload_resp.json()["documents"][0]["id"]

    dg_csrf = login(client, dg_user.email)
    assert (
        client.get(f"/api/employees/{employee_a.id}/documents/{document_id}/download").status_code
        == 200
    )
    assert (
        client.post(
            f"/api/employees/{employee_a.id}/documents?type_document=CV",
            files={"file": ("cv2.pdf", b"cv-bytes", "application/pdf")},
            headers={"X-CSRF-Token": dg_csrf},
        ).status_code
        == 403
    )
    assert (
        client.delete(
            f"/api/employees/{employee_a.id}/documents/{document_id}",
            headers={"X-CSRF-Token": dg_csrf},
        ).status_code
        == 403
    )


def test_employee_has_no_document_routes(client, employee_a_user, employee_a):
    login(client, employee_a_user.email)
    assert client.get(f"/api/employees/{employee_a.id}/documents/1/download").status_code == 403
    assert client.get("/api/employees/documents/alertes").status_code == 403


def test_document_alert_flags_soon_to_expire_document_not_a_fresh_one(
    client, hr_user, employee_a, employee_b
):
    csrf = login(client, hr_user.email)
    soon = (datetime.now(UTC).date() + timedelta(days=5)).isoformat()
    far = (datetime.now(UTC).date() + timedelta(days=200)).isoformat()

    client.post(
        f"/api/employees/{employee_a.id}/documents",
        params={"type_document": "CIN scanné", "date_expiration": soon},
        files={"file": ("cin.pdf", b"cin-bytes", "application/pdf")},
        headers={"X-CSRF-Token": csrf},
    )
    client.post(
        f"/api/employees/{employee_b.id}/documents",
        params={"type_document": "CIN scanné", "date_expiration": far},
        files={"file": ("cin.pdf", b"cin-bytes", "application/pdf")},
        headers={"X-CSRF-Token": csrf},
    )

    resp = client.get("/api/employees/documents/alertes")
    assert resp.status_code == 200
    alerted_ids = {a["employee_id"] for a in resp.json()}
    assert employee_a.id in alerted_ids
    assert employee_b.id not in alerted_ids


# ------------------------------------------------------------ bulk import --


def _import_csv(nom="Bennani", prenom="Karim", departement="") -> bytes:
    header = "Matricule,Nom,Prénom,CIN,Date de naissance,Lieu de naissance,Téléphone,Email,Ville,Adresse,Département,Poste,Statut,Type de contrat,Catégorie,CNSS,Salaire de base,Salaire net,Date d'embauche,Équipe"
    row = f",{nom},{prenom},,,,,,,,{departement},,,,,,,,,"
    return f"{header}\n{row}\n".encode()


def test_hr_can_download_import_template(client, hr_user):
    login(client, hr_user.email)
    resp = client.get("/api/employees/import/template")
    assert resp.status_code == 200
    assert (
        resp.headers["content-type"]
        == "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
    assert resp.content[:2] == b"PK"


def test_non_hr_cannot_download_import_template(client, dg_user, employee_a_user):
    for user in (dg_user, employee_a_user):
        login(client, user.email)
        assert client.get("/api/employees/import/template").status_code == 403


def test_hr_can_preview_and_confirm_bulk_import(client, hr_user):
    csrf = login(client, hr_user.email)

    preview_resp = client.post(
        "/api/employees/import/upload",
        files={"file": ("collaborateurs.csv", _import_csv(), "text/csv")},
        headers={"X-CSRF-Token": csrf},
    )
    assert preview_resp.status_code == 200
    preview = preview_resp.json()
    assert preview["nb_valid"] == 1
    assert preview["nb_errors"] == 0
    assert preview["rows"][0]["ok"] is True

    confirm_resp = client.post(
        "/api/employees/import/confirm",
        json={"token": preview["token"]},
        headers={"X-CSRF-Token": csrf},
    )
    assert confirm_resp.status_code == 200
    result = confirm_resp.json()
    assert result["created"] == 1
    assert result["skipped"] == []

    roster = client.get("/api/employees").json()
    assert any(e["full_name"] == "Karim Bennani" for e in roster)


def test_bulk_import_preview_flags_unknown_department(client, hr_user):
    csrf = login(client, hr_user.email)
    preview_resp = client.post(
        "/api/employees/import/upload",
        files={
            "file": (
                "collaborateurs.csv",
                _import_csv(departement="Département Inexistant"),
                "text/csv",
            )
        },
        headers={"X-CSRF-Token": csrf},
    )
    preview = preview_resp.json()
    assert preview["nb_valid"] == 0
    assert preview["nb_errors"] == 1
    assert any("inconnu" in e for e in preview["rows"][0]["errors"])


def test_non_hr_cannot_bulk_import(client, dg_user, employee_a_user):
    for user in (dg_user, employee_a_user):
        csrf = login(client, user.email)
        assert (
            client.post(
                "/api/employees/import/upload",
                files={"file": ("x.csv", _import_csv(), "text/csv")},
                headers={"X-CSRF-Token": csrf},
            ).status_code
            == 403
        )
        assert (
            client.post(
                "/api/employees/import/confirm",
                json={"token": "whatever"},
                headers={"X-CSRF-Token": csrf},
            ).status_code
            == 403
        )
