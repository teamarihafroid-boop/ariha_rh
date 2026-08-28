from __future__ import annotations

from datetime import date
from decimal import Decimal

import pytest

from app.models import Holiday
from app.services import leave_service


def test_jours_ouvres_excludes_sunday_counts_saturday(db):
    # Mon 2026-09-07 .. Sun 2026-09-13: 7 calendar days, one Sunday excluded,
    # Saturday (09-12) counted — Ariha Froid works Mon-Sat.
    result = leave_service.jours_ouvres(db, date(2026, 9, 7), date(2026, 9, 13))
    assert result == Decimal(6)


def test_jours_ouvres_excludes_holidays(db):
    db.add(Holiday(date=date(2026, 9, 9), libelle="Jour férié test"))
    db.flush()
    # Same week as above, minus the holiday on Wed 09-09: 6 - 1 = 5.
    result = leave_service.jours_ouvres(db, date(2026, 9, 7), date(2026, 9, 13))
    assert result == Decimal(5)


def test_jours_ouvres_empty_range_is_zero(db):
    assert leave_service.jours_ouvres(db, date(2026, 9, 10), date(2026, 9, 9)) == Decimal(0)


def test_jours_pris_single_year(db, employee_a, leave_type, hr_user):
    request = leave_service.create_request(
        db,
        employee_id=employee_a.id,
        leave_type_id=leave_type.id,
        date_debut=date(2026, 9, 7),
        date_fin=date(2026, 9, 11),
        commentaire=None,
        submitted_by_user_id=hr_user.id,
    )
    leave_service.approve_request(db, request, decided_by_user_id=hr_user.id, comment=None)

    pris = leave_service.jours_pris(db, employee_a.id, leave_type.id, 2026)
    assert pris == Decimal(5)  # Mon-Fri, no Saturday/Sunday in range


def test_jours_pris_splits_across_year_boundary(db, employee_a, leave_type, hr_user):
    request = leave_service.create_request(
        db,
        employee_id=employee_a.id,
        leave_type_id=leave_type.id,
        date_debut=date(2026, 12, 28),
        date_fin=date(2027, 1, 3),
        commentaire=None,
        submitted_by_user_id=hr_user.id,
    )
    leave_service.approve_request(db, request, decided_by_user_id=hr_user.id, comment=None)

    assert leave_service.jours_pris(db, employee_a.id, leave_type.id, 2026) == Decimal(4)
    assert leave_service.jours_pris(db, employee_a.id, leave_type.id, 2027) == Decimal(2)


def test_balance_solde_is_acquis_minus_pris_computed_at_read_time(
    db, employee_a, leave_type, hr_user
):
    balance = leave_service.get_or_create_balance(db, employee_a.id, leave_type.id, 2026)
    balance.jours_acquis = Decimal(18)
    db.flush()

    request = leave_service.create_request(
        db,
        employee_id=employee_a.id,
        leave_type_id=leave_type.id,
        date_debut=date(2026, 9, 7),
        date_fin=date(2026, 9, 11),
        commentaire=None,
        submitted_by_user_id=hr_user.id,
    )
    leave_service.approve_request(db, request, decided_by_user_id=hr_user.id, comment=None)

    assert leave_service.solde(db, employee_a.id, leave_type.id, 2026) == Decimal(13)


def test_pending_request_does_not_affect_balance(db, employee_a, leave_type, hr_user):
    leave_service.create_request(
        db,
        employee_id=employee_a.id,
        leave_type_id=leave_type.id,
        date_debut=date(2026, 9, 7),
        date_fin=date(2026, 9, 11),
        commentaire=None,
        submitted_by_user_id=hr_user.id,
    )
    assert leave_service.jours_pris(db, employee_a.id, leave_type.id, 2026) == Decimal(0)


def test_rejected_request_does_not_affect_balance(db, employee_a, leave_type, hr_user):
    request = leave_service.create_request(
        db,
        employee_id=employee_a.id,
        leave_type_id=leave_type.id,
        date_debut=date(2026, 9, 7),
        date_fin=date(2026, 9, 11),
        commentaire=None,
        submitted_by_user_id=hr_user.id,
    )
    leave_service.reject_request(db, request, decided_by_user_id=hr_user.id, comment="Refusé")
    assert leave_service.jours_pris(db, employee_a.id, leave_type.id, 2026) == Decimal(0)


