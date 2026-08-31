# ARIHA AI — Product Requirements Document (Production)

**Status:** Draft v1 — for review
**Owner:** Engineering (new developer handoff)
**Source material:** existing local prototype (`README.md`, `ANALYSE_TECHNIQUE.md`), built iteratively by
Ariha Froid's HR manager via Claude Code.

## 1. Summary

ARIHA AI is Ariha Froid's HR system: employee records, recruitment, attendance & leave, payroll journal,
performance & discipline, tasks, meetings, and a local AI assistant. A working prototype already exists and
is in daily use, built by the HR manager herself (no coding background) by describing what she needed to
an AI coding agent. It runs on a single Windows PC on the office LAN, with no authentication — anyone who
reaches the machine's IP can use and see everything.

This PRD defines what "production" means for ARIHA AI: the same functional ground, rebuilt to support
**multiple distinct users with different permissions**, hosted so it's reliably available rather than
depending on one PC staying powered on, and hardened enough to hold CIN numbers, CNSS numbers, salaries,
and disciplinary records safely.

**This is a rebuild, not a migration.** The prototype's code is treated as validated *requirements*, not as
a foundation to extend. Engineering is free to choose whatever stack and architecture best serves this PRD
(see the companion `TECHNICAL_DECISIONS.md`).

## 2. Background

- The prototype was built module-by-module over time, driven entirely by the HR manager's real day-to-day
  needs — this means the feature set, while unconventional in places, is *not speculative*. Every module
  exists because someone needed it.
- A security/architecture audit of the prototype (2026-08-11, recorded in `CLAUDE.md`) identified: no
  authentication, LAN-wide exposure by design, an audit trail that logs the host PC's Windows account
  rather than the real actor, no automated tests, and no real schema migration tooling.
- The company (Ariha Froid, commercial/industrial refrigeration, Morocco) intends to keep using this system
  as its system of record for HR — the rebuild needs to reach parity with the prototype's real modules
  before or alongside adding anything new.

## 3. Goals

1. **Multi-role access** — HR, Direction Générale (DG), and Employees each get their own login and see
   only what their role should see, including a narrow department-scoped leave-submission capability that
   isn't a full role of its own (see §5).
2. **Reliable hosting** — the app runs on infrastructure that doesn't depend on one employee's PC staying
   on; planned maintenance and outages are handled gracefully.
3. **Data safety** — sensitive data (CIN, CNSS, salary, disciplinary files) is protected by real
   authentication, authorization, and an audit trail that identifies the actual person who acted.
4. **Functional parity first** — every module the HR manager actually uses today keeps working at least as
   well after the rebuild, before new scope is added.
5. **Room to grow** — the new architecture should make it realistic to add the features in §6.4 (new
   capabilities) without another full rebuild.

## 4. Non-Goals (for this phase)

- Multi-tenant SaaS (supporting other companies besides Ariha Froid) — single-tenant only, for now.
- Building a real payroll *calculation* engine (CNSS/IR computation from scratch) — the app will continue
  to centralize payslips already produced elsewhere, not calculate them (see `PAIE` in §6).
- Full legal/compliance sign-off on the termination-indemnity simulator — it stays an indicative tool, not
  a certified legal product.
- Native mobile apps — a responsive web app is sufficient for this phase.
- OCR for scanned image documents.

## 5. Users & Roles

Today: one shared, unauthenticated login. Production needs **three real roles** — HR, DG, Employee — plus
one narrowly-scoped capability that is deliberately *not* a fourth role.

