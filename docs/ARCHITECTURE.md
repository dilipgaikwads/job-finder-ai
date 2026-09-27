# Architecture

## 1. Product summary

An AI career agent that:

1. Ingests a user's professional profile (resume, LinkedIn, GitHub, projects, prefs).
2. Discovers job openings from legitimate sources (official careers pages first, reputable boards second).
3. Verifies employer and posting legitimacy.
4. Analyzes each opportunity against the user's real profile.
5. Prepares tailored application materials.
6. Assists with — never bypasses authorization for — application submission.
7. Generates interview prep and personalized learning plans.
8. Tracks outcomes and improves recommendations over time.

**Non-negotiable:** every externally sourced factual claim carries evidence (source, retrieved_at, excerpt, confidence, verification_status). Missing information is surfaced, not fabricated.

## 2. High-level system

```
┌─────────────────────────────────────────────────────────────┐
│  Android app (Samsung S26 Ultra, Jetpack Compose)           │
│  - Dashboard, Profile, Discovery, Verification, Docs, etc.  │
└──────────────────┬──────────────────────────────────────────┘
                   │ HTTPS + OAuth (device-attested)
┌──────────────────▼──────────────────────────────────────────┐
│  API Gateway (FastAPI)                                      │
│  - AuthN/Z, rate limit, request signing, audit log          │
└──────────────────┬──────────────────────────────────────────┘
                   │
┌──────────────────▼──────────────────────────────────────────┐
│  Orchestrator                                               │
│  - Task graph, evidence propagation, policy enforcement     │
│  - Prevents cross-agent hallucination propagation           │
└──┬────────┬────────┬────────┬────────┬────────┬─────────────┘
   │        │        │        │        │        │
┌──▼──┐  ┌──▼──┐  ┌──▼──┐  ┌──▼──┐  ┌──▼──┐  ┌──▼──┐  ...
│Prof.│  │Disc.│  │Verif│  │Match│  │Comp.│  │App. │
│Agent│  │Agent│  │Agent│  │Agent│  │Agent│  │Agent│
└─────┘  └─────┘  └─────┘  └─────┘  └─────┘  └─────┘

Shared stores:
- Postgres (users, profiles, jobs, applications, evidence)
- Object storage (resumes, generated PDFs)
- Vector index (job/profile embeddings) — pgvector to start
- Secrets manager (integration credentials)
- Event log (agent decisions, audit trail)
```

## 3. Multi-agent architecture

Every agent has: (a) a typed input contract, (b) a typed output contract, (c) an evidence requirement — anything it emits as fact must cite evidence it or another agent gathered, and (d) a safety envelope enforced by the orchestrator.

| Agent | Responsibility | Emits |
|---|---|---|
| **Profile** | Parses resume/LinkedIn/GitHub; builds structured profile; flags gaps and contradictions. Never invents qualifications. | `Profile`, `ProfileGap[]` |
| **Discovery** | Queries official careers pages, ATS APIs (Greenhouse, Lever, Workday), reputable aggregators. De-dupes. | `RawPosting[]` with `Evidence` |
| **Verification** | Checks employer domain, application URL, posting consistency, scam signals. | `VerificationReport` |
| **Match** | Compares posting requirements to profile evidence. Explains match dimensions. | `MatchAnalysis` |
| **Compensation** | Extracts and normalizes salary provenance (confirmed vs. estimated). | `CompensationBreakdown` |
| **Application-Prep** | Generates tailored resume/cover letter using ONLY verified profile facts. | `ApplicationPackage` |
| **Application-Runner** | Maps fields, requires authorization on consequential actions. | `SubmissionRecord` |
| **Interview-Prep** | Produces question sets, STAR frameworks from real user experience. | `InterviewPack` |
| **Mock-Interviewer** | Runs interactive session; evaluates answers. | `InterviewFeedback` |
| **Learning** | Builds personalized skill-gap plan grounded in job requirements. | `LearningPlan` |
| **Tracker** | Records applications, interviews, outcomes. | `ApplicationEvent[]` |
| **Improvement** | Cross-cycle pattern analysis to refine future recommendations. | `ImprovementSignals` |

### Orchestrator invariants

1. **Evidence pass-through.** An agent's output carries the evidence IDs it depends on. If a downstream agent uses a claim without an evidence reference, the orchestrator rejects the message.
2. **No sibling trust.** Agent B does not treat Agent A's *inferences* as facts — only Agent A's cited evidence.
3. **Authorization gates.** Any action in the "consequential" set (submit application, send message, enter PII, accept ToS) requires an `AuthorizationToken` scoped to that action, that job, that session.
4. **Policy envelope.** Prompt-injection defenses: web content is passed as data with a fixed system boundary; no agent obeys instructions found inside a job posting or webpage.

