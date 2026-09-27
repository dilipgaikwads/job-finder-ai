# Backend

Python 3.11+, FastAPI, Pydantic v2.

## Install

```bash
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
```

## Run

```bash
uvicorn app.main:app --reload
```

## Test

```bash
pytest
```

## Layout

```
app/
  main.py                # FastAPI wiring
  models/                # Pydantic domain models (evidence, profile, job, verification, match)
  agents/
    base.py              # Agent[TIn, TOut] contract
    orchestrator.py      # Enforces evidence propagation
    verification_agent.py# Deterministic scam/legitimacy signals
  services/
    evidence_store.py    # EvidenceStore protocol + InMemory impl
  core/
    domains.py           # Registrable domain / ATS-host helpers
  api/                   # Future route modules
tests/
  test_evidence_invariants.py
  test_domains.py
  test_verification_agent.py
  test_api.py
```

## What's here (Phases 1–5)

- Evidence-first models with invariants (`Job` refuses to construct without evidence ids on core fields).
- `Orchestrator` rejects any agent output whose emitted evidence ids don't resolve in the store.
- `VerificationAgent` — 7 deterministic signals (domain match, ATS allowlist, source consistency, scam phrases, upfront payment, required fields, comp provenance).
- **Resume parser** — PDF/DOCX/TXT → structured Profile draft with `gaps[]` (never invents).
- **Discovery adapters** — Greenhouse and Lever public job boards, real APIs, `httpx.MockTransport` tests.
- **`MatchAgent`** — deterministic per-dimension scoring with per-dimension evidence.
- **Notifications** — `LogNotifier` (default) and `SMTPNotifier` (env-configured); high-risk postings never trigger notifications.
- 27 passing tests, including a full upload → search → verify → match → notify end-to-end.

## Endpoints

| Method | Path | What |
|---|---|---|
| GET  | `/health` | Liveness. |
| POST | `/jobs/verify` | Verify an arbitrary `Job` payload — returns `VerificationReport`. |
| POST | `/resumes` | Multipart upload (.pdf/.docx/.txt) → returns `user_id`, detected fields, and `gaps[]`. |
| PATCH | `/profiles/{user_id}` | Confirm user-owned facts (name, email, prefs). Nothing is inferred. |
| POST | `/profiles/{user_id}/search` | Fan out across adapters → verify → match → notify. |
| GET  | `/notifications/{user_id}` | Inspect notifications sent (dev, when `LogNotifier` is active). |

## What's next

See `docs/ROADMAP.md`. Phase 6 = comp normalization & richer match; Phase 7 = extended verification (WHOIS, cross-source consistency); Phase 8 = application prep.
