from __future__ import annotations

import pytest

from app.agents import Orchestrator, VerificationAgent
from app.services.evidence_store import InMemoryEvidenceStore


@pytest.fixture
def store() -> InMemoryEvidenceStore:
    return InMemoryEvidenceStore()


@pytest.fixture
def orchestrator(store: InMemoryEvidenceStore) -> Orchestrator:
    orch = Orchestrator(store)
    orch.register(VerificationAgent())
    return orch


def make_job(**overrides):
    """Build a minimally-valid Job with placeholder evidence for tests."""
    from app.models.evidence import (
        ConfidenceLevel, Evidence, SourceType, VerificationStatus,
    )
    from app.models.job import Job

    def _mk(store, claim: str) -> str:
        return store.put(Evidence(
            source_url="https://boards.greenhouse.io/acme/jobs/1",
            source_type=SourceType.ATS_GREENHOUSE,
            claim=claim,
            excerpt=None,
            confidence=ConfidenceLevel.HIGH,
            verification_status=VerificationStatus.VERIFIED,
        ))

    # Note: tests build their own store when they need evidence to resolve.
    defaults = dict(
        dedup_key="acme::senior-ai-engineer::remote::2026-09",
        title="Senior AI Engineer",
        employer="Acme AI",
        employer_domain="acme.ai",
        application_url="https://boards.greenhouse.io/acme/jobs/1",
        source_url="https://boards.greenhouse.io/acme/jobs/1",
        location="Remote (US)",
        description="We are hiring a Senior AI Engineer to build production LLM systems.",
        title_evidence_ids=["placeholder-id-title"],
        employer_evidence_ids=["placeholder-id-employer"],
        application_url_evidence_ids=["placeholder-id-app-url"],
    )
    defaults.update(overrides)
    return Job(**defaults)
