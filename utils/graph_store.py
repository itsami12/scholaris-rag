"""
Neo4j Aura graph store.
Nodes: Paper, Author, Keyword, Journal
Relationships: AUTHORED_BY, HAS_KEYWORD, PUBLISHED_IN, HAS_CHUNK
"""
from __future__ import annotations

import uuid
from typing import Any

from neo4j import GraphDatabase
from neo4j.exceptions import Neo4jError, ServiceUnavailable, SessionExpired

from config import NEO4J_URI, NEO4J_USERNAME, NEO4J_PASSWORD, NEO4J_DATABASE
from utils.metadata_extractor import PaperMetadata


class GraphStore:
    def __init__(self) -> None:
        self._database = NEO4J_DATABASE.strip() or None
        self._driver = GraphDatabase.driver(
            NEO4J_URI, auth=(NEO4J_USERNAME, NEO4J_PASSWORD)
        )
        self._available = True

    def close(self) -> None:
        self._driver.close()

    def _mark_unavailable(self, exc: Exception) -> None:
        if self._available:
            print(f"Neo4j unavailable; graph features disabled for this session: {exc}")
        self._available = False

    def _run_write(self, callback) -> None:
        if not self._available:
            return
        try:
            with self._driver.session(database=self._database) as session:
                callback(session)
        except (ServiceUnavailable, SessionExpired, Neo4jError) as exc:
            self._mark_unavailable(exc)

    def _run_read(self, callback, default):
        if not self._available:
            return default
        try:
            with self._driver.session(database=self._database) as session:
                return callback(session)
        except (ServiceUnavailable, SessionExpired, Neo4jError) as exc:
            self._mark_unavailable(exc)
            return default

    # ── Constraints (idempotent) ──────────────────────────────────

    def ensure_constraints(self) -> None:
        self._run_write(
            lambda session: (
                session.run(
                    "CREATE CONSTRAINT paper_id IF NOT EXISTS "
                    "FOR (p:Paper) REQUIRE p.paper_id IS UNIQUE"
                ),
                session.run(
                    "CREATE CONSTRAINT author_name IF NOT EXISTS "
                    "FOR (a:Author) REQUIRE a.name IS UNIQUE"
                ),
                session.run(
                    "CREATE CONSTRAINT keyword_val IF NOT EXISTS "
                    "FOR (k:Keyword) REQUIRE k.value IS UNIQUE"
                ),
            )
        )

    # ── Upsert paper ─────────────────────────────────────────────

    def upsert_paper(self, paper_id: str, metadata: PaperMetadata) -> str:
        def _write(session):
            # Paper node
            session.run(
                """
                MERGE (p:Paper {paper_id: $pid})
                SET p.title      = $title,
                    p.year       = $year,
                    p.doi        = $doi,
                    p.abstract   = $abstract,
                    p.page_count = $page_count,
                    p.filename   = $filename
                """,
                pid=paper_id,
                title=metadata.title,
                year=metadata.year,
                doi=metadata.doi,
                abstract=metadata.abstract[:500],
                page_count=metadata.page_count,
                filename=metadata.filename,
            )

            # Authors
            for author in metadata.authors:
                if not author.strip():
                    continue
                session.run(
                    """
                    MERGE (a:Author {name: $name})
                    WITH a
                    MATCH (p:Paper {paper_id: $pid})
                    MERGE (p)-[:AUTHORED_BY]->(a)
                    """,
                    name=author.strip(),
                    pid=paper_id,
                )

            # Keywords
            for kw in metadata.keywords:
                if not kw.strip():
                    continue
                session.run(
                    """
                    MERGE (k:Keyword {value: $kw})
                    WITH k
                    MATCH (p:Paper {paper_id: $pid})
                    MERGE (p)-[:HAS_KEYWORD]->(k)
                    """,
                    kw=kw.strip().lower(),
                    pid=paper_id,
                )

            # Journal
            if metadata.journal:
                session.run(
                    """
                    MERGE (j:Journal {name: $jname})
                    WITH j
                    MATCH (p:Paper {paper_id: $pid})
                    MERGE (p)-[:PUBLISHED_IN]->(j)
                    """,
                    jname=metadata.journal,
                    pid=paper_id,
                )

        self._run_write(_write)
        return paper_id

    # ── Register chunk ───────────────────────────────────────────

    def register_chunk(self, paper_id: str, chunk_id: str, chunk_index: int, page_hint: int) -> None:
        def _write(session):
            session.run(
                """
                MATCH (p:Paper {paper_id: $pid})
                MERGE (c:Chunk {chunk_id: $cid})
                SET c.chunk_index = $cidx,
                    c.page_hint   = $page
                MERGE (p)-[:HAS_CHUNK]->(c)
                """,
                pid=paper_id,
                cid=chunk_id,
                cidx=chunk_index,
                page=page_hint,
            )

        self._run_write(_write)

    # ── Fetch paper metadata ──────────────────────────────────────

    def get_paper(self, paper_id: str) -> dict[str, Any]:
        def _read(session):
            result = session.run(
                """
                MATCH (p:Paper {paper_id: $pid})
                OPTIONAL MATCH (p)-[:AUTHORED_BY]->(a:Author)
                OPTIONAL MATCH (p)-[:HAS_KEYWORD]->(k:Keyword)
                OPTIONAL MATCH (p)-[:PUBLISHED_IN]->(j:Journal)
                RETURN p,
                       collect(DISTINCT a.name) AS authors,
                       collect(DISTINCT k.value) AS keywords,
                       j.name AS journal
                """,
                pid=paper_id,
            )
            row = result.single()
            if not row:
                return {}
            p = dict(row["p"])
            p["authors"]  = row["authors"]
            p["keywords"] = row["keywords"]
            p["journal"]  = row["journal"]
            return p

        return self._run_read(_read, {})

    # ── List all papers ───────────────────────────────────────────

    def list_papers(self) -> list[dict[str, Any]]:
        def _read(session):
            result = session.run(
                """
                MATCH (p:Paper)
                OPTIONAL MATCH (p)-[:AUTHORED_BY]->(a:Author)
                RETURN p.paper_id AS paper_id,
                       p.title    AS title,
                       p.year     AS year,
                       p.filename AS filename,
                       collect(DISTINCT a.name) AS authors
                ORDER BY p.title
                """
            )
            return [dict(r) for r in result]

        return self._run_read(_read, [])

    # ── Delete paper ──────────────────────────────────────────────

    def delete_paper(self, paper_id: str) -> None:
        def _write(session):
            session.run(
                """
                MATCH (p:Paper {paper_id: $pid})
                OPTIONAL MATCH (p)-[:HAS_CHUNK]->(c:Chunk)
                DETACH DELETE p, c
                """,
                pid=paper_id,
            )

        self._run_write(_write)
