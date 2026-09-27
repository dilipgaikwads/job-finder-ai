"""Job posting model. Every non-user-supplied fact carries evidence_ids."""
from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Literal

from pydantic import BaseModel, Field, HttpUrl, model_validator
from ulid import ULID

from .evidence import VerificationStatus


class RemoteStatus(str, Enum):
    ONSITE = "onsite"
    HYBRID = "hybrid"
    REMOTE_REGION = "remote_region"       # remote within a country/region
    REMOTE_GLOBAL = "remote_global"
    UNKNOWN = "unknown"


class CompensationComponent(BaseModel):
    kind: Literal["base", "bonus", "equity", "signing", "total"]
    currency: str  # ISO 4217
    amount_min: float | None = None
    amount_max: float | None = None
    period: Literal["year", "month", "hour"] = "year"
    evidence_ids: list[str] = Field(default_factory=list)


class CompensationBreakdown(BaseModel):
    provenance: Literal[
        "confirmed", "employer_range", "legally_disclosed",
        "third_party_estimate", "inferred", "unknown"
    ]
    components: list[CompensationComponent] = Field(default_factory=list)
    evidence_ids: list[str] = Field(default_factory=list)
    verification_status: VerificationStatus = VerificationStatus.UNVERIFIED


class Job(BaseModel):
    id: str = Field(default_factory=lambda: str(ULID()))
    dedup_key: str  # employer_slug + normalized_title + location_key + posted_bucket
    title: str
    employer: str
    employer_domain: str | None = None            # canonical, lower-cased
    application_url: HttpUrl                       # required — must know where to apply
    source_url: HttpUrl                            # where we discovered the posting
    location: str | None = None
    remote_status: RemoteStatus = RemoteStatus.UNKNOWN
    employment_type: Literal["full_time", "part_time", "contract", "intern", "unknown"] = "unknown"
    posted_at: datetime | None = None
    deadline_at: datetime | None = None
    description: str
    requirements: list[str] = Field(default_factory=list)
    preferred: list[str] = Field(default_factory=list)
    tech_stack: list[str] = Field(default_factory=list)
    compensation: CompensationBreakdown = Field(default_factory=lambda: CompensationBreakdown(provenance="unknown"))
    visa_sponsorship_disclosed: bool | None = None  # None = unknown (never guess Yes)

    # Evidence attribution for every non-user-supplied factual field.
    title_evidence_ids: list[str] = Field(default_factory=list)
    employer_evidence_ids: list[str] = Field(default_factory=list)
    application_url_evidence_ids: list[str] = Field(default_factory=list)
    location_evidence_ids: list[str] = Field(default_factory=list)
    remote_evidence_ids: list[str] = Field(default_factory=list)
    requirements_evidence_ids: list[str] = Field(default_factory=list)
    visa_evidence_ids: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def _require_evidence_for_core_facts(self):
        for field in ("title_evidence_ids", "employer_evidence_ids", "application_url_evidence_ids"):
            if not getattr(self, field):
                raise ValueError(f"Job.{field} must reference at least one Evidence.id")
        return self

    def all_evidence_ids(self) -> set[str]:
        ids: set[str] = set()
        for field in (
            self.title_evidence_ids, self.employer_evidence_ids,
            self.application_url_evidence_ids, self.location_evidence_ids,
            self.remote_evidence_ids, self.requirements_evidence_ids,
            self.visa_evidence_ids,
        ):
            ids.update(field)
        for c in self.compensation.components:
            ids.update(c.evidence_ids)
        ids.update(self.compensation.evidence_ids)
        return ids
