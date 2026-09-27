"""Deterministic verification agent.

Signals used (no LLM required):
  1. application_url_domain_matches_employer
  2. application_url_on_known_ats
  3. source_url_domain_matches_employer
  4. no_scam_phrases_in_description
  5. no_upfront_payment_request
  6. posting_has_required_fields
  7. compensation_provenance_disclosed

The agent returns a VerificationReport with each signal and a composite status.
Explanations are factual and non-defamatory (e.g. "domain does not match" rather than "scam").
"""
from __future__ import annotations

import re
from datetime import UTC, datetime

from pydantic import BaseModel

from app.core.domains import domains_match, is_ats_host, registrable_domain
from app.models.evidence import (
    ConfidenceLevel,
    Evidence,
    SourceType,
    VerificationStatus,
)
from app.models.job import Job
from app.models.verification import SignalOutcome, VerificationReport, VerificationSignal
from app.services.evidence_store import EvidenceStore

from .base import Agent, AgentContext


class VerificationAgentInput(BaseModel):
    job: Job


# Non-defamatory, factual patterns. Presence == warning, not a defamation claim.
_SCAM_PHRASES: tuple[re.Pattern, ...] = tuple(
    re.compile(p, re.IGNORECASE)
    for p in (
        r"\bwire\s+transfer\b",
        r"\bpay(?:ment)?\s+(?:a\s+)?(?:small\s+)?fee\b",
        r"\bprocessing\s+fee\b",
        r"\btraining\s+fee\b",
        r"\bequipment\s+fee\b",
        r"\bsend\s+(?:your\s+)?bank\s+(?:details|account)\b",
        r"\bwhats?app\s+me\b",
        r"\btelegram\s+me\b",
        # Guaranteed-earnings claims are only a scam signal when NOT immediately
        # followed by a legitimate qualifier like "during paid training" or
        # "on-target earnings (OTE)".  We look for the earnings phrase followed
        # by <=40 chars of non-qualifier text, then a "no experience" or "start
        # immediately" style pitch — that co-occurrence is what fraud posts do.
        r"\bearn\s+\$?\d{3,}\s*(?:/|per)\s*(?:day|week)\b(?!\s+during\s+paid|\s+ote\b)"
        r".{0,80}(?:no\s+experience|start\s+immediately|guaranteed|from\s+home)",
        r"\bno\s+experience\s+(?:needed|required)\b.*\bhigh\s+pay\b",
        r"\bcrypto(?:currency)?\s+wallet\b",
        r"\bsend\s+(?:your\s+)?social\s+security\b",
    )
)


