from __future__ import annotations

import json

import httpx

from app.agents.discovery import GreenhouseAdapter, LeverAdapter


def test_greenhouse_adapter_parses_public_board():
    payload = {
        "jobs": [
            {
                "id": 1,
                "title": "Senior AI Engineer",
                "absolute_url": "https://boards.greenhouse.io/acme/jobs/1",
                "company_name": "Acme AI",
                "location": {"name": "Remote - US"},
                "updated_at": "2026-09-20T12:00:00Z",
                "content": "<p>Build production <b>LLM</b> systems with PyTorch.</p>",
            },
            {
                "id": 2,
                "title": "Data Engineer",
                "absolute_url": "https://boards.greenhouse.io/acme/jobs/2",
                "company_name": "Acme AI",
                "location": {"name": "New York"},
                "updated_at": "2026-09-15T12:00:00Z",
                "content": "<p>Own our data platform.</p>",
            },
        ]
    }
    transport = httpx.MockTransport(lambda req: httpx.Response(200, content=json.dumps(payload)))
    client = httpx.Client(transport=transport)
    adapter = GreenhouseAdapter(client=client)
    postings = adapter.fetch("acme")
    assert len(postings) == 2
    p0 = postings[0]
    assert p0.job.title == "Senior AI Engineer"
    assert str(p0.job.application_url) == "https://boards.greenhouse.io/acme/jobs/1"
    assert p0.job.title_evidence_ids and p0.job.employer_evidence_ids
    assert p0.evidence[0].source_type.value == "ats_greenhouse"
    # HTML stripped
    assert "<b>" not in p0.job.description
    # Remote inferred from location containing 'Remote'
    assert p0.job.remote_status.value.startswith("remote")


def test_lever_adapter_parses_public_postings():
    payload = [
        {
            "text": "Machine Learning Engineer",
            "hostedUrl": "https://jobs.lever.co/acme/abc",
            "applyUrl": "https://jobs.lever.co/acme/abc/apply",
            "categories": {"location": "Remote", "commitment": "Full-time"},
            "workplaceType": "remote",
            "createdAt": 1758400000000,
            "descriptionPlain": "Own our ML platform. Python, PyTorch, LLM experience required.",
        }
    ]
    transport = httpx.MockTransport(lambda req: httpx.Response(200, content=json.dumps(payload)))
    client = httpx.Client(transport=transport)
    adapter = LeverAdapter(client=client)
    postings = adapter.fetch("acme")
    assert len(postings) == 1
    p = postings[0]
    assert p.job.title == "Machine Learning Engineer"
    assert str(p.job.application_url) == "https://jobs.lever.co/acme/abc/apply"
    assert p.job.remote_status.value.startswith("remote")
    assert p.job.employment_type == "full_time"
    assert p.evidence[0].source_type.value == "ats_lever"


def test_adapter_returns_empty_on_http_error():
    def handler(req):
        return httpx.Response(404)

    client = httpx.Client(transport=httpx.MockTransport(handler))
    assert GreenhouseAdapter(client=client).fetch("nope") == []
    assert LeverAdapter(client=client).fetch("nope") == []
