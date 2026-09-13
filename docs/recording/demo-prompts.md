# Final Demo Prompts

Use these prompts exactly during the primary recording. Do not improvise unless
the live environment requires a retry after following the recovery plan.

## PROMPT 1 — CREATE

```text
ABC Pharma reported brown discoloration on approximately 120 Metformin Hydrochloride 500 mg tablets from batch MT24003. The batch was manufactured on 18 July 2026 and expires on 30 June 2028. No adverse events have been reported.
```

## PROMPT 2 — EDIT

```text
Actually change the batch number to MT24004 and quantity affected to 500 tablets.
```

## PROMPT 3 — RISK CHANGE

```text
Also one patient experienced severe vomiting after taking the product.
```

## PROMPT 4 — CLEAR FIELD

```text
Remove the expiry date because the customer did not provide it.
```

This demonstrates an explicit clear request. The field becomes `null`; an
omitted field in an edit must remain unchanged.

## PROMPT 5 — DOCUMENT EDIT

```text
Change the quantity affected to 250 tablets.
```

Use this after uploading `sample_documents/metformin_discoloration.pdf`.

## Duplicate-demo prompt

After the primary complaint has been saved, reset the workspace and submit this
similar complaint:

```text
ABC Pharma reported brown spots on approximately 120 Metformin Hydrochloride 500 mg tablets from batch MT24003.
```

Expected result: a `Possible Duplicate` review cue that points to the saved
Metformin complaint. It is not a confirmed duplicate.

## Exact document path

```text
sample_documents/metformin_discoloration.pdf
```
