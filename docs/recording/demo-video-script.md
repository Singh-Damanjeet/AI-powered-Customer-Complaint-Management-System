# Working Demo Video Script

Target duration: 5–8 minutes. Planned run time: approximately 6 minutes 30 seconds.

This script is for the real application. Use a configured Groq account and a
real PostgreSQL connection during recording. Do not show secrets, use fake AI
responses, or type into the complaint record fields.

## Before the timer starts

- Start PostgreSQL or confirm the managed PostgreSQL provider is reachable.
- From `backend/`, run `alembic upgrade head` and then
  `uvicorn app.main:app --reload`.
- From `frontend/`, run `npm run dev`.
- Verify `GET /api/health` returns `status: ok` and `database: connected`.
- Confirm `GROQ_API_KEY` and `GROQ_MODEL` are configured without exposing them
  on screen.
- Confirm one saved Metformin complaint is available for the duplicate demo.
- Reset the workspace before the opening shot.

## 0:00–0:20 — Introduction

Say:

> This is an AI-powered Customer Complaint Management System designed for
> pharmaceutical manufacturing. The complaint form is intentionally read-only.
> Users create and modify complaints entirely through the AI Copilot or document
> upload.

Show the empty workspace, the read-only badge, the Copilot, and the disabled
`Save Complaint` button.

## 0:20–1:20 — Log Complaint Tool

Submit Prompt 1 from [demo-prompts.md](demo-prompts.md):

```text
ABC Pharma reported brown discoloration on approximately 120 Metformin Hydrochloride 500 mg tablets from batch MT24003. The batch was manufactured on 18 July 2026 and expires on 30 June 2028. No adverse events have been reported.
```

Show:

- The prompt in the Copilot conversation.
- The assistant response.
- The read-only form auto-populating with ABC Pharma, product, strength,
  batch, dates, quantity, and discoloration details.
- The complaint fields remaining non-editable.

Narrate that factual values are extracted from the supplied message. Do not
invent fields that were not supplied.

## 1:20–2:00 — AI Risk Assessment

Show the risk card with severity, priority, rationale, QA investigation
recommendation, and recommended actions.

Say:

> The factual complaint data and AI risk reasoning are intentionally separated.
> Missing factual data remains empty rather than being hallucinated.

Point out that the assessment is preliminary and requires QA review.

## 2:00–2:45 — Edit Complaint Tool

Submit Prompt 2:

```text
Actually change the batch number to MT24004 and quantity affected to 500 tablets.
```

Show:

- The batch changing from `MT24003` to `MT24004`.
- The quantity changing from `120` to `500` tablets.
- The other product, customer, date, and description fields remaining unchanged.
- The changed-field markers.
- The refreshed risk assessment.

Explain that the edit is patch-based and that omitted fields are preserved.

## 2:45–3:30 — Risk-Changing Edit

Submit Prompt 3:

```text
Also one patient experienced severe vomiting after taking the product.
```

Show the complaint context and the new risk assessment. Severity, priority, and
recommendations may change because the adverse event is now part of the
complaint context.

Say:

> Every successful edit triggers a fresh risk assessment.

Do not describe the AI result as a regulatory decision; it is a preliminary QA
triage signal.

## 3:30–4:20 — Document Extraction Tool

Reset the workspace. Upload:

```text
sample_documents/metformin_discoloration.pdf
```

Show:

- The selected PDF name.
- Document extraction status and assistant response.
- The same read-only form populated from the document.
- The generated risk assessment.

Submit Prompt 5:

```text
Change the quantity affected to 250 tablets.
```

Show that the document-derived complaint is edited through the same AI-only
workflow and that the quantity field is highlighted.

## 4:20–5:10 — Bonus AI Features

Show the AI insights panel containing, when available:

- Complaint Completeness Checker.
- Possible Duplicate Detection.
- Complaint Summary.
- Potential Investigation Areas.
- Suggested CAPA actions.

Explain:

- Completeness is deterministic.
- Duplicate detection compares saved structured complaints and is an
  explainable review cue.
- Investigation areas are hypotheses, not confirmed root causes.
- CAPA recommendations require QA review.

If the pre-seeded complaint is present, point to the `Possible Duplicate`
label and matching fields. Never call it a confirmed duplicate.

## 5:10–5:50 — Audit Trail

Show the complaint history entries for:

- Complaint created by AI.
- Batch change.
- Quantity change.
- Risk reassessment.
- Document extraction, when viewing the document path.

Say:

> The audit trail records AI-driven changes and preserves old and new values.

Explain that events remain local until the user saves the complaint.

## 5:50–6:30 — Save Complaint

Click `Save Complaint`.

Show:

- The saved state and disabled post-save editing controls.
- The generated complaint number, for example `CMP-2026-0001`.
- The persisted audit history.
- The saved complaint number in the UI.

Say:

> This demonstrates the complete workflow from natural-language complaint
> intake or document upload through structured extraction, AI-assisted risk
> assessment, editing, audit tracking, and persistence.

Use the separate [duplicate-demo.md](../duplicate-demo.md) preparation when
recording the duplicate warning as a dedicated shot.

## If the live AI request fails

Do not fake a response. Follow [recovery-plan.md](recovery-plan.md), preserve
the current workspace state, and retry only after the service is available.
