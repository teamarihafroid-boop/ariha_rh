from __future__ import annotations

from pydantic import BaseModel, EmailStr

from app.models.enums import UserRole


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class MeResponse(BaseModel):
    id: int
    email: str
    role: UserRole
    employee_id: int | None
    department_id: int | None = None
