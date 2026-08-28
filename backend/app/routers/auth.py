from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from sqlalchemy.orm import Session

from app.config import get_settings
from app.database import get_db
from app.dependencies import AuthUser, get_current_user, verify_csrf
from app.models import Employee
from app.schemas.auth import LoginRequest, MeResponse
from app.services import auth_service
from app.services.session_store import (
    CSRF_COOKIE_NAME,
    SESSION_COOKIE_NAME,
    create_session,
    destroy_session,
)

router = APIRouter(prefix="/api/auth", tags=["auth"])
settings = get_settings()


@router.post("/login", response_model=MeResponse)
def login(payload: LoginRequest, response: Response, db: Session = Depends(get_db)):
    user = auth_service.authenticate(db, payload.email, payload.password)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Identifiants invalides."
        )
    db.commit()

    signed_sid, csrf_token = create_session(user.id, user.role.value, user.employee_id)
    response.set_cookie(
        SESSION_COOKIE_NAME,
        signed_sid,
        httponly=True,
        secure=settings.cookie_secure,
        samesite="lax",
        max_age=settings.session_absolute_ttl_seconds,
    )
    response.set_cookie(
        CSRF_COOKIE_NAME,
        csrf_token,
        httponly=False,
        secure=settings.cookie_secure,
        samesite="lax",
        max_age=settings.session_absolute_ttl_seconds,
    )
    department_id = None
    if user.employee_id is not None:
        employee = db.get(Employee, user.employee_id)
        department_id = employee.department_id if employee else None
    return MeResponse(
        id=user.id,
        email=user.email,
        role=user.role,
        employee_id=user.employee_id,
        department_id=department_id,
    )


@router.post("/logout", dependencies=[Depends(verify_csrf)])
def logout(request: Request, response: Response):
    destroy_session(request.cookies.get(SESSION_COOKIE_NAME))
    response.delete_cookie(SESSION_COOKIE_NAME)
    response.delete_cookie(CSRF_COOKIE_NAME)
    return {"ok": True}


@router.get("/me", response_model=MeResponse)
def me(current_user: AuthUser = Depends(get_current_user)):
    return MeResponse(
        id=current_user.id,
        email=current_user.email,
        role=current_user.role,
        employee_id=current_user.employee_id,
        department_id=current_user.department_id,
    )
