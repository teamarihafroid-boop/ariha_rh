from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import AuthUser, get_current_user, require_role, verify_csrf
from app.models import Holiday
from app.models.enums import UserRole
from app.schemas.reference import HolidayIn, HolidayOut
from app.services import audit_service

router = APIRouter(prefix="/api/holidays", tags=["holidays"])


@router.get("", response_model=list[HolidayOut])
def list_holidays(
    current_user: AuthUser = Depends(get_current_user), db: Session = Depends(get_db)
):
    return db.query(Holiday).order_by(Holiday.date).all()


@router.post(
    "",
    response_model=HolidayOut,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(verify_csrf)],
)
def create_holiday(
    payload: HolidayIn,
    current_user: AuthUser = Depends(require_role(UserRole.HR)),
    db: Session = Depends(get_db),
):
    holiday = Holiday(date=payload.date, libelle=payload.libelle)
    db.add(holiday)
    db.flush()
    audit_service.log(
        db,
        entity_type="holiday",
        entity_id=holiday.id,
        action="created",
        actor_user_id=current_user.id,
        actor_email=current_user.email,
        description=f"Jour férié créé : {holiday.libelle}",
    )
    db.commit()
    db.refresh(holiday)
    return holiday


@router.delete(
    "/{holiday_id}", status_code=status.HTTP_204_NO_CONTENT, dependencies=[Depends(verify_csrf)]
)
def delete_holiday(
    holiday_id: int,
    current_user: AuthUser = Depends(require_role(UserRole.HR)),
    db: Session = Depends(get_db),
):
    holiday = db.get(Holiday, holiday_id)
    if holiday is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Jour férié introuvable.")
    audit_service.log(
        db,
        entity_type="holiday",
        entity_id=holiday.id,
        action="deleted",
        actor_user_id=current_user.id,
        actor_email=current_user.email,
        description=f"Jour férié supprimé : {holiday.libelle}",
    )
    db.delete(holiday)
    db.commit()
