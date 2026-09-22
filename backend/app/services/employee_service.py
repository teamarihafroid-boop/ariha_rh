from __future__ import annotations

from datetime import UTC, date, datetime, timedelta

from sqlalchemy.orm import Session

from app.models import (
    Department,
    EmergencyContact,
    Employee,
    EmployeeDocument,
    EmployeeEquipment,
    EmployeeStatus,
    JobOffer,
    JobOfferStatus,
    ProbationEvaluation,
)
from app.schemas.employee import EmployeeCreate, EmployeeLite, ProbationEvaluationCreate

ALLOWED_FIELDS = tuple(EmployeeCreate.model_fields.keys())


class EmployeeServiceError(ValueError):
    pass


def serialize_employee_lite(employee: Employee) -> EmployeeLite:
    return EmployeeLite(
        id=employee.id,
        full_name=employee.full_name,
        matricule=employee.matricule,
        department_id=employee.department_id,
        department_nom=employee.department.nom if employee.department else None,
        position_intitule=employee.position.intitule if employee.position else None,
        status_libelle=employee.status.libelle if employee.status else None,
        status_couleur=employee.status.couleur if employee.status else None,
    )


def _check_matricule_unique(db: Session, matricule: str | None, *, exclude_id: int | None) -> None:
    if not matricule:
        return
    query = db.query(Employee).filter(Employee.matricule == matricule)
    if exclude_id is not None:
        query = query.filter(Employee.id != exclude_id)
    if query.first() is not None:
        raise EmployeeServiceError(f"Le matricule « {matricule} » est déjà utilisé.")


def _check_not_own_manager(employee_id: int | None, manager_id: int | None) -> None:
    if employee_id is not None and manager_id == employee_id:
        raise EmployeeServiceError("Un collaborateur ne peut pas être son propre responsable.")


def create_employee(db: Session, payload: EmployeeCreate) -> Employee:
    _check_matricule_unique(db, payload.matricule, exclude_id=None)
    _check_not_own_manager(None, payload.manager_id)
    employee = Employee(**payload.model_dump())
    db.add(employee)
    db.flush()
    return employee


def update_employee(db: Session, employee: Employee, payload: EmployeeCreate) -> Employee:
    _check_matricule_unique(db, payload.matricule, exclude_id=employee.id)
    _check_not_own_manager(employee.id, payload.manager_id)
    for field in ALLOWED_FIELDS:
        setattr(employee, field, getattr(payload, field))
    db.flush()
    return employee


def deactivate_employee(db: Session, employee: Employee, *, date_sortie: date) -> Employee:
    inactive_status = db.query(EmployeeStatus).filter_by(is_active_status=False).first()
    if inactive_status is None:
        raise EmployeeServiceError(
            "Aucun statut inactif n'est configuré (voir Paramètres > Statuts)."
        )
    employee.date_sortie = date_sortie
    employee.status_id = inactive_status.id
    db.flush()
    return employee


def add_emergency_contact(
    db: Session, employee: Employee, *, nom: str, lien: str | None, telephone: str
):
    contact = EmergencyContact(employee_id=employee.id, nom=nom, lien=lien, telephone=telephone)
    db.add(contact)
    db.flush()
    return contact


def add_equipment(db: Session, employee: Employee, *, libelle: str) -> EmployeeEquipment:
    item = EmployeeEquipment(employee_id=employee.id, libelle=libelle)
    db.add(item)
    db.flush()
    return item


def record_probation_evaluation(
    db: Session, employee: Employee, payload: ProbationEvaluationCreate
) -> ProbationEvaluation:
    evaluation = ProbationEvaluation(employee_id=employee.id, **payload.model_dump())
    db.add(evaluation)
    if payload.decision == "Prolongé" and payload.nouvelle_date_fin is not None:
        employee.date_fin_periode_essai = payload.nouvelle_date_fin
    elif payload.decision in ("Confirmé", "Rompu"):
        employee.date_fin_periode_essai = None
    db.flush()
    return evaluation


def _is_double_signed_off(evaluations: list[ProbationEvaluation]) -> bool:
    return any(e.avis_rh and e.evaluateur_rh and e.avis_dg and e.evaluateur_dg for e in evaluations)


