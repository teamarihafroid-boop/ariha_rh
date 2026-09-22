from __future__ import annotations

import time
from datetime import UTC, datetime, timedelta

from sqlalchemy import update

from app.models import ApplicationComment, Candidate, EmployeeStatus, JobApplication
from app.schemas.recruitment import HireRequest
from app.services import recruitment_service


def _backdate_last_movement(db, application_id: int, days: int) -> None:
    # A plain attribute assignment + flush would trigger JobApplication's own
    # onupdate=func.now() and silently reset it back to "now" — a Core-level
    # bulk UPDATE (explicitly setting the column) bypasses that ORM default,
    # same as server_default/onupdate only apply to columns absent from the
    # emitted SQL.
    db.execute(
        update(JobApplication)
        .where(JobApplication.id == application_id)
        .values(date_dernier_mouvement=datetime.now(UTC) - timedelta(days=days))
    )
    db.flush()


def _make_candidate(db, **overrides) -> Candidate:
    defaults = {"nom_complet": "Sara Alami", "email": "sara@example.com", "telephone": "0600000000"}
    candidate = Candidate(**{**defaults, **overrides})
    db.add(candidate)
    db.flush()
    return candidate


def test_find_duplicate_candidates_matches_on_email(db):
    _make_candidate(db, email="dup@example.com", telephone="0600000001")
    dups = recruitment_service.find_duplicate_candidates(
        db, email="dup@example.com", telephone="0699999999"
    )
    assert len(dups) == 1


def test_find_duplicate_candidates_matches_on_phone(db):
    _make_candidate(db, email="unique@example.com", telephone="0611111111")
    dups = recruitment_service.find_duplicate_candidates(
        db, email="different@example.com", telephone="0611111111"
    )
    assert len(dups) == 1


def test_find_duplicate_candidates_no_match(db):
    _make_candidate(db, email="a@example.com", telephone="0600000002")
    dups = recruitment_service.find_duplicate_candidates(
        db, email="b@example.com", telephone="0600000003"
    )
    assert dups == []


def test_move_stage_touches_date_dernier_mouvement(db, job_offer, application_stage_recu):
    candidate = _make_candidate(db)
    application = recruitment_service.create_application(
        db, candidate_id=candidate.id, job_offer_id=job_offer.id, responsable=None
    )
    db.flush()
    original = application.date_dernier_mouvement
    time.sleep(0.01)

    recruitment_service.move_stage(db, application, application_stage_recu.id)
    db.flush()
    db.refresh(application)
    assert application.stage_id == application_stage_recu.id
    assert application.date_dernier_mouvement >= original


def test_create_application_rejects_duplicate_pair(db, job_offer):
    candidate = _make_candidate(db)
    recruitment_service.create_application(
        db, candidate_id=candidate.id, job_offer_id=job_offer.id, responsable=None
    )
    try:
        recruitment_service.create_application(
            db, candidate_id=candidate.id, job_offer_id=job_offer.id, responsable=None
        )
        assert False, "expected RecruitmentServiceError"
    except recruitment_service.RecruitmentServiceError:
        pass


def test_create_application_defaults_to_first_stage_by_ordre(
    db, job_offer, application_stage_recu, application_stage_accepte
):
    candidate = _make_candidate(db)
    application = recruitment_service.create_application(
        db, candidate_id=candidate.id, job_offer_id=job_offer.id, responsable=None
    )
    assert application.stage_id == application_stage_recu.id


def test_delete_application_removes_comments(db, job_offer, application_stage_recu, hr_user):
    candidate = _make_candidate(db)
    application = recruitment_service.create_application(
        db, candidate_id=candidate.id, job_offer_id=job_offer.id, responsable=None
    )
    application_id = application.id
    db.add(ApplicationComment(application_id=application_id, texte="ok", auteur_user_id=hr_user.id))
    db.flush()

    recruitment_service.delete_application(db, application)

    assert db.query(ApplicationComment).filter_by(application_id=application_id).count() == 0


def test_hire_candidate_creates_employee_and_links_candidate(db, job_offer, hr_user):
    db.add(EmployeeStatus(libelle="Actif", couleur="#43A047", is_active_status=True))
    db.flush()
    candidate = _make_candidate(db, nom_complet="Omar Fassi")
    application = recruitment_service.create_application(
        db, candidate_id=candidate.id, job_offer_id=job_offer.id, responsable=None
    )
    db.refresh(application)

    employee = recruitment_service.hire_candidate(
        db,
        application,
        HireRequest(prenom="Omar", nom="Fassi", date_embauche=None),
        current_user_id=hr_user.id,
    )
    assert employee.full_name == "Omar Fassi"
    assert candidate.employee_id == employee.id


