"""Render docs/GETTING_STARTED.md to a nicely styled PDF using WeasyPrint.

Run from the repository root:
    python backend/scripts/build_getting_started_pdf.py
"""
from __future__ import annotations

import re
import sys
from html import escape
from pathlib import Path

from weasyprint import HTML


CSS = """
@page {
    size: Letter;
    margin: 22mm 20mm 24mm 20mm;
    @bottom-center {
        content: "Job Finder AI — Getting Started    ·    page " counter(page) " of " counter(pages);
        font-family: -apple-system, "Helvetica Neue", Arial, sans-serif;
        font-size: 9pt;
        color: #7a7a7a;
    }
}
* { box-sizing: border-box; }
body {
    font-family: -apple-system, "Helvetica Neue", Arial, sans-serif;
    font-size: 11pt;
    line-height: 1.55;
    color: #1a1a1a;
}
h1 {
    font-size: 26pt;
    margin: 0 0 6pt 0;
    color: #0b3d91;
    border-bottom: 3px solid #0b3d91;
    padding-bottom: 8pt;
}
h1 + p { color: #555; margin-top: 4pt; }
h2 {
    font-size: 17pt;
    margin: 22pt 0 8pt 0;
    color: #0b3d91;
    page-break-after: avoid;
}
h3 {
    font-size: 13pt;
    margin: 14pt 0 4pt 0;
    color: #2a2a2a;
    page-break-after: avoid;
}
p { margin: 6pt 0; }
hr { border: none; border-top: 1px solid #d0d0d0; margin: 18pt 0; }
ul, ol { margin: 6pt 0 6pt 22pt; }
li { margin: 3pt 0; }
strong { color: #0b3d91; }
code {
    font-family: "SF Mono", Menlo, Consolas, monospace;
    font-size: 10pt;
    background: #f0f2f5;
    padding: 1pt 4pt;
    border-radius: 3px;
}
pre {
    background: #0f172a;
    color: #e2e8f0;
    padding: 10pt 12pt;
    border-radius: 6px;
    font-size: 9.5pt;
    line-height: 1.4;
    overflow-wrap: anywhere;
    white-space: pre-wrap;
    page-break-inside: avoid;
    margin: 8pt 0;
}
pre code {
    background: transparent;
    color: inherit;
    padding: 0;
    font-size: inherit;
}
a { color: #0b57d0; text-decoration: none; }
blockquote {
    border-left: 4px solid #0b3d91;
    background: #eef3fb;
    padding: 8pt 12pt;
    margin: 8pt 0;
    color: #1a1a1a;
    border-radius: 4px;
    page-break-inside: avoid;
}
.callout-note {
    background: #fff8e1;
    border-left: 4px solid #f59e0b;
    padding: 8pt 12pt;
    margin: 8pt 0;
    border-radius: 4px;
}
.toc {
    background: #f7f9fc;
    padding: 10pt 14pt;
    border-radius: 6px;
    margin: 14pt 0 20pt 0;
    page-break-inside: avoid;
}
.toc h3 { margin-top: 0; color: #0b3d91; }
.toc ol { margin-left: 18pt; }
.footer-note {
    margin-top: 18pt;
    padding-top: 10pt;
    border-top: 1px solid #d0d0d0;
    font-size: 9pt;
    color: #666;
}
"""


