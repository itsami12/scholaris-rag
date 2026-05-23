"""
Chat History Manager
--------------------
Persists all conversations in  ./chat_history/<session_id>.json
Each session = one "conversation thread" (like a GPT sidebar item).

Structure of a session file:
{
  "session_id": "...",
  "title": "First question asked",
  "created_at": "ISO-8601",
  "updated_at": "ISO-8601",
  "paper_id": "optional paper filter",
  "paper_title": "optional",
  "messages": [
    {
      "role": "user" | "assistant",
      "content": "...",
      "timestamp": "ISO-8601",
      "sources": []          # only on assistant turns
    }
  ]
}
"""
from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

HISTORY_DIR = Path("chat_history")
HISTORY_DIR.mkdir(exist_ok=True)

MAX_CONTEXT_TURNS = 10          # how many prior turns to send to the LLM
TITLE_MAX_CHARS   = 60


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _session_path(session_id: str) -> Path:
    return HISTORY_DIR / f"{session_id}.json"


# ─────────────────────────────────────────────────────────────────
# CRUD
# ─────────────────────────────────────────────────────────────────

def create_session(
    paper_id: Optional[str] = None,
    paper_title: Optional[str] = None,
) -> dict:
    """Create a brand-new session and persist it."""
    session = {
        "session_id":  str(uuid.uuid4()),
        "title":       "New conversation",
        "created_at":  _now(),
        "updated_at":  _now(),
        "paper_id":    paper_id,
        "paper_title": paper_title or "",
        "messages":    [],
    }
    _save(session)
    return session


def load_session(session_id: str) -> Optional[dict]:
    path = _session_path(session_id)
    if not path.exists():
        return None
    with path.open(encoding="utf-8") as f:
        return json.load(f)


def list_sessions() -> list[dict]:
    """Return all sessions sorted newest-first (summary only, no messages)."""
    sessions = []
    for p in HISTORY_DIR.glob("*.json"):
        try:
            with p.open(encoding="utf-8") as f:
                s = json.load(f)
            sessions.append({
                "session_id":  s["session_id"],
                "title":       s["title"],
                "created_at":  s["created_at"],
                "updated_at":  s["updated_at"],
                "paper_title": s.get("paper_title", ""),
                "message_count": len(s.get("messages", [])),
            })
        except Exception:
            continue
    return sorted(sessions, key=lambda x: x["updated_at"], reverse=True)


def add_message(
    session_id: str,
    role: str,
    content: str,
    sources: Optional[list] = None,
) -> dict:
    """Append a message to a session and save."""
    session = load_session(session_id)
    if session is None:
        raise ValueError(f"Session {session_id} not found")

    msg = {
        "role":      role,
        "content":   content,
        "timestamp": _now(),
    }
    if sources is not None:
        msg["sources"] = sources

    session["messages"].append(msg)
    session["updated_at"] = _now()

    # Auto-title: use first user message (truncated)
    if session["title"] == "New conversation" and role == "user":
        session["title"] = content[:TITLE_MAX_CHARS] + ("…" if len(content) > TITLE_MAX_CHARS else "")

    _save(session)
    return msg


def delete_session(session_id: str) -> bool:
    path = _session_path(session_id)
    if path.exists():
        path.unlink()
        return True
    return False


def delete_all_sessions() -> int:
    count = 0
    for p in HISTORY_DIR.glob("*.json"):
        p.unlink()
        count += 1
    return count


def rename_session(session_id: str, new_title: str) -> bool:
    session = load_session(session_id)
    if session is None:
        return False
    session["title"] = new_title[:TITLE_MAX_CHARS]
    _save(session)
    return True


# ─────────────────────────────────────────────────────────────────
# Context window helper
# ─────────────────────────────────────────────────────────────────

def get_context_messages(session_id: str) -> list[dict]:
    """
    Return the last MAX_CONTEXT_TURNS pairs as
    [{"role": ..., "content": ...}] suitable for the LLM.
    Sources are stripped — the LLM doesn't need them.
    """
    session = load_session(session_id)
    if not session:
        return []
    msgs = session.get("messages", [])
    tail = msgs[-(MAX_CONTEXT_TURNS * 2):]   # pairs
    return [{"role": m["role"], "content": m["content"]} for m in tail]


# ─────────────────────────────────────────────────────────────────
# Markdown export
# ─────────────────────────────────────────────────────────────────

def export_session_markdown(session_id: str) -> Optional[str]:
    """Render a full session as a Markdown string."""
    session = load_session(session_id)
    if not session:
        return None

    lines: list[str] = []
    lines.append(f"# {session['title']}")
    lines.append("")

    meta_parts = [f"**Created:** {session['created_at'][:10]}"]
    if session.get("paper_title"):
        meta_parts.append(f"**Paper:** {session['paper_title']}")
    lines.append(" · ".join(meta_parts))
    lines.append("")
    lines.append("---")
    lines.append("")

    for msg in session.get("messages", []):
        ts  = msg["timestamp"][:16].replace("T", " ")
        role_label = "🧑 **You**" if msg["role"] == "user" else "🤖 **Scholaris**"
        lines.append(f"### {role_label} — {ts}")
        lines.append("")
        lines.append(msg["content"])

        # Attach cited sources for assistant turns
        sources = msg.get("sources", [])
        if sources:
            lines.append("")
            lines.append("**Sources cited:**")
            for s in sources[:3]:
                title   = s.get("title", "Unknown")
                page    = s.get("page_hint", "?")
                score   = s.get("score", 0)
                lines.append(f"- *{title}* — Page {page} (relevance: {score:.2f})")

        lines.append("")
        lines.append("---")
        lines.append("")

    return "\n".join(lines)


def export_all_markdown() -> str:
    """Export every session as one big Markdown document."""
    sessions = list_sessions()
    if not sessions:
        return "# Scholaris Chat History\n\nNo conversations yet."

    parts: list[str] = ["# Scholaris — Full Chat History\n"]
    parts.append(f"Exported {_now()[:10]}  |  {len(sessions)} conversation(s)\n")
    parts.append("---\n")

    for s in sessions:
        md = export_session_markdown(s["session_id"])
        if md:
            parts.append(md)
            parts.append("\n\n")

    return "\n".join(parts)


# ─────────────────────────────────────────────────────────────────
# Internal
# ─────────────────────────────────────────────────────────────────

def _save(session: dict) -> None:
    path = _session_path(session["session_id"])
    with path.open("w", encoding="utf-8") as f:
        json.dump(session, f, ensure_ascii=False, indent=2)
