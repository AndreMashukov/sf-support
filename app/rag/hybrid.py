"""Vector cosine + Postgres FTS, fused with Reciprocal Rank Fusion."""

from dataclasses import dataclass
from typing import Any
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.db import SessionLocal
from app.models import ArticleStatus
from app.rag.embeddings import embed_text, embeddings_configured

VECTOR_CANDIDATES = 8
KEYWORD_CANDIDATES = 8
DEFAULT_LIMIT = 6
RRF_K = 60

_VECTOR_SQL = text(
    """
    SELECT c.id, c.text, c.article_id, a.title
    FROM chunks c
    JOIN articles a ON a.id = c.article_id
    WHERE a.status = :status
      AND c.embedding IS NOT NULL
    ORDER BY c.embedding <=> CAST(:embedding AS vector)
    LIMIT :limit
    """
)

_KEYWORD_SQL = text(
    """
    SELECT c.id, c.text, c.article_id, a.title
    FROM chunks c
    JOIN articles a ON a.id = c.article_id
    WHERE a.status = :status
      AND c.tsv @@ websearch_to_tsquery('english', :query)
    ORDER BY ts_rank_cd(c.tsv, websearch_to_tsquery('english', :query)) DESC
    LIMIT :limit
    """
)


@dataclass
class RetrievedChunk:
    text: str
    article_title: str
    article_id: str
    score: float
    chunk_id: str = ""


def rrf_fuse(
    ranked_lists: list[list[UUID]],
    *,
    k: int = RRF_K,
) -> list[tuple[UUID, float]]:
    scores: dict[UUID, float] = {}
    for ranking in ranked_lists:
        for rank, chunk_id in enumerate(ranking, start=1):
            scores[chunk_id] = scores.get(chunk_id, 0.0) + 1.0 / (k + rank)
    return sorted(scores.items(), key=lambda item: (-item[1], str(item[0])))


def hybrid_search(
    query: str,
    limit: int = DEFAULT_LIMIT,
    db: Session | None = None,
) -> list[RetrievedChunk]:
    cleaned = query.strip()
    if not cleaned or limit <= 0:
        return []

    owns_session = db is None
    session = SessionLocal() if owns_session else db
    try:
        return _hybrid_search(session, cleaned, limit)
    finally:
        if owns_session:
            session.close()


def _hybrid_search(db: Session, query: str, limit: int) -> list[RetrievedChunk]:
    by_id: dict[UUID, dict[str, Any]] = {}
    vector_ids: list[UUID] = []
    keyword_ids: list[UUID] = []

    if embeddings_configured():
        try:
            embedding = embed_text(query, role="query")
        except Exception:
            embedding = None
        if embedding is not None:
            vector_ids = _load_candidates(
                db,
                _VECTOR_SQL,
                {
                    "status": ArticleStatus.published.value,
                    "embedding": _vector_literal(embedding),
                    "limit": VECTOR_CANDIDATES,
                },
                by_id,
            )

    keyword_ids = _load_candidates(
        db,
        _KEYWORD_SQL,
        {
            "status": ArticleStatus.published.value,
            "query": query,
            "limit": KEYWORD_CANDIDATES,
        },
        by_id,
    )

    fused = rrf_fuse([vector_ids, keyword_ids])
    results: list[RetrievedChunk] = []
    for chunk_id, score in fused[:limit]:
        row = by_id[chunk_id]
        results.append(
            RetrievedChunk(
                text=row["text"],
                article_title=row["title"],
                article_id=str(row["article_id"]),
                score=score,
                chunk_id=str(chunk_id),
            )
        )
    return results


def _load_candidates(
    db: Session,
    statement: Any,
    params: dict[str, Any],
    by_id: dict[UUID, dict[str, Any]],
) -> list[UUID]:
    rows = db.execute(statement, params).mappings()
    ordered: list[UUID] = []
    for row in rows:
        chunk_id = row["id"]
        if not isinstance(chunk_id, UUID):
            chunk_id = UUID(str(chunk_id))
        by_id[chunk_id] = {
            "text": row["text"],
            "title": row["title"],
            "article_id": row["article_id"],
        }
        ordered.append(chunk_id)
    return ordered


def _vector_literal(values: list[float]) -> str:
    return "[" + ",".join(str(float(value)) for value in values) + "]"