| Module / data | HR | Direction Générale (DG) | Employee (self-service) |
|---|---|---|---|
| Employee records | Full (create/edit/delete) | Read-only, full detail, all employees | Read-only, **own record only** — a recap of their own info, no editing, no correction-request flow |
| Org chart | Full | Read-only | Read-only |
| Recruitment (offers, candidates, ATS) | Full, including final approval | Read-only | None |
| Attendance & leave | Full (import, correct, approve) | Read-only, company-wide | Request own leave, or via department leave-responsable (see below); view own balance; **download a printable leave certificate once HR approves a request** |
| Variable pay (advances, loans, bonuses) | Full | Read-only, full detail | View own only |
| Payroll (payslips, mass salariale) | Full | Read-only, full detail, including individual payslips | View/download own payslips only |
| Performance & KPI | Full | Read-only, full detail | View own reviews & KPIs only — **scope pending**, see note below |
| Disciplinary records | Full | Read-only, full detail | None |
| Tasks | Full | **No access at all** | **None — not part of employee self-service** |
| Meetings | Full | Read-only | None (unless a participant) |
| Documents library | Full | Read-only | Scoped to visible categories |
| Knowledge base / wiki | Full | Read | Read |
| Job descriptions & skills | Full | Read | Read own job description |
| Cockpits (dashboards) | HR cockpit + any team-level cockpit (see below) | DG cockpit | Personal dashboard (**new**) |
| Notifications | All HR-relevant alerts | Executive-relevant alerts only | Own alerts only (**new**) |
| Settings / parameters | Full | None | None |

**Employee self-service is deliberately narrow.** It is: a recap of their own info, their leave balance,
requesting leave, downloading the resulting printable leave certificate once approved, and viewing their
own payslips — not a scaled-down version of every HR module. Tasks and profile-correction requests were
in an earlier draft of this PRD and are **out of scope** — a normal employee never sees a task list or
task-management surface in this app at all.

**Performance & KPI self-service is tentatively in scope, but the underlying process isn't defined yet.**
Ariha Froid hasn't decided how performance evaluation will actually work going forward, so this row stays
a placeholder — build the rest of self-service first, and revisit this once that process is settled rather
than guessing at its shape now.

**DG is strictly view-only, everywhere it has access, with no exceptions.** The current prototype has DG
actively validate recruitment requests and weigh in on probation-period decisions inside the app —
production **drops that in-app approval gate entirely**. DG can still see the outcome of those workflows
(read access), but HR is the only role that ever clicks approve/reject; any input DG gives happens outside
the app and HR records the resulting decision.

### Leave-responsable — not a role, a per-department flag

There is no separate "Manager" login role. What exists instead is one narrow, per-department capability:

- Each **Department** gets a new setting in Paramètres (configurable like everything else in this app): a
  yes/no toggle for whether it has a leave-responsable, and if yes, which single employee holds that role
  for the department.
- In a department **with** the toggle on: that one designated employee can submit a leave request on
  behalf of any employee in that department. That is their *entire* extra capability — no salary
  visibility, no task or KPI oversight, nothing else. They remain a normal Employee for every other module.
- In a department **without** the toggle: employees submit their own leave requests directly.
- **Either way, every leave request still requires HR approval before it's recorded as granted.** The
  toggle only changes who *submits* the request, never who approves it — HR remains the single approval
  authority for leave.

**The prototype's "Manager Cockpit"** (a team-level dashboard: overdue tasks, KPIs, leave for a manager's
direct reports) is **kept, but repurposed as an HR-only tool** — HR can open any department/team's cockpit
view to check on its status. It is not exposed as a separate login-restricted role, since no such role
exists in this model.

**New capability implied by this table:** an **Employee self-service portal** does not exist in the
prototype at all today — a recap of their own info, leave balance, requesting leave, downloading the
resulting printable certificate once approved, and viewing own payslips. This is the single biggest
net-new scope item versus the prototype.

## 6. Functional Requirements

Organized by the prototype's existing modules. For each: what's carried over as-is, what changes for
production, and what's genuinely new.

### 6.1 Employés (Employee records)
- **Carried over:** full profile (bilingual name, CIN, CNSS, contract dates, contacts), documents
  (contracts, CV, diplomas, with expiry tracking), emergency contacts, interactive org chart, printable
  employee sheet, probation-period double sign-off (HR + DG) with auto-reminder 10 days before deadline.
- **Changes for production:** field-level visibility by role (see §5 table); an audit trail that records
  the real logged-in user, not a shared account.
- **New:** employees get a read-only recap of their own record. No correction-request flow — if something
  needs updating, that happens outside the app (ask HR directly), not through a submitted request.

