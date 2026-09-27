# Job Finder AI

An evidence-first, multi-agent career platform that discovers verified job opportunities, prepares tailored applications, and coaches the user through interviews — without hallucinating facts.

**Design principle:** Reliability over apparent intelligence. Prefer "I could not verify this" over confident guesses.

## Contents

- [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) — system, agent, data, evidence, and safety architecture
- [`docs/ROADMAP.md`](docs/ROADMAP.md) — 16-phase implementation plan with acceptance criteria
- [`docs/AGENTS.md`](docs/AGENTS.md) — agent responsibilities, prompts, and tool contracts
- [`docs/EVIDENCE.md`](docs/EVIDENCE.md) — the evidence/provenance model that every fact flows through
- [`backend/`](backend/) — Python FastAPI service (agents, orchestrator, evidence store, verification)
- [`android/`](android/) — Jetpack Compose app targeting Samsung Galaxy S26 Ultra / modern Android

## Status

Phase 1–3 scaffold. Runnable backend with evidence-first models, a stub orchestrator, and one verified thin slice: profile → job → verification → match. Android is directory layout + one starter screen. See `ROADMAP.md` for what is intentionally not yet built.
