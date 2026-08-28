from __future__ import annotations

import calendar as cal
from datetime import date, timedelta
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session, joinedload

from app.database import get_db
from app.dependencies import (
    AuthUser,
    can_submit_leave_for,
    get_current_user,
    require_role,
    verify_csrf,
)
from app.models import Employee, Holiday, LeaveRequest, LeaveRequestStatus, LeaveType
from app.models.enums import UserRole
from app.schemas.leave import (
    LeaveBalanceOut,
    LeaveBalanceUpsert,
    LeaveCalendarEntry,
    LeaveCalendarResponse,
    LeaveDecisionRequest,
    LeaveRequestCreate,
    LeaveRequestOut,
)
from app.services import audit_service, leave_service, notification_service

router = APIRouter(prefix="/api", tags=["leave"])

TEMPLATES_DIR = Path(__file__).resolve().parent.parent / "templates"
templates = Jinja2Templates(directory=str(TEMPLATES_DIR))


def _serialize(r: LeaveRequest) -> LeaveRequestOut:
    return LeaveRequestOut(
        id=r.id,
        employee_id=r.employee_id,
        employee_nom=r.employee.full_name,
        leave_type_id=r.leave_type_id,
        leave_type_libelle=r.leave_type.libelle,
        date_debut=r.date_debut,
        date_fin=r.date_fin,
        nb_jours=r.nb_jours,
        commentaire=r.commentaire,
        status=r.status,
        submitted_by_user_id=r.submitted_by_user_id,
        decided_by_user_id=r.decided_by_user_id,
        decision_comment=r.decision_comment,
        decided_at=r.decided_at,
        created_at=r.created_at,
    )


def _load_request_or_404(db: Session, request_id: int) -> LeaveRequest:
    request = (
        db.query(LeaveRequest)
        .options(joinedload(LeaveRequest.employee), joinedload(LeaveRequest.leave_type))
        .filter(LeaveRequest.id == request_id)
        .first()
    )
    if request is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Demande introuvable.")
    return request


def _assert_visible(request: LeaveRequest, current_user: AuthUser) -> None:
    if current_user.role == UserRole.EMPLOYEE and request.employee_id != current_user.employee_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Demande introuvable.")


# ---------------------------------------------------------------- requests --


@router.post(
    "/leave-requests",
    response_model=LeaveRequestOut,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(verify_csrf)],
)
def create_leave_request(
    payload: LeaveRequestCreate,
    current_user: AuthUser = Depends(require_role(UserRole.HR, UserRole.EMPLOYEE)),
    db: Session = Depends(get_db),
):
    if not can_submit_leave_for(db, current_user, payload.employee_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Vous ne pouvez pas soumettre de demande de congé pour ce collaborateur.",
        )
    try:
        request = leave_service.create_request(
            db,
            employee_id=payload.employee_id,
            leave_type_id=payload.leave_type_id,
            date_debut=payload.date_debut,
            date_fin=payload.date_fin,
            commentaire=payload.commentaire,
            submitted_by_user_id=current_user.id,
        )
    except leave_service.LeaveServiceError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    audit_service.log(
        db,
        entity_type="leave_request",
        entity_id=request.id,
        action="created",
        actor_user_id=current_user.id,
        actor_email=current_user.email,
        description=f"Demande de congé créée pour employee_id={request.employee_id}",
    )
    db.commit()
    db.refresh(request)
    return _serialize(request)


