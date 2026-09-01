from __future__ import annotations

from datetime import date

from pydantic import BaseModel


class LeaveTypeOut(BaseModel):
    id: int
    libelle: str
    couleur: str
    deduit_du_solde: bool
    accrual_legal: bool
    is_active: bool
    code_court: str | None

    model_config = {"from_attributes": True}


class LeaveTypeCreate(BaseModel):
    libelle: str
    couleur: str = "#0288D1"
    deduit_du_solde: bool = True
    accrual_legal: bool = False
    code_court: str | None = None


class LeaveTypeUpdate(BaseModel):
    libelle: str
    couleur: str
    deduit_du_solde: bool
    accrual_legal: bool
    is_active: bool
    code_court: str | None = None


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
