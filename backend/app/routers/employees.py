from __future__ import annotations

import base64
import io
from datetime import UTC, date, datetime
from pathlib import Path

from fastapi import APIRouter, Depends, File, HTTPException, Query, Response, UploadFile, status
from fastapi.templating import Jinja2Templates
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, joinedload
from xhtml2pdf import pisa

from app.database import get_db
from app.dependencies import AuthUser, get_current_user, require_role, verify_csrf
from app.models import Department, Employee, EmployeeDocument
from app.models.enums import UserRole
from app.schemas.employee import (
    DocumentAlertOut,
    EmergencyContactCreate,
    EmployeeCreate,
    EmployeeDocumentOut,
    EmployeeEquipmentCreate,
    EmployeeLite,
    EmployeeOut,
    EmployeeUpdate,
    OrgChartOut,
    ProbationAlertOut,
    ProbationEvaluationCreate,
)
from app.services import audit_service, contract_service, employee_service, storage_service

router = APIRouter(prefix="/api/employees", tags=["employees"])

TEMPLATES_DIR = Path(__file__).resolve().parent.parent / "templates"
templates = Jinja2Templates(directory=str(TEMPLATES_DIR))

_LOGO_PATH = Path(__file__).resolve().parent.parent / "static" / "logo.png"
_LOGO_DATA_URI = "data:image/png;base64," + base64.b64encode(_LOGO_PATH.read_bytes()).decode()

# Mirrors the paper "Fiche salarié" checklist used by HR today; kept in sync
# with frontend/src/lib/documentTypes.ts's EMPLOYEE_DOCUMENT_TYPES.
FICHE_DOCUMENT_CHECKLIST = [
    "CIN",
    "Contrat signé",
    "CV",
    "Diplômes",
    "Certificats / Attestations de travail",
    "Photos",
    "RIB",
    "Certificat d'aptitude physique",
    "Déclaration sur l'honneur",
]


def _serialize_document(document: EmployeeDocument) -> EmployeeDocumentOut:
    return EmployeeDocumentOut(
        id=document.id,
        type_document=document.type_document,
        nom_fichier=document.nom_fichier,
        content_type=document.content_type,
        taille_octets=document.taille_octets,
        date_expiration=document.date_expiration,
        uploaded_by_email=document.uploaded_by.email,
        created_at=document.created_at,
    )


def _serialize_employee(employee: Employee) -> EmployeeOut:
    return EmployeeOut(
        id=employee.id,
        matricule=employee.matricule,
        nom=employee.nom,
        prenom=employee.prenom,
        full_name=employee.full_name,
        nom_arabe=employee.nom_arabe,
        prenom_arabe=employee.prenom_arabe,
        date_naissance=employee.date_naissance,
        lieu_naissance=employee.lieu_naissance,
        date_embauche=employee.date_embauche,
        date_sortie=employee.date_sortie,
        motif_sortie=employee.motif_sortie,
        date_fin_periode_essai=employee.date_fin_periode_essai,
        email=employee.email,
        telephone=employee.telephone,
        ville=employee.ville,
        adresse=employee.adresse,
        cin=employee.cin,
        cnss=employee.cnss,
        type_contrat=employee.type_contrat,
        categorie_professionnelle=employee.categorie_professionnelle,
        salaire_base=employee.salaire_base,
        salaire_net=employee.salaire_net,
        notes=employee.notes,
        equipe=employee.equipe,
        department_id=employee.department_id,
        department_nom=employee.department.nom if employee.department else None,
        position_id=employee.position_id,
        position_intitule=employee.position.intitule if employee.position else None,
        status_id=employee.status_id,
        status_libelle=employee.status.libelle if employee.status else None,
        manager_id=employee.manager_id,
        manager_nom=employee.manager.full_name if employee.manager else None,
        emergency_contacts=list(employee.emergency_contacts),
        probation_evaluations=list(employee.probation_evaluations),
        documents=[_serialize_document(d) for d in employee.documents],
        equipements=list(employee.equipements),
    )