def probation_alerts(db: Session) -> list[dict]:
    """Read-time (no cron), like the prototype's own 10-day reminder. Unlike
    the prototype, this requires BOTH avis_rh+evaluateur_rh AND
    avis_dg+evaluateur_dg on at least one evaluation before considering the
    employee "signed off" — the prototype silenced its alert as soon as any
    single evaluation row existed, even a one-sided one."""
    today = datetime.now(UTC).date()
    seuil = today + timedelta(days=10)
    alerts: list[dict] = []
    employees = (
        db.query(Employee)
        .filter(
            Employee.date_fin_periode_essai.isnot(None), Employee.date_fin_periode_essai <= seuil
        )
        .all()
    )
    for employee in employees:
        if _is_double_signed_off(employee.probation_evaluations):
            continue
        jours_restants = (employee.date_fin_periode_essai - today).days
        if jours_restants < 0:
            urgence = "retard"
        elif jours_restants <= 3:
            urgence = "urgent"
        else:
            urgence = "semaine"
        alerts.append(
            {
                "employee_id": employee.id,
                "employee_nom": employee.full_name,
                "date_fin_periode_essai": employee.date_fin_periode_essai,
                "urgence": urgence,
                "a_evaluation_complete": False,
            }
        )
    return alerts


def document_alerts(db: Session) -> list[dict]:
    """Read-time (no cron), same shape as probation_alerts. Flags a document
    whose date_expiration falls within 30 days — chosen as a reasonable
    default (HR-02 doesn't specify a threshold); get HR sign-off before
    trusting this window for anything beyond an operational reminder, same
    posture as the accrual-legal docstring elsewhere in this module. Only the
    single most-recently-uploaded document per (employee_id, type_document)
    is considered "current" — an older expiring copy of a type that's since
    been renewed with a fresh upload is not re-flagged."""
    today = datetime.now(UTC).date()
    seuil = today + timedelta(days=30)
    # Fetch every document (not pre-filtered by expiry) so the "most recent
    # upload per type" pick is correct even when that latest upload has no
    # expiration or one beyond the window — otherwise a superseded, still-
    # expiring older copy would get flagged after its type was renewed.
    documents = (
        db.query(EmployeeDocument)
        .order_by(
            EmployeeDocument.employee_id, EmployeeDocument.type_document, EmployeeDocument.id.desc()
        )
        .all()
    )
    seen: set[tuple[int, str]] = set()
    alerts: list[dict] = []
    for document in documents:
        key = (document.employee_id, document.type_document)
        if key in seen:
            continue
        seen.add(key)

        if document.date_expiration is None or document.date_expiration > seuil:
            continue
        jours_restants = (document.date_expiration - today).days
        if jours_restants < 0:
            urgence = "retard"
        elif jours_restants <= 7:
            urgence = "urgent"
        else:
            urgence = "semaine"
        alerts.append(
            {
                "employee_id": document.employee_id,
                "employee_nom": document.employee.full_name,
                "document_id": document.id,
                "type_document": document.type_document,
                "date_expiration": document.date_expiration,
                "urgence": urgence,
            }
        )
    return alerts


def _employee_niveau(employee: Employee, *, is_direction: bool) -> str:
    if is_direction:
        return "direction"
    return "responsable" if employee.categorie_professionnelle == "cadre" else "employe"


