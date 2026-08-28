from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import AuthUser, get_current_user
from app.models import LeaveType
from app.schemas.reference import LeaveTypeOut

router = APIRouter(prefix="/api/leave-types", tags=["leave-types"])


@router.get("", response_model=list[LeaveTypeOut])
def list_leave_types(
    current_user: AuthUser = Depends(get_current_user), db: Session = Depends(get_db)
):
    return db.query(LeaveType).order_by(LeaveType.libelle).all()
