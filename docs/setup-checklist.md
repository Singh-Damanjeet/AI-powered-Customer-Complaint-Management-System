# Clean-Machine Setup Checklist

This project uses no Docker. Confirm that PostgreSQL is available through a
managed provider or a locally installed server before starting.

## Backend

From the repository root:

```bash
python3 --version
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
pip install -r backend/requirements-dev.txt
cp .env.example .env
cp frontend/.env.example frontend/.env
```

Edit `.env` and set:

```ini
DATABASE_URL=postgresql+psycopg://USER:PASSWORD@HOST:5432/DATABASE_NAME
GROQ_API_KEY=your-key
GROQ_MODEL=your-configured-model
FRONTEND_ORIGIN=http://localhost:5173
APP_VERSION=1.0.0
```

Then migrate and start FastAPI:

```bash
cd backend
alembic upgrade head
uvicorn app.main:app --reload
```

Verify the database-backed health check:

```bash
curl http://localhost:8000/api/health
```

Expected response:

```json
{"status":"ok","database":"connected","version":"1.0.0"}
```

## Frontend

In a second terminal from the repository root:

```bash
cd frontend
npm install
npm run dev
```

Open `http://localhost:5173`. The checked-in frontend template uses the backend
origin `http://localhost:8000`; the API client appends `/api`. For a deployed
backend, update `frontend/.env` with:

```ini
VITE_API_BASE_URL=http://localhost:8000
```

## Verification commands

```bash
cd backend
../.venv/bin/pytest -q
../.venv/bin/ruff check app tests
cd ../frontend
npm test -- --run
npm run lint
npm run build
```

Use `http://localhost:8000/docs` for the FastAPI Swagger walkthrough. Keep
`.env` private and do not add Docker files or real customer data.
