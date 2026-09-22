from __future__ import annotations

from decimal import Decimal

from pydantic import BaseModel


class AttendanceCodeOut(BaseModel):
    id: int
    libelle: str
    code_court: str
    couleur: str
    compte_absence: bool
    is_active: bool

    model_config = {"from_attributes": True}


class AttendanceCodeCreate(BaseModel):
    libelle: str
    code_court: str
    couleur: str = "#607D8B"
    compte_absence: bool = False


class AttendanceCodeUpdate(BaseModel):
    libelle: str
    code_court: str
    couleur: str
    compte_absence: bool
    is_active: bool


class UploadPreviewOut(BaseModel):
    token: str
    columns: list[str]
    sample_rows: list[dict[str, str]]
    guessed_identifier_column: str | None
    guessed_day_columns: list[str]
    nb_rows: int
    # Raw cell values (from the guessed day columns) that don't match any
    # configured AttendanceCode — HR maps each one to a code before
    # confirming, instead of it silently importing as a blank/unrecognized
    # cell. Recomputed against the exact day-column selection at /import
    # time isn't needed: HR reviews this list before confirming either way.
    unmapped_values: list[str]


class ImportRequest(BaseModel):
    token: str
    identifier_column: str
    day_columns: list[str]
    mois: int
    annee: int
    code_map: dict[str, int] | None = None


class ImportResultOut(BaseModel):
    id: int
    nom_fichier: str
    mois: int
    annee: int
    nb_lignes_importees: int
    nb_lignes_non_reconnues: int
    noms_non_reconnus: list[str]

    model_config = {"from_attributes": True}


class MonthlyStateDay(BaseModel):
    date: str
    code: str | None
    conflict: bool


class MonthlyStateRow(BaseModel):
    employee_id: int
    nom_complet: str
    departement: str | None
    days: list[MonthlyStateDay]


class MonthlyStateOut(BaseModel):
    mois: int
    annee: int
    nb_jours: int
    nb_conflits: int
    rows: list[MonthlyStateRow]


class MonthlySummaryOut(BaseModel):
    """Per-employee monthly totals matching the presence-related columns of
    ARIHA FROID's real "ETAT DE PAIE" spreadsheet — see
    attendance_export_service.build_monthly_summary for how each is
    computed."""

    employee_id: int
    mois: int
    annee: int
    jours_ouvres_mois: Decimal
    jours_travailles: Decimal
    conge_paye: Decimal
    recuperation: Decimal
    conge_exceptionnel: Decimal
    absence_maladie: Decimal
    conge_sans_solde: Decimal
    absence: Decimal
    mission: int
    jours_non_travailles: Decimal
