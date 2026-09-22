from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, Depends, File, HTTPException, Response, UploadFile, status
from sqlalchemy import func
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, joinedload

from app.database import get_db
from app.dependencies import AuthUser, require_role, verify_csrf
from app.models import (
    ApplicationComment,
    ApplicationStage,
    Candidate,
    CandidateAttachment,
    JobApplication,
    JobOffer,
    JobOfferStatus,
)
from app.models.enums import UserRole
from app.routers.employees import _serialize_employee
from app.schemas.employee import EmployeeOut
from app.schemas.recruitment import (
    ApplicationCommentCreate,
    ApplicationCommentOut,
    ApplicationStageOut,
    BulkCvImportItem,
    BulkCvImportResult,
    CandidateApplicationOut,
    CandidateAttachmentOut,
    CandidateCreate,
    CandidateCreateResult,
    CandidateOut,
    CandidateUpdate,
    HirePreviewOut,
    HireRequest,
    JobApplicationCreate,
    JobApplicationOut,
    JobOfferCreate,
    JobOfferOut,
    JobOfferStatusOut,
    JobOfferUpdate,
    StageUpdate,
    StalledApplicationOut,
)
from app.services import audit_service, cv_extraction_service, recruitment_service, storage_service
from app.services.cv_extraction_service import CvFields

router = APIRouter(prefix="/api/recruitment", tags=["recruitment"])

_READ_ROLES = (UserRole.HR, UserRole.DG)


def _serialize_offer(offer: JobOffer, *, candidatures_count: int = 0) -> JobOfferOut:
    return JobOfferOut(
        id=offer.id,
        titre=offer.titre,
        ville=offer.ville,
        department_id=offer.department_id,
        department_nom=offer.department.nom if offer.department else None,
        position_id=offer.position_id,
        position_intitule=offer.position.intitule if offer.position else None,
        status_id=offer.status_id,
        status_libelle=offer.status.libelle,
        status_couleur=offer.status.couleur,
        description=offer.description,
        responsable=offer.responsable,
        date_creation=offer.date_creation,
        date_cloture=offer.date_cloture,
        candidatures_count=candidatures_count,
    )


def _serialize_application(app_row: JobApplication) -> JobApplicationOut:
    return JobApplicationOut(
        id=app_row.id,
        candidate_id=app_row.candidate_id,
        candidate_nom=app_row.candidate.nom_complet,
        candidate_ville=app_row.candidate.ville,
        job_offer_id=app_row.job_offer_id,
        job_offer_titre=app_row.job_offer.titre,
        stage_id=app_row.stage_id,
        stage_libelle=app_row.stage.libelle if app_row.stage else None,
        responsable=app_row.responsable,
        date_creation=app_row.date_creation,
        date_dernier_mouvement=app_row.date_dernier_mouvement,
    )


def _serialize_attachment(attachment: CandidateAttachment) -> CandidateAttachmentOut:
    return CandidateAttachmentOut(
        id=attachment.id,
        type_document=attachment.type_document,
        nom_fichier=attachment.nom_fichier,
        content_type=attachment.content_type,
        taille_octets=attachment.taille_octets,
        uploaded_by_email=attachment.uploaded_by.email,
        created_at=attachment.created_at,
    )


def _serialize_candidate(candidate: Candidate) -> CandidateOut:
    return CandidateOut(
        id=candidate.id,
        nom_complet=candidate.nom_complet,
        telephone=candidate.telephone,
        email=candidate.email,
        ville=candidate.ville,
        annees_experience=candidate.annees_experience,
        experience_resume=candidate.experience_resume,
        competences=candidate.competences,
        diplomes=candidate.diplomes,
        langues=candidate.langues,
        favori=candidate.favori,
        notes=candidate.notes,
        employee_id=candidate.employee_id,
        date_ajout=candidate.date_ajout,
        attachments=[_serialize_attachment(a) for a in candidate.attachments],
        applications=[
            CandidateApplicationOut(
                id=a.id,
                job_offer_id=a.job_offer_id,
                job_offer_titre=a.job_offer.titre,
                stage_libelle=a.stage.libelle if a.stage else None,
            )
            for a in candidate.applications
        ],
    )


