# ARIHA AI — Technical Decisions (Production)

**Status:** Draft v1 — for review
**Companion doc:** `PRD.md` — read that first; every choice here exists to serve those requirements.
**Scope:** architecture and stack for the production rebuild. The existing Flask/SQLite prototype is not a
constraint — it's prior art. Where a decision below reuses something from the prototype, it's because it's
genuinely the right call, not out of inertia.

## 1. Guiding principles

1. **Railway (PaaS)**, chosen over self-hosting a VPS — decided after weighing ops burden, reliability, and
   backup/DR risk for a solo developer against the cost of a managed platform (see §8). The developer is
   already using Railway for other work, which also means less new operational surface to learn.
2. **Security is not optional this time.** The prototype's "no auth, trust the LAN" model is exactly what
   production must not repeat (PRD §7).
3. **Small team, real maintainability.** One developer is taking this over. Prefer fewer moving parts and
   boring, well-documented technology over novelty.
4. **The AI/RAG pipeline is a real asset, not throwaway code.** Whatever stack is chosen must keep the
   LangChain/FAISS integration and the cloud AI API client (§5) realistic — these are Python-native
   ecosystems. (Meeting audio transcription is dropped for production — see PRD §6.8; meetings now capture
   the PV directly as text.)

## 2. Backend

### Decision: Python, FastAPI, PostgreSQL, SQLAlchemy 2.0, Alembic

**Why Python, specifically:** the AI assistant (RAG via LangChain/FAISS, calling out to an external cloud
AI API per §5) is the hardest, most differentiated part of this application, and its ecosystem is Python.
Rewriting it in another language means reimplementing or losing this capability. Given a single-developer
team, one language end-to-end (backend + AI + background jobs) is a real maintainability win over
splitting the stack.

**Why FastAPI over Flask:** async support (useful for I/O-bound work like calling the AI API or handling
file uploads), built-in request/response validation via Pydantic (removes a whole class of the manual
parsing/validation bugs a hand-rolled Flask API accumulates), automatic OpenAPI docs (useful once multiple
frontends — web app, maybe future mobile — consume the same API), and first-class dependency injection,
which maps cleanly onto **role-based access control**: a `require_role("hr")` dependency is a natural fit
and is easy to unit-test in isolation, which matters a lot now that access control is a hard requirement
instead of nonexistent.

**Why PostgreSQL over SQLite:** SQLite's single-writer model was fine for one PC with one user; it is not
acceptable for a multi-role, concurrently-used production system. PostgreSQL gives real concurrent writes,
proper constraints, JSONB for the flexible fields the prototype already uses (e.g. `notes_criteres`,
`entites_json`), and built-in full-text search — which can also reduce reliance on FAISS for some simpler
lookups (see §5).

**Why Alembic:** the prototype's `_apply_lightweight_migrations()` (auto-`ALTER TABLE ADD COLUMN`, no
rename/drop support) was a reasonable hack for a single non-technical maintainer but is not appropriate
once schema changes need to be reviewed, reversible, and safely deployed. Alembic is the standard
SQLAlchemy migration tool and integrates directly with the existing model definitions.

