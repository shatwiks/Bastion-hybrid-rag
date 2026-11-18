import time
import uuid
from contextlib import contextmanager
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pytest

from app.retrievers.base import RetrievedChunk
from app.schemas.cache import CachedCitation
from app.schemas.chat import PipelineStepTelemetry, PipelineTraceRecord
from app.services.grounded_generator import GroundedGeneratorService
from app.services.refusal_gate import RefusalGateService
from app.services.telemetry import TelemetryService, get_telemetry_service


def _make_chunk(
    idx: int,
    content: str,
    title: str = "Storage Troubleshooting Guide",
    section: str = "Resolving ERR_409_CONFLICT",
    rerank_score: float = 0.91,
) -> RetrievedChunk:
    return RetrievedChunk(
        chunk_id=f"chunk-{idx}-{uuid.uuid4().hex[:6]}",
        document_id=str(uuid.uuid4()),
        document_title=title,
        section_header=section,
        content=content,
        allowed_roles=["support_tier_1", "executive"],
        dense_rank=idx + 1,
        sparse_rank=idx + 1,
        rrf_score=round(0.032 - idx * 0.002, 5),
        rerank_score=rerank_score,
    )


def _sample_trace(trace_id: str, tenant_id: str = "acme_corp") -> PipelineTraceRecord:
    steps = [
        PipelineStepTelemetry(
            step=1,
            name="auth_guardrail",
            label="Auth & RBAC Guardrail",
            status="completed",
            latency_ms=0.3,
            details={"tenant_id": tenant_id, "scope_hash": "hash123"},
        ),
        PipelineStepTelemetry(
            step=2,
            name="semantic_cache",
            label="Permission-Scoped Semantic Cache",
            status="completed",
            latency_ms=2.1,
            details={"cache_hit": False},
        ),
        PipelineStepTelemetry(
            step=3,
            name="hybrid_retrieval",
            label="Hybrid RRF Retrieval",
            status="completed",
            latency_ms=14.5,
            details={"candidate_count": 5},
        ),
        PipelineStepTelemetry(
            step=4,
            name="rerank_gate",
            label="Cross-Encoder & Refusal Gate",
            status="completed",
            latency_ms=28.0,
            details={"top_rerank_score": 0.91, "threshold": 0.65},
        ),
        PipelineStepTelemetry(
            step=5,
            name="grounded_generation",
            label="Grounded Citation Generation",
            status="completed",
            latency_ms=18.2,
            details={"llm_called": True},
        ),
        PipelineStepTelemetry(
            step=6,
            name="telemetry_commit",
            label="Cache & Telemetry Commit",
            status="completed",
            latency_ms=0.8,
            details={},
        ),
    ]
    return PipelineTraceRecord(
        trace_id=trace_id,
        tenant_id=tenant_id,
        scope_hash="hash123",
        original_query="How do I fix ERR_409_CONFLICT?",
        rewritten_query="How do I fix ERR_409_CONFLICT?",
        cache_hit=False,
        cache_similarity=0.0,
        refused=False,
        refusal_reason=None,
        top_rerank_score=0.91,
        llm_called=True,
        steps=steps,
        citations=[
            CachedCitation(
                chunk_id="chunk-0-abc123",
                document_id="doc-1",
                document_title="Storage Troubleshooting Guide",
                section_header="Resolving ERR_409_CONFLICT",
                content="Inspect lease owner with acme-storage-cli locks inspect.",
                allowed_roles=["support_tier_1", "executive"],
                rerank_score=0.91,
            )
        ],
        total_latency_ms=63.9,
        token_usage={"prompt_tokens": 120, "completion_tokens": 35, "total_tokens": 155},
    )


def test_build_system_prompt_formats_chunks_and_caps_at_max() -> None:
    """System prompt formats [<chunk_id>] (<document_title> - <section_header>) and caps at 5."""
    chunks = [
        _make_chunk(i, f"[Doc > Sec {i}]\nFact number {i} about ERR_409_CONFLICT.")
        for i in range(7)
    ]
    service = GroundedGeneratorService(
        openai_api_key="",
        gemini_api_key="",
        anthropic_api_key="",
        max_context_chunks=5,
    )

    prompt = service.build_system_prompt(chunks)

    assert "STRICT GROUNDING RULES (ZERO HALLUCINATION)" in prompt
    assert "[<chunk_id>]" in prompt
    for chunk in chunks[:5]:
        expected_header = (
            f"[{chunk.chunk_id}] ({chunk.document_title} - {chunk.section_header}):"
        )
        assert expected_header in prompt
    for excluded in chunks[5:]:
        assert excluded.chunk_id not in prompt


