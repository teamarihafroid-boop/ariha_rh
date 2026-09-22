from __future__ import annotations

from app.services import cv_extraction_service
from tests.conftest import login

CANDIDATE_PAYLOAD = {
    "nom_complet": "Karim Idrissi",
    "telephone": "0600112233",
    "email": "karim.idrissi@example.com",
    "ville": "Casablanca",
    "annees_experience": None,
    "experience_resume": None,
    "competences": None,
    "diplomes": None,
    "langues": None,
    "favori": False,
    "notes": None,
}


def test_hr_full_recruitment_flow(client, db, hr_user, job_offer, application_stage_accepte):
    csrf = login(client, hr_user.email)

    offer_resp = client.get("/api/recruitment/job-offers")
    assert offer_resp.status_code == 200
    assert any(o["id"] == job_offer.id for o in offer_resp.json())

    candidate_resp = client.post(
        "/api/recruitment/candidates", json=CANDIDATE_PAYLOAD, headers={"X-CSRF-Token": csrf}
    )
    assert candidate_resp.status_code == 201, candidate_resp.text
    body = candidate_resp.json()
    assert body["duplicates"] == []
    candidate_id = body["candidate"]["id"]

    application_resp = client.post(
        "/api/recruitment/applications",
        json={"candidate_id": candidate_id, "job_offer_id": job_offer.id, "responsable": "RH Test"},
        headers={"X-CSRF-Token": csrf},
    )
    assert application_resp.status_code == 201, application_resp.text
    application_id = application_resp.json()["id"]

    stage_resp = client.put(
        f"/api/recruitment/applications/{application_id}/stage",
        json={"stage_id": application_stage_accepte.id},
        headers={"X-CSRF-Token": csrf},
    )
    assert stage_resp.status_code == 200
    assert stage_resp.json()["stage_libelle"] == "Accepté"

    comment_resp = client.post(
        f"/api/recruitment/applications/{application_id}/comments",
        json={"texte": "Bon profil"},
        headers={"X-CSRF-Token": csrf},
    )
    assert comment_resp.status_code == 201
    assert comment_resp.json()["auteur_email"] == hr_user.email

    preview_resp = client.get(f"/api/recruitment/applications/{application_id}/hire-preview")
    assert preview_resp.status_code == 200
    preview = preview_resp.json()
    assert preview["prenom_suggere"] == "Karim"
    assert preview["nom_suggere"] == "Idrissi"

    hire_resp = client.post(
        f"/api/recruitment/applications/{application_id}/hire",
        json={
            "prenom": preview["prenom_suggere"],
            "nom": preview["nom_suggere"],
            "telephone": preview["telephone"],
            "email": preview["email"],
            "ville": preview["ville"],
            "department_id": preview["department_id"],
            "date_embauche": "2026-09-10",
        },
        headers={"X-CSRF-Token": csrf},
    )
    assert hire_resp.status_code == 201, hire_resp.text
    employee = hire_resp.json()
    assert employee["full_name"] == "Karim Idrissi"

    # Hiring the same candidate again is rejected.
    second_hire = client.post(
        f"/api/recruitment/applications/{application_id}/hire",
        json={"prenom": "Karim", "nom": "Idrissi"},
        headers={"X-CSRF-Token": csrf},
    )
    assert second_hire.status_code == 400


def test_duplicate_candidate_detection(client, hr_user):
    csrf = login(client, hr_user.email)
    client.post(
        "/api/recruitment/candidates", json=CANDIDATE_PAYLOAD, headers={"X-CSRF-Token": csrf}
    )

    dup_resp = client.post(
        "/api/recruitment/candidates",
        json={**CANDIDATE_PAYLOAD, "nom_complet": "Karim I. (doublon)"},
        headers={"X-CSRF-Token": csrf},
    )
    assert dup_resp.status_code == 201
    assert len(dup_resp.json()["duplicates"]) == 1


def test_duplicate_application_returns_409(client, hr_user, job_offer):
    csrf = login(client, hr_user.email)
    candidate = client.post(
        "/api/recruitment/candidates", json=CANDIDATE_PAYLOAD, headers={"X-CSRF-Token": csrf}
    ).json()["candidate"]

    payload = {"candidate_id": candidate["id"], "job_offer_id": job_offer.id, "responsable": None}
    first = client.post(
        "/api/recruitment/applications", json=payload, headers={"X-CSRF-Token": csrf}
    )
    assert first.status_code == 201
    second = client.post(
        "/api/recruitment/applications", json=payload, headers={"X-CSRF-Token": csrf}
    )
    assert second.status_code == 409


