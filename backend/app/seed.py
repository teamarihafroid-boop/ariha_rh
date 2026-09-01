"""Minimal reference-data + login seed for local dev. Not a data migration
from the prototype — that's a separate, later decision (PRD open question 6).
Run with: python -m app.seed
"""

from __future__ import annotations

from datetime import UTC, date, datetime

from app.core.security import hash_password
from app.database import SessionLocal
from app.models import (
    AttendanceCode,
    Department,
    Employee,
    EmployeeStatus,
    LeaveType,
    Position,
    User,
)
from app.models.enums import UserRole
from app.services import holiday_service

# (libelle, couleur, deduit_du_solde, accrual_legal, code_court)
# accrual_legal=True only for "Congé payé": its jours_acquis is computed
# automatically from tenure (leave_service.jours_acquis_legaux) rather than
# entered manually — see that function's docstring for the legal basis.
# code_court is the short label shown on the monthly attendance export grid.
SEED_LEAVE_TYPES = [
    ("Congé payé", "#0288D1", True, True, "CP"),
    ("Récupération", "#43A047", True, False, "REC"),
    ("Maladie", "#FB8C00", False, False, "MAL"),
    ("Sans solde", "#8E24AA", False, False, "SS"),
    ("Exceptionnel (mariage/naissance/décès)", "#546E7A", False, False, "EXC"),
]

# (libelle, code_court, couleur, compte_absence)
SEED_ATTENDANCE_CODES = [
    ("Présent", "P", "#43A047", False),
    ("Absence non justifiée", "A", "#E53935", True),
    ("Retard", "R", "#FB8C00", False),
    ("Mission", "M", "#1E88E5", False),
]


def run() -> None:
    db = SessionLocal()
    try:
        if db.query(EmployeeStatus).count() == 0:
            db.add_all(
                [
                    EmployeeStatus(libelle="Actif", couleur="#43A047", is_active_status=True),
                    EmployeeStatus(
                        libelle="Période d'essai", couleur="#FB8C00", is_active_status=True
                    ),
                    EmployeeStatus(libelle="Congé", couleur="#0288D1", is_active_status=True),
                    EmployeeStatus(libelle="Sorti", couleur="#9E9E9E", is_active_status=False),
                ]
            )
            db.flush()

        if db.query(LeaveType).count() == 0:
            for libelle, couleur, deduit, accrual_legal, code_court in SEED_LEAVE_TYPES:
                db.add(
                    LeaveType(
                        libelle=libelle,
                        couleur=couleur,
                        deduit_du_solde=deduit,
                        accrual_legal=accrual_legal,
                        code_court=code_court,
                    )
                )
            db.flush()
        else:
            # Backfill for a DB seeded before accrual_legal/code_court existed.
            db.query(LeaveType).filter_by(libelle="Congé payé").update(
                {"accrual_legal": True, "code_court": "CP"}
            )
            for libelle, _couleur, _deduit, _accrual, code_court in SEED_LEAVE_TYPES:
                db.query(LeaveType).filter_by(libelle=libelle, code_court=None).update(
                    {"code_court": code_court}
                )
            db.flush()

        if db.query(AttendanceCode).count() == 0:
            for libelle, code_court, couleur, compte_absence in SEED_ATTENDANCE_CODES:
                db.add(
                    AttendanceCode(
                        libelle=libelle,
                        code_court=code_court,
                        couleur=couleur,
                        compte_absence=compte_absence,
                    )
                )
            db.flush()

        active_status = db.query(EmployeeStatus).filter_by(libelle="Actif").first()

        department = db.query(Department).filter_by(nom="Direction").first()
        if department is None:
            department = Department(nom="Direction", description="Département de démonstration")
            db.add(department)
            db.flush()

        position = db.query(Position).filter_by(intitule="Collaborateur").first()
        if position is None:
            position = Position(intitule="Collaborateur", department_id=department.id)
            db.add(position)
            db.flush()

        def ensure_user(email: str, role: UserRole, *, employee: Employee | None = None) -> None:
            if db.query(User).filter_by(email=email).first() is not None:
                return
            db.add(
                User(
                    email=email,
                    password_hash=hash_password("ChangeMoi123!"),
                    role=role,
                    employee_id=employee.id if employee else None,
                    is_active=True,
                )
            )

        ensure_user("rh@arihafroid.ma", UserRole.HR)
        ensure_user("dg@arihafroid.ma", UserRole.DG)

        demo_employee = db.query(Employee).filter_by(email="employe@arihafroid.ma").first()
        if demo_employee is None:
            demo_employee = Employee(
                nom="Alami",
                prenom="Sara",
                email="employe@arihafroid.ma",
                department_id=department.id,
                position_id=position.id,
                status_id=active_status.id if active_status else None,
                # Illustrative hire date so the automatic congé-payé accrual
                # (jours_acquis_legaux) has something real to compute from.
                date_embauche=date(2023, 3, 1),
            )
            db.add(demo_employee)
            db.flush()

        ensure_user("employe@arihafroid.ma", UserRole.EMPLOYEE, employee=demo_employee)

        current_year = datetime.now(UTC).date().year
        for annee in (current_year, current_year + 1):
            holiday_service.generate_fixed_holidays(db, annee)

        db.commit()
        print("Seed complete: HR/DG/Employee logins ready (password: ChangeMoi123!).")
    finally:
        db.close()


if __name__ == "__main__":
    run()
