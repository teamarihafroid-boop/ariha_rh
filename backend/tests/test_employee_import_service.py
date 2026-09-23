from __future__ import annotations

import openpyxl

from app.models import Position
from app.services import employee_import_service


def _row(**overrides) -> dict[str, str]:
    base = {
        "Matricule": "",
        "Nom": "Alami",
        "Prénom": "Sara",
        "CIN": "BE123456",
        "Date de naissance": "15/03/1990",
        "Lieu de naissance": "Casablanca",
        "Téléphone": "0600112233",
        "Email": "sara.alami@example.com",
        "Ville": "Casablanca",
        "Adresse": "12 Rue Exemple",
        "Département": "",
        "Poste": "",
        "Statut": "",
        "Type de contrat": "CDI",
        "Catégorie": "cadre",
        "CNSS": "1234567",
        "Salaire de base": "8000",
        "Salaire net": "10000",
        "Date d'embauche": "01/06/2023",
        "Équipe": "",
    }
    base.update(overrides)
    return base


def test_build_template_xlsx_has_the_expected_headers(db):
    content = employee_import_service.build_template_xlsx(db)
    assert content[:2] == b"PK"
    from io import BytesIO

    workbook = openpyxl.load_workbook(BytesIO(content))
    sheet = workbook["Collaborateurs"]
    header = [
        sheet.cell(row=1, column=c).value
        for c in range(1, len(employee_import_service.TEMPLATE_HEADERS) + 1)
    ]
    assert header == employee_import_service.TEMPLATE_HEADERS


def test_parse_rows_requires_nom_and_prenom(db):
    rows = employee_import_service.parse_rows(db, [_row(Nom="", Prénom="")])
    assert rows[0].data is None
    assert "obligatoires" in rows[0].errors[0]


def test_parse_rows_matches_department_and_position(db, department_no_responsable):
    position = Position(intitule="Technicien", department_id=department_no_responsable.id)
    db.add(position)
    db.flush()

    rows = employee_import_service.parse_rows(
        db, [_row(Département=department_no_responsable.nom, Poste="Technicien")]
    )
    row = rows[0]
    assert row.errors == []
    assert row.data.department_id == department_no_responsable.id
    assert row.data.position_id == position.id


def test_parse_rows_matches_department_name_accent_and_case_insensitive(
    db, department_no_responsable
):
    department_no_responsable.nom = "Département Sans Responsable"
    db.flush()
    rows = employee_import_service.parse_rows(
        db, [_row(Département="departement sans responsable")]
    )
    assert rows[0].errors == []
    assert rows[0].data.department_id == department_no_responsable.id


def test_parse_rows_flags_unknown_department(db):
    rows = employee_import_service.parse_rows(db, [_row(Département="Ne Existe Pas")])
    assert rows[0].data is None
    assert any("inconnu" in e for e in rows[0].errors)


def test_parse_rows_flags_unknown_poste(db):
    rows = employee_import_service.parse_rows(db, [_row(Poste="Poste Fantome")])
    assert rows[0].data is None
    assert any("inconnu" in e for e in rows[0].errors)


def test_parse_rows_defaults_status_to_actif_when_blank(db, active_status):
    rows = employee_import_service.parse_rows(db, [_row(Statut="")])
    assert rows[0].data.status_id == active_status.id


def test_parse_rows_flags_unknown_status(db):
    rows = employee_import_service.parse_rows(db, [_row(Statut="Statut Fantome")])
    assert rows[0].data is None
    assert any("Statut inconnu" in e for e in rows[0].errors)


def test_parse_rows_handles_excel_native_date_format(db):
    # openpyxl's read_table stringifies a real date cell as str(datetime), not
    # the "JJ/MM/AAAA" a human would type.
    rows = employee_import_service.parse_rows(
        db, [_row(**{"Date de naissance": "1990-03-15 00:00:00"})]
    )
    assert rows[0].errors == []
    assert str(rows[0].data.date_naissance) == "1990-03-15"


def test_parse_rows_flags_unparseable_date(db):
    rows = employee_import_service.parse_rows(db, [_row(**{"Date de naissance": "not a date"})])
    assert rows[0].data is None
    assert any("date non reconnue" in e for e in rows[0].errors)


def test_parse_rows_handles_comma_decimal_and_thousands_space(db):
    rows = employee_import_service.parse_rows(db, [_row(**{"Salaire net": "10 000,50"})])
    assert rows[0].errors == []
    assert str(rows[0].data.salaire_net) == "10000.50"


def test_parse_rows_warns_on_probable_duplicate(db, department_no_responsable, active_status):
    from datetime import date

    from app.models import Employee

    db.add(
        Employee(
            nom="Alami",
            prenom="Sara",
            date_naissance=date(1990, 3, 15),
            department_id=department_no_responsable.id,
            status_id=active_status.id,
        )
    )
    db.flush()

    rows = employee_import_service.parse_rows(db, [_row()])
    assert rows[0].data is not None
    assert any("existe déjà" in w for w in rows[0].warnings)


def test_create_employees_creates_valid_rows_and_skips_invalid(db):
    rows = employee_import_service.parse_rows(
        db, [_row(Nom="Bennani", Prénom="Karim"), _row(Nom="", Prénom="")]
    )
    outcome = employee_import_service.create_employees(db, rows)
    assert outcome.created == 1
    assert len(outcome.skipped) == 1
    assert outcome.skipped[0]["row_number"] == 3


def test_create_employees_skips_duplicate_matricule(db):
    rows = employee_import_service.parse_rows(
        db,
        [
            _row(Matricule="M-1", Nom="Bennani", Prénom="Karim"),
            _row(Matricule="M-1", Nom="Idrissi", Prénom="Yassine"),
        ],
    )
    outcome = employee_import_service.create_employees(db, rows)
    assert outcome.created == 1
    assert len(outcome.skipped) == 1
    assert "matricule" in outcome.skipped[0]["reason"].lower()