def _serialize_comment(comment: ApplicationComment) -> ApplicationCommentOut:
    return ApplicationCommentOut(
        id=comment.id,
        application_id=comment.application_id,
        texte=comment.texte,
        auteur_email=comment.auteur.email,
        created_at=comment.created_at,
    )


def _load_offer_or_404(db: Session, offer_id: int) -> JobOffer:
    offer = db.get(JobOffer, offer_id)
    if offer is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Offre introuvable.")
    return offer


def _load_candidate_or_404(db: Session, candidate_id: int) -> Candidate:
    candidate = db.get(Candidate, candidate_id)
    if candidate is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Candidat introuvable.")
    return candidate


def _load_attachment_or_404(
    db: Session, candidate_id: int, attachment_id: int
) -> CandidateAttachment:
    attachment = (
        db.query(CandidateAttachment)
        .filter(
            CandidateAttachment.id == attachment_id,
            CandidateAttachment.candidate_id == candidate_id,
        )
        .first()
    )
    if attachment is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Pièce jointe introuvable."
        )
    return attachment


def _load_application_or_404(db: Session, application_id: int) -> JobApplication:
    application = (
        db.query(JobApplication)
        .options(
            joinedload(JobApplication.candidate),
            joinedload(JobApplication.job_offer),
            joinedload(JobApplication.stage),
        )
        .filter(JobApplication.id == application_id)
        .first()
    )
    if application is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Candidature introuvable."
        )
    return application


# --------------------------------------------------------------- reference --


@router.get("/job-offer-statuses", response_model=list[JobOfferStatusOut])
def list_job_offer_statuses(
    current_user: AuthUser = Depends(require_role(*_READ_ROLES)),
    db: Session = Depends(get_db),
):
    return db.query(JobOfferStatus).order_by(JobOfferStatus.libelle).all()


@router.get("/application-stages", response_model=list[ApplicationStageOut])
def list_application_stages(
    current_user: AuthUser = Depends(require_role(*_READ_ROLES)),
    db: Session = Depends(get_db),
):
    return db.query(ApplicationStage).order_by(ApplicationStage.ordre).all()


# --------------------------------------------------------------- job offers --


@router.get("/job-offers", response_model=list[JobOfferOut])
def list_job_offers(
    current_user: AuthUser = Depends(require_role(*_READ_ROLES)),
    db: Session = Depends(get_db),
):
    offers = db.query(JobOffer).order_by(JobOffer.date_creation.desc()).all()
    counts = dict(
        db.query(JobApplication.job_offer_id, func.count(JobApplication.id)).group_by(
            JobApplication.job_offer_id
        )
    )
    return [_serialize_offer(o, candidatures_count=counts.get(o.id, 0)) for o in offers]


@router.post(
    "/job-offers",
    response_model=JobOfferOut,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(verify_csrf)],
)
def create_job_offer(
    payload: JobOfferCreate,
    current_user: AuthUser = Depends(require_role(UserRole.HR)),
    db: Session = Depends(get_db),
):
    offer = JobOffer(**payload.model_dump())
    db.add(offer)
    db.flush()
    audit_service.log(
        db,
        entity_type="job_offer",
        entity_id=offer.id,
        action="created",
        actor_user_id=current_user.id,
        actor_email=current_user.email,
        description=offer.titre,
    )
    db.commit()
    db.refresh(offer)
    return _serialize_offer(offer, candidatures_count=0)


@router.put(
    "/job-offers/{offer_id}", response_model=JobOfferOut, dependencies=[Depends(verify_csrf)]
)
def update_job_offer(
    offer_id: int,
    payload: JobOfferUpdate,
    current_user: AuthUser = Depends(require_role(UserRole.HR)),
    db: Session = Depends(get_db),
):
    offer = _load_offer_or_404(db, offer_id)
    for field, value in payload.model_dump().items():
        setattr(offer, field, value)
    db.flush()
    audit_service.log(
        db,
        entity_type="job_offer",
        entity_id=offer.id,
        action="updated",
        actor_user_id=current_user.id,
        actor_email=current_user.email,
        description=offer.titre,
    )
    db.commit()
    db.refresh(offer)
    count = (
        db.query(func.count(JobApplication.id))
        .filter(JobApplication.job_offer_id == offer.id)
        .scalar()
    )
    return _serialize_offer(offer, candidatures_count=count or 0)


