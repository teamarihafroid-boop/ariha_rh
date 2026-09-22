from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.config import get_settings
from app.middleware import SecurityHeadersMiddleware
from app.routers import (
    attendance,
    auth,
    departments,
    employees,
    holidays,
    leave,
    leave_types,
    notifications,
    positions,
    recruitment,
    users,
)

settings = get_settings()

app = FastAPI(title="ARIHA AI API", version="0.1.0")

app.add_middleware(SecurityHeadersMiddleware, hsts=settings.env == "production")

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
app.include_router(positions.router)
app.include_router(recruitment.router)
app.include_router(users.router)


@app.get("/health")
def health():
    return {"status": "ok"}


# Serves the built React app (see /Dockerfile, which builds it into ./web)
# from the same origin/service as the API — no separate frontend host, no
# extra CORS to manage. Inert in local dev, where ./web doesn't exist and
# the frontend runs instead via `npm run dev` on :5173 (which proxies /api
# to this service — see frontend/vite.config.ts).
_FRONTEND_DIST = Path(__file__).resolve().parent.parent / "web"

if _FRONTEND_DIST.is_dir():
    app.mount("/assets", StaticFiles(directory=_FRONTEND_DIST / "assets"), name="frontend-assets")

    @app.get("/{full_path:path}")
    def serve_frontend(full_path: str):
        # Registered last, so every real API route above already had first
        # crack at matching — this only ever sees paths nothing else claimed.
        if full_path.startswith("api/"):
            raise HTTPException(status_code=404)
        candidate = _FRONTEND_DIST / full_path
        if candidate.is_file():
            return FileResponse(candidate)
        # Client-side routes (e.g. /hr/collaborateurs/4) aren't real files —
        # serve the SPA shell and let React Router take over.
        return FileResponse(_FRONTEND_DIST / "index.html")
