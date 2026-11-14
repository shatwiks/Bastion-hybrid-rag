from collections.abc import AsyncGenerator

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import compute_scope_hash
from app.db.session import async_engine, async_session_maker
from app.retrievers.postgres_hybrid import PostgresHybridRetriever
from app.schemas.auth import SecurityContext
from app.schemas.retrieval import ChatMessage
from app.scripts.seed_corpus import run_seed
from app.services.embeddings import EmbeddingService, get_embedding_service
from app.services.hybrid_retrieval import HybridRetrievalService
from app.services.query_rewriter import QueryRewriterService

_SEED_INITIALIZED = False


@pytest.fixture(scope="module", autouse=True)
def warmup_embeddings_once() -> None:
    """Warm up the local SentenceTransformer singleton once for this test module."""
    get_embedding_service().warmup()


@pytest.fixture
async def db_session() -> AsyncGenerator[AsyncSession, None]:
    """Ensure seed corpus is populated, yield a session, and dispose engine on teardown."""
    global _SEED_INITIALIZED
    if not _SEED_INITIALIZED:
        await run_seed()
        _SEED_INITIALIZED = True

    async with async_session_maker() as session:
        yield session
    await async_engine.dispose()


def _make_security_ctx(tenant_id: str, roles: tuple[str, ...]) -> SecurityContext:
    return SecurityContext(
        tenant_id=tenant_id,
        allowed_roles=roles,
        scope_hash=compute_scope_hash(tenant_id, roles),
    )


def _build_service(
    session: AsyncSession,
    embedding_service: EmbeddingService | None = None,
) -> HybridRetrievalService:
    retriever = PostgresHybridRetriever(session=session, candidate_pool_size=50)
    rewriter = QueryRewriterService(openai_api_key="", gemini_api_key="", anthropic_api_key="")
    return HybridRetrievalService(
        retriever=retriever,
        embedding_service=embedding_service or get_embedding_service(),
        query_rewriter=rewriter,
    )


@pytest.mark.asyncio
async def test_hybrid_retrieval_exact_error_code_ranks_first_with_telemetry(
    db_session: AsyncSession,
) -> None:
    """Turn-1 query for ERR_409_CONFLICT bypasses rewrite and ranks matching chunk #1 via RRF."""
    service = _build_service(db_session)
    ctx = _make_security_ctx("acme_corp", ("support_tier_1", "executive"))

    result = await service.retrieve_candidates(
        security_ctx=ctx,
        query="How do I fix ERR_409_CONFLICT?",
        top_k=10,
    )

    assert result.query_rewrite.was_rewritten is False
    assert result.query_rewrite.preserved_tokens == ["ERR_409_CONFLICT"]
    assert result.embedding_latency_ms > 0.0
    assert result.retrieval_latency_ms > 0.0
    assert len(result.candidates) > 0

    scores = [c.rrf_score for c in result.candidates]
    assert scores == sorted(scores, reverse=True)

    top_chunk = result.candidates[0]
    assert top_chunk.document_title == "Storage Troubleshooting Guide"
    assert "ERR_409_CONFLICT" in top_chunk.content
    assert top_chunk.dense_rank is not None
    assert top_chunk.sparse_rank is not None
    assert top_chunk.rrf_score > 0.0


@pytest.mark.asyncio
async def test_hybrid_retrieval_cli_flag_not_negated_by_fts(
    db_session: AsyncSession,
) -> None:
    """CLI flag --enable-read-replica matches Globex docs without hyphen-negation starvation."""
    service = _build_service(db_session)
    ctx = _make_security_ctx("globex_corp", ("support_tier_1", "executive"))

    result = await service.retrieve_candidates(
        security_ctx=ctx,
        query="How do I use --enable-read-replica on firewall policy sync?",
        top_k=10,
    )

    assert result.query_rewrite.preserved_tokens == ["--enable-read-replica"]
    assert len(result.candidates) > 0
    assert any(
        "--enable-read-replica" in c.content and c.sparse_rank is not None
        for c in result.candidates[:3]
    )


@pytest.mark.asyncio
async def test_hybrid_retrieval_multiturn_followup_resolves_context(
    db_session: AsyncSession,
) -> None:
    """Multi-turn follow-up rewrites query and retrieves ERR_409_CONFLICT troubleshooting chunks."""
    service = _build_service(db_session)
    ctx = _make_security_ctx("acme_corp", ("support_tier_1", "executive"))
    history = [
        ChatMessage(
            role="user",
            content="We are seeing ERR_409_CONFLICT during Acme bucket sync.",
        ),
        ChatMessage(
            role="assistant",
            content="ERR_409_CONFLICT occurs when two sync workers contend on the same lease.",
        ),
    ]

    result = await service.retrieve_candidates(
        security_ctx=ctx,
        query="What CLI command inspects that active lease?",
        chat_history=history,
        top_k=10,
    )

    assert result.query_rewrite.was_rewritten is True
    assert "ERR_409_CONFLICT" in result.query_rewrite.rewritten_query
    assert len(result.candidates) > 0
    assert any("acme-storage-cli locks inspect" in c.content for c in result.candidates[:3])


@pytest.mark.asyncio
async def test_hybrid_retrieval_enforces_rbac_and_tenant_isolation(
    db_session: AsyncSession,
) -> None:
    """Public role and cross-tenant contexts never retrieve restricted or foreign chunks."""
    service = _build_service(db_session)

    # 1. Public Acme user querying executive M&A topic must never receive executive/support chunks
    acme_public_ctx = _make_security_ctx("acme_corp", ("public",))
    public_result = await service.retrieve_candidates(
        security_ctx=acme_public_ctx,
        query="What is the stretch ceiling bid for Project Nimbus and ERR_409_CONFLICT?",
        top_k=25,
    )
    for chunk in public_result.candidates:
        assert "public" in chunk.allowed_roles
        assert "Project Nimbus" not in chunk.content
        assert "Q3 Financial Expansion Plan" not in chunk.document_title
        assert "Storage Troubleshooting Guide" not in chunk.document_title

    # 2. Globex executive querying Acme error code must never receive Acme chunks
    globex_exec_ctx = _make_security_ctx("globex_corp", ("executive",))
    cross_tenant_result = await service.retrieve_candidates(
        security_ctx=globex_exec_ctx,
        query="How do I fix Acme ERR_409_CONFLICT on SKU-9921-A?",
        top_k=25,
    )
    acme_titles = {
        "Cloud Storage Overview",
        "Storage Troubleshooting Guide",
        "Hardware Inventory Skus",
        "Q3 Financial Expansion Plan",
    }
    for chunk in cross_tenant_result.candidates:
        assert chunk.document_title not in acme_titles
        assert "ERR_409_CONFLICT" not in chunk.content
