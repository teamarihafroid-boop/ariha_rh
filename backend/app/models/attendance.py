from __future__ import annotations

from datetime import date, datetime
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, Date, DateTime, ForeignKey, Index, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base

if TYPE_CHECKING:
    from app.models.employee import Employee
    from app.models.user import User


class AttendanceCode(Base):
    """Reference data for a pointeuse/timesheet cell value: 'P' = présent,
    'A' = absence, etc. HR defines these before importing (mirrors how
    LeaveType works for congé)."""

    __tablename__ = "attendance_codes"

    id: Mapped[int] = mapped_column(primary_key=True)
    libelle: Mapped[str] = mapped_column(String(60), unique=True, nullable=False)
    code_court: Mapped[str] = mapped_column(String(8), unique=True, nullable=False)
    couleur: Mapped[str] = mapped_column(String(20), default="#607D8B")
    compte_absence: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class AttendanceImport(Base):
    """One row per confirmed timesheet import — audit trail for HR-16."""

    __tablename__ = "attendance_imports"

    id: Mapped[int] = mapped_column(primary_key=True)
    nom_fichier: Mapped[str] = mapped_column(String(255), nullable=False)
    mois: Mapped[int] = mapped_column(nullable=False)
    annee: Mapped[int] = mapped_column(nullable=False)
    importe_par_user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    nb_lignes_importees: Mapped[int] = mapped_column(nullable=False, default=0)
    nb_lignes_non_reconnues: Mapped[int] = mapped_column(nullable=False, default=0)
    noms_non_reconnus: Mapped[str | None] = mapped_column(String(2000), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    importe_par: Mapped[User] = relationship("User")


class AttendanceEntry(Base):
    """One employee/day pointeuse cell. Upserted on re-import of the same
    employee+date (never silently duplicated — see the unique constraint)."""

    __tablename__ = "attendance_entries"
    __table_args__ = (
        UniqueConstraint("employee_id", "date", name="uq_attendance_entries_employee_date"),
        Index("ix_attendance_entries_date", "date"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    employee_id: Mapped[int] = mapped_column(ForeignKey("employees.id"), nullable=False)
    date: Mapped[date] = mapped_column(Date, nullable=False)
    code_id: Mapped[int | None] = mapped_column(ForeignKey("attendance_codes.id"), nullable=True)
    valeur_brute: Mapped[str | None] = mapped_column(String(60), nullable=True)
    import_id: Mapped[int | None] = mapped_column(
        ForeignKey("attendance_imports.id"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    employee: Mapped[Employee] = relationship("Employee")
    code: Mapped[AttendanceCode | None] = relationship("AttendanceCode")
