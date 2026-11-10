import uuid
from typing import AsyncGenerator

import pytest
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Document, DocumentChunk
from app.db.session import async_engine, async_session_maker


@pytest.fixture
async def db_session() -> AsyncGenerator[AsyncSession, None]:
    """Yield an async database session and cleanly dispose pool connections on test teardown."""
    async with async_session_maker() as session:
        yield session
    await async_engine.dispose()


@pytest.fixture
async def seeded_test_data(db_session: AsyncSession) -> AsyncGenerator[dict[str, uuid.UUID], None]:
    """Seed test Document and DocumentChunk records and guarantee cleanup after tests."""
    tenant_id = f"test_tenant_{uuid.uuid4().hex[:8]}"

    doc = Document(
        id=uuid.uuid4(),
        title="Enterprise Troubleshooting Guide",
        tenant_id=tenant_id,
        doc_metadata={"category": "troubleshooting", "version": "1.0"},
    )
    db_session.add(doc)

    # Chunk 1: Webhook troubleshooting with technical error code ERR_409_CONFLICT
    # Embedding vector populated with 384 dimensions centered at 0.05
    chunk1 = DocumentChunk(
        id=uuid.uuid4(),
        document_id=doc.id,
        tenant_id=tenant_id,
        section_header="Webhook Delivery Failures",
        content="Error code ERR_409_CONFLICT occurs during concurrent webhook delivery when resource lock is active.",
        allowed_roles=["support_tier_1", "public"],
        embedding=[0.05] * 384,
    )

    # Chunk 2: Executive compensation and confidential strategy
    # Embedding vector populated with 384 dimensions centered at 0.85 (distant from chunk1)
    chunk2 = DocumentChunk(
        id=uuid.uuid4(),
        document_id=doc.id,
        tenant_id=tenant_id,
        section_header="Executive Compensation & Strategy",
        content="Confidential executive strategy review and quarterly leadership bonus allocations.",
        allowed_roles=["executive"],
        embedding=[0.85] * 384,
    )

    db_session.add_all([chunk1, chunk2])
    await db_session.commit()

    yield {
        "doc_id": doc.id,
        "chunk1_id": chunk1.id,
        "chunk2_id": chunk2.id,
        "tenant_id": tenant_id,
    }

    # Teardown: delete parent document (which cascades to child chunks if still present)
    clean_session = async_session_maker()
    async with clean_session as session:
        existing_doc = await session.get(Document, doc.id)
        if existing_doc is not None:
            await session.delete(existing_doc)
            await session.commit()


@pytest.mark.asyncio
async def test_vector_distance_query(
    db_session: AsyncSession, seeded_test_data: dict[str, uuid.UUID]
) -> None:
    """Test 1: Query with <=> cosine distance operator and assert closest chunk is returned."""
    # Query vector very close to chunk 1 ([0.05] * 384)
    query_vector = [0.05] * 384
    tenant_id = seeded_test_data["tenant_id"]

    stmt = (
        select(DocumentChunk)
        .where(DocumentChunk.tenant_id == tenant_id)
        .order_by(DocumentChunk.embedding.cosine_distance(query_vector))
        .limit(1)
    )
    result = await db_session.execute(stmt)
    closest_chunk = result.scalar_one()

    assert closest_chunk.id == seeded_test_data["chunk1_id"]
    assert closest_chunk.section_header == "Webhook Delivery Failures"
    assert len(closest_chunk.embedding) == 384


@pytest.mark.asyncio
async def test_dual_lexical_fts_matching(
    db_session: AsyncSession, seeded_test_data: dict[str, uuid.UUID]
) -> None:
    """Test 2: Dual lexical FTS query matching exact error code 'ERR_409_CONFLICT' via tsvector."""
    query = text(
        "SELECT content FROM document_chunks "
        "WHERE tenant_id = :tenant_id "
        "AND tsv_content @@ websearch_to_tsquery('english', 'ERR_409_CONFLICT')"
    )
    result = await db_session.execute(query, {"tenant_id": seeded_test_data["tenant_id"]})
    rows = result.scalars().all()

    assert len(rows) == 1
    assert "ERR_409_CONFLICT" in rows[0]


@pytest.mark.asyncio
async def test_role_array_gin_overlap(
    db_session: AsyncSession, seeded_test_data: dict[str, uuid.UUID]
) -> None:
    """Test 3: Query with allowed_roles && ARRAY['support_tier_1'] and verify role overlap filtering."""
    query = text(
        "SELECT content, allowed_roles FROM document_chunks "
        "WHERE tenant_id = :tenant_id "
        "AND allowed_roles && ARRAY['support_tier_1']"
    )
    result = await db_session.execute(query, {"tenant_id": seeded_test_data["tenant_id"]})
    rows = result.all()

    assert len(rows) == 1
    assert "support_tier_1" in rows[0].allowed_roles
    assert "public" in rows[0].allowed_roles


@pytest.mark.asyncio
async def test_foreign_key_cascade_deletion(
    db_session: AsyncSession, seeded_test_data: dict[str, uuid.UUID]
) -> None:
    """Test 4: Delete the parent Document and verify child chunks are deleted via CASCADE."""
    doc_id = seeded_test_data["doc_id"]

    # Verify chunks exist before deletion
    check_stmt = select(DocumentChunk).where(DocumentChunk.document_id == doc_id)
    chunks_before = (await db_session.execute(check_stmt)).scalars().all()
    assert len(chunks_before) == 2

    # Delete parent Document
    doc = await db_session.get(Document, doc_id)
    assert doc is not None
    await db_session.delete(doc)
    await db_session.commit()

    # Verify child chunks are completely removed by PostgreSQL foreign key ON DELETE CASCADE
    chunks_after = (await db_session.execute(check_stmt)).scalars().all()
    assert len(chunks_after) == 0