def test_hire_candidate_rejects_already_hired(db, job_offer, hr_user):
    db.add(EmployeeStatus(libelle="Actif", couleur="#43A047", is_active_status=True))
    db.flush()
    candidate = _make_candidate(db, nom_complet="Nadia Chraibi")
    application = recruitment_service.create_application(
        db, candidate_id=candidate.id, job_offer_id=job_offer.id, responsable=None
    )
    db.refresh(application)
    recruitment_service.hire_candidate(
        db, application, HireRequest(prenom="Nadia", nom="Chraibi"), current_user_id=hr_user.id
    )

    try:
        recruitment_service.hire_candidate(
            db,
            application,
            HireRequest(prenom="Nadia", nom="Chraibi"),
            current_user_id=hr_user.id,
        )
        assert False, "expected RecruitmentServiceError"
    except recruitment_service.RecruitmentServiceError:
        pass


def test_hire_candidate_migrates_cv_bank_attachments_to_employee_documents(
    db, job_offer, hr_user, tmp_path, monkeypatch
):
    """Regression test: a CV attached to a candidate (e.g. via the bulk CV
    import) must show up on the new employee's fiche once hired — it used
    to stay stranded on the now-orphaned candidate record."""
    from app.config import get_settings
    from app.models import CandidateAttachment
    from app.services import storage_service

    settings = get_settings()
    monkeypatch.setattr(settings, "storage_backend", "local")
    monkeypatch.setattr(settings, "storage_local_dir", str(tmp_path))

    candidate = _make_candidate(db, nom_complet="Youssef Radi")
    key = storage_service.build_key("candidates", candidate.id, "cv-youssef.pdf")
    storage_service.get_storage().save(key, b"%PDF-cv-content")
    db.add(
        CandidateAttachment(
            candidate_id=candidate.id,
            type_document="CV",
            nom_fichier="cv-youssef.pdf",
            storage_key=key,
            content_type="application/pdf",
            taille_octets=16,
            uploaded_by_user_id=hr_user.id,
        )
    )
    db.flush()
    db.refresh(candidate)

    application = recruitment_service.create_application(
        db, candidate_id=candidate.id, job_offer_id=job_offer.id, responsable=None
    )
    db.refresh(application)

    employee = recruitment_service.hire_candidate(
        db,
        application,
        HireRequest(prenom="Youssef", nom="Radi"),
        current_user_id=hr_user.id,
    )
    db.flush()
    db.refresh(employee)

    assert len(employee.documents) == 1
    doc = employee.documents[0]
    assert doc.type_document == "CV"
    assert doc.nom_fichier == "cv-youssef.pdf"
    assert doc.storage_key != key  # independent copy, not a shared reference
    assert storage_service.get_storage().read(doc.storage_key) == b"%PDF-cv-content"


def test_stalled_applications_flags_old_movement_not_a_fresh_one(db, job_offer):
    stale_candidate = _make_candidate(db, nom_complet="Stale Candidate", email="stale@example.com")
    fresh_candidate = _make_candidate(db, nom_complet="Fresh Candidate", email="fresh@example.com")

    stale_application = recruitment_service.create_application(
        db, candidate_id=stale_candidate.id, job_offer_id=job_offer.id, responsable=None
    )
    fresh_application = recruitment_service.create_application(
        db, candidate_id=fresh_candidate.id, job_offer_id=job_offer.id, responsable=None
    )
    _backdate_last_movement(db, stale_application.id, days=20)

    alerts = recruitment_service.stalled_applications(db, threshold_days=14)
    alerted_ids = {a["application_id"] for a in alerts}
    assert stale_application.id in alerted_ids
    assert fresh_application.id not in alerted_ids


def test_stalled_applications_excludes_already_hired_candidates(db, job_offer, hr_user):
    db.add(EmployeeStatus(libelle="Actif", couleur="#43A047", is_active_status=True))
    db.flush()
    candidate = _make_candidate(db, nom_complet="Hired Candidate")
    application = recruitment_service.create_application(
        db, candidate_id=candidate.id, job_offer_id=job_offer.id, responsable=None
    )
    db.refresh(application)
    recruitment_service.hire_candidate(
        db, application, HireRequest(prenom="Hired", nom="Candidate"), current_user_id=hr_user.id
    )
    _backdate_last_movement(db, application.id, days=20)

    alerts = recruitment_service.stalled_applications(db, threshold_days=14)
    assert application.id not in {a["application_id"] for a in alerts}
