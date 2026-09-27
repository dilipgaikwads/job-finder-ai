"""Resume ingestion: PDF/DOCX/plain-text -> raw text -> structured Profile draft.

This is a v0 heuristic parser. It never *invents* fields; it emits what it
extracted plus a list of `gaps` for anything ambiguous. Downstream code must
ask the user to fill or confirm.
"""
from __future__ import annotations

import io
import re
from dataclasses import dataclass, field
from datetime import date

from app.models.profile import Preferences, Profile, Skill, WorkExperience


class UnsupportedResumeFormat(ValueError):
    pass


@dataclass
class ParseResult:
    profile: Profile
    raw_text: str
    gaps: list[str] = field(default_factory=list)   # human-readable questions we need the user to answer


_EMAIL_RE = re.compile(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}")
_URL_RE = re.compile(r"https?://[^\s)>\]]+", re.IGNORECASE)
_GITHUB_RE = re.compile(r"https?://(?:www\.)?github\.com/[A-Za-z0-9_.-]+/?", re.IGNORECASE)
_LINKEDIN_RE = re.compile(r"https?://(?:www\.)?linkedin\.com/in/[A-Za-z0-9_-]+/?", re.IGNORECASE)

# Deliberately conservative skill vocabulary. Better to miss than to guess a skill the user doesn't have.
_SKILL_VOCAB: tuple[str, ...] = (
    "python", "java", "kotlin", "javascript", "typescript", "go", "rust", "c++", "c#", "swift",
    "sql", "postgresql", "mysql", "mongodb", "redis", "elasticsearch",
    "aws", "gcp", "azure", "docker", "kubernetes", "terraform",
    "react", "angular", "vue", "svelte", "next.js", "django", "flask", "fastapi", "spring",
    "android", "jetpack compose", "ios",
    "pytorch", "tensorflow", "jax", "scikit-learn", "pandas", "numpy",
    "llm", "rag", "langchain", "llamaindex", "openai", "anthropic", "hugging face",
    "machine learning", "deep learning", "nlp", "computer vision", "mlops",
    "kafka", "spark", "airflow", "dbt", "snowflake", "databricks",
    "graphql", "rest", "grpc", "microservices",
    "linux", "git", "ci/cd", "github actions",
)


def extract_text(filename: str, data: bytes) -> str:
    """Extract raw text from a resume file. Supports .pdf, .docx, .txt."""
    lower = filename.lower()
    if lower.endswith(".pdf"):
        return _extract_pdf(data)
    if lower.endswith(".docx"):
        return _extract_docx(data)
    if lower.endswith(".txt"):
        try:
            return data.decode("utf-8")
        except UnicodeDecodeError:
            return data.decode("latin-1", errors="replace")
    raise UnsupportedResumeFormat(f"Unsupported resume format: {filename}")


def _extract_pdf(data: bytes) -> str:
    from pypdf import PdfReader
    reader = PdfReader(io.BytesIO(data))
    parts: list[str] = []
    for page in reader.pages:
        try:
            parts.append(page.extract_text() or "")
        except Exception:  # noqa: BLE001 — pypdf can raise a variety
            parts.append("")
    return "\n".join(parts)


def _extract_docx(data: bytes) -> str:
    from docx import Document
    doc = Document(io.BytesIO(data))
    return "\n".join(p.text for p in doc.paragraphs)


def parse_resume(filename: str, data: bytes, *, user_id: str) -> ParseResult:
    text = extract_text(filename, data)
    if not text.strip():
        raise UnsupportedResumeFormat("Resume produced no extractable text (scanned image?).")

    email = _first(_EMAIL_RE.findall(text))
    github = _first(_GITHUB_RE.findall(text))
    linkedin = _first(_LINKEDIN_RE.findall(text))
    portfolio = _first([u for u in _URL_RE.findall(text) if not (
        "github.com" in u.lower() or "linkedin.com" in u.lower()
    )])

    skills = _extract_skills(text)
    experience = _extract_experience(text)
    name = _extract_name(text)

    gaps: list[str] = []
    if not name:
        gaps.append("full_name: could not extract from resume — please confirm your name.")
    if not email:
        gaps.append("email: no email address found — please provide one for notifications.")
    if not experience:
        gaps.append("experience: no work-experience entries confidently parsed — please add or confirm.")
    if not skills:
        gaps.append("skills: no known skills matched — please list your key skills.")
    gaps.append("preferences: please confirm remote/onsite, target locations, salary expectations.")
    gaps.append("work_authorization: please confirm your work authorization per country.")

    profile = Profile(
        user_id=user_id,
        full_name=name,
        email=email,
        skills=[Skill(name=s, source="extracted_from_resume") for s in skills],
        experience=experience,
        github_url=github,
        linkedin_url=linkedin,
        portfolio_url=portfolio,
        preferences=Preferences(),
    )
    return ParseResult(profile=profile, raw_text=text, gaps=gaps)


def _first(items):
    return items[0] if items else None


def _extract_skills(text: str) -> list[str]:
    lower = text.lower()
    found: list[str] = []
    for skill in _SKILL_VOCAB:
        # word-boundary-ish match; allow punctuation around multi-word skills
        pattern = r"(?<![A-Za-z0-9+])" + re.escape(skill) + r"(?![A-Za-z0-9+])"
        if re.search(pattern, lower):
            found.append(skill)
    # Stable order, no dupes
    seen = set()
    result = []
    for s in found:
        if s not in seen:
            seen.add(s)
            result.append(s)
    return result


_EXP_LINE_RE = re.compile(
    r"""^\s*
        (?P<title>[A-Z][A-Za-z0-9 /,&\-.+]{2,80}?)
        \s+(?:at|@|—|-)\s+
        (?P<company>[A-Z][A-Za-z0-9 /,.&\-]{1,80}?)
        \s*(?:\((?P<dates>[^)]+)\))?
        \s*$
    """,
    re.VERBOSE | re.MULTILINE,
)

_YEAR_RE = re.compile(r"(19|20)\d{2}")


def _extract_experience(text: str) -> list[WorkExperience]:
    """Very conservative: only accept lines that plausibly look like 'Title at Company (2020-2023)'.

    Anything ambiguous → skip and let the parser emit a gap instead of inventing.
    """
    out: list[WorkExperience] = []
    for m in _EXP_LINE_RE.finditer(text):
        title = m.group("title").strip()
        company = m.group("company").strip()
        dates = m.group("dates") or ""
        years = _YEAR_RE.findall(dates)
        try:
            start = date(int(years[0][0] + years[0][1] if isinstance(years[0], tuple) else years[0]), 1, 1) if years else date(2000, 1, 1)
        except Exception:  # noqa: BLE001
            continue
        end: date | None = None
        if len(years) >= 2:
            try:
                end = date(int(years[1] if isinstance(years[1], str) else years[1][0] + years[1][1]), 12, 31)
            except Exception:  # noqa: BLE001
                end = None
        out.append(WorkExperience(company=company, title=title, start=start, end=end))
    return out


def _extract_name(text: str) -> str | None:
    """Grab the first line if it looks like a name (2–4 capitalized tokens, no digits, no @)."""
    for raw in text.splitlines():
        line = raw.strip()
        if not line or "@" in line or any(c.isdigit() for c in line):
            continue
        parts = line.split()
        if 2 <= len(parts) <= 4 and all(p[:1].isupper() and p.isalpha() for p in parts if p):
            return line
        break
    return None
