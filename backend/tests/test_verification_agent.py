"""End-to-end verification agent tests (Phase 3)."""
from __future__ import annotations

import pytest

from app.agents.verification_agent import VerificationAgentInput
from app.models.evidence import (
    ConfidenceLevel,
    Evidence,
    SourceType,
    VerificationStatus,
)
from app.models.job import CompensationBreakdown, CompensationComponent, Job
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
        dedup_key="acme::senior-ai-engineer::remote::2026-09",
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


def test_legitimate_ats_posting_passes(orchestrator, store):
    job = _job(store, compensation=CompensationBreakdown(provenance="employer_range"))
    report = orchestrator.invoke("verification_agent", "u1", VerificationAgentInput(job=job))
    assert report.composite_status.value in {"verified", "partially_verified"}
    assert not report.has_fail()
    # Every signal carries evidence
    assert all(s.evidence_ids for s in report.signals)


def test_application_domain_mismatch_flags_risk(orchestrator, store):
    job = _job(
        store,
        application_url="https://acme-hr-portal-secure-verify.com/apply/1",
    )
    report = orchestrator.invoke("verification_agent", "u1", VerificationAgentInput(job=job))
    assert "application_domain_mismatch" in report.risk_flags
    assert report.has_fail()


def test_upfront_payment_detected_high_risk(orchestrator, store):
    job = _job(
        store,
        description="Great opportunity! Pay a small training fee to get started.",
    )
    report = orchestrator.invoke("verification_agent", "u1", VerificationAgentInput(job=job))
    assert "upfront_payment_request" in report.risk_flags
    assert report.composite_status.value == "high_risk"


def test_scam_phrases_detected(orchestrator, store):
    job = _job(
        store,
        description="WhatsApp me for details. Earn $500/day. Send your bank account.",
    )
    report = orchestrator.invoke("verification_agent", "u1", VerificationAgentInput(job=job))
    assert "scam_phrase_detected" in report.risk_flags


def test_orchestrator_rejects_unresolved_evidence(store, orchestrator):
    from app.agents.base import Agent, AgentContext, AgentError
    from app.models.verification import VerificationReport, VerificationSignal
    from pydantic import BaseModel

    class RogueInput(BaseModel):
        job_id: str

    class RogueAgent(Agent[RogueInput, VerificationReport]):
        name = "rogue"

        def run(self, ctx: AgentContext, input_: RogueInput) -> VerificationReport:
            return VerificationReport(
                job_id=input_.job_id,
                signals=[VerificationSignal(
                    name="fake", outcome=SignalOutcome.PASS,
                    explanation="fabricated", evidence_ids=["nonexistent-id"],
                )],
                composite_status=VerificationStatus.VERIFIED,
                summary="",
            )

    orchestrator.register(RogueAgent())
    with pytest.raises(AgentError):
        orchestrator.invoke("rogue", "u1", RogueInput(job_id="j1"))
