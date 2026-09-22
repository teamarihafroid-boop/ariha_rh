from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import AuthUser, get_current_user, require_role, verify_csrf
from app.models import Department, Employee
from app.models.enums import UserRole
from app.schemas.reference import (
    DepartmentCreate,
    DepartmentOut,
    DepartmentUpdate,
    SetLeaveResponsableRequest,
)
from app.services import audit_service

router = APIRouter(prefix="/api/departments", tags=["departments"])


@router.get("", response_model=list[DepartmentOut])
def list_departments(
    include_inactive: bool = False,
    current_user: AuthUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    query = db.query(Department)
    if not (include_inactive and current_user.role == UserRole.HR):
        query = query.filter(Department.is_active.is_(True))
    return query.order_by(Department.nom).all()


@router.post(
    "",
    response_model=DepartmentOut,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(verify_csrf)],
)
def create_department(
    payload: DepartmentCreate,
    current_user: AuthUser = Depends(require_role(UserRole.HR)),
    db: Session = Depends(get_db),
):
    department = Department(nom=payload.nom, description=payload.description)
    db.add(department)
    try:
        db.flush()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Un département porte déjà ce nom.",
        ) from exc

    audit_service.log(
        db,
        entity_type="department",
        entity_id=department.id,
        action="created",
        actor_user_id=current_user.id,
        actor_email=current_user.email,
        description=department.nom,
    )
    db.commit()
    db.refresh(department)
    return department


@router.put("/{department_id}", response_model=DepartmentOut, dependencies=[Depends(verify_csrf)])
def update_department(
    department_id: int,
    payload: DepartmentUpdate,
    current_user: AuthUser = Depends(require_role(UserRole.HR)),
    db: Session = Depends(get_db),
):
    department = db.get(Department, department_id)
    if department is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Département introuvable."
        )
    department.nom = payload.nom
    department.description = payload.description
    department.is_active = payload.is_active
    try:
        db.flush()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Un département porte déjà ce nom.",
        ) from exc

    audit_service.log(
        db,
        entity_type="department",
        entity_id=department.id,
        action="updated",
        actor_user_id=current_user.id,
        actor_email=current_user.email,
        description=department.nom,
    )
    db.commit()
    db.refresh(department)
    return department


@router.patch(
    "/{department_id}/leave-responsable",
    response_model=DepartmentOut,
    dependencies=[Depends(verify_csrf)],
)
def set_leave_responsable(
    department_id: int,
    payload: SetLeaveResponsableRequest,
    current_user: AuthUser = Depends(require_role(UserRole.HR)),
    db: Session = Depends(get_db),
):
    department = db.get(Department, department_id)
    if department is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Département introuvable."
        )

    if payload.employee_id is not None:
        employee = db.get(Employee, payload.employee_id)
        if employee is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Collaborateur introuvable."
            )
        if employee.department_id != department.id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Le responsable congés doit appartenir au département.",
            )

    department.leave_responsable_employee_id = payload.employee_id
    db.flush()
    audit_service.log(
        db,
        entity_type="department",
        entity_id=department.id,
        action="leave_responsable_updated",
        actor_user_id=current_user.id,
        actor_email=current_user.email,
        description=f"Responsable congés défini sur employee_id={payload.employee_id}",
    )
    db.commit()
    db.refresh(department)
    return department
