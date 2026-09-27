# Sourcing policy

This document lists what job sources this system uses, what it excludes, and why. The policy is enforced in code; new adapters go through a review checklist before being added.

## What we source from

**Tier 1 — official ATS platforms** (evidence: `ats_greenhouse`, `ats_lever`, `ats_workday`, …)
- Greenhouse (`boards-api.greenhouse.io`)
- Lever (`api.lever.co`)
- Workday, Ashby, SmartRecruiters, iCIMS — planned

Employer accounts on these platforms give us strong provenance: the URL, the employer name, and the posting all resolve to the same tenancy on a known ATS host.

**Tier 2 — official employer careers pages** (evidence: `official_careers_page`)
- Directly fetched from a canonical employer domain (verified via WHOIS/allowlist).

**Tier 3 — reputable aggregators** (evidence: `aggregator`, only when a Tier-1 or Tier-2 evidence source is also present)
- Considered but never sole source of truth. If an aggregator carries a listing that we cannot corroborate on the employer's ATS or careers page within a freshness window, the listing is marked `UNVERIFIED` and downranked.

## What we do NOT source from

- **Dark web / Tor hidden services / .onion sites.** Not a source of legitimate employment. The population of "job postings" on dark-web forums is dominated by scams, wage theft, money-muling recruitment, and trafficking. Ingesting them would pollute the verification model with adversarial signals crafted to look legitimate, undermine the entire anti-scam premise of this product, and expose users to categories of harm no user-facing warning can adequately mitigate.
- **Paste sites, unmoderated forums, DMs, Telegram/WhatsApp groups.** Same reasoning at lower magnitude — no verifiable provenance chain to an employer.
- **Scraping sites that prohibit it in their ToS.** Regardless of technical feasibility.
- **Copy-pasted "referral" listings without a resolvable ATS or careers-page URL.**

## Adding a new source

Each new adapter must satisfy the following before being wired into `DiscoveryAgent`:

1. Public or contractual API — no ToS violation.
2. A stable identity linking posting → employer → application destination.
3. A canonical `Evidence.source_type` (extend `SourceType` if needed).
4. Deterministic parsing (no LLM in the parse path — LLMs may classify ambiguous *language*, but never fabricate structured fields).
5. Adapter tests with `httpx.MockTransport` covering: happy path, HTTP error, malformed payload.
6. Verification pathway confirmed: does at least one signal in `VerificationAgent` benefit from this source, and does no signal falsely pass because of it?

If any check fails, the source stays out.