**Architecture layering:** keep the prototype's proven separation — `models` / `services` / `routers`
(FastAPI's term for blueprints) — one router per domain, services never import FastAPI, models never import
either. This part of the prototype's architecture was already correct and is worth preserving as a
convention, independent of the framework rewrite.

## 3. Authentication & Authorization

### Decision: server-side sessions (not bare JWT), Argon2 password hashing, RBAC with per-resource scoping

- **Sessions over JWT:** for a single-tenant app with a browser-based UI, server-side sessions
  (signed, httpOnly, secure cookies backed by a Redis session store) are simpler to reason about and to
  revoke instantly (e.g., disabling a departed employee's access) than JWTs, which are awkward to revoke
  before expiry. JWT would matter more if a separate mobile app or third-party API consumer existed — not
  the case here.
- **Argon2id** for password hashing (current best practice, memory-hard, resists GPU cracking better than
  bcrypt).
- **RBAC model:** three roles from PRD §5 — HR (full), DG (view-only, every module except Tâches, which it
  cannot access at all), Employee (self-service, own data only). There is **no fourth "Manager" role**.
  Instead, the one department-scoped exception (leave-responsable, PRD §5) is modeled as a capability on a
  specific `Employee` row, not a role: a nullable `Department.leave_responsable_employee_id` FK, checked by
  a narrow dependency (e.g. `can_submit_leave_for(department_id)`) used only on the leave-submission
  endpoint — it grants nothing else. Row-level scoping (an Employee only ever sees their own record; DG
  never sees Tâches at all, not even read-only) is enforced in the service layer (query filters / route
  guards), not just hidden in the UI — verified in code review and covered by tests (§9).
- **Audit trail fix:** replace `audit_service.py::current_user()` (currently returns the host PC's Windows
  account — flagged in the prototype's own audit) with the real authenticated session user. This was the
  single most-flagged issue in the prototype's security audit and is a hard requirement, not a nice-to-have.
- **Password reset / account provisioning:** HR creates accounts for new hires (tied into the existing
  hiring workflow — `hiring_workflow_service.py` already converts an application into an employee; extend
  it to optionally provision a login). Self-service password reset via email.

## 4. Frontend

### Decision: React + TypeScript, a component library (e.g. shadcn/ui or MUI), Vite

The prototype's single 4,300-line vanilla JS file with manual `innerHTML` templating was appropriate for
one non-technical author iterating with an AI agent. It is not appropriate once:
- Four roles need meaningfully different UIs (not just hidden buttons).
- A new employee self-service portal is being built from scratch (PRD §5, §6.1–6.6) — new surface area,
  not a retrofit.
- A second developer may eventually join — untyped, un-componentized JS is expensive to onboard into.

**Why React + TypeScript specifically:** widest ecosystem and hiring pool if the team grows, mature
component libraries that cover most of the CRUD/table/Kanban/calendar UI patterns this app is full of
(reducing custom CSS work versus the prototype's hand-written `style.css`), and TypeScript catches the
exact class of bug (`esc()` not called before `innerHTML`, silently wrong field names) that the prototype's
architecture skill had to document as a manual discipline rule. A type system enforces it instead.

**Migration approach:** rebuild screen-by-screen against the new API, using the existing `app.js` as a
*functional reference* for exact behavior (it's a good spec — it just shouldn't be extended further).

## 5. AI strategy — Decision: direct/global cloud API (not self-hosted, not EU-restricted)

Per PRD §6.10 and §8. Resolved: the assistant's generation step (and embeddings) run on a direct/global
cloud AI API — e.g. the Anthropic API or OpenAI API, called directly rather than through an EU-region
managed offering (AWS Bedrock / Google Vertex AI EU) — rather than a self-hosted model. The prototype's
`llama3.2:3b`/Ollama setup is not carried into production. Ariha Froid explicitly chose the global option
over the EU-region-only alternative, accepting the compliance step this adds (see below) in exchange for
provider simplicity/choice. Still open: the exact provider and a signed data processing agreement.

| | Self-hosted (prototype, dropped) | EU-region cloud API (considered, not chosen) | Direct/global cloud API (decided) |
|---|---|---|---|
| **Privacy** | Strongest in theory — no HR data ever left the server. | HR data sent to a third party, but the transfer itself is compliant by construction (EU is an "adequate protection" destination under Loi 09-08). | HR data (employee names, performance text, disciplinary content) is sent to a third-party provider outside Morocco's "adequate protection" list — legal, but only after prior CNDP authorization and safeguards (standard contractual clauses) are in place (PRD §8, question 5b). Needs a data processing agreement and explicit Ariha Froid sign-off given the sensitivity of the data involved. |
| **Quality** | `llama3.2:3b` is a small model chosen specifically to run on CPU without a GPU — noticeably weaker reasoning than frontier cloud models, especially on nuanced drafting (contracts, job descriptions). | Meaningfully better than local, though EU-region deployments sometimes lag the provider's flagship models. | Meaningfully better generation quality and reliability, direct access to the provider's latest models, less prompt-engineering effort needed to get consistent results. |
| **Infra cost** | Needs a Railway service with enough RAM/CPU to run Ollama continuously — a real, fixed infrastructure line item regardless of usage. | Pay-per-use API cost. | Pay-per-use API cost, no model-serving infrastructure to maintain — the reason this was chosen over self-hosting. |
| **Operational burden** | Model updates, prompt tuning, and troubleshooting inference issues are entirely on the team. | Provider handles model quality/updates; team only maintains the integration. | Same, plus a one-time CNDP authorization step and DPA to put in place before launch. |
| **Offline resilience** | Works even if the server's internet connection drops. | Requires outbound internet connectivity to the API provider at all times. | Requires outbound internet connectivity to the API provider at all times. |

**Compliance consequence of this choice:** because the chosen provider is not on Morocco's "adequate
protection" list, this transfer requires prior CNDP authorization and safeguards before launch — see PRD
§8, question 5b. This is a separate authorization from the app's own hosting region (Railway, §8 below),
which stays EU-hosted regardless.

**Scope note:** transcription is no longer part of this decision — it's dropped for production (PRD §6.8),
so this covers the **chat assistant's generation step and its embeddings**. The RAG retrieval index itself
(FAISS or equivalent, over the company's own data) can still be built and queried on the server; only the
embedding and generation calls leave the server, and only the retrieved context is sent, not the full
database.

## 6. Background jobs

### Decision: Redis + RQ (not Celery)

Async work still needed: monthly Excel exports, eventually notification digests, and any AI generation
calls worth running off the request/response cycle. Celery is the more common choice but brings meaningful
operational complexity
(broker + result backend + worker pools + beat scheduler) that isn't justified at this scale (single
company, moderate job volume). **RQ** (Redis Queue) gives a simple job queue backed by the same Redis
instance already needed for sessions (§3), with a much smaller operational surface for a solo developer to
own.

## 7. File storage

### Decision: S3-compatible object storage from day one (e.g. Cloudflare R2), not local disk

Uploaded files (CVs, contracts, payslips) currently live directly in `data/documents/` on the host PC,
served without access control beyond "the route exists." On Railway, a service's local filesystem is not
reliably persistent across redeploys/restarts the way a VPS's disk is (Railway Volumes exist but are tied
to a single service instance and are a worse fit for this than object storage) — so unlike the earlier
VPS-based plan, **start directly with S3-compatible object storage** rather than "filesystem now, migrate
later." **Cloudflare R2** is a good default: S3-compatible API (works with the same tooling/SDKs as AWS
S3), no egress fees (matters for serving files like payslips/CVs back to users), and cheap at this scale.
- Files must be served through an authenticated, authorized route (never a direct storage URL) — enforce
  the same RBAC as the data they belong to (e.g., a payslip file must pass the same check as the `Payslip`
  record it belongs to) — generate short-lived signed URLs or proxy the download through the API.
- Structure storage access behind a small internal interface (`save`, `read`, `delete` by key) so the
  actual provider (R2 vs. S3 vs. something else) stays swappable without touching every call site.

## 8. Deployment & infrastructure

### Decision: Railway, EU region, with managed Postgres + Redis add-ons, GitHub Actions for CI gating

- **Region: EU** (e.g. Railway's EU-West), not US — driven by Loi 09-08's cross-border data transfer rules
  (PRD §8 open question 5a): the EU qualifies as an "adequate protection" destination under Moroccan law,
  the US does not without extra CNDP authorization. Every managed add-on (Postgres, Redis) and any object
  storage bucket (§7) should be provisioned in the same EU region — there's no data-residency benefit to
  getting compute right and leaving the database or file storage in a US region by default. **This is a
  separate transfer from the AI API's own region (§5)** — Railway staying EU-hosted does not cover the AI
  API's compliance requirement (PRD §8 question 5b); that needs its own CNDP authorization.
- **Services on Railway:** `app` (FastAPI, deployed from a Dockerfile or Railway's native buildpack),
  `worker` (RQ), plus Railway's managed **Postgres** and **Redis** plugins provisioned in the same project
  — connection strings are injected automatically as environment variables, no manual wiring needed. No
  `ollama` service: AI generation and embeddings run against a direct/global cloud API (§5), not a
  self-hosted model, so there's no model-serving workload on Railway — only the API key/credentials to
  manage as a
  secret.
- **TLS & routing:** handled automatically by Railway (HTTPS on the provided domain or a custom domain) —
  no Caddy/Nginx needed, unlike the earlier self-hosted plan.
- **CI (GitHub Actions):** lint + typecheck + test on every PR — this is the gate that matters, since
  Railway's own GitHub integration can auto-deploy on push to `main`. Keep the actual deploy trigger tied
  to CI passing (either by only merging to `main` after CI is green, or by using the Railway CLI in a
  GitHub Actions job for more explicit control) so a broken build never reaches production automatically.
- **Backups:** rely on Railway's managed Postgres backups as the first line, but also run an independent
  nightly `pg_dump`, encrypted, exported to the same object storage as file uploads (§7) — a backup that
  only lives inside the platform you're depending on is a single point of failure for exactly the
  disaster-recovery risk that motivated moving off self-hosting in the first place. Either way, this
  replaces the prototype's "manually copy the `data/` folder" process, which is not acceptable for
  production (PRD §7).
- **Secrets:** Railway's built-in per-environment variable management — never committed, unlike the
  prototype's hardcoded default `SECRET_KEY`.
- **Staging:** Railway supports multiple environments per project (e.g. `staging` and `production`) — use
  a separate staging environment with its own database before any deploy touches real Ariha Froid data.

## 9. Testing & code quality

- **Backend:** `pytest`, with the RBAC scoping rules (§3) specifically covered — every "DG gets zero access
  to Tâches," "employee can't see another employee's payslip," and "leave-responsable can only submit for
  their own department" rule needs a test, since this is the single biggest behavioral gap versus the
  prototype.
- **Frontend:** Vitest + React Testing Library for component/interaction tests.
- **Linting/formatting:** `ruff` + `black` (Python), `eslint` + `prettier` (TypeScript) — enforced in CI,
  not just locally.
- The prototype had **zero automated tests** (explicitly flagged in its own audit) — this is the other
  major gap production must close, not just the security one.

## 10. Observability

- Structured logging (JSON) from the app — Railway captures service logs natively, but for anything worth
  keeping beyond Railway's own retention window, ship to a simple external log aggregator.
- Error tracking (e.g. a hosted Sentry free tier) — the prototype has no visibility into failures beyond
  someone noticing the app misbehaving.
- Basic uptime monitoring (external ping) given PRD §7's availability requirement — worth having
  independent of Railway's own status, so an outage is caught even if Railway's own monitoring doesn't
  surface it fast enough.

## 11. Data migration from the prototype

Per PRD §8 open question 7 — if real data needs to move from the prototype's SQLite database into
production PostgreSQL:
- Write a one-time migration script (not a general-purpose sync) mapping SQLite tables to the new schema.
- Run it against a copy, validate row counts and spot-check sensitive records (payroll, disciplinary)
  before any cutover.
- Decide the cutover moment with HR — the prototype and production should not run in parallel accepting
  writes to both, to avoid divergence.

## 12. What's deliberately not being carried over

- The lightweight auto-migration hack (§2) — replaced by Alembic.
- The single shared login (§3) — replaced by real RBAC.
- Vanilla JS templating (§4) — replaced by React/TypeScript.
- `HOST=0.0.0.0` unauthenticated LAN exposure — replaced by TLS + real auth over the internet. On Railway
  the app is reachable via a public HTTPS domain by default (there's no LAN to restrict to anymore), so
  authentication is now the only access boundary — this makes RBAC (§3) load-bearing in a way it wasn't
  when the LAN itself was the (weak) perimeter.
