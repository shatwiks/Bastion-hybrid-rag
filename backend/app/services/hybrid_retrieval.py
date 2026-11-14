import asyncio
import time

from app.retrievers.base import VectorStoreRetriever
from app.schemas.auth import SecurityContext
from app.schemas.retrieval import ChatMessage, HybridRetrievalResult
from app.services.embeddings import EmbeddingService, get_embedding_service
from app.services.query_rewriter import QueryRewriterService


class HybridRetrievalService:
    """Orchestrates query rewriting, embedding, and RBAC-scoped hybrid RRF retrieval (RET-02)."""

    def __init__(
        self,
        retriever: VectorStoreRetriever,
        embedding_service: EmbeddingService | None = None,
        query_rewriter: QueryRewriterService | None = None,
    ) -> None:
        self.retriever = retriever
        self.embedding_service = embedding_service or get_embedding_service()
        self.query_rewriter = query_rewriter or QueryRewriterService()

    async def retrieve_candidates(
        self,
        security_ctx: SecurityContext,
        query: str,
        chat_history: list[ChatMessage] | None = None,
        top_k: int = 25,
    ) -> HybridRetrievalResult:
        """Rewrite query if multi-turn, embed, and retrieve RBAC-filtered RRF candidates."""
        rewrite_result = await self.query_rewriter.rewrite(
            query=query,
            chat_history=chat_history,
        )

        if not self.embedding_service.is_warmed_up:
            await asyncio.to_thread(self.embedding_service.warmup)

        embed_start = time.perf_counter()
        query_vec = await self.embedding_service.embed_query(rewrite_result.rewritten_query)
        embedding_latency_ms = (time.perf_counter() - embed_start) * 1000.0

        retrieval_start = time.perf_counter()
        candidates = await self.retriever.retrieve_hybrid(
            security_ctx=security_ctx,
            query_text=rewrite_result.rewritten_query,
            query_embedding=query_vec,
            top_k=top_k,
        )
        retrieval_latency_ms = (time.perf_counter() - retrieval_start) * 1000.0

        return HybridRetrievalResult(
            query_rewrite=rewrite_result,
            candidates=candidates,
            embedding_latency_ms=embedding_latency_ms,
            retrieval_latency_ms=retrieval_latency_ms,
        )