def md_to_html(md: str) -> str:
    """Small, purposeful markdown → HTML converter.

    Handles: headings, paragraphs, unordered/ordered lists, fenced code blocks,
    inline code, bold, links, blockquotes, hr. Deliberately avoids adding a
    heavy dependency for a doc-shaped file we control.
    """
    lines = md.splitlines()
    out: list[str] = []
    i = 0
    in_ul = False
    in_ol = False

    def close_lists() -> None:
        nonlocal in_ul, in_ol
        if in_ul:
            out.append("</ul>")
            in_ul = False
        if in_ol:
            out.append("</ol>")
            in_ol = False

    while i < len(lines):
        line = lines[i]

        # fenced code block
        if line.startswith("```"):
            close_lists()
            i += 1
            buf: list[str] = []
            while i < len(lines) and not lines[i].startswith("```"):
                buf.append(lines[i])
                i += 1
            i += 1  # skip closing ```
            out.append("<pre><code>" + escape("\n".join(buf)) + "</code></pre>")
            continue

        # horizontal rule
        if line.strip() == "---":
            close_lists()
            out.append("<hr />")
            i += 1
            continue

        # blockquote (single line, sufficient for our doc)
        m = re.match(r"^\s*>\s?(.*)", line)
        if m:
            close_lists()
            out.append("<blockquote>" + _inline(m.group(1)) + "</blockquote>")
            i += 1
            continue

        # headings
        m = re.match(r"^(#{1,3})\s+(.*)$", line)
        if m:
            close_lists()
            level = len(m.group(1))
            out.append(f"<h{level}>{_inline(m.group(2))}</h{level}>")
            i += 1
            continue

        # unordered list
        m = re.match(r"^\s*[-*]\s+(.*)$", line)
        if m:
            if not in_ul:
                close_lists()
                out.append("<ul>")
                in_ul = True
            out.append("<li>" + _inline(m.group(1)) + "</li>")
            i += 1
            continue

        # ordered list
        m = re.match(r"^\s*\d+\.\s+(.*)$", line)
        if m:
            if not in_ol:
                close_lists()
                out.append("<ol>")
                in_ol = True
            out.append("<li>" + _inline(m.group(1)) + "</li>")
            i += 1
            continue

        # blank line
        if not line.strip():
            close_lists()
            i += 1
            continue

        # paragraph — collect consecutive non-blank/non-block lines
        para: list[str] = [line]
        i += 1
        while i < len(lines) and lines[i].strip() and not _is_block_start(lines[i]):
            para.append(lines[i])
            i += 1
        close_lists()
        out.append("<p>" + _inline(" ".join(para)) + "</p>")

    close_lists()
    return "\n".join(out)


def _is_block_start(line: str) -> bool:
    return (
        line.startswith("#")
        or line.startswith("```")
        or line.strip() == "---"
        or bool(re.match(r"^\s*[-*]\s+", line))
        or bool(re.match(r"^\s*\d+\.\s+", line))
        or bool(re.match(r"^\s*>", line))
    )


_INLINE_CODE_RE = re.compile(r"`([^`]+)`")
_BOLD_RE = re.compile(r"\*\*([^*]+)\*\*")
_ITALIC_RE = re.compile(r"(?<!\*)\*([^*]+)\*(?!\*)")
_LINK_RE = re.compile(r"\[([^\]]+)\]\(([^)]+)\)")
_AUTOLINK_RE = re.compile(r"<((?:https?://|mailto:)[^>]+)>")


def _inline(text: str) -> str:
    """Escape + apply inline formatting. Order matters: escape first, then re-inject tags."""
    # Protect code spans by replacing with placeholders before escaping.
    spans: list[str] = []

    def _cap(m):
        spans.append(m.group(1))
        return f"\x00CODE{len(spans) - 1}\x00"

    text = _INLINE_CODE_RE.sub(_cap, text)
    text = escape(text)
    # restore code spans (already escape-safe because we escape their content here)
    for idx, s in enumerate(spans):
        text = text.replace(f"\x00CODE{idx}\x00", f"<code>{escape(s)}</code>")
    text = _BOLD_RE.sub(r"<strong>\1</strong>", text)
    text = _ITALIC_RE.sub(r"<em>\1</em>", text)
    text = _LINK_RE.sub(r'<a href="\2">\1</a>', text)
    text = _AUTOLINK_RE.sub(r'<a href="\1">\1</a>', text)
    return text


def build(md_path: Path, out_path: Path) -> Path:
    md = md_path.read_text(encoding="utf-8")
    body_html = md_to_html(md)
    full_html = f"""<!doctype html>
<html><head><meta charset="utf-8"><title>Job Finder AI — Getting Started</title>
<style>{CSS}</style></head>
<body>
{body_html}
<div class="footer-note">
Generated from <code>docs/GETTING_STARTED.md</code>. Repository:
<a href="https://github.com/dilipgaikwads/job-finder-ai">github.com/dilipgaikwads/job-finder-ai</a>.
</div>
</body></html>"""
    out_path.parent.mkdir(parents=True, exist_ok=True)
    HTML(string=full_html).write_pdf(str(out_path))
    return out_path


if __name__ == "__main__":
    root = Path(__file__).resolve().parents[2]
    md_path = root / "docs" / "GETTING_STARTED.md"
    out_path = root / "docs" / "Job-Finder-AI-Getting-Started.pdf"
    result = build(md_path, out_path)
    print(f"wrote {result}")
    sys.exit(0)
