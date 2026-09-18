import enum
import uuid
from datetime import datetime

from pgvector.sqlalchemy import VECTOR
from sqlalchemy import (
    DateTime,
    Enum,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import TSVECTOR, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import EMBEDDING_DIMENSIONS, Base


class ArticleStatus(enum.StrEnum):
    draft = "draft"
    published = "published"


class ArticleSource(enum.StrEnum):
    seed = "seed"
    staff = "staff"


class TicketCategory(enum.StrEnum):
    how_it_works = "how_it_works"
    bug = "bug"
    billing = "billing"


class TicketStatus(enum.StrEnum):
    open = "open"
    closed = "closed"


class AuthorType(enum.StrEnum):
    user = "user"
    staff = "staff"
    system = "system"


class Article(Base):
    __tablename__ = "articles"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    title: Mapped[str] = mapped_column(String(300))
    body_markdown: Mapped[str] = mapped_column(Text)
    status: Mapped[ArticleStatus] = mapped_column(Enum(ArticleStatus))
    source: Mapped[ArticleSource] = mapped_column(Enum(ArticleSource))
    seed_path: Mapped[str | None] = mapped_column(
        String(500), nullable=True, unique=True
    )
    updated_by: Mapped[str | None] = mapped_column(String(128), nullable=True)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
    chunks: Mapped[list["Chunk"]] = relationship(back_populates="article")


class Chunk(Base):
    __tablename__ = "chunks"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    article_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("articles.id", ondelete="CASCADE")
    )
    chunk_index: Mapped[int] = mapped_column(Integer)
    text: Mapped[str] = mapped_column(Text)
    embedding: Mapped[list[float]] = mapped_column(VECTOR(EMBEDDING_DIMENSIONS))
    tsv: Mapped[str] = mapped_column(TSVECTOR)
    content_hash: Mapped[str] = mapped_column(String(64))
    article: Mapped[Article] = relationship(back_populates="chunks")

    __table_args__ = (
        UniqueConstraint("article_id", "chunk_index", name="uq_chunks_article_index"),
        Index(
            "ix_chunks_embedding_hnsw",
            "embedding",
            postgresql_using="hnsw",
            postgresql_ops={"embedding": "vector_cosine_ops"},
        ),
        Index("ix_chunks_tsv_gin", "tsv", postgresql_using="gin"),
    )


class Ticket(Base):
    __tablename__ = "tickets"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[str] = mapped_column(String(128), index=True)
    user_email: Mapped[str] = mapped_column(String(320))
    category: Mapped[TicketCategory] = mapped_column(Enum(TicketCategory))
    status: Mapped[TicketStatus] = mapped_column(
        Enum(TicketStatus), default=TicketStatus.open
    )
    title: Mapped[str] = mapped_column(String(300))
    url: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    closed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    closed_by: Mapped[str | None] = mapped_column(String(128), nullable=True)
    messages: Mapped[list["Message"]] = relationship(back_populates="ticket")


class Message(Base):
    __tablename__ = "messages"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    ticket_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tickets.id", ondelete="CASCADE")
    )
    author_type: Mapped[AuthorType] = mapped_column(Enum(AuthorType))
    author_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    body: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    ticket: Mapped[Ticket] = relationship(back_populates="messages")


class RagRun(Base):
    __tablename__ = "rag_runs"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[str] = mapped_column(String(128))
    category: Mapped[TicketCategory] = mapped_column(Enum(TicketCategory))
    query: Mapped[str] = mapped_column(Text)
    ticket_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tickets.id"), nullable=True
    )
    langsmith_run_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
