# ARIHA AI — User Stories

**Status:** Draft v1 — derived directly from `PRD.md` §5 (Users & Roles) and §6 (Functional Requirements).
If a story here conflicts with the PRD, the PRD is the source of truth — update both together.

Each story is `ID: As a <role>, I want to <capability>, so that <benefit>.` IDs exist so these can be
referenced from tickets/tests later. Three real roles (**HR**, **Direction Générale / DG**, **Employee**)
plus one narrow capability that is deliberately not a fourth role (**leave-responsable** — see PRD §5).

## HR

### Collaborateurs
- **HR-01**: As HR, I want to create, edit, and archive employee records (identity, CIN, CNSS, contract
  dates, bilingual name), so that the company has one accurate source of truth for every employee.
- **HR-02**: As HR, I want to upload employee documents (contracts, CV, diplomas) and track their expiry
  dates, so that I'm alerted before something lapses.
- **HR-03**: As HR, I want to record emergency contacts per employee, so that the right person can be
  reached quickly if needed.
- **HR-04**: As HR, I want to view the interactive org chart, so that I can see reporting lines at a
  glance.
- **HR-05**: As HR, I want to print an individual employee sheet, so that I can keep a physical copy in a
  personnel file when needed.
- **HR-06**: As HR, I want to record probation-period evaluations and get an automatic reminder 10 days
  before a probation deadline, so that no decision is missed.
- **HR-07**: As HR, I want every write to an employee record attributed to my real logged-in account (not
  a shared login), so that there's a trustworthy audit trail.

### Recrutement
- **HR-08**: As HR, I want to publish and manage job offers, so that open positions feed the recruitment
  pipeline.
- **HR-09**: As HR, I want candidate info auto-extracted from uploaded CVs (while staying fully editable),
  so that I don't retype it by hand.
- **HR-10**: As HR, I want duplicate candidates flagged automatically, so that I don't create redundant
  records.
- **HR-11**: As HR, I want to move a candidate through a Kanban recruitment pipeline (screening,
  interviews, tests, offer), so that I can track where each candidacy stands.
- **HR-12**: As HR, I want to log phone screens, interview scores, and test results per candidate, so that
  hiring decisions are backed by a documented record.
- **HR-13**: As HR, I want to convert an accepted candidacy directly into an employee record, so that I
  never re-enter the same information twice.
- **HR-14**: As HR, I want to receive and give final approval on recruitment requests (a department asking
  to hire), so that new positions are validated before an offer goes out.

### Présence & Congés
- **HR-15**: As HR, I want a unified calendar of leave, holidays, and suspensions, so that I can see the
  whole company's attendance picture at once.
- **HR-16**: As HR, I want to import a monthly timesheet spreadsheet and manually reconcile unmatched
  rows, so that attendance data stays accurate even when the source file is messy.
- **HR-17**: As HR, I want to see and correct each employee's leave balance, so that balances stay accurate
  over time.
- **HR-18**: As HR, I want to review and approve or reject every leave request — whether submitted by the
  employee or by a department's leave-responsable — so that I remain the single approval authority for
  leave.
- **HR-19**: As HR, I want an approved leave request to automatically produce a printable/downloadable
  leave certificate for the employee, so that I don't generate it by hand every time.
- **HR-20**: As HR, I want to export the monthly consolidated attendance state to Excel, so that I can hand
  it to payroll.

### Rémunération variable
- **HR-21**: As HR, I want to record salary advances, loans (with a repayment schedule), back pay, bonuses,
  and commissions per employee, so that all variable pay lives in one place.

### Paie
- **HR-22**: As HR, I want to centralize payslips already issued elsewhere (importing the PDF, key figures
  entered manually), so that I have one place to find any employee's pay history.
- **HR-23**: As HR, I want a monthly masse-salariale view (brut/net/cotisations) with a simple forward
  projection, so that I can track payroll cost trends.
- **HR-24**: As HR, I want to run an indicative termination-indemnity simulation under Moroccan labor law,
  so that I can estimate severance cost before a difficult conversation — understanding it is never a
  certified legal opinion.

### Performance & Discipline
- **HR-25**: As HR, I want to run annual evaluation campaigns and track KPIs per employee, so that
  performance is documented over time.
- **HR-26**: As HR, I want to record bilingual (FR/AR) disciplinary files with hearing minutes, printable
  and signature-ready, so that the disciplinary process is properly documented.
- **HR-27**: As HR, I want disciplinary records restricted to HR only — no DG or employee access — so that
  sensitive personnel matters stay confidential.

### Emplois & Compétences
- **HR-28**: As HR, I want to write job descriptions distinct from recruitment offers, so that I have a
  durable reference independent of any one hiring cycle.
- **HR-29**: As HR, I want a skills catalogue by category reusable across job descriptions, so that I don't
  redefine the same skill repeatedly.

### Tâches, Réunions, Base de connaissances
- **HR-30**: As HR, I want a Kanban/list/calendar task view with subtasks, comments, and attachments, so
  that I can organize my own and my team's work.
- **HR-31**: As HR, I want to type or upload a meeting's minutes (PV) directly and have the AI assistant
  generate a structured summary (decisions, action items) from that text, so that I don't write the
  summary by hand.
- **HR-32**: As HR, I want a searchable internal knowledge base/wiki, so that procedures and decisions
  aren't lost.
- **HR-33**: As HR, I want Tâches to stay entirely private to HR — no DG or employee access — so that
  internal work planning doesn't leak into other roles' views.

### Documents
- **HR-34**: As HR, I want a centralized document library with configurable categories and keyword search,
  so that I can find any company document quickly.

### Assistant IA
- **HR-35**: As HR, I want an AI assistant that answers from real ARIHA AI data and cites its sources, so
  that I can trust its answers instead of double-checking everything by hand.
