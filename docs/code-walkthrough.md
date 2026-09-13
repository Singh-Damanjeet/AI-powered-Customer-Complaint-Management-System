# Technical Code Walkthrough

Follow one complaint through the repository rather than opening unrelated
files. All paths below are relative to the repository root.

## 1. Frontend input to API

```text
frontend/src/components/copilot/ChatInput.jsx
        ↓
frontend/src/hooks/useComplaintWorkflow.js
        ↓
frontend/src/services/api.js
        ↓
POST /api/agent/message
```

`ChatInput.jsx` owns only the temporary message draft. Complaint facts are not
edited there. `useComplaintWorkflow.js` sends the current complaint only when
an edit is being made, applies the validated response to Redux, and creates
local pending audit events. `api.js` contains the Axios boundaries for chat,
document upload, save, audit, and assessment requests.

`frontend/src/store/store.js` combines the Redux slices. Complaint data,
risk, insights, changed fields, save state, and audit state live in
`frontend/src/store/complaintSlice.js`; Copilot messages and processing state
live in `frontend/src/store/copilotSlice.js`.

## 2. FastAPI boundary and graph service

```text
backend/app/api/ai.py
        ↓
backend/app/services/complaint_graph_service.py
        ↓
backend/app/agents/graph.py
        ↓
LangGraph StateGraph
```

`backend/app/api/ai.py` exposes `/api/agent/message` and
`/api/agent/document`, maps parser/provider errors to safe HTTP responses, and
does not persist AI intake. `ComplaintGraphService` validates request state,
invokes the compiled graph, and validates the final
`ComplaintAgentResponse`.

## 3. LangGraph routing and tools

`backend/app/agents/router.py` classifies obvious intents deterministically:
`LOG_COMPLAINT`, `EDIT_COMPLAINT`, `DOCUMENT_COMPLAINT`, or `UNKNOWN`.
`backend/app/agents/graph.py` connects the nodes in this order:

```text
classify_intent
  → log_complaint / edit_complaint / extract_document
  → validate_complaint
  → assess_risk
  → generate_insights
  → generate_response
```

The log path uses `backend/app/agents/nodes/log_complaint.py` and
`backend/app/agents/tools/log_complaint.py`. The edit path uses
`backend/app/agents/nodes/edit_complaint.py` and
`backend/app/agents/tools/edit_complaint.py`. The document path uses
`backend/app/agents/nodes/extract_document.py`,
`backend/app/agents/nodes/extract_complaint_from_document.py`,
`backend/app/services/document_parser.py`, and
`backend/app/agents/tools/document_extraction.py`.

## 4. Structured AI and validation

```text
tool/node
  ↓
backend/app/services/structured_ai.py
  ↓
backend/app/services/groq_service.py
  ↓
Groq structured JSON
  ↓
Pydantic validation
```

`GroqService` is the only provider adapter. It uses `GROQ_API_KEY` and
`GROQ_MODEL` from `backend/app/config.py`, requests a JSON schema, and
validates the response. Factual extraction is implemented in
`backend/app/services/complaint_extraction_service.py`; the contracts are in
`backend/app/schemas/complaint.py`.

The risk path is `backend/app/agents/nodes/assess_risk.py` plus
`backend/app/services/risk_service.py`, with deterministic signals in
`backend/app/schemas/risk.py`. Risk assessment runs after logging, editing,
and document extraction.

Optional insights are coordinated by
`backend/app/services/complaint_insights_service.py` and
`backend/app/agents/nodes/generate_insights.py`. Completeness is deterministic
(`backend/app/services/completeness_service.py`); duplicate matching uses
`backend/app/services/duplicate_detection_service.py`; summaries,
investigation hypotheses, and CAPA recommendations use the existing Groq
adapter and the typed contracts in `backend/app/schemas/insights.py`.

## 5. Response to read-only UI

```text
ComplaintAgentResponse
  ↓
backend/app/schemas/complaint.py
  ↓
frontend/src/hooks/useComplaintWorkflow.js
  ↓
frontend/src/components/complaint/ComplaintForm.jsx
  ↓
frontend/src/components/complaint/ReadOnlyField.jsx
```

`ComplaintForm.jsx` renders every complaint field with a read-only input or
textarea. The only frontend complaint mutation action is applying a response
from the Copilot/document API; there is no manual field edit path.

## 6. Persistence, save, and audit

```text
Save Complaint
  ↓
POST /api/complaints
  ↓
backend/app/services/complaint_save_service.py
  ↓
backend/app/repositories/complaint_repository.py
  ↓
SQLAlchemy models + PostgreSQL
```

`backend/app/api/complaints.py` owns persistence routes. The transactional
save service writes `backend/app/models/complaint.py`,
`backend/app/models/ai_assessment.py`, and
`backend/app/models/audit_log.py` together. `ComplaintRepository` loads the
latest assessment and chronological audit events. The schema is created by
`backend/alembic/versions/0001_foundation.py`,
`backend/alembic/versions/0002_complaint_persistence.py`, and
`backend/alembic/versions/0003_phase9_history_indexes.py`.

The frontend displays unsaved events from Redux through
`frontend/src/components/audit/AuditTimeline.jsx`. After a successful save it
refreshes persisted history through `frontend/src/services/api.js` and locks
the workspace until Reset.

