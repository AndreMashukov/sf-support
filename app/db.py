from sqlalchemy import create_engine, text
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from app.settings import settings

EMBEDDING_DIMENSIONS = 1024


class Base(DeclarativeBase):
    pass


engine = create_engine(settings.database_url, pool_pre_ping=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def ensure_schema() -> None:
    """Create the vector extension, tables, and Help-chunk indexes."""
    import app.models  # noqa: F401

    with engine.begin() as conn:
        conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
    Base.metadata.create_all(bind=engine)
    with engine.begin() as conn:
        conn.execute(
            text(
                f"ALTER TABLE chunks ADD COLUMN IF NOT EXISTS "
                f"embedding vector({EMBEDDING_DIMENSIONS})"
            )
        )
        conn.execute(text("ALTER TABLE chunks ADD COLUMN IF NOT EXISTS tsv tsvector"))
        conn.execute(
            text(
                "CREATE INDEX IF NOT EXISTS ix_chunks_embedding_hnsw "
                "ON chunks USING hnsw (embedding vector_cosine_ops)"
            )
        )
        conn.execute(
            text(
                "CREATE INDEX IF NOT EXISTS ix_chunks_tsv_gin ON chunks USING gin (tsv)"
            )
        )
        conn.execute(
            text(
                "CREATE UNIQUE INDEX IF NOT EXISTS uq_articles_seed_path "
                "ON articles (seed_path) WHERE seed_path IS NOT NULL"
            )
        )
        conn.execute(
            text("ALTER TABLE rag_runs ADD COLUMN IF NOT EXISTS command_id varchar(64)")
        )
        conn.execute(
            text("ALTER TABLE tickets ADD COLUMN IF NOT EXISTS write_id varchar(64)")
        )
        conn.execute(
            text(
                "ALTER TABLE rag_runs ADD COLUMN IF NOT EXISTS enough_context boolean"
            )
        )
        conn.execute(text("ALTER TABLE rag_runs ADD COLUMN IF NOT EXISTS answer text"))
        conn.execute(
            text("ALTER TABLE rag_runs ADD COLUMN IF NOT EXISTS citations jsonb")
        )
        conn.execute(
            text("ALTER TABLE rag_runs ADD COLUMN IF NOT EXISTS no_answer_reason text")
        )
        conn.execute(
            text("ALTER TABLE rag_runs ADD COLUMN IF NOT EXISTS chunk_ids jsonb")
        )
        conn.execute(
            text(
                "ALTER TABLE rag_runs ADD COLUMN IF NOT EXISTS resolution varchar(32)"
            )
        )
        conn.execute(
            text(
                "ALTER TABLE rag_runs ADD COLUMN IF NOT EXISTS resolved_at "
                "timestamptz"
            )
        )
        conn.execute(
            text(
                "CREATE UNIQUE INDEX IF NOT EXISTS uq_rag_runs_command_id "
                "ON rag_runs (command_id) WHERE command_id IS NOT NULL"
            )
        )
