from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, EmailStr, field_validator

from app.models.enums import UserRole


class UserOut(BaseModel):
    id: int
    email: str
    role: UserRole
    employee_id: int | None
    employee_nom: str | None
    is_active: bool
    last_login_at: datetime | None
    created_at: datetime


class UserCreate(BaseModel):
    email: EmailStr
    password: str
    role: UserRole
    employee_id: int | None = None

    @field_validator("password")
    @classmethod
    def _password_min_length(cls, value: str) -> str:
        if len(value) < 8:
            raise ValueError("Le mot de passe doit contenir au moins 8 caractères.")
        return value


class UserUpdate(BaseModel):
    role: UserRole
    employee_id: int | None
    is_active: bool


class PasswordReset(BaseModel):
    password: str

    @field_validator("password")
    @classmethod
    def _password_min_length(cls, value: str) -> str:
        if len(value) < 8:
            raise ValueError("Le mot de passe doit contenir au moins 8 caractères.")
        return value
