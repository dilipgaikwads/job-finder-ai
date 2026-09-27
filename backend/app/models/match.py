"""MatchAnalysis: transparent per-dimension breakdown. No hidden scalar score."""
from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

DimensionName = Literal[
    "profile_compatibility",
    "compensation",
    "ai_relevance",
    "remote_compatibility",
    "international_fit",
    "growth_potential",
    "learning_value",
    "employer_verification",
    "application_accessibility",
]


class MatchDimension(BaseModel):
    name: DimensionName
    score: float = Field(ge=0.0, le=1.0)     # 0..1
    weight: float = Field(ge=0.0)
    explanation: str
    evidence_ids: list[str] = Field(default_factory=list)
    contributing_facts: list[str] = Field(default_factory=list)


class MatchAnalysis(BaseModel):
    job_id: str
    user_id: str
    dimensions: list[MatchDimension]
    matching_qualifications: list[str] = Field(default_factory=list)
    gaps: list[str] = Field(default_factory=list)
    tradeoffs: list[str] = Field(default_factory=list)
    recommended_next_action: str

    def composite(self) -> float:
        total_w = sum(d.weight for d in self.dimensions) or 1.0
        return round(sum(d.score * d.weight for d in self.dimensions) / total_w, 3)