class VerificationAgent(Agent[VerificationAgentInput, VerificationReport]):
    name = "verification_agent"

    def run(self, ctx: AgentContext, input_: VerificationAgentInput) -> VerificationReport:
        job = input_.job
        signals: list[VerificationSignal] = []
        risk_flags: list[str] = []

        signals.append(self._sig_app_url_matches_employer(ctx.evidence_store, job, risk_flags))
        signals.append(self._sig_app_url_on_known_ats(ctx.evidence_store, job))
        signals.append(self._sig_source_url_matches_employer(ctx.evidence_store, job))
        signals.append(self._sig_application_url_https(ctx.evidence_store, job, risk_flags))
        signals.append(self._sig_scam_phrases(ctx.evidence_store, job, risk_flags))
        signals.append(self._sig_payment_request(ctx.evidence_store, job, risk_flags))
        signals.append(self._sig_required_fields(ctx.evidence_store, job))
        signals.append(self._sig_comp_provenance(ctx.evidence_store, job))

        composite = self._composite(signals)
        summary = self._summarize(job, signals, composite)

        return VerificationReport(
            job_id=job.id,
            signals=signals,
            composite_status=composite,
            summary=summary,
            risk_flags=risk_flags,
        )

    # ---------- signals ----------

    def _sig_app_url_matches_employer(
        self, store: EvidenceStore, job: Job, risk_flags: list[str]
    ) -> VerificationSignal:
        app_domain = registrable_domain(str(job.application_url))
        emp = job.employer_domain
        if not emp:
            return _inconclusive(
                store,
                "application_url_domain_matches_employer",
                "Employer canonical domain not provided; cannot compare.",
            )
        if is_ats_host(str(job.application_url)):
            # Employer using a known ATS — application domain won't literally match, and that's OK.
            return _pass(
                store,
                "application_url_domain_matches_employer",
                f"Application URL is on a known ATS ({is_ats_host(str(job.application_url))}); "
                "handled by the ATS signal.",
                weight=0.5,
            )
        if domains_match(str(job.application_url), emp):
            return _pass(
                store,
                "application_url_domain_matches_employer",
                f"Application URL domain matches employer domain ({emp}).",
                weight=2.0,
            )
        risk_flags.append("application_domain_mismatch")
        return _fail(
            store,
            "application_url_domain_matches_employer",
            f"Application URL registrable domain '{app_domain}' does not match employer "
            f"domain '{emp}'.",
            weight=2.0,
        )

    def _sig_app_url_on_known_ats(self, store: EvidenceStore, job: Job) -> VerificationSignal:
        ats = is_ats_host(str(job.application_url))
        if ats:
            return _pass(
                store,
                "application_url_on_known_ats",
                f"Application URL is hosted on a well-known ATS: {ats}.",
                weight=1.5,
            )
        return _inconclusive(
            store,
            "application_url_on_known_ats",
            "Application URL is not on a recognized ATS host.",
        )

    def _sig_application_url_https(
        self, store: EvidenceStore, job: Job, risk_flags: list[str]
    ) -> VerificationSignal:
        scheme = str(job.application_url).split("://", 1)[0].lower()
        if scheme == "https":
            return _pass(
                store,
                "application_url_https",
                "Application URL uses HTTPS.",
                weight=0.5,
            )
        risk_flags.append("application_url_not_https")
        return _warn(
            store,
            "application_url_https",
            f"Application URL uses '{scheme}://', not HTTPS. Credentials or PII submitted "
            "through this URL would travel unencrypted.",
            weight=1.0,
        )

    def _sig_source_url_matches_employer(self, store: EvidenceStore, job: Job) -> VerificationSignal:
        emp = job.employer_domain
        if not emp:
            return _inconclusive(
                store,
                "source_url_domain_matches_employer",
                "Employer canonical domain not provided; cannot compare source URL.",
            )
        if is_ats_host(str(job.source_url)):
            return _pass(
                store,
                "source_url_domain_matches_employer",
                "Source URL is on a known ATS host.",
                weight=0.5,
            )
        if domains_match(str(job.source_url), emp):
            return _pass(
                store,
                "source_url_domain_matches_employer",
                f"Source URL domain matches employer domain ({emp}).",
                weight=1.0,
            )
        return _warn(
            store,
            "source_url_domain_matches_employer",
            f"Source URL domain does not match employer domain ({emp}); may be an aggregator.",
        )

    def _sig_scam_phrases(
        self, store: EvidenceStore, job: Job, risk_flags: list[str]
    ) -> VerificationSignal:
        text = f"{job.title}\n{job.description}"
        hits = [p.pattern for p in _SCAM_PHRASES if p.search(text)]
        if not hits:
            return _pass(
                store,
                "no_scam_phrases_in_description",
                "No known scam-indicative phrases detected in title or description.",
            )
        risk_flags.append("scam_phrase_detected")
        return _fail(
            store,
            "no_scam_phrases_in_description",
            f"Posting contains phrases commonly associated with fraudulent listings "
            f"({len(hits)} match(es)). Please review with caution.",
            weight=2.0,
        )

    def _sig_payment_request(
        self, store: EvidenceStore, job: Job, risk_flags: list[str]
    ) -> VerificationSignal:
        payment_patterns = (
            r"\bpay(?:ment)?\s+(?:a\s+)?(?:small\s+)?fee\b",
            r"\bprocessing\s+fee\b",
            r"\btraining\s+fee\b",
            r"\bequipment\s+fee\b",
        )
        if any(re.search(p, job.description, re.IGNORECASE) for p in payment_patterns):
            risk_flags.append("upfront_payment_request")
            return _fail(
                store,
                "no_upfront_payment_request",
                "Posting appears to request payment from applicants. Legitimate employers "
                "do not require candidates to pay fees.",
                weight=3.0,
            )
        return _pass(
            store,
            "no_upfront_payment_request",
            "No indication that the applicant is asked to pay a fee.",
        )

    def _sig_required_fields(self, store: EvidenceStore, job: Job) -> VerificationSignal:
        missing = []
        if not job.title.strip():
            missing.append("title")
        if not job.employer.strip():
            missing.append("employer")
        if not job.description.strip():
            missing.append("description")
        if missing:
            return _fail(
                store,
                "posting_has_required_fields",
                f"Posting is missing required fields: {', '.join(missing)}.",
            )
        return _pass(
            store,
            "posting_has_required_fields",
            "All required posting fields are present.",
        )

    def _sig_comp_provenance(self, store: EvidenceStore, job: Job) -> VerificationSignal:
        prov = job.compensation.provenance
        if prov in {"confirmed", "employer_range", "legally_disclosed"}:
            return _pass(
                store,
                "compensation_provenance_disclosed",
                f"Compensation provenance is '{prov}'.",
                weight=0.5,
            )
        if prov in {"third_party_estimate", "inferred"}:
            return _warn(
                store,
                "compensation_provenance_disclosed",
                f"Compensation is '{prov}' — treat as estimate, not confirmed.",
            )
        return _inconclusive(
            store,
            "compensation_provenance_disclosed",
            "Compensation not disclosed in the posting.",
        )

    # ---------- composition ----------

    def _composite(self, signals: list[VerificationSignal]) -> VerificationStatus:
        fails = [s for s in signals if s.outcome is SignalOutcome.FAIL]
        if fails:
            # Any hard fail with weight >= 2 → HIGH_RISK; else UNVERIFIED
            if any(s.weight >= 2.0 for s in fails):
                return VerificationStatus.HIGH_RISK
            return VerificationStatus.UNVERIFIED
        passes = [s for s in signals if s.outcome is SignalOutcome.PASS]
        warns = [s for s in signals if s.outcome is SignalOutcome.WARN]
        pass_weight = sum(s.weight for s in passes)
        total_evaluable = pass_weight + sum(s.weight for s in warns)
        if total_evaluable == 0:
            return VerificationStatus.UNVERIFIED
        ratio = pass_weight / total_evaluable
        if ratio >= 0.8 and pass_weight >= 3.0:
            return VerificationStatus.VERIFIED
        if ratio >= 0.5:
            return VerificationStatus.PARTIALLY_VERIFIED
        return VerificationStatus.UNVERIFIED

    def _summarize(self, job: Job, signals: list[VerificationSignal], status: VerificationStatus) -> str:
        base = {
            VerificationStatus.VERIFIED: "Employer and application destination checks pass.",
            VerificationStatus.PARTIALLY_VERIFIED: "Some checks pass; others could not be independently confirmed.",
            VerificationStatus.UNVERIFIED: "Insufficient evidence to confirm this posting.",
            VerificationStatus.HIGH_RISK: "Multiple suspicious indicators detected. Review carefully before applying.",
            VerificationStatus.CONFLICTING: "Sources disagree; manual review recommended.",
        }[status]
        return f"{job.employer} — {job.title}: {base}"


