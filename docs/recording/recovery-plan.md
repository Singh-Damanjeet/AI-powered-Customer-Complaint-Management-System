# Demo Recovery Plan

Use this plan if Groq temporarily fails during recording.

1. Do not fake or manually insert an AI response.
2. Wait for the current request to finish and read the Copilot error message.
3. Retry the request once after confirming the backend is still running.
4. Verify `GROQ_API_KEY` and `GROQ_MODEL` in the local environment without
   displaying their values.
5. Verify the Groq service status and network access.
6. Confirm that the current complaint state is still present; the application
   is expected to preserve it after an AI failure.
7. If necessary, restart the backend, re-run `GET /api/health`, and retry the
   exact prompt.
8. If the failure persists, stop the recording and document the unavailable
   external dependency. Do not add a mocked demo mode to production.

For a database failure, stop before saving, preserve the unsaved workspace, and
restore PostgreSQL connectivity before retrying. Never claim persistence until
the save response and complaint number are visible.
