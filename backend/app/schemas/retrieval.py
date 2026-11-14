from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from app.retrievers.base import RetrievedChunk


class ChatMessage(BaseModel):
    """Single conversational turn message used for multi-turn query rewriting."""

    model_config = ConfigDict(frozen=True)

    role: Literal["user", "assistant"] = Field(..., description="Speaker role in conversation")
    content: str = Field(..., description="Raw conversational message text")


class QueryRewriteResult(BaseModel):
    """Structured output from QueryRewriterService including latency and token telemetry."""

    model_config = ConfigDict(frozen=True)

    original_query: str = Field(..., description="Raw user query prior to rewriting")
    rewritten_query: str = Field(..., description="Standalone search-optimized query string")
    was_rewritten: bool = Field(
        ..., description="False when turn-1 fast-path bypassed rewriting; True otherwise"
    )
    preserved_tokens: list[str] = Field(
        default_factory=list,
        description="Technical identifiers extracted from the raw query that must remain verbatim",
    )
    latency_ms: float = Field(..., ge=0.0, description="Query rewrite duration in milliseconds")


class HybridRetrievalResult(BaseModel):
    """Result envelope combining query rewrite metadata, RRF candidates, and step latencies."""

    model_config = ConfigDict(frozen=True)

    query_rewrite: QueryRewriteResult = Field(..., description="Step 3 query rewrite telemetry")
    candidates: list[RetrievedChunk] = Field(
        default_factory=list,
        description="RRF-fused candidate chunks ordered by descending rrf_score",
    )
    embedding_latency_ms: float = Field(
        ..., ge=0.0, description="Query dense embedding latency in milliseconds"
    )
    retrieval_latency_ms: float = Field(
        ..., ge=0.0, description="Hybrid RRF database retrieval latency in milliseconds"
    )
