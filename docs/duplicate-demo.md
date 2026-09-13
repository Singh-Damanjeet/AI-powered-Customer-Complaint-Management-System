# Duplicate Detection Demo

Use two fictional complaints to demonstrate a review cue.

## Exact preparation steps

1. Start the backend and frontend using the commands in `README.md`.
2. Reset the workspace so the complaint form is empty.
3. Submit the primary demo complaint from
   `docs/recording/demo-prompts.md`.
4. Confirm the structured complaint and risk assessment appear, then click
   `Save Complaint`.
5. Confirm a complaint number is shown and the saved audit history is visible.
6. Reset the workspace to start a new unsaved complaint.
7. Submit the following similar complaint through the AI Copilot:

```text
ABC Pharma reported brown spots on approximately 120 Metformin Hydrochloride 500 mg tablets from batch MT24003.
```

## First complaint reference

The saved complaint must contain:

- Product: Metformin Hydrochloride
- Strength: 500 mg
- Batch: MT24003
- Complaint: brown discoloration

## Expected second-complaint result

- A `Possible Duplicate` card appears.
- A similarity score is shown.
- Matching fields and reasons are shown.
- The UI does not claim that the complaints are confirmed duplicates.

The first complaint must be explicitly saved before starting the second one;
duplicate detection intentionally compares against persisted complaints and
excludes a complaint from matching itself.
