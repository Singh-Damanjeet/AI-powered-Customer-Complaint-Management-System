# AI-Powered Customer Complaint Management System

An AI-assisted customer complaint intake workspace for pharmaceutical API and
finished-dose-form (FDF) manufacturing. The project extracts source-grounded
facts, reassesses preliminary risk after every change, provides QA-oriented
insights, and keeps an append-only history when a complaint is explicitly
saved.

This is a no-Docker assignment/demo project. PostgreSQL is supplied through a
managed provider such as Neon/Supabase or a locally installed PostgreSQL
server.

## Overview

The application is designed around one important control: the complaint form
is read-only. Complaint facts can only be created or modified through the AI
Copilot or document extraction workflow. A user must explicitly click Save
Complaint before anything is persisted.

## Core Capabilities

- Log Complaint Tool for natural-language complaint intake.
- Edit Complaint Tool for sparse, source-grounded natural-language updates.
- Document Extraction Tool for PDF, DOCX, TXT, and EML intake.
- Preliminary AI risk assessment with mandatory QA review.
- Read-only AI-controlled complaint form with explicit user save control.
- Persisted complaint history, assessment snapshots, and audit trail.

## Optional AI Features

- Completeness scoring and explainable possible-duplicate detection.
- Complaint summary, potential investigation areas, and proposed CAPA actions.

## Demo Flow

1. Enter the complaint narrative in the AI Copilot.
2. Let AI populate the read-only complaint form.
3. Review the preliminary AI risk assessment.
4. Modify selected fields using natural language.
5. Upload a PDF or email document and review the extracted complaint.
6. Review completeness, duplicate, summary, investigation, and CAPA insights.
7. Explicitly save the complaint and review its audit history.

The exact prompts and timed recording sequence are in
`docs/recording/demo-prompts.md` and
`docs/recording/demo-video-script.md`.

## Design Decisions

- Patch-based editing preserves unrelated complaint values when an edit omits
  them.
- Structured LLM outputs are validated with typed Pydantic contracts before
  entering application state.
- LangGraph makes the log, edit, document, validation, risk, insights, and
  response steps explicit.
- Deterministic risk signals provide guardrails while the LLM supplies
  contextual preliminary reasoning.
- Risk classifications, investigation areas, and CAPA actions are explicitly
  subject to human QA review.

## Evaluator & Submission

- [Evaluator quickstart](docs/evaluator-quickstart.md)
- [Final handoff](docs/handoff.md)
- [Final submission template](docs/final-submission.md)
- [Requirement mapping](docs/requirement-mapping.md)
- [Working demo recording package](docs/recording/)

## Assignment Requirements

The mandatory AI capabilities are implemented as separate workflow tools:

1. `LogComplaintTool` extracts factual fields into `ComplaintData`.
2. `EditComplaintTool` returns a sparse `ComplaintPatch`; omitted fields are
   never used to erase existing state.
3. `DocumentExtractionTool` reuses the same factual extraction contract after
   the uploaded document has been parsed.

Every log, edit, or document extraction request runs risk assessment again.
Unknown factual information remains `null`; risk classification and proposed
actions may be inferred only as preliminary AI recommendations.

## Features

- Read-only AI-controlled complaint record with highlighted changed fields.
- AI Copilot for log and edit messages.
- In-memory document upload for PDF, DOCX, TXT, and EML files.
- Negation-aware pharmaceutical risk signals, including adverse-event signals.
- Risk severity and priority cards with QA disclaimer.
- Deterministic completeness score from 0–100.
- Explainable `Possible Duplicate` matches against saved complaints.
- Concise factual summary, potential investigation areas, and three CAPA
  recommendation sections.
- Transactional save of the complaint, risk snapshot, and audit events.
- Persisted complaint history and assessment history endpoints.
- Friendly handling for unavailable AI, invalid model output, bad files, and
  database failures.

## Architecture

```mermaid
flowchart TD
    UI[React + Redux Toolkit] --> API[FastAPI]
    API --> GRAPH[LangGraph]
    GRAPH --> LOG[Log Complaint Tool]
    GRAPH --> EDIT[Edit Complaint Tool]
    GRAPH --> DOC[Document Extraction Tool]
    LOG --> RISK[Risk Assessment]
    EDIT --> RISK
    DOC --> RISK
    RISK --> INSIGHTS[Completeness + Optional AI Insights]
    INSIGHTS --> GROQ[Groq structured output]
    API --> DB[(PostgreSQL via SQLAlchemy)]
```

The graph owns request orchestration. Groq calls are made only through the
reusable `GroqService` and its async adapter; business logic does not call the
Groq SDK directly. SQLAlchemy models are separate from the Pydantic API
contracts, and Alembic owns database schema creation.

