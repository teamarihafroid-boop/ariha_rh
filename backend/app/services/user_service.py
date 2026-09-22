from __future__ import annotations

from sqlalchemy.orm import Session

from app.core.security import hash_password
from app.models import Employee, User
from app.models.enums import UserRole
from app.schemas.user import UserCreate, UserUpdate


class UserServiceError(ValueError):
    pass


def _check_email_unique(db: Session, email: str, *, exclude_id: int | None) -> None:
    query = db.query(User).filter(User.email == email)
    if exclude_id is not None:
        query = query.filter(User.id != exclude_id)
    if query.first() is not None:
        raise UserServiceError(f"L'adresse « {email} » est déjà utilisée par un autre compte.")


def _check_employee_linkable(
    db: Session, employee_id: int | None, *, exclude_id: int | None
) -> None:
    if employee_id is None:
        return
    employee = db.get(Employee, employee_id)
    if employee is None:
        raise UserServiceError("Collaborateur introuvable.")
    query = db.query(User).filter(User.employee_id == employee_id)
    if exclude_id is not None:
        query = query.filter(User.id != exclude_id)
    if query.first() is not None:
        raise UserServiceError("Ce collaborateur a déjà un compte lié.")


def _check_not_last_active_hr(db: Session, user: User, *, will_stay_active_hr: bool) -> None:
    if will_stay_active_hr:
        return
    if user.role != UserRole.HR or not user.is_active:
        return
    other_active_hr = (
        db.query(User)
        .filter(User.role == UserRole.HR, User.is_active.is_(True), User.id != user.id)
        .first()
    )
    if other_active_hr is None:
        raise UserServiceError(
            "Impossible : ce compte est le dernier compte RH actif. "
            "Créez ou réactivez un autre compte RH avant de modifier celui-ci."
        )


def create_user(db: Session, payload: UserCreate) -> User:
    _check_email_unique(db, payload.email, exclude_id=None)
    _check_employee_linkable(db, payload.employee_id, exclude_id=None)
    user = User(
        email=payload.email,
        password_hash=hash_password(payload.password),
        role=payload.role,
        employee_id=payload.employee_id,
        is_active=True,
    )
    db.add(user)
    db.flush()
    return user


def update_user(db: Session, user: User, payload: UserUpdate) -> User:
    _check_employee_linkable(db, payload.employee_id, exclude_id=user.id)
    will_stay_active_hr = payload.role == UserRole.HR and payload.is_active
    _check_not_last_active_hr(db, user, will_stay_active_hr=will_stay_active_hr)

    user.role = payload.role
    user.employee_id = payload.employee_id
    user.is_active = payload.is_active
    db.flush()
    return user


def reset_password(db: Session, user: User, new_password: str) -> User:
    user.password_hash = hash_password(new_password)
    db.flush()
    return user
