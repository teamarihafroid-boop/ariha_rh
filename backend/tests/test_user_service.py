from __future__ import annotations

from app.schemas.user import BulkUserCreateItem
from app.services import user_service


def test_list_account_candidates_excludes_linked_employees(
    db, employee_a, employee_a_user, employee_b
):
    candidates = user_service.list_account_candidates(db)
    ids = {c.id for c in candidates}
    assert employee_a.id not in ids
    assert employee_b.id in ids


def test_coverage_note_flags_employee_covered_by_department_responsable(
    db, colleague_under_responsable, responsable_employee
):
    candidates = {c.id: c for c in user_service.list_account_candidates(db)}
    note = candidates[colleague_under_responsable.id].coverage_note
    assert responsable_employee.full_name in note
    assert "non indispensable" in note


def test_coverage_note_recommends_account_for_the_responsable_itself(db, responsable_employee):
    candidates = {c.id: c for c in user_service.list_account_candidates(db)}
    note = candidates[responsable_employee.id].coverage_note
    assert "gérer" in note


def test_coverage_note_recommends_account_when_no_responsable_designated(db, employee_a):
    candidates = {c.id: c for c in user_service.list_account_candidates(db)}
    note = candidates[employee_a.id].coverage_note
    assert "Aucun responsable" in note


def test_suggested_emails_are_unique_across_candidates(
    db, department_no_responsable, active_status
):
    from tests.conftest import _make_employee

    _make_employee(db, department_no_responsable, active_status, nom="Alami", prenom="Sara")
    _make_employee(db, department_no_responsable, active_status, nom="Alami", prenom="Sara")
    candidates = user_service.list_account_candidates(db)
    emails = [c.suggested_email for c in candidates]
    assert len(emails) == len(set(emails))


def test_bulk_create_users_creates_employee_accounts_with_generated_passwords(
    db, employee_a, employee_b
):
    results = user_service.bulk_create_users(
        db,
        [
            BulkUserCreateItem(employee_id=employee_a.id),
            BulkUserCreateItem(employee_id=employee_b.id),
        ],
    )
    assert len(results) == 2
    for r in results:
        assert r.error is None
        assert r.user_id is not None
        assert r.password and len(r.password) >= 8
        assert r.email and r.email.endswith("@arihafroid.ma")


def test_bulk_create_users_reports_error_for_employee_that_already_has_an_account(
    db, employee_a, employee_a_user
):
    results = user_service.bulk_create_users(db, [BulkUserCreateItem(employee_id=employee_a.id)])
    assert results[0].error is not None
    assert results[0].user_id is None


def test_bulk_create_users_reports_error_for_missing_employee(db):
    results = user_service.bulk_create_users(db, [BulkUserCreateItem(employee_id=999999)])
    assert results[0].error == "Collaborateur introuvable."