### 6.2 Recrutement (Recruitment)
- **Carried over:** job offers, CV bank with automatic extraction (name, contact, city, skills — always
  editable, never final), duplicate detection, Kanban ATS pipeline, phone screens, interview scoring,
  candidate tests, comments/attachments per application, conversion of an accepted application into an
  employee record.
- **Changes for production:** the upstream `RecruitmentRequest` workflow (demandeur → HR validates →
  converted to a job offer) becomes a real, accountable HR-only approval gate. The DG validation step in
  the current prototype is dropped, per §5. The `demandeur` field stays a free-text/reference field
  recording who's asking, since there's no separate role tied to it — HR creates the request on their
  behalf.
- **New:** none required for parity; candidate-facing application forms are out of scope unless requested.

### 6.3 Présence & Congés (Attendance & Leave)
- **Carried over:** unified calendar (leave, holidays, suspensions), attendance-code import from a
  timesheet spreadsheet with manual reconciliation, per-employee/per-type leave balances, monthly
  consolidated attendance state with Excel export, printable leave-request form.
- **Changes for production:** leave requests move from "HR enters everything manually" to a real
  request/approval flow (full mechanism in §5): the employee submits their own request, or — in
  departments with a designated leave-responsable — that person submits on the employee's behalf. HR
  approves in every case. This is a genuine process change for the HR team, not just an access-control
  change.
- **New:** employee-facing "my leave balance" and "request leave" views; a leave-responsable's "submit for
  my department" view; the Department-level leave-responsable toggle and assignment in Paramètres.
  **The employee-facing flow's endpoint is the printable leave certificate** — the prototype's existing
  printable form (carried over above) becomes something the employee can download themselves the moment
  HR approves their request, not just a document HR prints for a physical file. This is the core of what
  "employee self-service" actually means for this module — see §5.

### 6.4 Rémunération variable (Variable pay)
- **Carried over:** salary advances, loans (with repayment schedule/balance), back pay, performance bonuses,
  commissions — all rolled into the monthly attendance/pay detail per employee.
- **Changes for production:** none functionally; access restricted per §5.
- **New:** employee view of their own variable-pay history (currently only visible to HR).

### 6.5 Paie (Payroll)
- **Carried over:** payslip import (PDF, key figures entered manually — the PDF remains authoritative,
  nothing is auto-calculated), monthly mass-salariale analysis (brut/net/cotisations), simple projection
  by carrying forward the last known mass, termination-indemnity simulator (Moroccan labor law, indicative
  only).
- **Changes for production:** none functionally; this module explicitly does **not** become a real payroll
  engine (see Non-Goals).
- **New:** employee self-service payslip download (their own payslips only), which does not exist today.

### 6.6 Performance & Discipline
- **Carried over:** annual evaluation campaigns, KPI tracking per employee, bilingual (FR/AR) disciplinary
  files with hearing minutes, printable and signature-ready.
- **Changes for production:** evaluation and KPI entry remain HR-only — there is no manager role to
  delegate this to (§5); DG's role in the current prototype's probation/evaluation input becomes view-only,
  same as the recruitment gate in §6.2; disciplinary records remain HR-only, full stop.
- **New — tentative:** employee view of their own evaluations and KPI results. Ariha Froid hasn't yet
  decided how performance evaluation will actually work going forward, so treat this as a placeholder
  rather than a spec — don't build it ahead of that decision.

### 6.7 Emplois & Compétences (Jobs & Skills)
- **Carried over:** job descriptions distinct from recruitment offers, skills catalogue by category,
  reusable across job descriptions and (once built) the training module.
- **Changes for production:** none beyond access control.
- **New:** none required for parity.

### 6.8 Tâches (Tasks), Réunions (Meetings), Base de connaissances (Knowledge base)
- **Carried over:** Kanban/list/calendar task views with subtasks, comments, attachments; AI-generated
  meeting summary (decisions, action items); wiki-style knowledge base with tagging and search.
