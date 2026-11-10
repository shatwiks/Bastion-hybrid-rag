import uuid
from unittest.mock import AsyncMock

import pytest
from qdrant_client import AsyncQdrantClient, models
from qdrant_client.http.models.models import QueryResponse, ScoredPoint

from app.core.security import compute_scope_hash
from app.retrievers.base import RetrievedChunk, VectorStoreRetriever
from app.retrievers.qdrant_hybrid import QdrantHybridRetriever
from app.schemas.auth import SecurityContext


@pytest.fixture
def mock_qdrant_client() -> AsyncMock:
    """Fixture providing an AsyncMock for AsyncQdrantClient."""
    return AsyncMock(spec=AsyncQdrantClient)


def test_qdrant_retriever_protocol_conformance(mock_qdrant_client: AsyncMock) -> None:
    """Assert QdrantHybridRetriever satisfies VectorStoreRetriever protocol."""
    retriever = QdrantHybridRetriever(client=mock_qdrant_client)
    assert isinstance(retriever, VectorStoreRetriever)
    assert issubclass(QdrantHybridRetriever, VectorStoreRetriever)


@pytest.mark.asyncio
async def test_qdrant_retriever_constructs_rbac_filter_and_queries_points(
    mock_qdrant_client: AsyncMock,
) -> None:
    """Assert retrieve_hybrid builds pre-retrieval RBAC filter with tenant_id and allowed_roles."""
    tenant_id = "acme_corp"
    roles = ("support_tier_1", "public")
    sec_ctx = SecurityContext(
        tenant_id=tenant_id,
        allowed_roles=roles,
        scope_hash=compute_scope_hash(tenant_id, roles),
    )

    chunk_id = str(uuid.uuid4())
    doc_id = str(uuid.uuid4())
    mock_point = ScoredPoint(
        id=chunk_id,
        version=1,
        score=0.032,
        payload={
            "chunk_id": chunk_id,
            "document_id": doc_id,
            "document_title": "Acme Webhook Guide",
            "section_header": "Concurrency Control",
            "content": "Resolving ERR_409_CONFLICT locks.",
            "allowed_roles": ["support_tier_1", "public"],
            "dense_rank": 1,
            "dense_score": 0.94,
            "sparse_rank": 2,
            "sparse_score": 0.55,
        },
    )

    mock_qdrant_client.query_points.return_value = QueryResponse(points=[mock_point])

    retriever = QdrantHybridRetriever(
        client=mock_qdrant_client,
        collection_name="enterprise_rag_custom",
    )
    query_vector = [0.1] * 384
    query_text = "ERR_409_CONFLICT"

    chunks = await retriever.retrieve_hybrid(
        security_ctx=sec_ctx,
        query_text=query_text,
        query_embedding=query_vector,
        top_k=10,
    )

    # 1. Assert client.query_points was called once with expected arguments
    mock_qdrant_client.query_points.assert_awaited_once()
    call_kwargs = mock_qdrant_client.query_points.await_args.kwargs

    assert call_kwargs["collection_name"] == "enterprise_rag_custom"
    assert call_kwargs["limit"] == 10
    assert isinstance(call_kwargs["query"], models.FusionQuery)
    assert call_kwargs["query"].fusion == models.Fusion.RRF

    # 2. Assert prefetch filter enforces MatchValue on tenant_id and MatchAny on allowed_roles
    prefetch_list = call_kwargs["prefetch"]
    assert len(prefetch_list) == 1
    prefetch = prefetch_list[0]
    assert prefetch.using == "dense"
    assert prefetch.limit == 50
    assert prefetch.query == query_vector

    rbac_filter = prefetch.filter
    assert isinstance(rbac_filter, models.Filter)
    assert len(rbac_filter.must) == 2

    # Check tenant_id condition
    tenant_cond = next(c for c in rbac_filter.must if c.key == "tenant_id")
    assert isinstance(tenant_cond.match, models.MatchValue)
    assert tenant_cond.match.value == tenant_id

    # Check allowed_roles condition
    roles_cond = next(c for c in rbac_filter.must if c.key == "allowed_roles")
    assert isinstance(roles_cond.match, models.MatchAny)
    assert set(roles_cond.match.any) == {"support_tier_1", "public"}

    # 3. Assert mapping to RetrievedChunk domain model instances
    assert len(chunks) == 1
    chunk = chunks[0]
    assert isinstance(chunk, RetrievedChunk)
    assert chunk.chunk_id == chunk_id
    assert chunk.document_id == doc_id
    assert chunk.document_title == "Acme Webhook Guide"
    assert chunk.section_header == "Concurrency Control"
    assert chunk.content == "Resolving ERR_409_CONFLICT locks."
    assert chunk.allowed_roles == ["support_tier_1", "public"]
    assert chunk.dense_rank == 1
    assert chunk.dense_score == 0.94
    assert chunk.sparse_rank == 2
    assert chunk.sparse_score == 0.55
    assert chunk.rrf_score == pytest.approx(0.032)
