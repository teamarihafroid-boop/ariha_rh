from __future__ import annotations

from datetime import date, datetime
from typing import TYPE_CHECKING

from sqlalchemy import Date, DateTime, ForeignKey, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base

if TYPE_CHECKING:
    from app.models.employee import Employee


class ProbationEvaluation(Base):
    """avis_dg/evaluateur_dg are data fields only — DG never gets an in-app
    write route (PRD §5/§6.6: DG's probation input happens outside the app,
    HR records the resulting decision here, same posture as recruitment)."""

    __tablename__ = "probation_evaluations"

    id: Mapped[int] = mapped_column(primary_key=True)
    employee_id: Mapped[int] = mapped_column(ForeignKey("employees.id"), nullable=False)
    date_evaluation: Mapped[date] = mapped_column(Date, nullable=False)
    avis_rh: Mapped[str | None] = mapped_column(Text, nullable=True)
    evaluateur_rh: Mapped[str | None] = mapped_column(String(120), nullable=True)
    avis_dg: Mapped[str | None] = mapped_column(Text, nullable=True)
    evaluateur_dg: Mapped[str | None] = mapped_column(String(120), nullable=True)
    # "Confirmé" / "Prolongé" / "Rompu"
    decision: Mapped[str | None] = mapped_column(String(20), nullable=True)
    nouvelle_date_fin: Mapped[date | None] = mapped_column(Date, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    employee: Mapped[Employee] = relationship("Employee", back_populates="probation_evaluations")