- **Changes for production — decided:** audio/video import and local transcription (Faster-Whisper) are
  **dropped**. Meetings now capture the PV (procès-verbal / minutes) directly — typed or uploaded as a
  document — instead of an audio recording that gets auto-transcribed. The AI assistant still reads that
  PV text and generates the structured summary (decisions, action items) exactly as it does today from a
  transcript; only the audio-to-text step is removed, not the AI summarization step. This simplifies the
  module meaningfully: no audio file storage, no async transcription job, no Faster-Whisper dependency.
- **Changes for production:** task/meeting visibility scoped by role and participation (see §5) — note that
  DG has **no access at all** to Tâches, not even read-only; the bidirectional Task↔Meeting/Performance
  sync (a deliberate coupling in the prototype) is preserved. **Employees also have no access to Tâches at
  all** — it stays an HR-internal work-tracking tool, same exclusion as DG, not something that scales down
  into a personal task list for self-service.
- **New:** none required for parity.

### 6.9 Documents
- **Carried over:** centralized document library (PDF/Word/Excel/images), configurable categories,
  keyword search over indexed content, version history.
- **Changes for production:** access scoped by category and role; storage should move off local disk to a
  managed store appropriate for the chosen hosting (see technical doc).
- **New:** none required for parity.

### 6.10 Assistant IA (AI Assistant)
- **Carried over:** chat assistant answering from real ARIHA AI data with cited sources, recognized direct
  commands, drafting of job descriptions/contracts (always marked as drafts), meeting summarization — all
  write actions require explicit human confirmation before execution.
- **Changes for production:** **decided** — the assistant moves off the prototype's fully local model to a
  direct/global cloud AI API (e.g. the Anthropic or OpenAI API), replacing the "no data ever leaves the
  building" guarantee with "HR data is sent to a third-party provider outside Morocco (typically the US)
  for inference." See `TECHNICAL_DECISIONS.md` §5. Because the provider is outside the countries Morocco's
  Loi 09-08 treats as having "adequate" data protection, this requires prior CNDP authorization and
  safeguards (standard contractual clauses) before launch — see Open Questions §8, question 5b. Still needs
  Ariha Froid's explicit sign-off on the privacy implication before building.
- **New:** the assistant's RAG retrieval must respect the same data-visibility rules as the rest of the app
  per role (e.g., DG asking the assistant about Tâches should get nothing back, since DG has no access to
  that module at all; an employee should never get another employee's salary in an answer).

### 6.11 Centre de notifications (Notifications)
- **Carried over:** overdue tasks, overdue meeting actions, upcoming leave, stalled applications, probation
  deadlines.
- **Changes for production:** notifications scoped per role (see §5).
- **New:** employee-facing notifications (their own leave approved/rejected, task assigned, evaluation due).

### 6.12 Paramètres (Settings)
- **Carried over:** departments, positions, statuses, document types, offer statuses, ATS stages, leave
  types, attendance codes, task columns/priorities, wiki categories, KPI definitions, sanction types, skill
  categories — all editable, nothing hardcoded.
- **Changes for production:** HR-only access; changes to reference data used in legal/financial calculations
  (e.g. SMIG) should be logged in the audit trail given their downstream impact.
- **New:** role/permission management itself becomes a new settings area (who has which role).

### 6.13 Formations (Training) — not yet built in the prototype
Referenced in the prototype's roadmap (catalogue, participants, attendance, certificates) but not
implemented. Confirm with HR whether this is in scope for the production v1 or a later phase.

## 7. Non-Functional Requirements

- **Security:** real authentication (§5 roles), authorization enforced server-side (not just hidden in the
  UI), CSRF protection, secrets never hardcoded, an audit trail that identifies the real actor.
- **Data protection:** CIN, CNSS, salary, and disciplinary data are personal/sensitive data under Moroccan
  data protection rules (Loi 09-08) — access must be logged and restricted per §5, and backups must be
  encrypted at rest.
- **Availability:** the app should not depend on a single employee's PC being on. Target uptime and
  acceptable maintenance windows to be defined with Ariha Froid (see Open Questions).
- **Backups:** automated, regular, tested restore procedure — today's model ("copy the `data/` folder
  manually") is not acceptable in production.
- **Localization:** French as the primary language throughout; Arabic required specifically for
  disciplinary documents and employee bilingual name fields, matching the prototype.
- **Auditability:** every write to sensitive data (employee record, payroll, disciplinary) must be
  attributable to a real user and timestamped.
- **Browser support:** modern evergreen browsers (Chrome, Edge, Firefox, Safari) — no legacy IE support
  needed.

## 8. Open Questions

These need an answer from Ariha Froid (HR + DG) and/or a decision from engineering before or during build:

1. **AI hosting strategy — decided.** The assistant's generation step (and embeddings) move to a
   direct/global cloud AI API (e.g. the Anthropic or OpenAI API), replacing the prototype's fully local
   Ollama setup — chosen over an EU-region-only option (Bedrock/Vertex AI) despite the extra compliance
   step below, per Ariha Froid's preference. (See `TECHNICAL_DECISIONS.md` §5. Transcription itself is no
   longer part of this question — dropped per §6.8.) What still needs Ariha Froid's explicit sign-off:
   that sending HR data to a third-party API provider outside Morocco is acceptable, which provider to
   use, and completing the CNDP authorization this now requires (see question 5b below).
