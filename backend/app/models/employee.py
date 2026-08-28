from __future__ import annotations

from datetime import date, datetime
from typing import TYPE_CHECKING

from sqlalchemy import Date, DateTime, ForeignKey, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base

if TYPE_CHECKING:
    from app.models.department import Department
    from app.models.employee_status import EmployeeStatus
    from app.models.position import Position
    from app.models.user import User


class Employee(Base):
    """Trimmed to what auth/RBAC and the leave module need. Full HR-record CRUD
    (CIN, CNSS, salaire, documents, ...) is a later module, not this slice."""

    __tablename__ = "employees"

    id: Mapped[int] = mapped_column(primary_key=True)
    matricule: Mapped[str | None] = mapped_column(String(30), unique=True, nullable=True)
    nom: Mapped[str] = mapped_column(String(80), nullable=False)
    prenom: Mapped[str] = mapped_column(String(80), nullable=False)
    date_embauche: Mapped[date | None] = mapped_column(Date, nullable=True)
    date_sortie: Mapped[date | None] = mapped_column(Date, nullable=True)
    email: Mapped[str | None] = mapped_column(String(150), nullable=True)
    telephone: Mapped[str | None] = mapped_column(String(30), nullable=True)

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

    @property
    def full_name(self) -> str:
        return f"{self.prenom} {self.nom}"
