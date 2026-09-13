# Code Walkthrough File Map

These are the inspected final repository paths. Use the paths exactly as shown
during the technical walkthrough.

| Walkthrough item | Actual file path |
| --- | --- |
| Frontend Copilot input | `frontend/src/components/copilot/ChatInput.jsx` |
| Complaint read-only form | `frontend/src/components/complaint/ComplaintForm.jsx` and `frontend/src/components/complaint/ReadOnlyField.jsx` |
| Redux complaint slice | `frontend/src/store/complaintSlice.js` |
| Redux Copilot slice | `frontend/src/store/copilotSlice.js` |
| Frontend workflow orchestration | `frontend/src/hooks/useComplaintWorkflow.js` |
| Frontend API service | `frontend/src/services/api.js` |
| FastAPI agent route | `backend/app/api/ai.py` |
| ComplaintGraphService | `backend/app/services/complaint_graph_service.py` |
| LangGraph graph | `backend/app/agents/graph.py` |
| LangGraph state | `backend/app/agents/state.py` |
| Intent router | `backend/app/agents/router.py` |
| Log Complaint Tool | `backend/app/agents/tools/log_complaint.py` |
| Edit Complaint Tool | `backend/app/agents/tools/edit_complaint.py` |
| Document Extraction Tool | `backend/app/agents/tools/document_extraction.py` |
| Document parser | `backend/app/services/document_parser.py` |
| Groq structured-output service | `backend/app/services/groq_service.py` |
| Complaint Pydantic schema | `backend/app/schemas/complaint.py` |
| Risk service | `backend/app/services/risk_service.py` |
| Completeness service | `backend/app/services/completeness_service.py` |
| Duplicate service | `backend/app/services/duplicate_detection_service.py` |
| Complaint summary service | `backend/app/services/complaint_summary_service.py` |
| Investigation/root-cause service | `backend/app/services/root_cause_service.py` |
| CAPA service | `backend/app/services/capa_service.py` |
| Save service | `backend/app/services/complaint_save_service.py` |
| Complaint DB model | `backend/app/models/complaint.py` |
| AI assessment DB model | `backend/app/models/ai_assessment.py` |
| Audit DB model | `backend/app/models/audit_log.py` |
| Persistence schemas | `backend/app/schemas/persistence.py` |
| Persistence migration | `backend/alembic/versions/0002_complaint_persistence.py` |

The graph uses the node implementations in `backend/app/agents/nodes/` for
classification, extraction, validation, risk, insights, and response assembly.