def test_cancelled_request_does_not_affect_balance(db, employee_a, leave_type, hr_user):
    request = leave_service.create_request(
        db,
        employee_id=employee_a.id,
        leave_type_id=leave_type.id,
        date_debut=date(2026, 9, 7),
        date_fin=date(2026, 9, 11),
        commentaire=None,
        submitted_by_user_id=hr_user.id,
    )
    leave_service.cancel_request(db, request)
    assert leave_service.jours_pris(db, employee_a.id, leave_type.id, 2026) == Decimal(0)


def test_nb_jours_always_server_computed(db, employee_a, leave_type, hr_user):
    request = leave_service.create_request(
        db,
        employee_id=employee_a.id,
        leave_type_id=leave_type.id,
        date_debut=date(2026, 9, 7),
        date_fin=date(2026, 9, 11),
        commentaire=None,
        submitted_by_user_id=hr_user.id,
    )
    # create_request's signature has no nb_jours parameter at all — the only
    # way to get this value is jours_ouvres(), never a client-supplied one.
    assert request.nb_jours == Decimal(5)


def test_approve_sets_decided_by_and_decided_at(db, employee_a, leave_type, hr_user):
    request = leave_service.create_request(
        db,
        employee_id=employee_a.id,
        leave_type_id=leave_type.id,
        date_debut=date(2026, 9, 7),
        date_fin=date(2026, 9, 11),
        commentaire=None,
        submitted_by_user_id=hr_user.id,
    )
    leave_service.approve_request(db, request, decided_by_user_id=hr_user.id, comment="OK")
    assert request.decided_by_user_id == hr_user.id
    assert request.decided_at is not None
    assert request.status.value == "approved"


def test_reject_requires_comment(db, employee_a, leave_type, hr_user):
    request = leave_service.create_request(
        db,
        employee_id=employee_a.id,
        leave_type_id=leave_type.id,
        date_debut=date(2026, 9, 7),
        date_fin=date(2026, 9, 11),
        commentaire=None,
        submitted_by_user_id=hr_user.id,
    )
    with pytest.raises(leave_service.LeaveServiceError):
        leave_service.reject_request(db, request, decided_by_user_id=hr_user.id, comment="")


def test_cannot_re_decide_already_decided_request(db, employee_a, leave_type, hr_user):
    request = leave_service.create_request(
        db,
        employee_id=employee_a.id,
        leave_type_id=leave_type.id,
        date_debut=date(2026, 9, 7),
        date_fin=date(2026, 9, 11),
        commentaire=None,
        submitted_by_user_id=hr_user.id,
    )
    leave_service.approve_request(db, request, decided_by_user_id=hr_user.id, comment=None)
    with pytest.raises(leave_service.LeaveServiceError):
        leave_service.approve_request(db, request, decided_by_user_id=hr_user.id, comment=None)
    with pytest.raises(leave_service.LeaveServiceError):
        leave_service.reject_request(db, request, decided_by_user_id=hr_user.id, comment="x")


def test_cancel_allowed_only_while_pending(db, employee_a, leave_type, hr_user):
    request = leave_service.create_request(
        db,
        employee_id=employee_a.id,
        leave_type_id=leave_type.id,
        date_debut=date(2026, 9, 7),
        date_fin=date(2026, 9, 11),
        commentaire=None,
        submitted_by_user_id=hr_user.id,
    )
    leave_service.approve_request(db, request, decided_by_user_id=hr_user.id, comment=None)
    with pytest.raises(leave_service.LeaveServiceError):
        leave_service.cancel_request(db, request)


def test_create_request_rejects_inverted_date_range(db, employee_a, leave_type, hr_user):
    with pytest.raises(leave_service.LeaveServiceError):
        leave_service.create_request(
            db,
            employee_id=employee_a.id,
            leave_type_id=leave_type.id,
            date_debut=date(2026, 9, 11),
            date_fin=date(2026, 9, 7),
            commentaire=None,
            submitted_by_user_id=hr_user.id,
        )


def test_create_request_rejects_range_with_no_working_days(db, employee_a, leave_type, hr_user):
    # A single Sunday: zero jours ouvrés.
    with pytest.raises(leave_service.LeaveServiceError):
        leave_service.create_request(
            db,
            employee_id=employee_a.id,
            leave_type_id=leave_type.id,
            date_debut=date(2026, 9, 13),
            date_fin=date(2026, 9, 13),
            commentaire=None,
            submitted_by_user_id=hr_user.id,
        )
