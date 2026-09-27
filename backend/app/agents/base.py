"""Agent base contract. Every specialized agent inherits from this."""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Generic, TypeVar

from pydantic import BaseModel

from app.services.evidence_store import EvidenceStore


class AgentError(Exception):
    """Raised when an agent cannot fulfill its contract (missing input, evidence, etc.)."""


TIn = TypeVar("TIn", bound=BaseModel)
TOut = TypeVar("TOut", bound=BaseModel)


@dataclass
class AgentContext:
    user_id: str
    evidence_store: EvidenceStore
    # In real deployment: request_id, trace_id, autonomy_mode, feature flags, LLM adapter, etc.


class Agent(ABC, Generic[TIn, TOut]):
    """Typed I/O agent. The orchestrator invokes `run` and validates output evidence."""

    name: str = "unnamed_agent"

    @abstractmethod
    def run(self, ctx: AgentContext, input_: TIn) -> TOut:
        ...
