"""EvidenceStore abstracts durable evidence storage.

In-memory implementation for tests and Phase 1–3. Swap for Postgres later.
"""
from __future__ import annotations

from typing import Protocol

from app.models.evidence import Evidence


class EvidenceStore(Protocol):
    def put(self, evidence: Evidence) -> str: ...
    def get(self, evidence_id: str) -> Evidence | None: ...
    def get_many(self, evidence_ids: list[str]) -> list[Evidence]: ...
    def missing(self, evidence_ids: list[str]) -> list[str]: ...


class InMemoryEvidenceStore:
    def __init__(self) -> None:
        self._by_id: dict[str, Evidence] = {}

    def put(self, evidence: Evidence) -> str:
        self._by_id[evidence.id] = evidence
        return evidence.id

    def get(self, evidence_id: str) -> Evidence | None:
        return self._by_id.get(evidence_id)

    def get_many(self, evidence_ids: list[str]) -> list[Evidence]:
        return [e for eid in evidence_ids if (e := self._by_id.get(eid)) is not None]

    def missing(self, evidence_ids: list[str]) -> list[str]:
        return [eid for eid in evidence_ids if eid not in self._by_id]
