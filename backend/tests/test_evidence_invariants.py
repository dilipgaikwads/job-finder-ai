"""Property tests for evidence invariants (Phase 2)."""
from __future__ import annotations

import pytest
from pydantic import ValidationError

from app.models.evidence import (
    ConfidenceLevel,
    Evidence,
    SourceType,
    VerificationStatus,
)
from app.models.job import CompensationBreakdown, Job


def test_evidence_requires_url_for_web_sources():
    with pytest.raises(ValueError):
        Evidence(
            source_url=None,
            source_type=SourceType.ATS_GREENHOUSE,
            claim="Job exists",
            excerpt=None,
            confidence=ConfidenceLevel.HIGH,
            verification_status=VerificationStatus.VERIFIED,
        )


def test_evidence_allows_no_url_for_deterministic_inference():
    ev = Evidence(
        source_url=None,
        source_type=SourceType.INFERRED_DETERMINISTIC,
        claim="Application domain does not match employer domain",
        excerpt=None,
        confidence=ConfidenceLevel.HIGH,
        verification_status=VerificationStatus.HIGH_RISK,
    )
    assert ev.source_type is SourceType.INFERRED_DETERMINISTIC


def test_job_requires_evidence_for_core_fields():
    with pytest.raises(ValidationError):
        Job(
            dedup_key="x",
            title="Engineer",
            employer="Acme",
            application_url="https://acme.example/careers/1",
            source_url="https://acme.example/careers/1",
            description="desc",
            compensation=CompensationBreakdown(provenance="unknown"),
            # missing all *_evidence_ids
        )


def test_job_all_evidence_ids_aggregates():
    j = Job(
        dedup_key="x",
        title="Engineer",
        employer="Acme",
        employer_domain="acme.example",
        application_url="https://acme.example/careers/1",
        source_url="https://acme.example/careers/1",
        description="desc",
        title_evidence_ids=["a"],
        employer_evidence_ids=["b"],
        application_url_evidence_ids=["c"],
        requirements_evidence_ids=["d"],
    )
    assert {"a", "b", "c", "d"}.issubset(j.all_evidence_ids())
