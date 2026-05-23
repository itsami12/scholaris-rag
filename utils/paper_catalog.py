"""Local paper catalog for uploaded documents.

This keeps a lightweight, persistent index of ingested papers so the UI can
list papers even if the graph database is temporarily unavailable.
"""
from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from threading import Lock
from typing import Any

CATALOG_PATH = Path(os.getenv("PAPER_CATALOG_PATH", "chat_history/papers.json"))
CATALOG_PATH.parent.mkdir(parents=True, exist_ok=True)

_LOCK = Lock()


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _read_all() -> list[dict[str, Any]]:
    if not CATALOG_PATH.exists():
        return []
    try:
        with CATALOG_PATH.open(encoding="utf-8") as f:
            data = json.load(f)
    except Exception:
        return []

    if isinstance(data, list):
        return [item for item in data if isinstance(item, dict)]
    return []


def _write_all(records: list[dict[str, Any]]) -> None:
    tmp_path = CATALOG_PATH.with_suffix(".tmp")
    with tmp_path.open("w", encoding="utf-8") as f:
        json.dump(records, f, ensure_ascii=False, indent=2)
    tmp_path.replace(CATALOG_PATH)


def upsert_paper(record: dict[str, Any]) -> dict[str, Any]:
    paper_id = record.get("paper_id")
    if not paper_id:
        raise ValueError("paper_id is required")

    with _LOCK:
        records = _read_all()
        updated = []
        for item in records:
            if item.get("paper_id") != paper_id:
                updated.append(item)

        stored = dict(record)
        stored.setdefault("uploaded_at", _now())
        updated.append(stored)
        _write_all(updated)
        return stored


def find_paper_by_hash(file_hash: str) -> dict[str, Any] | None:
    for item in _read_all():
        if item.get("file_hash") == file_hash:
            return item
    return None


def list_papers() -> list[dict[str, Any]]:
    records = _read_all()
    return sorted(records, key=lambda item: item.get("uploaded_at", ""), reverse=True)


def get_paper(paper_id: str) -> dict[str, Any] | None:
    for item in _read_all():
        if item.get("paper_id") == paper_id:
            return item
    return None


def delete_paper(paper_id: str) -> bool:
    with _LOCK:
        records = [item for item in _read_all() if item.get("paper_id") != paper_id]
        _write_all(records)
        return True