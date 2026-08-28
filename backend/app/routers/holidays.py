from __future__ import annotations

from datetime import date as date_type

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import AuthUser, get_current_user, require_role, verify_csrf
from app.models import Holiday
from app.models.enums import UserRole
from app.schemas.reference import HolidayIn, HolidayOut
from app.services import audit_service, holiday_service

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


@router.post(
    "/generate-fixed",
    response_model=list[HolidayOut],
    dependencies=[Depends(verify_csrf)],
)
def generate_fixed_holidays(
    annee: int,
    current_user: AuthUser = Depends(require_role(UserRole.HR)),
    db: Session = Depends(get_db),
):
    """Generates Morocco's fixed-date civil holidays for the given year
    (idempotent — safe to call again). Mobile Islamic holidays still need to
    be added manually via POST /holidays once their dates are confirmed —
    see holiday_service.py for why those can't be computed."""
    created = holiday_service.generate_fixed_holidays(db, annee)
    if created:
        audit_service.log(
            db,
            entity_type="holiday",
            entity_id=annee,
            action="generated_fixed",
            actor_user_id=current_user.id,
            actor_email=current_user.email,
            description=f"{len(created)} jour(s) férié(s) fixe(s) généré(s) pour {annee}",
        )
        db.commit()
    return (
        db.query(Holiday)
        .filter(Holiday.date.between(date_type(annee, 1, 1), date_type(annee, 12, 31)))
        .order_by(Holiday.date)
        .all()
    )


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
