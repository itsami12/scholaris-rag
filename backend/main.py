"""
Scholaris FastAPI Backend  v2.0
─────────────────────────────────────────────────────────────────
Document endpoints
  POST   /upload                    ingest PDF / DOCX / TXT
  GET    /papers                    list all papers
  GET    /papers/{id}               paper metadata
  DELETE /papers/{id}               delete paper + vectors

Chat endpoints
  POST   /chat                      RAG chat (session-aware)
  POST   /summarize/{paper_id}      summarize a paper

History endpoints
  GET    /history                   list all sessions
  GET    /history/{sid}             get full session
  DELETE /history/{sid}             delete one session
  DELETE /history                   delete ALL sessions
  PATCH  /history/{sid}/rename      rename a session
  GET    /history/{sid}/export      export session as Markdown
  GET    /history/export/all        export ALL history as Markdown

Misc
  GET    /health
"""
from __future__ import annotations

import uuid
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import PlainTextResponse
from pydantic import BaseModel

from utils.document_processor import extract_text
from utils.metadata_extractor  import extract_metadata
from utils.chunker              import chunk_text
from utils.paper_catalog        import upsert_paper as catalog_upsert_paper
from utils.paper_catalog        import list_papers as catalog_list_papers
from utils.paper_catalog        import get_paper as catalog_get_paper
from utils.paper_catalog        import delete_paper as catalog_delete_paper
from utils.graph_store          import GraphStore
from utils.vector_store         import VectorStore
from utils.llm                  import chat_with_paper, summarize_paper
from utils.history_manager      import (
    create_session, load_session, list_sessions,
    add_message, delete_session, delete_all_sessions,
    rename_session, get_context_messages,
    export_session_markdown, export_all_markdown,
)

