from __future__ import annotations

from app.agents.base import AgentContext
from app.agents.match_agent import MatchAgent, MatchInput
from app.models.evidence import ConfidenceLevel, Evidence, SourceType, VerificationStatus
from app.models.job import CompensationBreakdown, Job, RemoteStatus
from app.models.profile import Preferences, Profile, Skill
from app.services.evidence_store import InMemoryEvidenceStore


def _job(store: InMemoryEvidenceStore, description: str, remote: RemoteStatus = RemoteStatus.REMOTE_REGION) -> Job:
    def mk() -> str:
        return store.put(Evidence(
            source_url="https://boards.greenhouse.io/acme/jobs/1",
            source_type=SourceType.ATS_GREENHOUSE,
            claim="posting",
            excerpt=None,
            confidence=ConfidenceLevel.HIGH,
            verification_status=VerificationStatus.VERIFIED,
        ))
    return Job(
        dedup_key="acme::x::remote::2026-09",
        title="Senior AI Engineer",
        employer="Acme AI",
        employer_domain="acme.ai",
        application_url="https://boards.greenhouse.io/acme/jobs/1",
        source_url="https://boards.greenhouse.io/acme/jobs/1",
        location="Remote",
        remote_status=remote,
        description=description,
        compensation=CompensationBreakdown(provenance="unknown"),
        title_evidence_ids=[mk()],
        employer_evidence_ids=[mk()],
        application_url_evidence_ids=[mk()],
    )


def _profile(remote_only: bool = True) -> Profile:
    return Profile(
        user_id="u1",
        full_name="Jane",
        skills=[Skill(name=n, source="user_supplied") for n in
                ("python", "pytorch", "llm", "rag", "postgresql", "docker")],
        preferences=Preferences(remote_only=remote_only, hybrid_ok=False, onsite_ok=False),
    )


def test_match_composes_with_evidence():
    store = InMemoryEvidenceStore()
    ctx = AgentContext(user_id="u1", evidence_store=store)
    job = _job(store, "Build LLM systems with Python, PyTorch. RAG a plus. Docker experience.")
    result = MatchAgent().run(ctx, MatchInput(profile=_profile(), job=job))
    # All dimensions carry evidence ids that resolve
    for d in result.dimensions:
        for eid in d.evidence_ids:
            assert store.get(eid) is not None
    # AI relevance should be strong given LLM/RAG in description
    ai = next(d for d in result.dimensions if d.name == "ai_relevance")
    assert ai.score > 0.5
    # Skill hits populated
    compat = next(d for d in result.dimensions if d.name == "profile_compatibility")
    assert compat.score > 0.4
    assert "python" in result.matching_qualifications


def test_match_penalizes_onsite_for_remote_only_user():
    store = InMemoryEvidenceStore()
    ctx = AgentContext(user_id="u1", evidence_store=store)
    job = _job(store, "Python role, LLM", remote=RemoteStatus.ONSITE)
    result = MatchAgent().run(ctx, MatchInput(profile=_profile(remote_only=True), job=job))
    remote_dim = next(d for d in result.dimensions if d.name == "remote_compatibility")
    assert remote_dim.score <= 0.2


def test_match_omits_compensation_when_undisclosed():
    store = InMemoryEvidenceStore()
    ctx = AgentContext(user_id="u1", evidence_store=store)
    job = _job(store, "python role")
    result = MatchAgent().run(ctx, MatchInput(profile=_profile(), job=job))
    assert not any(d.name == "compensation" for d in result.dimensions)
    assert any("Compensation not disclosed" in t for t in result.tradeoffs)