def _load_employee_or_404(db: Session, employee_id: int) -> Employee:
    employee = db.get(Employee, employee_id)
    if employee is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Collaborateur introuvable."
        )
    return employee


def _assert_visible(employee_id: int, current_user: AuthUser) -> None:
    if current_user.role == UserRole.EMPLOYEE and employee_id != current_user.employee_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Collaborateur introuvable."
        )


# --------------------------------------------------------------- roster/list --


@router.get("", response_model=list[EmployeeLite])
def list_employees(
    department_id: int | None = None,
    ville: str | None = None,
    status_id: int | None = None,
    q: str | None = None,
    current_user: AuthUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """HR/DG: full roster, optionally filtered. Employee: unchanged narrow
    case — may only list a department, and only when they are that
    department's leave-responsable (feeds the congé "submit for a colleague"
    picker, RESP-01 — nothing broader)."""
    if current_user.role == UserRole.EMPLOYEE:
        if department_id is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail="department_id requis."
            )
        department = db.get(Department, department_id)
        if (
            department is None
            or department.leave_responsable_employee_id != current_user.employee_id
        ):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Accès refusé.")
        employees = (
            db.query(Employee)
            .options(
                joinedload(Employee.department),
                joinedload(Employee.position),
                joinedload(Employee.status),
            )
            .filter(Employee.department_id == department_id)
            .all()
        )
        return [employee_service.serialize_employee_lite(e) for e in employees]

    query = db.query(Employee).options(
        joinedload(Employee.department),
        joinedload(Employee.position),
        joinedload(Employee.status),
    )
    if department_id is not None:
        query = query.filter(Employee.department_id == department_id)
    if ville:
        query = query.filter(Employee.ville.ilike(f"%{ville}%"))
    if status_id is not None:
        query = query.filter(Employee.status_id == status_id)
    if q:
        like = f"%{q}%"
        query = query.filter(
            (Employee.nom.ilike(like))
            | (Employee.prenom.ilike(like))
            | (Employee.email.ilike(like))
            | (Employee.telephone.ilike(like))
            | (Employee.matricule.ilike(like))
        )
    employees = query.order_by(Employee.nom, Employee.prenom).all()
    return [employee_service.serialize_employee_lite(e) for e in employees]


@router.get("/me", response_model=EmployeeOut)
def get_my_employee_record(
    current_user: AuthUser = Depends(require_role(UserRole.EMPLOYEE)),
    db: Session = Depends(get_db),
):
    if current_user.employee_id is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Aucune fiche associée à ce compte."
        )
    employee = _load_employee_or_404(db, current_user.employee_id)
    return _serialize_employee(employee)


@router.get("/periode-essai/alertes", response_model=list[ProbationAlertOut])
def list_probation_alerts(
    current_user: AuthUser = Depends(require_role(UserRole.HR)),
    db: Session = Depends(get_db),
):
    return employee_service.probation_alerts(db)


@router.get("/orgchart", response_model=OrgChartOut)
def get_org_chart(
    current_user: AuthUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return employee_service.build_org_chart(db)


@router.get("/{employee_id}", response_model=EmployeeOut)
def get_employee(
    employee_id: int,
    current_user: AuthUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    _assert_visible(employee_id, current_user)
    employee = _load_employee_or_404(db, employee_id)
    return _serialize_employee(employee)


@router.post(
    "",
    response_model=EmployeeOut,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(verify_csrf)],
)
def create_employee(
    payload: EmployeeCreate,
    current_user: AuthUser = Depends(require_role(UserRole.HR)),
    db: Session = Depends(get_db),
):
    try:
        employee = employee_service.create_employee(db, payload)
    except employee_service.EmployeeServiceError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Ce matricule est déjà utilisé."
        ) from exc

    audit_service.log(
        db,
        entity_type="employee",
        entity_id=employee.id,
        action="created",
        actor_user_id=current_user.id,
        actor_email=current_user.email,
        description=employee.full_name,
    )
    db.commit()
    db.refresh(employee)
    return _serialize_employee(employee)


