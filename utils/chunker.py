"""
Text chunking with overlap.
Each chunk carries: text, chunk_index, page_hint, char_start, char_end.
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass
class Chunk:
    text: str
    chunk_index: int
    page_hint: int       # approximate page number (0-based)
    char_start: int
    char_end: int


def chunk_text(
    full_text: str,
    page_texts: list[str],
    chunk_size: int = 800,
    overlap: int = 150,
) -> list[Chunk]:
    """
    Split full_text into overlapping chunks.
    page_hint is estimated by character offset vs cumulative page lengths.
    """
    # Build cumulative page offsets so we can map char_pos → page
    page_offsets: list[int] = []
    offset = 0
    for pt in page_texts:
        page_offsets.append(offset)
        offset += len(pt) + 2  # +2 for the "\n\n" join

    def _page_of(char_pos: int) -> int:
        page = 0
        for i, off in enumerate(page_offsets):
            if char_pos >= off:
                page = i
            else:
                break
        return page

    chunks: list[Chunk] = []
    start = 0
    idx = 0
    text_len = len(full_text)

    while start < text_len:
        end = min(start + chunk_size, text_len)
        # Try to break at sentence boundary
        if end < text_len:
            for sep in (". ", ".\n", "\n\n", "\n", " "):
                pos = full_text.rfind(sep, start + overlap, end)
                if pos != -1:
                    end = pos + len(sep)
                    break

        snippet = full_text[start:end].strip()
        if snippet:
            chunks.append(Chunk(
                text=snippet,
                chunk_index=idx,
                page_hint=_page_of(start) + 1,  # 1-based
                char_start=start,
                char_end=end,
            ))
            idx += 1

        next_start = end - overlap
        if next_start <= start:
            next_start = start + 1
        start = next_start

    return chunks
