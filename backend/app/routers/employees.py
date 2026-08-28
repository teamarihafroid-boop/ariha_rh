from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import AuthUser, get_current_user
from app.models import Department, Employee
from app.models.enums import UserRole
from app.schemas.employee import EmployeeLite

router = APIRouter(prefix="/api/employees", tags=["employees"])


@router.get("", response_model=list[EmployeeLite])
def list_employees(
    department_id: int,
    current_user: AuthUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Minimal roster lookup. HR/DG can list any department. An Employee may
    only list their own department, and only when they are that
    department's leave-responsable — this exists solely to populate the
    "submit for a colleague" picker (RESP-01), nothing broader."""
    if current_user.role == UserRole.EMPLOYEE:
        department = db.get(Department, department_id)
        if (
            department is None
            or department.leave_responsable_employee_id != current_user.employee_id
        ):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Accès refusé.")

    employees = db.query(Employee).filter(Employee.department_id == department_id).all()
    return [
        EmployeeLite(id=e.id, full_name=e.full_name, department_id=e.department_id)
        for e in employees
    ]
