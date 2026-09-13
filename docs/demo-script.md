# Working Demo Video Script

Target duration: approximately 7 minutes. Use fictional data only. Keep the
browser at `http://localhost:5173` and the API at `http://localhost:8000`.

## 0:00–0:30 — Project overview

Show the empty workspace and explain that the system supports pharmaceutical
API/FDF complaint intake. Point out the read-only complaint record, AI
Copilot, risk assessment, AI insights, and audit trail. State the control:
facts are changed only by Copilot messages or document upload; Save Complaint
is explicit.

## 0:30–1:30 — Log Complaint Tool

In the Copilot, send:

> ABC Pharma reported brown discoloration on approximately 120 Metformin 500
> mg tablets from batch MT24003. No adverse events have been reported.

Show the populated facts. Point out that unsupported facts such as product
type and dates remain blank (`—`), while the description preserves the
reported wording. Confirm that no database save has occurred.

## 1:30–2:15 — AI Risk Assessment

Show the preliminary severity, priority, rationale, recommended actions, and
the `AI recommendation — QA review required` disclaimer. Show Complaint
Completeness, the factual summary, and any available optional insight cards.
Explain that the risk result is a triage recommendation, not a final QA
disposition.

## 2:15–3:00 — Edit Complaint Tool

Send this exact edit:

> Actually change the batch number to MT24004 and quantity affected to 500.

Show that only Batch / Lot Number and Quantity Affected are highlighted and
changed. Call out that the other complaint values remain in place, the risk
card is recalculated, and the local audit timeline records the edit. The
complaint is still unsaved.

## 3:00–3:45 — Risk-changing edit

Send:

> Also one patient experienced severe vomiting after taking the product.

Show the description update, changed risk result/recommendations, and the
new audit entry. Explain that the explicit adverse-event signal can increase
triage urgency, but QA still makes the final decision.

## 3:45–4:45 — Document Extraction Tool

Reset the workspace and upload:

`sample_documents/metformin_discoloration.pdf`

Show the extraction status, populated record, risk assessment, insights, and
`DOCUMENT_EXTRACTED` audit event. Then send:

> Change quantity affected to 250.

Point out that document-derived fields are preserved while the quantity is
updated through the Edit Complaint Tool. Optionally repeat the upload with
`foreign_material.docx`, `packaging_issue.txt`, or `complaint_email.eml` to
demonstrate all supported formats.

## 4:45–5:30 — Completeness and duplicate detection

Show the deterministic completeness score and missing-field labels. If a
matching saved record exists, show the `Possible Duplicate` card, similarity
score, matched fields, and explanation. Emphasize that the result is a review
cue and not a confirmed duplicate determination.

## 5:30–6:15 — Summary, investigation, and CAPA

Show the concise source-grounded summary, `Potential Investigation Areas`,
and the three CAPA sections:

- Immediate Actions
- Investigation Actions
- Preventive Actions

Point out that investigation output is phrased as a hypothesis and CAPA is
labeled `AI recommendation — QA review required`.

## 6:15–7:00 — Audit Trail and Save Complaint

Click Save Complaint once. Show the saving state, generated complaint number
such as `CMP-2026-0001`, and persisted audit timeline. In the API or Swagger,
open the complaint, `/audit`, and `/assessments` endpoints to demonstrate
reloadable data. Finish by clicking Reset and show that complaint, risk,
insights, pending audit events, saved state, and Copilot messages clear for a
new intake.

