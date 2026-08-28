from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base

if TYPE_CHECKING:
    from app.models.employee import Employee
    from app.models.position import Position


class Department(Base):
    __tablename__ = "departments"

    id: Mapped[int] = mapped_column(primary_key=True)
    nom: Mapped[str] = mapped_column(String(120), unique=True, nullable=False)
    description: Mapped[str | None] = mapped_column(String(255), nullable=True)
    # use_alter=True: departments -> employees -> positions -> departments is
    # a genuine FK cycle (Employee.department_id, Position.department_id,
    # this column). Marking this edge deferred lets create_all/drop_all (and
    # Alembic autogenerate) topologically sort the other three tables and
    # add/drop this one constraint via a separate ALTER TABLE.
    leave_responsable_employee_id: Mapped[int | None] = mapped_column(
        ForeignKey(
            "employees.id", use_alter=True, name="fk_departments_leave_responsable_employee_id"
        ),
        nullable=True,
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    employees: Mapped[list[Employee]] = relationship(
        "Employee", back_populates="department", foreign_keys="Employee.department_id"
    )
    leave_responsable: Mapped[Employee | None] = relationship(
        "Employee", foreign_keys=[leave_responsable_employee_id]
    )
    positions: Mapped[list[Position]] = relationship("Position", back_populates="department")
