from __future__ import annotations

import calendar
import io
from datetime import date
from decimal import Decimal

import openpyxl
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter
from sqlalchemy.orm import Session, joinedload

from app.models import (
    AttendanceCode,
    AttendanceEntry,
    Employee,
    EmployeeStatus,
    Holiday,
    LeaveRequest,
    LeaveRequestStatus,
    LeaveType,
)
from app.services import leave_service

MONTHS_FR = [
    "",
    "Janvier",
    "Février",
    "Mars",
    "Avril",
    "Mai",
    "Juin",
    "Juillet",
    "Août",
    "Septembre",
    "Octobre",
    "Novembre",
    "Décembre",
]

HOLIDAY_CODE = "F"


def _leave_code(leave_type: LeaveType) -> str:
    if leave_type.code_court:
        return leave_type.code_court
    return leave_type.libelle[:3].upper()


def build_monthly_state(db: Session, mois: int, annee: int) -> dict:
    """Merges, per active employee per day of the month: pointeuse import
    (AttendanceEntry), approved congé (LeaveRequest — takes precedence for
    payroll purposes), and holidays. Does NOT include variable pay
    (avances/primes/commissions) or disciplinary suspensions — those modules
    don't exist yet in this rebuild; see README known gaps. A day carrying
    both a pointeuse entry and an approved leave is flagged as a conflict
    rather than silently dropping one."""
    nb_jours = calendar.monthrange(annee, mois)[1]
    start, end = date(annee, mois, 1), date(annee, mois, nb_jours)

    employees = (
        db.query(Employee)
        .join(EmployeeStatus, Employee.status_id == EmployeeStatus.id, isouter=True)
        .filter(EmployeeStatus.is_active_status.is_(True))
        .order_by(Employee.nom, Employee.prenom)
        .all()
    )

    entries = (
        db.query(AttendanceEntry)
        .filter(AttendanceEntry.date >= start, AttendanceEntry.date <= end)
        .all()
    )
    entries_by_key = {(e.employee_id, e.date): e for e in entries}

    leave_requests = (
        db.query(LeaveRequest)
        .filter(
            LeaveRequest.status == LeaveRequestStatus.APPROVED,
            LeaveRequest.date_debut <= end,
            LeaveRequest.date_fin >= start,
        )
        .all()
    )
    leaves_by_employee: dict[int, list[LeaveRequest]] = {}
    for req in leave_requests:
        leaves_by_employee.setdefault(req.employee_id, []).append(req)

    holidays = {
        h.date for h in db.query(Holiday).filter(Holiday.date >= start, Holiday.date <= end).all()
    }

    rows = []
    nb_conflits = 0
    for employee in employees:
        emp_leaves = leaves_by_employee.get(employee.id, [])
        days = []
        for day_num in range(1, nb_jours + 1):
            current = date(annee, mois, day_num)
            entry = entries_by_key.get((employee.id, current))
            leave = next((r for r in emp_leaves if r.date_debut <= current <= r.date_fin), None)

            code: str | None = None
            conflict = False
            if leave is not None:
                code = _leave_code(leave.leave_type)
                if entry is not None and entry.code_id is not None:
                    conflict = True
                    nb_conflits += 1
            elif entry is not None and entry.code is not None:
                code = entry.code.code_court
            elif current in holidays:
                code = HOLIDAY_CODE

            days.append({"date": current.isoformat(), "code": code, "conflict": conflict})

        rows.append(
            {
                "employee_id": employee.id,
                "nom_complet": employee.full_name,
                "departement": employee.department.nom if employee.department else None,
                "days": days,
            }
        )

    return {
        "mois": mois,
        "annee": annee,
        "nb_jours": nb_jours,
        "rows": rows,
        "nb_conflits": nb_conflits,
    }


# Maps a LeaveType's code_court (see app/seed.py's SEED_LEAVE_TYPES) to the
# matching column in ARIHA FROID's real "ETAT DE PAIE" spreadsheet. A custom
# leave type HR adds later (not one of these five) still counts against
# jours_travailles/jours_non_travailles — it just doesn't get its own
# labeled column, since the paper template doesn't have one for it either.
_LEAVE_CODE_TO_SUMMARY_KEY = {
    "CP": "conge_paye",
    "REC": "recuperation",
    "EXC": "conge_exceptionnel",
    "MAL": "absence_maladie",
    "SS": "conge_sans_solde",
}


