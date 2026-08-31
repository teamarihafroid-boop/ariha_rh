# ARIHA AI — AI Usage Specification

**Status:** Draft v1 — for review
**Companion docs:** `PRD.md` §6.10 (product requirements for the assistant), `TECHNICAL_DECISIONS.md` §5
(direct/global cloud AI API — decided, not self-hosted, not EU-restricted), `USER_STORIES.md` (HR-35 to
HR-37, XCUT-01).

This document exists to answer one question precisely: **where does AI actually touch this app, what
does each touchpoint do, and what data does it see?** Useful on its own, and specifically needed to reason
about the AI hosting decision — see §7 for what's decided and what's still open.

## 1. What "AI" means in this app

In the prototype, one model did all of it: `llama3.2:3b` via Ollama, running locally, plus
`nomic-embed-text` for embeddings. For production, this moves to a **direct/global cloud AI API** (e.g.
the Anthropic API or OpenAI API, called directly) — not self-hosted, and not restricted to an EU-region
deployment. There is still no separate model per feature — every capability below is the same underlying
model, called with a different prompt/context for a different purpose — so switching providers stays one
integration point (`ai_service.py`), not five.

## 2. The AI-touching capabilities

### 2.1 Conversational assistant (RAG Q&A)
- **What it does:** answers a free-text question by retrieving relevant chunks from the app's own data
  (FAISS index, see §4) and generating an answer grounded in those chunks — with sources always cited.
- **Triggered by:** a user typing a question into the assistant chat.
- **Data it touches:** whatever the retrieval layer surfaces — potentially anything indexed (§4), which as
  of today is not filtered by who's asking. See §6 — this is the single biggest privacy consideration.
- **Safeguard:** never presents invented data as fact; if the answer isn't grounded in retrieved data, it
  says so rather than guessing.
- **Status:** carried over from the prototype as-is.