def test_dg_is_read_only_on_recruitment(client, dg_user, job_offer):
    csrf = login(client, dg_user.email)
    assert client.get("/api/recruitment/job-offers").status_code == 200
    assert client.get("/api/recruitment/candidates").status_code == 200
    assert (
        client.get(f"/api/recruitment/applications?job_offer_id={job_offer.id}").status_code == 200
    )

    assert (
        client.post(
            "/api/recruitment/job-offers",
            json={"titre": "X", "status_id": job_offer.status_id},
            headers={"X-CSRF-Token": csrf},
        ).status_code
        == 403
    )
    assert (
        client.post(
            "/api/recruitment/candidates", json=CANDIDATE_PAYLOAD, headers={"X-CSRF-Token": csrf}
        ).status_code
        == 403
    )


def test_hr_can_withdraw_application_and_its_comments(client, hr_user, job_offer):
    csrf = login(client, hr_user.email)
    candidate = client.post(
        "/api/recruitment/candidates", json=CANDIDATE_PAYLOAD, headers={"X-CSRF-Token": csrf}
    ).json()["candidate"]
    application_id = client.post(
        "/api/recruitment/applications",
        json={"candidate_id": candidate["id"], "job_offer_id": job_offer.id, "responsable": None},
        headers={"X-CSRF-Token": csrf},
    ).json()["id"]
    client.post(
        f"/api/recruitment/applications/{application_id}/comments",
        json={"texte": "Bon profil"},
        headers={"X-CSRF-Token": csrf},
    )

    delete_resp = client.delete(
        f"/api/recruitment/applications/{application_id}", headers={"X-CSRF-Token": csrf}
    )
    assert delete_resp.status_code == 204

    assert client.get(f"/api/recruitment/applications/{application_id}/comments").status_code == 404


def test_dg_cannot_withdraw_application(client, hr_user, dg_user, job_offer):
    hr_csrf = login(client, hr_user.email)
    candidate = client.post(
        "/api/recruitment/candidates", json=CANDIDATE_PAYLOAD, headers={"X-CSRF-Token": hr_csrf}
    ).json()["candidate"]
    application_id = client.post(
        "/api/recruitment/applications",
        json={"candidate_id": candidate["id"], "job_offer_id": job_offer.id, "responsable": None},
        headers={"X-CSRF-Token": hr_csrf},
    ).json()["id"]

    dg_csrf = login(client, dg_user.email)
    assert (
        client.delete(
            f"/api/recruitment/applications/{application_id}", headers={"X-CSRF-Token": dg_csrf}
        ).status_code
        == 403
    )


def test_employee_has_no_recruitment_access(client, employee_a_user, job_offer):
    login(client, employee_a_user.email)
    assert client.get("/api/recruitment/job-offers").status_code == 403
    assert client.get("/api/recruitment/candidates").status_code == 403
    assert (
        client.get(f"/api/recruitment/applications?job_offer_id={job_offer.id}").status_code == 403
    )


def test_hr_can_upload_download_and_delete_candidate_attachment(client, hr_user):
    csrf = login(client, hr_user.email)
    candidate_id = client.post(
        "/api/recruitment/candidates", json=CANDIDATE_PAYLOAD, headers={"X-CSRF-Token": csrf}
    ).json()["candidate"]["id"]

    upload_resp = client.post(
        f"/api/recruitment/candidates/{candidate_id}/attachments",
        params={"type_document": "CV"},
        files={"file": ("cv-karim.pdf", b"%PDF-fake-cv", "application/pdf")},
        headers={"X-CSRF-Token": csrf},
    )
    assert upload_resp.status_code == 201, upload_resp.text
    attachment = upload_resp.json()
    assert attachment["type_document"] == "CV"
    assert attachment["uploaded_by_email"] == hr_user.email

    download_resp = client.get(
        f"/api/recruitment/candidates/{candidate_id}/attachments/{attachment['id']}/download"
    )
    assert download_resp.status_code == 200
    assert download_resp.content == b"%PDF-fake-cv"

    list_resp = client.get("/api/recruitment/candidates?q=Karim")
    assert list_resp.json()[0]["attachments"][0]["id"] == attachment["id"]

    delete_resp = client.delete(
        f"/api/recruitment/candidates/{candidate_id}/attachments/{attachment['id']}",
        headers={"X-CSRF-Token": csrf},
    )
    assert delete_resp.status_code == 204
    assert (
        client.get(
            f"/api/recruitment/candidates/{candidate_id}/attachments/{attachment['id']}/download"
        ).status_code
        == 404
    )


