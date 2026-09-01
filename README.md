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
./.venv/Scripts/python -m pytest          # 96 tests: auth, RBAC, leave business logic, accrual, holidays, PDF, attendance
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
- Notifications on approve/reject (EMP-05), formal downloadable PDF certificate gated on approval
  (EMP-06/HR-19) — server-rendered via xhtml2pdf, letterhead + signature blocks.
- Real audit trail (`audit_logs.actor_user_id`, NOT NULL) replacing the prototype's host-PC-account bug.
- **Solde-sufficiency check**: a request is rejected (400) if it would exceed the employee's current
  balance for that leave type, checked per calendar year for a year-spanning request.
- **Automatic congé-payé accrual** (`LeaveType.accrual_legal`, `leave_service.jours_acquis_legaux`):
  "Congé payé"'s `jours_acquis` is computed from the employee's `date_embauche`, not entered manually —
  1.5 days/month of service + a 5-year seniority bonus, capped at 30 days/year, per Morocco's Code du
  Travail (Loi 65-99) Art. 231 & 238. **This is a real legal/financial parameter — the function's
  docstring lists the simplifications it makes (no exclusion of unpaid-leave months, no separate
  6-month eligibility gate, seniority-bonus proration for a partial year isn't literally spelled out in
  the law's text). Get HR/legal sign-off before trusting this for anything beyond an operational
  estimate**, consistent with `HR/CLAUDE.md`'s own stated principle of never silently inventing a legal
  value. HR can no longer manually edit this balance (400 on `PUT /leave-balances`); the fix path for a
  wrong number is correcting the employee's `date_embauche`.
- **Moroccan public holidays**: `POST /holidays/generate-fixed?annee=` (HR only, idempotent) auto-fills
  the 9 fixed-Gregorian-date civil holidays for a year. The mobile Islamic holidays (Aïd al-Fitr, Aïd
  al-Adha, 1 Muharram, Aïd al-Mawlid) shift every year with the lunar calendar and can't be computed —
  those still need manual entry via the same "Jours fériés" panel at `/hr/parametres`, once each year's
  dates are confirmed (same deliberate limitation as the prototype's original empty-seeded holidays).
- **No overlapping leave requests**: a new request is rejected (400) if its dates overlap any of the
  employee's existing pending/approved requests, regardless of leave type — an employee can't be
  simultaneously "on" congé payé and maladie. Rejected/cancelled requests never conflict.
- **Leave type management** (HR-39): HR can create, edit, and deactivate leave types at
  `/hr/parametres` (`POST`/`PUT /leave-types`) instead of needing a developer to change the seed.
  Deactivating a type (soft delete — `is_active`) hides it from new-request pickers without touching
  existing leave_requests/leave_balances that reference it; a type can't be re-deleted outright since
  those FKs would break. Accrual-legal types must also deduct from solde (enforced server-side).
- **Timesheet import + monthly attendance export** (HR-16/HR-20, `/hr/presence`): upload a pointeuse
  export (.xlsx/.csv), map the identifier column (name or matricule) and day columns from a preview,
  confirm to upsert `AttendanceEntry` rows — unmatched names are reported (not auto-fixed; correct the
  source file or the employee record and re-import, no partial reconciliation UI, matching the
  prototype). `GET /attendance/export` produces a real `.xlsx` (openpyxl) with a per-employee/per-day
  grid (pointage code, or the congé's `code_court` if approved leave overlaps that day — flagged as a
  conflict when both exist) plus a "Légende" sheet. Attendance codes (`P`, `A`, ...) are HR-managed at
  `/hr/parametres/codes-presence`, mirroring how leave types work. **Deliberately does not include
  variable pay (avances/primes/commissions) or disciplinary suspensions** in the export, unlike the
  prototype's version — those modules don't exist yet in this rebuild.

## Known gaps / next steps

- No CI pipeline wired yet (lint/test run locally only).
- No Railway/staging deployment — local dev only so far.
- Employee/Department schema is trimmed to what this slice needs (no CIN/CNSS/salaire/documents yet —
  those land with the employee-records module).
- AI hosting provider (§5 open question in TECHNICAL_DECISIONS.md) and CNDP authorization are still open —
  unrelated to this slice, not touched.
- Data migration from the `HR/` prototype's SQLite data is a deliberately separate, later decision
  (PRD open question 6) — this slice seeds fresh reference data only.
