"""Discovery adapter contract. One adapter per legitimate job source."""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field

from app.models.evidence import Evidence
from app.models.job import Job


@dataclass
class RawPosting:
    job: Job
    evidence: list[Evidence] = field(default_factory=list)  # NOT yet in the store; caller stores + wires


class DiscoveryAdapter(ABC):
    name: str = "unnamed_adapter"

    @abstractmethod
    def fetch(self, employer_slug: str) -> list[RawPosting]:
        """Fetch postings for a single employer on this source. Deterministic — no LLM."""
