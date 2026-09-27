"""FastAPI app wiring: evidence store, orchestrator, one working endpoint.

Run:
    uvicorn app.main:app --reload
"""
from __future__ import annotations

from fastapi import FastAPI, HTTPException

from app.agents import Orchestrator, VerificationAgent
from app.agents.verification_agent import VerificationAgentInput
from app.models.job import Job
from app.models.verification import VerificationReport
from app.services.evidence_store import InMemoryEvidenceStore


def create_app() -> FastAPI:
    app = FastAPI(
        title="Job Finder AI — Backend",
        version="0.1.0",
        description="Evidence-first multi-agent career platform.",
    )

    store = InMemoryEvidenceStore()
    orchestrator = Orchestrator(store)
    orchestrator.register(VerificationAgent())

    app.state.evidence_store = store
    app.state.orchestrator = orchestrator

    @app.get("/health")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    @app.post("/jobs/verify", response_model=VerificationReport)
    def verify_job(job: Job) -> VerificationReport:
        try:
            report = orchestrator.invoke(
                "verification_agent",
                user_id="anonymous",   # replaced by auth in Phase 4
                payload=VerificationAgentInput(job=job),
            )
        except Exception as e:  # narrow later
            raise HTTPException(status_code=400, detail=str(e))
        return report  # type: ignore[return-value]

    return app


app = create_app()
