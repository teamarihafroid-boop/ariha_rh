from __future__ import annotations

from fastapi import APIRouter, Depends, File, HTTPException, Query, Response, UploadFile, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import AuthUser, require_role, verify_csrf
from app.models import AttendanceCode, AttendanceImport
from app.models.enums import UserRole
from app.schemas.attendance import (
    AttendanceCodeCreate,
    AttendanceCodeOut,
    AttendanceCodeUpdate,
    ImportRequest,
    ImportResultOut,
    MonthlyStateOut,
    MonthlySummaryOut,
    UploadPreviewOut,
)
from app.services import attendance_export_service, attendance_service, audit_service

router = APIRouter(prefix="/api/attendance", tags=["attendance"])


def _serialize_import(row: AttendanceImport) -> ImportResultOut:
    return ImportResultOut(
        id=row.id,
        nom_fichier=row.nom_fichier,
        mois=row.mois,
        annee=row.annee,
        nb_lignes_importees=row.nb_lignes_importees,
        nb_lignes_non_reconnues=row.nb_lignes_non_reconnues,
        noms_non_reconnus=row.noms_non_reconnus.split(", ") if row.noms_non_reconnus else [],
    )


# ------------------------------------------------------------------- codes --


@router.get("/codes", response_model=list[AttendanceCodeOut])
def list_codes(
    include_inactive: bool = False,
    current_user: AuthUser = Depends(require_role(UserRole.HR)),
    db: Session = Depends(get_db),
):
    query = db.query(AttendanceCode)
    if not include_inactive:
        query = query.filter(AttendanceCode.is_active.is_(True))
    return query.order_by(AttendanceCode.code_court).all()


@router.post(
    "/codes",
    response_model=AttendanceCodeOut,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(verify_csrf)],
)
def create_code(
    payload: AttendanceCodeCreate,
    current_user: AuthUser = Depends(require_role(UserRole.HR)),
    db: Session = Depends(get_db),
):
    code = AttendanceCode(
        libelle=payload.libelle,
        code_court=payload.code_court,
        couleur=payload.couleur,
        compte_absence=payload.compte_absence,
    )
    db.add(code)
    try:
        db.flush()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Un code de présence porte déjà ce libellé ou ce code court.",
        ) from exc

    audit_service.log(
        db,
        entity_type="attendance_code",
        entity_id=code.id,
        action="created",
        actor_user_id=current_user.id,
        actor_email=current_user.email,
        description=code.libelle,
    )
    db.commit()
    db.refresh(code)
    return code


@router.put(
    "/codes/{code_id}", response_model=AttendanceCodeOut, dependencies=[Depends(verify_csrf)]
)
def update_code(
    code_id: int,
    payload: AttendanceCodeUpdate,
    current_user: AuthUser = Depends(require_role(UserRole.HR)),
    db: Session = Depends(get_db),
):
    code = db.get(AttendanceCode, code_id)
    if code is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Code introuvable.")

    code.libelle = payload.libelle
    code.code_court = payload.code_court
    code.couleur = payload.couleur
    code.compte_absence = payload.compte_absence
    code.is_active = payload.is_active
    try:
        db.flush()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Un code de présence porte déjà ce libellé ou ce code court.",
        ) from exc

    audit_service.log(
        db,
        entity_type="attendance_code",
        entity_id=code.id,
        action="updated",
        actor_user_id=current_user.id,
        actor_email=current_user.email,
        description=code.libelle,
    )
    db.commit()
    db.refresh(code)
    return code


# ----------------------------------------------------------------- import --


@router.post("/upload", response_model=UploadPreviewOut, dependencies=[Depends(verify_csrf)])
async def upload_timesheet(
    file: UploadFile = File(...),
    current_user: AuthUser = Depends(require_role(UserRole.HR)),
    db: Session = Depends(get_db),
):
    content = await file.read()
    try:
        columns, rows = attendance_service.read_table(content, file.filename or "")
    except attendance_service.AttendanceServiceError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    token = attendance_service.store_upload(content, file.filename or "import")
    guessed_day_columns = attendance_service.guess_day_columns(columns)
    return UploadPreviewOut(
        token=token,
        columns=columns,
        sample_rows=rows[:5],
        guessed_identifier_column=attendance_service.guess_identifier_column(columns),
        guessed_day_columns=guessed_day_columns,
        nb_rows=len(rows),
        unmapped_values=attendance_service.find_unmapped_day_values(db, rows, guessed_day_columns),
    )


