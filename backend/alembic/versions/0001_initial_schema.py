"""Initial schema with pgvector, documents, and document_chunks

Revision ID: 0001
Revises: 
Create Date: 2026-11-10 22:30:00.000000

"""
from typing import Sequence, Union

from alembic import op
import pgvector.sqlalchemy
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "0001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Enable pgvector extension
    op.execute("CREATE EXTENSION IF NOT EXISTS vector;")

    # 2. Create documents table
    op.create_table(
        "documents",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("title", sa.String(length=512), nullable=False),
        sa.Column("tenant_id", sa.String(length=128), nullable=False),
        sa.Column("doc_metadata", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    op.create_index("ix_documents_tenant_id", "documents", ["tenant_id"], unique=False)

    # 3. Create document_chunks table
    op.create_table(
        "document_chunks",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("document_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("documents.id", ondelete="CASCADE"), nullable=False),
        sa.Column("tenant_id", sa.String(length=128), nullable=False),
        sa.Column("section_header", sa.String(length=512), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("allowed_roles", postgresql.ARRAY(sa.String()), nullable=False),
        sa.Column("embedding", pgvector.sqlalchemy.Vector(384), nullable=True),
        sa.Column(
            "tsv_content",
            postgresql.TSVECTOR(),
            sa.Computed("to_tsvector('simple', content) || to_tsvector('english', content)", persisted=True),
            nullable=True,
        ),
    )
    op.create_index("ix_document_chunks_document_id", "document_chunks", ["document_id"], unique=False)
    op.create_index("ix_document_chunks_tenant_id", "document_chunks", ["tenant_id"], unique=False)
    op.create_index("ix_document_chunks_allowed_roles", "document_chunks", ["allowed_roles"], unique=False, postgresql_using="gin")
    op.create_index("ix_document_chunks_tsv_content", "document_chunks", ["tsv_content"], unique=False, postgresql_using="gin")
    op.create_index(
        "ix_document_chunks_embedding_hnsw",
        "document_chunks",
        ["embedding"],
        unique=False,
        postgresql_using="hnsw",
        postgresql_with={"m": 16, "ef_construction": 64},
        postgresql_ops={"embedding": "vector_cosine_ops"},
    )


def downgrade() -> None:
    op.drop_index("ix_document_chunks_embedding_hnsw", table_name="document_chunks", postgresql_using="hnsw")
    op.drop_index("ix_document_chunks_tsv_content", table_name="document_chunks", postgresql_using="gin")
    op.drop_index("ix_document_chunks_allowed_roles", table_name="document_chunks", postgresql_using="gin")
    op.drop_index("ix_document_chunks_tenant_id", table_name="document_chunks")
    op.drop_index("ix_document_chunks_document_id", table_name="document_chunks")
    op.drop_table("document_chunks")

    op.drop_index("ix_documents_tenant_id", table_name="documents")
    op.drop_table("documents")