def build_org_chart(db: Session) -> dict:
    """Ports HR/core/services/orgchart_service.py::build_tree() verbatim,
    except the active-employee filter uses EmployeeStatus.is_active_status
    (already modeled) instead of the prototype's libelle=="Actif" string
    match. Two additions over the port: Employee.equipe groups siblings
    into a synthetic team box (e.g. "Logistique", "Caisse") so a
    department's chart can show sub-teams without a dedicated table, and
    open JobOffers surface as "postes_ouverts" per department."""
    employees = (
        db.query(Employee)
        .join(EmployeeStatus, Employee.status_id == EmployeeStatus.id)
        .filter(EmployeeStatus.is_active_status.is_(True))
        .all()
    )
    by_id = {e.id: e for e in employees}
    children: dict[int, list[Employee]] = {}
    for e in employees:
        if e.manager_id is not None and e.manager_id in by_id:
            children.setdefault(e.manager_id, []).append(e)

    def distinct_departments(employee: Employee) -> set[int | None]:
        return {k.department_id for k in children.get(employee.id, [])}

    direction_employees = [
        e for e in employees if e.manager_id is None and len(distinct_departments(e)) >= 3
    ]
    direction_ids = {e.id for e in direction_employees}

    # Synthetic (non-employee) node ids just need to be unique in the
    # payload — negative and decreasing keeps them out of the employees.id
    # range without a lookup table.
    _next_synthetic_id = [-1]

    def synthetic_id() -> int:
        value = _next_synthetic_id[0]
        _next_synthetic_id[0] -= 1
        return value

    def employee_node(employee: Employee, *, rapporte_a: dict | None = None) -> dict:
        kids = [
            k for k in children.get(employee.id, []) if k.department_id == employee.department_id
        ]
        return {
            "id": employee.id,
            "full_name": employee.full_name,
            "department_id": employee.department_id,
            "department_nom": employee.department.nom if employee.department else None,
            "position_intitule": employee.position.intitule if employee.position else None,
            "niveau": _employee_niveau(employee, is_direction=employee.id in direction_ids),
            "rapporte_a": rapporte_a,
            "enfants": group_kids(kids, department_id=employee.department_id),
        }

    def group_kids(kids: list[Employee], *, department_id: int | None) -> list[dict]:
        """Direct reports with no equipe become their own node; those
        sharing an equipe label collapse into one synthetic team box."""
        direct: list[Employee] = []
        teams: dict[str, list[Employee]] = {}
        for kid in kids:
            if kid.equipe:
                teams.setdefault(kid.equipe, []).append(kid)
            else:
                direct.append(kid)

        nodes = [employee_node(k) for k in direct]
        for equipe_label, membres in teams.items():
            nodes.append(
                {
                    "id": synthetic_id(),
                    "full_name": equipe_label,
                    "department_id": department_id,
                    "department_nom": None,
                    "position_intitule": None,
                    "niveau": "equipe",
                    "rapporte_a": None,
                    "enfants": [employee_node(m) for m in membres],
                }
            )
        return nodes

    direction = [employee_node(e) for e in direction_employees]

    departements: list[dict] = []
    dept_groups: dict[int, list[Employee]] = {}
    for e in employees:
        if e.department_id is not None:
            dept_groups.setdefault(e.department_id, []).append(e)

    open_offers = (
        db.query(JobOffer)
        .join(JobOfferStatus, JobOffer.status_id == JobOfferStatus.id)
        .filter(JobOfferStatus.libelle == "Ouverte", JobOffer.department_id.isnot(None))
        .all()
    )
    offers_by_department: dict[int, list[JobOffer]] = {}
    for offer in open_offers:
        offers_by_department.setdefault(offer.department_id, []).append(offer)

    department_ids = set(dept_groups.keys()) | set(offers_by_department.keys())
    department_names = {
        d.id: d.nom for d in db.query(Department).filter(Department.id.in_(department_ids))
    }

    for department_id in department_ids:
        dept_employees = dept_groups.get(department_id, [])
        roots = [
            e
            for e in dept_employees
            if e.manager_id is None
            or e.manager_id not in by_id
            or e.id in direction_ids
            or by_id[e.manager_id].department_id != department_id
        ]
        collaborateurs = []
        for e in roots:
            if e.id in direction_ids:
                continue
            manager = by_id.get(e.manager_id) if e.manager_id else None
            rapporte_a = None
            if manager is not None and manager.department_id != department_id:
                rapporte_a = {
                    "id": manager.id,
                    "nom_complet": manager.full_name,
                    "department_nom": manager.department.nom if manager.department else None,
                }
            collaborateurs.append(employee_node(e, rapporte_a=rapporte_a))
        postes_ouverts = [
            {"id": offer.id, "titre": offer.titre, "ville": offer.ville}
            for offer in offers_by_department.get(department_id, [])
        ]
        if collaborateurs or postes_ouverts:
            departements.append(
                {
                    "department_id": department_id,
                    "department_nom": department_names[department_id],
                    "collaborateurs": collaborateurs,
                    "postes_ouverts": postes_ouverts,
                }
            )

    return {"direction": direction, "departements": departements}
