from __future__ import annotations

from datetime import UTC, date, datetime, timedelta
from decimal import Decimal

from sqlalchemy.orm import Session

from app.models import Employee, Holiday, LeaveBalance, LeaveRequest, LeaveRequestStatus, LeaveType


class LeaveServiceError(ValueError):
    """Raised for business-rule violations the router should turn into 4xx."""


def jours_ouvres(db: Session, date_debut: date, date_fin: date) -> Decimal:
    """Counts every calendar day in [date_debut, date_fin] except Sunday and
    any date listed in `holidays`. Saturday IS a counted/worked day — Ariha
    Froid works Mon-Sat, verified against real historical leave records in
    the prototype this reimplements (HR/core/services/leave_service.py).
    Do not "fix" this as if it were a bug."""
    if date_fin < date_debut:
        return Decimal(0)

    holiday_dates = {
        h.date
        for h in db.query(Holiday.date)
        .filter(Holiday.date >= date_debut, Holiday.date <= date_fin)
        .all()
    }

    count = 0
    current = date_debut
    while current <= date_fin:
        if current.weekday() != 6 and current not in holiday_dates:  # 6 = Sunday
            count += 1
        current += timedelta(days=1)
    return Decimal(count)


def jours_pris(db: Session, employee_id: int, leave_type_id: int, annee: int) -> Decimal:
    """Sums approved leave requests for the given year. A request spanning two
    calendar years has its year-boundary portion recomputed via
    jours_ouvres() rather than double-counted, matching the prototype's
    read-time per-year attribution."""
    annee_debut = date(annee, 1, 1)
    annee_fin = date(annee, 12, 31)

    requests = (
        db.query(LeaveRequest)
        .filter(
            LeaveRequest.employee_id == employee_id,
            LeaveRequest.leave_type_id == leave_type_id,
            LeaveRequest.status == LeaveRequestStatus.APPROVED,
            LeaveRequest.date_debut <= annee_fin,
            LeaveRequest.date_fin >= annee_debut,
        )
        .all()
    )

    total = Decimal(0)
    for r in requests:
        if r.date_debut >= annee_debut and r.date_fin <= annee_fin:
            total += r.nb_jours
        else:
            segment_debut = max(r.date_debut, annee_debut)
            segment_fin = min(r.date_fin, annee_fin)
            total += jours_ouvres(db, segment_debut, segment_fin)
    return total


def get_or_create_balance(
    db: Session, employee_id: int, leave_type_id: int, annee: int
) -> LeaveBalance:
    balance = (
        db.query(LeaveBalance)
        .filter_by(employee_id=employee_id, leave_type_id=leave_type_id, annee=annee)
        .first()
    )
    if balance is None:
        balance = LeaveBalance(
            employee_id=employee_id,
            leave_type_id=leave_type_id,
            annee=annee,
            jours_acquis=Decimal(0),
        )
        db.add(balance)
        db.flush()
    return balance


def solde(db: Session, employee_id: int, leave_type_id: int, annee: int) -> Decimal:
    balance = get_or_create_balance(db, employee_id, leave_type_id, annee)
    return balance.jours_acquis - jours_pris(db, employee_id, leave_type_id, annee)


def create_request(
    db: Session,
    *,
    employee_id: int,
    leave_type_id: int,
    date_debut: date,
    date_fin: date,
    commentaire: str | None,
    submitted_by_user_id: int,
) -> LeaveRequest:
    if date_fin < date_debut:
        raise LeaveServiceError("La date de fin doit être postérieure ou égale à la date de début.")
    if db.get(Employee, employee_id) is None:
        raise LeaveServiceError("Collaborateur introuvable.")
    if db.get(LeaveType, leave_type_id) is None:
        raise LeaveServiceError("Type de congé introuvable.")

    nb_jours = jours_ouvres(db, date_debut, date_fin)
    if nb_jours <= 0:
        raise LeaveServiceError("La période sélectionnée ne contient aucun jour ouvré.")

    request = LeaveRequest(
        employee_id=employee_id,
        leave_type_id=leave_type_id,
        date_debut=date_debut,
        date_fin=date_fin,
        nb_jours=nb_jours,
        commentaire=commentaire,
        status=LeaveRequestStatus.PENDING,
        submitted_by_user_id=submitted_by_user_id,
    )
    db.add(request)
    db.flush()
    return request


def _require_pending(request: LeaveRequest) -> None:
    if request.status != LeaveRequestStatus.PENDING:
        raise LeaveServiceError(
            f"Cette demande n'est plus en attente (statut actuel : {request.status.value})."
        )


def approve_request(
    db: Session, request: LeaveRequest, *, decided_by_user_id: int, comment: str | None
) -> LeaveRequest:
    _require_pending(request)
    request.status = LeaveRequestStatus.APPROVED
    request.decided_by_user_id = decided_by_user_id
    request.decision_comment = comment
    request.decided_at = datetime.now(UTC)
    db.flush()
    return request


def reject_request(
    db: Session, request: LeaveRequest, *, decided_by_user_id: int, comment: str
) -> LeaveRequest:
    if not comment or not comment.strip():
        raise LeaveServiceError("Un motif est obligatoire pour refuser une demande.")
    _require_pending(request)
    request.status = LeaveRequestStatus.REJECTED
    request.decided_by_user_id = decided_by_user_id
    request.decision_comment = comment
    request.decided_at = datetime.now(UTC)
    db.flush()
    return request


def cancel_request(db: Session, request: LeaveRequest) -> LeaveRequest:
    _require_pending(request)
    request.status = LeaveRequestStatus.CANCELLED
    db.flush()
    return request
