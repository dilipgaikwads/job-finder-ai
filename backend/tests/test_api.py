from __future__ import annotations

from fastapi.testclient import TestClient

from app.main import create_app


def _valid_job_payload() -> dict:
    return {
        "dedup_key": "acme::senior-ai-engineer::remote::2026-09",
        "title": "Senior AI Engineer",
        "employer": "Acme AI",
        "employer_domain": "acme.ai",
        "application_url": "https://boards.greenhouse.io/acme/jobs/1",
        "source_url": "https://boards.greenhouse.io/acme/jobs/1",
        "location": "Remote (US)",
        "description": "Build production LLM systems.",
        "title_evidence_ids": ["placeholder"],
        "employer_evidence_ids": ["placeholder"],
        "application_url_evidence_ids": ["placeholder"],
        "compensation": {"provenance": "employer_range"},
    }


def test_health():
    client = TestClient(create_app())
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json() == {"status": "ok"}


def test_verify_endpoint_legitimate_posting():
    client = TestClient(create_app())
    r = client.post("/jobs/verify", json=_valid_job_payload())
    assert r.status_code == 200
    body = r.json()
    assert body["composite_status"] in {"verified", "partially_verified"}
    assert body["risk_flags"] == []


def test_verify_endpoint_flags_scam_language():
    client = TestClient(create_app())
    payload = _valid_job_payload()
    payload["description"] = "Pay a small processing fee to secure this role. WhatsApp me."
    r = client.post("/jobs/verify", json=payload)
    assert r.status_code == 200
    body = r.json()
    assert body["composite_status"] == "high_risk"
    assert "upfront_payment_request" in body["risk_flags"]