def test_dg_cannot_upload_candidate_attachment(client, hr_user, dg_user):
    hr_csrf = login(client, hr_user.email)
    candidate_id = client.post(
        "/api/recruitment/candidates", json=CANDIDATE_PAYLOAD, headers={"X-CSRF-Token": hr_csrf}
    ).json()["candidate"]["id"]

    dg_csrf = login(client, dg_user.email)
    assert (
        client.post(
            f"/api/recruitment/candidates/{candidate_id}/attachments",
            params={"type_document": "CV"},
            files={"file": ("cv.pdf", b"cv-bytes", "application/pdf")},
            headers={"X-CSRF-Token": dg_csrf},
        ).status_code
        == 403
    )


class _FakeModels:
    def generate_content(self, *, model, contents, config):
        class _Resp:
            text = '{"nom_complet": "Karim Idrissi", "email": "karim@example.com"}'

        return _Resp()


class _FakeClient:
    def __init__(self, api_key):
        self.models = _FakeModels()


def test_hr_can_extract_cv_fields(client, hr_user, monkeypatch):
    settings = cv_extraction_service.get_settings()
    monkeypatch.setattr(settings, "gemini_api_key", "fake-key")
    monkeypatch.setattr(cv_extraction_service.genai, "Client", _FakeClient)

    csrf = login(client, hr_user.email)
    resp = client.post(
        "/api/recruitment/candidates/extract-cv",
        files={"file": ("cv.pdf", b"%PDF-fake", "application/pdf")},
        headers={"X-CSRF-Token": csrf},
    )
    assert resp.status_code == 200, resp.text
    assert resp.json()["nom_complet"] == "Karim Idrissi"


def test_dg_and_employee_cannot_extract_cv_fields(
    client, hr_user, dg_user, employee_a_user, monkeypatch
):
    settings = cv_extraction_service.get_settings()
    monkeypatch.setattr(settings, "gemini_api_key", "fake-key")
    monkeypatch.setattr(cv_extraction_service.genai, "Client", _FakeClient)

    for user in (dg_user, employee_a_user):
        csrf = login(client, user.email)
        resp = client.post(
            "/api/recruitment/candidates/extract-cv",
            files={"file": ("cv.pdf", b"%PDF-fake", "application/pdf")},
            headers={"X-CSRF-Token": csrf},
        )
        assert resp.status_code == 403


def test_hr_can_list_stalled_applications_dg_and_employee_cannot(
    client, hr_user, dg_user, employee_a_user, job_offer
):
    login(client, hr_user.email)
    assert client.get("/api/recruitment/applications/stagnantes").status_code == 200

    for user in (dg_user, employee_a_user):
        login(client, user.email)
        assert client.get("/api/recruitment/applications/stagnantes").status_code == 403


class _FakeModelsMulti:
    """Returns a distinct extracted name per call so a batch of files each
    look like a different person, keyed off the uploaded filename."""

    def generate_content(self, *, model, contents, config):
        # contents = [prompt, file_part]; the fake CV content encodes who it is.
        file_part = contents[1]
        raw = file_part if isinstance(file_part, str) else file_part.data.decode()

        class _Resp:
            text = raw

        return _Resp()


class _FakeClientMulti:
    def __init__(self, api_key):
        self.models = _FakeModelsMulti()


def test_bulk_import_cvs_is_hr_only(client, hr_user, dg_user, employee_a_user, job_offer):
    for user in (dg_user, employee_a_user):
        csrf = login(client, user.email)
        resp = client.post(
            f"/api/recruitment/job-offers/{job_offer.id}/bulk-import-cvs",
            files=[("files", ("cv.txt", b"peu importe", "text/plain"))],
            headers={"X-CSRF-Token": csrf},
        )
        assert resp.status_code == 403