@router.put("/{employee_id}", response_model=EmployeeOut, dependencies=[Depends(verify_csrf)])
def update_employee(
    employee_id: int,
    payload: EmployeeUpdate,
    current_user: AuthUser = Depends(require_role(UserRole.HR)),
    db: Session = Depends(get_db),
):
    employee = _load_employee_or_404(db, employee_id)
    try:
        employee_service.update_employee(db, employee, payload)
    except employee_service.EmployeeServiceError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Ce matricule est déjà utilisé."
        ) from exc

    audit_service.log(
        db,
        entity_type="employee",
        entity_id=employee.id,
        action="updated",
        actor_user_id=current_user.id,
        actor_email=current_user.email,
        description=employee.full_name,
    )
    db.commit()
    db.refresh(employee)
    return _serialize_employee(employee)


@router.delete("/{employee_id}", response_model=EmployeeOut, dependencies=[Depends(verify_csrf)])
def deactivate_employee(
    employee_id: int,
    date_sortie: date = Query(default_factory=lambda: datetime.now(UTC).date()),
    current_user: AuthUser = Depends(require_role(UserRole.HR)),
    db: Session = Depends(get_db),
):
    """Soft-deactivate only — nothing is ever physically deleted, unlike the
    prototype's hard cascade delete (see plan Context)."""
    employee = _load_employee_or_404(db, employee_id)
    try:
        employee_service.deactivate_employee(db, employee, date_sortie=date_sortie)
    except employee_service.EmployeeServiceError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    audit_service.log(
        db,
        entity_type="employee",
        entity_id=employee.id,
        action="deactivated",
        actor_user_id=current_user.id,
        actor_email=current_user.email,
        description=f"date_sortie={date_sortie.isoformat()}",
    )
    db.commit()
    db.refresh(employee)
    return _serialize_employee(employee)


# --------------------------------------------------------- emergency contacts --


@router.post(
    "/{employee_id}/contacts-urgence",
    response_model=EmployeeOut,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(verify_csrf)],
)
def add_emergency_contact(
    employee_id: int,
    payload: EmergencyContactCreate,
    current_user: AuthUser = Depends(require_role(UserRole.HR)),
    db: Session = Depends(get_db),
):
    employee = _load_employee_or_404(db, employee_id)
    employee_service.add_emergency_contact(
        db, employee, nom=payload.nom, lien=payload.lien, telephone=payload.telephone
    )
    audit_service.log(
        db,
        entity_type="employee",
        entity_id=employee.id,
        action="contact_urgence_added",
        actor_user_id=current_user.id,
        actor_email=current_user.email,
        description=payload.nom,
    )
    db.commit()
    db.refresh(employee)
    return _serialize_employee(employee)


@router.delete(
    "/{employee_id}/contacts-urgence/{contact_id}",
    response_model=EmployeeOut,
    dependencies=[Depends(verify_csrf)],
)
def delete_emergency_contact(
    employee_id: int,
    contact_id: int,
    current_user: AuthUser = Depends(require_role(UserRole.HR)),
    db: Session = Depends(get_db),
):
    employee = _load_employee_or_404(db, employee_id)
    contact = next((c for c in employee.emergency_contacts if c.id == contact_id), None)
    if contact is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Contact introuvable.")
    db.delete(contact)
    audit_service.log(
        db,
        entity_type="employee",
        entity_id=employee.id,
        action="contact_urgence_removed",
        actor_user_id=current_user.id,
        actor_email=current_user.email,
        description=contact.nom,
    )
    db.commit()
    db.refresh(employee)
    return _serialize_employee(employee)


# -------------------------------------------------------------------- équipement --


