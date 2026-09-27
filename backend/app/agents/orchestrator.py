"""Orchestrator: enforces evidence propagation and authorization boundaries.

Phase 1–3 scope: registration, invocation, and evidence-integrity check.
Future: task graph, retries, streaming, LLM adapter injection.
"""
from __future__ import annotations

from typing import Any

from pydantic import BaseModel

from app.services.evidence_store import EvidenceStore

from .base import Agent, AgentContext, AgentError


class OrchestratorPolicy(BaseModel):
    require_evidence_resolution: bool = True   # every emitted evidence_id must resolve in the store
    max_agent_seconds: float = 30.0


class Orchestrator:
    def __init__(self, evidence_store: EvidenceStore, policy: OrchestratorPolicy | None = None) -> None:
        self.evidence_store = evidence_store
        self.policy = policy or OrchestratorPolicy()
        self._agents: dict[str, Agent[Any, Any]] = {}

    def register(self, agent: Agent[Any, Any]) -> None:
        if agent.name in self._agents:
            raise AgentError(f"Agent already registered: {agent.name}")
        self._agents[agent.name] = agent

    def get(self, name: str) -> Agent[Any, Any]:
        try:
            return self._agents[name]
        except KeyError as e:
            raise AgentError(f"Unknown agent: {name}") from e

    def invoke(self, agent_name: str, user_id: str, payload: BaseModel) -> BaseModel:
        agent = self.get(agent_name)
        ctx = AgentContext(user_id=user_id, evidence_store=self.evidence_store)
        result = agent.run(ctx, payload)
        if self.policy.require_evidence_resolution:
            self._check_evidence_resolution(agent_name, result)
        return result

    def _check_evidence_resolution(self, agent_name: str, out: BaseModel) -> None:
        """Any evidence_id emitted by an agent MUST resolve in the store.

        Prevents Agent A's inferences from becoming Agent B's untraceable 'facts'.
        """
        ids = _collect_evidence_ids(out.model_dump())
        missing = self.evidence_store.missing(list(ids))
        if missing:
            raise AgentError(
                f"Agent '{agent_name}' emitted unresolved evidence ids: {missing[:5]}"
                + (" (+more)" if len(missing) > 5 else "")
            )


def _collect_evidence_ids(obj: Any) -> set[str]:
    ids: set[str] = set()
    if isinstance(obj, dict):
        for k, v in obj.items():
            if k == "evidence_ids" and isinstance(v, list) or k.endswith("_evidence_ids") and isinstance(v, list):
                ids.update(str(x) for x in v)
            else:
                ids.update(_collect_evidence_ids(v))
    elif isinstance(obj, list):
        for item in obj:
            ids.update(_collect_evidence_ids(item))
    return ids
