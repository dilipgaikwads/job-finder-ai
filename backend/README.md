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

## What's here (Phase 1–3)

- Evidence-first models with invariants (`Job` refuses to construct without evidence ids on core fields).
- `Orchestrator` rejects any agent output whose emitted evidence ids don't resolve in the store — prevents cross-agent hallucination propagation.
- `VerificationAgent` runs 7 deterministic signals and returns a per-signal + composite `VerificationReport`.
- `POST /jobs/verify` endpoint end-to-end.

## What's next

See `docs/ROADMAP.md`. Phase 4 = profile ingestion; Phase 5 = Discovery adapters (Greenhouse/Lever first).
