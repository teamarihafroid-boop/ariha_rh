from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, field_validator

from app.models.enums import LeaveRequestStatus


class LeaveRequestCreate(BaseModel):
    employee_id: int
    leave_type_id: int
    date_debut: date
    date_fin: date
    commentaire: str | None = None

    @field_validator("date_fin")
    @classmethod
    def check_range(cls, v: date, info):
        debut = info.data.get("date_debut")
        if debut and v < debut:
            raise ValueError("La date de fin doit être postérieure ou égale à la date de début.")
        return v


class LeaveDecisionRequest(BaseModel):
    comment: str | None = None


class LeaveRequestOut(BaseModel):
    id: int
    employee_id: int
    employee_nom: str
    leave_type_id: int
    leave_type_libelle: str
    date_debut: date
    date_fin: date
    nb_jours: Decimal
    commentaire: str | None
    status: LeaveRequestStatus
    submitted_by_user_id: int
    decided_by_user_id: int | None
    decision_comment: str | None
    decided_at: datetime | None
    created_at: datetime

    model_config = {"from_attributes": True}


class LeaveBalanceOut(BaseModel):
    employee_id: int
    leave_type_id: int
    leave_type_libelle: str
    annee: int
    jours_acquis: Decimal
    jours_pris: Decimal
    solde: Decimal


class LeaveBalanceUpsert(BaseModel):
    employee_id: int
    leave_type_id: int
    annee: int
    jours_acquis: Decimal


class LeaveCalendarEntry(BaseModel):
    id: int
    employee_id: int
    employee_nom: str
    leave_type_libelle: str
    couleur: str
    date_debut: date
    date_fin: date
    nb_jours: Decimal
    status: LeaveRequestStatus


class LeaveCalendarResponse(BaseModel):
    conges: list[LeaveCalendarEntry]
    jours_feries: list[dict]
