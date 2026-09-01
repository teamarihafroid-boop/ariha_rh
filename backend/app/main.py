from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import get_settings
from app.routers import (
    attendance,
    auth,
    departments,
    employees,
    holidays,
    leave,
    leave_types,
    notifications,
)

settings = get_settings()

app = FastAPI(title="ARIHA AI API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(attendance.router)
app.include_router(auth.router)
app.include_router(departments.router)
app.include_router(employees.router)
app.include_router(holidays.router)
app.include_router(leave_types.router)
app.include_router(leave.router)
app.include_router(notifications.router)


@app.get("/health")
def health():
    return {"status": "ok"}