def build_monthly_summary(
    db: Session, mois: int, annee: int, employee_ids: list[int] | None = None
) -> list[dict]:
    """One row per employee: monthly day totals matching the presence
    columns of the real "ETAT DE PAIE" spreadsheet (module of
    certificate/ETAT PRESENCE.xlsx) — identity + Jours Trav/CP/RC/Mission/
    Congé Excep/ABS Maladie/ABS/Congé sans Solde/Jours non Trav. Payroll-only
    columns (salaire, avances, primes, commission, net à payer, ABS AT) have
    no equivalent in this app — this app has no payroll engine — and are
    left for Finance to fill in by hand, same as the blank paper scaffold.

    jours_travailles = jours_ouvres_mois - (every approved-leave day of any
    type + every AttendanceEntry day whose code has compte_absence=True).
    "Mission" (a normal AttendanceCode, compte_absence=False) is deliberately
    NOT subtracted — a mission day is worked, just off-site.
    """
    nb_jours = calendar.monthrange(annee, mois)[1]
    start, end = date(annee, mois, 1), date(annee, mois, nb_jours)
    jours_ouvres_mois = leave_service.jours_ouvres(db, start, end)

    employees_query = db.query(Employee).options(
        joinedload(Employee.department), joinedload(Employee.position)
    )
    if employee_ids is not None:
        employees_query = employees_query.filter(Employee.id.in_(employee_ids))
    else:
        employees_query = employees_query.join(
            EmployeeStatus, Employee.status_id == EmployeeStatus.id, isouter=True
        ).filter(EmployeeStatus.is_active_status.is_(True))
    employees = employees_query.order_by(Employee.nom, Employee.prenom).all()
    employee_id_set = {e.id for e in employees}

    entries = (
        db.query(AttendanceEntry)
        .options(joinedload(AttendanceEntry.code))
        .filter(
            AttendanceEntry.date >= start,
            AttendanceEntry.date <= end,
            AttendanceEntry.employee_id.in_(employee_id_set),
        )
        .all()
        if employee_id_set
        else []
    )
    entries_by_employee: dict[int, list[AttendanceEntry]] = {}
    for entry in entries:
        entries_by_employee.setdefault(entry.employee_id, []).append(entry)

    leave_requests = (
        db.query(LeaveRequest)
        .options(joinedload(LeaveRequest.leave_type))
        .filter(
            LeaveRequest.status == LeaveRequestStatus.APPROVED,
            LeaveRequest.date_debut <= end,
            LeaveRequest.date_fin >= start,
            LeaveRequest.employee_id.in_(employee_id_set),
        )
        .all()
        if employee_id_set
        else []
    )
    leaves_by_employee: dict[int, list[LeaveRequest]] = {}
    for req in leave_requests:
        leaves_by_employee.setdefault(req.employee_id, []).append(req)

    rows = []
    for employee in employees:
        summary = {
            "conge_paye": Decimal(0),
            "recuperation": Decimal(0),
            "conge_exceptionnel": Decimal(0),
            "absence_maladie": Decimal(0),
            "conge_sans_solde": Decimal(0),
            "absence": Decimal(0),
        }
        autres_conge_days = Decimal(0)
        for req in leaves_by_employee.get(employee.id, []):
            segment_debut = max(req.date_debut, start)
            segment_fin = min(req.date_fin, end)
            jours = leave_service.jours_ouvres(db, segment_debut, segment_fin)
            key = _LEAVE_CODE_TO_SUMMARY_KEY.get(req.leave_type.code_court or "")
            if key:
                summary[key] += jours
            else:
                autres_conge_days += jours

        mission_days = 0
        for entry in entries_by_employee.get(employee.id, []):
            if entry.code is None:
                continue
            if entry.code.code_court == "M":
                mission_days += 1
            elif entry.code.compte_absence:
                summary["absence"] += 1

        jours_non_travailles = (
            summary["conge_paye"]
            + summary["recuperation"]
            + summary["conge_exceptionnel"]
            + summary["absence_maladie"]
            + summary["conge_sans_solde"]
            + summary["absence"]
            + autres_conge_days
        )
        jours_travailles = jours_ouvres_mois - jours_non_travailles

        rows.append(
            {
                "employee": employee,
                "employee_id": employee.id,
                "jours_ouvres_mois": jours_ouvres_mois,
                "jours_travailles": jours_travailles,
                "mission": mission_days,
                "jours_non_travailles": jours_non_travailles,
                **summary,
            }
        )
    return rows


