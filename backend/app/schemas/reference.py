from __future__ import annotations

from datetime import date

from pydantic import BaseModel


class LeaveTypeOut(BaseModel):
    id: int
    libelle: str
    couleur: str
    deduit_du_solde: bool

    model_config = {"from_attributes": True}


class HolidayIn(BaseModel):
    date: date
    libelle: str


class HolidayOut(HolidayIn):
    id: int

    model_config = {"from_attributes": True}


class DepartmentOut(BaseModel):
    id: int
    nom: str
    description: str | None
    leave_responsable_employee_id: int | None

    model_config = {"from_attributes": True}


class SetLeaveResponsableRequest(BaseModel):
    employee_id: int | None
