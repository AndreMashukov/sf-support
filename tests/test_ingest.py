import uuid
from pathlib import Path
from unittest.mock import MagicMock

from app.ingest import ingest_seed
from app.models import Article, ArticleSource, ArticleStatus


class _EmptyScalars:
    def first(self):
        return None


def test_ingest_seed_creates_published_seed_articles(
    tmp_path: Path, monkeypatch
) -> None:
    (tmp_path / "faq.md").write_text("# FAQ\n\nHow credits work.\n", encoding="utf-8")
    reindexed: list[Article] = []

    def fake_reindex(_db, article: Article) -> int:
        reindexed.append(article)
        return 1

    monkeypatch.setattr("app.ingest.reindex_article", fake_reindex)
    monkeypatch.setattr(
        "app.ingest.article_has_embeddings",
        lambda _db, _id: False,
    )

    db = MagicMock()
    db.scalars.return_value = _EmptyScalars()

    count = ingest_seed(db, tmp_path)
    assert count == 1
    assert db.add.call_count == 1
    added = db.add.call_args[0][0]
    assert added.source == ArticleSource.seed
    assert added.status == ArticleStatus.published
    assert added.seed_path == "seed/faq.md"
    assert added.title == "FAQ"
    assert reindexed == [added]
    db.commit.assert_called_once()


def test_ingest_seed_skips_unchanged_indexed_article(
    tmp_path: Path, monkeypatch
) -> None:
    body = "# FAQ\n\nSame body\n"
    (tmp_path / "faq.md").write_text(body, encoding="utf-8")
    existing = Article(
        id=uuid.uuid4(),
        title="FAQ",
        body_markdown=body,
        status=ArticleStatus.published,
        source=ArticleSource.seed,
        seed_path="seed/faq.md",
    )

    class _Found:
        def first(self):
            return existing

    db = MagicMock()
    db.scalars.return_value = _Found()
    monkeypatch.setattr("app.ingest.article_has_embeddings", lambda _db, _id: True)
    monkeypatch.setattr(
        "app.ingest.reindex_article",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(AssertionError("skip")),
    )

    assert ingest_seed(db, tmp_path) == 0
    db.add.assert_not_called()
    db.commit.assert_called_once()
