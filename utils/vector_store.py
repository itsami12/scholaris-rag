"""
Qdrant vector store + Nomic embedding generation.
"""
from __future__ import annotations

import uuid
from typing import Any

import requests
from qdrant_client import QdrantClient
from qdrant_client.http.models import (
    Distance,
    PointStruct,
    VectorParams,
    Filter,
    FieldCondition,
    MatchValue,
)

from config import (
    NOMIC_API_KEY,
    NOMIC_MODEL,
    QDRANT_API_KEY,
    QDRANT_URL,
    QDRANT_COLLECTION,
)
from utils.chunker import Chunk

EMBEDDING_DIM = 768  # nomic-embed-text-v1.5 output dimension


# ─────────────────────────────────────────────────────────────────
# Nomic embeddings
# ─────────────────────────────────────────────────────────────────

def embed_texts(texts: list[str]) -> list[list[float]]:
    """Batch embed texts using the Nomic API."""
    url = "https://api-atlas.nomic.ai/v1/embedding/text"
    headers = {
        "Authorization": f"Bearer {NOMIC_API_KEY}",
        "Content-Type": "application/json",
    }
    # Nomic recommends task_type for retrieval
    payload = {
        "model": NOMIC_MODEL,
        "texts": texts,
        "task_type": "search_document",
    }
    resp = requests.post(url, json=payload, headers=headers, timeout=60)
    resp.raise_for_status()
    return resp.json()["embeddings"]


def embed_query(query: str) -> list[float]:
    """Embed a single query text (different task_type for retrieval)."""
    url = "https://api-atlas.nomic.ai/v1/embedding/text"
    headers = {
        "Authorization": f"Bearer {NOMIC_API_KEY}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": NOMIC_MODEL,
        "texts": [query],
        "task_type": "search_query",
    }
    resp = requests.post(url, json=payload, headers=headers, timeout=30)
    resp.raise_for_status()
    return resp.json()["embeddings"][0]


# ─────────────────────────────────────────────────────────────────
# Qdrant client
# ─────────────────────────────────────────────────────────────────

class VectorStore:
    def __init__(self) -> None:
        self._client = QdrantClient(
            url=QDRANT_URL,
            api_key=QDRANT_API_KEY,
            timeout=60,
        )
        self._ensure_collection()

    def _ensure_collection(self) -> None:
        existing = [c.name for c in self._client.get_collections().collections]
        if QDRANT_COLLECTION not in existing:
            self._client.create_collection(
                collection_name=QDRANT_COLLECTION,
                vectors_config=VectorParams(size=EMBEDDING_DIM, distance=Distance.COSINE),
            )

    # ── Upsert chunks ─────────────────────────────────────────────

    def upsert_chunks(
        self,
        chunks: list[Chunk],
        paper_id: str,
        metadata: dict,
        batch_size: int = 32,
    ) -> list[str]:
        """Embed and upsert all chunks. Returns list of chunk_ids."""
        chunk_ids: list[str] = []
        points: list[PointStruct] = []

        texts = [c.text for c in chunks]

        # Batch embed
        all_embeddings: list[list[float]] = []
        for i in range(0, len(texts), batch_size):
            batch = texts[i : i + batch_size]
            all_embeddings.extend(embed_texts(batch))

        for chunk, embedding in zip(chunks, all_embeddings):
            cid = str(uuid.uuid4())
            chunk_ids.append(cid)
            points.append(
                PointStruct(
                    id=cid,
                    vector=embedding,
                    payload={
                        "chunk_id":    cid,
                        "paper_id":    paper_id,
                        "chunk_index": chunk.chunk_index,
                        "page_hint":   chunk.page_hint,
                        "text":        chunk.text,
                        "title":       metadata.get("title", ""),
                        "authors":     metadata.get("authors", []),
                        "year":        metadata.get("year", ""),
                        "filename":    metadata.get("filename", ""),
                    },
                )
            )

        # Upsert in batches
        for i in range(0, len(points), batch_size):
            self._client.upsert(
                collection_name=QDRANT_COLLECTION,
                points=points[i : i + batch_size],
            )

        return chunk_ids

    # ── Search ────────────────────────────────────────────────────

    def search(
        self,
        query: str,
        top_k: int = 6,
        paper_id: str | None = None,
    ) -> list[dict[str, Any]]:
        """Semantic search. Optionally filter by paper_id."""
        q_vec = embed_query(query)

        query_filter = None
        if paper_id:
            query_filter = Filter(
                must=[
                    FieldCondition(
                        key="paper_id",
                        match=MatchValue(value=paper_id),
                    )
                ]
            )

        results = self._client.search(
            collection_name=QDRANT_COLLECTION,
            query_vector=q_vec,
            limit=top_k,
            query_filter=query_filter,
            with_payload=True,
        )

        return [
            {
                "score":       r.score,
                "text":        r.payload["text"],
                "chunk_index": r.payload["chunk_index"],
                "page_hint":   r.payload["page_hint"],
                "paper_id":    r.payload["paper_id"],
                "title":       r.payload.get("title", ""),
                "authors":     r.payload.get("authors", []),
                "year":        r.payload.get("year", ""),
                "filename":    r.payload.get("filename", ""),
            }
            for r in results
        ]

    # ── Delete by paper ───────────────────────────────────────────

    def delete_paper_chunks(self, paper_id: str) -> None:
        self._client.delete(
            collection_name=QDRANT_COLLECTION,
            points_selector=Filter(
                must=[
                    FieldCondition(key="paper_id", match=MatchValue(value=paper_id))
                ]
            ),
        )