# --------------------------------------------------------------- candidates --


@router.get("/candidates", response_model=list[CandidateOut])
def list_candidates(
    ville: str | None = None,
    favori: bool | None = None,
    q: str | None = None,
    current_user: AuthUser = Depends(require_role(*_READ_ROLES)),
    db: Session = Depends(get_db),
):
    query = db.query(Candidate).options(
        joinedload(Candidate.applications).joinedload(JobApplication.job_offer),
        joinedload(Candidate.applications).joinedload(JobApplication.stage),
    )
    if ville:
        query = query.filter(Candidate.ville.ilike(f"%{ville}%"))
    if favori is not None:
        query = query.filter(Candidate.favori == favori)
    if q:
        like = f"%{q}%"
        query = query.filter(
            (Candidate.nom_complet.ilike(like))
            | (Candidate.email.ilike(like))
            | (Candidate.telephone.ilike(like))
        )
    candidates = query.order_by(Candidate.nom_complet).all()
    return [_serialize_candidate(c) for c in candidates]


@router.post(
    "/candidates",
    response_model=CandidateCreateResult,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(verify_csrf)],
)
def create_candidate(
    payload: CandidateCreate,
    current_user: AuthUser = Depends(require_role(UserRole.HR)),
    db: Session = Depends(get_db),
):
    duplicates = recruitment_service.find_duplicate_candidates(
        db, email=payload.email, telephone=payload.telephone
    )
    candidate = Candidate(**payload.model_dump())
    db.add(candidate)
    db.flush()
    audit_service.log(
        db,
        entity_type="candidate",
        entity_id=candidate.id,
        action="created",
        actor_user_id=current_user.id,
        actor_email=current_user.email,
        description=candidate.nom_complet,
    )
    db.commit()
    db.refresh(candidate)
    return CandidateCreateResult(
        candidate=_serialize_candidate(candidate),
        duplicates=[_serialize_candidate(d) for d in duplicates],
    )


@router.put(
    "/candidates/{candidate_id}", response_model=CandidateOut, dependencies=[Depends(verify_csrf)]
)
def update_candidate(
    candidate_id: int,
    payload: CandidateUpdate,
    current_user: AuthUser = Depends(require_role(UserRole.HR)),
    db: Session = Depends(get_db),
):
    candidate = _load_candidate_or_404(db, candidate_id)
    for field, value in payload.model_dump().items():
        setattr(candidate, field, value)
    db.flush()
    audit_service.log(
        db,
        entity_type="candidate",
        entity_id=candidate.id,
        action="updated",
        actor_user_id=current_user.id,
        actor_email=current_user.email,
        description=candidate.nom_complet,
    )
    db.commit()
    db.refresh(candidate)
    return _serialize_candidate(candidate)


# ------------------------------------------------------- candidate attachments --


@router.post(
    "/candidates/{candidate_id}/attachments",
    response_model=CandidateAttachmentOut,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(verify_csrf)],
)
async def upload_candidate_attachment(
    candidate_id: int,
    type_document: str,
    file: UploadFile = File(...),
    current_user: AuthUser = Depends(require_role(UserRole.HR)),
    db: Session = Depends(get_db),
):
    _load_candidate_or_404(db, candidate_id)
    content = await file.read()
    if len(content) > storage_service.MAX_UPLOAD_BYTES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Fichier trop volumineux (limite : 10 Mo).",
        )
    key = storage_service.build_key("candidates", candidate_id, file.filename or "fichier")
    try:
        storage_service.get_storage().save(key, content)
    except storage_service.StorageServiceError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    attachment = CandidateAttachment(
        candidate_id=candidate_id,
        type_document=type_document,
        nom_fichier=file.filename or "fichier",
        storage_key=key,
        content_type=file.content_type or "application/octet-stream",
        taille_octets=len(content),
        uploaded_by_user_id=current_user.id,
    )
    db.add(attachment)
    db.flush()
    audit_service.log(
        db,
        entity_type="candidate",
        entity_id=candidate_id,
        action="attachment_added",
        actor_user_id=current_user.id,
        actor_email=current_user.email,
        description=attachment.nom_fichier,
    )
    db.commit()
    db.refresh(attachment)
    return _serialize_attachment(attachment)


