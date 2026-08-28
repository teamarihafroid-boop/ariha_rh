from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, Integer, Numeric, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base

if TYPE_CHECKING:
    from app.models.employee import Employee
    from app.models.leave_type import LeaveType


class LeaveBalance(Base):
    """jours_acquis is entered manually (no automatic legal accrual rule is
    presumed) — same deliberate choice as the prototype. jours_pris/solde are
    computed at read time by leave_service, never stored here."""

    __tablename__ = "leave_balances"
    __table_args__ = (
        UniqueConstraint(
            "employee_id", "leave_type_id", "annee", name="uq_leave_balance_emp_type_year"
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    employee_id: Mapped[int] = mapped_column(ForeignKey("employees.id"), nullable=False)
    leave_type_id: Mapped[int] = mapped_column(ForeignKey("leave_types.id"), nullable=False)
    annee: Mapped[int] = mapped_column(Integer, nullable=False)
    jours_acquis: Mapped[Decimal] = mapped_column(Numeric(5, 1), default=0, nullable=False)
    updated_by_user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    employee: Mapped[Employee] = relationship("Employee")
    leave_type: Mapped[LeaveType] = relationship("LeaveType")
