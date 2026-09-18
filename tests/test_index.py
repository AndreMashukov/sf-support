import uuid
from unittest.mock import MagicMock

from app.models import Article, ArticleSource, ArticleStatus
from app.rag.index import reindex_article


def test_reindex_published_article_embeds_then_replaces(monkeypatch) -> None:
    calls: list[list[str]] = []

    def fake_embed(texts: list[str], *, role: str = "passage") -> list[list[float]]:
        calls.append(texts)
        assert role == "passage"
        return [[0.1, 0.2] for _ in texts]

    monkeypatch.setattr("app.rag.index.embed_texts", fake_embed)

    article = Article(
        id=uuid.uuid4(),
        title="FAQ",
        body_markdown="Hello support. " * 80,
        status=ArticleStatus.published,
        source=ArticleSource.seed,
        seed_path="seed/faq.md",
    )
    db = MagicMock()
    count = reindex_article(db, article)
    assert count >= 1
    assert calls
    db.execute.assert_called_once()
    assert db.add.call_count == count


def test_reindex_draft_deletes_chunks_without_embed(monkeypatch) -> None:
    monkeypatch.setattr(
        "app.rag.index.embed_texts",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(AssertionError("no embed")),
    )
    article = Article(
        id=uuid.uuid4(),
        title="Draft",
        body_markdown="secret billing 12.00",
        status=ArticleStatus.draft,
        source=ArticleSource.staff,
    )
    db = MagicMock()
    assert reindex_article(db, article) == 0
    db.execute.assert_called_once()
    db.add.assert_not_called()