@router.get("/candidates/{candidate_id}/attachments/{attachment_id}/download")
def download_candidate_attachment(
    candidate_id: int,
    attachment_id: int,
    current_user: AuthUser = Depends(require_role(*_READ_ROLES)),
    db: Session = Depends(get_db),
):
    attachment = _load_attachment_or_404(db, candidate_id, attachment_id)
    content = storage_service.get_storage().read(attachment.storage_key)
    return Response(
        content=content,
        media_type=attachment.content_type,
        headers={"Content-Disposition": f'attachment; filename="{attachment.nom_fichier}"'},
    )


@router.delete(
    "/candidates/{candidate_id}/attachments/{attachment_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(verify_csrf)],
)
def delete_candidate_attachment(
    candidate_id: int,
    attachment_id: int,
    current_user: AuthUser = Depends(require_role(UserRole.HR)),
    db: Session = Depends(get_db),
):
    attachment = _load_attachment_or_404(db, candidate_id, attachment_id)
    storage_service.get_storage().delete(attachment.storage_key)
    db.delete(attachment)
    audit_service.log(
        db,
        entity_type="candidate",
        entity_id=candidate_id,
        action="attachment_deleted",
        actor_user_id=current_user.id,
        actor_email=current_user.email,
        description=attachment.nom_fichier,
    )
    db.commit()


@router.post(
    "/candidates/extract-cv",
    response_model=CvFields,
    dependencies=[Depends(verify_csrf)],
)
async def extract_cv_fields(
    file: UploadFile = File(...),
    current_user: AuthUser = Depends(require_role(UserRole.HR)),
    db: Session = Depends(get_db),
):
    """HR-09 (partial): suggests candidate fields from an uploaded CV — never
    authoritative, no candidate is created here. Sends the file's content to
    Google's Gemini API for extraction (see .env.example for the CNDP caveat)."""
    content = await file.read()
    if len(content) > storage_service.MAX_UPLOAD_BYTES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Fichier trop volumineux (limite : 10 Mo).",
        )
    try:
        fields = cv_extraction_service.extract_fields(
            content, file.content_type or "application/octet-stream", file.filename or "fichier"
        )
    except cv_extraction_service.CvExtractionError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)
        ) from exc

    audit_service.log(
        db,
        entity_type="candidate",
        entity_id=0,  # no candidate exists yet at extraction time; AuditLog.entity_id is NOT NULL
        action="cv_extraction_used",
        actor_user_id=current_user.id,
        actor_email=current_user.email,
        description=file.filename or "fichier",
    )
    db.commit()
    return fields


