"""DiscoveryAgent: fan out across adapters, dedupe, store evidence, wire ids."""
from __future__ import annotations

from pydantic import BaseModel, Field

from app.agents.base import Agent, AgentContext
from app.models.job import Job

from .base import DiscoveryAdapter


class DiscoveryTarget(BaseModel):
    adapter: str        # "greenhouse" | "lever"
    employer_slug: str


class DiscoveryInput(BaseModel):
    targets: list[DiscoveryTarget]


class DiscoveryOutput(BaseModel):
    jobs: list[Job] = Field(default_factory=list)
    errors: list[str] = Field(default_factory=list)


class DiscoveryAgent(Agent[DiscoveryInput, DiscoveryOutput]):
    name = "discovery_agent"

    def __init__(self, adapters: dict[str, DiscoveryAdapter]) -> None:
        self._adapters = adapters

    def run(self, ctx: AgentContext, input_: DiscoveryInput) -> DiscoveryOutput:
        out = DiscoveryOutput()
        seen_dedup: set[str] = set()
        for tgt in input_.targets:
            adapter = self._adapters.get(tgt.adapter)
            if adapter is None:
                out.errors.append(f"unknown_adapter:{tgt.adapter}")
                continue
            try:
                postings = adapter.fetch(tgt.employer_slug)
            except Exception as e:  # noqa: BLE001
                out.errors.append(f"{tgt.adapter}:{tgt.employer_slug}:{type(e).__name__}")
                continue
            for rp in postings:
                if rp.job.dedup_key in seen_dedup:
                    continue
                seen_dedup.add(rp.job.dedup_key)
                for ev in rp.evidence:
                    ctx.evidence_store.put(ev)
                out.jobs.append(rp.job)
        return out
