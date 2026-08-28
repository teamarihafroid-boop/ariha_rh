from __future__ import annotations

from sqlalchemy import Boolean, String
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class EmployeeStatus(Base):
    __tablename__ = "employee_statuses"

    id: Mapped[int] = mapped_column(primary_key=True)
    libelle: Mapped[str] = mapped_column(String(60), unique=True, nullable=False)
    couleur: Mapped[str] = mapped_column(String(20), default="#9E9E9E")
    is_active_status: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