app = FastAPI(title="Scholaris API", version="2.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Singletons
graph  = GraphStore()
vector = VectorStore()
graph.ensure_constraints()


# ─────────────────────────────────────────────────────────────────
# Pydantic models
# ─────────────────────────────────────────────────────────────────

class ChatRequest(BaseModel):
    query:      str
    paper_id:   Optional[str] = None   # None → search all papers
    session_id: Optional[str] = None   # None → auto-create session


class ChatResponse(BaseModel):
    answer:     str
    sources:    list[dict]
    session_id: str


class RenameRequest(BaseModel):
    title: str


# ─────────────────────────────────────────────────────────────────
# Health
# ─────────────────────────────────────────────────────────────────

@app.get("/health")
def health() -> dict:
    return {"status": "ok", "service": "Scholaris", "version": "2.0.0"}


# ─────────────────────────────────────────────────────────────────
# Document endpoints
# ─────────────────────────────────────────────────────────────────

@app.post("/upload")
async def upload_document(file: UploadFile = File(...)) -> dict:
    allowed = {".pdf", ".docx", ".doc", ".txt"}
    ext = Path(file.filename).suffix.lower()
    if ext not in allowed:
        raise HTTPException(400, f"Unsupported file type: {ext}")

    content = await file.read()
    if len(content) > 50 * 1024 * 1024:
        raise HTTPException(413, "File too large (max 50 MB)")

    try:
        full_text, page_texts, doc_type = extract_text(content, file.filename)
    except Exception as exc:
        raise HTTPException(422, f"Text extraction failed: {exc}")

    if not full_text.strip():
        raise HTTPException(422, "No text could be extracted from the document.")

    metadata   = extract_metadata(full_text, filename=file.filename, page_count=len(page_texts))
    chunks     = chunk_text(full_text, page_texts)
    if not chunks:
        raise HTTPException(422, "Document produced no text chunks.")

    paper_id   = str(uuid.uuid4())
    warnings: list[str] = []

    try:
        graph.upsert_paper(paper_id, metadata)
    except Exception as exc:
        warnings.append(f"Graph store unavailable: {exc}")

    meta_dict  = metadata.to_dict()
    chunk_ids: list[str] = []
    try:
        chunk_ids = vector.upsert_chunks(chunks, paper_id, meta_dict)
    except Exception as exc:
        warnings.append(f"Vector store unavailable: {exc}")

    if chunk_ids:
        for chunk, cid in zip(chunks, chunk_ids):
            try:
                graph.register_chunk(paper_id, cid, chunk.chunk_index, chunk.page_hint)
            except Exception as exc:
                warnings.append(f"Chunk graph registration skipped: {exc}")
                break

    result = {
        "paper_id":    paper_id,
        "title":       metadata.title,
        "authors":     metadata.authors,
        "year":        metadata.year,
        "doi":         metadata.doi,
        "keywords":    metadata.keywords,
        "page_count":  metadata.page_count,
        "chunk_count": len(chunks),
        "doc_type":    doc_type,
        "message":     "Document ingested successfully.",
    }

    if warnings:
        result["warning"] = " ".join(warnings)
        result["message"] = "Document ingested with warnings."

    catalog_upsert_paper(result)

    return result


@app.get("/papers")
def list_papers() -> list[dict]:
    papers = catalog_list_papers()
    if papers:
        return papers
    return graph.list_papers()


@app.get("/papers/{paper_id}")
def get_paper(paper_id: str) -> dict:
    paper = graph.get_paper(paper_id)
    if not paper:
        paper = catalog_get_paper(paper_id) or {}
    if not paper:
        raise HTTPException(404, "Paper not found")
    return paper


@app.delete("/papers/{paper_id}")
def delete_paper(paper_id: str) -> dict:
    graph.delete_paper(paper_id)
    vector.delete_paper_chunks(paper_id)
    catalog_delete_paper(paper_id)
    return {"message": "Paper deleted", "paper_id": paper_id}


# ─────────────────────────────────────────────────────────────────
# Chat endpoint (session-aware)
# ─────────────────────────────────────────────────────────────────

@app.post("/chat", response_model=ChatResponse)
def chat(req: ChatRequest) -> ChatResponse:
    if not req.query.strip():
        raise HTTPException(400, "Query cannot be empty")

    # Resolve or create session
    if req.session_id:
        session = load_session(req.session_id)
        if session is None:
            raise HTTPException(404, f"Session {req.session_id} not found")
        session_id = req.session_id
    else:
        # Auto-create a new session
        paper_title = ""
        if req.paper_id:
            p = graph.get_paper(req.paper_id)
            paper_title = p.get("title", "") if p else ""
        session    = create_session(paper_id=req.paper_id, paper_title=paper_title)
        session_id = session["session_id"]

    # Persist user message
    add_message(session_id, "user", req.query)

    # Build conversation history for LLM context
    history = get_context_messages(session_id)
    # Remove the last user message (we pass it separately via retrieved context)
    if history and history[-1]["role"] == "user":
        history = history[:-1]

    # Retrieve relevant chunks
    chunks = vector.search(req.query, top_k=6, paper_id=req.paper_id)

    # Generate answer
    answer = chat_with_paper(req.query, chunks, history=history)

    # Persist assistant message (with sources)
    add_message(session_id, "assistant", answer, sources=chunks)

    return ChatResponse(answer=answer, sources=chunks, session_id=session_id)


# ─────────────────────────────────────────────────────────────────
# Summarize
# ─────────────────────────────────────────────────────────────────

@app.post("/summarize/{paper_id}")
def summarize(paper_id: str) -> dict:
    paper = graph.get_paper(paper_id)
    if not paper:
        paper = catalog_get_paper(paper_id) or {}
    if not paper:
        raise HTTPException(404, "Paper not found")
    summary = summarize_paper(
        abstract=paper.get("abstract", ""),
        title=paper.get("title", "Unknown"),
    )
    return {"paper_id": paper_id, "title": paper.get("title"), "summary": summary}


# ─────────────────────────────────────────────────────────────────
# History endpoints
# ─────────────────────────────────────────────────────────────────

@app.get("/history")
def get_all_history() -> list[dict]:
    """List all chat sessions (newest first)."""
    return list_sessions()


@app.get("/history/export/all", response_class=PlainTextResponse)
def export_all_history() -> str:
    """Download entire chat history as Markdown."""
    return export_all_markdown()


@app.get("/history/{session_id}")
def get_session(session_id: str) -> dict:
    session = load_session(session_id)
    if not session:
        raise HTTPException(404, "Session not found")
    return session


@app.delete("/history/{session_id}")
def remove_session(session_id: str) -> dict:
    ok = delete_session(session_id)
    if not ok:
        raise HTTPException(404, "Session not found")
    return {"message": "Session deleted", "session_id": session_id}


@app.delete("/history")
def clear_all_history() -> dict:
    count = delete_all_sessions()
    return {"message": f"Deleted {count} session(s)"}


@app.patch("/history/{session_id}/rename")
def rename(session_id: str, body: RenameRequest) -> dict:
    ok = rename_session(session_id, body.title)
    if not ok:
        raise HTTPException(404, "Session not found")
    return {"message": "Renamed", "session_id": session_id, "title": body.title}


@app.get("/history/{session_id}/export", response_class=PlainTextResponse)
def export_session(session_id: str) -> str:
    md = export_session_markdown(session_id)
    if md is None:
        raise HTTPException(404, "Session not found")
    return md
