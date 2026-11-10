import uuid
from datetime import datetime
from typing import Any, List, Optional

import pgvector.sqlalchemy
from sqlalchemy import (
    Computed,
    DateTime,
    ForeignKey,
    Index,
    String,
    Text,
    func,
)
from sqlalchemy.dialects.postgresql import ARRAY, JSONB, TSVECTOR, UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


class Document(Base):
    __tablename__ = "documents"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    title: Mapped[str] = mapped_column(
        String(512),
        nullable=False,
    )
    tenant_id: Mapped[str] = mapped_column(
        String(128),
        nullable=False,
        index=True,
    )
    doc_metadata: Mapped[dict[str, Any]] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    chunks: Mapped[List["DocumentChunk"]] = relationship(
        "DocumentChunk",
        back_populates="document",
        cascade="all, delete-orphan",
    )


class DocumentChunk(Base):
    __tablename__ = "document_chunks"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    document_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("documents.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    tenant_id: Mapped[str] = mapped_column(
        String(128),
        nullable=False,
        index=True,
    )
    section_header: Mapped[str] = mapped_column(
        String(512),
        nullable=False,
    )
    content: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )
    allowed_roles: Mapped[List[str]] = mapped_column(
        ARRAY(String),
        nullable=False,
    )
    embedding: Mapped[Optional[List[float]]] = mapped_column(
        pgvector.sqlalchemy.Vector(384),
        nullable=True,
    )
    tsv_content: Mapped[Optional[str]] = mapped_column(
        TSVECTOR,
        Computed("to_tsvector('simple', content) || to_tsvector('english', content)", persisted=True),
        nullable=True,
    )

    document: Mapped["Document"] = relationship(
        "Document",
        back_populates="chunks",
    )

    __table_args__ = (
        Index(
            "ix_document_chunks_allowed_roles",
            "allowed_roles",
            postgresql_using="gin",
        ),
        Index(
            "ix_document_chunks_tsv_content",
            "tsv_content",
            postgresql_using="gin",
        ),
        Index(
            "ix_document_chunks_embedding_hnsw",
            "embedding",
            postgresql_using="hnsw",
            postgresql_with={"m": 16, "ef_construction": 64},
            postgresql_ops={"embedding": "vector_cosine_ops"},
        ),
    )
