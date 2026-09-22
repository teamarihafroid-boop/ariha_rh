# ARIHA AI — Production Rebuild

Production rebuild of Ariha Froid's HR app (see `../HR/docs/PRD.md` and `../HR/docs/TECHNICAL_DECISIONS.md`
for the full spec). Stack: FastAPI + PostgreSQL + SQLAlchemy 2.0 (backend), React + TypeScript + Vite
(frontend). The old `HR/` prototype (Flask/SQLite, no auth) is left untouched as reference.

**Current slice:** authentication/RBAC foundation (HR / DG / Employee roles), Collaborateurs (employee
records, org chart, equipment/document tracking), Recrutement (offers, candidates, pipeline, CV import,
CDI contract generation), Congés (leave requests/balances/certificates, leave-responsable delegation),
Présence (pointeuse import + monthly export), and Paramètres (départements/postes, leave/attendance
reference data, user accounts) — all behind real RBAC. See `docs/DEPLOYMENT.md` to deploy to production.

## Local setup

Requires Docker, Python 3.11+, Node 18+.

```bash
docker compose up -d          # Postgres (localhost:5433) + Redis (localhost:6379)

cd backend
python -m venv .venv
./.venv/Scripts/pip install -e ".[dev]"      # Windows; use .venv/bin/pip on macOS/Linux
cp .env.example .env                         # optionally set GEMINI_API_KEY to enable CV auto-extraction
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
./.venv/Scripts/python -m pytest          # 213 tests: auth/rate-limiting, RBAC, leave business logic, accrual, holidays, PDF, attendance, employee records, recruitment, file storage (local + S3), CV extraction, user accounts, notifications, backups
./.venv/Scripts/python -m ruff check app tests
./.venv/Scripts/python -m black app tests
```

Note: the test suite uses a separate `ariha_test` database (create once: `CREATE DATABASE ariha_test;`
against the same Postgres container) and Redis DB index 15 — it never touches the dev database/sessions.

## Frontend

