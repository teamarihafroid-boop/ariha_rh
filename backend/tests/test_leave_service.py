from __future__ import annotations

from datetime import date
from decimal import Decimal

import pytest

from app.models import Holiday
from app.services import leave_service
from tests.conftest import grant_balance


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
    grant_balance(db, employee_a.id, leave_type.id, 2026)
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
    grant_balance(db, employee_a.id, leave_type.id, 2026)
    grant_balance(db, employee_a.id, leave_type.id, 2027)
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
    grant_balance(db, employee_a.id, leave_type.id, 2026)
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
    grant_balance(db, employee_a.id, leave_type.id, 2026)
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
    grant_balance(db, employee_a.id, leave_type.id, 2026)
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
    grant_balance(db, employee_a.id, leave_type.id, 2026)
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
    grant_balance(db, employee_a.id, leave_type.id, 2026)
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
    grant_balance(db, employee_a.id, leave_type.id, 2026)
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
    grant_balance(db, employee_a.id, leave_type.id, 2026)
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
    grant_balance(db, employee_a.id, leave_type.id, 2026)
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


# --------------------------------------------------------- solde checks --


def test_create_request_rejects_when_solde_insufficient(db, employee_a, leave_type, hr_user):
    grant_balance(db, employee_a.id, leave_type.id, 2026, jours=3)
    with pytest.raises(leave_service.LeaveServiceError, match="Solde insuffisant"):
        leave_service.create_request(
            db,
            employee_id=employee_a.id,
            leave_type_id=leave_type.id,
            date_debut=date(2026, 9, 7),
            date_fin=date(2026, 9, 11),  # 5 jours ouvrés, only 3 available
            commentaire=None,
            submitted_by_user_id=hr_user.id,
        )


def test_create_request_allows_exact_solde_match(db, employee_a, leave_type, hr_user):
    grant_balance(db, employee_a.id, leave_type.id, 2026, jours=5)
    request = leave_service.create_request(
        db,
        employee_id=employee_a.id,
        leave_type_id=leave_type.id,
        date_debut=date(2026, 9, 7),
        date_fin=date(2026, 9, 11),
        commentaire=None,
        submitted_by_user_id=hr_user.id,
    )
    assert request.nb_jours == Decimal(5)


def test_create_request_skips_solde_check_for_non_deductible_type(db, employee_a, hr_user):
    from app.models import LeaveType

    maladie = LeaveType(libelle="Maladie (test)", couleur="#FB8C00", deduit_du_solde=False)
    db.add(maladie)
    db.flush()
    # No balance at all — must still succeed.
    request = leave_service.create_request(
        db,
        employee_id=employee_a.id,
        leave_type_id=maladie.id,
        date_debut=date(2026, 9, 7),
        date_fin=date(2026, 9, 11),
        commentaire=None,
        submitted_by_user_id=hr_user.id,
    )
    assert request.nb_jours == Decimal(5)


def test_solde_check_spans_both_years_for_a_split_request(db, employee_a, leave_type, hr_user):
    # 2026 segment (Dec 28-31) = 4 jours ouvrés, 2027 segment (Jan 1-3) = 2.
    grant_balance(db, employee_a.id, leave_type.id, 2026, jours=4)
    grant_balance(db, employee_a.id, leave_type.id, 2027, jours=1)  # short by 1
    with pytest.raises(leave_service.LeaveServiceError, match="2027"):
        leave_service.create_request(
            db,
            employee_id=employee_a.id,
            leave_type_id=leave_type.id,
            date_debut=date(2026, 12, 28),
            date_fin=date(2027, 1, 3),
            commentaire=None,
            submitted_by_user_id=hr_user.id,
        )


# ------------------------------------------------------------ accrual ----


def test_jours_acquis_legaux_mid_month_hire_partial_year(db, employee_a):
    # Hired 2019-03-15, checked against the fully-completed past year 2019
    # (independent of wall-clock "today"). By Dec 31 2019 the employee has
    # reached 9 monthiversaries (Apr15..Dec15); the 10th completes Jan 15
    # 2020, after the year ends, so it must NOT count.
    employee_a.date_embauche = date(2019, 3, 15)
    db.flush()
    accrued = leave_service.jours_acquis_legaux(db, employee_a.id, 2019)
    assert accrued == Decimal("13.5")  # 1.5 * 9 full months, no seniority bonus yet


def test_jours_acquis_legaux_no_hire_date_is_zero(db, employee_a):
    assert leave_service.jours_acquis_legaux(db, employee_a.id, 2026) == Decimal(0)


def test_jours_acquis_legaux_full_year_worked_is_eighteen_days(db, employee_a):
    # Hired well before 2020 and 2020 is a fully completed past year (12
    # full months, well under any 30-day cap, no ambiguity from "today").
    employee_a.date_embauche = date(2015, 1, 1)
    db.flush()
    accrued = leave_service.jours_acquis_legaux(db, employee_a.id, 2020)
    # Base: 1.5 * 12 = 18. Seniority by end of 2020 (5 full years since 2015)
    # adds one 5-year bonus block: +1.5. Total 19.5, well under the 30 cap.
    assert accrued == Decimal("19.5")


def test_jours_acquis_legaux_prior_to_hire_is_zero(db, employee_a):
    employee_a.date_embauche = date(2030, 1, 1)
    db.flush()
    assert leave_service.jours_acquis_legaux(db, employee_a.id, 2020) == Decimal(0)


def test_jours_acquis_legaux_capped_at_thirty_for_high_seniority(db, employee_a):
    # 40 years of seniority by end of a fully-completed year: base 18 +
    # bonus (8 blocks of 5 years * 1.5 = 12) = 30, exactly the Art. 238 cap
    # (would be 30 uncapped here, so this also confirms the cap doesn't
    # under-shoot when the raw total lands exactly on it).
    employee_a.date_embauche = date(1980, 1, 1)
    db.flush()
    accrued = leave_service.jours_acquis_legaux(db, employee_a.id, 2020)
    assert accrued == Decimal(30)


def test_accrual_legal_type_ignores_manual_balance(db, employee_a):
    from app.models import LeaveType

    conge_paye = LeaveType(
        libelle="Congé payé (test)", couleur="#0288D1", deduit_du_solde=True, accrual_legal=True
    )
    db.add(conge_paye)
    db.flush()
    employee_a.date_embauche = date(2015, 1, 1)
    db.flush()

    # Manually setting jours_acquis on the underlying LeaveBalance row must
    # NOT affect what jours_acquis_effectifs()/solde() report for this type.
    balance = leave_service.get_or_create_balance(db, employee_a.id, conge_paye.id, 2020)
    balance.jours_acquis = Decimal(999)
    db.flush()

    assert leave_service.jours_acquis_effectifs(db, employee_a.id, conge_paye.id, 2020) == Decimal(
        "19.5"
    )
