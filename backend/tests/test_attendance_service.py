from __future__ import annotations

from datetime import date

import pytest

from app.models import AttendanceCode, AttendanceEntry, Holiday
from app.services import attendance_export_service, attendance_service, leave_service
from tests.conftest import grant_balance


@pytest.fixture()
def code_present(db) -> AttendanceCode:
    code = AttendanceCode(libelle="Présent", code_court="P", couleur="#43A047")
    db.add(code)
    db.flush()
    return code


def test_guess_identifier_column_matches_common_headers():
    assert attendance_service.guess_identifier_column(["Ville", "Nom", "1", "2"]) == "Nom"
    assert attendance_service.guess_identifier_column(["Matricule", "1"]) == "Matricule"
    assert attendance_service.guess_identifier_column(["Ville", "Poste"]) is None


def test_guess_day_columns_picks_1_to_31_only():
    columns = ["Nom", "01", "2", "31", "32", "Total"]
    assert attendance_service.guess_day_columns(columns) == ["01", "2", "31"]


def test_read_table_parses_csv():
    content = b"Nom,01,02\nSara Alami,P,A\n"
    columns, rows = attendance_service.read_table(content, "pointage.csv")
    assert columns == ["Nom", "01", "02"]
    assert rows == [{"Nom": "Sara Alami", "01": "P", "02": "A"}]


def test_read_table_rejects_unsupported_extension():
    with pytest.raises(attendance_service.AttendanceServiceError):
        attendance_service.read_table(b"whatever", "pointage.xls")


def test_run_import_matches_by_full_name_both_orders(
    db, employee_a, employee_b, hr_user, code_present
):
    rows = [
        {"Nom": f"{employee_a.prenom} {employee_a.nom}", "01": "P"},
        {"Nom": f"{employee_b.nom} {employee_b.prenom}", "01": "P"},
    ]
    import_row = attendance_service.run_import(
        db,
        rows=rows,
        identifier_column="Nom",
        day_columns=["01"],
        mois=9,
        annee=2026,
        filename="pointage.csv",
        actor_user_id=hr_user.id,
    )
    assert import_row.nb_lignes_importees == 2
    assert import_row.nb_lignes_non_reconnues == 0

    entry_a = (
        db.query(AttendanceEntry)
        .filter_by(employee_id=employee_a.id, date=date(2026, 9, 1))
        .first()
    )
    entry_b = (
        db.query(AttendanceEntry)
        .filter_by(employee_id=employee_b.id, date=date(2026, 9, 1))
        .first()
    )
    assert entry_a is not None and entry_a.code_id == code_present.id
    assert entry_b is not None and entry_b.code_id == code_present.id


def test_run_import_matches_by_matricule(db, employee_a, hr_user, code_present):
    employee_a.matricule = "MAT-042"
    db.flush()
    rows = [{"Matricule": "mat 042", "01": "P"}]
    import_row = attendance_service.run_import(
        db,
        rows=rows,
        identifier_column="Matricule",
        day_columns=["01"],
        mois=9,
        annee=2026,
        filename="pointage.csv",
        actor_user_id=hr_user.id,
    )
    assert import_row.nb_lignes_importees == 1
    entry = (
        db.query(AttendanceEntry)
        .filter_by(employee_id=employee_a.id, date=date(2026, 9, 1))
        .first()
    )
    assert entry is not None


def test_run_import_collects_unmatched_rows_without_writing(db, hr_user, code_present):
    rows = [{"Nom": "Personne Inconnue", "01": "P"}]
    import_row = attendance_service.run_import(
        db,
        rows=rows,
        identifier_column="Nom",
        day_columns=["01"],
        mois=9,
        annee=2026,
        filename="pointage.csv",
        actor_user_id=hr_user.id,
    )
    assert import_row.nb_lignes_importees == 0
    assert import_row.nb_lignes_non_reconnues == 1
    assert import_row.noms_non_reconnus == "Personne Inconnue"
    assert db.query(AttendanceEntry).count() == 0


