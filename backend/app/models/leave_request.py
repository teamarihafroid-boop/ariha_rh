from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import CheckConstraint, Date, DateTime, ForeignKey, Index, Numeric, String, func
from sqlalchemy import Enum as SAEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models.enums import LeaveRequestStatus

if TYPE_CHECKING:
    from app.models.employee import Employee
    from app.models.leave_type import LeaveType
    from app.models.user import User


class LeaveRequest(Base):
    """Replaces the prototype's ungated LeaveEntry: approval is a status
    transition on this same row, not a separate entity. Only status=approved
    rows count against a balance (see leave_service.jours_pris)."""

    __tablename__ = "leave_requests"
    __table_args__ = (
        CheckConstraint("date_fin >= date_debut", name="ck_leave_requests_date_range"),
        Index("ix_leave_requests_employee_status", "employee_id", "status"),
        Index("ix_leave_requests_status", "status"),
        Index("ix_leave_requests_dates", "date_debut", "date_fin"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    employee_id: Mapped[int] = mapped_column(ForeignKey("employees.id"), nullable=False)
    leave_type_id: Mapped[int] = mapped_column(ForeignKey("leave_types.id"), nullable=False)
    date_debut: Mapped[date] = mapped_column(Date, nullable=False)
    date_fin: Mapped[date] = mapped_column(Date, nullable=False)
    nb_jours: Mapped[Decimal] = mapped_column(Numeric(5, 1), nullable=False)
    commentaire: Mapped[str | None] = mapped_column(String(255), nullable=True)
    status: Mapped[LeaveRequestStatus] = mapped_column(
        SAEnum(LeaveRequestStatus, name="leave_request_status"),
        default=LeaveRequestStatus.PENDING,
        nullable=False,
    )
    submitted_by_user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    decided_by_user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    decision_comment: Mapped[str | None] = mapped_column(String(255), nullable=True)
    decided_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    employee: Mapped[Employee] = relationship("Employee", foreign_keys=[employee_id])
    leave_type: Mapped[LeaveType] = relationship("LeaveType")
    submitted_by: Mapped[User] = relationship("User", foreign_keys=[submitted_by_user_id])
    decided_by: Mapped[User | None] = relationship("User", foreign_keys=[decided_by_user_id])