@pytest.mark.asyncio
async def test_stream_answer_offline_deterministic_includes_inline_chunk_citations() -> None:
    """Offline mode streams grounded tokens containing exact inline [chunk_id] citations."""
    chunk_a = _make_chunk(
        0,
        "[Storage Troubleshooting Guide > Resolving ERR_409_CONFLICT]\n"
        "ERR_409_CONFLICT occurs when two sync workers contend on the same lease. "
        "Inspect lease owner with `acme-storage-cli locks inspect`.\n\n"
        "Search Index Tokens: ERR-409-CONFLICT ERR_409_CONFLICT err409conflict",
        rerank_score=0.94,
    )
    chunk_b = _make_chunk(
        1,
        "[Storage Troubleshooting Guide > Step 2]\n"
        "Release stale leases older than 30 seconds and retry with exponential backoff.",
        section="Step 2: Release Stale Leases",
        rerank_score=0.82,
    )

    service = GroundedGeneratorService(
        openai_api_key="",
        gemini_api_key="",
        anthropic_api_key="",
    )
    tokens: list[str] = []
    async for delta in service.stream_answer("How do I fix ERR_409_CONFLICT?", [chunk_a, chunk_b]):
        tokens.append(delta)

    full_answer = "".join(tokens)
    assert len(tokens) > 3
    assert service.last_mode == "offline_deterministic"
    assert f"[{chunk_a.chunk_id}]" in full_answer
    assert "ERR_409_CONFLICT" in full_answer
    assert "Search Index Tokens:" not in full_answer
    assert service.last_token_usage["total_tokens"] > 0


@pytest.mark.asyncio
async def test_stream_answer_uses_litellm_temperature_zero_when_api_key_configured() -> None:
    """When a cloud LLM key is configured, stream_answer invokes litellm.acompletion(temperature=0.0)."""
    chunk = _make_chunk(
        0,
        "Run `acme-storage-cli locks inspect` to identify the conflicting lease.",
    )
    service = GroundedGeneratorService(
        model="gpt-4o-mini",
        openai_api_key="sk-test-key",
        gemini_api_key="",
        anthropic_api_key="",
    )

    async def _fake_stream():
        for piece in ["Run `acme-storage-cli locks inspect` ", f"[{chunk.chunk_id}]."]:
            yield SimpleNamespace(
                choices=[SimpleNamespace(delta=SimpleNamespace(content=piece))]
            )

    with patch(
        "app.services.grounded_generator.litellm.acompletion",
        new=AsyncMock(return_value=_fake_stream()),
    ) as mock_acompletion:
        tokens = [
            delta
            async for delta in service.stream_answer("How do I inspect leases?", [chunk])
        ]

    assert "".join(tokens) == f"Run `acme-storage-cli locks inspect` [{chunk.chunk_id}]."
    assert service.last_mode == "cloud_llm"
    mock_acompletion.assert_awaited_once()
    call_kwargs = mock_acompletion.call_args.kwargs
    assert call_kwargs["model"] == "gpt-4o-mini"
    assert call_kwargs["stream"] is True
    assert call_kwargs["temperature"] == 0.0
    assert call_kwargs["api_key"] == "sk-test-key"
    assert f"[{chunk.chunk_id}]" in call_kwargs["messages"][0]["content"]


@pytest.mark.asyncio
async def test_telemetry_service_bounded_ring_buffer_and_local_fallback() -> None:
    """Without Langfuse credentials, TelemetryService records traces cleanly in bounded ring buffer."""
    telemetry = TelemetryService(max_traces=3, public_key="", secret_key="")
    assert telemetry.langfuse_enabled is False

    for idx in range(5):
        tenant = "acme_corp" if idx % 2 == 0 else "globex_corp"
        await telemetry.record_trace(_sample_trace(f"trace-{idx}", tenant_id=tenant))

    # Bounded at max_traces=3: trace-0 and trace-1 evicted
    assert telemetry.get_trace("trace-0") is None
    assert telemetry.get_trace("trace-1") is None
    for idx in (2, 3, 4):
        rec = telemetry.get_trace(f"trace-{idx}")
        assert rec is not None
        assert rec.trace_id == f"trace-{idx}"

    acme_traces = telemetry.list_traces(tenant_id="acme_corp")
    assert [t.trace_id for t in acme_traces] == ["trace-4", "trace-2"]
    assert get_telemetry_service() is get_telemetry_service()


