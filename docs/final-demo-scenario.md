# Final Demo Scenario

Use fictional data and start with a clean application. The primary scenario is
ABC Pharma reporting a Metformin Hydrochloride Tablets quality complaint:

- Strength: 500 mg
- Batch: MT24003
- Manufacturing date: 2026-07-18
- Expiry date: 2028-06-30
- Quantity: 120 tablets
- Complaint: brown discoloration observed on several tablets
- Initial adverse event: none reported

## Step 1 — Start clean

Click **Reset**.

Verify that the form is empty, no risk assessment is shown, and no previous
complaint state remains.

## Step 2 — Log complaint

Send this exact prompt through the AI Copilot:

> ABC Pharma reported brown discoloration on approximately 120 Metformin Hydrochloride 500 mg tablets from batch MT24003. The batch was manufactured on 18 July 2026 and expires on 30 June 2028. No adverse events have been reported.

Verify that the form populates, all complaint fields remain read-only, and risk,
completeness, summary, investigation suggestions, and CAPA recommendations
appear.

## Step 3 — Edit complaint

Send:

> Actually change the batch number to MT24004 and quantity affected to 500 tablets.

Verify that only batch and quantity change, unrelated fields remain identical,
changed fields highlight, and risk reruns.

## Step 4 — Risk-changing edit

Send:

> Also one patient experienced severe vomiting after taking the product.

Verify that the new factual information is added, risk reassesses, and
recommendations update.

## Step 5 — Document extraction

Click **Reset**, then upload:

`sample_documents/metformin_discoloration.pdf`

Verify that the document parses and populates the same complaint form and risk
assessment.

## Step 6 — Edit document-derived complaint

Send:

> Change the quantity affected to 250.

Verify that quantity changes, document-derived data remains, and risk
reassesses.

## Step 7 — Save complaint

Click **Save Complaint** once.

Verify that a complaint number is generated and that the PostgreSQL complaint,
assessment snapshot, and audit history are persisted. Reload the complaint
through the API or Swagger endpoints to confirm the latest values.
