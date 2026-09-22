from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import Date, DateTime, ForeignKey, Numeric, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base

if TYPE_CHECKING:
    from app.models.department import Department
    from app.models.emergency_contact import EmergencyContact
    from app.models.employee_document import EmployeeDocument
    from app.models.employee_equipment import EmployeeEquipment
    from app.models.employee_status import EmployeeStatus
    from app.models.position import Position
    from app.models.probation_evaluation import ProbationEvaluation
    from app.models.user import User


class Employee(Base):
    """Full HR record (§6.1 of the PRD): identity, contract, and legal-ID
    fields, plus emergency contacts and probation evaluations as satellite
    tables. Document/photo attachments are deliberately not modeled yet —
    they need object storage (see TECHNICAL_DECISIONS.md §7), which isn't
    provisioned yet."""

    __tablename__ = "employees"

    id: Mapped[int] = mapped_column(primary_key=True)
    matricule: Mapped[str | None] = mapped_column(String(30), unique=True, nullable=True)
    nom: Mapped[str] = mapped_column(String(80), nullable=False)
    prenom: Mapped[str] = mapped_column(String(80), nullable=False)
    nom_arabe: Mapped[str | None] = mapped_column(String(100), nullable=True)
    prenom_arabe: Mapped[str | None] = mapped_column(String(100), nullable=True)
    date_naissance: Mapped[date | None] = mapped_column(Date, nullable=True)
    lieu_naissance: Mapped[str | None] = mapped_column(String(100), nullable=True)
    date_embauche: Mapped[date | None] = mapped_column(Date, nullable=True)
    date_sortie: Mapped[date | None] = mapped_column(Date, nullable=True)
    motif_sortie: Mapped[str | None] = mapped_column(String(255), nullable=True)
    date_fin_periode_essai: Mapped[date | None] = mapped_column(Date, nullable=True)
    email: Mapped[str | None] = mapped_column(String(150), nullable=True)
    telephone: Mapped[str | None] = mapped_column(String(30), nullable=True)
    ville: Mapped[str | None] = mapped_column(String(100), nullable=True)
    adresse: Mapped[str | None] = mapped_column(String(255), nullable=True)
    cin: Mapped[str | None] = mapped_column(String(30), nullable=True)
    cnss: Mapped[str | None] = mapped_column(String(30), nullable=True)
    type_contrat: Mapped[str | None] = mapped_column(String(30), nullable=True)
    # "cadre" ou "salarie" — utilisé ailleurs pour des règles de paie, pas encore construites ici.
    categorie_professionnelle: Mapped[str | None] = mapped_column(String(20), nullable=True)
    salaire_base: Mapped[Decimal | None] = mapped_column(Numeric(10, 2), nullable=True)
    salaire_net: Mapped[Decimal | None] = mapped_column(Numeric(10, 2), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Free-text sub-team label (e.g. "Logistique", "Caisse") used only to
    # group siblings under a synthetic team box on the org chart — not a
    # real reporting relationship, so it doesn't need its own table.
    equipe: Mapped[str | None] = mapped_column(String(80), nullable=True)

    department_id: Mapped[int | None] = mapped_column(ForeignKey("departments.id"), nullable=True)
    position_id: Mapped[int | None] = mapped_column(ForeignKey("positions.id"), nullable=True)
    status_id: Mapped[int | None] = mapped_column(ForeignKey("employee_statuses.id"), nullable=True)
    manager_id: Mapped[int | None] = mapped_column(ForeignKey("employees.id"), nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    department: Mapped[Department | None] = relationship(
        "Department", back_populates="employees", foreign_keys=[department_id]
    )
    position: Mapped[Position | None] = relationship("Position", back_populates="employees")
    status: Mapped[EmployeeStatus | None] = relationship("EmployeeStatus")
    manager: Mapped[Employee | None] = relationship("Employee", remote_side=[id])
    user: Mapped[User | None] = relationship(
        "User", back_populates="employee", uselist=False, foreign_keys="User.employee_id"
    )
    emergency_contacts: Mapped[list[EmergencyContact]] = relationship(
        "EmergencyContact", back_populates="employee", cascade="all, delete-orphan"
    )
    probation_evaluations: Mapped[list[ProbationEvaluation]] = relationship(
        "ProbationEvaluation", back_populates="employee", cascade="all, delete-orphan"
    )
    documents: Mapped[list[EmployeeDocument]] = relationship(
        "EmployeeDocument", back_populates="employee", cascade="all, delete-orphan"
    )
    equipements: Mapped[list[EmployeeEquipment]] = relationship(
        "EmployeeEquipment", back_populates="employee", cascade="all, delete-orphan"
    )

    @property
    def full_name(self) -> str:
        return f"{self.prenom} {self.nom}"