### 2.2 Direct command recognition & confirmed actions
- **What it does:** recognizes specific commands inside the chat ("créer une tâche pour…", "candidats de
  Casablanca", log a leave entry, draft a job offer, hire a candidate) and prepares the corresponding
  action.
- **Triggered by:** a recognized command pattern in the chat input (rule-based first pass, LLM router as
  fallback per the prototype's `_try_intent` / `_llm_route_action`).
- **Data it touches:** whatever the specific action needs (e.g., employee/candidate records to hire
  someone).
- **Safeguard — the load-bearing one:** **no write action ever executes without explicit human
  confirmation.** The assistant proposes; the user approves; only then does `execute_confirmed_action` run.
  This is non-negotiable and must survive the production rebuild unchanged (PRD §6.10, HR-37).
- **Status:** carried over from the prototype as-is.

### 2.3 Meeting summary generation
- **What it does:** reads a meeting's PV (procès-verbal / minutes — now typed or uploaded as text, not
  transcribed from audio, per the decision in PRD §6.8) and generates a structured summary: key decisions,
  action items.
- **Triggered by:** HR marking a meeting's PV as ready for summarization.
- **Data it touches:** the PV text itself — whatever was discussed in that meeting, which could include
  sensitive personnel topics depending on the meeting.
- **Safeguard:** the generated summary is a starting point HR reviews, not an auto-published record.
- **Status:** changed — used to run on a Faster-Whisper transcript; now runs on the PV text directly.
  Same generation step, simpler input pipeline (no audio, no transcription job).

### 2.4 Drafting (job descriptions, contracts, candidate emails)
- **What it does:** generates a first draft of a document from a prompt (e.g., "rédige une fiche de poste
  pour un technicien frigoriste") — always explicitly marked as a draft in the UI, never presented as
  final.
- **Triggered by:** HR requesting a draft via the assistant.
- **Data it touches:** whatever context is relevant to the draft (job description templates, the
  candidate's profile for an email, an employee's contract fields for a contract draft).
- **Safeguard:** the "draft" marking must never be removed, even if the output looks good — this is a
  CLAUDE.md-level principle (`ia-locale-rag-transcription` skill) carried into production.
- **Status:** carried over from the prototype as-is.

### 2.5 Inbox classification
- **What it does:** when a file or text is dropped into the universal "Ajouter quelque chose" inbox,
  detects what kind of thing it is (a CV, a generic document, something else) and proposes an action (e.g.,
  "on dirait un CV — créer un candidat ?").
- **Triggered by:** any file/text drop into the inbox.
- **Data it touches:** the dropped file's extracted text/content.
- **Safeguard:** proposes, doesn't act — the resulting `InboxItem` still needs explicit validation before
  it becomes a real record (candidate, document, etc.), same confirmation principle as §2.2.
- **Status:** carried over from the prototype as-is.

## 3. What is *not* AI in this app (boundary cases worth being precise about)

Not everything that looks automated is an LLM call. Getting this distinction right matters directly for
the hosting decision — these do **not** move if AI hosting changes, so they're out of scope for that
decision entirely:

- **CV field extraction** (`cv_extraction_service.py`) — heuristic PDF/DOCX text and field extraction
  (name, city, sections) via PyMuPDF/python-docx, explicitly documented in the prototype as "not
  definitive." This is pattern-based extraction, not a model call.
- **Employee 360° synthesis and DG cockpit synthesis** (`employee_synthesis_service.py`,
  `dg_cockpit_service.py`) — described in the prototype as generating narrative summary text. **Unverified
  which of these is template-based string assembly vs. an actual LLM call** — worth confirming directly
  against the prototype's source before the rebuild, since if either does call the LLM, it belongs in §2
  and inherits the same guardrails (grounded-only, no invented figures).

## 4. The retrieval layer underneath §2.1 and §2.2

- **Embeddings:** in the prototype, `nomic-embed-text` run locally via Ollama. In production, generated via
  the same direct/global cloud API as generation (§7), not self-hosted.
- **Index:** FAISS, rebuilt on demand (`/api/assistant/reindex`) or presumably on a schedule in production
  (confirm cadence — not specified in the prototype). The index itself still lives on the server; only the
  embedding calls that build it leave the server.
- **What's indexed:** described in the prototype as "the app's own data" — this needs a precise inventory
  before production (which models/tables get embedded, at what granularity) since it directly determines
  what the assistant *can* surface in an answer, and therefore what §6's privacy analysis actually covers.

## 5. Guardrails that apply across every capability above

These are not per-feature — they're invariants the whole AI layer must hold, carried from
`CLAUDE.md` / the `ia-locale-rag-transcription` skill into production requirements:

1. **No write action without explicit human confirmation** (§2.2) — never automate a database write from
   an AI suggestion alone.
2. **Sources always cited** (§2.1) — an answer without a traceable source is a red flag, not a feature.
3. **Drafts always marked as drafts** (§2.4) — never silently promoted to "final."
4. **Never invent legal or financial data** — SMIG, CNSS rates, indemnity thresholds must come from real
   parameters (`AppParameter`) or real documents, never generated (`conformite-paie-droit-travail-maroc`
   skill's principle, applies here too).
5. **Retrieval must respect role-based visibility (new requirement, not yet built)** — see §6. The
   prototype has no auth, so this guardrail doesn't exist yet in any form; it becomes load-bearing the
   moment RBAC ships (PRD §5, USER_STORIES.md XCUT-01).

## 6. Data touched by AI — the privacy surface

Because §2.1's retrieval currently has no visibility filtering, **the honest current answer is "potentially
anything indexed."** Once RBAC ships, retrieval must be scoped per the asking user's role — concretely:

- An **Employee** asking the assistant a question must never receive another employee's salary, CIN, or
  disciplinary content in an answer, even if that data is technically in the index.
- **DG** asking about Tâches must get nothing back — DG has zero access to that module (PRD §5), and the
  assistant is not a backdoor around that.
- **HR** is the only role for which "potentially anything indexed" is actually the intended behavior.

This is real, non-trivial engineering work — not a config flag — and should be scoped as its own
deliverable in the production build, not an afterthought bolted onto the RAG pipeline after the fact.

## 7. Where does the model run? Decided: direct/global cloud API

Resolved (PRD §8, `TECHNICAL_DECISIONS.md` §5): the prototype's self-hosted setup (Ollama, running
locally) is **not** carried into production. Generation and embeddings both run against a **direct/global
cloud AI API** (e.g. the Anthropic API or OpenAI API, called directly rather than through an EU-region
managed offering like AWS Bedrock or Google Vertex AI EU), which also removes the fixed infrastructure
cost of running a model-serving service continuously — pay-per-use instead.

- **Why global over EU-restricted:** an EU-region-only deployment (Bedrock/Vertex AI EU) would have been
  compliant with Loi 09-08 by construction, with no extra authorization step. Ariha Froid chose the
  direct/global option instead, for provider simplicity and access to the provider's latest models, and
  is accepting the compliance step this adds.
- **Compliance consequence:** because the provider processes data outside the countries Loi 09-08 treats
  as having "adequate" protection (EU, Switzerland, Canada), this transfer requires **prior CNDP
  authorization and safeguards (standard contractual clauses) before launch** — not optional, and this is
  a separate requirement from wherever the app itself is hosted (e.g. Railway EU, `TECHNICAL_DECISIONS.md`
  §8).
- **Still open:** the exact provider (Anthropic vs. OpenAI vs. another global option) and formalizing a
  data processing agreement with whichever is chosen. See `ariha-legal-loi0908` — things still need
  confirming directly with Ariha Froid / a Moroccan lawyer / cndp.ma before launch: (a) that sending HR
  data to a third-party API provider outside Morocco is acceptable to Ariha Froid, (b) completing the CNDP
  authorization this transfer requires, and (c) whether Ariha Froid already holds a separate CNDP
  declaration/authorization for processing this employee data at all — required under Loi 09-08
  independent of hosting location.

This changes the *implementation* of §2.1–§2.5 and §4, not their existence — the five capabilities in §2
stay the product regardless of which specific provider runs them.
