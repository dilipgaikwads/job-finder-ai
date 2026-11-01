# Evidence & provenance model

Every externally sourced factual claim in the system carries an `Evidence` record. Agents may not emit facts they cannot cite.

## Record

```python
class Evidence(BaseModel):
    id: str                     # ulid
    source_url: HttpUrl
    source_type: Literal[
        "official_careers_page", "ats_greenhouse", "ats_lever",
        "ats_workday", "aggregator", "recruiter_message",
        "user_supplied", "whois", "inferred_deterministic"
    ]
    retrieved_at: datetime      # UTC
    claim: str                  # short natural-language statement of the fact
    excerpt: str | None         # verbatim excerpt supporting the claim (<= 500 chars)
    structured: dict | None     # optional structured payload (e.g., parsed salary)
    confidence: Literal["low", "medium", "high"]
    verification_status: Literal[
        "verified", "partially_verified", "unverified",
        "conflicting", "high_risk"
    ]
    conflicts: list[str]        # ids of conflicting Evidence records
```

## Rules

1. **No fact without an id.** Any field on `Job`, `VerificationReport`, `MatchAnalysis`, or `CompensationBreakdown` that is not user-supplied must reference at least one `Evidence.id` via a sibling `*_evidence_ids: list[str]` field.
2. **No re-inference.** If Agent A infers a fact from Evidence E1, Agent B must consume E1 directly to re-inference — Agent A's *conclusion* is not itself evidence for B.
3. **Freshness.** Every consumer checks `retrieved_at`. If older than the type-specific TTL (e.g., 24h for salary, 7d for posting existence), the orchestrator triggers a refresh before displaying the fact as current.
4. **Conflict surface.** When two evidences disagree, both are retained; `verification_status` becomes `conflicting` and the UI shows both with sources.
5. **User-supplied ≠ verified.** A user-supplied claim about themselves is trusted for use in *their* materials, but is not automatically labeled `verified` for external contexts (e.g., we do not tell an employer the user has certifications without user confirmation for that specific application).
6. **Deterministic inferences allowed.** Some evidence is `source_type = "inferred_deterministic"` — e.g., "application domain does not match employer domain" is derived by rule, and the rule + inputs are the evidence.
7. **Status describes the fact, not the check.** `Evidence.verification_status` describes the verification status of the *fact being recorded*. It must not be used to encode the outcome of a derived check — that belongs on `VerificationSignal.outcome`. See **Three levels of status** below.

## Three levels of status

Three different concepts carry status values. They answer different questions and must not be conflated.

| Field | Enum | Answers |
|---|---|---|
| `Evidence.verification_status` | `VerificationStatus` | *Is the underlying fact/observation itself established?* |
| `VerificationSignal.outcome` | `SignalOutcome` (`pass / warn / fail / inconclusive`) | *Did a specific check pass, warn, fail, or come back inconclusive?* |
| `VerificationReport.composite_status` | `VerificationStatus` | *Across all signals, what is the overall risk/legitimacy posture of this job?* |

### Consequence: a scam posting has three *different* status values at once

For a posting whose description contains a known scam phrase, the deterministic scam-phrase detector produces:

- `Evidence.verification_status = VERIFIED` — we did observe the phrase; the observation is a confirmed deterministic fact.
- `VerificationSignal.outcome = FAIL` — the check failed; the job does not pass this signal.
- `VerificationReport.composite_status = HIGH_RISK` — rolled up with other signals, the posting is high-risk.

A failing check does **not** mean the recorded observation is unverified. Do not confuse an unsuccessful check with an unverified observation.

### The one exception: inconclusive checks

When a check is `INCONCLUSIVE` (e.g., we could not resolve the employer domain), the *underlying observation* could not be established. The Evidence then carries `verification_status = UNVERIFIED`, because the fact itself is not established — only the fact that we were unable to establish it is. Agents must not mark observations VERIFIED when the underlying observation cannot be established.

## Invariants (property-tested)

- Every non-user-supplied factual field on a `Job` has ≥ 1 evidence id.
- Every referenced evidence id resolves.
- `verification_status = "verified"` requires at least one evidence with `source_type` in the "official" set for that fact type.
- No agent output validates if it declares a fact whose evidence's `retrieved_at` is beyond TTL without a refresh marker.
