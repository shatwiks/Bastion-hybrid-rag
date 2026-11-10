import uuid
from collections.abc import AsyncGenerator

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import compute_scope_hash
from app.db.models import Document, DocumentChunk
from app.db.session import async_engine, async_session_maker
from app.retrievers.base import VectorStoreRetriever
from app.retrievers.postgres_hybrid import PostgresHybridRetriever
from app.schemas.auth import SecurityContext


@pytest.fixture
async def db_session() -> AsyncGenerator[AsyncSession, None]:
    """Yield an async database session and dispose engine connections on teardown."""
    async with async_session_maker() as session:
        yield session
    await async_engine.dispose()


@pytest.fixture
async def seeded_rbac_corpus(
    db_session: AsyncSession,
) -> AsyncGenerator[dict[str, str | uuid.UUID], None]:
    """Populate database with multi-tenant and role-tiered documents and chunks.

    Structure:
    - Tenant A (acme_corp): 20 executive chunks, 10 support_tier_1 chunks, 5 public chunks (35 total).
    - Tenant B (globex_corp): 15 executive chunks, 10 public chunks (25 total).
    Tenant B chunks are seeded with vectors identical to the query vector to prove
    that pre-retrieval database filtering excludes them despite their higher similarity.
    """
    tenant_a = f"acme_corp_{uuid.uuid4().hex[:8]}"
    tenant_b = f"globex_corp_{uuid.uuid4().hex[:8]}"

    doc_a = Document(
        id=uuid.uuid4(),
        title="Acme Corp Enterprise Runbook",
        tenant_id=tenant_a,
        doc_metadata={"tier": "internal", "org": "acme"},
    )
    doc_b = Document(
        id=uuid.uuid4(),
        title="Globex Corp Operations Manual",
        tenant_id=tenant_b,
        doc_metadata={"tier": "external", "org": "globex"},
    )
    db_session.add_all([doc_a, doc_b])

    chunks: list[DocumentChunk] = []

    # Tenant A Chunks (35 total)
    # 20 Executive chunks (embedding centered at 0.85)
    for i in range(20):
        chunks.append(
            DocumentChunk(
                id=uuid.uuid4(),
                document_id=doc_a.id,
                tenant_id=tenant_a,
                section_header=f"Acme Executive Confidential Strategy Part {i}",
                content=f"Acme confidential corporate strategy, financial allocations, and leadership notes {i}. Error code ERR_409_CONFLICT on sync.",
                allowed_roles=["executive"],
                embedding=[0.85] * 384,
            )
        )

    # 10 Support Tier 1 chunks (embedding centered at 0.60)
    for i in range(10):
        chunks.append(
            DocumentChunk(
                id=uuid.uuid4(),
                document_id=doc_a.id,
                tenant_id=tenant_a,
                section_header=f"Acme Support Operations Part {i}",
                content=f"Acme tier 1 internal support runbook and diagnostic steps {i}. Error code ERR_409_CONFLICT on sync.",
                allowed_roles=["support_tier_1", "executive"],
                embedding=[0.60] * 384,
            )
        )

    # 5 Public chunks (embedding centered at 0.20)
    for i in range(5):
        chunks.append(
            DocumentChunk(
                id=uuid.uuid4(),
                document_id=doc_a.id,
                tenant_id=tenant_a,
                section_header=f"Acme Public Help Guide Part {i}",
                content=f"Acme general public knowledge base and webhook troubleshooting {i}. Error code ERR_409_CONFLICT on sync.",
                allowed_roles=["public", "support_tier_1", "executive"],
                embedding=[0.20] * 384,
            )
        )

    # Tenant B Chunks (25 total)
    # Seeded with 0.90 vectors (highest similarity to target query vector [0.90] * 384)
    # 15 Executive chunks
    for i in range(15):
        chunks.append(
            DocumentChunk(
                id=uuid.uuid4(),
                document_id=doc_b.id,
                tenant_id=tenant_b,
                section_header=f"Globex Executive Strategy Part {i}",
                content=f"Globex confidential executive strategy {i}. Error code ERR_409_CONFLICT on sync.",
                allowed_roles=["executive"],
                embedding=[0.90] * 384,
            )
        )

    # 10 Public chunks
    for i in range(10):
        chunks.append(
            DocumentChunk(
                id=uuid.uuid4(),
                document_id=doc_b.id,
                tenant_id=tenant_b,
                section_header=f"Globex Public Guide Part {i}",
                content=f"Globex public user overview and webhook steps {i}. Error code ERR_409_CONFLICT on sync.",
                allowed_roles=["public"],
                embedding=[0.90] * 384,
            )
        )

    db_session.add_all(chunks)
    await db_session.commit()

    yield {
        "tenant_a": tenant_a,
        "tenant_b": tenant_b,
        "doc_a_id": doc_a.id,
        "doc_b_id": doc_b.id,
    }

    # Teardown: delete parent documents (cascades to all seeded chunks)
    clean_session = async_session_maker()
    async with clean_session as session:
        for doc_id in (doc_a.id, doc_b.id):
            doc = await session.get(Document, doc_id)
            if doc is not None:
                await session.delete(doc)
        await session.commit()


@pytest.mark.asyncio
async def test_postgres_retriever_protocol_conformance(db_session: AsyncSession) -> None:
    """Verify PostgresHybridRetriever conforms to VectorStoreRetriever protocol."""
    retriever = PostgresHybridRetriever(session=db_session)
    assert isinstance(retriever, VectorStoreRetriever)