@router.post(
    "/{employee_id}/equipement",
    response_model=EmployeeOut,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(verify_csrf)],
)
def add_equipment(
    employee_id: int,
    payload: EmployeeEquipmentCreate,
    current_user: AuthUser = Depends(require_role(UserRole.HR)),
    db: Session = Depends(get_db),
):
    employee = _load_employee_or_404(db, employee_id)
    employee_service.add_equipment(db, employee, libelle=payload.libelle)
    audit_service.log(
        db,
        entity_type="employee",
        entity_id=employee.id,
        action="equipement_added",
        actor_user_id=current_user.id,
        actor_email=current_user.email,
        description=payload.libelle,
    )
    db.commit()
    db.refresh(employee)
    return _serialize_employee(employee)


@router.delete(
    "/{employee_id}/equipement/{item_id}",
    response_model=EmployeeOut,
    dependencies=[Depends(verify_csrf)],
)
def delete_equipment(
    employee_id: int,
    item_id: int,
    current_user: AuthUser = Depends(require_role(UserRole.HR)),
    db: Session = Depends(get_db),
):
    employee = _load_employee_or_404(db, employee_id)
    item = next((e for e in employee.equipements if e.id == item_id), None)
    if item is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Élément introuvable.")
    db.delete(item)
    audit_service.log(
        db,
        entity_type="employee",
        entity_id=employee.id,
        action="equipement_removed",
        actor_user_id=current_user.id,
        actor_email=current_user.email,
        description=item.libelle,
    )
    db.commit()
    db.refresh(employee)
    return _serialize_employee(employee)


# ------------------------------------------------------------------ probation --


@router.post(
    "/{employee_id}/periode-essai/evaluations",
    response_model=EmployeeOut,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(verify_csrf)],
)
def add_probation_evaluation(
    employee_id: int,
    payload: ProbationEvaluationCreate,
    current_user: AuthUser = Depends(require_role(UserRole.HR)),
    db: Session = Depends(get_db),
):
    employee = _load_employee_or_404(db, employee_id)
    employee_service.record_probation_evaluation(db, employee, payload)
    audit_service.log(
        db,
        entity_type="employee",
        entity_id=employee.id,
        action="probation_evaluation_added",
        actor_user_id=current_user.id,
        actor_email=current_user.email,
        description=payload.decision or "",
    )
    db.commit()
    db.refresh(employee)
    return _serialize_employee(employee)


# ----------------------------------------------------------------- documents --


@router.post(
    "/{employee_id}/documents",
    response_model=EmployeeOut,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(verify_csrf)],
)
async def upload_employee_document(
    employee_id: int,
    type_document: str,
    date_expiration: date | None = None,
    file: UploadFile = File(...),
    current_user: AuthUser = Depends(require_role(UserRole.HR)),
    db: Session = Depends(get_db),
):
    employee = _load_employee_or_404(db, employee_id)
    content = await file.read()
    if len(content) > storage_service.MAX_UPLOAD_BYTES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Fichier trop volumineux (limite : 10 Mo).",
        )
    key = storage_service.build_key("employees", employee_id, file.filename or "fichier")
    try:
        storage_service.get_storage().save(key, content)
    except storage_service.StorageServiceError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    document = EmployeeDocument(
        employee_id=employee_id,
        type_document=type_document,
        nom_fichier=file.filename or "fichier",
        storage_key=key,
        content_type=file.content_type or "application/octet-stream",
        taille_octets=len(content),
        date_expiration=date_expiration,
        uploaded_by_user_id=current_user.id,
    )
    db.add(document)
    audit_service.log(
        db,
        entity_type="employee",
        entity_id=employee.id,
        action="document_added",
        actor_user_id=current_user.id,
        actor_email=current_user.email,
        description=document.nom_fichier,
    )
    db.commit()
    db.refresh(employee)
    return _serialize_employee(employee)


