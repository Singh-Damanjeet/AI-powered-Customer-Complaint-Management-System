# Final Requirement Mapping

`PASS` means the requirement was verified in the repository, dependency files,
tests, or documented recording artifacts. Live provider credentials remain
environment-specific and are not stored in the repository.

| Requirement | Implementation | File/Feature | Status |
| --- | --- | --- | --- |
| React | Vite React application | `frontend/package.json`, `frontend/src/` | PASS |
| Redux | Redux Toolkit state management | `frontend/src/store/complaintSlice.js`, `frontend/src/store/copilotSlice.js` | PASS |
| Python | Python backend runtime and package environment | `backend/requirements.txt`, `backend/app/` | PASS |
| FastAPI | REST API and typed routes | `backend/requirements.txt`, `backend/app/main.py`, `backend/app/api/` | PASS |
| LangGraph | Explicit complaint workflow graph | `backend/app/agents/graph.py`, `backend/app/agents/state.py`, `backend/app/agents/router.py` | PASS |
| Groq | Centralized structured-output integration | `backend/requirements.txt`, `backend/app/services/groq_service.py` | PASS |
| Structured outputs | JSON-schema response requests with Pydantic validation | `backend/app/services/groq_service.py`, `backend/app/schemas/` | PASS |
| PostgreSQL | SQLAlchemy PostgreSQL persistence with psycopg | `backend/requirements.txt`, `backend/app/database/`, `backend/alembic/` | PASS |
| Inter font | Google Inter stylesheet and global font family | `frontend/index.html`, `frontend/src/index.css` | PASS |
| Log Complaint Tool | Source-grounded natural-language extraction | `backend/app/agents/tools/log_complaint.py` | PASS |
| Edit Complaint Tool | Sparse patch extraction and safe merge | `backend/app/agents/tools/edit_complaint.py`, `backend/app/services/complaint_merge_service.py` | PASS |
| Document Extraction Tool | PDF, DOCX, TXT, and EML intake | `backend/app/agents/tools/document_extraction.py`, `backend/app/services/document_parser.py` | PASS |
| Risk Assessment | Deterministic signals plus structured AI assessment | `backend/app/services/risk_service.py`, `backend/app/agents/nodes/assess_risk.py` | PASS |
| Read-only AI form | Complaint fields use read-only controls | `frontend/src/components/complaint/ComplaintForm.jsx`, `frontend/src/components/complaint/ReadOnlyField.jsx` | PASS |
| AI controls the form | Complaint state is applied from Copilot/document responses only | `frontend/src/hooks/useComplaintWorkflow.js`, `frontend/src/store/complaintSlice.js` | PASS |
| Form cannot be edited manually | Every complaint display control is rendered with `readOnly` | `frontend/src/components/complaint/ReadOnlyField.jsx` | PASS |
| PDF support | PyMuPDF parser | `backend/app/services/document_parser.py`, `sample_documents/metformin_discoloration.pdf` | PASS |
| Email support | Standard-library EML parser | `backend/app/services/document_parser.py`, `sample_documents/complaint_email.eml` | PASS |
| Document-created complaints can be edited | Shared complaint state and edit graph branch | `backend/app/agents/graph.py`, `frontend/src/hooks/useComplaintWorkflow.js` | PASS |
| Completeness Checker | Deterministic score and missing-field reporting | `backend/app/services/completeness_service.py`, `frontend/src/components/insights/AIInsightsPanel.jsx` | PASS |
| Duplicate Detection | Explainable structured matching against saved complaints | `backend/app/services/duplicate_detection_service.py`, `frontend/src/components/insights/AIInsightsPanel.jsx` | PASS |
| Complaint Summary | Optional source-grounded summary | `backend/app/services/complaint_summary_service.py` | PASS |
| Investigation Suggestions | Potential investigation hypotheses | `backend/app/services/root_cause_service.py` | PASS |
| CAPA Recommendations | Grouped immediate, investigation, and preventive actions | `backend/app/services/capa_service.py` | PASS |
| Audit Trail | Persisted AI/system events with old/new values | `backend/app/models/audit_log.py`, `frontend/src/components/audit/AuditTimeline.jsx` | PASS |
| Demo video readiness | Timed working demo script and exact prompts | `docs/recording/demo-video-script.md`, `docs/recording/demo-prompts.md` | PASS |
| Code walkthrough readiness | Timed lifecycle walkthrough and real file map | `docs/recording/code-walkthrough-script.md`, `docs/recording/code-file-map.md` | PASS |
