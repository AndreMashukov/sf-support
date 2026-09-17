"""Vector + Postgres FTS, fused with RRF. Not implemented in the scaffold."""

from dataclasses import dataclass


@dataclass
class RetrievedChunk:
    text: str
    article_title: str
    article_id: str
    score: float


def hybrid_search(query: str, limit: int = 6) -> list[RetrievedChunk]:
    _ = (query, limit)
    return []
