from __future__ import annotations

import io

from docx import Document

from app.services.resume_parser import parse_resume


def _docx_bytes(text: str) -> bytes:
    doc = Document()
    for line in text.splitlines():
        doc.add_paragraph(line)
    buf = io.BytesIO()
    doc.save(buf)
    return buf.getvalue()


def test_parse_docx_extracts_name_email_skills():
    text = """\
Jane Doe
jane.doe@example.com  •  https://github.com/janedoe  •  https://linkedin.com/in/janedoe

Senior AI Engineer at Acme AI (2021-2024)
Machine Learning Engineer at Startup Corp (2018-2021)

Skills: Python, PyTorch, LLM, RAG, PostgreSQL, Docker, Kubernetes, AWS
"""
    data = _docx_bytes(text)
    result = parse_resume("jane.docx", data, user_id="u1")
    assert result.profile.full_name == "Jane Doe"
    assert result.profile.email == "jane.doe@example.com"
    assert str(result.profile.github_url).rstrip("/") == "https://github.com/janedoe"
    skill_names = {s.name for s in result.profile.skills}
    assert {"python", "pytorch", "llm", "rag", "postgresql", "docker", "kubernetes", "aws"}.issubset(skill_names)
    assert len(result.profile.experience) >= 1
    # Gaps are always emitted for prefs/auth (we never invent those)
    assert any("preferences" in g for g in result.gaps)
    assert any("work_authorization" in g for g in result.gaps)


def test_parse_txt_flags_gaps_when_missing():
    data = b"Just some text with no structure\n"
    result = parse_resume("r.txt", data, user_id="u2")
    assert result.profile.email is None
    assert any("email" in g for g in result.gaps)
    assert any("skills" in g for g in result.gaps)


def test_parse_rejects_unsupported_format():
    import pytest

    from app.services.resume_parser import UnsupportedResumeFormat
    with pytest.raises(UnsupportedResumeFormat):
        parse_resume("r.rtf", b"x", user_id="u3")