@router.post("/import", response_model=ImportResultOut, dependencies=[Depends(verify_csrf)])
def confirm_import(
    payload: ImportRequest,
    current_user: AuthUser = Depends(require_role(UserRole.HR)),
    db: Session = Depends(get_db),
):
    upload = attendance_service.load_upload(payload.token)
    if upload is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Le fichier importé a expiré (15 min) — veuillez le renvoyer.",
        )
    content, filename = upload
    try:
        _, rows = attendance_service.read_table(content, filename)
        import_row = attendance_service.run_import(
            db,
            rows=rows,
            identifier_column=payload.identifier_column,
            day_columns=payload.day_columns,
            mois=payload.mois,
            annee=payload.annee,
            filename=filename,
            actor_user_id=current_user.id,
            code_map=payload.code_map,
        )
    except attendance_service.AttendanceServiceError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    attendance_service.discard_upload(payload.token)
    audit_service.log(
        db,
        entity_type="attendance_import",
        entity_id=import_row.id,
        action="imported",
        actor_user_id=current_user.id,
        actor_email=current_user.email,
        description=(
            f"{import_row.nb_lignes_importees} ligne(s) importée(s), "
            f"{import_row.nb_lignes_non_reconnues} non reconnue(s)"
        ),
    )
    db.commit()
    db.refresh(import_row)
    return _serialize_import(import_row)


@router.get("/imports", response_model=list[ImportResultOut])
def list_imports(
    current_user: AuthUser = Depends(require_role(UserRole.HR)),
    db: Session = Depends(get_db),
):
    imports = (
        db.query(AttendanceImport).order_by(AttendanceImport.created_at.desc()).limit(50).all()
    )
    return [_serialize_import(i) for i in imports]


# ------------------------------------------------------------------ state --


@router.get("/etat", response_model=MonthlyStateOut)
def monthly_state(
    mois: int = Query(..., ge=1, le=12),
    annee: int = Query(...),
    current_user: AuthUser = Depends(require_role(UserRole.HR)),
    db: Session = Depends(get_db),
):
    return attendance_export_service.build_monthly_state(db, mois, annee)


@router.get("/etat/resume", response_model=MonthlySummaryOut)
def monthly_summary_for_employee(
    employee_id: int,
    mois: int = Query(..., ge=1, le=12),
    annee: int = Query(...),
    current_user: AuthUser = Depends(require_role(UserRole.HR)),
    db: Session = Depends(get_db),
):
    rows = attendance_export_service.build_monthly_summary(
        db, mois, annee, employee_ids=[employee_id]
    )
    if not rows:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Collaborateur introuvable."
        )
    row = rows[0]
    return MonthlySummaryOut(
        employee_id=row["employee_id"],
        mois=mois,
        annee=annee,
        jours_ouvres_mois=row["jours_ouvres_mois"],
        jours_travailles=row["jours_travailles"],
        conge_paye=row["conge_paye"],
        recuperation=row["recuperation"],
        conge_exceptionnel=row["conge_exceptionnel"],
        absence_maladie=row["absence_maladie"],
        conge_sans_solde=row["conge_sans_solde"],
        absence=row["absence"],
        mission=row["mission"],
        jours_non_travailles=row["jours_non_travailles"],
    )


@router.get("/export")
def export_state(
    mois: int = Query(..., ge=1, le=12),
    annee: int = Query(...),
    current_user: AuthUser = Depends(require_role(UserRole.HR)),
    db: Session = Depends(get_db),
):
    content = attendance_export_service.export_monthly_state_xlsx(db, mois, annee)
    filename = f"etat_presence_{annee}_{mois:02d}.xlsx"
    return Response(
        content=content,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get("/export/detail")
def export_daily_grid(
    mois: int = Query(..., ge=1, le=12),
    annee: int = Query(...),
    current_user: AuthUser = Depends(require_role(UserRole.HR)),
    db: Session = Depends(get_db),
):
    content = attendance_export_service.export_daily_grid_xlsx(db, mois, annee)
    filename = f"detail_journalier_{annee}_{mois:02d}.xlsx"
    return Response(
        content=content,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