@router.get("/{employee_id}/documents/{document_id}/download")
def download_employee_document(
    employee_id: int,
    document_id: int,
    current_user: AuthUser = Depends(require_role(UserRole.HR, UserRole.DG)),
    db: Session = Depends(get_db),
):
    document = (
        db.query(EmployeeDocument)
        .filter(EmployeeDocument.id == document_id, EmployeeDocument.employee_id == employee_id)
        .first()
    )
    if document is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document introuvable.")
    content = storage_service.get_storage().read(document.storage_key)
    return Response(
        content=content,
        media_type=document.content_type,
        headers={"Content-Disposition": f'attachment; filename="{document.nom_fichier}"'},
    )


@router.delete(
    "/{employee_id}/documents/{document_id}",
    response_model=EmployeeOut,
    dependencies=[Depends(verify_csrf)],
)
def delete_employee_document(
    employee_id: int,
    document_id: int,
    current_user: AuthUser = Depends(require_role(UserRole.HR)),
    db: Session = Depends(get_db),
):
    employee = _load_employee_or_404(db, employee_id)
    document = next((d for d in employee.documents if d.id == document_id), None)
    if document is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document introuvable.")
    storage_service.get_storage().delete(document.storage_key)
    db.delete(document)
    audit_service.log(
        db,
        entity_type="employee",
        entity_id=employee.id,
        action="document_removed",
        actor_user_id=current_user.id,
        actor_email=current_user.email,
        description=document.nom_fichier,
    )
    db.commit()
    db.refresh(employee)
    return _serialize_employee(employee)


@router.get("/documents/alertes", response_model=list[DocumentAlertOut])
def list_document_alerts(
    current_user: AuthUser = Depends(require_role(UserRole.HR)),
    db: Session = Depends(get_db),
):
    return employee_service.document_alerts(db)


# ----------------------------------------------------------------- printable --


def _render_employee_sheet_pdf(employee: Employee) -> bytes:
    uploaded_types = {d.type_document for d in employee.documents}
    html = templates.env.get_template("employee_sheet.html").render(
        employee=employee,
        logo_data_uri=_LOGO_DATA_URI,
        generated_at=datetime.now(UTC).strftime("%d/%m/%Y"),
        document_checklist=FICHE_DOCUMENT_CHECKLIST,
        uploaded_types=uploaded_types,
    )
    pdf_buffer = io.BytesIO()
    pisa_status = pisa.CreatePDF(html, dest=pdf_buffer)
    if pisa_status.err:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Erreur lors de la génération de la fiche PDF.",
        )
    return pdf_buffer.getvalue()


@router.get("/me/fiche")
def get_my_employee_sheet(
    current_user: AuthUser = Depends(require_role(UserRole.EMPLOYEE)),
    db: Session = Depends(get_db),
):
    if current_user.employee_id is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Aucune fiche associée à ce compte."
        )
    employee = _load_employee_or_404(db, current_user.employee_id)
    pdf = _render_employee_sheet_pdf(employee)
    return Response(
        content=pdf,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="fiche_{employee.id}.pdf"'},
    )


@router.get("/{employee_id}/fiche")
def get_employee_sheet(
    employee_id: int,
    current_user: AuthUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    _assert_visible(employee_id, current_user)
    employee = _load_employee_or_404(db, employee_id)
    pdf = _render_employee_sheet_pdf(employee)
    return Response(
        content=pdf,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="fiche_{employee.id}.pdf"'},
    )


@router.get("/{employee_id}/contrat-cdi")
def get_employee_cdi_contract(
    employee_id: int,
    current_user: AuthUser = Depends(require_role(UserRole.HR)),
    db: Session = Depends(get_db),
):
    employee = _load_employee_or_404(db, employee_id)
    docx_bytes = contract_service.render_cdi_contract(employee)
    return Response(
        content=docx_bytes,
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        headers={"Content-Disposition": f'attachment; filename="contrat_cdi_{employee.id}.docx"'},
    )