@router.post(
    "/job-offers/{offer_id}/bulk-import-cvs",
    response_model=BulkCvImportResult,
    dependencies=[Depends(verify_csrf)],
)
async def bulk_import_cvs(
    offer_id: int,
    files: list[UploadFile] = File(...),
    current_user: AuthUser = Depends(require_role(UserRole.HR)),
    db: Session = Depends(get_db),
):
    """One offer, many CVs in one go: each file is extracted, matched
    against the existing CV bank (same email/phone reuses that candidate
    rather than duplicating them), attached, and put on this offer's
    pipeline. Each file gets its own SAVEPOINT so one bad file (corrupt
    upload, extraction failure) can't roll back the ones before it."""
    _load_offer_or_404(db, offer_id)
    items: list[BulkCvImportItem] = []

    for file in files:
        filename = file.filename or "fichier"
        content = await file.read()
        if len(content) > storage_service.MAX_UPLOAD_BYTES:
            items.append(
                BulkCvImportItem(
                    filename=filename,
                    status="error",
                    message="Fichier trop volumineux (limite : 10 Mo).",
                )
            )
            continue

        savepoint = db.begin_nested()
        try:
            extraction_error: str | None = None
            try:
                fields = cv_extraction_service.extract_fields(
                    content, file.content_type or "application/octet-stream", filename
                )
            except cv_extraction_service.CvExtractionError as exc:
                fields = CvFields()
                extraction_error = str(exc)

            duplicates = recruitment_service.find_duplicate_candidates(
                db, email=fields.email, telephone=fields.telephone
            )
            candidate = duplicates[0] if duplicates else None
            created_new = candidate is None
            if candidate is None:
                candidate = Candidate(
                    nom_complet=fields.nom_complet or Path(filename).stem,
                    telephone=fields.telephone,
                    email=fields.email,
                    ville=fields.ville,
                    experience_resume=fields.experience_resume,
                    competences=fields.competences,
                    diplomes=fields.diplomes,
                    langues=fields.langues,
                )
                db.add(candidate)
                db.flush()
                audit_service.log(
                    db,
                    entity_type="candidate",
                    entity_id=candidate.id,
                    action="created",
                    actor_user_id=current_user.id,
                    actor_email=current_user.email,
                    description=candidate.nom_complet,
                )

            key = storage_service.build_key("candidates", candidate.id, filename)
            storage_service.get_storage().save(key, content)
            attachment = CandidateAttachment(
                candidate_id=candidate.id,
                type_document="CV",
                nom_fichier=filename,
                storage_key=key,
                content_type=file.content_type or "application/octet-stream",
                taille_octets=len(content),
                uploaded_by_user_id=current_user.id,
            )
            db.add(attachment)
            db.flush()

            try:
                application = recruitment_service.create_application(
                    db, candidate_id=candidate.id, job_offer_id=offer_id, responsable=None
                )
            except recruitment_service.RecruitmentServiceError:
                savepoint.commit()
                items.append(
                    BulkCvImportItem(
                        filename=filename,
                        status="already_applied",
                        message="Ce candidat a déjà une candidature sur cette offre.",
                        candidate=_serialize_candidate(candidate),
                    )
                )
                continue

            audit_service.log(
                db,
                entity_type="job_application",
                entity_id=application.id,
                action="created",
                actor_user_id=current_user.id,
                actor_email=current_user.email,
            )
            savepoint.commit()
            items.append(
                BulkCvImportItem(
                    filename=filename,
                    status="created" if created_new else "linked_existing",
                    message=extraction_error,
                    candidate=_serialize_candidate(candidate),
                    application=_serialize_application(application),
                )
            )
        except Exception as exc:  # noqa: BLE001 — isolate this file, keep the batch going
            savepoint.rollback()
            items.append(BulkCvImportItem(filename=filename, status="error", message=str(exc)))

    db.commit()
    return BulkCvImportResult(items=items)


# ------------------------------------------------------------- applications --


@router.get("/applications", response_model=list[JobApplicationOut])
def list_applications(
    job_offer_id: int,
    current_user: AuthUser = Depends(require_role(*_READ_ROLES)),
    db: Session = Depends(get_db),
):
    applications = (
        db.query(JobApplication)
        .options(
            joinedload(JobApplication.candidate),
            joinedload(JobApplication.job_offer),
            joinedload(JobApplication.stage),
        )
        .filter(JobApplication.job_offer_id == job_offer_id)
        .all()
    )
    return [_serialize_application(a) for a in applications]


@router.post(
    "/applications",
    response_model=JobApplicationOut,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(verify_csrf)],
)
def create_application(
    payload: JobApplicationCreate,
    current_user: AuthUser = Depends(require_role(UserRole.HR)),
    db: Session = Depends(get_db),
):
    _load_candidate_or_404(db, payload.candidate_id)
    _load_offer_or_404(db, payload.job_offer_id)
    try:
        application = recruitment_service.create_application(
            db,
            candidate_id=payload.candidate_id,
            job_offer_id=payload.job_offer_id,
            responsable=payload.responsable,
            stage_id=payload.stage_id,
        )
    except recruitment_service.RecruitmentServiceError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Ce candidat a déjà une candidature sur cette offre.",
        ) from exc

    audit_service.log(
        db,
        entity_type="job_application",
        entity_id=application.id,
        action="created",
        actor_user_id=current_user.id,
        actor_email=current_user.email,
    )
    db.commit()
    application = _load_application_or_404(db, application.id)
    return _serialize_application(application)