## Mandatory AI Tools

### Log Complaint Tool

`backend/app/agents/tools/log_complaint.py` and
`backend/app/services/complaint_extraction_service.py` extract only facts
explicitly present in the narrative. The workflow then validates the
complaint and runs `RiskService` without saving.

### Edit Complaint Tool

`backend/app/agents/tools/edit_complaint.py` returns only explicitly requested
fields as `ComplaintPatch`. `backend/app/services/complaint_merge_service.py`
applies `exclude_unset=True`, so omitted fields remain unchanged and explicit
`null` is reserved for a clear request.

### Document Extraction Tool

`backend/app/services/document_parser.py` parses supported files in memory.
`backend/app/agents/tools/document_extraction.py` sends the normalized text to
the shared factual extraction service. Scanned PDFs are reported as requiring
OCR; production OCR is outside this assignment.

## LangGraph Workflow

```text
START
  ↓
classify_intent
  ├── LOG       → log_complaint
  ├── EDIT      → edit_complaint
  └── DOCUMENT  → extract_document → extract_complaint_from_document
                         ↓
                    validate_complaint
                         ↓
                    assess_risk
                         ↓
                    generate_insights
                         ↓
                    generate_response
                         ↓
                        END
```

Unrelated messages and unsupported requests terminate with a safe response.
The API routes call `ComplaintGraphService`, which invokes the compiled graph
for log, edit, and document operations.

## Tech Stack

- React and Vite
- Redux Toolkit and React Redux
- Axios
- Python FastAPI and Uvicorn
- LangGraph
- Groq Python SDK
- PostgreSQL
- SQLAlchemy 2 and Alembic
- Pydantic v2 / pydantic-settings
- PyMuPDF, python-docx, and Python standard-library email parsing
- Google Inter font

## Quick Start

Prerequisites:

- Node.js 20 or newer and npm.
- Python 3.11 or newer.
- PostgreSQL 14 or newer, locally installed or provided by a managed service.

Create the backend environment and install dependencies:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
pip install -r backend/requirements.txt
```

Create the environment files and fill in the database and Groq settings in the
root `.env`:

```bash
cp .env.example .env
cp frontend/.env.example frontend/.env
```

Run the backend in one terminal:

```bash
source .venv/bin/activate
cd backend
alembic upgrade head
uvicorn app.main:app --reload
```

Run the frontend in a second terminal:

```bash
cd frontend
npm install
npm run dev
```

No Docker configuration is required or included.

## Environment Variables

`.env.example` contains the backend/database template and
`frontend/.env.example` contains the Vite API URL template. Never commit either
resulting `.env` file or real credentials.

```ini
DATABASE_URL=postgresql+psycopg://USER:PASSWORD@HOST:5432/DATABASE_NAME
GROQ_API_KEY=
GROQ_MODEL=
FRONTEND_ORIGIN=http://localhost:5173
VITE_API_BASE_URL=http://localhost:8000
APP_VERSION=1.0.0
```

For a managed PostgreSQL provider that requires TLS, append
`?sslmode=require` to `DATABASE_URL`. `VITE_API_BASE_URL` should point to the
deployed backend origin when frontend and backend are hosted separately; the
frontend client appends `/api` and also accepts a value that already ends in
`/api`. A same-origin deployment can omit it and use the frontend's `/api`
fallback.

## Database Setup

With PostgreSQL available and `DATABASE_URL` configured:

```bash
cd backend
alembic upgrade head
```

The migration creates `complaints`, `ai_assessments`, and
`complaint_audit_logs`. The application verifies connectivity through
`GET /api/health`, which executes `SELECT 1` and does not call Groq.
The health response also exposes the configured release version without
returning any secret values:

```json
{"status":"ok","database":"connected","version":"1.0.0"}
```

## Running Backend

From the repository root, after activating `.venv`:

```bash
cd backend
uvicorn app.main:app --reload
```

FastAPI is available at `http://localhost:8000`. Swagger documentation is at
`http://localhost:8000/docs`.

## Running Frontend

In a second terminal:

```bash
cd frontend
npm run dev
```

Vite serves the workspace at `http://localhost:5173`.

## Deployment

The application is provider-neutral and does not require Docker. Host the
frontend as a static Vite site and the backend on a Python web service, using a
managed PostgreSQL provider for the database.

Frontend build settings:

```bash
cd frontend
npm ci
npm run build
```

Publish `frontend/dist` and set `VITE_API_BASE_URL` to the deployed backend API
base URL, for example `https://api.example.com/api`. Do not place that value in
source code.

Backend settings and start command:

```bash
cd backend
pip install -r requirements.txt
alembic upgrade head
uvicorn app.main:app --host 0.0.0.0 --port "${PORT:-8000}"
```

Set these backend environment variables in the hosting provider:

```ini
DATABASE_URL=postgresql+psycopg://<managed-user>:<managed-password>@<managed-host>/<database>
GROQ_API_KEY=<provider-secret>
GROQ_MODEL=<configured-model>
FRONTEND_ORIGIN=https://<deployed-frontend-host>
```

`FRONTEND_ORIGIN` accepts a comma-separated list when more than one deployed
frontend origin is required. The deployment health check is
`GET /api/health`; it verifies PostgreSQL with `SELECT 1` and never calls Groq.
Document uploads are parsed from request bytes and do not require a persistent
local filesystem. No remote deployment or Git push is performed by this
repository phase.

No authentication is required for this assignment demo.

## Sample Workflow

Start with an empty workspace and send:

```text
ABC Pharma reported brown discoloration on approximately 120 Metformin 500 mg
tablets from batch MT24003. No adverse events have been reported.
```

Then try these AI-only edits:

```text
Actually change the batch number to MT24004 and quantity affected to 500.
Also one patient experienced severe vomiting after taking the product.
Remove the expiry date because the customer did not provide it.
```

The form remains read-only, unrelated fields are preserved, risk is reassessed
after each request, and audit events remain local until Save Complaint is
clicked. The primary fictional document demo is
`sample_documents/metformin_discoloration.pdf`; the other sample formats are
also available in that directory.

For duplicate detection, save the first Metformin complaint, reset the workspace,
and submit a second complaint for the same product and batch with slightly
different wording. The result is a `Possible Duplicate` review cue. Reset is
the documented clean-demo action; there is no database-reset button and no
automatic seed script.

## API Endpoints

| Method | Endpoint | Purpose |
| --- | --- | --- |
| GET | `/api/health` | Check API and database connectivity |
| POST | `/api/agent/message` | Log a complaint or edit supplied in-memory state |
| POST | `/api/agent/document` | Parse and extract an uploaded complaint document |
| POST | `/api/ai/log-complaint` | Backward-compatible log workflow endpoint |
| POST | `/api/complaints` | Explicitly save a complaint and related records |
| GET | `/api/complaints` | List saved complaints |
| GET | `/api/complaints/{id}` | Retrieve a complaint and latest assessment |
| GET | `/api/complaints/{id}/audit` | Retrieve chronological audit events |
| GET | `/api/complaints/{id}/assessments` | Retrieve assessment snapshots |

AI endpoints return an unsaved `ComplaintAgentResponse` containing
`complaint`, `risk_assessment`, `assistant_message`, `changed_fields`, and
optional `ai_insights`. AI endpoints never write to PostgreSQL.

## Testing

Backend tests use disposable SQLite databases for repository and transaction
coverage, while the production configuration remains PostgreSQL:

```bash
cd backend
../.venv/bin/pytest -q
```

Frontend tests and a production build:

```bash
cd frontend
npm test -- --run
npm run build
npm run lint
```

Backend lint uses the optional `backend/requirements-dev.txt` check tools:

```bash
cd backend
../.venv/bin/pip install -r requirements-dev.txt
../.venv/bin/ruff check app tests
```

The suite covers schemas, source grounding, negation, Groq failures, parser
errors, LangGraph routing, patch preservation, persistence transactions,
audit/history APIs, completeness, duplicate detection, optional insight
failures, frontend read-only behavior, upload, save, reset, and error-state
preservation.

## Limitations

- AI output is preliminary and requires QA review.
- This is not a validated production GxP system.
- There is no production OCR for scanned PDFs.
- There are no electronic signatures, full RBAC, or regulatory approval
  workflow.
- CAPA output is a recommendation panel, not a full CAPA management system.
- Sample documents and data are fictional and intended for assignment/demo use.

## AI Safety / QA Review Notes

- Factual fields are source-grounded and unknown values remain `null`.
- Structured Groq responses are validated with Pydantic before use.
- Deterministic risk signals supplement, but do not replace, AI assessment.
- Every complaint creation or AI edit runs risk reassessment.
- Potential investigation areas are hypotheses; the UI does not present a
  confirmed root cause.
- CAPA sections are labeled `AI recommendation — QA review required`.
- Possible duplicate detection is explainable and intentionally says
  `Possible Duplicate`, never `Confirmed Duplicate`.
- AI failures preserve the in-memory complaint; optional insight failures do
  not invalidate the mandatory complaint/risk response.
- The complaint form is intentionally read-only. Complaint data can only be
  created or modified using the AI Copilot or document extraction workflow,
  matching the assignment requirement.