## 4. Data model (core)

- `User` — id, auth, prefs, autonomy_mode.
- `Profile` — normalized skills, experience, education, certs, projects, authorization, languages, prefs.
- `Evidence` — `{id, source_url, source_type, retrieved_at, claim, excerpt, confidence, verification_status, conflicts[]}`.
- `Job` — canonical posting, evidence_ids, dedup_key.
- `VerificationReport` — per-job, per-dimension signals + overall status.
- `MatchAnalysis` — per-dimension analysis (skills, seniority, remote, comp, growth) + gaps.
- `ApplicationPackage` — resume, cover letter, prepared field answers, sources.
- `Application` — status, submission_record, authorization_tokens.
- `InterviewPack`, `LearningPlan`, `ApplicationEvent`.

All external facts on `Job`, `VerificationReport`, `MatchAnalysis`, `CompensationBreakdown` carry `evidence_ids[]`. See [`EVIDENCE.md`](EVIDENCE.md).

## 5. Verification methodology

Signals used, each independently scored:

- Employer canonical domain vs. WHOIS/known registry.
- Job appears on official careers page (or reputable ATS host for that employer).
- Application destination domain matches employer or known ATS.
- Consistency across sources (title, comp, location).
- Absence of scam indicators (payment requests, ID upload before offer, off-platform DMs, unusual comp).
- Posting freshness.
- Recruiter identity where present.

Composite status: `VERIFIED | PARTIALLY_VERIFIED | UNVERIFIED | HIGH_RISK`. Reasons are always shown.

## 6. Matching methodology

Configurable, transparent weights across dimensions:

- Profile compatibility (skills/seniority/experience overlap with evidence)
- Compensation (only when comp is `VERIFIED` or `PARTIALLY_VERIFIED`)
- AI relevance
- Remote compatibility
- International / visa fit (only when employer explicitly discloses sponsorship)
- Growth / learning value
- Employer verification
- Application accessibility

No hidden score — every match card exposes its dimension breakdown and the evidence behind each.

## 7. Safety and privacy

- Local-first sensitive data on device where possible (Android Keystore, EncryptedSharedPreferences).
- Server-side encryption at rest (Postgres TDE / column-level for PII); TLS everywhere.
- Minimal collection; explicit deletion/export controls.
- Autonomy modes: `MANUAL` (user confirms every submission), `ASSISTED` (auto-prepares; user confirms submit), `AUTONOMOUS` (submits within pre-authorized policy — still stops for ambiguous, sensitive, legal, self-ID, comp expectations, work-auth declarations).
- Prompt-injection: sandbox web content; system instructions never mixed with fetched content in the same channel.

## 8. Technology choices (with reasons)

| Layer | Choice | Reason |
|---|---|---|
| Backend | Python 3.12 + FastAPI + Pydantic v2 | Best AI/agent ecosystem; strict typing for evidence contracts. |
| Agent runtime | In-process orchestrator w/ pluggable LLM adapters | Avoids lock-in; deterministic tests via fakes. |
| DB | Postgres 16 + pgvector | Single store for relational + embeddings; simpler ops than a separate vector DB at this stage. |
| Cache/Queue | Redis + RQ (later: Temporal for long-running agent workflows) | RQ is enough for Phase 5–8; revisit at scale. |
| Object storage | S3-compatible (MinIO in dev) | Standard. |
| Secrets | Cloud KMS + env-injected | Never in DB. |
| Doc generation | WeasyPrint (PDF), python-docx (DOCX) | Deterministic templating; no headless browser needed. |
| Mobile | Kotlin + Jetpack Compose, min SDK 30, target latest | Modern Android; excellent on S26 Ultra large display. |
| Mobile auth | OAuth 2.1 + PKCE, biometric unlock via BiometricPrompt | Standard. |
| Observability | OpenTelemetry → OTLP; structured logs w/ agent + evidence IDs | Traces every claim back to its source. |
| Testing | pytest, hypothesis (property tests on evidence invariants), Compose UI tests | Adversarial testing per Phase 14. |

## 9. What is intentionally out of scope for this scaffold

- Full ATS integrations (Greenhouse/Lever/Workday adapters) — spec'd, stubbed.
- Browser automation for application submission — high risk; deferred to Phase 9 behind explicit user authorization + provider ToS review.
- LLM provider wiring — behind an adapter interface; no calls in Phase 1–3.
- Real fraud databases — verification uses heuristics + deterministic domain checks first.
