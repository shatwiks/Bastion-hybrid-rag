import asyncio
import uuid

import pytest

from app.retrievers.base import RetrievedChunk
from app.services.reranker import CrossEncoderRerankerService, get_reranker_service


def _make_chunk(
    content: str,
    *,
    dense_rank: int | None = 1,
    sparse_rank: int | None = 2,
    rrf_score: float = 0.032,
    document_title: str = "Storage Troubleshooting Guide",
    section_header: str = "Error Codes",
) -> RetrievedChunk:
    return RetrievedChunk(
        chunk_id=str(uuid.uuid4()),
        document_id=str(uuid.uuid4()),
        document_title=document_title,
        section_header=section_header,
        content=content,
        allowed_roles=["support_tier_1", "executive"],
        dense_rank=dense_rank,
        dense_score=0.81,
        sparse_rank=sparse_rank,
        sparse_score=0.45,
        rrf_score=rrf_score,
    )


@pytest.fixture(scope="module")
def warmed_reranker_service() -> CrossEncoderRerankerService:
    """Return a pre-warmed CrossEncoderRerankerService once for the unit test module."""
    service = get_reranker_service()
    service.warmup()
    return service


@pytest.mark.asyncio
async def test_rerank_before_warmup_raises_runtime_error() -> None:
    """Calling rerank on an uninitialized service raises a clear RuntimeError."""
    uninitialized = CrossEncoderRerankerService()
    chunk = _make_chunk("Diagnostic steps for ERR_409_CONFLICT.")
    with pytest.raises(RuntimeError, match="not initialized"):
        await uninitialized.rerank("How do I fix ERR_409_CONFLICT?", [chunk])


@pytest.mark.asyncio
async def test_rerank_empty_chunks_returns_empty_and_zero_latency(
    warmed_reranker_service: CrossEncoderRerankerService,
) -> None:
    """Empty candidate list returns ([], 0.0) without invoking model prediction."""
    scored, latency_ms = await warmed_reranker_service.rerank("ERR_409_CONFLICT", [])
    assert scored == []
    assert latency_ms == 0.0


@pytest.mark.asyncio
async def test_rerank_sigmoid_calibration_relevance_separation_and_rank_preservation(
    warmed_reranker_service: CrossEncoderRerankerService,
) -> None:
    """Scores are calibrated in [0.0, 1.0], relevant >= 0.65 vs distractor < 0.30, ranks preserved."""
    distractor = _make_chunk(
        "The corporate cafeteria menu features roasted vegetables and sourdough bread every Friday.",
        dense_rank=1,
        sparse_rank=5,
        rrf_score=0.050,
    )
    relevant = _make_chunk(
        (
            "To fix ERR_409_CONFLICT during concurrent storage sync, inspect the active lease lock "
            "using acme-storage-cli locks inspect and retry with exponential backoff."
        ),
        dense_rank=3,
        sparse_rank=1,
        rrf_score=0.031,
    )
    partial = _make_chunk(
        "Enterprise storage replication uses asynchronous checkpoints across regional clusters.",
        dense_rank=2,
        sparse_rank=4,
        rrf_score=0.035,
    )

    query = "How do I fix ERR_409_CONFLICT during concurrent storage sync?"
    reranked, latency_ms = await warmed_reranker_service.rerank(
        query, [distractor, partial, relevant]
    )

    assert latency_ms > 0.0
    assert len(reranked) == 3

    # Every score strictly within [0.0, 1.0]
    for chunk in reranked:
        assert chunk.rerank_score is not None
        assert isinstance(chunk.rerank_score, float)
        assert 0.0 <= chunk.rerank_score <= 1.0

    # Sorted descending by rerank_score
    scores = [c.rerank_score for c in reranked]
    assert scores == sorted(scores, reverse=True)

    # Relevant chunk ranks first (>= 0.65) and distractor ranks last (< 0.30)
    assert reranked[0].chunk_id == relevant.chunk_id
    assert reranked[0].rerank_score is not None and reranked[0].rerank_score >= 0.65
    assert reranked[-1].chunk_id == distractor.chunk_id
    assert reranked[-1].rerank_score is not None and reranked[-1].rerank_score < 0.30

    # Original RRF diagnostic ranks and input immutability preserved
    assert reranked[0].dense_rank == 3
    assert reranked[0].sparse_rank == 1
    assert reranked[0].rrf_score == pytest.approx(0.031)
    assert reranked[-1].dense_rank == 1
    assert reranked[-1].sparse_rank == 5
    assert reranked[-1].rrf_score == pytest.approx(0.050)
    assert relevant.rerank_score is None


@pytest.mark.asyncio
async def test_concurrent_rerank_calls_are_non_blocking(
    warmed_reranker_service: CrossEncoderRerankerService,
) -> None:
    """Concurrent rerank calls under asyncio.gather do not block the asyncio event loop."""
    loop_ticks = 0
    stop_ticker = False

    async def ticker() -> None:
        nonlocal loop_ticks
        while not stop_ticker:
            loop_ticks += 1
            await asyncio.sleep(0.005)

    async def run_batches() -> list[tuple[list[RetrievedChunk], float]]:
        batches = [
            [
                _make_chunk(
                    f"Troubleshooting ERR_409_CONFLICT lease contention step {idx}.",
                    dense_rank=idx + 1,
                    sparse_rank=idx + 1,
                    rrf_score=0.03,
                )
                for idx in range(4)
            ]
            for _ in range(6)
        ]
        try:
            return await asyncio.gather(
                *(
                    warmed_reranker_service.rerank(
                        "How to resolve ERR_409_CONFLICT lease contention?", batch
                    )
                    for batch in batches
                )
            )
        finally:
            nonlocal stop_ticker
            stop_ticker = True

    _, results = await asyncio.gather(ticker(), run_batches())

    assert len(results) == 6
    for scored_chunks, latency_ms in results:
        assert len(scored_chunks) == 4
        assert latency_ms >= 0.0
        assert all(
            c.rerank_score is not None and 0.0 <= c.rerank_score <= 1.0 for c in scored_chunks
        )
    assert loop_ticks >= 1


def test_get_reranker_service_returns_singleton() -> None:
    """get_reranker_service returns the same singleton instance."""
    first = get_reranker_service()
    second = get_reranker_service()
    assert first is second
