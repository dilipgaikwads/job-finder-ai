"""VerificationReport: per-signal + composite status. Never claims certainty without evidence."""
from __future__ import annotations

from enum import Enum
from typing import Literal

from pydantic import BaseModel, Field

from .evidence import VerificationStatus


class SignalOutcome(str, Enum):
    PASS = "pass"
    WARN = "warn"
    FAIL = "fail"
    INCONCLUSIVE = "inconclusive"


class VerificationSignal(BaseModel):
    name: str
    outcome: SignalOutcome
    weight: float = 1.0                # relative weight in composite
    explanation: str                   # factual, non-defamatory
    evidence_ids: list[str] = Field(default_factory=list)


class VerificationReport(BaseModel):
    job_id: str
    signals: list[VerificationSignal] = Field(default_factory=list)
    composite_status: VerificationStatus
    summary: str
    risk_flags: list[str] = Field(default_factory=list)   # e.g., "application_domain_mismatch"

    def has_fail(self) -> bool:
        return any(s.outcome is SignalOutcome.FAIL for s in self.signals)
