from __future__ import annotations

import secrets
import string

from sqlalchemy.orm import Session, joinedload

from app.core.security import hash_password
from app.models import Department, Employee, User
from app.models.enums import UserRole
from app.schemas.user import (
    BulkUserCreateItem,
    BulkUserCreateResultItem,
    EmployeeAccountCandidateOut,
    UserCreate,
    UserUpdate,
)
from app.services.attendance_service import _normalize  # generic accent/case-insensitive match

# Bulk-created accounts get an auto-generated login on the company domain —
# same pattern already used for the seeded rh@/dg@/employe@ accounts.
_EMAIL_DOMAIN = "arihafroid.ma"


class UserServiceError(ValueError):
    pass


def _check_email_unique(db: Session, email: str, *, exclude_id: int | None) -> None:
    query = db.query(User).filter(User.email == email)
    if exclude_id is not None:
        query = query.filter(User.id != exclude_id)
    if query.first() is not None:
        raise UserServiceError(f"L'adresse « {email} » est déjà utilisée par un autre compte.")


def _check_employee_linkable(
    db: Session, employee_id: int | None, *, exclude_id: int | None
) -> None:
    if employee_id is None:
        return
    employee = db.get(Employee, employee_id)
    if employee is None:
        raise UserServiceError("Collaborateur introuvable.")
    query = db.query(User).filter(User.employee_id == employee_id)
    if exclude_id is not None:
        query = query.filter(User.id != exclude_id)
    if query.first() is not None:
        raise UserServiceError("Ce collaborateur a déjà un compte lié.")


def _check_not_last_active_hr(db: Session, user: User, *, will_stay_active_hr: bool) -> None:
    if will_stay_active_hr:
        return
    if user.role != UserRole.HR or not user.is_active:
        return
    other_active_hr = (
        db.query(User)
        .filter(User.role == UserRole.HR, User.is_active.is_(True), User.id != user.id)
        .first()
    )
    if other_active_hr is None:
        raise UserServiceError(
            "Impossible : ce compte est le dernier compte RH actif. "
            "Créez ou réactivez un autre compte RH avant de modifier celui-ci."
        )


def create_user(db: Session, payload: UserCreate) -> User:
    _check_email_unique(db, payload.email, exclude_id=None)
    _check_employee_linkable(db, payload.employee_id, exclude_id=None)
    user = User(
        email=payload.email,
        password_hash=hash_password(payload.password),
        role=payload.role,
        employee_id=payload.employee_id,
        is_active=True,
    )
    db.add(user)
    db.flush()
    return user


def update_user(db: Session, user: User, payload: UserUpdate) -> User:
    _check_employee_linkable(db, payload.employee_id, exclude_id=user.id)
    will_stay_active_hr = payload.role == UserRole.HR and payload.is_active
    _check_not_last_active_hr(db, user, will_stay_active_hr=will_stay_active_hr)

    user.role = payload.role
    user.employee_id = payload.employee_id
    user.is_active = payload.is_active
    db.flush()
    return user


def reset_password(db: Session, user: User, new_password: str) -> User:
    user.password_hash = hash_password(new_password)
    db.flush()
    return user


def _email_slug(nom: str, prenom: str) -> str:
    slug = _normalize(f"{prenom}.{nom}")
    return "".join(ch for ch in slug if ch.isalnum() or ch == ".")


def _unique_email(db: Session, nom: str, prenom: str, taken: set[str]) -> str:
    base = _email_slug(nom, prenom) or "collaborateur"
    existing = {e.lower() for (e,) in db.query(User.email).all()}
    candidate = f"{base}@{_EMAIL_DOMAIN}"
    suffix = 2
    while candidate.lower() in existing or candidate.lower() in taken:
        candidate = f"{base}{suffix}@{_EMAIL_DOMAIN}"
        suffix += 1
    return candidate


def generate_password() -> str:
    # Random, human-typable-enough initial password — HR communicates it to
    # the collaborateur, who can change it later via a password reset.
    alphabet = string.ascii_letters + string.digits
    return "".join(secrets.choice(alphabet) for _ in range(10))


def _coverage_note(db: Session, employee: Employee) -> str | None:
    """Explains whether this employee likely needs their own login, based on
    whether a department leave-responsable can already submit congé on
    their behalf (see dependencies.can_submit_leave_for)."""
    if employee.department_id is None:
        return None
    department = db.get(Department, employee.department_id)
    if department is None or department.leave_responsable_employee_id is None:
        return "Aucun responsable congé désigné pour ce département — accès individuel recommandé."
    if department.leave_responsable_employee_id == employee.id:
        return (
            "Responsable congé de ce département — accès nécessaire pour gérer "
            "les demandes de son équipe."
        )
    responsable = db.get(Employee, department.leave_responsable_employee_id)
    resp_name = responsable.full_name if responsable else "un responsable"
    return f"Couvert par {resp_name} (responsable congé) — compte non indispensable."


def list_account_candidates(db: Session) -> list[EmployeeAccountCandidateOut]:
    linked_ids = {uid for (uid,) in db.query(User.employee_id).filter(User.employee_id.isnot(None))}
    employees = (
        db.query(Employee)
        .options(joinedload(Employee.department), joinedload(Employee.position))
        .order_by(Employee.nom, Employee.prenom)
        .all()
    )
    taken: set[str] = set()
    candidates: list[EmployeeAccountCandidateOut] = []
    for e in employees:
        if e.id in linked_ids:
            continue
        email = _unique_email(db, e.nom, e.prenom, taken)
        taken.add(email.lower())
        candidates.append(
            EmployeeAccountCandidateOut(
                id=e.id,
                full_name=e.full_name,
                matricule=e.matricule,
                department_nom=e.department.nom if e.department else None,
                position_intitule=e.position.intitule if e.position else None,
                coverage_note=_coverage_note(db, e),
                suggested_email=email,
            )
        )
    return candidates


def bulk_create_users(
    db: Session, items: list[BulkUserCreateItem]
) -> list[BulkUserCreateResultItem]:
    """Creates one 'employee'-role account per requested employee, each with
    an auto-generated password. Bulk creation always targets the employee
    role — HR/DG accounts stay on the single-account form, since those are
    rare, deliberate assignments rather than a batch of collaborateurs."""
    taken: set[str] = set()
    results: list[BulkUserCreateResultItem] = []
    for item in items:
        employee = db.get(Employee, item.employee_id)
        if employee is None:
            results.append(
                BulkUserCreateResultItem(
                    employee_id=item.employee_id,
                    employee_nom="?",
                    user_id=None,
                    email=None,
                    password=None,
                    error="Collaborateur introuvable.",
                )
            )
            continue

        email = item.email or _unique_email(db, employee.nom, employee.prenom, taken)
        try:
            _check_email_unique(db, email, exclude_id=None)
            _check_employee_linkable(db, employee.id, exclude_id=None)
        except UserServiceError as exc:
            results.append(
                BulkUserCreateResultItem(
                    employee_id=employee.id,
                    employee_nom=employee.full_name,
                    user_id=None,
                    email=email,
                    password=None,
                    error=str(exc),
                )
            )
            continue

        password = generate_password()
        user = User(
            email=email,
            password_hash=hash_password(password),
            role=UserRole.EMPLOYEE,
            employee_id=employee.id,
            is_active=True,
        )
        db.add(user)
        db.flush()
        taken.add(email.lower())
        results.append(
            BulkUserCreateResultItem(
                employee_id=employee.id,
                employee_nom=employee.full_name,
                user_id=user.id,
                email=email,
                password=password,
                error=None,
            )
        )
    return results