- **HR-36**: As HR, I want the assistant to draft things like job descriptions, contracts, and candidate
  emails — always clearly marked as drafts — so that I have a starting point instead of a blank page, while
  staying responsible for the final version.
- **HR-37**: As HR, I want any write action the assistant proposes (creating a task, logging a leave,
  hiring a candidate) to require my explicit confirmation before it executes, so that nothing happens
  without my sign-off.

### Notifications
- **HR-38**: As HR, I want a notification center surfacing everything HR-relevant (overdue tasks, upcoming
  probation deadlines, stalled candidacies, pending leave requests), so that nothing falls through the
  cracks.

### Paramètres
- **HR-39**: As HR, I want to configure reference data (departments, positions, leave types, document
  categories, etc.) myself without needing a developer, so that the app adapts as the organization changes.
- **HR-40**: As HR, I want to manage which employee holds the leave-responsable capability for each
  department (and toggle whether a department has one at all), so that leave-request routing matches how
  each team actually works.
- **HR-41**: As HR, I want changes to legally/financially sensitive reference data (like the SMIG) logged
  in the audit trail, so that I can see who changed a legal parameter and when.

### Cockpit
- **HR-42**: As HR, I want a cockpit dashboard aggregating actionable signals (overdue tasks, upcoming
  probation deadlines, stalled candidacies, pending approvals), so that I know what needs my attention
  today.
- **HR-43**: As HR, I want to open any department's team-level cockpit view (the former "Manager Cockpit"),
  so that I can check on a specific team's status without a separate manager login existing.

## Direction Générale (DG)

- **DG-01**: As the DG, I want read-only access to full employee detail — including salary, CIN, and
  disciplinary files — for every employee, so that I have complete visibility without asking HR for each
  figure.
- **DG-02**: As the DG, I want a read-only executive cockpit (headcount, masse salariale, absenteeism rate,
  open recruitments), so that I can see the company's HR situation at a glance.
- **DG-03**: As the DG, I want read-only access to recruitment, attendance/leave, variable pay, payroll,
  performance/discipline, and job descriptions, so that I stay informed across every HR area without
  becoming a bottleneck for HR's daily work.
- **DG-04**: As the DG, I want zero access to Tâches, so that HR's internal task planning stays a private
  working space.
- **DG-05**: As the DG, I want to never be required to click an approval inside the app (recruitment
  validation, probation decisions), so that HR stays the accountable, single decision-executor while I can
  still weigh in through normal conversation.
- **DG-06**: As the DG, I want executive-relevant notifications only — not HR's full operational alert
  stream — so that I'm not overwhelmed by day-to-day noise.
- **DG-07**: As the DG, I want it visually obvious whenever I'm in a read-only view, so that I never
  mistake it for an editable screen.

## Employee (self-service)

- **EMP-01**: As an employee, I want a read-only recap of my own record (identity, contract, department,
  position), so that I can check my information is correct without asking HR.
- **EMP-02**: As an employee, I want to see my current leave balance, so that I know how many days I have
  left before requesting time off.
- **EMP-03**: As an employee, I want to submit my own leave request (in departments without a
  leave-responsable), so that I don't have to go through HR manually every time.
- **EMP-04**: As an employee in a department with a leave-responsable, I want that person able to submit a
  leave request on my behalf, so that the process matches how my team actually works day to day.
- **EMP-05**: As an employee, I want to be notified when my leave request is approved or rejected, so that
  I know the outcome without checking back manually.
- **EMP-06**: As an employee, I want to download a printable leave certificate once my request is approved,
  so that I have a formal document without waiting for HR to print and hand it to me.
- **EMP-07**: As an employee, I want to view and download my own past payslips, so that I don't have to ask
  HR for a copy every time I need one.
- **EMP-08**: As an employee, I want to see only my own data — never another employee's — anywhere in the
  app, so that my personal information stays private.
- **EMP-09** *(tentative — pending Ariha Froid's decision on the evaluation process, PRD §6.6)*: As an
  employee, I want to see my own performance evaluations and KPI results, so that I understand how my
  performance is being tracked. Not yet built — placeholder only, don't build ahead of that decision.

**Explicitly not a story**: an employee never sees or manages tasks in this app (PRD §5, §6.8) — no
"EMP-xx: view my tasks" exists on purpose. Same for profile-correction requests — dropped from scope.

## Leave-responsable (a capability, not a separate role)

- **RESP-01**: As a leave-responsable for my department, I want to submit a leave request on behalf of any
  employee in my department, so that I can handle it the way my team already works.
- **RESP-02**: As a leave-responsable, I want no other elevated capability beyond leave submission — no
  salary visibility, no task/KPI oversight — so that this narrow responsibility doesn't quietly turn into a
  full manager role.
- **RESP-03**: As a leave-responsable, I want my submitted requests to still require HR's approval before
  being granted, so that HR remains the final authority — my role is initiating the request, not approving
  it.

## Cross-cutting

Not tied to one role — properties the whole system must hold, from PRD §7 (Non-Functional Requirements).

- **XCUT-01**: As any user, I want the AI assistant's answers to respect my role's data-visibility rules,
  so that I never see through the assistant what I couldn't see through the normal UI (PRD §6.10).
- **XCUT-02**: As Ariha Froid, I want every write to sensitive data attributable to a real authenticated
  user — never a shared account — so that the audit trail is meaningful for compliance and dispute
  resolution.
- **XCUT-03**: As Ariha Froid, I want authentication and server-side authorization enforced on every
  action — not just hidden in the UI — so that a role's restrictions can't be bypassed by calling the API
  directly.
- **XCUT-04**: As Ariha Froid, I want regular, automated, tested backups, so that HR data can actually be
  recovered if something goes wrong — not just theoretically backed up.