# Column headers, in order, exactly as they appear in ARIHA FROID's real
# "ETAT DE PAIE" spreadsheet — including its "ABS AT" column appearing
# twice, which is a quirk of their original template, not a typo introduced
# here. Columns with no app-computed equivalent (payroll figures the app
# doesn't track) are left blank for Finance to fill in by hand.
def export_daily_grid_xlsx(db: Session, mois: int, annee: int) -> bytes:
    """The original day-by-day calendar grid (one column per day, pointeuse/
    congé/férié code per cell, conflicts highlighted) — kept as a separate
    "Détail journalier" download alongside the ETAT PRESENCE-format export,
    since it's the only place in the app that shows day-level detail."""
    state = build_monthly_state(db, mois, annee)
    nb_jours = state["nb_jours"]

    workbook = openpyxl.Workbook()
    sheet = workbook.active
    sheet.title = "Détail journalier"

    bold = Font(bold=True)
    header_fill = PatternFill(start_color="E6EEF9", end_color="E6EEF9", fill_type="solid")
    conflict_fill = PatternFill(start_color="FDEAE3", end_color="FDEAE3", fill_type="solid")

    title_cell = sheet.cell(row=1, column=1, value=f"État de présence — {MONTHS_FR[mois]} {annee}")
    title_cell.font = Font(bold=True, size=13)
    sheet.merge_cells(start_row=1, start_column=1, end_row=1, end_column=nb_jours + 2)

    header_row = 3
    sheet.cell(row=header_row, column=1, value="Collaborateur").font = bold
    sheet.cell(row=header_row, column=2, value="Département").font = bold
    for day_num in range(1, nb_jours + 1):
        cell = sheet.cell(row=header_row, column=2 + day_num, value=day_num)
        cell.font = bold
        cell.fill = header_fill

    row_idx = header_row + 1
    for row in state["rows"]:
        sheet.cell(row=row_idx, column=1, value=row["nom_complet"])
        sheet.cell(row=row_idx, column=2, value=row["departement"] or "—")
        for i, day in enumerate(row["days"]):
            cell = sheet.cell(row=row_idx, column=3 + i, value=day["code"] or "")
            if day["conflict"]:
                cell.fill = conflict_fill
        row_idx += 1

    sheet.column_dimensions[get_column_letter(1)].width = 24
    sheet.column_dimensions[get_column_letter(2)].width = 18
    for col_idx in range(3, nb_jours + 3):
        sheet.column_dimensions[get_column_letter(col_idx)].width = 4

    legend = workbook.create_sheet("Légende")
    legend.cell(row=1, column=1, value="Code").font = bold
    legend.cell(row=1, column=2, value="Libellé").font = bold
    legend_row = 2
    for code in (
        db.query(AttendanceCode)
        .filter(AttendanceCode.is_active.is_(True))
        .order_by(AttendanceCode.code_court)
        .all()
    ):
        legend.cell(row=legend_row, column=1, value=code.code_court)
        legend.cell(row=legend_row, column=2, value=code.libelle)
        legend_row += 1
    for leave_type in (
        db.query(LeaveType).filter(LeaveType.is_active.is_(True)).order_by(LeaveType.libelle).all()
    ):
        legend.cell(row=legend_row, column=1, value=_leave_code(leave_type))
        legend.cell(row=legend_row, column=2, value=f"{leave_type.libelle} (congé)")
        legend_row += 1
    legend.cell(row=legend_row, column=1, value=HOLIDAY_CODE)
    legend.cell(row=legend_row, column=2, value="Jour férié")
    legend.column_dimensions["A"].width = 10
    legend.column_dimensions["B"].width = 30

    buffer = io.BytesIO()
    workbook.save(buffer)
    return buffer.getvalue()


_HEADERS = [
    "MAT",
    "Nom",
    "Pénom",
    "Département",
    "Fonction",
    "Date d'Entrée",
    "CIN",
    "CNSS",
    "Date de Naissance",
    "Situation Familiale",
    "# d'enfants",
    "Adresse",
    "Salaire fixe",
    "Jours Trav",
    "Avance sur Salaire",
    "PRÊT",
    "RAPL",
    "RC",
    "CP",
    "Mission",
    "Congé Excep",
    "ABS AT",
    "ABS Maladie",
    "ABS AT",
    "ABS",
    "Congé sans Solde",
    "Jours non Trav",
    "Prime de Déplacement",
    "Total Jours Payés",
    "Prime de Rendement",
    "Commission",
    "Net à Payer",
    "Mode de Paiement",
]


