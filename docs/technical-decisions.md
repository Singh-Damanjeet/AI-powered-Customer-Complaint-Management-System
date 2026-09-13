# Technical Decisions

These notes explain the design choices an evaluator should be able to discuss
in the code walkthrough.

1. **LangGraph** — The complaint workflow has explicit stages and branches for
   logging, editing, document intake, validation, risk, and insights. LangGraph
   makes those transitions visible and keeps the next step deterministic.

2. **Patch-based editing** — Edit requests return a sparse `ComplaintPatch`.
   Only fields explicitly identified by the request are merged, so omitted
   complaint facts cannot be erased accidentally.

3. **Separate risk assessment** — Extraction records source-grounded facts;
   risk classification reasons over the resulting complaint. Keeping them
   separate makes both outputs auditable and ensures risk runs after every
   complaint change.

4. **Deterministic risk signals** — Explicit adverse-event, hospitalization,
   recall, and similar phrases are detected before the AI recommendation. The
   signals provide consistent safety guardrails and context; they do not
   replace QA review.

5. **PostgreSQL** — The system needs durable relational complaint, assessment,
   and audit history. PostgreSQL provides transactions, JSONB for structured
   recommendations, and managed hosting options without Docker coupling.

6. **Redux as frontend authority** — Redux holds the current complaint, risk,
   insight, audit, and save state in one predictable store. Components render
   that state and do not maintain competing complaint copies.

7. **Read-only complaint fields** — The form is intentionally not an editor.
   Copilot and document extraction are the only complaint mutation paths, which
   preserves the requirement that every change is AI-mediated and reassessed.

8. **Document-to-text extraction** — PDF, DOCX, TXT, and EML files are parsed
   from uploaded bytes into normalized text first. The same factual extraction
   contract can then be reused without a separate model for every file format.

9. **QA review is mandatory** — AI risk, investigation areas, summaries, and
   CAPA suggestions are preliminary recommendations. Structured validation and
   source grounding reduce errors, but a qualified reviewer must decide what to
   investigate or execute.

10. **Production limitations** — There is no authentication, RBAC, OCR for
    scanned PDFs, electronic signature, regulated validation package, or remote
    object storage. Deployment must add those controls before production GxP
    use.
