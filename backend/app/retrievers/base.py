import inspect
import uuid
from typing import Any, Protocol, runtime_checkable

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.schemas.auth import SecurityContext


class RetrievedChunk(BaseModel):
    """Domain model representing a chunk retrieved via dense, sparse, or hybrid search."""

    model_config = ConfigDict(frozen=True)

    chunk_id: str = Field(..., description="Unique chunk identifier (UUID string)")
    document_id: str = Field(..., description="Parent document identifier (UUID string)")
    document_title: str = Field(..., description="Title of the parent document")
    section_header: str = Field(..., description="Markdown section header for the chunk")
    content: str = Field(..., description="Raw text content of the chunk")
    allowed_roles: list[str] = Field(
        ..., description="List of authorized roles allowed to view this chunk"
    )
    dense_rank: int | None = Field(default=None, description="1-indexed rank from dense vector retrieval")
    dense_score: float | None = Field(default=None, description="Dense cosine similarity score [0.0, 1.0]")
    sparse_rank: int | None = Field(default=None, description="1-indexed rank from sparse BM25/FTS retrieval")
    sparse_score: float | None = Field(default=None, description="Sparse BM25/ts_rank_cd matching score")
    rrf_score: float = Field(..., description="Reciprocal Rank Fusion score combining dense and sparse ranks")
    rerank_score: float | None = Field(
        default=None, description="Calibrated Cross-Encoder reranking score [0.0, 1.0]"
    )

    @field_validator("chunk_id", "document_id", mode="before")
    @classmethod
    def coerce_uuid_to_str(cls, v: Any) -> str:
        if isinstance(v, uuid.UUID):
            return str(v)
        return str(v)


class _VectorStoreRetrieverMeta(type(Protocol)):  # type: ignore[misc]
    """Metaclass enforcing runtime checkable method signatures for VectorStoreRetriever.

    Validates that any conforming class not only provides `retrieve_hybrid`, but also
    requires `security_ctx` as its first operational argument.
    """

    def __instancecheck__(cls, instance: Any) -> bool:
        if not super().__instancecheck__(instance):
            return False
        return cls._validate_retrieve_hybrid_signature(type(instance))

    def __subclasscheck__(cls, subclass: type) -> bool:
        if not super().__subclasscheck__(subclass):
            return False
        return cls._validate_retrieve_hybrid_signature(subclass)

    @staticmethod
    def _validate_retrieve_hybrid_signature(target_cls: type) -> bool:
        fn = getattr(target_cls, "retrieve_hybrid", None)
        if fn is None or not callable(fn):
            return False
        try:
            sig = inspect.signature(fn)
            param_names = [p for p in sig.parameters if p not in ("self", "cls")]
            return bool(param_names and param_names[0] == "security_ctx")
        except (ValueError, TypeError):
            return False


@runtime_checkable
class VectorStoreRetriever(Protocol, metaclass=_VectorStoreRetrieverMeta):
    """Protocol defining the interface for pluggable RAG vector/hybrid retrievers.

    Mandates that `security_ctx` is passed as the first argument to every retrieval
    invocation, mathematically preventing unscoped queries at the architectural boundary (STOR-02).
    """

    async def retrieve_hybrid(
        self,
        security_ctx: SecurityContext,
        query_text: str,
        query_embedding: list[float],
        top_k: int = 25,
    ) -> list[RetrievedChunk]:
        """Execute pre-retrieval RBAC filtered hybrid search.

        Args:
            security_ctx: Immutable caller SecurityContext containing tenant_id and allowed_roles.
            query_text: Raw user query string for lexical/BM25 matching.
            query_embedding: Pre-computed dense embedding vector (e.g. 384 dimensions).
            top_k: Maximum number of fused candidate chunks to return.

        Returns:
            List of RetrievedChunk instances ordered by fused relevance.
        """
        ...


class RetrieverError(Exception):
    """Base exception for all retriever operations with credential-safe diagnostic serialization."""

    def __init__(self, message: str, details: dict[str, Any] | None = None) -> None:
        super().__init__(message)
        self.message = message
        self.details = details or {}

    def to_dict(self) -> dict[str, Any]:
        """Serialize diagnostic failure details without leaking credentials or secret keys."""
        sensitive_keywords = {"token", "secret", "password", "authorization", "bearer", "key"}
        sanitized_details: dict[str, Any] = {}
        for k, v in self.details.items():
            if any(kw in k.lower() for kw in sensitive_keywords):
                sanitized_details[k] = "[REDACTED]"
            else:
                sanitized_details[k] = v

        return {
            "error_type": self.__class__.__name__,
            "message": self.message,
            "details": sanitized_details,
        }


class RBACSecurityViolation(RetrieverError):
    """Raised when an unauthorized access, cross-tenant leak, or role mismatch is detected."""
