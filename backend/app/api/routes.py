"""HTTP routes: resume upload, discovery + match + notify pipeline."""
from __future__ import annotations

from typing import Any

from fastapi import APIRouter, File, HTTPException, Request, UploadFile
from pydantic import BaseModel, EmailStr, Field
from ulid import ULID

from app.agents.discovery import DiscoveryAgent, DiscoveryInput
from app.agents.discovery.discovery_agent import DiscoveryTarget
from app.agents.match_agent import MatchAgent, MatchInput
from app.agents.verification_agent import VerificationAgent, VerificationAgentInput
from app.models.job import Job
from app.services.notifications import build_payload

# Upload cap: fits typical resumes; guards against ingest DoS.
MAX_RESUME_BYTES = 4 * 1024 * 1024  # 4 MB


router = APIRouter()


class ResumeUploadResponse(BaseModel):
    user_id: str
    detected_email: str | None
    detected_name: str | None
    skills: list[str]
    experience_count: int
    gaps: list[str]      # questions the parser needs the user to answer


@router.post("/resumes", response_model=ResumeUploadResponse)
async def upload_resume(request: Request, file: UploadFile = File(...)) -> ResumeUploadResponse:
    from app.services.resume_parser import parse_resume, UnsupportedResumeFormat

    filename = file.filename or "resume"
    data = await file.read()
    if len(data) > MAX_RESUME_BYTES:
        raise HTTPException(status_code=413, detail=f"Resume exceeds {MAX_RESUME_BYTES} bytes.")
    if len(data) == 0:
        raise HTTPException(status_code=400, detail="Empty upload.")

    user_id = str(ULID())
    try:
        result = parse_resume(filename, data, user_id=user_id)
    except UnsupportedResumeFormat as e:
        raise HTTPException(status_code=415, detail=str(e))

    request.app.state.profile_store.put(result.profile)

    return ResumeUploadResponse(
        user_id=user_id,
        detected_email=result.profile.email,
        detected_name=result.profile.full_name,
        skills=[s.name for s in result.profile.skills],
        experience_count=len(result.profile.experience),
        gaps=result.gaps,
    )


class ProfilePatch(BaseModel):
    """Fields the user can confirm/patch after upload. Nothing is invented server-side."""
    full_name: str | None = None
    email: EmailStr | None = None
    remote_only: bool | None = None
    hybrid_ok: bool | None = None
    onsite_ok: bool | None = None
    open_to_international: bool | None = None
    open_to_relocation: bool | None = None
    min_base_salary_usd: float | None = None
    target_base_salary_usd: float | None = None
    role_interests: list[str] | None = None


@router.patch("/profiles/{user_id}")
def patch_profile(user_id: str, patch: ProfilePatch, request: Request) -> dict[str, Any]:
    store = request.app.state.profile_store
    profile = store.get(user_id)
    if profile is None:
        raise HTTPException(status_code=404, detail="profile_not_found")
    if patch.full_name is not None:
        profile.full_name = patch.full_name
    if patch.email is not None:
        profile.email = patch.email
    prefs = profile.preferences
    for f in ("remote_only", "hybrid_ok", "onsite_ok", "open_to_international",
              "open_to_relocation", "min_base_salary_usd", "target_base_salary_usd",
              "role_interests"):
        v = getattr(patch, f)
        if v is not None:
            setattr(prefs, f, v)
    store.put(profile)
    return {"ok": True, "user_id": user_id}


class SearchTarget(BaseModel):
    adapter: str = Field(pattern=r"^(greenhouse|lever)$")
    employer_slug: str


class SearchRequest(BaseModel):
    targets: list[SearchTarget]
    top_n: int = 20
    notify: bool = True         # send an email if the user's profile has one and matches pass verification


class SearchResultItem(BaseModel):
    job: Job
    verification_status: str
    composite_match: float
    match_summary: str
    application_url: str
    risk_flags: list[str]


class SearchResponse(BaseModel):
    user_id: str
    total_discovered: int
    returned: int
    filtered_out_high_risk: int
    notifications_sent: int
    items: list[SearchResultItem]
    errors: list[str]


@router.post("/profiles/{user_id}/search", response_model=SearchResponse)
def search_for_profile(user_id: str, req: SearchRequest, request: Request) -> SearchResponse:
    app_state = request.app.state
    profile = app_state.profile_store.get(user_id)
    if profile is None:
        raise HTTPException(status_code=404, detail="profile_not_found")

    orchestrator = app_state.orchestrator
    discovery: DiscoveryAgent = app_state.agents["discovery_agent"]  # type: ignore[assignment]
    verifier: VerificationAgent = app_state.agents["verification_agent"]  # type: ignore[assignment]
    matcher: MatchAgent = app_state.agents["match_agent"]  # type: ignore[assignment]

    disc_out = orchestrator.invoke(
        "discovery_agent", user_id,
        DiscoveryInput(targets=[DiscoveryTarget(**t.model_dump()) for t in req.targets]),
    )

    scored: list[tuple[Job, Any, Any]] = []
    filtered_high_risk = 0
    for job in disc_out.jobs:
        vr = orchestrator.invoke("verification_agent", user_id, VerificationAgentInput(job=job))
        if vr.composite_status.value == "high_risk":
            filtered_high_risk += 1
            continue
        ma = orchestrator.invoke("match_agent", user_id, MatchInput(profile=profile, job=job))
        scored.append((job, vr, ma))

    scored.sort(key=lambda t: t[2].composite(), reverse=True)
    scored = scored[: req.top_n]

    notifications_sent = 0
    if req.notify and profile.email:
        notifier = app_state.notifier
        for job, vr, ma in scored:
            if vr.composite_status.value in {"verified", "partially_verified"}:
                payload = build_payload(profile.email, job, vr, ma)
                if notifier.send(payload):
                    notifications_sent += 1

    items = [SearchResultItem(
        job=j,
        verification_status=v.composite_status.value,
        composite_match=m.composite(),
        match_summary=m.recommended_next_action,
        application_url=str(j.application_url),
        risk_flags=v.risk_flags,
    ) for j, v, m in scored]

    return SearchResponse(
        user_id=user_id,
        total_discovered=len(disc_out.jobs),
        returned=len(items),
        filtered_out_high_risk=filtered_high_risk,
        notifications_sent=notifications_sent,
        items=items,
        errors=disc_out.errors,
    )


@router.get("/notifications/{user_id}")
def list_notifications(user_id: str, request: Request) -> dict[str, Any]:
    """Dev-only inspection endpoint when using LogNotifier."""
    notifier = request.app.state.notifier
    sent = getattr(notifier, "sent", None)
    if sent is None:
        raise HTTPException(status_code=404, detail="notifier_not_inspectable")
    return {"user_id": user_id, "notifications": [
        {"subject": p.subject, "job_id": p.job_id, "created_at": p.created_at.isoformat()}
        for p in sent if p.user_email  # simple filter placeholder
    ]}
