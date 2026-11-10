import uuid

import pytest
from pydantic import ValidationError

from app.retrievers.base import (
    RBACSecurityViolation,
    RetrievedChunk,
    RetrieverError,
    VectorStoreRetriever,
)
from app.schemas.auth import SecurityContext


class ConformingDummyRetriever:
    """Mock retriever conforming fully to the VectorStoreRetriever protocol."""

    async def retrieve_hybrid(
        self,
        security_ctx: SecurityContext,
        query_text: str,
        query_embedding: list[float],
        top_k: int = 25,
    ) -> list[RetrievedChunk]:
        return []


class NonConformingRetrieverMissingSecurityCtx:
    """Mock retriever omitting mandatory security_ctx parameter."""

    async def retrieve_hybrid(
        self,
        query_text: str,
        query_embedding: list[float],
        top_k: int = 25,
    ) -> list[RetrievedChunk]:
        return []


class NonConformingRetrieverWrongMethod:
    """Mock retriever with wrong method name."""

    async def retrieve(
        self,
        security_ctx: SecurityContext,
        query: str,
    ) -> list[RetrievedChunk]:
        return []


def test_retrieved_chunk_model_validation_and_serialization() -> None:
    """Test 1: RetrievedChunk enforces all required attributes and validates optional rank fields."""
    chunk_id = str(uuid.uuid4())
    doc_id = str(uuid.uuid4())

    chunk = RetrievedChunk(
        chunk_id=chunk_id,
        document_id=doc_id,
        document_title="Webhook Architecture Guide",
        section_header="Webhook Delivery Failures",
        content="Resolving ERR_409_CONFLICT under concurrent load.",
        allowed_roles=["support_tier_1", "public"],
        dense_rank=1,
        dense_score=0.92,
        sparse_rank=2,
        sparse_score=0.45,
        rrf_score=0.032,
        rerank_score=0.88,
    )

    assert chunk.chunk_id == chunk_id
    assert chunk.document_id == doc_id
    assert chunk.dense_rank == 1
    assert chunk.dense_score == 0.92
    assert chunk.sparse_rank == 2
    assert chunk.sparse_score == 0.45
    assert chunk.rrf_score == 0.032
    assert chunk.rerank_score == 0.88
    assert chunk.allowed_roles == ["support_tier_1", "public"]

    # UUID object coercion test
    chunk_from_uuids = RetrievedChunk(
        chunk_id=uuid.UUID(chunk_id),  # type: ignore[arg-type]
        document_id=uuid.UUID(doc_id),  # type: ignore[arg-type]
        document_title="Doc Title",
        section_header="Header",
        content="Body",
        allowed_roles=["public"],
        rrf_score=0.015,
    )
    assert chunk_from_uuids.chunk_id == chunk_id
    assert chunk_from_uuids.document_id == doc_id
    assert chunk_from_uuids.dense_rank is None
    assert chunk_from_uuids.rerank_score is None

    # Test serialization round-trip
    dumped = chunk.model_dump()
    assert dumped["chunk_id"] == chunk_id
    assert dumped["rrf_score"] == 0.032

    # Missing required field raises ValidationError
    with pytest.raises(ValidationError):
        RetrievedChunk(  # type: ignore[call-arg]
            chunk_id=chunk_id,
            document_id=doc_id,
            # missing document_title, section_header, content, allowed_roles, rrf_score
        )


def test_vector_store_retriever_protocol_conformance() -> None:
    """Test 2: Protocol is runtime-checkable and verifies conforming implementations."""
    retriever = ConformingDummyRetriever()
    assert isinstance(retriever, VectorStoreRetriever)
    assert issubclass(ConformingDummyRetriever, VectorStoreRetriever)


def test_vector_store_retriever_rejects_missing_security_ctx() -> None:
    """Test 3: Implementations omitting security_ctx fail protocol conformance checks."""
    bad_retriever = NonConformingRetrieverMissingSecurityCtx()
    assert not isinstance(bad_retriever, VectorStoreRetriever)
    assert not issubclass(NonConformingRetrieverMissingSecurityCtx, VectorStoreRetriever)

    wrong_method_retriever = NonConformingRetrieverWrongMethod()
    assert not isinstance(wrong_method_retriever, VectorStoreRetriever)
    assert not issubclass(NonConformingRetrieverWrongMethod, VectorStoreRetriever)


def test_retriever_exception_hierarchy_and_sanitization() -> None:
    """Test 4: Custom exception hierarchy serializes details without leaking sensitive credentials."""
    err = RetrieverError(
        message="Database connection failed",
        details={
            "host": "localhost",
            "port": 5432,
            "api_key": "secret_abc_123",
            "bearer_token": "ey12345.sensitive.token",
        },
    )
    assert isinstance(err, Exception)

    data = err.to_dict()
    assert data["error_type"] == "RetrieverError"
    assert data["message"] == "Database connection failed"
    assert data["details"]["host"] == "localhost"
    assert data["details"]["port"] == 5432
    assert data["details"]["api_key"] == "[REDACTED]"
    assert data["details"]["bearer_token"] == "[REDACTED]"

    rbac_err = RBACSecurityViolation(
        message="Cross-tenant query rejected",
        details={"tenant_id": "bad_tenant", "password_hash": "secret"},
    )
    assert isinstance(rbac_err, RetrieverError)
    rbac_data = rbac_err.to_dict()
    assert rbac_data["error_type"] == "RBACSecurityViolation"
    assert rbac_data["details"]["tenant_id"] == "bad_tenant"
    assert rbac_data["details"]["password_hash"] == "[REDACTED]"
