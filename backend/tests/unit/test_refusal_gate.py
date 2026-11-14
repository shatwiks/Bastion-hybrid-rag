import uuid

import pytest

from app.retrievers.base import RetrievedChunk
from app.services.refusal_gate import VERIFIED_REFUSAL_MESSAGE, RefusalGateService


def _make_candidate(idx: int, content: str | None = None) -> RetrievedChunk:
    return RetrievedChunk(
        chunk_id=str(uuid.uuid4()),
        document_id=str(uuid.uuid4()),
        document_title=f"Doc {idx}",
        section_header=f"Section {idx}",
        content=content or f"Candidate chunk content {idx}",
        allowed_roles=["support_tier_1", "executive"],
        dense_rank=idx + 1,
        sparse_rank=idx + 1,
        rrf_score=round(0.05 - idx * 0.001, 4),
    )


class _StubReranker:
    """Deterministic async reranker double returning controlled calibrated scores."""

    def __init__(self, scores: list[float], latency_ms: float = 12.5) -> None:
        self._scores = scores
        self._latency_ms = latency_ms
        self.called = False

    async def rerank(
        self,
        query: str,
        chunks: list[RetrievedChunk],
    ) -> tuple[list[RetrievedChunk], float]:
        self.called = True
        scored = [
            chunk.model_copy(update={"rerank_score": score})
            for chunk, score in zip(chunks, self._scores, strict=True)
        ]
        scored.sort(key=lambda c: c.rerank_score or 0.0, reverse=True)
        return (scored, self._latency_ms)


@pytest.mark.asyncio
async def test_refusal_gate_zero_candidates_short_circuits_without_rerank() -> None:
    """Empty candidate pool (0 RBAC-accessible chunks) triggers no_accessible_chunks refusal."""
    stub_reranker = _StubReranker([])
    gate = RefusalGateService(reranker=stub_reranker)  # type: ignore[arg-type]

    decision = await gate.evaluate("What is the Acme executive M&A ceiling?", [])

    assert stub_reranker.called is False
    assert decision.should_refuse is True
    assert decision.refusal_reason == "no_accessible_chunks"
    assert decision.refusal_message == VERIFIED_REFUSAL_MESSAGE
    assert decision.top_rerank_score == 0.0
    assert decision.threshold == pytest.approx(0.65)
    assert decision.llm_called is False
    assert decision.selected_chunks == []
    assert decision.all_reranked_chunks == []
    assert decision.rerank_latency_ms == 0.0


@pytest.mark.asyncio
async def test_refusal_gate_below_threshold_short_circuits_with_telemetry() -> None:
    """Top Cross-Encoder score < 0.65 (e.g. 0.42) triggers below_confidence_threshold refusal."""
    candidates = [_make_candidate(0), _make_candidate(1), _make_candidate(2)]
    stub_reranker = _StubReranker([0.19, 0.42, 0.31], latency_ms=18.4)
    gate = RefusalGateService(reranker=stub_reranker)  # type: ignore[arg-type]

    decision = await gate.evaluate("What is the office Wi-Fi guest password?", candidates)

    assert stub_reranker.called is True
    assert decision.should_refuse is True
    assert decision.refusal_reason == "below_confidence_threshold"
    assert decision.refusal_message == VERIFIED_REFUSAL_MESSAGE
    assert decision.top_rerank_score == pytest.approx(0.42)
    assert decision.threshold == pytest.approx(0.65)
    assert decision.llm_called is False
    assert decision.selected_chunks == []
    assert len(decision.all_reranked_chunks) == 3
    assert [c.rerank_score for c in decision.all_reranked_chunks] == [0.42, 0.31, 0.19]
    assert decision.rerank_latency_ms == pytest.approx(18.4)


@pytest.mark.asyncio
async def test_refusal_gate_passes_and_caps_selected_chunks_at_max_context() -> None:
    """Scores >= 0.65 pass the gate, cap selected_chunks at 5, and preserve all_reranked_chunks."""
    candidates = [_make_candidate(i) for i in range(8)]
    # 6 chunks >= 0.65, 2 chunks < 0.65; top score = 0.89
    scores = [0.71, 0.89, 0.44, 0.83, 0.66, 0.77, 0.30, 0.68]
    stub_reranker = _StubReranker(scores, latency_ms=24.2)
    gate = RefusalGateService(reranker=stub_reranker, max_context_chunks=5)  # type: ignore[arg-type]

    decision = await gate.evaluate("How do I fix ERR_409_CONFLICT?", candidates)

    assert decision.should_refuse is False
    assert decision.refusal_reason is None
    assert decision.refusal_message is None
    assert decision.top_rerank_score == pytest.approx(0.89)
    assert decision.threshold == pytest.approx(0.65)
    assert decision.llm_called is False
    assert decision.rerank_latency_ms == pytest.approx(24.2)

    assert len(decision.all_reranked_chunks) == 8
    assert len(decision.selected_chunks) == 5
    selected_scores = [c.rerank_score for c in decision.selected_chunks]
    assert selected_scores == [0.89, 0.83, 0.77, 0.71, 0.68]
    assert all(score is not None and score >= 0.65 for score in selected_scores)


@pytest.mark.asyncio
async def test_refusal_gate_exact_threshold_boundary_065_passes() -> None:
    """Exact boundary score == 0.65 passes (>= threshold) and selects only >= 0.65 chunks."""
    candidates = [_make_candidate(0), _make_candidate(1)]
    stub_reranker = _StubReranker([0.65, 0.6499], latency_ms=9.1)
    gate = RefusalGateService(reranker=stub_reranker, max_context_chunks=5)  # type: ignore[arg-type]

    decision = await gate.evaluate("Boundary check query", candidates)

    assert decision.should_refuse is False
    assert decision.refusal_reason is None
    assert decision.refusal_message is None
    assert decision.top_rerank_score == pytest.approx(0.65)
    assert decision.llm_called is False
    assert len(decision.selected_chunks) == 1
    assert decision.selected_chunks[0].rerank_score == pytest.approx(0.65)
    assert len(decision.all_reranked_chunks) == 2
