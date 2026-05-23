"""
Metadata extraction from academic paper text.
Extracts: title, authors, abstract, journal, date, DOI, keywords, page count.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field, asdict
from typing import Optional


@dataclass
class PaperMetadata:
    title: str = "Unknown Title"
    authors: list[str] = field(default_factory=list)
    abstract: str = ""
    journal: str = ""
    year: str = ""
    doi: str = ""
    keywords: list[str] = field(default_factory=list)
    page_count: int = 0
    filename: str = ""

    def to_dict(self) -> dict:
        return asdict(self)


# ─────────────────────────────────────────────────────────────────
# Patterns
# ─────────────────────────────────────────────────────────────────

_DOI_RE      = re.compile(r"10\.\d{4,}/[^\s]+", re.IGNORECASE)
_YEAR_RE     = re.compile(r"\b(19|20)\d{2}\b")
_ABSTRACT_RE = re.compile(
    r"(?:abstract|summary)[:\s—–-]*(.+?)(?=\n(?:keywords?|introduction|1[\.\s]|$))",
    re.IGNORECASE | re.DOTALL,
)
_KEYWORDS_RE = re.compile(
    r"keywords?[:\s—–-]*(.+?)(?=\n[A-Z\d]|\Z)",
    re.IGNORECASE | re.DOTALL,
)
_JOURNAL_PATTERNS = [
    re.compile(p, re.IGNORECASE) for p in [
        r"(?:published in|journal of|proceedings of|transactions on|conference on)[^\n]+",
        r"(?:IEEE|ACM|Nature|Science|Elsevier|Springer)[^\n]+",
        r"(?:vol\.?|volume)\s*\d+",
    ]
]

# Author heuristic: lines near the top that look like name lists
_AUTHOR_LINE_RE = re.compile(
    r"^(?:[A-Z][a-z]+(?:\s+[A-Z]\.?)?\s+[A-Z][a-z]+)(?:\s*,\s*[A-Z][a-z]+(?:\s+[A-Z]\.?)?\s+[A-Z][a-z]+)*$"
)


def _extract_doi(text: str) -> str:
    m = _DOI_RE.search(text)
    return m.group(0).rstrip(".,)") if m else ""


def _extract_year(text: str) -> str:
    years = _YEAR_RE.findall(text[:3000])
    return years[0] if years else ""


def _extract_abstract(text: str) -> str:
    m = _ABSTRACT_RE.search(text)
    if m:
        raw = m.group(1).strip()
        return re.sub(r"\s+", " ", raw)[:2000]
    return ""


def _extract_keywords(text: str) -> list[str]:
    m = _KEYWORDS_RE.search(text)
    if not m:
        return []
    raw = m.group(1).strip().split("\n")[0]  # First line only
    kws = re.split(r"[;,|·•]\s*", raw)
    return [k.strip() for k in kws if 2 < len(k.strip()) < 60][:10]


def _extract_journal(text: str) -> str:
    for pat in _JOURNAL_PATTERNS:
        m = pat.search(text[:4000])
        if m:
            return m.group(0).strip()[:200]
    return ""


def _extract_title(text: str) -> str:
    """Take the first non-trivial line from the document as a title guess."""
    for line in text.splitlines():
        line = line.strip()
        if len(line) > 15 and not line.lower().startswith(("abstract", "http", "doi", "©", "copyright")):
            return line[:250]
    return "Unknown Title"


def _extract_authors(text: str) -> list[str]:
    """Heuristic: look for author-like lines in first 30 lines."""
    lines = [l.strip() for l in text.splitlines()[:30] if l.strip()]
    authors: list[str] = []
    for line in lines:
        if _AUTHOR_LINE_RE.match(line):
            parts = re.split(r"\s*,\s*", line)
            authors.extend(p.strip() for p in parts if p.strip())
    return authors[:10]


# ─────────────────────────────────────────────────────────────────
# Public
# ─────────────────────────────────────────────────────────────────

def extract_metadata(text: str, filename: str = "", page_count: int = 0) -> PaperMetadata:
    return PaperMetadata(
        title=_extract_title(text),
        authors=_extract_authors(text),
        abstract=_extract_abstract(text),
        journal=_extract_journal(text),
        year=_extract_year(text),
        doi=_extract_doi(text),
        keywords=_extract_keywords(text),
        page_count=page_count,
        filename=filename,
    )