@router.get("/leave-requests", response_model=list[LeaveRequestOut])
def list_leave_requests(
    status_filter: LeaveRequestStatus | None = Query(None, alias="status"),
    annee: int | None = None,
    employee_id: int | None = None,
    department_id: int | None = None,
    current_user: AuthUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    query = db.query(LeaveRequest).options(
        joinedload(LeaveRequest.employee), joinedload(LeaveRequest.leave_type)
    )

    if current_user.role == UserRole.EMPLOYEE:
        # Employee's own requests only, regardless of what employee_id was passed.
        query = query.filter(LeaveRequest.employee_id == current_user.employee_id)
    elif employee_id is not None:
        query = query.filter(LeaveRequest.employee_id == employee_id)

    if department_id is not None and current_user.role in (UserRole.HR, UserRole.DG):
        query = query.join(Employee, LeaveRequest.employee_id == Employee.id).filter(
            Employee.department_id == department_id
        )

    if status_filter is not None:
        query = query.filter(LeaveRequest.status == status_filter)
    if annee is not None:
        year_start, year_end = date(annee, 1, 1), date(annee, 12, 31)
        query = query.filter(
            LeaveRequest.date_debut <= year_end, LeaveRequest.date_fin >= year_start
        )

    requests = query.order_by(LeaveRequest.date_debut.desc()).all()
    return [_serialize(r) for r in requests]


@router.get("/leave-requests/{request_id}", response_model=LeaveRequestOut)
def get_leave_request(
    request_id: int,
    current_user: AuthUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    request = _load_request_or_404(db, request_id)
    _assert_visible(request, current_user)
    return _serialize(request)


@router.post(
    "/leave-requests/{request_id}/approve",
    response_model=LeaveRequestOut,
    dependencies=[Depends(verify_csrf)],
)
def approve_leave_request(
    request_id: int,
    payload: LeaveDecisionRequest,
    current_user: AuthUser = Depends(require_role(UserRole.HR)),
    db: Session = Depends(get_db),
):
    request = _load_request_or_404(db, request_id)
    try:
        leave_service.approve_request(
            db, request, decided_by_user_id=current_user.id, comment=payload.comment
        )
    except leave_service.LeaveServiceError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc

    notification_service.notify_leave_decision(db, request, approved=True)
    audit_service.log(
        db,
        entity_type="leave_request",
        entity_id=request.id,
        action="approved",
        actor_user_id=current_user.id,
        actor_email=current_user.email,
    )
    db.commit()
    db.refresh(request)
    return _serialize(request)


@router.post(
    "/leave-requests/{request_id}/reject",
    response_model=LeaveRequestOut,
    dependencies=[Depends(verify_csrf)],
)
def reject_leave_request(
    request_id: int,
    payload: LeaveDecisionRequest,
    current_user: AuthUser = Depends(require_role(UserRole.HR)),
    db: Session = Depends(get_db),
):
    request = _load_request_or_404(db, request_id)
    try:
        leave_service.reject_request(
            db, request, decided_by_user_id=current_user.id, comment=payload.comment or ""
        )
    except leave_service.LeaveServiceError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    notification_service.notify_leave_decision(db, request, approved=False)
    audit_service.log(
        db,
        entity_type="leave_request",
        entity_id=request.id,
        action="rejected",
        actor_user_id=current_user.id,
        actor_email=current_user.email,
        description=payload.comment,
    )
    db.commit()
    db.refresh(request)
    return _serialize(request)


@router.post(
    "/leave-requests/{request_id}/cancel",
    response_model=LeaveRequestOut,
    dependencies=[Depends(verify_csrf)],
)
def cancel_leave_request(
    request_id: int,
    current_user: AuthUser = Depends(require_role(UserRole.HR, UserRole.EMPLOYEE)),
    db: Session = Depends(get_db),
):
    request = _load_request_or_404(db, request_id)
    if current_user.role == UserRole.EMPLOYEE and request.employee_id != current_user.employee_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Demande introuvable.")
    try:
        leave_service.cancel_request(db, request)
    except leave_service.LeaveServiceError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc

    audit_service.log(
        db,
        entity_type="leave_request",
        entity_id=request.id,
        action="cancelled",
        actor_user_id=current_user.id,
        actor_email=current_user.email,
    )
    db.commit()
    db.refresh(request)
    return _serialize(request)


@router.get("/leave-requests/{request_id}/certificate")
def leave_certificate(
    request_id: int,
    http_request: Request,
    current_user: AuthUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    request = _load_request_or_404(db, request_id)
    _assert_visible(request, current_user)
    if request.status != LeaveRequestStatus.APPROVED:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Le certificat n'est disponible qu'une fois la demande approuvée.",
        )

    employee = request.employee
    repos = []
    d = request.date_debut
    while d <= request.date_fin:
        if d.weekday() == 6:
            repos.append(d)
        d += timedelta(days=1)
    feries = (
        db.query(Holiday)
        .filter(Holiday.date >= request.date_debut, Holiday.date <= request.date_fin)
        .order_by(Holiday.date)
        .all()
    )
    repos_labels = ", ".join(d.strftime("%d/%m/%Y") for d in repos)
    feries_labels = ", ".join(f"{h.date.strftime('%d/%m/%Y')} ({h.libelle})" for h in feries)

    annee = request.date_debut.year
    jours_acquis = leave_service.jours_acquis_effectifs(
        db, employee.id, request.leave_type_id, annee
    )
    jours_pris_total = leave_service.jours_pris(db, employee.id, request.leave_type_id, annee)
    solde_apres = jours_acquis - jours_pris_total
    solde_avant = solde_apres + request.nb_jours

    return templates.TemplateResponse(
        http_request,
        "leave_certificate.html",
        {
            "entry": request,
            "employee": employee,
            "numero": f"{annee % 100:02d}{request.id:03d}",
            "date_retour": request.date_fin + timedelta(days=1),
            "repos_labels": repos_labels,
            "feries_labels": feries_labels,
            "solde_avant": solde_avant,
            "solde_apres": solde_apres,
        },
    )


# ---------------------------------------------------------------- balances --


@router.get("/leave-balances", response_model=list[LeaveBalanceOut])
def list_leave_balances(
    annee: int,
    employee_id: int | None = None,
    current_user: AuthUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if current_user.role == UserRole.EMPLOYEE:
        target_employee_id = current_user.employee_id
    else:
        target_employee_id = employee_id

    if target_employee_id is None:
        if current_user.role == UserRole.EMPLOYEE:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail="Employé sans fiche associée."
            )
        employees = db.query(Employee).all()
    else:
        employee = db.get(Employee, target_employee_id)
        if employee is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Collaborateur introuvable."
            )
        employees = [employee]

    leave_types = db.query(LeaveType).all()
    results: list[LeaveBalanceOut] = []
    for emp in employees:
        for lt in leave_types:
            jours_acquis = leave_service.jours_acquis_effectifs(db, emp.id, lt.id, annee)
            pris = leave_service.jours_pris(db, emp.id, lt.id, annee)
            results.append(
                LeaveBalanceOut(
                    employee_id=emp.id,
                    leave_type_id=lt.id,
                    leave_type_libelle=lt.libelle,
                    annee=annee,
                    jours_acquis=jours_acquis,
                    jours_pris=pris,
                    solde=jours_acquis - pris,
                )
            )
    db.commit()
    return results


@router.put("/leave-balances", response_model=LeaveBalanceOut, dependencies=[Depends(verify_csrf)])
def upsert_leave_balance(
    payload: LeaveBalanceUpsert,
    current_user: AuthUser = Depends(require_role(UserRole.HR)),
    db: Session = Depends(get_db),
):
    leave_type = db.get(LeaveType, payload.leave_type_id)
    if leave_type is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Type de congé introuvable."
        )
    if leave_type.accrual_legal:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                "Le solde de ce type de congé est calculé automatiquement à partir de "
                "l'ancienneté (date d'embauche). Corrigez la date d'embauche du collaborateur "
                "si le solde affiché est incorrect, plutôt que de le modifier manuellement."
            ),
        )

    balance = leave_service.get_or_create_balance(
        db, payload.employee_id, payload.leave_type_id, payload.annee
    )
    balance.jours_acquis = payload.jours_acquis
    balance.updated_by_user_id = current_user.id
    db.flush()
    pris = leave_service.jours_pris(db, payload.employee_id, payload.leave_type_id, payload.annee)
    audit_service.log(
        db,
        entity_type="leave_balance",
        entity_id=balance.id,
        action="updated",
        actor_user_id=current_user.id,
        actor_email=current_user.email,
        description=f"jours_acquis={payload.jours_acquis}",
    )
    db.commit()
    return LeaveBalanceOut(
        employee_id=balance.employee_id,
        leave_type_id=balance.leave_type_id,
        leave_type_libelle=balance.leave_type.libelle,
        annee=balance.annee,
        jours_acquis=balance.jours_acquis,
        jours_pris=pris,
        solde=balance.jours_acquis - pris,
    )


