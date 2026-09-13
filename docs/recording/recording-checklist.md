# Recording Checklist

## BEFORE RECORDING

- [ ] Close unnecessary browser tabs.
- [ ] Start the backend.
- [ ] Start the frontend.
- [ ] Verify PostgreSQL connectivity with `GET /api/health`.
- [ ] Verify Groq configuration without showing secrets.
- [ ] Apply Alembic migrations.
- [ ] Reset the application.
- [ ] Verify duplicate seed data exists.
- [ ] Open the sample PDF folder.
- [ ] Increase browser zoom if needed.
- [ ] Disable notifications if possible.
- [ ] Clear unnecessary terminal noise.
- [ ] Confirm the browser viewport has no horizontal overflow.
- [ ] Keep [demo-video-script.md](demo-video-script.md),
  [demo-prompts.md](demo-prompts.md), and the file map available off-camera.

## WORKING DEMO

- [ ] Introduce the system and the AI-controlled read-only form.
- [ ] Log a complaint through the Copilot.
- [ ] Show form population.
- [ ] Show preliminary risk assessment.
- [ ] Edit the batch and quantity using natural language.
- [ ] Show unrelated-field preservation and changed markers.
- [ ] Add the adverse event.
- [ ] Show risk reassessment.
- [ ] Upload the sample document.
- [ ] Edit the extracted complaint.
- [ ] Show bonus AI tools.
- [ ] Show the audit trail.
- [ ] Save the complaint and show its complaint number.

## CODE VIDEO

- [ ] Frontend Copilot input.
- [ ] Read-only complaint fields.
- [ ] Redux complaint and Copilot slices.
- [ ] API service.
- [ ] FastAPI route.
- [ ] LangGraph graph, state, and router.
- [ ] Log Complaint Tool.
- [ ] Edit Complaint Tool and merge logic.
- [ ] Document parser.
- [ ] Groq service.
- [ ] Pydantic contracts.
- [ ] Risk service.
- [ ] Redux response application.
- [ ] Save service.
- [ ] Database models and migration.
- [ ] Audit persistence.

## FINAL TEST BEFORE RECORDING

- [ ] Run backend tests.
- [ ] Run frontend tests.
- [ ] Run the frontend production build.
- [ ] Run backend lint.
- [ ] Start the backend successfully.
- [ ] Verify the health check.
- [ ] Perform the exact final-demo sequence once.
- [ ] Confirm no real secret appears in the recording.

Do not record until the configured live workflow passes completely. If external
Groq or PostgreSQL access is unavailable, stop and use the documented recovery
plan; do not substitute a mock response.

## RECOVERY PLAN

See [recovery-plan.md](recovery-plan.md). The required behavior is to preserve
the current complaint state, report the service failure honestly, and retry
after configuration or provider health is restored.
