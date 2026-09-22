from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import AuthUser, get_current_user, require_role, verify_csrf
from app.models import EmployeeStatus, Position
from app.models.enums import UserRole
from app.schemas.reference import (
    EmployeeStatusOut,
    PositionCreate,
    PositionOut,
    PositionUpdate,
)
from app.services import audit_service

router = APIRouter(prefix="/api", tags=["reference"])


@router.get("/positions", response_model=list[PositionOut])
def list_positions(
    include_inactive: bool = False,
    current_user: AuthUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    query = db.query(Position)
    if not (include_inactive and current_user.role == UserRole.HR):
        query = query.filter(Position.is_active.is_(True))
    return query.order_by(Position.intitule).all()


@router.post(
    "/positions",
    response_model=PositionOut,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(verify_csrf)],
)
def create_position(
    payload: PositionCreate,
    current_user: AuthUser = Depends(require_role(UserRole.HR)),
    db: Session = Depends(get_db),
):
    position = Position(intitule=payload.intitule, department_id=payload.department_id)
    db.add(position)
    db.flush()

    audit_service.log(
        db,
        entity_type="position",
        entity_id=position.id,
        action="created",
        actor_user_id=current_user.id,
        actor_email=current_user.email,
        description=position.intitule,
    )
    db.commit()
    db.refresh(position)
    return position


@router.put(
    "/positions/{position_id}", response_model=PositionOut, dependencies=[Depends(verify_csrf)]
)
def update_position(
    position_id: int,
    payload: PositionUpdate,
    current_user: AuthUser = Depends(require_role(UserRole.HR)),
    db: Session = Depends(get_db),
):
    position = db.get(Position, position_id)
    if position is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Poste introuvable.")
    position.intitule = payload.intitule
    position.department_id = payload.department_id
    position.is_active = payload.is_active
    db.flush()

    audit_service.log(
        db,
        entity_type="position",
        entity_id=position.id,
        action="updated",
        actor_user_id=current_user.id,
        actor_email=current_user.email,
        description=position.intitule,
    )
    db.commit()
    db.refresh(position)
    return position


@router.get("/employee-statuses", response_model=list[EmployeeStatusOut])
def list_employee_statuses(
    current_user: AuthUser = Depends(get_current_user), db: Session = Depends(get_db)
):
    return db.query(EmployeeStatus).order_by(EmployeeStatus.libelle).all()
