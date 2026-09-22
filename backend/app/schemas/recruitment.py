from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel


class JobOfferStatusOut(BaseModel):
    id: int
    libelle: str
    couleur: str

    model_config = {"from_attributes": True}


class ApplicationStageOut(BaseModel):
    id: int
    libelle: str
    ordre: int
    couleur: str
    is_hire_stage: bool

    model_config = {"from_attributes": True}


class JobOfferOut(BaseModel):
    id: int
    titre: str
    ville: str | None
    department_id: int | None
    department_nom: str | None
    position_id: int | None
    position_intitule: str | None
    status_id: int
    status_libelle: str
    status_couleur: str
    description: str | None
    responsable: str | None
    date_creation: datetime
    date_cloture: date | None
    candidatures_count: int


class JobOfferCreate(BaseModel):
    titre: str
    ville: str | None = None
    department_id: int | None = None
    position_id: int | None = None
    status_id: int
    description: str | None = None
    responsable: str | None = None
    date_cloture: date | None = None


class JobOfferUpdate(JobOfferCreate):
    pass


class CandidateAttachmentOut(BaseModel):
    id: int
    type_document: str
    nom_fichier: str
    content_type: str
    taille_octets: int
    uploaded_by_email: str
    created_at: datetime


class CandidateApplicationOut(BaseModel):
    id: int
    job_offer_id: int
    job_offer_titre: str
    stage_libelle: str | None


class CandidateOut(BaseModel):
    id: int
    nom_complet: str
    telephone: str | None
    email: str | None
    ville: str | None
    annees_experience: Decimal | None
    experience_resume: str | None
    competences: str | None
    diplomes: str | None
    langues: str | None
    favori: bool
    notes: str | None
    employee_id: int | None
    date_ajout: datetime
    attachments: list[CandidateAttachmentOut]
    applications: list[CandidateApplicationOut]

    model_config = {"from_attributes": True}


class CandidateCreate(BaseModel):
    nom_complet: str
    telephone: str | None = None
    email: str | None = None
    ville: str | None = None
    annees_experience: Decimal | None = None
    experience_resume: str | None = None
    competences: str | None = None
    diplomes: str | None = None
    langues: str | None = None
    favori: bool = False
    notes: str | None = None


class CandidateUpdate(CandidateCreate):
    pass


class CandidateCreateResult(BaseModel):
    candidate: CandidateOut
    duplicates: list[CandidateOut]


class JobApplicationOut(BaseModel):
    id: int
    candidate_id: int
    candidate_nom: str
    candidate_ville: str | None
    job_offer_id: int
    job_offer_titre: str
    stage_id: int | None
    stage_libelle: str | None
    responsable: str | None
    date_creation: datetime
    date_dernier_mouvement: datetime


class JobApplicationCreate(BaseModel):
    candidate_id: int
    job_offer_id: int
    responsable: str | None = None
    stage_id: int | None = None


class BulkCvImportItem(BaseModel):
    filename: str
    # "created" | "linked_existing" | "already_applied" | "error"
    status: str
    message: str | None = None
    candidate: CandidateOut | None = None
    application: JobApplicationOut | None = None


class BulkCvImportResult(BaseModel):
    items: list[BulkCvImportItem]


class StageUpdate(BaseModel):
    stage_id: int


class ApplicationCommentOut(BaseModel):
    id: int
    application_id: int
    texte: str
    auteur_email: str
    created_at: datetime


class ApplicationCommentCreate(BaseModel):
    texte: str


class HirePreviewOut(BaseModel):
    prenom_suggere: str
    nom_suggere: str
    telephone: str | None
    email: str | None
    ville: str | None
    department_id: int | None
    department_nom: str | None
    cv_disponible: bool


class HireRequest(BaseModel):
    prenom: str
    nom: str
    telephone: str | None = None
    email: str | None = None
    ville: str | None = None
    department_id: int | None = None
    position_id: int | None = None
    categorie_professionnelle: str | None = None
    date_embauche: date | None = None
    date_fin_periode_essai: date | None = None


class StalledApplicationOut(BaseModel):
    application_id: int
    candidate_nom: str
    job_offer_titre: str
    stage_libelle: str | None
    date_dernier_mouvement: datetime
    jours_stagnation: int
