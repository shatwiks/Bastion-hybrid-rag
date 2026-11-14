import time
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.schemas.cache import CachedCitation
from app.schemas.retrieval import ChatMessage


class ChatStreamRequest(BaseModel):
    """Request payload for POST /api/v1/chat/stream."""

    query: str = Field(..., min_length=1, description="User query string")
    chat_history: list[ChatMessage] = Field(
        default_factory=list,
        description="Optional prior conversational turns for multi-turn query rewriting",
    )
    bypass_cache: bool = Field(
        default=False,
        description="When True, bypasses Step 2 semantic cache lookup while still caching valid outputs",
    )

    @field_validator("query")
    @classmethod
    def validate_non_blank_query(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("query must not be empty or whitespace-only")
        return cleaned


class PipelineStepTelemetry(BaseModel):
    """Per-stage status, latency, and structured diagnostic metadata emitted via step_update."""

    model_config = ConfigDict(frozen=True)

    step: int = Field(..., ge=1, le=6, description="1-indexed RAG lifecycle stage (1..6)")
    name: str = Field(..., description="Machine-readable lifecycle step identifier")
    label: str = Field(..., description="Human-readable stage label for telemetry inspector")
    status: Literal["pending", "running", "completed", "short_circuited", "skipped"] = Field(
        ..., description="Current execution status of this stage"
    )
    latency_ms: float = Field(default=0.0, ge=0.0, description="Stage execution latency in ms")
    details: dict[str, Any] = Field(
        default_factory=dict,
        description="Stage-specific telemetry details (RBAC, cache sim, RRF ranks, rerank scores)",
    )


class PipelineTraceRecord(BaseModel):
    """Complete 6-step RAG lifecycle trace persisted for Langfuse and GET /api/v1/chat/traces/{trace_id}."""

    model_config = ConfigDict(frozen=True)

    trace_id: str = Field(..., description="Unique trace identifier")
    tenant_id: str = Field(..., description="Verified tenant_id from SecurityContext")
    scope_hash: str = Field(..., description="Canonical RBAC scope hash from SecurityContext")
    original_query: str = Field(..., description="Raw user query")
    rewritten_query: str = Field(..., description="Standalone query used for cache/retrieval")
    cache_hit: bool = Field(..., description="True when Step 2 semantic cache short-circuited")
    cache_similarity: float = Field(
        ..., ge=0.0, le=1.0, description="Highest semantic cache cosine similarity observed"
    )
    refused: bool = Field(..., description="True when Step 4 Refusal Gate short-circuited")
    refusal_reason: str | None = Field(
        default=None, description="Deterministic refusal reason code when refused is True"
    )
    top_rerank_score: float = Field(
        ..., ge=0.0, le=1.0, description="Highest Cross-Encoder score observed"
    )
    llm_called: bool = Field(..., description="Whether Step 5 grounded generation executed")
    steps: list[PipelineStepTelemetry] = Field(
        default_factory=list, description="Ordered list of lifecycle step telemetry records"
    )
    citations: list[CachedCitation] = Field(
        default_factory=list, description="Grounded citations delivered to the user"
    )
    total_latency_ms: float = Field(..., ge=0.0, description="Total end-to-end pipeline latency in ms")
    entity_fingerprint: str = Field(
        default="none", description="Normalized technical entity fingerprint used in Step 2"
    )
    token_usage: dict[str, int] = Field(
        default_factory=dict, description="Prompt, completion, and total token counts"
    )
    created_at: float = Field(
        default_factory=time.time, description="Unix timestamp when the trace was recorded"
    )
