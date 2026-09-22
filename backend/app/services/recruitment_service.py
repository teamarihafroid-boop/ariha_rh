from __future__ import annotations

from datetime import UTC, datetime, timedelta

from sqlalchemy import or_
from sqlalchemy.orm import Session, joinedload

from app.models import (
    ApplicationComment,
    ApplicationStage,
    Candidate,
    Employee,
    EmployeeDocument,
    EmployeeStatus,
    JobApplication,
)
from app.schemas.employee import EmployeeCreate
from app.schemas.recruitment import HireRequest
from app.services import employee_service, storage_service


class RecruitmentServiceError(ValueError):
    pass


def find_duplicate_candidates(
    db: Session, *, email: str | None, telephone: str | None, exclude_id: int | None = None
) -> list[Candidate]:
    """Email-OR-phone exact match, ported verbatim from the prototype's
    candidate_service.find_duplicates. Never blocks creation — the caller
    surfaces this as a warning alongside the newly created candidate."""
    if not email and not telephone:
        return []
    conditions = []
    if email:
        conditions.append(Candidate.email == email)
    if telephone:
        conditions.append(Candidate.telephone == telephone)
    query = db.query(Candidate).filter(or_(*conditions))
    if exclude_id is not None:
        query = query.filter(Candidate.id != exclude_id)
    return query.all()


def create_application(
    db: Session,
    *,
    candidate_id: int,
    job_offer_id: int,
    responsable: str | None,
    stage_id: int | None = None,
) -> JobApplication:
    existing = (
        db.query(JobApplication)
        .filter(
            JobApplication.candidate_id == candidate_id,
            JobApplication.job_offer_id == job_offer_id,
        )
        .first()
    )
    if existing is not None:
        raise RecruitmentServiceError("Ce candidat a déjà une candidature sur cette offre.")
    if stage_id is None:
        first_stage = db.query(ApplicationStage).order_by(ApplicationStage.ordre).first()
        stage_id = first_stage.id if first_stage else None
    application = JobApplication(
        candidate_id=candidate_id,
        job_offer_id=job_offer_id,
        responsable=responsable,
        stage_id=stage_id,
    )
    db.add(application)
    db.flush()
    return application


def move_stage(db: Session, application: JobApplication, stage_id: int) -> JobApplication:
    application.stage_id = stage_id
    db.flush()
    return application


def delete_application(db: Session, application: JobApplication) -> None:
    db.query(ApplicationComment).filter(
        ApplicationComment.application_id == application.id
    ).delete()
    db.delete(application)
    db.flush()


def hire_preview(db: Session, application: JobApplication) -> dict:
    candidate = application.candidate
    offer = application.job_offer
    parts = candidate.nom_complet.strip().split(maxsplit=1)
    prenom_suggere = parts[0] if parts else candidate.nom_complet
    nom_suggere = parts[1] if len(parts) > 1 else ""
    return {
        "prenom_suggere": prenom_suggere,
        "nom_suggere": nom_suggere,
        "telephone": candidate.telephone,
        "email": candidate.email,
        "ville": candidate.ville,
        "department_id": offer.department_id,
        "department_nom": offer.department.nom if offer.department else None,
        "cv_disponible": False,
    }


def _migrate_candidate_attachments_to_employee(
    db: Session, candidate: Candidate, employee: Employee, *, uploaded_by_user_id: int
) -> None:
    """Carries the CV bank's files (CV, diploma, ...) over to the new
    fiche's Documents tab. Copies the bytes under the employee's own
    storage key rather than reusing the candidate's — the two records now
    have independent lifecycles (e.g. deleting the candidate attachment
    later must not orphan the employee's document, or vice versa)."""
    storage = storage_service.get_storage()
    for attachment in candidate.attachments:
        content = storage.read(attachment.storage_key)
        key = storage_service.build_key("employees", employee.id, attachment.nom_fichier)
        storage.save(key, content)
        db.add(
            EmployeeDocument(
                employee_id=employee.id,
                type_document=attachment.type_document,
                nom_fichier=attachment.nom_fichier,
                storage_key=key,
                content_type=attachment.content_type,
                taille_octets=attachment.taille_octets,
                uploaded_by_user_id=uploaded_by_user_id,
            )
        )


def hire_candidate(
    db: Session, application: JobApplication, payload: HireRequest, *, current_user_id: int
) -> Employee:
    candidate = application.candidate
    if candidate.employee_id is not None:
        raise RecruitmentServiceError("Ce candidat a déjà une fiche collaborateur liée.")

    active_status = db.query(EmployeeStatus).filter_by(libelle="Actif").first()
    notes = (
        f"Recruté via l'offre « {application.job_offer.titre} » "
        f"(candidature #{application.id})."
    )
    employee_payload = EmployeeCreate(
        nom=payload.nom,
        prenom=payload.prenom,
        telephone=payload.telephone,
        email=payload.email,
        ville=payload.ville,
        department_id=payload.department_id,
        position_id=payload.position_id,
        categorie_professionnelle=payload.categorie_professionnelle,
        date_embauche=payload.date_embauche,
        date_fin_periode_essai=payload.date_fin_periode_essai,
        status_id=active_status.id if active_status else None,
        notes=notes,
    )
    employee = employee_service.create_employee(db, employee_payload)
    _migrate_candidate_attachments_to_employee(
        db, candidate, employee, uploaded_by_user_id=current_user_id
    )
    candidate.employee_id = employee.id
    db.flush()
    return employee


def stalled_applications(db: Session, *, threshold_days: int = 14) -> list[dict]:
    """HR-38 "stalled candidacies": read-time, no cron, same posture as
    employee_service.probation_alerts/document_alerts. Flags an application
    whose date_dernier_mouvement hasn't moved in threshold_days, excluding
    ones that already converted to a hire. Known simplification: there's no
    is_terminal flag on ApplicationStage, so an application sitting in a
    dead-end stage like "Refusé" will also surface here after the threshold
    — acceptable, HR can withdraw it via the existing pipeline UI."""
    cutoff = datetime.now(UTC) - timedelta(days=threshold_days)
    applications = (
        db.query(JobApplication)
        .options(
            joinedload(JobApplication.candidate),
            joinedload(JobApplication.job_offer),
            joinedload(JobApplication.stage),
        )
        .filter(JobApplication.date_dernier_mouvement <= cutoff)
        .all()
    )
    alerts = []
    for application in applications:
        if application.candidate.employee_id is not None:
            continue
        jours = (datetime.now(UTC) - application.date_dernier_mouvement).days
        alerts.append(
            {
                "application_id": application.id,
                "candidate_nom": application.candidate.nom_complet,
                "job_offer_titre": application.job_offer.titre,
                "stage_libelle": application.stage.libelle if application.stage else None,
                "date_dernier_mouvement": application.date_dernier_mouvement,
                "jours_stagnation": jours,
            }
        )
    return alerts
