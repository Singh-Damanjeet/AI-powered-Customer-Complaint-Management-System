# Final Release Summary

Version: `1.0.0`

## Mandatory features

- Log Complaint Tool for natural-language complaint creation.
- Edit Complaint Tool for sparse natural-language updates that preserve
  unrelated complaint fields.
- Document Extraction Tool for source-grounded complaint intake.
- AI risk assessment after every complaint creation or modification.
- Read-only complaint form with AI Copilot and document upload as the only
  complaint input paths.

## Bonus features

- Completeness checker.
- Possible duplicate detection.
- Complaint summary.
- Potential investigation areas.
- CAPA recommendations.
- Append-only audit trail and persisted assessment history.

## Supported documents

- PDF
- DOCX
- TXT
- EML

## Technology stack

- React
- Redux Toolkit
- FastAPI
- LangGraph
- Groq
- PostgreSQL
- SQLAlchemy
- Alembic
- Google Inter font

## Release verification

The automated backend and frontend quality gates pass, including tests, lint,
build, dependency checks, and offline persistence smoke checks. A positive
live AI workflow requires the evaluator’s `GROQ_API_KEY` and `GROQ_MODEL`; a
live PostgreSQL verification requires a configured `DATABASE_URL`.