def export_monthly_state_xlsx(db: Session, mois: int, annee: int) -> bytes:
    rows = build_monthly_summary(db, mois, annee)

    workbook = openpyxl.Workbook()
    sheet = workbook.active
    sheet.title = f"PRESENCE {mois:02d}-{annee}"

    thin = Side(style="thin")
    border = Border(left=thin, right=thin, top=thin, bottom=thin)
    header_font = Font(bold=True, size=12)
    title_font = Font(bold=True, size=18)
    header_fill = PatternFill(start_color="E6EEF9", end_color="E6EEF9", fill_type="solid")

    last_col = len(_HEADERS)
    title_cell = sheet.cell(row=1, column=1, value=f"ETAT DE PRESENCE {mois:02d}-{annee}")
    title_cell.font = title_font
    title_cell.alignment = Alignment(horizontal="center")
    sheet.merge_cells(start_row=1, start_column=1, end_row=1, end_column=last_col)

    header_row = 3
    for col_idx, label in enumerate(_HEADERS, start=1):
        cell = sheet.cell(row=header_row, column=col_idx, value=label)
        cell.font = header_font
        cell.alignment = Alignment(wrap_text=True, vertical="center")
        cell.border = border
        cell.fill = header_fill

    row_idx = header_row + 1
    for row in rows:
        employee: Employee = row["employee"]
        values = [
            employee.matricule,
            employee.nom,
            employee.prenom,
            employee.department.nom if employee.department else None,
            employee.position.intitule if employee.position else None,
            employee.date_embauche.strftime("%d/%m/%Y") if employee.date_embauche else None,
            employee.cin,
            employee.cnss,
            employee.date_naissance.strftime("%d/%m/%Y") if employee.date_naissance else None,
            None,  # Situation Familiale — not tracked by this app
            None,  # # d'enfants — not tracked by this app
            employee.adresse,
            float(employee.salaire_base) if employee.salaire_base is not None else None,
            float(row["jours_travailles"]),
            None,  # Avance sur Salaire — payroll, not tracked
            None,  # PRÊT — payroll, not tracked
            None,  # RAPL — payroll, not tracked
            float(row["recuperation"]),
            float(row["conge_paye"]),
            row["mission"],
            float(row["conge_exceptionnel"]),
            None,  # ABS AT — not tracked (no accident-du-travail code in this app)
            float(row["absence_maladie"]),
            None,  # ABS AT (duplicate column in the original template)
            float(row["absence"]),
            float(row["conge_sans_solde"]),
            float(row["jours_non_travailles"]),
            None,  # Prime de Déplacement — payroll, not tracked
            None,  # Total Jours Payés — payroll, not tracked
            None,  # Prime de Rendement — payroll, not tracked
            None,  # Commission — payroll, not tracked
            None,  # Net à Payer — payroll, not tracked
            None,  # Mode de Paiement — payroll, not tracked
        ]
        for col_idx, value in enumerate(values, start=1):
            cell = sheet.cell(row=row_idx, column=col_idx, value=value)
            cell.border = border
        row_idx += 1

    total_row = row_idx
    sheet.cell(row=total_row, column=2, value=f"Total Collaborateurs: {len(rows)}").font = Font(
        bold=True
    )

    signature_row = total_row + 2
    sheet.cell(row=signature_row, column=2, value="Responsable RH").font = Font(bold=True)
    sheet.cell(row=signature_row, column=15, value="Responsable Financier").font = Font(bold=True)
    sheet.cell(row=signature_row, column=29, value="Directeur Général").font = Font(bold=True)

    widths = [
        8,
        20,
        20,
        18,
        22,
        13,
        13,
        13,
        15,
        15,
        10,
        30,
        12,
        10,
        12,
        10,
        10,
        8,
        8,
        10,
        12,
        10,
        12,
        10,
        8,
        15,
        12,
        14,
        14,
        14,
        12,
        14,
        16,
    ]
    for col_idx, width in enumerate(widths, start=1):
        sheet.column_dimensions[get_column_letter(col_idx)].width = width
    sheet.row_dimensions[header_row].height = 45

    buffer = io.BytesIO()
    workbook.save(buffer)
    return buffer.getvalue()
