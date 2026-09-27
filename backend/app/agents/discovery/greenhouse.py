"""Greenhouse public job-board adapter.

Public API: https://boards-api.greenhouse.io/v1/boards/{board_token}/jobs?content=true
No auth required. This is a first-party endpoint from Greenhouse; employers
authoring these boards is a strong evidence signal for legitimacy.
"""
from __future__ import annotations

import re
from datetime import UTC, datetime

import httpx

from app.core.domains import registrable_domain
from app.models.evidence import ConfidenceLevel, Evidence, SourceType, VerificationStatus
from app.models.job import CompensationBreakdown, Job, RemoteStatus

from .base import DiscoveryAdapter, RawPosting

_GREENHOUSE_API = "https://boards-api.greenhouse.io/v1/boards/{slug}/jobs"


class GreenhouseAdapter(DiscoveryAdapter):
    name = "greenhouse"

    def __init__(self, client: httpx.Client | None = None, timeout: float = 15.0) -> None:
        self._client = client or httpx.Client(timeout=timeout, headers={
            "User-Agent": "job-finder-ai/0.1 (+https://github.com/dilipgaikwads/job-finder-ai)"
        })
        self._own_client = client is None

    def close(self) -> None:
        if self._own_client:
            self._client.close()

    def fetch(self, employer_slug: str) -> list[RawPosting]:
        url = _GREENHOUSE_API.format(slug=employer_slug)
        try:
            resp = self._client.get(url, params={"content": "true"})
            resp.raise_for_status()
        except httpx.HTTPError:
            return []
        data = resp.json()
        return [self._to_posting(employer_slug, j) for j in data.get("jobs", [])]

    def _to_posting(self, employer_slug: str, j: dict) -> RawPosting:
        now = datetime.now(UTC)
        title = j.get("title", "").strip()
        absolute_url = j.get("absolute_url") or ""
        source_url = absolute_url  # Greenhouse absolute_url is the canonical posting URL
        application_url = absolute_url
        location = (j.get("location") or {}).get("name") or None
        description_html = j.get("content", "") or ""
        description = _strip_html(description_html)
        company_name = (j.get("company_name") or employer_slug.replace("-", " ").title()).strip()

        source_ev = Evidence(
            source_url=source_url or None,
            source_type=SourceType.ATS_GREENHOUSE,
            retrieved_at=now,
            claim=f"Posting '{title}' listed on {employer_slug} Greenhouse board.",
            excerpt=(description[:400] if description else None),
            confidence=ConfidenceLevel.HIGH,
            verification_status=VerificationStatus.VERIFIED,
        )
        # Evidence records travel with the RawPosting; the DiscoveryAgent stores them and wires ids into Job.
        job = Job(
            dedup_key=_dedup_key(employer_slug, title, location, j.get("updated_at")),
            title=title or "Untitled",
            employer=company_name,
            employer_domain=_guess_employer_domain(employer_slug, absolute_url),
            application_url=application_url,
            source_url=source_url,
            location=location,
            remote_status=_infer_remote(location, description),
            description=description,
            requirements=[],  # Greenhouse doesn't break these out; requirements extraction is Phase 6
            compensation=CompensationBreakdown(provenance="unknown"),
            title_evidence_ids=[source_ev.id],
            employer_evidence_ids=[source_ev.id],
            application_url_evidence_ids=[source_ev.id],
            location_evidence_ids=[source_ev.id] if location else [],
            remote_evidence_ids=[source_ev.id],
        )
        return RawPosting(job=job, evidence=[source_ev])


def _strip_html(s: str) -> str:
    # deliberately naive — good enough for parsing signals; no external deps
    text = re.sub(r"<br\s*/?>", "\n", s, flags=re.IGNORECASE)
    text = re.sub(r"</p>", "\n", text, flags=re.IGNORECASE)
    text = re.sub(r"<[^>]+>", "", text)
    text = re.sub(r"&nbsp;", " ", text)
    text = re.sub(r"&amp;", "&", text)
    text = re.sub(r"&lt;", "<", text)
    text = re.sub(r"&gt;", ">", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def _dedup_key(slug: str, title: str, location: str | None, updated_at: str | None) -> str:
    bucket = (updated_at or "")[:7]  # yyyy-mm
    loc = (location or "unknown").lower().replace(" ", "-")
    t = re.sub(r"[^a-z0-9]+", "-", (title or "untitled").lower()).strip("-")
    return f"{slug}::{t}::{loc}::{bucket}"


_LOC_REMOTE_RE = re.compile(r"\bremote\b", re.IGNORECASE)
# 'global' alone is too loose ("global scope"); require it to describe the role's reach.
_GLOBAL_REMOTE_RE = re.compile(
    r"\b(?:worldwide|from\s+anywhere|remote\s+worldwide|remote\s+global|"
    r"work\s+from\s+anywhere|globally\s+distributed)\b",
    re.IGNORECASE,
)
_MUST_RELOCATE_RE = re.compile(r"\bmust\s+relocate\b|\brelocation\s+required\b", re.IGNORECASE)


def _infer_remote(location: str | None, description: str) -> RemoteStatus:
    loc = location or ""
    text = f"{loc} {description}"
    if _LOC_REMOTE_RE.search(loc):
        # Guard against posts that say "Remote (must relocate to NYC)" — that's onsite.
        if _MUST_RELOCATE_RE.search(text):
            return RemoteStatus.ONSITE
        if _GLOBAL_REMOTE_RE.search(text):
            return RemoteStatus.REMOTE_GLOBAL
        return RemoteStatus.REMOTE_REGION
    if re.search(r"\bhybrid\b", text, re.IGNORECASE):
        return RemoteStatus.HYBRID
    if re.search(r"\b(?:on-?site|in[- ]office)\b", text, re.IGNORECASE):
        return RemoteStatus.ONSITE
    return RemoteStatus.UNKNOWN


def _guess_employer_domain(employer_slug: str, absolute_url: str) -> str | None:
    """We don't fetch the employer website here; leave None unless the slug is a domain-like token.

    The verification agent already knows Greenhouse is a legitimate ATS host, so an empty
    employer_domain simply makes the domain-match signal inconclusive rather than failing.
    """
    reg = registrable_domain(absolute_url)
    if reg and reg not in ("greenhouse.io",):
        return reg
    return None
