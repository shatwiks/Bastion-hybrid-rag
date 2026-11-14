from app.config import get_settings
from app.retrievers.base import RetrievedChunk
from app.schemas.retrieval import RefusalGateDecision
from app.services.reranker import CrossEncoderRerankerService, get_reranker_service

VERIFIED_REFUSAL_MESSAGE = (
    "I don't have enough verified information in your accessible knowledge base to answer this."
)


class RefusalGateService:
    """Deterministic < 0.65 Cross-Encoder confidence gate (GATE-02)."""

    def __init__(
        self,
        reranker: CrossEncoderRerankerService | None = None,
        threshold: float | None = None,
        max_context_chunks: int = 5,
    ) -> None:
        settings = get_settings()
        self.reranker: CrossEncoderRerankerService = reranker or get_reranker_service()
        self.threshold: float = (
            settings.REFUSAL_THRESHOLD if threshold is None else float(threshold)
        )
        self.max_context_chunks: int = max_context_chunks

    async def evaluate(
        self,
        query: str,
        candidates: list[RetrievedChunk],
    ) -> RefusalGateDecision:
        """Score candidates with Cross-Encoder and enforce deterministic refusal short-circuit."""
        if not candidates:
            return RefusalGateDecision(
                should_refuse=True,
                refusal_reason="no_accessible_chunks",
                refusal_message=VERIFIED_REFUSAL_MESSAGE,
                top_rerank_score=0.0,
                threshold=self.threshold,
                llm_called=False,
                selected_chunks=[],
                all_reranked_chunks=[],
                rerank_latency_ms=0.0,
            )

        reranked, rerank_latency_ms = await self.reranker.rerank(query, candidates)
        if not reranked:
            return RefusalGateDecision(
                should_refuse=True,
                refusal_reason="no_accessible_chunks",
                refusal_message=VERIFIED_REFUSAL_MESSAGE,
                top_rerank_score=0.0,
                threshold=self.threshold,
                llm_called=False,
                selected_chunks=[],
                all_reranked_chunks=[],
                rerank_latency_ms=rerank_latency_ms,
            )

        top_score = reranked[0].rerank_score if reranked[0].rerank_score is not None else 0.0
        if top_score < self.threshold:
            return RefusalGateDecision(
                should_refuse=True,
                refusal_reason="below_confidence_threshold",
                refusal_message=VERIFIED_REFUSAL_MESSAGE,
                top_rerank_score=top_score,
                threshold=self.threshold,
                llm_called=False,
                selected_chunks=[],
                all_reranked_chunks=reranked,
                rerank_latency_ms=rerank_latency_ms,
            )

        passing_chunks = [
            chunk for chunk in reranked if (chunk.rerank_score or 0.0) >= self.threshold
        ]
        selected_chunks = passing_chunks[: self.max_context_chunks]

        return RefusalGateDecision(
            should_refuse=False,
            refusal_reason=None,
            refusal_message=None,
            top_rerank_score=top_score,
            threshold=self.threshold,
            llm_called=False,
            selected_chunks=selected_chunks,
            all_reranked_chunks=reranked,
            rerank_latency_ms=rerank_latency_ms,
        )
