"""Domain utilities for verification. Deterministic, testable, no LLM."""
from __future__ import annotations

from urllib.parse import urlparse

import tldextract


# Well-known ATS hosts. If an application URL is on one of these, it's a strong signal
# (though the employer subdomain/slug is what actually anchors trust).
ATS_HOSTS: dict[str, str] = {
    "greenhouse.io": "greenhouse",
    "boards.greenhouse.io": "greenhouse",
    "lever.co": "lever",
    "jobs.lever.co": "lever",
    "myworkdayjobs.com": "workday",
    "workday.com": "workday",
    "smartrecruiters.com": "smartrecruiters",
    "ashbyhq.com": "ashby",
    "jobs.ashbyhq.com": "ashby",
    "recruitee.com": "recruitee",
    "workable.com": "workable",
    "bamboohr.com": "bamboohr",
    "icims.com": "icims",
    "successfactors.com": "successfactors",
    "taleo.net": "taleo",
    "jobvite.com": "jobvite",
}


def registrable_domain(url_or_host: str) -> str | None:
    """Return the eTLD+1 (registrable domain), lower-cased. None if not parseable."""
    if "://" in url_or_host:
        host = urlparse(url_or_host).hostname or ""
    else:
        host = url_or_host
    if not host:
        return None
    ext = tldextract.extract(host)
    if not ext.domain or not ext.suffix:
        return None
    return f"{ext.domain}.{ext.suffix}".lower()


def is_ats_host(url_or_host: str) -> str | None:
    """If the host is a known ATS, return the ATS name; else None."""
    reg = registrable_domain(url_or_host)
    if reg is None:
        return None
    if reg in ATS_HOSTS:
        return ATS_HOSTS[reg]
    # Sometimes ATS hosts are subdomains under the ATS eTLD+1
    for known, name in ATS_HOSTS.items():
        if reg == known or reg.endswith(f".{known}"):
            return name
    return None


def domains_match(a: str | None, b: str | None) -> bool:
    if not a or not b:
        return False
    ra, rb = registrable_domain(a), registrable_domain(b)
    return ra is not None and ra == rb
