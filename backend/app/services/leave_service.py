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


def _months_between(start: date, end: date) -> int:
    """Complete calendar months elapsed from start to end (inclusive of the
    day-of-month boundary), clamped to >= 0. E.g. Jan 15 -> Feb 14 is 0 full
    months; Jan 15 -> Feb 15 is 1."""
    if end < start:
        return 0
    months = (end.year - start.year) * 12 + (end.month - start.month)
    if end.day < start.day:
        months -= 1
    return max(months, 0)


def jours_acquis_legaux(db: Session, employee_id: int, annee: int) -> Decimal:
    """Automatic paid-leave accrual from tenure, per Morocco's Code du
    Travail (Loi 65-99): Art. 231 grants 1.5 working days per full month of
    effective service; Art. 238 adds 1.5 days per each completed 5-year
    seniority block, with the total annual entitlement capped at 30 days.

    Simplifications, not covered by this function (flag to HR/legal before
    relying on this for anything beyond an operational estimate):
    - Assumes every month since date_embauche counts as "effective service."
      The law excludes some absence types (e.g. unpaid leave) from this
      count; this app doesn't track daily attendance, so it can't apply that
      exclusion.
    - Does not enforce the separate "6 months of service before the leave
      can actually be taken" eligibility rule (Art. 231's second paragraph)
      — only the accrual amount is computed here.
    - The 5-year seniority bonus is prorated by the same fraction of the
      year actually worked, and the 30-day cap is prorated identically for a
      partial year; the law's text doesn't spell out that proration for a
      partial year explicitly, this is a reasonable but not literally-cited
      interpretation.

    Returns Decimal(0) if the employee has no date_embauche on file, or if
    `annee` is entirely before hire or entirely in the future.
    """
    employee = db.get(Employee, employee_id)
    if employee is None or employee.date_embauche is None:
        return Decimal(0)

    today = datetime.now(UTC).date()
    annee_debut = date(annee, 1, 1)
    annee_fin = date(annee, 12, 31)

    period_start = max(annee_debut, employee.date_embauche)
    period_end = annee_fin if annee < today.year else (today if annee == today.year else None)
    if period_end is None or period_end < period_start:
        return Decimal(0)

    # "As of end of period_end" means as of the instant period_end's full day
    # has elapsed — i.e. the start of the next day. Using period_end itself
    # would undercount by one day at every month/year boundary (e.g. Jan 1
    # -> Dec 31 the same year is a full 12 months of service, but Dec 31 is
    # one day short of the Jan-1-next-year "monthiversary" _months_between
    # checks against).
    as_of = period_end + timedelta(days=1)

    full_months = min(_months_between(period_start, as_of), 12)
    base = Decimal("1.5") * full_months

    seniority_years = _months_between(employee.date_embauche, as_of) // 12
    bonus = Decimal("1.5") * (seniority_years // 5)

    cap = Decimal(30) if full_months >= 12 else (Decimal(30) * full_months / Decimal(12))
    return min(base + bonus, cap)


def jours_acquis_effectifs(
    db: Session, employee_id: int, leave_type_id: int, annee: int
) -> Decimal:
    """The jours_acquis actually used for this employee/type/year: computed
    automatically (jours_acquis_legaux) for accrual_legal types, otherwise
    the manually-entered LeaveBalance value."""
    leave_type = db.get(LeaveType, leave_type_id)
    if leave_type is not None and leave_type.accrual_legal:
        return jours_acquis_legaux(db, employee_id, annee)
    return get_or_create_balance(db, employee_id, leave_type_id, annee).jours_acquis


def solde(db: Session, employee_id: int, leave_type_id: int, annee: int) -> Decimal:
    jours_acquis = jours_acquis_effectifs(db, employee_id, leave_type_id, annee)
    return jours_acquis - jours_pris(db, employee_id, leave_type_id, annee)


def _check_solde_suffisant(
    db: Session, employee_id: int, leave_type: LeaveType, date_debut: date, date_fin: date
) -> None:
    """Rejects a request that would exceed the employee's current solde. A
    request spanning a year boundary is checked one calendar year at a time
    (each year has its own accrual/solde), same split points jours_pris()
    uses for attribution."""
    annee_debut, annee_fin = date_debut.year, date_fin.year
    for annee in range(annee_debut, annee_fin + 1):
        segment_debut = max(date_debut, date(annee, 1, 1))
        segment_fin = min(date_fin, date(annee, 12, 31))
        jours_demandes = jours_ouvres(db, segment_debut, segment_fin)
        if jours_demandes <= 0:
            continue
        disponible = solde(db, employee_id, leave_type.id, annee)
        if jours_demandes > disponible:
            raise LeaveServiceError(
                f"Solde insuffisant pour {annee} : {disponible} jour(s) disponible(s) pour "
                f"{jours_demandes} jour(s) demandé(s)."
            )


def _check_no_overlap(db: Session, employee_id: int, date_debut: date, date_fin: date) -> None:
    """Rejects a request whose dates overlap an existing pending or approved
    request for the same employee, regardless of leave type — an employee
    can't be on two leaves (e.g. congé payé and maladie) at once. Rejected/
    cancelled requests never conflict."""
    conflict = (
        db.query(LeaveRequest)
        .filter(
            LeaveRequest.employee_id == employee_id,
            LeaveRequest.status.in_([LeaveRequestStatus.PENDING, LeaveRequestStatus.APPROVED]),
            LeaveRequest.date_debut <= date_fin,
            LeaveRequest.date_fin >= date_debut,
        )
        .first()
    )
    if conflict is not None:
        raise LeaveServiceError(
            "Chevauchement avec une demande existante "
            f"({conflict.date_debut.strftime('%d/%m/%Y')} - "
            f"{conflict.date_fin.strftime('%d/%m/%Y')}, statut : {conflict.status.value})."
        )


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
    leave_type = db.get(LeaveType, leave_type_id)
    if leave_type is None:
        raise LeaveServiceError("Type de congé introuvable.")
    if not leave_type.is_active:
        raise LeaveServiceError("Ce type de congé n'est plus actif.")

    nb_jours = jours_ouvres(db, date_debut, date_fin)
    if nb_jours <= 0:
        raise LeaveServiceError("La période sélectionnée ne contient aucun jour ouvré.")

    _check_no_overlap(db, employee_id, date_debut, date_fin)

    if leave_type.deduit_du_solde:
        _check_solde_suffisant(db, employee_id, leave_type, date_debut, date_fin)

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
