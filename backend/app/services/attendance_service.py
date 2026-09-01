from __future__ import annotations

import csv
import io
import re
import secrets
import unicodedata
from datetime import date

import openpyxl
import redis
from sqlalchemy.orm import Session

from app.config import get_settings
from app.models import AttendanceCode, AttendanceEntry, AttendanceImport, Employee

settings = get_settings()
_redis = redis.from_url(settings.redis_url, decode_responses=False)

UPLOAD_TTL_SECONDS = 15 * 60
_IDENTIFIER_KEYWORDS = ("nom", "salarie", "employe", "matricule", "collaborateur")
_DAY_COLUMN_RE = re.compile(r"^0?(\d{1,2})$")


class AttendanceServiceError(ValueError):
    """Raised for business-rule violations the router should turn into 4xx."""


def _normalize(value: str) -> str:
    """Accent-strip + remove spaces/hyphens + lowercase, so a pointeuse export
    that concatenates 'Nom Prénom' without consistent spacing still matches."""
    decomposed = unicodedata.normalize("NFKD", value)
    without_accents = "".join(c for c in decomposed if not unicodedata.combining(c))
    return re.sub(r"[\s\-]+", "", without_accents).strip().lower()


def read_table(content: bytes, filename: str) -> tuple[list[str], list[dict[str, str]]]:
    """Parses an uploaded .xlsx or .csv into (columns, rows), all cell values
    as strings. Legacy .xls (binary) is not supported — re-save as .xlsx."""
    name = filename.lower()
    if name.endswith(".csv"):
        text = content.decode("utf-8-sig")
        reader = csv.DictReader(io.StringIO(text))
        columns = [c for c in (reader.fieldnames or []) if c]
        rows = [{k: (v or "") for k, v in row.items() if k} for row in reader]
        return columns, rows

    if name.endswith(".xlsx"):
        workbook = openpyxl.load_workbook(io.BytesIO(content), data_only=True)
        sheet = workbook.active
        rows_iter = sheet.iter_rows(values_only=True)
        header = next(rows_iter, ())
        columns = [str(c).strip() if c is not None else "" for c in header]
        rows = []
        for raw_row in rows_iter:
            if all(v is None for v in raw_row):
                continue
            row = {col: ("" if val is None else str(val)) for col, val in zip(columns, raw_row)}
            rows.append(row)
        return [c for c in columns if c], rows

    raise AttendanceServiceError(
        "Format de fichier non supporté — utilisez un fichier .xlsx ou .csv."
    )


def guess_identifier_column(columns: list[str]) -> str | None:
    for col in columns:
        norm = _normalize(col)
        if any(keyword in norm for keyword in _IDENTIFIER_KEYWORDS):
            return col
    return None


def guess_day_columns(columns: list[str]) -> list[str]:
    result = []
    for col in columns:
        match = _DAY_COLUMN_RE.match(col.strip())
        if match and 1 <= int(match.group(1)) <= 31:
            result.append(col)
    return result


def store_upload(content: bytes, filename: str) -> str:
    token = secrets.token_urlsafe(24)
    _redis.set(f"attendance_upload:{token}:content", content, ex=UPLOAD_TTL_SECONDS)
    _redis.set(f"attendance_upload:{token}:filename", filename.encode(), ex=UPLOAD_TTL_SECONDS)
    return token


def load_upload(token: str) -> tuple[bytes, str] | None:
    content = _redis.get(f"attendance_upload:{token}:content")
    filename = _redis.get(f"attendance_upload:{token}:filename")
    if content is None or filename is None:
        return None
    return content, filename.decode()


def discard_upload(token: str) -> None:
    _redis.delete(f"attendance_upload:{token}:content", f"attendance_upload:{token}:filename")


def _build_employee_lookup(db: Session) -> tuple[dict[str, int], dict[str, int]]:
    by_name: dict[str, int] = {}
    by_matricule: dict[str, int] = {}
    for employee in db.query(Employee).all():
        by_name[_normalize(f"{employee.prenom} {employee.nom}")] = employee.id
        by_name[_normalize(f"{employee.nom} {employee.prenom}")] = employee.id
        if employee.matricule:
            by_matricule[_normalize(employee.matricule)] = employee.id
    return by_name, by_matricule


def _build_code_lookup(db: Session) -> dict[str, int]:
    lookup: dict[str, int] = {}
    for code in db.query(AttendanceCode).filter(AttendanceCode.is_active.is_(True)).all():
        lookup[_normalize(code.code_court)] = code.id
        lookup[_normalize(code.libelle)] = code.id
    return lookup


def run_import(
    db: Session,
    *,
    rows: list[dict[str, str]],
    identifier_column: str,
    day_columns: list[str],
    mois: int,
    annee: int,
    filename: str,
    actor_user_id: int,
    code_map: dict[str, int] | None = None,
) -> AttendanceImport:
    """Matches each row to an employee by normalized full name (either word
    order) or matricule — never by email, pointeuses don't export that.
    Unmatched rows are skipped and their raw identifier collected for HR to
    review; there is no automatic partial reconciliation — HR fixes the
    source file or the employee record and re-imports (same as the
    prototype this reimplements). Re-importing the same employee+date
    upserts rather than duplicates (unique constraint)."""
    if not (1 <= mois <= 12):
        raise AttendanceServiceError("Mois invalide.")
    if not day_columns:
        raise AttendanceServiceError("Aucune colonne de jour sélectionnée.")

    import_row = AttendanceImport(
        nom_fichier=filename,
        mois=mois,
        annee=annee,
        importe_par_user_id=actor_user_id,
        nb_lignes_importees=0,
        nb_lignes_non_reconnues=0,
    )
    db.add(import_row)
    db.flush()

    by_name, by_matricule = _build_employee_lookup(db)
    code_lookup = _build_code_lookup(db)
    code_map = code_map or {}

    nb_importees = 0
    unmatched: list[str] = []

    for row in rows:
        identifier_value = (row.get(identifier_column) or "").strip()
        if not identifier_value:
            continue
        key = _normalize(identifier_value)
        employee_id = by_name.get(key) or by_matricule.get(key)
        if employee_id is None:
            unmatched.append(identifier_value)
            continue

        for day_col in day_columns:
            day_match = _DAY_COLUMN_RE.match(day_col.strip())
            if not day_match:
                continue
            try:
                entry_date = date(annee, mois, int(day_match.group(1)))
            except ValueError:
                continue  # e.g. day 31 in a 30-day month

            raw_value = (row.get(day_col) or "").strip()
            if not raw_value:
                continue
            code_id = code_map.get(raw_value) or code_lookup.get(_normalize(raw_value))

            entry = (
                db.query(AttendanceEntry)
                .filter_by(employee_id=employee_id, date=entry_date)
                .first()
            )
            if entry is None:
                entry = AttendanceEntry(employee_id=employee_id, date=entry_date)
                db.add(entry)
            entry.code_id = code_id
            entry.valeur_brute = raw_value
            entry.import_id = import_row.id

        nb_importees += 1

    import_row.nb_lignes_importees = nb_importees
    import_row.nb_lignes_non_reconnues = len(unmatched)
    import_row.noms_non_reconnus = ", ".join(unmatched)[:2000] if unmatched else None
    db.flush()
    return import_row