def test_bulk_import_cvs_creates_one_candidate_per_file_and_links_to_offer(
    client, hr_user, job_offer, application_stage_recu, monkeypatch
):
    settings = cv_extraction_service.get_settings()
    monkeypatch.setattr(settings, "gemini_api_key", "fake-key")
    monkeypatch.setattr(cv_extraction_service.genai, "Client", _FakeClientMulti)

    csrf = login(client, hr_user.email)
    resp = client.post(
        f"/api/recruitment/job-offers/{job_offer.id}/bulk-import-cvs",
        files=[
            (
                "files",
                (
                    "cv1.txt",
                    b'{"nom_complet": "Amine Fassi", "email": "amine.fassi@example.com"}',
                    "text/plain",
                ),
            ),
            (
                "files",
                (
                    "cv2.txt",
                    b'{"nom_complet": "Nawal Ziani", "email": "nawal.ziani@example.com"}',
                    "text/plain",
                ),
            ),
        ],
        headers={"X-CSRF-Token": csrf},
    )
    assert resp.status_code == 200, resp.text
    items = resp.json()["items"]
    assert len(items) == 2
    assert {i["status"] for i in items} == {"created"}
    assert {i["candidate"]["nom_complet"] for i in items} == {"Amine Fassi", "Nawal Ziani"}

    applications = client.get(f"/api/recruitment/applications?job_offer_id={job_offer.id}").json()
    assert {a["candidate_nom"] for a in applications} == {"Amine Fassi", "Nawal Ziani"}


def test_bulk_import_cvs_links_existing_candidate_instead_of_duplicating(
    client, hr_user, job_offer, application_stage_recu, monkeypatch
):
    settings = cv_extraction_service.get_settings()
    monkeypatch.setattr(settings, "gemini_api_key", "fake-key")
    monkeypatch.setattr(cv_extraction_service.genai, "Client", _FakeClientMulti)

    csrf = login(client, hr_user.email)
    existing = client.post(
        "/api/recruitment/candidates",
        json={**CANDIDATE_PAYLOAD, "email": "karim.idrissi@example.com"},
        headers={"X-CSRF-Token": csrf},
    ).json()["candidate"]

    resp = client.post(
        f"/api/recruitment/job-offers/{job_offer.id}/bulk-import-cvs",
        files=[
            (
                "files",
                (
                    "cv.txt",
                    (
                        b'{"nom_complet": "Karim Idrissi (nouveau CV)", '
                        b'"email": "karim.idrissi@example.com"}'
                    ),
                    "text/plain",
                ),
            )
        ],
        headers={"X-CSRF-Token": csrf},
    )
    assert resp.status_code == 200, resp.text
    item = resp.json()["items"][0]
    assert item["status"] == "linked_existing"
    assert item["candidate"]["id"] == existing["id"]
    # The original record's name isn't overwritten by the new CV's guess.
    assert item["candidate"]["nom_complet"] == "Karim Idrissi"
    # But the freshly uploaded CV is now attached to that same candidate.
    assert len(item["candidate"]["attachments"]) == 1

    all_candidates = client.get("/api/recruitment/candidates?q=Karim").json()
    assert len(all_candidates) == 1


def test_bulk_import_cvs_reports_already_applied_without_failing_the_batch(
    client, hr_user, job_offer, application_stage_recu, monkeypatch
):
    settings = cv_extraction_service.get_settings()
    monkeypatch.setattr(settings, "gemini_api_key", "fake-key")
    monkeypatch.setattr(cv_extraction_service.genai, "Client", _FakeClientMulti)

    csrf = login(client, hr_user.email)
    same_cv = (
        "cv.txt",
        b'{"nom_complet": "Sami Radi", "email": "sami.radi@example.com"}',
        "text/plain",
    )
    # Uploading the same person's CV twice in one batch: first creates and
    # applies, second recognizes them and finds they're already applied.
    resp = client.post(
        f"/api/recruitment/job-offers/{job_offer.id}/bulk-import-cvs",
        files=[("files", same_cv), ("files", same_cv)],
        headers={"X-CSRF-Token": csrf},
    )
    assert resp.status_code == 200, resp.text
    statuses = [i["status"] for i in resp.json()["items"]]
    assert statuses == ["created", "already_applied"]


def test_bulk_import_cvs_falls_back_to_filename_when_extraction_unavailable(
    client, hr_user, job_offer, application_stage_recu
):
    """No GEMINI_API_KEY configured (the test-env default) shouldn't sink
    the whole batch — each file still becomes a candidate, named from its
    filename, ready for RH to fill in by hand."""
    csrf = login(client, hr_user.email)
    resp = client.post(
        f"/api/recruitment/job-offers/{job_offer.id}/bulk-import-cvs",
        files=[("files", ("Fatima Zahra CV.pdf", b"%PDF-fake", "application/pdf"))],
        headers={"X-CSRF-Token": csrf},
    )
    assert resp.status_code == 200, resp.text
    item = resp.json()["items"][0]
    assert item["status"] == "created"
    assert item["candidate"]["nom_complet"] == "Fatima Zahra CV"
    assert item["message"] is not None
