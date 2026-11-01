"""FastAPI application wiring and local web dashboard."""
from __future__ import annotations

import os
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.agents import Orchestrator, VerificationAgent
from app.agents.discovery import DiscoveryAgent, GreenhouseAdapter, LeverAdapter
from app.agents.match_agent import MatchAgent
from app.agents.verification_agent import VerificationAgentInput
from app.api.routes import router as api_router
from app.models.job import Job
from app.models.verification import VerificationReport
from app.services.auth_tokens import InMemoryTokenStore
from app.services.evidence_store import InMemoryEvidenceStore
from app.services.notifications import LogNotifier, SMTPNotifier
from app.services.profile_store import InMemoryProfileStore


def create_app() -> FastAPI:
    app = FastAPI(
        title="Job Finder AI",
        version="0.3.0",
        description=(
            "Evidence-first career workspace: resume upload, official-source job discovery, "
            "verification, matching and notifications."
        ),
    )

    static_dir = Path(__file__).resolve().parent / "static"
    app.mount("/static", StaticFiles(directory=static_dir), name="static")

    @app.get("/", include_in_schema=False)
    def home() -> FileResponse:
        return FileResponse(static_dir / "index.html")

    store = InMemoryEvidenceStore()
    profile_store = InMemoryProfileStore()

    greenhouse = GreenhouseAdapter()
    lever = LeverAdapter()
    discovery = DiscoveryAgent(adapters={"greenhouse": greenhouse, "lever": lever})
    verification = VerificationAgent()
    matcher = MatchAgent()

    orch = Orchestrator(store)
    orch.register(discovery)
    orch.register(verification)
    orch.register(matcher)

    # SMTP is optional. Without SMTP_HOST, notifications are safely logged locally.
    notifier = SMTPNotifier() if os.environ.get("SMTP_HOST") else LogNotifier()

    app.state.evidence_store = store
    app.state.profile_store = profile_store
    app.state.token_store = InMemoryTokenStore()
    app.state.orchestrator = orch
    app.state.agents = {
        "discovery_agent": discovery,
        "verification_agent": verification,
        "match_agent": matcher,
    }
    app.state.notifier = notifier

    @app.get("/health")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    @app.post("/jobs/verify", response_model=VerificationReport)
    def verify_job(job: Job) -> VerificationReport:
        try:
            report = orch.invoke(
                "verification_agent",
                user_id="anonymous",
                payload=VerificationAgentInput(job=job),
            )
        except Exception as e:
            raise HTTPException(status_code=400, detail=str(e))
        return report

    app.include_router(api_router)
    return app


app = create_app()
