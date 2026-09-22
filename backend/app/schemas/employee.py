from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel


class EmployeeLite(BaseModel):
    id: int
    full_name: str
    matricule: str | None
    department_id: int | None
    department_nom: str | None
    position_intitule: str | None
    status_libelle: str | None
    status_couleur: str | None


class EmergencyContactOut(BaseModel):
    id: int
    nom: str
    lien: str | None
    telephone: str

    model_config = {"from_attributes": True}


class EmergencyContactCreate(BaseModel):
    nom: str
    lien: str | None = None
    telephone: str


class EmployeeEquipmentOut(BaseModel):
    id: int
    libelle: str

    model_config = {"from_attributes": True}


class EmployeeEquipmentCreate(BaseModel):
    libelle: str


class ProbationEvaluationOut(BaseModel):
    id: int
    date_evaluation: date
    avis_rh: str | None
    evaluateur_rh: str | None
    avis_dg: str | None
    evaluateur_dg: str | None
    decision: str | None
    nouvelle_date_fin: date | None

    model_config = {"from_attributes": True}


class ProbationEvaluationCreate(BaseModel):
    date_evaluation: date
    avis_rh: str | None = None
    evaluateur_rh: str | None = None
    avis_dg: str | None = None
    evaluateur_dg: str | None = None
    decision: str | None = None
    nouvelle_date_fin: date | None = None


class ProbationAlertOut(BaseModel):
    employee_id: int
    employee_nom: str
    date_fin_periode_essai: date
    urgence: str  # "retard" | "urgent" | "semaine"
    a_evaluation_complete: bool


class EmployeeDocumentOut(BaseModel):
    id: int
    type_document: str
    nom_fichier: str
    content_type: str
    taille_octets: int
    date_expiration: date | None
    uploaded_by_email: str
    created_at: datetime


class DocumentAlertOut(BaseModel):
    employee_id: int
    employee_nom: str
    document_id: int
    type_document: str
    date_expiration: date
    urgence: str  # "retard" | "urgent" | "semaine"


class EmployeeOut(BaseModel):
    id: int
    matricule: str | None
    nom: str
    prenom: str
    full_name: str
    nom_arabe: str | None
    prenom_arabe: str | None
    date_naissance: date | None
    lieu_naissance: str | None
    date_embauche: date | None
    date_sortie: date | None
    motif_sortie: str | None
    date_fin_periode_essai: date | None
    email: str | None
    telephone: str | None
    ville: str | None
    adresse: str | None
    cin: str | None
    cnss: str | None
    type_contrat: str | None
    categorie_professionnelle: str | None
    salaire_base: Decimal | None
    salaire_net: Decimal | None
    notes: str | None
    equipe: str | None
    department_id: int | None
    department_nom: str | None
    position_id: int | None
    position_intitule: str | None
    status_id: int | None
    status_libelle: str | None
    manager_id: int | None
    manager_nom: str | None
    emergency_contacts: list[EmergencyContactOut]
    probation_evaluations: list[ProbationEvaluationOut]
    documents: list[EmployeeDocumentOut]
    equipements: list[EmployeeEquipmentOut]

    # Built manually via employees.py's _serialize_employee (like leave.py's
    # _serialize): department_nom/position_intitule/status_libelle/manager_nom
    # are flattened joins, not direct Employee attributes, so from_attributes
    # auto-mapping doesn't apply here.


class EmployeeCreate(BaseModel):
    matricule: str | None = None
    nom: str
    prenom: str
    nom_arabe: str | None = None
    prenom_arabe: str | None = None
    date_naissance: date | None = None
    lieu_naissance: str | None = None
    date_embauche: date | None = None
    date_sortie: date | None = None
    motif_sortie: str | None = None
    date_fin_periode_essai: date | None = None
    email: str | None = None
    telephone: str | None = None
    ville: str | None = None
    adresse: str | None = None
    cin: str | None = None
    cnss: str | None = None
    type_contrat: str | None = None
    categorie_professionnelle: str | None = None
    salaire_base: Decimal | None = None
    salaire_net: Decimal | None = None
    notes: str | None = None
    equipe: str | None = None
    department_id: int | None = None
    position_id: int | None = None
    status_id: int | None = None
    manager_id: int | None = None


class EmployeeUpdate(EmployeeCreate):
    pass


class OrgChartVacant(BaseModel):
    id: int
    titre: str
    ville: str | None


class OrgChartNode(BaseModel):
    id: int
    full_name: str
    department_id: int | None
    department_nom: str | None
    position_intitule: str | None
    # "direction" | "equipe" (synthetic team box, no real employee behind
    # it — see Employee.equipe) | "responsable" | "employe". Drives the
    # box color on the org chart, matching the paper legend.
    niveau: str
    rapporte_a: dict | None
    enfants: list[OrgChartNode]


class OrgChartDepartment(BaseModel):
    department_id: int
    department_nom: str
    collaborateurs: list[OrgChartNode]
    postes_ouverts: list[OrgChartVacant]


class OrgChartOut(BaseModel):
    direction: list[OrgChartNode]
    departements: list[OrgChartDepartment]
