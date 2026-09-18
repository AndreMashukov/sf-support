"""Load seed markdown as published Help articles and reindex chunks."""

from __future__ import annotations

import logging
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db import SessionLocal, ensure_schema
from app.models import Article, ArticleSource, ArticleStatus
from app.rag.chunking import title_from_markdown
from app.rag.embeddings import embeddings_configured
from app.rag.index import article_has_embeddings, reindex_article

logger = logging.getLogger(__name__)

SEED_DIR = Path(__file__).resolve().parent.parent / "seed"


def ingest_seed(db: Session, seed_dir: Path = SEED_DIR) -> int:
    """Upsert seed/*.md as published articles (source seed) and reindex."""
    if not seed_dir.is_dir():
        logger.warning("Seed directory missing: %s", seed_dir)
        return 0

    indexed = 0
    for path in sorted(seed_dir.glob("*.md")):
        body = path.read_text(encoding="utf-8")
        seed_path = f"seed/{path.name}"
        title = title_from_markdown(path, body)
        article = db.scalars(
            select(Article).where(Article.seed_path == seed_path)
        ).first()
        body_unchanged = article is not None and article.body_markdown == body
        if (
            article is not None
            and body_unchanged
            and article.status == ArticleStatus.published
            and article_has_embeddings(db, article.id)
        ):
            continue
        if article is None:
            article = Article(
                title=title,
                body_markdown=body,
                status=ArticleStatus.published,
                source=ArticleSource.seed,
                seed_path=seed_path,
                updated_by="seed",
            )
            db.add(article)
            db.flush()
        else:
            article.title = title
            article.body_markdown = body
            article.status = ArticleStatus.published
            article.source = ArticleSource.seed
            article.updated_by = "seed"
        reindex_article(db, article)
        indexed += 1
    db.commit()
    return indexed


def run_seed_ingest() -> int:
    if not embeddings_configured():
        logger.warning("Skip seed ingest: OPENROUTER_API_KEY is not set")
        return 0
    ensure_schema()
    db = SessionLocal()
    try:
        count = ingest_seed(db)
        logger.info("Seed ingest indexed %s article(s)", count)
        return count
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


def main() -> None:
    logging.basicConfig(level=logging.INFO)
    count = run_seed_ingest()
    print(f"Indexed {count} seed article(s)")


if __name__ == "__main__":
    main()
