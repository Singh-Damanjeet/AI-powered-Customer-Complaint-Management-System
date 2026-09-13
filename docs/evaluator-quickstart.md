# Evaluator Quickstart

1. Ensure PostgreSQL and a Groq account are available, then create a Python
   environment and install the backend dependencies:

   ```bash
   python3 -m venv .venv
   source .venv/bin/activate
   pip install -r backend/requirements.txt
   ```

2. Install the frontend dependencies:

   ```bash
   cd frontend
   npm install
   cd ..
   ```

3. Copy `.env.example` to `.env`, copy `frontend/.env.example` to
   `frontend/.env`, and set `DATABASE_URL`, `GROQ_API_KEY`, and `GROQ_MODEL`.
4. Apply the schema:

   ```bash
   cd backend
   alembic upgrade head
   ```

5. Start the backend with `uvicorn app.main:app --reload`.
6. In a second terminal, run `cd frontend && npm run dev`.
7. Open `http://localhost:5173` and confirm `/api/health` is connected.
8. Paste the primary prompt from `docs/recording/demo-prompts.md` into the AI
   Copilot. The complaint form is intentionally read-only.
