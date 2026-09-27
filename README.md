# Job Finder AI

An evidence-first, multi-agent career platform that discovers verified job opportunities, prepares tailored applications, and coaches the user through interviews — without hallucinating facts.

**Design principle:** Reliability over apparent intelligence. Prefer "I could not verify this" over confident guesses.

## Contents

- [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) — system, agent, data, evidence, and safety architecture
- [`docs/ROADMAP.md`](docs/ROADMAP.md) — 16-phase implementation plan with acceptance criteria
- [`docs/AGENTS.md`](docs/AGENTS.md) — agent responsibilities, prompts, and tool contracts
- [`docs/EVIDENCE.md`](docs/EVIDENCE.md) — the evidence/provenance model that every fact flows through
- [`backend/`](backend/) — Python FastAPI service (agents, orchestrator, evidence store, verification)
- [`docs/SOURCING_POLICY.md`](docs/SOURCING_POLICY.md) — what job sources are and aren't allowed, and why (dark web is out — read this)
- [`android/`](android/) — Jetpack Compose app targeting Samsung Galaxy S26 Ultra / modern Android

## Status

Phases 1–5 working. Runnable backend: **resume upload → job discovery (Greenhouse & Lever) → verification → matching → notifications**, end-to-end, with 27 passing tests. High-risk postings are filtered before they can reach a notification.

Android is directory layout + a starter screen. See `docs/ROADMAP.md` for what's next.
