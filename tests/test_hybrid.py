from unittest.mock import MagicMock
from uuid import uuid4

from app.rag.hybrid import hybrid_search, rrf_fuse


def test_rrf_ranks_overlap_first() -> None:
    only_vector, both, only_keyword = uuid4(), uuid4(), uuid4()
    fused = rrf_fuse([[only_vector, both], [both, only_keyword]])
    assert [chunk_id for chunk_id, _score in fused] == [
        both,
        only_vector,
        only_keyword,
    ]
    assert fused[0][1] > fused[1][1]


def test_hybrid_search_rejects_blank_query() -> None:
    assert hybrid_search("   ") == []
    assert hybrid_search("q", limit=0) == []


def test_hybrid_search_fuses_vector_and_keyword(monkeypatch) -> None:
    article_id = uuid4()
    vector_only = uuid4()
    both = uuid4()
    keyword_only = uuid4()

    monkeypatch.setattr("app.rag.hybrid.embeddings_configured", lambda: True)
    monkeypatch.setattr(
        "app.rag.hybrid.embed_text",
        lambda _query, *, role: [0.1, 0.2] if role == "query" else [],
    )

    def execute(statement, params=None):
        sql = str(statement)
        result = MagicMock()
        if "<=>" in sql:
            result.mappings.return_value = [
                {
                    "id": vector_only,
                    "text": "vector hit",
                    "article_id": article_id,
                    "title": "FAQ",
                },
                {
                    "id": both,
                    "text": "overlap",
                    "article_id": article_id,
                    "title": "FAQ",
                },
            ]
        else:
            result.mappings.return_value = [
                {
                    "id": both,
                    "text": "overlap",
                    "article_id": article_id,
                    "title": "FAQ",
                },
                {
                    "id": keyword_only,
                    "text": "keyword hit",
                    "article_id": article_id,
                    "title": "FAQ",
                },
            ]
        return result

    db = MagicMock()
    db.execute.side_effect = execute

    chunks = hybrid_search("how do credits work", db=db)
    assert [chunk.chunk_id for chunk in chunks] == [
        str(both),
        str(vector_only),
        str(keyword_only),
    ]
    assert chunks[0].article_title == "FAQ"
    assert chunks[0].text == "overlap"
    assert len(chunks) <= 6


def test_hybrid_search_keyword_only_when_embeddings_off(monkeypatch) -> None:
    chunk_id = uuid4()
    monkeypatch.setattr("app.rag.hybrid.embeddings_configured", lambda: False)
    monkeypatch.setattr(
        "app.rag.hybrid.embed_text",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(
            AssertionError("should not embed")
        ),
    )

    result = MagicMock()
    result.mappings.return_value = [
        {
            "id": chunk_id,
            "text": "keyword only",
            "article_id": uuid4(),
            "title": "Help",
        }
    ]
    db = MagicMock()
    db.execute.return_value = result

    chunks = hybrid_search("billing", db=db)
    assert len(chunks) == 1
    assert chunks[0].chunk_id == str(chunk_id)
    db.execute.assert_called_once()


def test_hybrid_search_keyword_only_when_embed_fails(monkeypatch) -> None:
    chunk_id = uuid4()
    monkeypatch.setattr("app.rag.hybrid.embeddings_configured", lambda: True)
    monkeypatch.setattr(
        "app.rag.hybrid.embed_text",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(
            RuntimeError("OpenRouter embeddings failed (503)")
        ),
    )

    result = MagicMock()
    result.mappings.return_value = [
        {
            "id": chunk_id,
            "text": "keyword fallback",
            "article_id": uuid4(),
            "title": "Help",
        }
    ]
    db = MagicMock()
    db.execute.return_value = result

    chunks = hybrid_search("credits", db=db)
    assert len(chunks) == 1
    assert chunks[0].chunk_id == str(chunk_id)
    sql = str(db.execute.call_args[0][0])
    assert "<=>" not in sql
    db.execute.assert_called_once()
