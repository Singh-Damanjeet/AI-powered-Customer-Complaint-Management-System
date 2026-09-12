# Pharma Complaint AI

Foundation for an AI-powered customer complaint management system for pharmaceutical API/FDF manufacturing.

This repository currently contains the Phase 0 foundation and Phase 1 domain contracts. AI calls and complaint workflows are intentionally not implemented yet.

## Architecture

```text
pharma-complaint-ai/
├── frontend/
├── backend/
├── sample_documents/
├── docker-compose.yml
├── .gitignore
├── .env.example
└── README.md
```

## Prerequisites

- Node.js 20 or newer and npm
- Python 3.11 or newer
- Docker with Docker Compose

## Local setup

1. Copy the environment template and set a local PostgreSQL password:

   ```bash
   cp .env.example .env
   ```

   Set `POSTGRES_PASSWORD` in `.env`. Once PostgreSQL is running, set `DATABASE_URL` to the matching SQLAlchemy URL, for example:

   ```ini
   DATABASE_URL=postgresql+psycopg://postgres:your-password@localhost:5432/pharma_complaint_ai
   ```

2. Start PostgreSQL:

   ```bash
   docker compose up -d postgres
   ```

3. Install backend dependencies and start FastAPI:

   ```bash
   python3 -m venv .venv
   source .venv/bin/activate
   pip install -r backend/requirements.txt
   cd backend
   alembic upgrade head
   uvicorn app.main:app --reload
   ```

   The API is available at `http://localhost:8000`.

4. Install frontend dependencies and start Vite in a second terminal:

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
  "status": "ok"
}
```

## Phase 0 scope

- React/Vite frontend shell with Redux Toolkit, React Redux, Axios, and Google Inter font loading.
- FastAPI application with environment-based settings and local-development CORS.
- SQLAlchemy session foundation and Alembic configuration.
- PostgreSQL Docker Compose service.
- LangGraph and Groq SDK dependencies ready for a later phase.

## Phase 1 scope

- Typed Pydantic complaint, patch, risk assessment, and agent response contracts.
- Nullable factual complaint fields for unknown information.
- Patch serialization that excludes omitted fields from natural-language updates.
- Validation tests for supported values, malformed risk classifications, and patch semantics.

No AI calls, complaint creation/editing endpoints, document extraction, database persistence, risk reassessment execution, or manual complaint form has been added.
