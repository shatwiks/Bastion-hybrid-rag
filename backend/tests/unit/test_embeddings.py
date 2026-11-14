import asyncio
import math

import pytest

from app.services.embeddings import EmbeddingService, get_embedding_service


@pytest.fixture(scope="module")
def warmed_embedding_service() -> EmbeddingService:
    """Return a pre-warmed EmbeddingService once for the unit test module."""
    service = get_embedding_service()
    service.warmup()
    return service


@pytest.mark.asyncio
async def test_embed_texts_before_warmup_raises_runtime_error() -> None:
    """Calling embed_texts on an uninitialized service raises a clear RuntimeError."""
    uninitialized = EmbeddingService()
    with pytest.raises(RuntimeError, match="not initialized"):
        await uninitialized.embed_texts(["ERR_409_CONFLICT"])


@pytest.mark.asyncio
async def test_embed_texts_dimensions_and_l2_normalization(
    warmed_embedding_service: EmbeddingService,
) -> None:
    """Output vectors must have 384 float dimensions and unit L2 norm."""
    texts = [
        "Error code ERR_409_CONFLICT during concurrent webhook delivery.",
        "Enterprise cloud storage replication architecture overview.",
    ]
    vectors = await warmed_embedding_service.embed_texts(texts)

    assert len(vectors) == 2
    for vec in vectors:
        assert len(vec) == 384
        assert all(isinstance(val, float) for val in vec)
        l2_norm_sq = sum(x**2 for x in vec)
        assert math.isclose(l2_norm_sq, 1.0, abs_tol=1e-4)


@pytest.mark.asyncio
async def test_embed_query_returns_single_384d_normalized_vector(
    warmed_embedding_service: EmbeddingService,
) -> None:
    """embed_query returns a single 384-dimensional unit L2 normalized vector."""
    vector = await warmed_embedding_service.embed_query("How do I resolve ERR_409_CONFLICT?")

    assert len(vector) == 384
    assert all(isinstance(val, float) for val in vector)
    assert abs(sum(x**2 for x in vector) - 1.0) < 1e-4


@pytest.mark.asyncio
async def test_embed_texts_empty_input_returns_empty_list(
    warmed_embedding_service: EmbeddingService,
) -> None:
    """Empty text batch returns an empty list without invoking model encode."""
    assert await warmed_embedding_service.embed_texts([]) == []


@pytest.mark.asyncio
async def test_concurrent_embed_calls_are_non_blocking(
    warmed_embedding_service: EmbeddingService,
) -> None:
    """Concurrent embed_texts calls under asyncio.gather do not stall the event loop."""
    loop_ticks = 0
    stop_ticker = False

    async def ticker() -> None:
        nonlocal loop_ticks
        while not stop_ticker:
            loop_ticks += 1
            await asyncio.sleep(0.005)

    async def run_batches() -> list[list[list[float]]]:
        batches = [
            [f"Batch {idx} document chunk explaining SKU-9921-A and ERR_409_CONFLICT." for idx in range(4)]
            for _ in range(6)
        ]
        try:
            return await asyncio.gather(
                *(warmed_embedding_service.embed_texts(batch) for batch in batches)
            )
        finally:
            nonlocal stop_ticker
            stop_ticker = True

    _, results = await asyncio.gather(ticker(), run_batches())

    assert len(results) == 6
    for batch_vectors in results:
        assert len(batch_vectors) == 4
        for vec in batch_vectors:
            assert len(vec) == 384
            assert abs(sum(x**2 for x in vec) - 1.0) < 1e-4
    assert loop_ticks >= 1


def test_get_embedding_service_returns_singleton() -> None:
    """get_embedding_service returns the same singleton instance."""
    first = get_embedding_service()
    second = get_embedding_service()
    assert first is second
