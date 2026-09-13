# Technical Code Walkthrough Script

Target duration: 6–10 minutes. Planned run time: approximately 9 minutes.

Follow the file order below. Keep the browser demo and the code editor on the
same commit. Use [code-file-map.md](code-file-map.md) as the on-screen index;
do not open unrelated files.

## Opening — 0:00–0:25

State the request lifecycle:

```text
React + Redux → Axios → FastAPI → LangGraph → tools/services → Groq/PostgreSQL
```

The form is read-only, AI/document intake changes in-memory complaint state,
and persistence occurs only after an explicit save.

## Step 1 — Frontend input — 0:25–0:55

Show:

- `frontend/src/components/copilot/ChatInput.jsx`
- `frontend/src/components/complaint/ReadOnlyField.jsx`

Explain that the user types into the Copilot message textarea, while every
complaint input and textarea uses `readOnly` and `aria-readonly="true"`.

## Step 2 — Redux — 0:55–1:25

Show:

- `frontend/src/store/complaintSlice.js`
- `frontend/src/store/copilotSlice.js`
- `frontend/src/hooks/useComplaintWorkflow.js`

Say:

> Redux is the authoritative frontend state, so chat, document intake, the
> read-only form, risk assessment, insights, audit events, and save workflow all
> use the same complaint object.

Point out the async request orchestration and reset behavior in the hook.

## Step 3 — API service — 1:25–1:50

Show `frontend/src/services/api.js`.

Explain that `POST /api/agent/message` receives the Copilot message and current
complaint state. Document intake uses `POST /api/agent/document` with multipart
form data. Save uses `POST /api/complaints`.

## Step 4 — FastAPI route — 1:50–2:20

Show `backend/app/api/ai.py`.

Explain that the route validates request/file boundaries, maps parser and AI
errors to safe HTTP responses, and calls `ComplaintGraphService`; it does not
contain LLM business logic directly.

## Step 5 — LangGraph — 2:20–3:05

Show:

- `backend/app/agents/graph.py`
- `backend/app/agents/state.py`
- `backend/app/agents/router.py`

Explain the graph:

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

Say:

> Each complaint operation has separate steps and shared state, so LangGraph
> provides explicit orchestration instead of placing everything inside one
> large LLM prompt.

## Step 6 — Log Complaint Tool — 3:05–3:35

Show:

- `backend/app/agents/tools/log_complaint.py`
- `backend/app/services/complaint_extraction_service.py`

Explain structured factual extraction, source grounding, Pydantic validation,
and the rule that missing values remain `null`.

## Step 7 — Groq service — 3:35–4:05

Show `backend/app/services/groq_service.py`.

Explain:

- Groq integration is centralized in one reusable service.
- The model and key are environment-configured.
- Responses request structured JSON and are validated with Pydantic.
- Provider, malformed JSON, and validation failures are converted to typed
  errors.

## Step 8 — Pydantic contracts — 4:05–4:30

Show:

- `backend/app/schemas/complaint.py` — `ComplaintData` and `ComplaintPatch`.
- `backend/app/schemas/complaint.py` — `RiskAssessment`.

Say:

> Pydantic prevents invalid model output from entering application state.

Mention that `ComplaintPatch` is sparse and explicit `null` is distinct from
an omitted field.

## Step 9 — Edit Complaint Tool — 4:30–5:05

Show:

- `backend/app/agents/tools/edit_complaint.py`
- `backend/app/services/edit_complaint_service.py`
- `backend/app/services/complaint_merge_service.py`

Explain:

> The model does not regenerate the entire complaint. It returns only changed
> fields, which are safely merged with existing state.

Point to `exclude_unset=True` or the equivalent `as_update_dict()` path and
explain why unrelated values survive.

## Step 10 — Risk service — 5:05–5:35

Show `backend/app/services/risk_service.py`.

Explain deterministic signals for adverse events, contamination, foreign
material, damage, packaging, and other obvious terms; then explain the
contextual Groq assessment, negation handling, and QA-review disclaimer.

Say:

> The LLM does not make the final regulatory decision.

## Step 11 — Document extraction — 5:35–6:05

Show:

- `backend/app/services/document_parser.py`
- `backend/app/agents/tools/document_extraction.py`

Explain:

- PDF uses PyMuPDF.
- DOCX uses `python-docx`.
- TXT uses plain text decoding.
- EML uses Python's standard email parser.

Then trace:

```text
extracted text → shared ComplaintExtractionService → ComplaintData
```

Say:

> Document intake and chat intake ultimately use the same complaint schema and
> extraction pipeline.

## Step 12 — AI insights — 6:05–6:45

Show:

- `backend/app/services/completeness_service.py`
- `backend/app/services/duplicate_detection_service.py`
- `backend/app/services/complaint_summary_service.py`
- `backend/app/services/root_cause_service.py`
- `backend/app/services/capa_service.py`

Explain deterministic completeness, explainable structured duplicate scoring,
and optional AI-generated summary, investigation hypotheses, and CAPA
recommendations.

## Step 13 — Frontend response — 6:45–7:10

Return to `frontend/src/hooks/useComplaintWorkflow.js` and
`frontend/src/store/complaintSlice.js`.

Show the response fields:

```text
response.complaint
response.risk_assessment
response.ai_insights
```

Explain that Redux applies them to the read-only form, risk card, insights
panel, changed-field markers, and pending audit events.

## Step 14 — Save workflow — 7:10–7:40

Show the Save button in `frontend/src/pages/ComplaintPage.jsx`, then
`frontend/src/hooks/useComplaintWorkflow.js` and
`backend/app/services/complaint_save_service.py`.

Say:

> AI interactions do not automatically persist data. Persistence happens only
> when the user explicitly clicks Save Complaint.

## Step 15 — Database — 7:40–8:15

Show:

- `backend/app/models/complaint.py`
- `backend/app/models/ai_assessment.py`
- `backend/app/models/audit_log.py`
- `backend/alembic/versions/0002_complaint_persistence.py`

Explain the complaint, immutable AI assessment snapshots, audit relationships,
JSONB recommended actions, and Alembic-managed PostgreSQL schema.

## Step 16 — Audit — 8:15–8:50

Show:

- `frontend/src/components/audit/AuditTimeline.jsx`
- `backend/app/services/complaint_save_service.py`
- `backend/app/schemas/persistence.py`

Point to `changed_fields`, old/new values, event source, and timestamps.

Conclude:

> This keeps an explainable history of how AI changed complaint information,
> while keeping the final action under explicit QA review and user save control.

## Closing — 8:50–9:00

Return to the live UI and state that all mandatory intake paths—Copilot log,
Copilot edit, and PDF/DOCX/TXT/EML document extraction—share the same typed
state, risk reassessment, and save boundary.