@router.put(
    "/applications/{application_id}/stage",
    response_model=JobApplicationOut,
    dependencies=[Depends(verify_csrf)],
)
def update_application_stage(
    application_id: int,
    payload: StageUpdate,
    current_user: AuthUser = Depends(require_role(UserRole.HR)),
    db: Session = Depends(get_db),
):
    application = _load_application_or_404(db, application_id)
    stage = db.get(ApplicationStage, payload.stage_id)
    if stage is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Étape introuvable.")
    recruitment_service.move_stage(db, application, payload.stage_id)
    audit_service.log(
        db,
        entity_type="job_application",
        entity_id=application.id,
        action="stage_changed",
        actor_user_id=current_user.id,
        actor_email=current_user.email,
        description=stage.libelle,
    )
    db.commit()
    db.refresh(application)
    return _serialize_application(application)


@router.delete(
    "/applications/{application_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(verify_csrf)],
)
def withdraw_application(
    application_id: int,
    current_user: AuthUser = Depends(require_role(UserRole.HR)),
    db: Session = Depends(get_db),
):
    application = _load_application_or_404(db, application_id)
    candidate_nom = application.candidate.nom_complet
    job_offer_titre = application.job_offer.titre
    recruitment_service.delete_application(db, application)
    audit_service.log(
        db,
        entity_type="job_application",
        entity_id=application_id,
        action="deleted",
        actor_user_id=current_user.id,
        actor_email=current_user.email,
        description=f"{candidate_nom} — {job_offer_titre}",
    )
    db.commit()


@router.get("/applications/{application_id}/comments", response_model=list[ApplicationCommentOut])
def list_comments(
    application_id: int,
    current_user: AuthUser = Depends(require_role(*_READ_ROLES)),
    db: Session = Depends(get_db),
):
    _load_application_or_404(db, application_id)
    comments = (
        db.query(ApplicationComment)
        .options(joinedload(ApplicationComment.auteur))
        .filter(ApplicationComment.application_id == application_id)
        .order_by(ApplicationComment.created_at.desc())
        .all()
    )
    return [_serialize_comment(c) for c in comments]


@router.post(
    "/applications/{application_id}/comments",
    response_model=ApplicationCommentOut,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(verify_csrf)],
)
def add_comment(
    application_id: int,
    payload: ApplicationCommentCreate,
    current_user: AuthUser = Depends(require_role(UserRole.HR)),
    db: Session = Depends(get_db),
):
    _load_application_or_404(db, application_id)
    comment = ApplicationComment(
        application_id=application_id, texte=payload.texte, auteur_user_id=current_user.id
    )
    db.add(comment)
    db.flush()
    audit_service.log(
        db,
        entity_type="job_application",
        entity_id=application_id,
        action="comment_added",
        actor_user_id=current_user.id,
        actor_email=current_user.email,
    )
    db.commit()
    db.refresh(comment)
    return _serialize_comment(comment)


# -------------------------------------------------------------------- hire --


@router.get("/applications/{application_id}/hire-preview", response_model=HirePreviewOut)
def get_hire_preview(
    application_id: int,
    current_user: AuthUser = Depends(require_role(UserRole.HR)),
    db: Session = Depends(get_db),
):
    application = _load_application_or_404(db, application_id)
    return recruitment_service.hire_preview(db, application)


@router.post(
    "/applications/{application_id}/hire",
    response_model=EmployeeOut,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(verify_csrf)],
)
def hire_from_application(
    application_id: int,
    payload: HireRequest,
    current_user: AuthUser = Depends(require_role(UserRole.HR)),
    db: Session = Depends(get_db),
):
    application = _load_application_or_404(db, application_id)
    try:
        employee = recruitment_service.hire_candidate(
            db, application, payload, current_user_id=current_user.id
        )
    except recruitment_service.RecruitmentServiceError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    audit_service.log(
        db,
        entity_type="job_application",
        entity_id=application.id,
        action="hired",
        actor_user_id=current_user.id,
        actor_email=current_user.email,
        description=f"employee_id={employee.id}",
    )
    db.commit()
    db.refresh(employee)
    return _serialize_employee(employee)


@router.get("/applications/stagnantes", response_model=list[StalledApplicationOut])
def list_stalled_applications(
    current_user: AuthUser = Depends(require_role(UserRole.HR)),
    db: Session = Depends(get_db),
):
    return recruitment_service.stalled_applications(db)
