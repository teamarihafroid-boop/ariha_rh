from __future__ import annotations

import os

# Must run before any `app.*` import: several modules (database.py, session_store.py)
# read settings at import time via module-level get_settings() calls.
os.environ["DATABASE_URL"] = "postgresql+psycopg://ariha:ariha_dev_pw@localhost:5433/ariha_test"
os.environ["REDIS_URL"] = "redis://localhost:6379/15"
os.environ["SESSION_SECRET"] = "test-secret-not-for-production"
os.environ["COOKIE_SECURE"] = "false"

from decimal import Decimal

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.core.security import hash_password
from app.database import Base, get_db
from app.main import app
from app.models import Department, Employee, EmployeeStatus, LeaveType, User
from app.models.enums import UserRole
from app.services.leave_service import get_or_create_balance
from app.services.session_store import _redis as redis_client

engine = create_engine(os.environ["DATABASE_URL"])


@pytest.fixture(scope="session", autouse=True)
def _schema():
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)


@pytest.fixture()
def db():
    """SQLAlchemy 2.0's documented pattern for joining a Session into an
    external, per-test transaction: inner commit()/flush() calls only
    release/recreate a SAVEPOINT, so the whole test's writes roll back
    cleanly regardless of how many times route/service code commits."""
    connection = engine.connect()
    trans = connection.begin()
    session_factory = sessionmaker(bind=connection, join_transaction_mode="create_savepoint")
    session = session_factory()
    try:
        yield session
    finally:
        session.close()
        trans.rollback()
        connection.close()


@pytest.fixture()
def client(db):
    def _override_get_db():
        yield db

    app.dependency_overrides[get_db] = _override_get_db
    redis_client.flushdb()
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


@pytest.fixture()
def active_status(db) -> EmployeeStatus:
    status = EmployeeStatus(libelle="Actif", couleur="#43A047", is_active_status=True)
    db.add(status)
    db.flush()
    return status


@pytest.fixture()
def leave_type(db) -> LeaveType:
    lt = LeaveType(libelle="Congé payé", couleur="#0288D1", deduit_du_solde=True)
    db.add(lt)
    db.flush()
    return lt


@pytest.fixture()
def department_no_responsable(db) -> Department:
    dept = Department(nom="Sans responsable")
    db.add(dept)
    db.flush()
    return dept


@pytest.fixture()
def other_department(db) -> Department:
    dept = Department(nom="Autre département")
    db.add(dept)
    db.flush()
    return dept


def _make_employee(db, department, active_status, *, nom="Doe", prenom="Jane") -> Employee:
    emp = Employee(nom=nom, prenom=prenom, department_id=department.id, status_id=active_status.id)
    db.add(emp)
    db.flush()
    return emp


def _make_user(db, email: str, role: UserRole, *, employee: Employee | None = None) -> User:
    user = User(
        email=email,
        password_hash=hash_password("TestPass123!"),
        role=role,
        employee_id=employee.id if employee else None,
        is_active=True,
    )
    db.add(user)
    db.flush()
    return user


@pytest.fixture()
def hr_user(db) -> User:
    return _make_user(db, "hr@test.example", UserRole.HR)


@pytest.fixture()
def dg_user(db) -> User:
    return _make_user(db, "dg@test.example", UserRole.DG)


@pytest.fixture()
def employee_a(db, department_no_responsable, active_status) -> Employee:
    """Belongs to a department with no leave-responsable: can self-submit."""
    return _make_employee(db, department_no_responsable, active_status, nom="Alami", prenom="Sara")


@pytest.fixture()
def employee_a_user(db, employee_a) -> User:
    return _make_user(db, "employee-a@test.example", UserRole.EMPLOYEE, employee=employee_a)


@pytest.fixture()
def employee_b(db, department_no_responsable, active_status) -> Employee:
    """Second employee in the SAME no-responsable department as employee_a."""
    return _make_employee(
        db, department_no_responsable, active_status, nom="Idrissi", prenom="Karim"
    )


@pytest.fixture()
def employee_b_user(db, employee_b) -> User:
    return _make_user(db, "employee-b@test.example", UserRole.EMPLOYEE, employee=employee_b)


@pytest.fixture()
def employee_other_dept(db, other_department, active_status) -> Employee:
    return _make_employee(db, other_department, active_status, nom="Bennani", prenom="Yassine")


@pytest.fixture()
def department_with_responsable(db, active_status) -> Department:
    dept = Department(nom="Avec responsable")
    db.add(dept)
    db.flush()
    return dept


@pytest.fixture()
def responsable_employee(db, department_with_responsable, active_status) -> Employee:
    emp = _make_employee(
        db, department_with_responsable, active_status, nom="Chraibi", prenom="Nadia"
    )
    department_with_responsable.leave_responsable_employee_id = emp.id
    db.flush()
    return emp


@pytest.fixture()
def responsable_user(db, responsable_employee) -> User:
    return _make_user(
        db, "responsable@test.example", UserRole.EMPLOYEE, employee=responsable_employee
    )


@pytest.fixture()
def colleague_under_responsable(
    db, department_with_responsable, active_status, responsable_employee
) -> Employee:
    # Depends on responsable_employee explicitly (not just the department) so
    # the department's leave_responsable_employee_id is actually set before
    # this colleague is used in a test.
    return _make_employee(
        db, department_with_responsable, active_status, nom="Fassi", prenom="Omar"
    )


@pytest.fixture()
def colleague_under_responsable_user(db, colleague_under_responsable) -> User:
    return _make_user(
        db, "colleague@test.example", UserRole.EMPLOYEE, employee=colleague_under_responsable
    )


def grant_balance(db, employee_id: int, leave_type_id: int, annee: int, jours=100) -> None:
    """Test setup helper: directly funds a solde so tests whose focus is
    NOT balance-sufficiency (RBAC, workflow, date-splitting, ...) don't have
    to think about it — leave_service._check_solde_suffisant now runs on
    every create_request() call for a deduit_du_solde=True type. Tests that
    ARE about balance sufficiency fund a specific, deliberately small amount
    instead of calling this."""
    balance = get_or_create_balance(db, employee_id, leave_type_id, annee)
    balance.jours_acquis = Decimal(jours)
    db.flush()


def login(client: TestClient, email: str, password: str = "TestPass123!") -> str:
    """Logs in via the real endpoint and returns the CSRF token, matching how
    a browser client would authenticate before a mutating request."""
    resp = client.post("/api/auth/login", json={"email": email, "password": password})
    assert resp.status_code == 200, resp.text
    return client.cookies.get("csrf_token")
