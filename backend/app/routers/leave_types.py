from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import AuthUser, get_current_user, require_role, verify_csrf
from app.models import LeaveType
from app.models.enums import UserRole
from app.schemas.reference import LeaveTypeCreate, LeaveTypeOut, LeaveTypeUpdate
from app.services import audit_service

router = APIRouter(prefix="/api/leave-types", tags=["leave-types"])


def _validate_accrual(deduit_du_solde: bool, accrual_legal: bool) -> None:
    if accrual_legal and not deduit_du_solde:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                "Un type de congé à accrual automatique doit obligatoirement déduire du " "solde."
            ),
        )


@router.get("", response_model=list[LeaveTypeOut])
def list_leave_types(
    include_inactive: bool = False,
    current_user: AuthUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    query = db.query(LeaveType)
    if not (include_inactive and current_user.role == UserRole.HR):
        query = query.filter(LeaveType.is_active.is_(True))
    return query.order_by(LeaveType.libelle).all()


@router.post(
    "",
    response_model=LeaveTypeOut,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(verify_csrf)],
)
def create_leave_type(
    payload: LeaveTypeCreate,
    current_user: AuthUser = Depends(require_role(UserRole.HR)),
    db: Session = Depends(get_db),
):
    _validate_accrual(payload.deduit_du_solde, payload.accrual_legal)
    leave_type = LeaveType(
        libelle=payload.libelle,
        couleur=payload.couleur,
        deduit_du_solde=payload.deduit_du_solde,
        accrual_legal=payload.accrual_legal,
        code_court=payload.code_court,
    )
    db.add(leave_type)
    try:
        db.flush()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Un type de congé porte déjà ce libellé.",
        ) from exc

    audit_service.log(
        db,
        entity_type="leave_type",
        entity_id=leave_type.id,
        action="created",
        actor_user_id=current_user.id,
        actor_email=current_user.email,
        description=leave_type.libelle,
    )
    db.commit()
    db.refresh(leave_type)
    return leave_type


@router.put("/{leave_type_id}", response_model=LeaveTypeOut, dependencies=[Depends(verify_csrf)])
def update_leave_type(
    leave_type_id: int,
    payload: LeaveTypeUpdate,
    current_user: AuthUser = Depends(require_role(UserRole.HR)),
    db: Session = Depends(get_db),
):
    leave_type = db.get(LeaveType, leave_type_id)
    if leave_type is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Type de congé introuvable."
        )
    _validate_accrual(payload.deduit_du_solde, payload.accrual_legal)

    leave_type.libelle = payload.libelle
    leave_type.couleur = payload.couleur
    leave_type.deduit_du_solde = payload.deduit_du_solde
    leave_type.accrual_legal = payload.accrual_legal
    leave_type.is_active = payload.is_active
    leave_type.code_court = payload.code_court
    try:
        db.flush()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Un type de congé porte déjà ce libellé.",
        ) from exc

    audit_service.log(
        db,
        entity_type="leave_type",
        entity_id=leave_type.id,
        action="updated",
        actor_user_id=current_user.id,
        actor_email=current_user.email,
        description=leave_type.libelle,
    )
    db.commit()
    db.refresh(leave_type)
    return leave_type
