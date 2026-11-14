import asyncio
import math
import threading
import time

import torch
from sentence_transformers import CrossEncoder

from app.config import get_settings
from app.retrievers.base import RetrievedChunk


class CrossEncoderRerankerService:
    """Singleton service for Sigmoid-calibrated local Cross-Encoder reranking (GATE-01)."""

    def __init__(self, model_name: str | None = None, max_concurrency: int = 4) -> None:
        settings = get_settings()
        self.model_name: str = (
            model_name or settings.RERANKER_MODEL or "cross-encoder/ms-marco-MiniLM-L6-v2"
        )
        self.max_concurrency: int = max_concurrency
        self._model: CrossEncoder | None = None
        self._semaphore: asyncio.Semaphore = asyncio.Semaphore(max_concurrency)
        self._semaphore_loop: asyncio.AbstractEventLoop | None = None
        self._warmup_lock = threading.Lock()

    @property
    def is_warmed_up(self) -> bool:
        """Return True when the underlying CrossEncoder weights are loaded."""
        return self._model is not None

    def _get_semaphore(self) -> asyncio.Semaphore:
        """Return a semaphore bound to the active running event loop."""
        loop = asyncio.get_running_loop()
        if self._semaphore_loop is not None and self._semaphore_loop is not loop:
            self._semaphore = asyncio.Semaphore(self.max_concurrency)
        self._semaphore_loop = loop
        return self._semaphore

    def warmup(self) -> None:
        """Synchronously load CrossEncoder with Sigmoid calibration and run a probe pass."""
        with self._warmup_lock:
            if self._model is None:
                model = CrossEncoder(self.model_name, activation_fn=torch.nn.Sigmoid())
                model.predict([("warmup query", "warmup document")], show_progress_bar=False)
                self._model = model

    async def rerank(
        self,
        query: str,
        chunks: list[RetrievedChunk],
    ) -> tuple[list[RetrievedChunk], float]:
        """Score candidate chunks in worker threads and return sorted chunks + latency_ms."""
        if not chunks:
            return ([], 0.0)
        if self._model is None:
            raise RuntimeError(
                "CrossEncoderRerankerService is not initialized. "
                "Call warmup() during application lifespan."
            )

        pairs = [(query, chunk.content) for chunk in chunks]
        semaphore = self._get_semaphore()

        start = time.perf_counter()
        async with semaphore:
            raw_scores = await asyncio.to_thread(
                self._model.predict,
                pairs,
                batch_size=32,
                show_progress_bar=False,
            )
        rerank_latency_ms = (time.perf_counter() - start) * 1000.0

        scored_chunks: list[RetrievedChunk] = []
        for chunk, raw_score in zip(chunks, raw_scores, strict=True):
            score = float(raw_score)
            clamped_score = 0.0 if math.isnan(score) else max(0.0, min(1.0, score))
            scored_chunks.append(chunk.model_copy(update={"rerank_score": clamped_score}))

        scored_chunks.sort(key=lambda c: c.rerank_score or 0.0, reverse=True)
        return (scored_chunks, rerank_latency_ms)


_reranker_service: CrossEncoderRerankerService | None = None


def get_reranker_service() -> CrossEncoderRerankerService:
    """Return the process-wide singleton CrossEncoderRerankerService instance."""
    global _reranker_service
    if _reranker_service is None:
        _reranker_service = CrossEncoderRerankerService()
    return _reranker_service
