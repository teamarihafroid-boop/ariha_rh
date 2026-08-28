from __future__ import annotations

from dataclasses import dataclass

from fastapi import Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Department, Employee, User
from app.models.enums import UserRole
from app.services.session_store import SESSION_COOKIE_NAME, get_csrf_token, load_session


@dataclass
class AuthUser:
    id: int
    role: UserRole
    employee_id: int | None
    email: str
    department_id: int | None = None


def get_current_user(request: Request, db: Session = Depends(get_db)) -> AuthUser:
    signed_sid = request.cookies.get(SESSION_COOKIE_NAME)
    session = load_session(signed_sid)
    if session is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Non authentifié.")
    user = db.get(User, session.user_id)
    if user is None or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Compte introuvable ou désactivé."
        )
    department_id = None
    if user.employee_id is not None:
        employee = db.get(Employee, user.employee_id)
        department_id = employee.department_id if employee else None
    return AuthUser(
        id=user.id,
        role=user.role,
        employee_id=user.employee_id,
        email=user.email,
        department_id=department_id,
    )


def require_role(*roles: UserRole):
    def _dependency(current_user: AuthUser = Depends(get_current_user)) -> AuthUser:
        if current_user.role not in roles:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Accès refusé.")
        return current_user

    return _dependency


def verify_csrf(request: Request) -> None:
    if request.method in ("GET", "HEAD", "OPTIONS"):
        return
    signed_sid = request.cookies.get(SESSION_COOKIE_NAME)
    expected = get_csrf_token(signed_sid)
    provided = request.headers.get("X-CSRF-Token")
    if not expected or not provided or expected != provided:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Jeton CSRF invalide.")


def can_submit_leave_for(db: Session, current_user: AuthUser, target_employee_id: int) -> bool:
    """The one narrow leave-responsable capability check (RESP-01..03) — used
    only on POST /leave-requests, grants nothing else. HR can always submit
    on anyone's behalf (matches HR-18's "HR remains sole approval authority"
    posture, which also implies HR can log leave directly as before)."""
    if current_user.role == UserRole.HR:
        return True
    if current_user.role != UserRole.EMPLOYEE or current_user.employee_id is None:
        return False

    target = db.get(Employee, target_employee_id)
    if target is None:
        return False

    department = db.get(Department, target.department_id) if target.department_id else None
    has_responsable = (
        department is not None and department.leave_responsable_employee_id is not None
    )
    is_the_responsable = (
        has_responsable and department.leave_responsable_employee_id == current_user.employee_id
    )

    if is_the_responsable:
        # RESP-01: the responsable submits for the whole department,
        # including themselves — not just their colleagues.
        return True

    if current_user.employee_id == target_employee_id:
        # EMP-03: self-submission only allowed when the department has no
        # designated leave-responsable (and current user isn't the
        # responsable, already handled above).
        return not has_responsable

    # A regular (non-responsable) employee may never submit for a colleague.
    return False
