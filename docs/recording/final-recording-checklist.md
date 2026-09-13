# Final Recording Checklist

This checklist is for the final human-recorded submission videos. The
repository does not generate or fabricate video files.

## Required file names

- `pharma-complaint-working-demo.mp4`
- `pharma-complaint-code-walkthrough.mp4`

## Working demo video

- [ ] Introduce the project and pharmaceutical API/FDF complaint context.
- [ ] Show that the complaint form is read-only before any AI action.
- [ ] Demonstrate the Log Complaint Tool with a natural-language complaint.
- [ ] Show the populated complaint state and AI risk assessment.
- [ ] Demonstrate an Edit Complaint Tool update.
- [ ] Show that unrelated complaint fields are preserved after the edit.
- [ ] Demonstrate a risk-changing edit and the new risk reassessment.
- [ ] Upload and extract a supported PDF or email document.
- [ ] Demonstrate a document-based edit or merge.
- [ ] Show completeness and duplicate insights.
- [ ] Show summary, potential investigation areas, and CAPA recommendations.
- [ ] Save the complaint and show its complaint number.
- [ ] Show complaint history, assessment history, and audit trail.
- [ ] Reset the workspace and demonstrate a clear recovery path for an
  unavailable-AI or invalid-file response.
- [ ] Keep the video between five and ten minutes.
- [ ] Ensure no API keys, database credentials, private URLs, or local secrets
  are visible.

## Technical code walkthrough video

- [ ] Show the frontend Copilot, read-only complaint form, document upload,
  insights, save, history, and audit components.
- [ ] Show Redux state and the API service boundary.
- [ ] Show the FastAPI routes and typed Pydantic contracts.
- [ ] Show LangGraph intent routing and workflow nodes.
- [ ] Show the Log Complaint Tool and factual extraction contract.
- [ ] Show the Edit Complaint Tool and sparse patch merge behavior.
- [ ] Show the Document Extraction Tool and supported parsers.
- [ ] Show `GroqService` as the only Groq SDK boundary.
- [ ] Show deterministic risk signals and AI risk assessment persistence.
- [ ] Show SQLAlchemy models, Alembic migrations, and repository services.
- [ ] Show audit logging and the explicit save boundary.
- [ ] Explain the complete input-to-output flow in order.
- [ ] Ensure no API keys, database credentials, private URLs, or local secrets
  are visible.

## Recording preflight

- [ ] Configure a working PostgreSQL `DATABASE_URL`.
- [ ] Configure `GROQ_API_KEY` and `GROQ_MODEL`.
- [ ] Run `alembic upgrade head`.
- [ ] Start the backend with `uvicorn app.main:app --reload`.
- [ ] Start the frontend with `npm run dev`.
- [ ] Confirm `GET /api/health` reports `status: ok` and
  `database: connected`.
- [ ] Use the exact prompts in `docs/recording/demo-prompts.md`.
- [ ] Watch both completed videos once before uploading them.
