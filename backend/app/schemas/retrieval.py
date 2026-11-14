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


class RefusalGateDecision(BaseModel):
    """Deterministic Refusal Gate output controlling downstream LLM invocation (GATE-02)."""

    model_config = ConfigDict(frozen=True)

    should_refuse: bool = Field(
        ..., description="True when query short-circuits before LLM generation"
    )
    refusal_reason: Literal["no_accessible_chunks", "below_confidence_threshold"] | None = Field(
        default=None,
        description="Structured reason code when the deterministic refusal gate triggers",
    )
    refusal_message: str | None = Field(
        default=None,
        description="Deterministic verified refusal message returned when should_refuse is True",
    )
    top_rerank_score: float = Field(
        ..., ge=0.0, le=1.0, description="Highest calibrated Cross-Encoder score among candidates"
    )
    threshold: float = Field(
        ..., ge=0.0, le=1.0, description="Configured minimum Cross-Encoder confidence threshold"
    )
    llm_called: bool = Field(
        default=False,
        description="Always False at the Refusal Gate boundary prior to generation",
    )
    selected_chunks: list[RetrievedChunk] = Field(
        default_factory=list,
        description="Top context chunks passing the confidence threshold (capped at max_context_chunks)",
    )
    all_reranked_chunks: list[RetrievedChunk] = Field(
        default_factory=list,
        description="All Cross-Encoder scored candidate chunks preserved for telemetry inspection",
    )
    rerank_latency_ms: float = Field(
        ..., ge=0.0, description="Cross-Encoder reranking latency in milliseconds"
    )
