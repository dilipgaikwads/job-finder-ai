"""End-to-end: upload resume → search Greenhouse (mocked) → verify → match → log-notify."""
from __future__ import annotations

import io
import json

import httpx
from docx import Document
from fastapi.testclient import TestClient

from app.agents.discovery import GreenhouseAdapter, LeverAdapter
from app.main import create_app


def _docx_bytes(text: str) -> bytes:
    doc = Document()
    for line in text.splitlines():
        doc.add_paragraph(line)
    buf = io.BytesIO()
    doc.save(buf)
    return buf.getvalue()


def _mocked_client(app):
    """Swap the Greenhouse & Lever adapters' HTTP clients for MockTransport."""
    payload = {
        "jobs": [
            {
                "id": 1,
                "title": "Senior AI Engineer",
                "absolute_url": "https://boards.greenhouse.io/acme/jobs/1",
                "company_name": "Acme AI",
                "location": {"name": "Remote - US"},
                "updated_at": "2026-09-20T12:00:00Z",
                "content": "<p>Build LLM systems with Python, PyTorch. RAG a plus.</p>",
            }
        ]
    }
    gh_transport = httpx.MockTransport(lambda req: httpx.Response(200, content=json.dumps(payload)))
    lv_transport = httpx.MockTransport(lambda req: httpx.Response(200, content=json.dumps([])))
    disc = app.state.agents["discovery_agent"]
    disc._adapters["greenhouse"] = GreenhouseAdapter(client=httpx.Client(transport=gh_transport))
    disc._adapters["lever"] = LeverAdapter(client=httpx.Client(transport=lv_transport))


def test_end_to_end_upload_search_notify():
    app = create_app()
    _mocked_client(app)
    client = TestClient(app)

    # 1. Upload resume
    resume_text = """\
Jane Doe
jane@example.com

Senior AI Engineer at Acme AI (2021-2024)

Skills: Python, PyTorch, LLM, RAG, PostgreSQL, Docker
"""
    r = client.post(
        "/resumes",
        files={"file": ("jane.docx", _docx_bytes(resume_text),
                        "application/vnd.openxmlformats-officedocument.wordprocessingml.document")},
    )
    assert r.status_code == 200, r.text
    body = r.json()
    user_id = body["user_id"]
    assert body["detected_email"] == "jane@example.com"
    assert "python" in body["skills"]

    # 2. Confirm prefs (user-supplied, never inferred)
    r = client.patch(f"/profiles/{user_id}", json={"remote_only": True, "hybrid_ok": True})
    assert r.status_code == 200

    # 3. Search
    r = client.post(
        f"/profiles/{user_id}/search",
        json={"targets": [{"adapter": "greenhouse", "employer_slug": "acme"}], "notify": True},
    )
    assert r.status_code == 200, r.text
    result = r.json()
    assert result["total_discovered"] == 1
    assert result["returned"] == 1
    item = result["items"][0]
    assert item["job"]["title"] == "Senior AI Engineer"
    assert item["verification_status"] in {"verified", "partially_verified"}
    assert item["composite_match"] > 0.0
    # 4. Notification was recorded by LogNotifier
    assert result["notifications_sent"] == 1


def test_search_filters_high_risk_jobs():
    app = create_app()
    # Inject a scam posting via Greenhouse mock
    payload = {
        "jobs": [{
            "id": 99,
            "title": "Remote Job — Easy Money",
            "absolute_url": "https://boards.greenhouse.io/scam/jobs/99",
            "company_name": "Scam Co",
            "location": {"name": "Remote"},
            "updated_at": "2026-09-20T12:00:00Z",
            "content": "Pay a small training fee to get started. WhatsApp me. Earn $500/day.",
        }]
    }
    transport = httpx.MockTransport(lambda req: httpx.Response(200, content=json.dumps(payload)))
    disc = app.state.agents["discovery_agent"]
    disc._adapters["greenhouse"] = GreenhouseAdapter(client=httpx.Client(transport=transport))
    disc._adapters["lever"] = LeverAdapter(
        client=httpx.Client(transport=httpx.MockTransport(lambda r: httpx.Response(200, content="[]")))
    )
    client = TestClient(app)

    r = client.post("/resumes", files={"file": ("r.txt", b"Jane Doe\njane@example.com\nSkills: Python", "text/plain")})
    assert r.status_code == 200
    user_id = r.json()["user_id"]

    r = client.post(
        f"/profiles/{user_id}/search",
        json={"targets": [{"adapter": "greenhouse", "employer_slug": "scam"}], "notify": True},
    )
    assert r.status_code == 200
    result = r.json()
    assert result["filtered_out_high_risk"] == 1
    assert result["returned"] == 0
    # No notification is ever sent for high_risk postings
    assert result["notifications_sent"] == 0
