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
pip install -r backend/requirements.txt
cp .env.example .env
```

Edit `.env` and set:

```ini
DATABASE_URL=postgresql+psycopg://USER:PASSWORD@HOST:5432/DATABASE_NAME
GROQ_API_KEY=your-key
GROQ_MODEL=your-configured-model
FRONTEND_ORIGIN=http://localhost:5173
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
{"status":"ok","database":"connected"}
```

## Frontend

In a second terminal from the repository root:

```bash
cd frontend
npm install
npm run dev
```

Open `http://localhost:5173`. The default API base URL is
`http://localhost:8000/api`; to override it, create `frontend/.env` with:

```ini
VITE_API_BASE_URL=http://localhost:8000/api
```

## Verification commands

```bash
cd backend
../.venv/bin/pytest -q
cd ../frontend
npm test -- --run
npm run build
```

Use `http://localhost:8000/docs` for the FastAPI Swagger walkthrough. Keep
`.env` private and do not add Docker files or real customer data.

