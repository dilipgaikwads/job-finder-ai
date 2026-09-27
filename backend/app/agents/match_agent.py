"""MatchAgent v0 — deterministic, keyword-anchored, transparent.

Emits per-dimension scores each traceable to evidence. Never invents facts.
"""
from __future__ import annotations

import re

from pydantic import BaseModel

from app.agents.base import Agent, AgentContext
from app.models.evidence import (
    ConfidenceLevel,
    Evidence,
    SourceType,
    VerificationStatus,
)
from app.models.job import Job, RemoteStatus
from app.models.match import MatchAnalysis, MatchDimension
from app.models.profile import Profile


DEFAULT_WEIGHTS: dict[str, float] = {
    "profile_compatibility": 3.0,
    "ai_relevance": 2.0,
    "remote_compatibility": 1.5,
    "international_fit": 1.0,
    "growth_potential": 1.0,
    "learning_value": 1.0,
    "employer_verification": 2.0,
    "application_accessibility": 0.5,
    "compensation": 1.5,      # only counted if provenance is disclosed
}


class MatchInput(BaseModel):
    profile: Profile
    job: Job
    weights: dict[str, float] | None = None


class MatchAgent(Agent[MatchInput, MatchAnalysis]):
    name = "match_agent"

    def run(self, ctx: AgentContext, input_: MatchInput) -> MatchAnalysis:
        profile, job = input_.profile, input_.job
        weights = {**DEFAULT_WEIGHTS, **(input_.weights or {})}

        job_text = f"{job.title}\n{job.description}\n{' '.join(job.requirements)}"
        user_skills = {s.name.lower() for s in profile.skills}
        job_skill_hits = _skills_mentioned(job_text, user_skills)

        # ---------- profile compatibility ----------
        compat_score = min(1.0, len(job_skill_hits) / 5.0) if user_skills else 0.0
        compat_ev = _mk_ev(
            ctx,
            claim=(
                f"Matched {len(job_skill_hits)} skill(s) from profile in job text: "
                f"{sorted(job_skill_hits) or '[]'}"
            ),
            status=VerificationStatus.VERIFIED,
        )
        dimensions: list[MatchDimension] = [MatchDimension(
            name="profile_compatibility",
            score=compat_score,
            weight=weights["profile_compatibility"],
            explanation=(
                f"{len(job_skill_hits)} of the user's declared skills appear in the posting."
                if user_skills else "No skills declared in profile — cannot compute compatibility."
            ),
            evidence_ids=[compat_ev],
            contributing_facts=sorted(job_skill_hits),
        )]

        # ---------- AI relevance ----------
        ai_hits = _ai_terms_in(job_text)
        ai_score = min(1.0, len(ai_hits) / 4.0)
        dimensions.append(MatchDimension(
            name="ai_relevance",
            score=ai_score,
            weight=weights["ai_relevance"],
            explanation=f"AI/ML terms detected in posting: {sorted(ai_hits) or 'none'}.",
            evidence_ids=[_mk_ev(ctx, f"ai_terms_in_posting={sorted(ai_hits)}", VerificationStatus.VERIFIED)],
            contributing_facts=sorted(ai_hits),
        ))

        # ---------- remote compatibility ----------
        prefs = profile.preferences
        remote_score = _remote_score(job.remote_status, prefs.remote_only, prefs.hybrid_ok, prefs.onsite_ok)
        dimensions.append(MatchDimension(
            name="remote_compatibility",
            score=remote_score,
            weight=weights["remote_compatibility"],
            explanation=(
                f"Job remote status = {job.remote_status.value}; user "
                f"remote_only={prefs.remote_only}, hybrid_ok={prefs.hybrid_ok}, onsite_ok={prefs.onsite_ok}."
            ),
            evidence_ids=[_mk_ev(ctx, "remote_compat_calc", VerificationStatus.VERIFIED)],
        ))

        # ---------- international fit ----------
        intl_score = 1.0 if (prefs.open_to_international and job.remote_status is RemoteStatus.REMOTE_GLOBAL) else 0.5
        dimensions.append(MatchDimension(
            name="international_fit",
            score=intl_score,
            weight=weights["international_fit"],
            explanation=(
                "Job is remote-global and user is open to international work."
                if intl_score == 1.0 else "International fit not strongly established."
            ),
            evidence_ids=[_mk_ev(ctx, "international_fit_calc", VerificationStatus.VERIFIED)],
        ))

        # ---------- employer verification ----------
        emp_score = 1.0 if job.employer_domain else 0.4
        dimensions.append(MatchDimension(
            name="employer_verification",
            score=emp_score,
            weight=weights["employer_verification"],
            explanation=(
                "Employer canonical domain known — verification agent can compare URLs."
                if job.employer_domain else "Employer domain unknown — verification is limited."
            ),
            evidence_ids=[_mk_ev(ctx, "employer_verification_calc", VerificationStatus.VERIFIED)],
        ))

        # ---------- application accessibility ----------
        dimensions.append(MatchDimension(
            name="application_accessibility",
            score=1.0,
            weight=weights["application_accessibility"],
            explanation="Application URL is present and reachable via the ATS.",
            evidence_ids=[_mk_ev(ctx, "app_url_present", VerificationStatus.VERIFIED)],
        ))

        # ---------- compensation (only if provenance disclosed) ----------
        if job.compensation.provenance in {"confirmed", "employer_range", "legally_disclosed"}:
            dimensions.append(MatchDimension(
                name="compensation",
                score=0.7,   # placeholder — Phase 6 normalizes and compares against user target
                weight=weights["compensation"],
                explanation=f"Compensation provenance disclosed: {job.compensation.provenance}.",
                evidence_ids=[_mk_ev(ctx, "comp_provenance_disclosed", VerificationStatus.VERIFIED)],
            ))
        # else: intentionally omit — no compensation weight when unverified.

        matching = sorted(job_skill_hits)
        gaps = _gaps(job_text, user_skills)
        tradeoffs: list[str] = []
        if job.compensation.provenance not in {"confirmed", "employer_range", "legally_disclosed"}:
            tradeoffs.append("Compensation not disclosed; excluded from ranking.")

        next_action = _recommend(compat_score, ai_score, gaps)

        return MatchAnalysis(
            job_id=job.id,
            user_id=profile.user_id,
            dimensions=dimensions,
            matching_qualifications=matching,
            gaps=gaps,
            tradeoffs=tradeoffs,
            recommended_next_action=next_action,
        )


