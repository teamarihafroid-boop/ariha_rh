from __future__ import annotations

from pydantic import BaseModel


class EmployeeLite(BaseModel):
    id: int
    full_name: str
    department_id: int | None
