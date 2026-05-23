"""
Document processing pipeline
  PDF  → PyMuPDF (text layer) or OCR.Space (scanned)
  DOCX → python-docx
  TXT  → plain read
"""
from __future__ import annotations

import io
import os
import re
import tempfile
from pathlib import Path
from typing import Optional

import requests

from config import OCR_SPACE_API_KEY


# ─────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────

def _clean(text: str) -> str:
    """Basic cleaning: collapse whitespace, remove form-feeds."""
    text = text.replace("\f", "\n")
    text = re.sub(r"\n{3,}", "\n\n", text)
    text = re.sub(r"[ \t]+", " ", text)
    return text.strip()


# ─────────────────────────────────────────────────────────────────
# OCR.Space
# ─────────────────────────────────────────────────────────────────

def _ocr_space(file_bytes: bytes, filename: str) -> str:
    """Send file to OCR.Space API and return extracted text."""
    url = "https://api.ocr.space/parse/image"
    payload = {
        "apikey": OCR_SPACE_API_KEY,
        "language": "eng",
        "isOverlayRequired": False,
        "detectOrientation": True,
        "scale": True,
        "OCREngine": 2,
    }
    files = {"file": (filename, file_bytes, "application/pdf")}
    try:
        resp = requests.post(url, data=payload, files=files, timeout=120)
        resp.raise_for_status()
        result = resp.json()
        if result.get("IsErroredOnProcessing"):
            raise RuntimeError(result.get("ErrorMessage", "OCR.Space error"))
        pages = result.get("ParsedResults", [])
        return "\n\n".join(p["ParsedText"] for p in pages if p.get("ParsedText"))
    except Exception as exc:
        raise RuntimeError(f"OCR.Space failed: {exc}") from exc


# ─────────────────────────────────────────────────────────────────
# PDF
# ─────────────────────────────────────────────────────────────────

def _is_scanned_pdf(file_bytes: bytes) -> bool:
    """Return True if the PDF has very little selectable text (i.e. scanned)."""
    try:
        import fitz  # PyMuPDF
        doc = fitz.open(stream=file_bytes, filetype="pdf")
        char_count = sum(len(page.get_text()) for page in doc)
        doc.close()
        # Heuristic: fewer than 100 chars per page → likely scanned
        return char_count < 100 * len(doc)
    except Exception:
        return False


def extract_pdf(file_bytes: bytes, filename: str = "document.pdf") -> tuple[str, list[str]]:
    """
    Returns (full_text, page_texts).
    Tries PyMuPDF first; falls back to OCR.Space for scanned PDFs.
    """
    import fitz

    doc = fitz.open(stream=file_bytes, filetype="pdf")
    page_texts: list[str] = []

    for page in doc:
        page_texts.append(page.get_text())

    doc.close()
    full_text = "\n\n".join(page_texts)

    if _is_scanned_pdf(file_bytes):
        try:
            ocr_text = _ocr_space(file_bytes, filename)
            if ocr_text.strip():
                # Re-split by approximate page boundaries
                approx_pages = ocr_text.split("\n\n")
                return _clean(ocr_text), [_clean(p) for p in approx_pages]
        except RuntimeError:
            pass  # Fall back to PyMuPDF output even if poor quality

    return _clean(full_text), [_clean(p) for p in page_texts]


# ─────────────────────────────────────────────────────────────────
# DOCX
# ─────────────────────────────────────────────────────────────────

def extract_docx(file_bytes: bytes) -> tuple[str, list[str]]:
    """Returns (full_text, paragraphs)."""
    from docx import Document

    doc = Document(io.BytesIO(file_bytes))
    paragraphs = [p.text for p in doc.paragraphs if p.text.strip()]
    full_text = "\n\n".join(paragraphs)
    return _clean(full_text), paragraphs


# ─────────────────────────────────────────────────────────────────
# TXT
# ─────────────────────────────────────────────────────────────────

def extract_txt(file_bytes: bytes) -> tuple[str, list[str]]:
    text = file_bytes.decode("utf-8", errors="replace")
    lines = [l for l in text.splitlines() if l.strip()]
    return _clean(text), lines


# ─────────────────────────────────────────────────────────────────
# Public dispatcher
# ─────────────────────────────────────────────────────────────────

def extract_text(file_bytes: bytes, filename: str) -> tuple[str, list[str], str]:
    """
    Detect file type and extract text.
    Returns (full_text, pages_or_sections, detected_type).
    """
    ext = Path(filename).suffix.lower()

    if ext == ".pdf":
        text, pages = extract_pdf(file_bytes, filename)
        return text, pages, "pdf"
    elif ext in (".docx", ".doc"):
        text, sections = extract_docx(file_bytes)
        return text, sections, "docx"
    elif ext == ".txt":
        text, lines = extract_txt(file_bytes)
        return text, lines, "txt"
    else:
        raise ValueError(f"Unsupported file type: {ext}")
