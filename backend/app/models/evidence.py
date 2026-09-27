"""Evidence: every externally sourced fact in the system carries one of these.

See docs/EVIDENCE.md for the rules and invariants.
"""
from __future__ import annotations

from datetime import UTC, datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field, HttpUrl, field_validator
from ulid import ULID


class SourceType(str, Enum):
    OFFICIAL_CAREERS_PAGE = "official_careers_page"
    ATS_GREENHOUSE = "ats_greenhouse"
    ATS_LEVER = "ats_lever"
    ATS_WORKDAY = "ats_workday"
    AGGREGATOR = "aggregator"
    RECRUITER_MESSAGE = "recruiter_message"
    USER_SUPPLIED = "user_supplied"
    WHOIS = "whois"
    INFERRED_DETERMINISTIC = "inferred_deterministic"


OFFICIAL_SOURCE_TYPES: frozenset[SourceType] = frozenset({
    SourceType.OFFICIAL_CAREERS_PAGE,
    SourceType.ATS_GREENHOUSE,
    SourceType.ATS_LEVER,
    SourceType.ATS_WORKDAY,
})


class ConfidenceLevel(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class VerificationStatus(str, Enum):
    VERIFIED = "verified"
    PARTIALLY_VERIFIED = "partially_verified"
    UNVERIFIED = "unverified"
    CONFLICTING = "conflicting"
    HIGH_RISK = "high_risk"


class Evidence(BaseModel):
    id: str = Field(default_factory=lambda: str(ULID()))
    source_url: HttpUrl | None  # None only when source_type is inferred_deterministic or user_supplied
    source_type: SourceType
    retrieved_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    claim: str = Field(min_length=1, max_length=500)
    excerpt: str | None = Field(default=None, max_length=500)
    structured: dict[str, Any] | None = None
    confidence: ConfidenceLevel
    verification_status: VerificationStatus
    conflicts: list[str] = Field(default_factory=list)

    @field_validator("source_url", mode="before")
    @classmethod
    def _require_url_for_web_sources(cls, v, info):
        # Enforced in model_validator to have access to source_type
        return v

    def model_post_init(self, __context) -> None:
        web_sources = {
            SourceType.OFFICIAL_CAREERS_PAGE,
            SourceType.ATS_GREENHOUSE,
            SourceType.ATS_LEVER,
            SourceType.ATS_WORKDAY,
            SourceType.AGGREGATOR,
            SourceType.WHOIS,
        }
        if self.source_type in web_sources and self.source_url is None:
            raise ValueError(
                f"source_url is required for source_type={self.source_type.value}"
            )

    @property
    def is_official(self) -> bool:
        return self.source_type in OFFICIAL_SOURCE_TYPES