@pytest.mark.asyncio
async def test_telemetry_service_non_blocking_langfuse_span_emission() -> None:
    """When Langfuse is configured, record_trace emits root + 6 step spans asynchronously."""
    observed_calls: list[dict[str, object]] = []
    flushed = {"count": 0}

    class _FakeLangfuseClient:
        @contextmanager
        def start_as_current_observation(self, **kwargs: object):
            observed_calls.append(kwargs)
            yield SimpleNamespace()

        def flush(self) -> None:
            time.sleep(0.01)
            flushed["count"] += 1

    telemetry = TelemetryService(langfuse_client=_FakeLangfuseClient())
    assert telemetry.langfuse_enabled is True

    start = time.perf_counter()
    await telemetry.record_trace(_sample_trace("trace-lf-1", tenant_id="acme_corp"))
    record_elapsed_ms = (time.perf_counter() - start) * 1000.0

    # Immediate ring-buffer availability without waiting for background Langfuse flush
    assert telemetry.get_trace("trace-lf-1") is not None
    assert record_elapsed_ms < 20.0

    await telemetry.flush_pending()
    assert flushed["count"] == 1
    assert len(observed_calls) == 7
    assert observed_calls[0]["name"] == "rag_pipeline_request"
    assert observed_calls[0]["as_type"] == "chain"
    assert [c["name"] for c in observed_calls[1:]] == [
        "auth_guardrail",
        "semantic_cache",
        "hybrid_retrieval",
        "rerank_gate",
        "grounded_generation",
        "telemetry_commit",
    ]


@pytest.mark.asyncio
async def test_refusal_gate_lazy_warms_unwarmed_reranker_and_tolerates_stub_without_attr() -> None:
    """RefusalGateService triggers warmup() only when is_warmed_up exists and is False."""

    class _LazyReranker:
        def __init__(self) -> None:
            self.is_warmed_up = False
            self.warmup_calls = 0

        def warmup(self) -> None:
            self.warmup_calls += 1
            self.is_warmed_up = True

        async def rerank(
            self, query: str, chunks: list[RetrievedChunk]
        ) -> tuple[list[RetrievedChunk], float]:
            assert self.is_warmed_up is True
            return ([c.model_copy(update={"rerank_score": 0.9}) for c in chunks], 5.0)

    lazy_reranker = _LazyReranker()
    gate = RefusalGateService(reranker=lazy_reranker)  # type: ignore[arg-type]
    chunk = _make_chunk(0, "ERR_409_CONFLICT lock resolution")

    decision = await gate.evaluate("ERR_409_CONFLICT", [chunk])
    assert lazy_reranker.warmup_calls == 1
    assert decision.should_refuse is False

    # Second call does not re-warmup
    await gate.evaluate("ERR_409_CONFLICT", [chunk])
    assert lazy_reranker.warmup_calls == 1


@pytest.mark.asyncio
async def test_stream_answer_ollama_passes_api_base_and_handles_trailing_type_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Ollama model prefix streams via api_base without requiring a cloud API key."""
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)

    chunk = _make_chunk(
        0,
        "Run `acme-storage-cli locks inspect` to identify the conflicting lease.",
    )
    service = GroundedGeneratorService(
        model="ollama_chat/llama3.2",
        ollama_api_base="http://localhost:11434/",
    )

    async def _fake_ollama_stream():
        yield SimpleNamespace(
            choices=[SimpleNamespace(delta=SimpleNamespace(content="Use `acme-storage-cli` "))]
        )
        yield SimpleNamespace(
            choices=[SimpleNamespace(delta=SimpleNamespace(content=f"[{chunk.chunk_id}]."))]
        )
        raise TypeError("NoneType object is not subscriptable")

    with patch(
        "app.services.grounded_generator.litellm.acompletion",
        new=AsyncMock(return_value=_fake_ollama_stream()),
    ) as mock_acompletion:
        tokens = [
            delta
            async for delta in service.stream_answer("How do I inspect leases?", [chunk])
        ]

    assert "".join(tokens) == f"Use `acme-storage-cli` [{chunk.chunk_id}]."
    assert service.last_mode == "ollama_local"
    mock_acompletion.assert_awaited_once()
    call_kwargs = mock_acompletion.call_args.kwargs
    assert call_kwargs["model"] == "ollama_chat/llama3.2"
    assert call_kwargs["api_base"] == "http://localhost:11434"
    assert "api_key" not in call_kwargs


@pytest.mark.asyncio
async def test_stream_answer_unreachable_ollama_falls_back_to_offline_grounded(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """If local Ollama server is unreachable before streaming, fall back cleanly."""
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    chunk = _make_chunk(
        0,
        "[Storage Guide > Fix]\nInspect leases using `acme-storage-cli locks inspect`.",
    )
    service = GroundedGeneratorService(
        model="ollama/llama3.2",
        ollama_api_base="http://localhost:11434",
    )

    with patch(
        "app.services.grounded_generator.litellm.acompletion",
        new=AsyncMock(side_effect=ConnectionError("Connection refused")),
    ):
        tokens = [
            delta
            async for delta in service.stream_answer("How do I inspect leases?", [chunk])
        ]

    full_answer = "".join(tokens)
    assert service.last_mode == "offline_deterministic"
    assert f"[{chunk.chunk_id}]" in full_answer
    assert "acme-storage-cli locks inspect" in full_answer

