# Job Finder AI

An evidence-first career platform that discovers job opportunities from supported official ATS sources, checks risk signals, and explains profile-to-job matching.

**Design principle:** Reliability over apparent intelligence. Prefer "I could not verify this" over confident guesses.

## Current runnable experience

- Responsive local web dashboard served by FastAPI at `http://127.0.0.1:8000/`.
- Resume upload and draft profile extraction (PDF, DOCX, TXT).
- Profile preference confirmation.
- Job discovery through supported Greenhouse and Lever boards.
- Verification and transparent match ranking with risk filtering.
- Local notification inspection (log-only by default).
- Interactive API documentation at `/docs`.

## Repository

- `backend/` — FastAPI service, agents, resume parser, APIs and static dashboard.
- `android/` — Jetpack Compose starter project.
- `docs/ARCHITECTURE.md` — architecture and safety model.
- `docs/ROADMAP.md` — planned product phases.
- `docs/SOURCING_POLICY.md` — allowed job-source policy.
- `docs/GETTING_STARTED.md` — macOS and Windows setup and run instructions.

## Run locally on macOS

```bash
cd "$HOME/Job Finder AI"
git switch feature/local-web-dashboard
git pull --ff-only origin feature/local-web-dashboard
cd backend
./.venv/bin/python -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

Open `http://127.0.0.1:8000/`.

## Development limitations

Profiles, tokens, evidence and notifications are held in memory and are cleared when the backend restarts. Email requires SMTP configuration. Job application submission, application-material generation, interview coaching, learning plans and persistent application tracking are not implemented in this version.

The dashboard is designed for local development and should not be exposed directly to the public internet.
