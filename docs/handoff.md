# Final Handoff

## PROJECT

AI-Powered Customer Complaint Management System

## VERSION

1.0.0

## STACK

- React
- Redux Toolkit
- FastAPI
- LangGraph
- Groq
- PostgreSQL
- SQLAlchemy + Alembic
- Google Inter font

## RUN BACKEND

From the repository root on a clean machine:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
pip install -r backend/requirements.txt
cp .env.example .env
cp frontend/.env.example frontend/.env
```

Set `DATABASE_URL`, `GROQ_API_KEY`, and `GROQ_MODEL` in the root `.env` before
starting the application. `FRONTEND_ORIGIN` defaults to
`http://localhost:5173`; `APP_VERSION` defaults to `1.0.0`.

From a backend terminal:

```bash
source .venv/bin/activate
cd backend
uvicorn app.main:app --reload
```

## RUN FRONTEND

From a second terminal:

```bash
cd frontend
npm install
npm run dev
```

Open `http://localhost:5173`.

## RUN MIGRATIONS

With PostgreSQL reachable through `DATABASE_URL`:

```bash
cd backend
alembic upgrade head
```

Verify the connection without calling Groq:

```bash
curl http://localhost:8000/api/health
```

Expected shape:

```json
{"status":"ok","database":"connected","version":"1.0.0"}
```

## RUN TESTS

```bash
cd backend
pip install -r requirements-dev.txt
../.venv/bin/pytest -q
../.venv/bin/ruff check app tests
cd ../frontend
npm test -- --run
npm run lint
npm run build
```

## REQUIRED ENVIRONMENT VARIABLES

Backend root `.env`:

```ini
DATABASE_URL=
GROQ_API_KEY=
GROQ_MODEL=
FRONTEND_ORIGIN=http://localhost:5173
APP_VERSION=1.0.0
```

Frontend `frontend/.env`:

```ini
VITE_API_BASE_URL=http://localhost:8000
```

Never commit the resulting `.env` files or real credentials.

## PRIMARY DEMO PROMPT

```text
ABC Pharma reported brown discoloration on approximately 120 Metformin Hydrochloride 500 mg tablets from batch MT24003. The batch was manufactured on 18 July 2026 and expires on 30 June 2028. No adverse events have been reported.
```

## SAMPLE DOCUMENT

`sample_documents/metformin_discoloration.pdf`

Other supported samples are `foreign_material.docx`, `packaging_issue.txt`, and
`complaint_email.eml` in the same directory.

## KNOWN LIMITATIONS

- Groq and PostgreSQL credentials/provider access must be supplied by the
  evaluator; no live secrets are included.
- The AI risk result and optional insights are preliminary and require QA
  review.
- Scanned-PDF OCR, authentication/RBAC, electronic signatures, and formal GxP
  validation are outside this assignment.
- The application is intentionally not a Docker deployment.
