"""HTTP routes: resume upload, discovery + match + notify pipeline.

Auth model: `POST /resumes` is anonymous and returns `{user_id, token}`. Every
subsequent user-scoped route requires `Authorization: Bearer <token>` and the
path `user_id` must match the token's user. This prevents ULID-guessing from
mutating another user's profile or reading their notifications.
"""
from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, File, HTTPException, Request, UploadFile
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel, EmailStr, Field, ValidationError
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

_bearer_scheme = HTTPBearer(auto_error=False)


def require_user(user_id: str, request: Request,
                 creds: HTTPAuthorizationCredentials | None = Depends(_bearer_scheme)) -> str:
    """Verify the bearer token resolves to the same user_id in the path.

    Any mismatch — missing header, unknown token, wrong user — is a 401.
    Returns the resolved user_id (which equals the path user_id on success).
    """
    if creds is None or not creds.credentials:
        raise HTTPException(status_code=401, detail="missing_bearer_token")
    resolved = request.app.state.token_store.resolve(creds.credentials)
    if resolved is None or resolved != user_id:
        raise HTTPException(status_code=401, detail="invalid_or_mismatched_token")
    return resolved


class ResumeUploadResponse(BaseModel):
    user_id: str
    token: str            # keep this — required on all user-scoped endpoints
    detected_email: str | None
    detected_name: str | None
    skills: list[str]
    experience_count: int
    gaps: list[str]


@router.post("/resumes", response_model=ResumeUploadResponse)
async def upload_resume(request: Request, file: UploadFile = File(...)) -> ResumeUploadResponse:
    from app.services.resume_parser import UnsupportedResumeFormat, parse_resume

    filename = file.filename or "resume"

    # Stream-read with a running byte cap so an attacker cannot force the worker to
    # buffer a multi-gigabyte body just to hit the size-check-then-413 path.
    chunks: list[bytes] = []
    total = 0
    while True:
        chunk = await file.read(64 * 1024)
        if not chunk:
            break
        total += len(chunk)
        if total > MAX_RESUME_BYTES:
            raise HTTPException(status_code=413, detail=f"Resume exceeds {MAX_RESUME_BYTES} bytes.")
        chunks.append(chunk)
    if total == 0:
        raise HTTPException(status_code=400, detail="Empty upload.")
    data = b"".join(chunks)

    user_id = str(ULID())
    try:
        result = parse_resume(filename, data, user_id=user_id)
    except UnsupportedResumeFormat as e:
        raise HTTPException(status_code=415, detail=str(e))
    except ValidationError as e:
        # Extracted URL/email failed HttpUrl/EmailStr validation. Return a 4xx, not 500.
        raise HTTPException(status_code=422, detail={"parse_error": e.errors()})

    request.app.state.profile_store.put(result.profile)
    token = request.app.state.token_store.issue(user_id)

    return ResumeUploadResponse(
        user_id=user_id,
        token=token,
        detected_email=result.profile.email,
        detected_name=result.profile.full_name,
        skills=[s.name for s in result.profile.skills],
        experience_count=len(result.profile.experience),
        gaps=result.gaps,
    )


class ProfilePatch(BaseModel):
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
def patch_profile(user_id: str, patch: ProfilePatch, request: Request,
                  _: str = Depends(require_user)) -> dict[str, Any]:
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
    employer_slug: str = Field(min_length=1, max_length=100, pattern=r"^[A-Za-z0-9_-]+$")


class SearchRequest(BaseModel):
    targets: list[SearchTarget] = Field(min_length=1, max_length=25)
    top_n: int = Field(default=20, ge=1, le=100)
    notify: bool = True


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
def search_for_profile(user_id: str, req: SearchRequest, request: Request,
                       _: str = Depends(require_user)) -> SearchResponse:
    app_state = request.app.state
    profile = app_state.profile_store.get(user_id)
    if profile is None:
        raise HTTPException(status_code=404, detail="profile_not_found")

    orchestrator = app_state.orchestrator

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
def list_notifications(user_id: str, request: Request,
                       _: str = Depends(require_user)) -> dict[str, Any]:
    profile = request.app.state.profile_store.get(user_id)
    if profile is None:
        raise HTTPException(status_code=404, detail="profile_not_found")
    notifier = request.app.state.notifier
    sent = getattr(notifier, "sent", None)
    if sent is None:
        raise HTTPException(status_code=404, detail="notifier_not_inspectable")
    if not profile.email:
        return {"user_id": user_id, "notifications": []}
    return {"user_id": user_id, "notifications": [
        {"subject": p.subject, "job_id": p.job_id, "created_at": p.created_at.isoformat()}
        for p in sent if p.user_email.lower() == profile.email.lower()
    ]}