# ---------- signal builders ----------

def _mk_evidence(store: EvidenceStore, claim: str, status: VerificationStatus) -> str:
    ev = Evidence(
        source_url=None,
        source_type=SourceType.INFERRED_DETERMINISTIC,
        retrieved_at=datetime.now(UTC),
        claim=claim,
        confidence=ConfidenceLevel.HIGH,
        verification_status=status,
    )
    return store.put(ev)


def _pass(store: EvidenceStore, name: str, explanation: str, weight: float = 1.0) -> VerificationSignal:
    return VerificationSignal(
        name=name, outcome=SignalOutcome.PASS, weight=weight, explanation=explanation,
        evidence_ids=[_mk_evidence(store, f"{name}: {explanation}", VerificationStatus.VERIFIED)],
    )


def _warn(store: EvidenceStore, name: str, explanation: str, weight: float = 1.0) -> VerificationSignal:
    return VerificationSignal(
        name=name, outcome=SignalOutcome.WARN, weight=weight, explanation=explanation,
        evidence_ids=[_mk_evidence(store, f"{name}: {explanation}", VerificationStatus.PARTIALLY_VERIFIED)],
    )


def _fail(store: EvidenceStore, name: str, explanation: str, weight: float = 1.0) -> VerificationSignal:
    return VerificationSignal(
        name=name, outcome=SignalOutcome.FAIL, weight=weight, explanation=explanation,
        evidence_ids=[_mk_evidence(store, f"{name}: {explanation}", VerificationStatus.HIGH_RISK)],
    )


def _inconclusive(store: EvidenceStore, name: str, explanation: str, weight: float = 1.0) -> VerificationSignal:
    return VerificationSignal(
        name=name, outcome=SignalOutcome.INCONCLUSIVE, weight=weight, explanation=explanation,
        evidence_ids=[_mk_evidence(store, f"{name}: {explanation}", VerificationStatus.UNVERIFIED)],
    )