def test_run_import_upserts_on_reimport_same_employee_date(db, employee_a, hr_user, code_present):
    rows = [{"Nom": f"{employee_a.prenom} {employee_a.nom}", "01": "P"}]
    attendance_service.run_import(
        db,
        rows=rows,
        identifier_column="Nom",
        day_columns=["01"],
        mois=9,
        annee=2026,
        filename="pointage1.csv",
        actor_user_id=hr_user.id,
    )
    absence = AttendanceCode(libelle="Absence", code_court="A", couleur="#E53935")
    db.add(absence)
    db.flush()
    rows2 = [{"Nom": f"{employee_a.prenom} {employee_a.nom}", "01": "A"}]
    attendance_service.run_import(
        db,
        rows=rows2,
        identifier_column="Nom",
        day_columns=["01"],
        mois=9,
        annee=2026,
        filename="pointage2.csv",
        actor_user_id=hr_user.id,
    )
    entries = (
        db.query(AttendanceEntry).filter_by(employee_id=employee_a.id, date=date(2026, 9, 1)).all()
    )
    assert len(entries) == 1
    assert entries[0].code_id == absence.id


def test_run_import_skips_invalid_calendar_day(db, employee_a, hr_user, code_present):
    # September has 30 days — day 31 must not raise, just be skipped.
    rows = [{"Nom": f"{employee_a.prenom} {employee_a.nom}", "31": "P"}]
    import_row = attendance_service.run_import(
        db,
        rows=rows,
        identifier_column="Nom",
        day_columns=["31"],
        mois=9,
        annee=2026,
        filename="pointage.csv",
        actor_user_id=hr_user.id,
    )
    assert import_row.nb_lignes_importees == 1
    assert db.query(AttendanceEntry).count() == 0


# ------------------------------------------------------------- export state --


def test_build_monthly_state_shows_pointage_code(db, employee_a, active_status, code_present):
    db.add(
        AttendanceEntry(employee_id=employee_a.id, date=date(2026, 9, 7), code_id=code_present.id)
    )
    db.flush()
    state = attendance_export_service.build_monthly_state(db, 9, 2026)
    row = next(r for r in state["rows"] if r["employee_id"] == employee_a.id)
    day7 = next(d for d in row["days"] if d["date"] == "2026-09-07")
    assert day7["code"] == "P"
    assert day7["conflict"] is False


def test_build_monthly_state_shows_holiday_code(db, employee_a):
    db.add(Holiday(date=date(2026, 9, 9), libelle="Test"))
    db.flush()
    state = attendance_export_service.build_monthly_state(db, 9, 2026)
    row = next(r for r in state["rows"] if r["employee_id"] == employee_a.id)
    day9 = next(d for d in row["days"] if d["date"] == "2026-09-09")
    assert day9["code"] == "F"


def test_build_monthly_state_flags_pointage_leave_conflict(
    db, employee_a, leave_type, hr_user, code_present
):
    grant_balance(db, employee_a.id, leave_type.id, 2026)
    request = leave_service.create_request(
        db,
        employee_id=employee_a.id,
        leave_type_id=leave_type.id,
        date_debut=date(2026, 9, 7),
        date_fin=date(2026, 9, 7),
        commentaire=None,
        submitted_by_user_id=hr_user.id,
    )
    leave_service.approve_request(db, request, decided_by_user_id=hr_user.id, comment=None)
    db.add(
        AttendanceEntry(employee_id=employee_a.id, date=date(2026, 9, 7), code_id=code_present.id)
    )
    db.flush()

    state = attendance_export_service.build_monthly_state(db, 9, 2026)
    row = next(r for r in state["rows"] if r["employee_id"] == employee_a.id)
    day7 = next(d for d in row["days"] if d["date"] == "2026-09-07")
    assert day7["conflict"] is True
    # The leave code (congé) takes precedence over the raw pointage code for
    # payroll purposes. The `leave_type` fixture has no code_court set, so
    # this also exercises the libelle-derived fallback abbreviation.
    assert day7["code"] == "CON"
    assert state["nb_conflits"] == 1


def test_export_monthly_state_xlsx_produces_a_real_workbook(db, employee_a):
    content = attendance_export_service.export_monthly_state_xlsx(db, 9, 2026)
    assert content[:2] == b"PK"  # xlsx is a zip archive
    assert len(content) > 1000