# ---------------------------------------------------------------- calendar --


@router.get("/leave-calendar", response_model=LeaveCalendarResponse)
def leave_calendar(
    mois: int,
    annee: int,
    current_user: AuthUser = Depends(require_role(UserRole.HR, UserRole.DG)),
    db: Session = Depends(get_db),
):
    nb_jours = cal.monthrange(annee, mois)[1]
    start, end = date(annee, mois, 1), date(annee, mois, nb_jours)

    requests = (
        db.query(LeaveRequest)
        .options(joinedload(LeaveRequest.employee), joinedload(LeaveRequest.leave_type))
        .filter(
            LeaveRequest.date_debut <= end,
            LeaveRequest.date_fin >= start,
            LeaveRequest.status.in_([LeaveRequestStatus.APPROVED, LeaveRequestStatus.PENDING]),
        )
        .all()
    )
    conges = [
        LeaveCalendarEntry(
            id=r.id,
            employee_id=r.employee_id,
            employee_nom=r.employee.full_name,
            leave_type_libelle=r.leave_type.libelle,
            couleur=r.leave_type.couleur,
            date_debut=r.date_debut,
            date_fin=r.date_fin,
            nb_jours=r.nb_jours,
            status=r.status,
        )
        for r in requests
    ]
    feries = db.query(Holiday).filter(Holiday.date >= start, Holiday.date <= end).all()
    return LeaveCalendarResponse(
        conges=conges,
        jours_feries=[
            {"id": h.id, "date": h.date.isoformat(), "libelle": h.libelle} for h in feries
        ],
    )
