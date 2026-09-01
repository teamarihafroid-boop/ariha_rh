from __future__ import annotations

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