2. **Leave-responsable data collection** — the mechanism is settled (§5), but the actual list of which
   departments currently work this way, and who that designated person is in each, needs to be gathered
   from HR before launch so it can be seeded into Paramètres.
3. **Formations module** — in scope for production v1, or deferred?
4. **Availability target** — is occasional planned downtime (e.g., a maintenance window) acceptable, or
   does this need to be always-on?
5. **Data residency — two separate transfers, two separate answers.** Morocco's Loi 09-08 restricts
   personal-data transfers abroad by default, but explicitly permits transfers to countries with
   "adequate" protection — the EU, Switzerland, and Canada — without extra authorization; transfers
   elsewhere (including the US) require prior CNDP authorization and safeguards (standard contractual
   clauses). This app has two distinct cross-border transfers to evaluate separately:
   - **(a) App hosting (Railway).** **Plan: host on Railway's EU region** — likely compliant by default,
     and there's no upside to choosing US here. Still needs confirming with Ariha Froid that EU hosting is
     acceptable to them (frame it as informing them of the legal default, not asking them to invent a
     policy).
   - **(b) The AI API provider (§6.10, `TECHNICAL_DECISIONS.md` §5).** Ariha Froid has chosen a
     direct/global provider (e.g. Anthropic or OpenAI directly) over an EU-region-only option, which means
     HR data sent to the AI assistant (employee names, performance text, disciplinary content depending on
     the query) crosses into a non-"adequate" jurisdiction. **This requires prior CNDP authorization and
     safeguards before launch** — not optional, and not satisfied by (a)'s Railway EU choice, since these
     are two separate transfers to two separate destinations.
   - Independent of both of the above: whether Ariha Froid already has a CNDP declaration/authorization
     for processing this employee data (CIN, CNSS, salary, disciplinary records) at all — required under
     Loi 09-08 regardless of hosting location, and worth checking whether that already exists.
   - **This should be verified with a Moroccan lawyer or directly via cndp.ma before launch** — this
     section is based on public research, not a review of Ariha Froid's specific situation, and the
     penalties for getting it wrong are real (fines up to 600,000 MAD, potential imprisonment for serious
     breaches).
6. **Existing data migration** — does the current prototype's `data/` folder (real employee/candidate data)
   need to be migrated into the production system, or does production start clean?
7. **Recruitment request origin** — confirmed HR creates every `RecruitmentRequest` on behalf of whoever's
   asking, since no separate submitting role exists (§6.2). Confirm this actually matches how these
   requests originate today (e.g., does a department head currently ask HR verbally/by email, or is there
   an existing process this needs to match)?

## 9. Success Criteria

- HR, DG, and Employee roles can log in independently and each sees exactly the data defined in §5,
  including correct enforcement of DG's Tâches exclusion and the per-department leave-responsable flag.
- Every module marked "carried over" in §6 works at least as well as the prototype, verified against real
  HR workflows before cutover.
- No shared/anonymous access to any HR data remains.
- Audit log entries correctly identify the real acting user for 100% of sensitive-data writes.
- Automated backups exist with a demonstrated, tested restore.
