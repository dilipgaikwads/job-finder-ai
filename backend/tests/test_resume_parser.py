from __future__ import annotations

import io
import zipfile

from docx import Document

from app.services.resume_parser import (
    MAX_DOCX_ENTRIES,
    MAX_DOCX_ENTRY_BYTES,
    UnsupportedResumeFormat,
    parse_resume,
)


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



def _zip_with_entries(entries: list[tuple[str, bytes]]) -> bytes:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for name, content in entries:
            archive.writestr(name, content)
    return buf.getvalue()


def test_docx_rejects_oversized_expanded_entry():
    import pytest

    data = _zip_with_entries([
        ("[Content_Types].xml", b"<Types/>"),
        ("word/document.xml", b"x" * (MAX_DOCX_ENTRY_BYTES + 1)),
    ])
    with pytest.raises(UnsupportedResumeFormat, match="entry exceeds"):
        parse_resume("oversized.docx", data, user_id="u4")


def test_docx_rejects_excessive_archive_entry_count():
    import pytest

    entries = [
        ("[Content_Types].xml", b"<Types/>"),
        ("word/document.xml", b"<document/>"),
    ]
    entries.extend((f"word/extra-{i}.xml", b"x") for i in range(MAX_DOCX_ENTRIES))
    data = _zip_with_entries(entries)
    with pytest.raises(UnsupportedResumeFormat, match="too many archive entries"):
        parse_resume("many-entries.docx", data, user_id="u5")


def test_docx_rejects_malformed_zip_package():
    import pytest

    with pytest.raises(UnsupportedResumeFormat, match="Invalid or unreadable DOCX"):
        parse_resume("broken.docx", b"not a zip archive", user_id="u6")
