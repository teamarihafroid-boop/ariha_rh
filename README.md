# ARIHA AI — Production Rebuild

Production rebuild of Ariha Froid's HR app (see `../HR/docs/PRD.md` and `../HR/docs/TECHNICAL_DECISIONS.md`
for the full spec). Stack: FastAPI + PostgreSQL + SQLAlchemy 2.0 (backend), React + TypeScript + Vite
(frontend). The old `HR/` prototype (Flask/SQLite, no auth) is left untouched as reference.

**Current slice:** authentication/RBAC foundation (HR / DG / Employee roles) + the congé (leave) module —
request → HR approval → printable certificate, with the leave-responsable capability (HR-40).

## Local setup

Requires Docker, Python 3.11+, Node 18+.

```bash
docker compose up -d          # Postgres (localhost:5433) + Redis (localhost:6379)

cd backend
python -m venv .venv
./.venv/Scripts/pip install -e ".[dev]"      # Windows; use .venv/bin/pip on macOS/Linux
cp .env.example .env
./.venv/Scripts/python -m alembic upgrade head
./.venv/Scripts/python -m app.seed           # seeds HR/DG/Employee logins, password: ChangeMoi123!
./.venv/Scripts/python -m uvicorn app.main:app --reload --port 8000

cd ../frontend
npm install
npm run dev                    # http://localhost:5173, proxies /api to :8000
```

Seeded logins (password `ChangeMoi123!` for all):
- `rh@arihafroid.ma` — HR
- `dg@arihafroid.ma` — DG
- `employe@arihafroid.ma` — Employee (Sara Alami, Département "Direction")

## Backend

```bash
cd backend
./.venv/Scripts/python -m pytest          # 49 tests: auth, RBAC, leave business logic
./.venv/Scripts/python -m ruff check app tests
./.venv/Scripts/python -m black app tests
```

Note: the test suite uses a separate `ariha_test` database (create once: `CREATE DATABASE ariha_test;`
against the same Postgres container) and Redis DB index 15 — it never touches the dev database/sessions.

## Frontend

```bash
cd frontend
npm run build          # tsc -b && vite build
npm test               # vitest run — 8 component tests
npm run lint            # oxlint
npm run format:check    # prettier --check
```

## What's built in this slice

- Sessions (Redis-backed, signed cookie) + Argon2id password hashing + CSRF (double-submit cookie).
- RBAC: HR (full), DG (read-only, no write routes registered at all), Employee (self-service, row-scoped).
- Leave request lifecycle: `pending → approved | rejected | cancelled`, `nb_jours` always server-computed
  via `jours_ouvres()` (Mon-Sat worked, Sun + holidays excluded — matches the prototype's real business rule).
- Leave-responsable capability (HR-40): per-department flag + submit-on-behalf, configurable at
  `/hr/parametres`; still requires HR approval regardless of who submitted (RESP-03).
- Notifications on approve/reject (EMP-05), printable HTML certificate gated on approval (EMP-06/HR-19).
- Real audit trail (`audit_logs.actor_user_id`, NOT NULL) replacing the prototype's host-PC-account bug.

## Known gaps / next steps

- No CI pipeline wired yet (lint/test run locally only).
- No Railway/staging deployment — local dev only so far.
- Employee/Department schema is trimmed to what this slice needs (no CIN/CNSS/salaire/documents yet —
  those land with the employee-records module).
- AI hosting provider (§5 open question in TECHNICAL_DECISIONS.md) and CNDP authorization are still open —
  unrelated to this slice, not touched.
- Data migration from the `HR/` prototype's SQLite data is a deliberately separate, later decision
  (PRD open question 6) — this slice seeds fresh reference data only.
