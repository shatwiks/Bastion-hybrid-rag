import asyncio
import json
import logging
import re
import time
import uuid
from collections.abc import AsyncIterator
from typing import Any

from app.retrievers.base import VectorStoreRetriever
from app.schemas.auth import SecurityContext
from app.schemas.cache import CachedCitation
from app.schemas.chat import (
    ChatStreamRequest,
    PipelineStepTelemetry,
    PipelineTraceRecord,
)
from app.services.embeddings import EmbeddingService, get_embedding_service
from app.services.grounded_generator import GroundedGeneratorService
from app.services.hybrid_retrieval import HybridRetrievalService
from app.services.query_rewriter import QueryRewriterService
from app.services.refusal_gate import RefusalGateService
from app.services.semantic_cache import SemanticCacheService, compute_entity_fingerprint
from app.services.telemetry import TelemetryService, get_telemetry_service

logger = logging.getLogger("rag_engine.rag_pipeline")

_WORD_OR_SPACE_RE = re.compile(r"\S+\s*|\n+")


def format_sse_event(event: str, payload: dict[str, Any]) -> str:
    """Serialize a Server-Sent Event frame with event name and JSON payload."""
    return f"event: {event}\ndata: {json.dumps(payload)}\n\n"


class RAGPipelineOrchestrator:
    """Coordinates the complete 6-Step Enterprise RAG Request Lifecycle over SSE (GEN-02)."""

    def __init__(
        self,
        retriever: VectorStoreRetriever,
        semantic_cache: SemanticCacheService | None = None,
        embedding_service: EmbeddingService | None = None,
        query_rewriter: QueryRewriterService | None = None,
        hybrid_retrieval: HybridRetrievalService | None = None,
        refusal_gate: RefusalGateService | None = None,
        grounded_generator: GroundedGeneratorService | None = None,
        telemetry: TelemetryService | None = None,
    ) -> None:
        self.retriever = retriever
        self.semantic_cache = semantic_cache or SemanticCacheService()
        self.embedding_service = embedding_service or get_embedding_service()
        self.query_rewriter = query_rewriter or QueryRewriterService()
        self.hybrid_retrieval = hybrid_retrieval or HybridRetrievalService(
            retriever=self.retriever,
            embedding_service=self.embedding_service,
            query_rewriter=self.query_rewriter,
        )
        self.refusal_gate = refusal_gate or RefusalGateService()
        self.grounded_generator = grounded_generator or GroundedGeneratorService()
        self.telemetry = telemetry or get_telemetry_service()

    async def stream_lifecycle(
        self,
        security_ctx: SecurityContext,
        request: ChatStreamRequest,
    ) -> AsyncIterator[str]:
        """Execute Steps 1..6 and yield multiplexed SSE frames."""
        trace_id = uuid.uuid4().hex
        pipeline_start = time.perf_counter()
        steps: list[PipelineStepTelemetry] = []

        # ------------------------------------------------------------------
        # Step 1: Auth & RBAC Guardrail
        # ------------------------------------------------------------------
        s1_start = time.perf_counter()
        step1 = PipelineStepTelemetry(
            step=1,
            name="auth_guardrail",
            label="Auth & RBAC Guardrail",
            status="completed",
            latency_ms=round((time.perf_counter() - s1_start) * 1000.0, 2),
            details={
                "tenant_id": security_ctx.tenant_id,
                "allowed_roles": list(security_ctx.allowed_roles),
                "scope_hash": security_ctx.scope_hash,
            },
        )
        steps.append(step1)
        yield format_sse_event("step_update", step1.model_dump())

        # ------------------------------------------------------------------
        # Step 2: Permission-Scoped Redis Semantic Cache
        # ------------------------------------------------------------------
        s2_start = time.perf_counter()
        rewrite_result = await self.query_rewriter.rewrite(
            query=request.query,
            chat_history=request.chat_history,
        )
        standalone_query = rewrite_result.rewritten_query
        entity_fp = compute_entity_fingerprint(standalone_query)

        if hasattr(self.embedding_service, "is_warmed_up") and not self.embedding_service.is_warmed_up:
            await asyncio.to_thread(self.embedding_service.warmup)
        query_vec = await self.embedding_service.embed_query(standalone_query)

        cache_similarity = 0.0
        if not request.bypass_cache:
            try:
                lookup_res = await self.semantic_cache.lookup(
                    security_ctx=security_ctx,
                    query=standalone_query,
                    query_embedding=query_vec,
                )
            except Exception as exc:  # noqa: BLE001
                logger.warning("Semantic cache lookup failed; proceeding as miss: %s", exc)
                lookup_res = None

            if lookup_res is not None:
                cache_similarity = float(lookup_res.similarity_score)
                entity_fp = lookup_res.entity_fingerprint

            if lookup_res is not None and lookup_res.hit and lookup_res.entry is not None:
                entry = lookup_res.entry
                s2_latency = round((time.perf_counter() - s2_start) * 1000.0, 2)
                step2 = PipelineStepTelemetry(
                    step=2,
                    name="semantic_cache",
                    label="Permission-Scoped Semantic Cache",
                    status="short_circuited",
                    latency_ms=s2_latency,
                    details={
                        "cache_hit": True,
                        "bypassed": False,
                        "similarity_score": round(cache_similarity, 4),
                        "entity_fingerprint": entity_fp,
                        "entry_id": entry.entry_id,
                    },
                )
                steps.append(step2)
                yield format_sse_event("step_update", step2.model_dump())

                for skipped_step, skipped_name, skipped_label in (
                    (3, "hybrid_retrieval", "Hybrid RRF Retrieval"),
                    (4, "rerank_gate", "Cross-Encoder & Refusal Gate"),
                    (5, "grounded_generation", "Grounded Citation Generation"),
                ):
                    skipped = PipelineStepTelemetry(
                        step=skipped_step,
                        name=skipped_name,
                        label=skipped_label,
                        status="skipped",
                        latency_ms=0.0,
                        details={"reason": "semantic_cache_hit"},
                    )
                    steps.append(skipped)
                    yield format_sse_event("step_update", skipped.model_dump())

                for piece in _WORD_OR_SPACE_RE.findall(entry.answer_text):
                    yield format_sse_event("token", {"delta": piece})
                    await asyncio.sleep(0)

                yield format_sse_event(
                    "citations",
                    {"citations": [c.model_dump() for c in entry.citations]},
                )

                s6_start = time.perf_counter()
                total_latency_ms = round((time.perf_counter() - pipeline_start) * 1000.0, 2)
                step6 = PipelineStepTelemetry(
                    step=6,
                    name="telemetry_commit",
                    label="Cache & Telemetry Commit",
                    status="completed",
                    latency_ms=round((time.perf_counter() - s6_start) * 1000.0, 2),
                    details={
                        "trace_id": trace_id,
                        "cache_hit": True,
                        "langfuse_enabled": self.telemetry.langfuse_enabled,
                    },
                )
                steps.append(step6)
                trace_record = PipelineTraceRecord(
                    trace_id=trace_id,
                    tenant_id=security_ctx.tenant_id,
                    scope_hash=security_ctx.scope_hash,
                    original_query=request.query,
                    rewritten_query=standalone_query,
                    cache_hit=True,
                    cache_similarity=round(cache_similarity, 4),
                    refused=False,
                    refusal_reason=None,
                    top_rerank_score=round(entry.top_rerank_score, 4),
                    llm_called=False,
                    steps=steps,
                    citations=entry.citations,
                    total_latency_ms=total_latency_ms,
                    entity_fingerprint=entity_fp,
                )
                await self.telemetry.record_trace(trace_record)
                yield format_sse_event("step_update", step6.model_dump())
                yield format_sse_event(
                    "done",
                    {
                        "trace_id": trace_id,
                        "total_latency_ms": total_latency_ms,
                        "cache_hit": True,
                        "refused": False,
                        "llm_called": False,
                    },
                )
                return

            step2 = PipelineStepTelemetry(
                step=2,
                name="semantic_cache",
                label="Permission-Scoped Semantic Cache",
                status="completed",
                latency_ms=round((time.perf_counter() - s2_start) * 1000.0, 2),
                details={
                    "cache_hit": False,
                    "bypassed": False,
                    "similarity_score": round(cache_similarity, 4),
                    "entity_fingerprint": entity_fp,
                },
            )
        else:
            step2 = PipelineStepTelemetry(
                step=2,
                name="semantic_cache",
                label="Permission-Scoped Semantic Cache",
                status="skipped",
                latency_ms=round((time.perf_counter() - s2_start) * 1000.0, 2),
                details={
                    "cache_hit": False,
                    "bypassed": True,
                    "similarity_score": 0.0,
                    "entity_fingerprint": entity_fp,
                },
            )
        steps.append(step2)
        yield format_sse_event("step_update", step2.model_dump())

        # ------------------------------------------------------------------
        # Step 3: Hybrid RRF Retrieval (Pre-Retrieval RBAC)
        # ------------------------------------------------------------------
        yield format_sse_event(
            "step_update",
            PipelineStepTelemetry(
                step=3,
                name="hybrid_retrieval",
                label="Hybrid RRF Retrieval",
                status="running",
                latency_ms=0.0,
                details={"rewritten_query": standalone_query},
            ).model_dump(),
        )
        s3_start = time.perf_counter()
        retrieval_res = await self.hybrid_retrieval.retrieve_candidates(
            security_ctx=security_ctx,
            query=request.query,
            chat_history=request.chat_history,
            top_k=25,
            rewrite_result=rewrite_result,
            query_embedding=query_vec,
        )
        s3_latency = round((time.perf_counter() - s3_start) * 1000.0, 2)
        step3 = PipelineStepTelemetry(
            step=3,
            name="hybrid_retrieval",
            label="Hybrid RRF Retrieval",
            status="completed",
            latency_ms=s3_latency,
            details={
                "original_query": retrieval_res.query_rewrite.original_query,
                "rewritten_query": retrieval_res.query_rewrite.rewritten_query,
                "was_rewritten": retrieval_res.query_rewrite.was_rewritten,
                "preserved_tokens": retrieval_res.query_rewrite.preserved_tokens,
                "candidate_count": len(retrieval_res.candidates),
                "retrieval_latency_ms": round(retrieval_res.retrieval_latency_ms, 2),
                "candidates": [
                    {
                        "chunk_id": c.chunk_id,
                        "document_title": c.document_title,
                        "section_header": c.section_header,
                        "dense_rank": c.dense_rank,
                        "sparse_rank": c.sparse_rank,
                        "rrf_score": round(c.rrf_score, 6),
                    }
                    for c in retrieval_res.candidates
                ],
            },
        )
        steps.append(step3)
        yield format_sse_event("step_update", step3.model_dump())

        # ------------------------------------------------------------------
        # Step 4: Cross-Encoder Reranking & Deterministic Refusal Gate
        # ------------------------------------------------------------------
        yield format_sse_event(
            "step_update",
            PipelineStepTelemetry(
                step=4,
                name="rerank_gate",
                label="Cross-Encoder & Refusal Gate",
                status="running",
                latency_ms=0.0,
                details={"candidate_count": len(retrieval_res.candidates)},
            ).model_dump(),
        )
        s4_start = time.perf_counter()
        decision = await self.refusal_gate.evaluate(
            query=retrieval_res.query_rewrite.rewritten_query,
            candidates=retrieval_res.candidates,
        )
        s4_latency = round((time.perf_counter() - s4_start) * 1000.0, 2)
        rerank_details: dict[str, Any] = {
            "top_rerank_score": round(decision.top_rerank_score, 4),
            "threshold": decision.threshold,
            "should_refuse": decision.should_refuse,
            "refusal_reason": decision.refusal_reason,
            "selected_count": len(decision.selected_chunks),
            "reranked_candidates": [
                {
                    "chunk_id": c.chunk_id,
                    "document_title": c.document_title,
                    "section_header": c.section_header,
                    "dense_rank": c.dense_rank,
                    "sparse_rank": c.sparse_rank,
                    "rrf_score": round(c.rrf_score, 6),
                    "rerank_score": round(c.rerank_score or 0.0, 4),
                }
                for c in decision.all_reranked_chunks
            ],
        }

        if decision.should_refuse:
            step4 = PipelineStepTelemetry(
                step=4,
                name="rerank_gate",
                label="Cross-Encoder & Refusal Gate",
                status="short_circuited",
                latency_ms=s4_latency,
                details=rerank_details,
            )
            steps.append(step4)
            yield format_sse_event("step_update", step4.model_dump())

            step5 = PipelineStepTelemetry(
                step=5,
                name="grounded_generation",
                label="Grounded Citation Generation",
                status="skipped",
                latency_ms=0.0,
                details={
                    "reason": decision.refusal_reason,
                    "llm_called": False,
                },
            )
            steps.append(step5)
            yield format_sse_event("step_update", step5.model_dump())

            yield format_sse_event(
                "refusal",
                {
                    "refused": True,
                    "reason": decision.refusal_reason,
                    "message": decision.refusal_message,
                    "top_score": round(decision.top_rerank_score, 4),
                    "threshold": decision.threshold,
                },
            )

            s6_start = time.perf_counter()
            total_latency_ms = round((time.perf_counter() - pipeline_start) * 1000.0, 2)
            step6 = PipelineStepTelemetry(
                step=6,
                name="telemetry_commit",
                label="Cache & Telemetry Commit",
                status="completed",
                latency_ms=round((time.perf_counter() - s6_start) * 1000.0, 2),
                details={
                    "trace_id": trace_id,
                    "cache_written": False,
                    "refused": True,
                    "langfuse_enabled": self.telemetry.langfuse_enabled,
                },
            )
            steps.append(step6)
            trace_record = PipelineTraceRecord(
                trace_id=trace_id,
                tenant_id=security_ctx.tenant_id,
                scope_hash=security_ctx.scope_hash,
                original_query=request.query,
                rewritten_query=retrieval_res.query_rewrite.rewritten_query,
                cache_hit=False,
                cache_similarity=round(cache_similarity, 4),
                refused=True,
                refusal_reason=decision.refusal_reason,
                top_rerank_score=round(decision.top_rerank_score, 4),
                llm_called=False,
                steps=steps,
                citations=[],
                total_latency_ms=total_latency_ms,
                entity_fingerprint=entity_fp,
            )
            await self.telemetry.record_trace(trace_record)
            yield format_sse_event("step_update", step6.model_dump())
            yield format_sse_event(
                "done",
                {
                    "trace_id": trace_id,
                    "total_latency_ms": total_latency_ms,
                    "cache_hit": False,
                    "refused": True,
                    "llm_called": False,
                },
            )
            return

        step4 = PipelineStepTelemetry(
            step=4,
            name="rerank_gate",
            label="Cross-Encoder & Refusal Gate",
            status="completed",
            latency_ms=s4_latency,
            details=rerank_details,
        )
        steps.append(step4)
        yield format_sse_event("step_update", step4.model_dump())

        # ------------------------------------------------------------------
        # Step 5: Grounded Citation Generation
        # ------------------------------------------------------------------
        yield format_sse_event(
            "step_update",
            PipelineStepTelemetry(
                step=5,
                name="grounded_generation",
                label="Grounded Citation Generation",
                status="running",
                latency_ms=0.0,
                details={"selected_count": len(decision.selected_chunks)},
            ).model_dump(),
        )
        s5_start = time.perf_counter()
        answer_parts: list[str] = []
        async for delta in self.grounded_generator.stream_answer(
            query=retrieval_res.query_rewrite.rewritten_query,
            chunks=decision.selected_chunks,
            chat_history=request.chat_history,
        ):
            answer_parts.append(delta)
            yield format_sse_event("token", {"delta": delta})

        full_answer = "".join(answer_parts)
        s5_latency = round((time.perf_counter() - s5_start) * 1000.0, 2)
        citations = [
            CachedCitation(
                chunk_id=c.chunk_id,
                document_id=c.document_id,
                document_title=c.document_title,
                section_header=c.section_header,
                content=c.content,
                allowed_roles=list(c.allowed_roles),
                rerank_score=float(c.rerank_score or 0.0),
            )
            for c in decision.selected_chunks
        ]

        step5 = PipelineStepTelemetry(
            step=5,
            name="grounded_generation",
            label="Grounded Citation Generation",
            status="completed",
            latency_ms=s5_latency,
            details={
                "llm_called": True,
                "model": self.grounded_generator.model,
                "mode": self.grounded_generator.last_mode,
                "token_usage": self.grounded_generator.last_token_usage,
                "selected_chunk_ids": [c.chunk_id for c in citations],
            },
        )
        steps.append(step5)
        yield format_sse_event("step_update", step5.model_dump())
        yield format_sse_event(
            "citations",
            {"citations": [c.model_dump() for c in citations]},
        )

        # ------------------------------------------------------------------
        # Step 6: Async Semantic Cache Write & Telemetry Commit
        # ------------------------------------------------------------------
        s6_start = time.perf_counter()
        cache_entry_id: str | None = None
        try:
            cache_entry_id = await self.semantic_cache.store(
                security_ctx=security_ctx,
                query=standalone_query,
                query_embedding=query_vec,
                answer_text=full_answer,
                citations=citations,
                top_rerank_score=decision.top_rerank_score,
            )
        except Exception as exc:  # noqa: BLE001
            logger.warning("Semantic cache store failed; continuing telemetry commit: %s", exc)

        total_latency_ms = round((time.perf_counter() - pipeline_start) * 1000.0, 2)
        step6 = PipelineStepTelemetry(
            step=6,
            name="telemetry_commit",
            label="Cache & Telemetry Commit",
            status="completed",
            latency_ms=round((time.perf_counter() - s6_start) * 1000.0, 2),
            details={
                "trace_id": trace_id,
                "cache_written": cache_entry_id is not None,
                "cache_entry_id": cache_entry_id,
                "langfuse_enabled": self.telemetry.langfuse_enabled,
            },
        )
        steps.append(step6)
        trace_record = PipelineTraceRecord(
            trace_id=trace_id,
            tenant_id=security_ctx.tenant_id,
            scope_hash=security_ctx.scope_hash,
            original_query=request.query,
            rewritten_query=retrieval_res.query_rewrite.rewritten_query,
            cache_hit=False,
            cache_similarity=round(cache_similarity, 4),
            refused=False,
            refusal_reason=None,
            top_rerank_score=round(decision.top_rerank_score, 4),
            llm_called=True,
            steps=steps,
            citations=citations,
            total_latency_ms=total_latency_ms,
            entity_fingerprint=entity_fp,
            token_usage=dict(self.grounded_generator.last_token_usage),
        )
        await self.telemetry.record_trace(trace_record)
        yield format_sse_event("step_update", step6.model_dump())
        yield format_sse_event(
            "done",
            {
                "trace_id": trace_id,
                "total_latency_ms": total_latency_ms,
                "cache_hit": False,
                "refused": False,
                "llm_called": True,
            },
        )