```bash
cd frontend
npm run build          # tsc -b && vite build
npm test               # vitest run — 56 component tests
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

- **Employee records** (`/hr/collaborateurs`, `/hr/organigramme`, `/mon-profil`, `/dg/collaborateurs`,
  `/dg/organigramme`): full HR-record CRUD (CIN, CNSS, bilingual name, contract dates, category, salary,
  notes) replacing the auth/leave slice's trimmed `Employee` model. Deactivating a collaborator
  (`DELETE /employees/{id}`) is a **soft delete** — sets `date_sortie` and flips to an inactive
  `EmployeeStatus`, never physically removes the row or cascades into leave/attendance history (a
  deliberate change from the `HR/` prototype's hard cascade delete). Emergency contacts and a
  probation-evaluation history (with a double sign-off gate — see below) are sub-resources of an employee.
  An interactive org chart (`GET /employees/orgchart`) groups active employees by department with a
  cross-department "rapporte à" annotation, and a downloadable PDF employee sheet (xhtml2pdf, same
  approach as the leave certificate) is role-gated: HR and DG get the full sheet (CIN/CNSS/contrat/salaire
  included, per PRD §5's "DG: full detail" access), while an employee's own self-service copy
  (`/me/fiche`) stays restricted to identity/contact/poste. Employee self-service is read-only ("Mon
  profil") — no correction-request flow, matching PRD §5. **DG never gets an in-app write path for
  probation sign-off** — `avis_dg`/`evaluateur_dg` are data fields HR records, since DG's actual input
  happens outside the app (PRD §5/§6.6, same posture as recruitment). A probation-deadline alert banner on
  `/hr/collaborateurs` (`GET /employees/periode-essai/alertes`) surfaces any employee within 10 days of
  `date_fin_periode_essai` that isn't yet double-signed-off (HR-06). **Document upload (HR-02)** — contracts,
  CV, diplomas, each with an optional `date_expiration` — is a sub-resource of an employee (Documents tab on
  `/hr/collaborateurs/:id`), backed by a swappable storage interface (`storage_service.py`, §7's "storage
  behind an interface" recommendation): local disk in dev, refused outright if `ENV=production` and no
  real S3-compatible backend (e.g. Cloudflare R2) has been configured — see "File storage" below. A second
  alert card, "Documents à renouveler," flags any document expiring within 30 days, same read-time pattern
  as the probation alert. HR and DG can download; only HR uploads/deletes; employee self-service does not
  get document access this round (kept narrow, matching PRD §5).

- **Recruitment — core pipeline** (`/hr/recrutement/{offres,candidats,pipeline}`, `/dg/recrutement`): job
  offers, a manually-entered candidate bank with CV/attachment upload, **plus CV field auto-extraction**
  (HR-09, `POST /recruitment/candidates/extract-cv`) — upload a PDF/DOCX/TXT CV and the create-candidate
  form pre-fills from it; every field stays editable, extraction never creates a candidate itself, and a
  failed/unconfigured extraction (missing `GEMINI_API_KEY`, bad response) degrades to the plain manual form
  rather than blocking anything. **Uses Google's Gemini API (free tier), a deliberate deviation from
  `TECHNICAL_DECISIONS.md` §5's Anthropic/OpenAI options** — the user's explicit choice, recorded here since
  it wasn't in that doc. **Sends real CV content (name, contact info) to a third-party API** — the same
  cross-border-transfer/CNDP-authorization question already flagged as open in PRD §8 applies here too; this
  is dev/test only pending that sign-off, same posture as the AI Assistant strategy elsewhere in the docs.
  A Kanban ATS pipeline
  (configurable `ApplicationStage`s, drag-and-drop or a stage picker, comments per application), and
  hire→Employee conversion. Moving a card into the stage flagged `is_hire_stage` (seeded on "Accepté")
  opens a hire proposal pre-filled from the candidate/offer — confirming it calls the same
  `employee_service.create_employee` used by the Employee Records module, never presuming
  `date_embauche`/`date_fin_periode_essai`/`categorie_professionnelle` beyond what's explicitly submitted.
  Duplicate-candidate detection is a simple email-OR-phone exact match, surfaced as a non-blocking warning.
  Comment authorship is the real authenticated user (fixes the prototype's audit gap). DG is read-only;
  **Employee has zero access to this module** (PRD §5). HR can fully edit an existing offer (including
  `date_cloture`, poste, and description — not just title/city/status) or an existing candidate's profile
  after creation; a candidate already linked to an employee is flagged "Embauché"/"Déjà embauché" in both
  the candidate bank and the pipeline board, so HR doesn't try to hire or re-add them by mistake. A card
  already sitting in the `is_hire_stage` column exposes a manual "Proposer l'embauche" button (not just a
  drag-triggered one), and an application can be withdrawn from a pipeline (`DELETE .../applications/{id}`,
  HR only) if it was added in error.

- **User accounts** (`/hr/parametres/utilisateurs`, HR only — DG gets no access, matching PRD §6.12's
  Paramètres row): closes a real gap found by reading the code — creating an **Employee record** and
  creating a **login** were entirely separate things, and nothing but the one-time `seed.py` script ever
  created the latter. HR can now create a login (optionally linked to an existing employee — the picker only
  offers employees who don't already have one), change a role, reset a password, and activate/deactivate an
  account. A **self-lockout guard** refuses to deactivate or demote the last remaining active HR account, so
  HR user management can't lock everyone out of itself. No SMTP/email exists in this app — HR sets the
  initial password directly and shares it outside the app, same implicit pattern as the three seeded demo
  accounts; there's no "send a reset link" flow, and no forced-password-change-on-first-login (not
  requested, would need a new column + a login-flow change). **Also foldable into the moment an employee is
  actually created**, not just the dedicated Comptes page — an optional "Créer aussi un compte de
  connexion" checkbox (`components/AccountCreationFields.tsx`) appears on both `/hr/collaborateurs`' "Nouveau
  collaborateur" form and Recruitment's hire-confirmation modal, so onboarding someone is one submit instead
  of two separate trips to two different pages. If the login step fails after the employee/hire succeeds,
  that's a non-blocking warning, not a rollback — the employee record always survives regardless.

- **Notification center (HR-38 / DG-06)**: the bell (`components/NotificationBell.tsx`, mounted for every
  role) now surfaces four signal types, not just leave decisions. Real, persisted events —
  `notifications` table, mark-as-read, mark-all-read — cover leave approved/rejected (existing) and **a new
  one: every active HR user gets notified the moment an employee submits a leave request** (`POST
  /leave-requests` → `notification_service.notify_leave_pending`). Three more are **computed at read time
  and merged into the bell client-side**, not stored — this app has no cron/scheduler
  (`TECHNICAL_DECISIONS.md` §6 chose Redis+RQ for background jobs, not a scheduler), so calendar-driven
  alerts can't fire as one-time stored events without a real dedup/expiry system: probation deadlines and
  document expiry (both already built, previously page-only banners on `/hr/collaborateurs`) plus a new
  one, **stalled candidacies** (`GET /recruitment/applications/stagnantes`, HR only — an application whose
  `date_dernier_mouvement` hasn't moved in 14+ days and isn't already hired; known simplification: no
  `is_terminal` flag exists on `ApplicationStage`, so an application sitting in "Refusé" also surfaces here
  eventually, HR can withdraw it via the already-built pipeline UI). Computed alerts have no persisted read
  state — clicking one navigates, it doesn't mark-as-read. **Overdue tasks/meeting actions from PRD §6.11's
  carried-over list are not buildable — no Tasks/Meetings module exists in this rebuild.** DG deliberately
  gets no new alert content this round (DG-06 asks for *not* being overwhelmed by HR's operational stream —
  satisfied by not inventing "executive" noise that doesn't correspond to any real signal among built
  modules yet, rather than padding the bell with manufactured content).

### File storage

`app/services/storage_service.py` defines a small `save`/`read`/`delete`-by-key interface
(`TECHNICAL_DECISIONS.md` §7) with one implementation today, `LocalFilesystemStorage` (writes under
`backend/var/uploads/`, gitignored). `get_storage()` reads `STORAGE_BACKEND`/`STORAGE_LOCAL_DIR` from env
and **raises if `STORAGE_BACKEND=local` and `ENV=production`** — Railway's filesystem isn't reliably
persistent across redeploys, so the local backend can never silently ship. Swapping to Cloudflare R2 (or
any S3-compatible store) later is one new class behind this interface, no call-site changes. Uploaded files
are always served through an authenticated/authorized API route (`.../download`), never a direct storage
URL, satisfying §7's access-control requirement regardless of backend.

## Known gaps / next steps

- No CI pipeline wired yet (lint/test run locally only).
- No Railway/staging deployment — local dev only so far. `STORAGE_BACKEND=local` must be swapped for a real
  S3-compatible backend before then (see "File storage" above) — the code refuses to start otherwise.
  `GEMINI_API_KEY` (CV extraction) similarly needs the CNDP sign-off in PRD §8 resolved before real launch.
- Application-level attachments (as opposed to candidate-level, already built) — a deliberate scope cut to
  avoid duplicating the CV-bank concept, not a technical blocker.
- Recruitment's phone screens, interview scoring, candidate tests, and the `RecruitmentRequest`→`JobOffer`
  approval workflow (PRD §6.2) are deferred — the prototype never built UI for these either, so they need
  original design, not porting. `JobOfferStatus`/`ApplicationStage` are seeded but not yet HR-editable
  (same deferral as Position/EmployeeStatus).
- Full Department/Position/EmployeeStatus CRUD UI (PRD §6.12, a Paramètres-module concern) — still
  seed/SQL-managed.
- AI hosting provider (§5 open question in TECHNICAL_DECISIONS.md) and CNDP authorization are still open —
  unrelated to this slice, not touched.
- Data migration from the `HR/` prototype's SQLite data is a deliberately separate, later decision
  (PRD open question 6) — this slice seeds fresh reference data only.
