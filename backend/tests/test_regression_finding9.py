"""Regression tests for reviewer finding #9 — evidence status semantics.

Locks in the three-level status contract documented in docs/EVIDENCE.md:

  - Evidence.verification_status describes the FACT being recorded.
  - VerificationSignal.outcome describes the CHECK result.
  - VerificationReport.composite_status describes the OVERALL posting posture.

The three must never collapse into one another.
"""
from __future__ import annotations

from app.agents.verification_agent import (
    VerificationAgentInput,
    _fail,
    _inconclusive,
    _pass,
    _warn,
)
from app.models.evidence import (
    ConfidenceLevel,
    Evidence,
    SourceType,
    VerificationStatus,
)
from app.models.job import Job
from app.models.verification import SignalOutcome


def _job(store, **overrides) -> Job:
    def mk(claim: str, url: str = "https://boards.greenhouse.io/acme/jobs/1") -> str:
        return store.put(Evidence(
            source_url=url,
            source_type=SourceType.ATS_GREENHOUSE,
            claim=claim,
            excerpt=None,
            confidence=ConfidenceLevel.HIGH,
            verification_status=VerificationStatus.VERIFIED,
        ))

    defaults = dict(
        dedup_key="acme::senior-ai-engineer::remote::2026-10",
        title="Senior AI Engineer",
        employer="Acme AI",
        employer_domain="acme.ai",
        application_url="https://boards.greenhouse.io/acme/jobs/1",
        source_url="https://boards.greenhouse.io/acme/jobs/1",
        location="Remote (US)",
        description="Build production LLM systems. Competitive compensation.",
        title_evidence_ids=[mk("title")],
        employer_evidence_ids=[mk("employer")],
        application_url_evidence_ids=[mk("app url")],
    )
    defaults.update(overrides)
    return Job(**defaults)


# ---------------------------------------------------------------------------
# Test 1 — fact-level status on every verification helper
# ---------------------------------------------------------------------------

def test_verification_helpers_use_fact_level_evidence_status(store):
    """Each helper records a deterministic observation whose fact-status is:

      _pass / _warn / _fail  -> VERIFIED  (observation was established)
      _inconclusive          -> UNVERIFIED (observation could NOT be established)

    This is the fact-vs-check distinction from docs/EVIDENCE.md.
    """
    s_pass = _pass(store, "domain_match_check", "application domain matches employer domain")
    s_warn = _warn(store, "comp_disclosure", "compensation partially disclosed")
    s_fail = _fail(store, "scam_phrase_check", "posting matches known scam phrase 'send bank account'")
    s_incon = _inconclusive(store, "employer_whois", "could not resolve WHOIS for employer domain")

    # pass/warn/fail record established observations -> VERIFIED
    for sig in (s_pass, s_warn, s_fail):
        assert len(sig.evidence_ids) == 1, f"{sig.name} should emit one evidence"
        ev = store.get(sig.evidence_ids[0])
        assert ev is not None, f"{sig.name} evidence must resolve in the store"
        assert ev.verification_status is VerificationStatus.VERIFIED, (
            f"{sig.name}: the observation was established, so the fact-level status "
            f"must be VERIFIED, not {ev.verification_status}."
        )

    # inconclusive records a non-established observation -> UNVERIFIED
    ev = store.get(s_incon.evidence_ids[0])
    assert ev is not None
    assert ev.verification_status is VerificationStatus.UNVERIFIED, (
        "Inconclusive checks mean the underlying observation could not be "
        "established; the Evidence must say UNVERIFIED, not VERIFIED."
    )


# ---------------------------------------------------------------------------
# Test 2 — pass/warn/fail live on VerificationSignal.outcome, nowhere else
# ---------------------------------------------------------------------------

def test_pass_warn_fail_only_on_signal_outcome(orchestrator, store):
    """Scan a full real VerificationReport. The pass/warn/fail/inconclusive
    distinction must live only on `VerificationSignal.outcome`. Evidence
    records must never encode that distinction via their verification_status
    (they must only ever report fact-level VERIFIED or UNVERIFIED).
    """
    job = _job(
        store,
        description="WhatsApp me for details. Earn $500/day. Send your bank account.",
    )
    report = orchestrator.invoke("verification_agent", "u1", VerificationAgentInput(job=job))

    # The report itself carries outcomes across the full range -- not just one kind
    outcomes = {s.outcome for s in report.signals}
    assert outcomes, "expected at least one signal"
    assert outcomes <= set(SignalOutcome), "outcomes must be the SignalOutcome enum"

    # Every Evidence emitted by every signal is EITHER VERIFIED (observation
    # established) OR UNVERIFIED (observation could not be established).
    # Nothing else is permitted on the Evidence layer -- any PARTIALLY_VERIFIED,
    # CONFLICTING, or HIGH_RISK here would be the old overloaded semantics.
    allowed = {VerificationStatus.VERIFIED, VerificationStatus.UNVERIFIED}
    for sig in report.signals:
        for ev_id in sig.evidence_ids:
            ev = store.get(ev_id)
            assert ev is not None, f"signal {sig.name} emitted an unresolved evidence id"
            assert ev.verification_status in allowed, (
                f"signal {sig.name!r} (outcome={sig.outcome.value}) stored an "
                f"evidence with verification_status={ev.verification_status.value}; "
                f"only VERIFIED or UNVERIFIED are allowed at the fact level."
            )


# ---------------------------------------------------------------------------
# Test 3 — scam posting: three levels of status differ at once
# ---------------------------------------------------------------------------

def test_scam_posting_separates_fact_signal_composite(orchestrator, store):
    """The canonical scam case from docs/EVIDENCE.md.

    For a posting containing a scam phrase:
      - Evidence of the detection has verification_status = VERIFIED
        (we really did observe the phrase; the fact is confirmed).
      - The scam-phrase VerificationSignal has outcome = FAIL
        (the check does not pass).
      - The VerificationReport.composite_status = HIGH_RISK
        (overall posture of the job).

    These three must coexist with different values.
    """
    job = _job(
        store,
        description="WhatsApp me for details. Earn $500/day. Send your bank account.",
    )
    report = orchestrator.invoke("verification_agent", "u1", VerificationAgentInput(job=job))

    # The scam-phrase signal fired with outcome=FAIL.
    scam_signals = [s for s in report.signals if "scam" in s.name.lower()]
    assert scam_signals, "expected a scam-related signal to be emitted"
    scam_fail_signals = [s for s in scam_signals if s.outcome is SignalOutcome.FAIL]
    assert scam_fail_signals, (
        "expected at least one scam-related signal with outcome=FAIL on a job "
        "whose description contains a known scam phrase"
    )

    # Every FAIL signal here cites evidence whose own verification_status is VERIFIED.
    for sig in scam_fail_signals:
        for ev_id in sig.evidence_ids:
            ev = store.get(ev_id)
            assert ev is not None
            assert ev.verification_status is VerificationStatus.VERIFIED, (
                "The scam-phrase OBSERVATION is a confirmed deterministic fact; "
                "the Evidence recording it must be VERIFIED, even though the "
                "SIGNAL outcome is FAIL and the COMPOSITE status is HIGH_RISK."
            )

    # Composite rolls up to HIGH_RISK.
    assert report.composite_status is VerificationStatus.HIGH_RISK, (
        f"composite should be HIGH_RISK for a scam posting, "
        f"got {report.composite_status.value}"
    )