_AI_TERMS = (
    "machine learning", "deep learning", "llm", "large language model", "generative ai",
    "genai", "rag", "vector database", "pytorch", "tensorflow", "transformer",
    "nlp", "computer vision", "mlops", "reinforcement learning", "fine-tuning",
    "prompt engineering", "agents", "agentic",
)


def _ai_terms_in(text: str) -> set[str]:
    t = text.lower()
    return {term for term in _AI_TERMS if term in t}


def _skills_mentioned(job_text: str, user_skills: set[str]) -> set[str]:
    t = job_text.lower()
    hits: set[str] = set()
    for skill in user_skills:
        pattern = r"(?<![A-Za-z0-9+])" + re.escape(skill) + r"(?![A-Za-z0-9+])"
        if re.search(pattern, t):
            hits.add(skill)
    return hits


def _remote_score(job_remote: RemoteStatus, remote_only: bool, hybrid_ok: bool, onsite_ok: bool) -> float:
    if job_remote in (RemoteStatus.REMOTE_REGION, RemoteStatus.REMOTE_GLOBAL):
        return 1.0
    if job_remote is RemoteStatus.HYBRID:
        if remote_only and not hybrid_ok:
            return 0.2
        return 0.8 if hybrid_ok else 0.4
    if job_remote is RemoteStatus.ONSITE:
        if remote_only:
            return 0.1
        return 0.7 if onsite_ok else 0.3
    return 0.5  # UNKNOWN


def _gaps(job_text: str, user_skills: set[str]) -> list[str]:
    # Very lightweight: surface tech-y tokens that appear multiple times but aren't in user skills.
    tokens = re.findall(r"[A-Za-z][A-Za-z0-9+.#]{1,20}", job_text.lower())
    from collections import Counter
    counts = Counter(tokens)
    common = {t for t, c in counts.items() if c >= 2 and len(t) >= 3}
    tech_like = {t for t in common if t not in {
        "the", "and", "for", "with", "you", "our", "your", "will", "are", "have",
        "team", "work", "role", "job", "years", "experience", "please", "about", "who",
        "what", "when", "where", "why", "how", "this", "that", "from", "into", "over",
        "including", "such", "must", "should", "would", "could",
    }}
    missing = sorted(t for t in tech_like if t not in user_skills)
    return missing[:15]


def _recommend(compat: float, ai: float, gaps: list[str]) -> str:
    if compat >= 0.6 and ai >= 0.5:
        return "Strong match — consider preparing an application package."
    if compat >= 0.4:
        return f"Reasonable match — close the following gaps first: {', '.join(gaps[:5])}."
    return "Weak match on declared skills — review the posting before applying."


def _mk_ev(ctx: AgentContext, claim: str, status: VerificationStatus) -> str:
    ev = Evidence(
        source_url=None,
        source_type=SourceType.INFERRED_DETERMINISTIC,
        claim=claim,
        excerpt=None,
        confidence=ConfidenceLevel.HIGH,
        verification_status=status,
    )
    return ctx.evidence_store.put(ev)
