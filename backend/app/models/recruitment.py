from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import (
    Boolean,
    Date,
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base

if TYPE_CHECKING:
    from app.models.department import Department
    from app.models.employee import Employee
    from app.models.position import Position
    from app.models.user import User


class JobOfferStatus(Base):
    __tablename__ = "job_offer_statuses"

    id: Mapped[int] = mapped_column(primary_key=True)
    libelle: Mapped[str] = mapped_column(String(60), unique=True, nullable=False)
    couleur: Mapped[str] = mapped_column(String(20), default="#607D8B")


class JobOffer(Base):
    __tablename__ = "job_offers"

    id: Mapped[int] = mapped_column(primary_key=True)
    titre: Mapped[str] = mapped_column(String(150), nullable=False)
    ville: Mapped[str | None] = mapped_column(String(100), nullable=True)
    department_id: Mapped[int | None] = mapped_column(ForeignKey("departments.id"), nullable=True)
    position_id: Mapped[int | None] = mapped_column(ForeignKey("positions.id"), nullable=True)
    status_id: Mapped[int] = mapped_column(ForeignKey("job_offer_statuses.id"), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    responsable: Mapped[str | None] = mapped_column(String(150), nullable=True)
    date_creation: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    date_cloture: Mapped[date | None] = mapped_column(Date, nullable=True)

    department: Mapped[Department | None] = relationship("Department")
    position: Mapped[Position | None] = relationship("Position")
    status: Mapped[JobOfferStatus] = relationship("JobOfferStatus")


class ApplicationStage(Base):
    """Kanban column. is_hire_stage replaces the prototype's fragile string
    match on a mutable libelle=="Accepté" to decide when to propose a hire."""

    __tablename__ = "application_stages"

    id: Mapped[int] = mapped_column(primary_key=True)
    libelle: Mapped[str] = mapped_column(String(60), unique=True, nullable=False)
    ordre: Mapped[int] = mapped_column(nullable=False, default=0)
    couleur: Mapped[str] = mapped_column(String(20), default="#607D8B")
    is_hire_stage: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)


class Candidate(Base):
    """CV-bank candidate. No file fields this round — entries are manual
    until object storage is provisioned for real CV upload/extraction."""

    __tablename__ = "candidates"

    id: Mapped[int] = mapped_column(primary_key=True)
    nom_complet: Mapped[str] = mapped_column(String(150), nullable=False)
    telephone: Mapped[str | None] = mapped_column(String(30), nullable=True)
    email: Mapped[str | None] = mapped_column(String(150), nullable=True)
    ville: Mapped[str | None] = mapped_column(String(100), nullable=True)
    annees_experience: Mapped[Decimal | None] = mapped_column(Numeric(4, 1), nullable=True)
    experience_resume: Mapped[str | None] = mapped_column(Text, nullable=True)
    competences: Mapped[str | None] = mapped_column(Text, nullable=True)
    diplomes: Mapped[str | None] = mapped_column(Text, nullable=True)
    langues: Mapped[str | None] = mapped_column(Text, nullable=True)
    favori: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    employee_id: Mapped[int | None] = mapped_column(ForeignKey("employees.id"), nullable=True)
    date_ajout: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    employee: Mapped[Employee | None] = relationship("Employee")
    attachments: Mapped[list[CandidateAttachment]] = relationship(
        "CandidateAttachment", back_populates="candidate", cascade="all, delete-orphan"
    )
    # Read-only: which offers this candidate is (or was) in the pipeline
    # for, so the CV bank list can show that without a separate lookup.
    applications: Mapped[list[JobApplication]] = relationship(
        "JobApplication", order_by="JobApplication.date_creation.desc()", viewonly=True
    )


class CandidateAttachment(Base):
    """HR-09 (partial): manually uploaded candidate files (CV, cover letter,
    diploma). Auto-extraction from the file is a separate, not-yet-built
    feature (depends on the AI Assistant module, PRD §6.10) — this only
    covers upload/download/delete."""

    __tablename__ = "candidate_attachments"

    id: Mapped[int] = mapped_column(primary_key=True)
    candidate_id: Mapped[int] = mapped_column(ForeignKey("candidates.id"), nullable=False)
    type_document: Mapped[str] = mapped_column(String(60), nullable=False)
    nom_fichier: Mapped[str] = mapped_column(String(255), nullable=False)
    storage_key: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    content_type: Mapped[str] = mapped_column(String(100), nullable=False)
    taille_octets: Mapped[int] = mapped_column(Integer, nullable=False)
    uploaded_by_user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    candidate: Mapped[Candidate] = relationship("Candidate", back_populates="attachments")
    uploaded_by: Mapped[User] = relationship("User")


class JobApplication(Base):
    __tablename__ = "job_applications"
    __table_args__ = (
        UniqueConstraint(
            "candidate_id", "job_offer_id", name="uq_job_applications_candidate_offer"
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    candidate_id: Mapped[int] = mapped_column(ForeignKey("candidates.id"), nullable=False)
    job_offer_id: Mapped[int] = mapped_column(ForeignKey("job_offers.id"), nullable=False)
    stage_id: Mapped[int | None] = mapped_column(ForeignKey("application_stages.id"), nullable=True)
    responsable: Mapped[str | None] = mapped_column(String(150), nullable=True)
    date_creation: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    date_dernier_mouvement: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    candidate: Mapped[Candidate] = relationship("Candidate")
    job_offer: Mapped[JobOffer] = relationship("JobOffer")
    stage: Mapped[ApplicationStage | None] = relationship("ApplicationStage")


class ApplicationComment(Base):
    """auteur_user_id is always the real authenticated actor — fixes the
    prototype's audit_service.current_user() bug (logs the host PC account)."""

    __tablename__ = "application_comments"

    id: Mapped[int] = mapped_column(primary_key=True)
    application_id: Mapped[int] = mapped_column(ForeignKey("job_applications.id"), nullable=False)
    texte: Mapped[str] = mapped_column(Text, nullable=False)
    auteur_user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    auteur: Mapped[User] = relationship("User")
