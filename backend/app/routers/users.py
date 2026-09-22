from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session, joinedload

from app.database import get_db
from app.dependencies import AuthUser, require_role, verify_csrf
from app.models import Employee, User
from app.models.enums import UserRole
from app.schemas.employee import EmployeeLite
from app.schemas.user import PasswordReset, UserCreate, UserOut, UserUpdate
from app.services import audit_service, employee_service, user_service

router = APIRouter(prefix="/api/users", tags=["users"])


def _serialize_user(user: User) -> UserOut:
    return UserOut(
        id=user.id,
        email=user.email,
        role=user.role,
        employee_id=user.employee_id,
        employee_nom=user.employee.full_name if user.employee else None,
        is_active=user.is_active,
        last_login_at=user.last_login_at,
        created_at=user.created_at,
    )


def _load_user_or_404(db: Session, user_id: int) -> User:
    user = db.get(User, user_id)
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Compte introuvable.")
    return user


@router.get("", response_model=list[UserOut])
def list_users(
    current_user: AuthUser = Depends(require_role(UserRole.HR)),
    db: Session = Depends(get_db),
):
    users = db.query(User).order_by(User.role, User.email).all()
    return [_serialize_user(u) for u in users]


@router.get("/employees-sans-compte", response_model=list[EmployeeLite])
def list_employees_without_account(
    current_user: AuthUser = Depends(require_role(UserRole.HR)),
    db: Session = Depends(get_db),
):
    linked_ids = {uid for (uid,) in db.query(User.employee_id).filter(User.employee_id.isnot(None))}
    employees = (
        db.query(Employee)
        .options(
            joinedload(Employee.department),
            joinedload(Employee.position),
            joinedload(Employee.status),
        )
        .order_by(Employee.nom, Employee.prenom)
        .all()
    )
    return [
        employee_service.serialize_employee_lite(e) for e in employees if e.id not in linked_ids
    ]


@router.post(
    "",
    response_model=UserOut,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(verify_csrf)],
)
def create_user(
    payload: UserCreate,
    current_user: AuthUser = Depends(require_role(UserRole.HR)),
    db: Session = Depends(get_db),
):
    try:
        user = user_service.create_user(db, payload)
    except user_service.UserServiceError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    audit_service.log(
        db,
        entity_type="user",
        entity_id=user.id,
        action="created",
        actor_user_id=current_user.id,
        actor_email=current_user.email,
        description=f"{user.email} ({user.role.value})",
    )
    db.commit()
    db.refresh(user)
    return _serialize_user(user)


@router.put("/{user_id}", response_model=UserOut, dependencies=[Depends(verify_csrf)])
def update_user(
    user_id: int,
    payload: UserUpdate,
    current_user: AuthUser = Depends(require_role(UserRole.HR)),
    db: Session = Depends(get_db),
):
    user = _load_user_or_404(db, user_id)
    try:
        user_service.update_user(db, user, payload)
    except user_service.UserServiceError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    audit_service.log(
        db,
        entity_type="user",
        entity_id=user.id,
        action="updated",
        actor_user_id=current_user.id,
        actor_email=current_user.email,
        description=f"role={user.role.value} actif={user.is_active}",
    )
    db.commit()
    db.refresh(user)
    return _serialize_user(user)


@router.post(
    "/{user_id}/reset-password", response_model=UserOut, dependencies=[Depends(verify_csrf)]
)
def reset_password(
    user_id: int,
    payload: PasswordReset,
    current_user: AuthUser = Depends(require_role(UserRole.HR)),
    db: Session = Depends(get_db),
):
    user = _load_user_or_404(db, user_id)
    user_service.reset_password(db, user, payload.password)

    audit_service.log(
        db,
        entity_type="user",
        entity_id=user.id,
        action="password_reset",
        actor_user_id=current_user.id,
        actor_email=current_user.email,
        description=user.email,
    )
    db.commit()
    db.refresh(user)
    return _serialize_user(user)
