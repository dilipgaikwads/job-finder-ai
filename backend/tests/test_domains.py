from app.core.domains import domains_match, is_ats_host, registrable_domain


def test_registrable_domain_basic():
    assert registrable_domain("https://careers.acme.co.uk/roles/1") == "acme.co.uk"
    assert registrable_domain("acme.ai") == "acme.ai"
    assert registrable_domain("boards.greenhouse.io") == "greenhouse.io"


def test_registrable_domain_bad_inputs():
    assert registrable_domain("") is None
    assert registrable_domain("not a url") is None


def test_is_ats_host():
    assert is_ats_host("https://boards.greenhouse.io/acme/jobs/1") == "greenhouse"
    assert is_ats_host("https://jobs.lever.co/acme/xyz") == "lever"
    assert is_ats_host("https://acme.myworkdayjobs.com/xyz") == "workday"
    assert is_ats_host("https://acme.ai/careers/1") is None


def test_domains_match():
    assert domains_match("https://acme.ai/x", "acme.ai")
    assert domains_match("https://careers.acme.ai/x", "acme.ai")
    assert not domains_match("https://acme-hr-portal.com/x", "acme.ai")
    assert not domains_match(None, "acme.ai")
