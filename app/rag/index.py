from uuid import UUID

from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session

from app.models import Article, ArticleStatus, Chunk
from app.rag.chunking import chunk_text, hash_content
from app.rag.embeddings import embed_texts


def reindex_article(db: Session, article: Article) -> int:
    """Replace Help chunks for one article. Embed before deleting old rows."""
    if article.status != ArticleStatus.published:
        db.execute(delete(Chunk).where(Chunk.article_id == article.id))
        return 0

    texts = chunk_text(article.body_markdown)
    vectors = embed_texts(texts, role="passage") if texts else []
    db.execute(delete(Chunk).where(Chunk.article_id == article.id))
    for index, (text, vector) in enumerate(zip(texts, vectors, strict=True)):
        db.add(
            Chunk(
                article_id=article.id,
                chunk_index=index,
                text=text,
                embedding=vector,
                tsv=func.to_tsvector("english", f"{article.title}\n{text}"),
                content_hash=hash_content(text),
            )
        )
    return len(texts)


def article_has_embeddings(db: Session, article_id: UUID) -> bool:
    chunk = db.scalars(
        select(Chunk).where(Chunk.article_id == article_id).limit(1)
    ).first()
    return chunk is not None and chunk.embedding is not None
