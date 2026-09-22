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
    employee_requestable: bool
    certificate_kind: str | None

    model_config = {"from_attributes": True}


class LeaveTypeCreate(BaseModel):
    libelle: str
    couleur: str = "#0288D1"
    deduit_du_solde: bool = True
    accrual_legal: bool = False
    code_court: str | None = None
    employee_requestable: bool = True
    certificate_kind: str | None = None


class LeaveTypeUpdate(BaseModel):
    libelle: str
    couleur: str
    deduit_du_solde: bool
    accrual_legal: bool
    is_active: bool
    code_court: str | None = None
    employee_requestable: bool = True
    certificate_kind: str | None = None


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
    is_active: bool

    model_config = {"from_attributes": True}


class DepartmentCreate(BaseModel):
    nom: str
    description: str | None = None


class DepartmentUpdate(BaseModel):
    nom: str
    description: str | None = None
    is_active: bool = True


class SetLeaveResponsableRequest(BaseModel):
    employee_id: int | None


class PositionOut(BaseModel):
    id: int
    intitule: str
    department_id: int | None
    is_active: bool

    model_config = {"from_attributes": True}


class PositionCreate(BaseModel):
    intitule: str
    department_id: int | None = None


class PositionUpdate(BaseModel):
    intitule: str
    department_id: int | None = None
    is_active: bool = True


class EmployeeStatusOut(BaseModel):
    id: int
    libelle: str
    couleur: str
    is_active_status: bool

    model_config = {"from_attributes": True}
