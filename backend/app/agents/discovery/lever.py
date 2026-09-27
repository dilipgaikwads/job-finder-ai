"""Lever public postings adapter.

Public API: https://api.lever.co/v0/postings/{site}?mode=json
No auth required for public postings.
"""
from __future__ import annotations

import re
from datetime import UTC, datetime

import httpx

from app.core.domains import registrable_domain
from app.models.evidence import ConfidenceLevel, Evidence, SourceType, VerificationStatus
from app.models.job import CompensationBreakdown, Job, RemoteStatus

from .base import DiscoveryAdapter, RawPosting

_LEVER_API = "https://api.lever.co/v0/postings/{site}"


class LeverAdapter(DiscoveryAdapter):
    name = "lever"

    def __init__(self, client: httpx.Client | None = None, timeout: float = 15.0) -> None:
        self._client = client or httpx.Client(timeout=timeout, headers={
            "User-Agent": "job-finder-ai/0.1 (+https://github.com/dilipgaikwads/job-finder-ai)"
        })
        self._own_client = client is None

    def close(self) -> None:
        if self._own_client:
            self._client.close()

    def fetch(self, employer_slug: str) -> list[RawPosting]:
        url = _LEVER_API.format(site=employer_slug)
        try:
            resp = self._client.get(url, params={"mode": "json"})
            resp.raise_for_status()
        except httpx.HTTPError:
            return []
        return [self._to_posting(employer_slug, p) for p in resp.json()]

    def _to_posting(self, employer_slug: str, p: dict) -> RawPosting:
        now = datetime.now(UTC)
        title = p.get("text", "").strip()
        hosted_url = p.get("hostedUrl") or ""
        apply_url = p.get("applyUrl") or hosted_url
        categories = p.get("categories", {}) or {}
        location = categories.get("location")
        commitment = (categories.get("commitment") or "").lower()
        description = _strip_html(p.get("descriptionPlain") or p.get("description") or "")
        workplace = (p.get("workplaceType") or "").lower()

        source_ev = Evidence(
            source_url=hosted_url or None,
            source_type=SourceType.ATS_LEVER,
            retrieved_at=now,
            claim=f"Posting '{title}' listed on {employer_slug} Lever site.",
            excerpt=(description[:400] if description else None),
            confidence=ConfidenceLevel.HIGH,
            verification_status=VerificationStatus.VERIFIED,
        )
        job = Job(
            dedup_key=_dedup_key(employer_slug, title, location, str(p.get("createdAt") or "")),
            title=title or "Untitled",
            employer=employer_slug.replace("-", " ").title(),
            employer_domain=_guess_employer_domain(hosted_url),
            application_url=apply_url,
            source_url=hosted_url,
            location=location,
            remote_status=_remote_from(workplace, location, description),
            employment_type=_employment_from(commitment),
            description=description,
            compensation=CompensationBreakdown(provenance="unknown"),
            title_evidence_ids=[source_ev.id],
            employer_evidence_ids=[source_ev.id],
            application_url_evidence_ids=[source_ev.id],
            location_evidence_ids=[source_ev.id] if location else [],
            remote_evidence_ids=[source_ev.id],
        )
        return RawPosting(job=job, evidence=[source_ev])


def _strip_html(s: str) -> str:
    text = re.sub(r"<br\s*/?>", "\n", s, flags=re.IGNORECASE)
    text = re.sub(r"</p>", "\n", text, flags=re.IGNORECASE)
    text = re.sub(r"<[^>]+>", "", text)
    text = re.sub(r"&nbsp;", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def _dedup_key(slug: str, title: str, location: str | None, created_at: str) -> str:
    bucket = created_at[:7] if len(created_at) >= 7 else ""
    loc = (location or "unknown").lower().replace(" ", "-")
    t = re.sub(r"[^a-z0-9]+", "-", (title or "untitled").lower()).strip("-")
    return f"{slug}::{t}::{loc}::{bucket}"


def _remote_from(workplace: str, location: str | None, description: str) -> RemoteStatus:
    if workplace == "remote":
        return RemoteStatus.REMOTE_REGION
    if workplace == "hybrid":
        return RemoteStatus.HYBRID
    if workplace == "on-site":
        return RemoteStatus.ONSITE
    text = f"{location or ''} {description}".lower()
    if "remote" in text:
        return RemoteStatus.REMOTE_REGION
    if "hybrid" in text:
        return RemoteStatus.HYBRID
    return RemoteStatus.UNKNOWN


def _employment_from(commitment: str) -> str:
    if "full" in commitment:
        return "full_time"
    if "part" in commitment:
        return "part_time"
    if "contract" in commitment:
        return "contract"
    if "intern" in commitment:
        return "intern"
    return "unknown"


def _guess_employer_domain(hosted_url: str) -> str | None:
    reg = registrable_domain(hosted_url)
    if reg and reg not in ("lever.co",):
        return reg
    return None