@pytest.mark.asyncio
async def test_cross_tenant_boundary_isolation(
    db_session: AsyncSession,
    seeded_rbac_corpus: dict[str, str | uuid.UUID],
) -> None:
    """Assert Test 1: Query for Tenant A never returns any Tenant B chunk.

    Even though Tenant B chunks have higher cosine similarity ([0.90] vs [0.85]/[0.60]/[0.20]),
    pre-retrieval SQL WHERE tenant_id = :tenant_id must exclude Tenant B with 0.0% leakage.
    """
    tenant_a = str(seeded_rbac_corpus["tenant_a"])
    tenant_b = str(seeded_rbac_corpus["tenant_b"])
    doc_a_id = str(seeded_rbac_corpus["doc_a_id"])

    sec_ctx = SecurityContext(
        tenant_id=tenant_a,
        allowed_roles=("executive", "support_tier_1", "public"),
        scope_hash=compute_scope_hash(tenant_a, ("executive", "support_tier_1", "public")),
    )

    retriever = PostgresHybridRetriever(session=db_session, candidate_pool_size=50)
    query_vector = [0.90] * 384
    query_text = "ERR_409_CONFLICT corporate strategy webhook"

    results = await retriever.retrieve_hybrid(
        security_ctx=sec_ctx,
        query_text=query_text,
        query_embedding=query_vector,
        top_k=25,
    )

    assert len(results) > 0
    # Assert 0 chunks from Tenant B are returned
    for chunk in results:
        assert chunk.document_id == doc_a_id
        assert tenant_b not in chunk.document_title


@pytest.mark.asyncio
async def test_role_based_boundary_isolation(
    db_session: AsyncSession,
    seeded_rbac_corpus: dict[str, str | uuid.UUID],
) -> None:
    """Assert Test 2: Query for Tenant A public role returns 0 executive or support_tier_1 restricted chunks."""
    tenant_a = str(seeded_rbac_corpus["tenant_a"])

    sec_ctx = SecurityContext(
        tenant_id=tenant_a,
        allowed_roles=("public",),
        scope_hash=compute_scope_hash(tenant_a, ("public",)),
    )

    retriever = PostgresHybridRetriever(session=db_session, candidate_pool_size=50)
    query_vector = [0.85] * 384
    query_text = "ERR_409_CONFLICT strategy"

    results = await retriever.retrieve_hybrid(
        security_ctx=sec_ctx,
        query_text=query_text,
        query_embedding=query_vector,
        top_k=25,
    )

    assert len(results) > 0
    # Every returned chunk MUST include 'public' in its allowed_roles
    for chunk in results:
        assert "public" in chunk.allowed_roles
        # Chunks restricted exclusively to executive or support_tier_1 must never leak
        assert "Executive Confidential" not in chunk.section_header


@pytest.mark.asyncio
async def test_top_k_starvation_immunity(
    db_session: AsyncSession,
    seeded_rbac_corpus: dict[str, str | uuid.UUID],
) -> None:
    """Assert Test 3: Pre-retrieval filtering guarantees immunity to Top-K starvation (Pitfall 1).

    In Tenant A, 20 executive chunks and 10 support chunks have much higher similarity (0.85, 0.60)
    than the 5 public chunks (0.20).
    A naive post-retrieval filter requesting top_k=5 would retrieve only executive chunks and drop them all.
    Pre-retrieval filtering in SQL must return all 5 valid public chunks.
    """
    tenant_a = str(seeded_rbac_corpus["tenant_a"])

    sec_ctx = SecurityContext(
        tenant_id=tenant_a,
        allowed_roles=("public",),
        scope_hash=compute_scope_hash(tenant_a, ("public",)),
    )

    retriever = PostgresHybridRetriever(session=db_session, candidate_pool_size=50)
    # Query vector close to executive chunks (0.85) and far from public chunks (0.20)
    query_vector = [0.85] * 384
    query_text = "ERR_409_CONFLICT troubleshooting"

    results = await retriever.retrieve_hybrid(
        security_ctx=sec_ctx,
        query_text=query_text,
        query_embedding=query_vector,
        top_k=5,
    )

    # Exactly 5 public chunks must be returned without starvation
    assert len(results) == 5
    for chunk in results:
        assert "public" in chunk.allowed_roles
        assert "Acme Public Help Guide" in chunk.section_header


@pytest.mark.asyncio
async def test_diagnostic_ranks_and_scores_populated(
    db_session: AsyncSession,
    seeded_rbac_corpus: dict[str, str | uuid.UUID],
) -> None:
    """Assert Test 4: All returned chunks have valid rrf_score and dense/sparse diagnostic ranks."""
    tenant_a = str(seeded_rbac_corpus["tenant_a"])

    sec_ctx = SecurityContext(
        tenant_id=tenant_a,
        allowed_roles=("executive", "support_tier_1", "public"),
        scope_hash=compute_scope_hash(tenant_a, ("executive", "support_tier_1", "public")),
    )

    retriever = PostgresHybridRetriever(session=db_session, candidate_pool_size=50)
    query_vector = [0.85] * 384
    query_text = "ERR_409_CONFLICT"

    results = await retriever.retrieve_hybrid(
        security_ctx=sec_ctx,
        query_text=query_text,
        query_embedding=query_vector,
        top_k=10,
    )

    assert len(results) > 0
    # Results must be ordered monotonically descending by rrf_score
    scores = [c.rrf_score for c in results]
    assert scores == sorted(scores, reverse=True)

    for chunk in results:
        assert chunk.rrf_score > 0.0
        assert chunk.dense_rank is not None or chunk.sparse_rank is not None
        assert chunk.content != ""
        assert chunk.document_title == "Acme Corp Enterprise Runbook"
