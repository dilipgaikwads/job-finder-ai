# Roadmap

Each phase ends with runnable software and tests. No phase depends on a later phase's stubs being real.

## Phase 1 — Requirements & architecture ✅
- `ARCHITECTURE.md`, `AGENTS.md`, `EVIDENCE.md`, `ROADMAP.md`.
- Success: architecture reviewed; open questions listed.

## Phase 2 — Repo & data model ✅ (scaffold in this commit)
- Monorepo layout (`backend/`, `android/`, `docs/`).
- Pydantic models for `Evidence`, `Profile`, `Job`, `VerificationReport`, `MatchAnalysis`.
- Property tests for evidence invariants.

## Phase 3 — Orchestrator + verification thin slice ✅ (scaffold in this commit)
- Orchestrator with typed agent contracts.
- Deterministic `VerificationAgent` (domain checks, scam heuristics, URL consistency).
- `POST /jobs/verify` end-to-end + tests.

## Phase 4 — Profile intelligence
- Resume parser (PDF/DOCX → structured `Profile`).
- LinkedIn/GitHub import adapters.
- Gap and contradiction detection.
- Acceptance: given 5 real resumes, extract skills/roles/dates with ≥ 95% field-level accuracy; flag every field it is unsure of.

## Phase 5 — Verified job discovery
- Adapters for Greenhouse and Lever public boards first (well-documented, employer-verified).
- Canonical dedupe key (employer + normalized title + location + posted_at bucket).
- Freshness re-fetch policy.
- Acceptance: for 10 seed employers, discover postings; every posting carries `source_url` on official ATS.

## Phase 6 — Evidence-based analysis
- `MatchAgent`, `CompensationAgent`.
- Configurable dimension weights; per-dimension explanations.
- Acceptance: match card renders full breakdown; no numeric score without dimension backing.

## Phase 7 — Verification & scam detection
- Extend Phase 3 signals with WHOIS lookup, ATS host allowlist, cross-source consistency, red-flag phrase detector.
- Acceptance: on labeled scam corpus, catch ≥ 90% with < 5% false-positive rate.

## Phase 8 — Application preparation
- Resume/cover-letter generator using ONLY verified profile facts.
- Field-answer prep with source pointers.
- PDF/DOCX export.
- Acceptance: every generated claim traces to a profile evidence ID.

## Phase 9 — Supervised application automation
- Field-mapping engine; authorization tokens for consequential steps.
- Optional browser automation only where permitted; per-employer allowlist; no CAPTCHA bypass.
- Acceptance: pilot on 3 ATS platforms with `MANUAL` mode; zero unauthorized submissions in adversarial tests.

## Phase 10 — Interview prep & mock interviewer
- Question set generator (role- and company-specific), STAR templates, mock interview loop with feedback.
- Acceptance: mock session logs answers with source-of-truth links back to real user experience.

## Phase 11 — Personalized learning
- Gap → priority → sequence → practical project.
- Acceptance: plan for each application; no invented market facts.

## Phase 12 — Document generation
- Templated PDF/DOCX/HTML for all 11 doc types; each identifies its source material.

## Phase 13 — Application tracking
- Event log; per-application timeline; outcome capture.

## Phase 14 — Security, privacy, hallucination, adversarial testing
- Prompt-injection corpus; scam corpus; PII scrubbing tests; authorization bypass fuzzer; property tests on evidence invariants.

## Phase 15 — Samsung Galaxy S26 Ultra optimization
- Large-screen layouts, S-Pen affordances where useful, dark/light, biometric flows, background sync policy tuned for battery.

## Phase 16 — Production deployment
- Infra as code, secrets rotation, observability dashboards, incident runbooks, backup/restore, DPA templates.

## Open questions to resolve with the user
1. Preferred LLM provider(s) and hosting posture (self-hosted vs. API)? Determines cost, privacy, and adapter defaults.
2. Which countries in scope initially? Affects legal/compliance surface (GDPR, right-to-work checks).
3. Autonomy default (`MANUAL` recommended)?
4. Which ATS integrations to prioritize beyond Greenhouse/Lever?
5. Any employers/domains to allowlist or blocklist up front?
