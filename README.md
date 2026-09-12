# Pharma Complaint AI

Foundation for an AI-powered customer complaint management system for pharmaceutical API/FDF manufacturing.

This repository currently contains the no-Docker Phase 0 foundation, Phase 1 domain contracts, Phase 2 persistence/API layer, Phase 3 Groq structured-output service, the Phase 4 in-memory log complaint/risk-assessment workflow, the Phase 5 LangGraph orchestration layer, and the Phase 6 in-memory natural-language edit workflow. Document extraction is not implemented yet.

## Architecture

```text
pharma-complaint-ai/
├── frontend/
├── backend/
├── sample_documents/
├── .env.example
├── .gitignore
└── README.md
```

## Prerequisites

- Node.js 20 or newer and npm
- Python 3.11 or newer
- PostgreSQL 14 or newer installed locally, or a managed PostgreSQL database from a provider such as Neon or Supabase

## Local setup

1. Copy the environment template:

   ```bash
   cp .env.example .env
   ```

   Set `DATABASE_URL` to your managed-provider or local PostgreSQL connection string. Use the `psycopg` SQLAlchemy driver prefix, for example:

   ```ini
   DATABASE_URL=postgresql+psycopg://USER:PASSWORD@HOST:5432/DATABASE_NAME
   ```

   For managed providers that require TLS, append `?sslmode=require` to the URL. Configure `GROQ_API_KEY` and `GROQ_MODEL` when using the Phase 3 service; never commit the resulting `.env` file.

2. Install backend dependencies, run migrations, and start FastAPI:

   ```bash
   python3 -m venv .venv
   source .venv/bin/activate
   pip install -r backend/requirements.txt
   cd backend
   alembic upgrade head
   uvicorn app.main:app --reload
   ```

   The API is available at `http://localhost:8000`.

3. Install frontend dependencies and start Vite in a second terminal:

   ```bash
   cd frontend
   npm install
   npm run dev
   ```

   The frontend is available at `http://localhost:5173`.

## Foundation endpoint

```http
GET http://localhost:8000/api/health
```

Response:

```json
{
  "status": "ok",
  "database": "connected"
}
```

The health check executes `SELECT 1` against `DATABASE_URL`. If the database is not configured or unavailable, it returns HTTP 503.

## Phase 0 scope

- React/Vite frontend shell with Redux Toolkit, React Redux, Axios, and Google Inter font loading.
- FastAPI application with environment-based settings and local-development CORS.
- SQLAlchemy session foundation and Alembic configuration.
- Managed or locally installed PostgreSQL connection through `DATABASE_URL`.
- Database-backed health check at `/api/health`.
- LangGraph and Groq SDK dependencies available for the structured AI service and later workflows.

## Phase 1 scope

- Typed Pydantic complaint, patch, risk assessment, and agent response contracts.
- Nullable factual complaint fields for unknown information.
- Patch serialization that excludes omitted fields from natural-language updates.
- Validation tests for supported values, malformed risk classifications, and patch semantics.

At the end of Phase 1, no AI calls, document extraction, risk reassessment execution, or manual complaint form had been added.

## Phase 2 scope

- SQLAlchemy models and Alembic migration for complaints, AI assessment snapshots, and audit logs.
- PostgreSQL JSONB storage for recommended actions.
- Complaint creation and read/list endpoints under `/api/complaints`.
- Atomic persistence of a complaint, initial not-assessed snapshot, and creation audit event.
- Repository/service tests covering reload from a new database session.

The initial assessment uses `Unknown` classifications and `not_assessed` as its model name until a later phase adds AI invocation.

## Phase 3 scope

- Environment-backed, dependency-injected Groq service for JSON Schema responses.
- Pydantic validation of every structured response returned by Groq.
- Provider, configuration, empty-response, JSON, and schema-validation error handling.
- The existing complaint APIs, migrations, and persistence behavior remain unchanged.
- Complaint edit/document tools are reserved for later phases.

## Phase 4 scope

- Factual natural-language extraction into validated `ComplaintData`.
- Safe complaint-type, strength, and quantity-unit normalization.
- Source-grounding that clears unsupported factual values to `null`.
- Deterministic pharmaceutical risk-signal detection with basic negation handling.
- Groq-backed preliminary `RiskAssessment` with mandatory QA review.
- Unsaved `POST /api/ai/log-complaint` endpoint returning `ComplaintAgentResponse`.
- No automatic PostgreSQL persistence, editing, or document parsing.

## Phase 5 scope

- Typed, serializable `ComplaintGraphState` for in-request LangGraph execution.
- Deterministic intent routing for log, edit, document, and unknown requests.
- Compiled log workflow: intent classification, factual extraction, Pydantic validation, risk assessment, and safe response generation.
- Existing Phase 4 extraction and risk services remain the source of AI business logic.
- Clean placeholder responses and error handling for unsupported future branches.
- `POST /api/ai/log-complaint` now executes through LangGraph and still returns an unsaved `ComplaintAgentResponse`.
- No automatic PostgreSQL persistence or document parsing.

## Phase 6 scope

- Source-grounded `EditComplaintTool` that returns only a sparse `ComplaintPatch`.
- Safe patch merging that preserves omitted fields and supports explicit `null` clears.
- Description additions preserve existing complaint context; explicit replacements replace it.
- LangGraph edit path converging on validation, mandatory risk reassessment, and response generation.
- `POST /api/agent/message` supports both new complaint logging and edits with caller-supplied current state.
- No automatic PostgreSQL persistence, document extraction, or frontend AI integration.

Docker is not required or included in this repository. There is no `docker-compose.yml` or `Dockerfile`.
