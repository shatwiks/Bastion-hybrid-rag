from pydantic import BaseModel, ConfigDict, Field


class CachedCitation(BaseModel):
    """Serializable citation metadata stored alongside a cached grounded answer."""

    model_config = ConfigDict(frozen=True)

    chunk_id: str = Field(..., description="Unique chunk identifier")
    document_id: str = Field(..., description="Parent document identifier")
    document_title: str = Field(..., description="Source document title")
    section_header: str = Field(..., description="Section breadcrumb/header")
    content: str = Field(..., description="Chunk text content")
    allowed_roles: list[str] = Field(..., description="Authorized roles for the chunk")
    rerank_score: float = Field(..., description="Cross-Encoder relevance score")


class SemanticCacheEntry(BaseModel):
    """Permission-scoped Redis semantic cache payload (CACHE-01, CACHE-02)."""

    model_config = ConfigDict(frozen=True)

    entry_id: str = Field(..., description="Unique cache entry identifier")
    tenant_id: str = Field(..., description="Tenant identifier partitioning the cache key")
    scope_hash: str = Field(..., description="Canonical RBAC scope hash partitioning the cache key")
    entity_fingerprint: str = Field(
        ..., description="Sorted normalized technical token fingerprint (or 'none')"
    )
    query_text: str = Field(..., description="Original or rewritten query text cached")
    query_embedding: list[float] = Field(
        ..., description="L2-normalized query embedding vector used for cosine matching"
    )
    answer_text: str = Field(..., description="Grounded answer text with inline [chunk_id] citations")
    citations: list[CachedCitation] = Field(
        default_factory=list, description="Grounded citations supporting the cached answer"
    )
    top_rerank_score: float = Field(
        ..., description="Top Cross-Encoder confidence score at cache write time"
    )
    created_at: float = Field(..., description="Unix timestamp when the entry was cached")


class SemanticCacheLookupResult(BaseModel):
    """Structured result returned from a permission-scoped Redis semantic cache lookup."""

    model_config = ConfigDict(frozen=True)

    hit: bool = Field(..., description="True if a cached entry met similarity_threshold")
    similarity_score: float = Field(
        default=0.0, description="Highest cosine similarity score observed in the scoped namespace"
    )
    entry: SemanticCacheEntry | None = Field(
        default=None, description="Matched cache entry when hit is True"
    )
    latency_ms: float = Field(..., ge=0.0, description="Cache lookup duration in milliseconds")
    entity_fingerprint: str = Field(
        ..., description="Technical entity fingerprint computed for the query"
    )
