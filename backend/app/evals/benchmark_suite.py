"""Comparative CI benchmark runner: Naive Dense-Only Baseline vs. Enterprise Hybrid RAG.

Measures genuine PostgreSQL + HuggingFace execution across:
1. Retrieval Precision & MRR Lift (Cohort 1 Answerable Golden + Technical Jargon Probes)
2. Hallucination Reduction & Zero RBAC Leakage (Cohort 2 Adversarial Refusal & RBAC Probes)
"""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, Field
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import compute_scope_hash
from app.db.session import async_engine, async_session_maker
from app.evals.ragas_runner import (
    AdversarialRefusalItem,
    AnswerableGoldenItem,
    PipelineExecutionOutcome,
    _find_leaked_terms,
    _parse_sse_frames,
    load_adversarial_dataset,
    load_answerable_dataset,
    resolve_eval_datasets_dir,
)
from app.redis_client import close_redis_pool
from app.retrievers.base import RetrievedChunk
from app.retrievers.postgres_hybrid import PostgresHybridRetriever
from app.schemas.auth import SecurityContext
from app.schemas.chat import ChatStreamRequest
from app.scripts.seed_corpus import run_seed
from app.services.embeddings import EmbeddingService, get_embedding_service
from app.services.grounded_generator import GroundedGeneratorService
from app.services.query_rewriter import QueryRewriterService
from app.services.rag_pipeline import RAGPipelineOrchestrator
from app.services.refusal_gate import RefusalGateService
from app.services.reranker import CrossEncoderRerankerService, get_reranker_service
from app.services.semantic_cache import SemanticCacheService
from app.services.telemetry import TelemetryService

_DENSE_BASELINE_SQL = text(
    """
    SELECT
        c.id::text AS chunk_id,
        c.document_id::text AS document_id,
        c.tenant_id,
        d.title AS document_title,
        c.section_header,
        c.content,
        c.allowed_roles,
        (1.0 - (c.embedding <=> CAST(:query_embedding AS vector))) AS cosine_score
    FROM document_chunks c
    JOIN documents d ON d.id = c.document_id
    WHERE c.tenant_id = :tenant_id
      AND c.allowed_roles && :user_roles
    ORDER BY c.embedding <=> CAST(:query_embedding AS vector) ASC
    LIMIT :top_k
    """
)


class TechnicalJargonProbe(BaseModel):
    """Exact technical-token lookup grounded in seeded multi-tenant corpus documents."""

    id: str
    tenant_id: str
    persona: Literal["public", "support_tier_1", "executive"]
    allowed_roles: list[str] = Field(..., min_length=1)
    query: str = Field(..., min_length=1)
    expected_token: str = Field(..., min_length=1)
    expected_document_title: str = Field(..., min_length=1)
    category: str = "technical_identifier"


DEFAULT_TECHNICAL_JARGON_PROBES: tuple[TechnicalJargonProbe, ...] = (
    TechnicalJargonProbe(
        id="jargon-01",
        tenant_id="acme_corp",
        persona="executive",
        allowed_roles=["public", "support_tier_1", "executive"],
        query="DE-FRA-04",
        expected_token="DE-FRA-04",
        expected_document_title="Q3 Financial Expansion Plan",
        category="facility_code",
    ),
    TechnicalJargonProbe(
        id="jargon-02",
        tenant_id="acme_corp",
        persona="executive",
        allowed_roles=["public", "support_tier_1", "executive"],
        query="JP-TYO-02",
        expected_token="JP-TYO-02",
        expected_document_title="Q3 Financial Expansion Plan",
        category="facility_code",
    ),
    TechnicalJargonProbe(
        id="jargon-03",
        tenant_id="acme_corp",
        persona="support_tier_1",
        allowed_roles=["public", "support_tier_1"],
        query="lease-9921-f8a",
        expected_token="lease-9921-f8a",
        expected_document_title="Storage Troubleshooting Guide",
        category="lease_identifier",
    ),
    TechnicalJargonProbe(
        id="jargon-04",
        tenant_id="acme_corp",
        persona="support_tier_1",
        allowed_roles=["public", "support_tier_1"],
        query="SKU-4410-C",
        expected_token="SKU-4410-C",
        expected_document_title="Hardware Inventory Skus",
        category="hardware_sku",
    ),
    TechnicalJargonProbe(
        id="jargon-05",
        tenant_id="acme_corp",
        persona="public",
        allowed_roles=["public"],
        query="/v2/health/ready",
        expected_token="/v2/health/ready",
        expected_document_title="Cloud Storage Overview",
        category="api_endpoint",
    ),
    TechnicalJargonProbe(
        id="jargon-06",
        tenant_id="globex_corp",
        persona="support_tier_1",
        allowed_roles=["public", "support_tier_1"],
        query="ERR_502_REPLICA_DESYNC",
        expected_token="ERR_502_REPLICA_DESYNC",
        expected_document_title="Firewall Error Codes",
        category="error_code",
    ),
    TechnicalJargonProbe(
        id="jargon-07",
        tenant_id="globex_corp",
        persona="support_tier_1",
        allowed_roles=["public", "support_tier_1"],
        query="SKU-GLX-900",
        expected_token="SKU-GLX-900",
        expected_document_title="Appliance Skus",
        category="hardware_sku",
    ),
    TechnicalJargonProbe(
        id="jargon-08",
        tenant_id="globex_corp",
        persona="executive",
        allowed_roles=["public", "support_tier_1", "executive"],
        query="TARGET-SENTINEL-X",
        expected_token="TARGET-SENTINEL-X",
        expected_document_title="Acquisition Targets Q4",
        category="acquisition_codename",
    ),
    TechnicalJargonProbe(
        id="jargon-09",
        tenant_id="acme_corp",
        persona="public",
        allowed_roles=["public"],
        query="Standard-HA",
        expected_token="Standard-HA",
        expected_document_title="Cloud Storage Overview",
        category="storage_tier",
    ),
    TechnicalJargonProbe(
        id="jargon-10",
        tenant_id="globex_corp",
        persona="public",
        allowed_roles=["public"],
        query="SOC2_TYPE_II",
        expected_token="SOC2_TYPE_II",
        expected_document_title="Cybersecurity Suite Intro",
        category="compliance_token",
    ),
    TechnicalJargonProbe(
        id="jargon-11",
        tenant_id="globex_corp",
        persona="support_tier_1",
        allowed_roles=["public", "support_tier_1"],
        query="QSFP28",
        expected_token="QSFP28",
        expected_document_title="Appliance Skus",
        category="transceiver_spec",
    ),
)


class RetrievalComparisonCase(BaseModel):
    """Per-query Baseline vs. Enterprise retrieval quality comparison."""

    id: str
    cohort: Literal["answerable_golden", "technical_jargon"]
    tenant_id: str
    persona: str
    query: str
    expected_document_title: str
    expected_token: str | None = None
    baseline_precision_at_k: float
    enterprise_precision_at_k: float
    baseline_reciprocal_rank: float
    enterprise_reciprocal_rank: float
    baseline_refused: bool
    enterprise_refused: bool
    enterprise_top_rerank_score: float
    baseline_latency_ms: float
    enterprise_latency_ms: float


class AdversarialComparisonCase(BaseModel):
    """Per-query Baseline vs. Enterprise refusal and RBAC leakage comparison."""

    id: str
    attack_type: Literal["out_of_domain", "cross_role", "cross_tenant"]
    tenant_id: str
    persona: str
    query: str
    baseline_refused: bool
    baseline_llm_called: bool
    baseline_ungrounded: bool
    enterprise_refused: bool
    enterprise_llm_called: bool
    enterprise_ungrounded: bool
    enterprise_top_rerank_score: float
    baseline_leaked_terms: list[str] = Field(default_factory=list)
    enterprise_leaked_terms: list[str] = Field(default_factory=list)


class BenchmarkGateThresholds(BaseModel):
    """Minimum CI acceptance thresholds enforced on the comparative benchmark."""

    min_enterprise_precision: float = 0.85
    min_mrr_lift_pct: float = 26.0
    min_hallucination_reduction_pct: float = 82.0
    max_rbac_leakage_rate: float = 0.0


class ComparativeBenchmarkReport(BaseModel):
    """Full Baseline vs. Enterprise benchmark output serialized to latest_benchmark.json."""

    generated_at: str
    dataset_counts: dict[str, int]
    baseline_precision: float
    enterprise_precision: float
    answerable_golden_precision: float
    technical_jargon_precision: float
    baseline_mrr: float
    enterprise_mrr: float
    mrr_lift_pct: float
    baseline_ungrounded_rate: float
    enterprise_ungrounded_rate: float
    hallucination_reduction_pct: float
    baseline_rbac_leakage_rate: float
    rbac_leakage_rate: float
    total_duration_ms: float
    gate_thresholds: BenchmarkGateThresholds = Field(default_factory=BenchmarkGateThresholds)
    gates_passed: dict[str, bool] = Field(default_factory=dict)
    all_gates_passed: bool = False
    retrieval_cases: list[RetrievalComparisonCase] = Field(default_factory=list)
    adversarial_cases: list[AdversarialComparisonCase] = Field(default_factory=list)


def default_benchmark_report_path() -> Path:
    """Return the canonical repository path evals/reports/latest_benchmark.json."""
    return resolve_eval_datasets_dir().parent / "reports" / "latest_benchmark.json"


def compute_mrr_lift_pct(baseline_mrr: float, enterprise_mrr: float) -> float:
    """Compute relative MRR lift percentage: (enterprise - baseline) / baseline * 100."""
    if baseline_mrr <= 0.0:
        return 0.0
    return round(((enterprise_mrr - baseline_mrr) / baseline_mrr) * 100.0, 2)


def compute_hallucination_reduction_pct(
    baseline_ungrounded_rate: float,
    enterprise_ungrounded_rate: float,
) -> float:
    """Compute relative reduction in ungrounded generation rate on adversarial/OOD queries."""
    if baseline_ungrounded_rate <= 0.0:
        return 0.0
    return round(
        ((baseline_ungrounded_rate - enterprise_ungrounded_rate) / baseline_ungrounded_rate)
        * 100.0,
        2,
    )


class ComparativeBenchmarkRunner:
    """Executes genuine Naive Dense-Only Baseline vs. Enterprise Hybrid RAG CI benchmarks."""

    def __init__(
        self,
        session: AsyncSession,
        embedding_service: EmbeddingService | None = None,
        reranker_service: CrossEncoderRerankerService | None = None,
        baseline_top_k: int = 5,
        thresholds: BenchmarkGateThresholds | None = None,
    ) -> None:
        self.session = session
        self.embedding_service = embedding_service or get_embedding_service()
        self.reranker_service = reranker_service or get_reranker_service()
        self.baseline_top_k = baseline_top_k
        self.thresholds = thresholds or BenchmarkGateThresholds()
        self._offline_generator = GroundedGeneratorService(
            openai_api_key="",
            gemini_api_key="",
            anthropic_api_key="",
            ollama_api_base="",
        )
        self._orchestrator = self._build_enterprise_orchestrator()

    def _build_enterprise_orchestrator(self) -> RAGPipelineOrchestrator:
        """Build an offline-deterministic, cache-isolated 6-step enterprise orchestrator."""
        return RAGPipelineOrchestrator(
            retriever=PostgresHybridRetriever(session=self.session, candidate_pool_size=50),
            semantic_cache=SemanticCacheService(),
            embedding_service=self.embedding_service,
            query_rewriter=QueryRewriterService(
                openai_api_key="",
                gemini_api_key="",
                anthropic_api_key="",
                ollama_api_base="",
            ),
            refusal_gate=RefusalGateService(reranker=self.reranker_service),
            grounded_generator=self._offline_generator,
            telemetry=TelemetryService(max_traces=200, public_key="", secret_key=""),
        )

    async def _warmup_models(self) -> None:
        """Ensure local bi-encoder and cross-encoder singletons are loaded once."""
        if not self.embedding_service.is_warmed_up:
            self.embedding_service.warmup()
        if not self.reranker_service.is_warmed_up:
            self.reranker_service.warmup()

    async def run_naive_dense_baseline(
        self,
        security_ctx: SecurityContext,
        query: str,
        top_k: int | None = None,
    ) -> PipelineExecutionOutcome:
        """Execute Naive Dense-Only RAG: RBAC-scoped cosine search, no BM25/reranker/gate."""
        await self._warmup_models()
        start = time.perf_counter()
        effective_top_k = top_k or self.baseline_top_k

        query_embedding = await self.embedding_service.embed_query(query)
        rows = (
            await self.session.execute(
                _DENSE_BASELINE_SQL,
                {
                    "tenant_id": security_ctx.tenant_id,
                    "user_roles": list(security_ctx.allowed_roles),
                    "query_embedding": str(query_embedding),
                    "top_k": effective_top_k,
                },
            )
        ).fetchall()

        dense_chunks = [
            RetrievedChunk(
                chunk_id=row.chunk_id,
                document_id=row.document_id,
                tenant_id=row.tenant_id,
                document_title=row.document_title,
                section_header=row.section_header or "",
                content=row.content,
                allowed_roles=list(row.allowed_roles),
                dense_rank=idx,
                dense_score=float(row.cosine_score) if row.cosine_score is not None else 0.0,
                rrf_score=float(row.cosine_score) if row.cosine_score is not None else 0.0,
            )
            for idx, row in enumerate(rows, start=1)
        ]

        # Naive RAG has NO <0.65 Refusal Gate: it always invokes generation on retrieved chunks.
        answer_text = (
            self._offline_generator.synthesize_offline_answer(query=query, chunks=dense_chunks)
            if dense_chunks
            else "No matching context found, attempting best-effort answer."
        )
        latency_ms = round((time.perf_counter() - start) * 1000.0, 2)

        return PipelineExecutionOutcome(
            query=query,
            tenant_id=security_ctx.tenant_id,
            allowed_roles=list(security_ctx.allowed_roles),
            answer_text=answer_text,
            retrieved_contexts=[c.content for c in dense_chunks],
            retrieved_document_titles=[c.document_title for c in dense_chunks],
            retrieved_chunk_ids=[c.chunk_id for c in dense_chunks],
            candidate_document_titles=[c.document_title for c in dense_chunks],
            candidate_section_headers=[c.section_header or "" for c in dense_chunks],
            refused=False,
            refusal_reason=None,
            llm_called=True,
            top_rerank_score=0.0,
            latency_ms=latency_ms,
        )

    async def run_enterprise_hybrid_pipeline(
        self,
        security_ctx: SecurityContext,
        query: str,
    ) -> PipelineExecutionOutcome:
        """Execute full Enterprise 6-step pipeline (Hybrid RRF + Cross-Encoder + <0.65 Gate)."""
        await self._warmup_models()
        start = time.perf_counter()

        raw_frames: list[str] = []
        async for frame in self._orchestrator.stream_lifecycle(
            security_ctx=security_ctx,
            request=ChatStreamRequest(query=query, bypass_cache=True),
        ):
            raw_frames.append(frame)

        latency_ms = round((time.perf_counter() - start) * 1000.0, 2)
        frames = _parse_sse_frames(raw_frames)

        tokens: list[str] = []
        citations: list[dict[str, Any]] = []
        step3_candidates: list[dict[str, Any]] = []
        refusal_payload: dict[str, Any] | None = None
        done_payload: dict[str, Any] = {}
        top_rerank_score = 0.0

        for event_name, payload in frames:
            if event_name == "token":
                tokens.append(str(payload.get("delta", "")))
            elif event_name == "citations":
                citations = list(payload.get("citations", []))
            elif event_name == "refusal":
                refusal_payload = payload
            elif event_name == "done":
                done_payload = payload
            elif event_name == "step_update":
                if payload.get("step") == 3 and payload.get("status") == "completed":
                    step3_candidates = list(payload.get("details", {}).get("candidates", []))
                elif payload.get("step") == 4 and "top_rerank_score" in payload.get("details", {}):
                    top_rerank_score = float(payload["details"]["top_rerank_score"])

        refused = bool(done_payload.get("refused", refusal_payload is not None))
        llm_called = bool(done_payload.get("llm_called", False))
        answer_text = (
            str(refusal_payload.get("message", ""))
            if refused and refusal_payload is not None
            else "".join(tokens)
        )

        return PipelineExecutionOutcome(
            query=query,
            tenant_id=security_ctx.tenant_id,
            allowed_roles=list(security_ctx.allowed_roles),
            answer_text=answer_text,
            retrieved_contexts=[str(c.get("content", "")) for c in citations],
            retrieved_document_titles=[str(c.get("document_title", "")) for c in citations],
            retrieved_chunk_ids=[str(c.get("chunk_id", "")) for c in citations],
            candidate_document_titles=[str(c.get("document_title", "")) for c in step3_candidates],
            candidate_section_headers=[str(c.get("section_header", "")) for c in step3_candidates],
            refused=refused,
            refusal_reason=(
                str(refusal_payload.get("reason"))
                if refusal_payload and refusal_payload.get("reason") is not None
                else None
            ),
            llm_called=llm_called,
            top_rerank_score=top_rerank_score,
            latency_ms=latency_ms,
        )

    @staticmethod
    def _score_document_retrieval(
        outcome: PipelineExecutionOutcome,
        expected_document_title: str,
    ) -> tuple[float, float]:
        """Return (precision_at_k, reciprocal_rank) by matching expected document title."""
        ranked_titles = (
            outcome.retrieved_document_titles
            if outcome.retrieved_document_titles
            else outcome.candidate_document_titles
        )
        if not ranked_titles:
            return 0.0, 0.0
        rel_flags = [title == expected_document_title for title in ranked_titles]
        precision = sum(1 for rel in rel_flags if rel) / len(rel_flags)
        reciprocal_rank = next((1.0 / i for i, rel in enumerate(rel_flags, start=1) if rel), 0.0)
        return round(precision, 4), round(reciprocal_rank, 4)

    @staticmethod
    def _score_jargon_retrieval(
        outcome: PipelineExecutionOutcome,
        expected_document_title: str,
        expected_token: str,
    ) -> tuple[float, float]:
        """Return (precision_at_k, reciprocal_rank) requiring exact token + target doc."""
        contexts = outcome.retrieved_contexts
        titles = outcome.retrieved_document_titles
        if not contexts or not titles:
            return 0.0, 0.0
        token_lower = expected_token.lower()
        doc_flags = [title == expected_document_title for title in titles]
        precision = sum(1 for rel in doc_flags if rel) / len(doc_flags)
        token_flags = [
            title == expected_document_title and token_lower in content.lower()
            for title, content in zip(titles, contexts, strict=False)
        ]
        reciprocal_rank = next(
            (1.0 / i for i, rel in enumerate(token_flags, start=1) if rel),
            0.0,
        )
        return round(precision, 4), round(reciprocal_rank, 4)

    @staticmethod
    def _collect_leaked_terms(
        item: AdversarialRefusalItem,
        outcome: PipelineExecutionOutcome,
    ) -> list[str]:
        """Scan answers, selected contexts, and cross-boundary candidates for forbidden terms."""
        text_blobs = [outcome.answer_text, *outcome.retrieved_contexts]
        if item.attack_type in {"cross_role", "cross_tenant"}:
            text_blobs.extend(outcome.candidate_document_titles)
            text_blobs.extend(outcome.candidate_section_headers)
        return _find_leaked_terms(item.forbidden_terms, text_blobs)

    async def run_benchmark(
        self,
        answerable_items: list[AnswerableGoldenItem] | None = None,
        jargon_probes: list[TechnicalJargonProbe] | None = None,
        adversarial_items: list[AdversarialRefusalItem] | None = None,
        write_report_path: Path | None = None,
    ) -> ComparativeBenchmarkReport:
        """Run full Naive Baseline vs. Enterprise benchmark and optionally save JSON report."""
        start = time.perf_counter()
        await self._warmup_models()

        golden = answerable_items if answerable_items is not None else load_answerable_dataset()
        jargon = (
            jargon_probes if jargon_probes is not None else list(DEFAULT_TECHNICAL_JARGON_PROBES)
        )
        adversarial = (
            adversarial_items if adversarial_items is not None else load_adversarial_dataset()
        )

        retrieval_cases: list[RetrievalComparisonCase] = []

        for item in golden:
            roles = tuple(item.allowed_roles)
            ctx = SecurityContext(
                tenant_id=item.tenant_id,
                allowed_roles=roles,
                scope_hash=compute_scope_hash(item.tenant_id, roles),
            )
            base_out = await self.run_naive_dense_baseline(ctx, item.question)
            ent_out = await self.run_enterprise_hybrid_pipeline(ctx, item.question)
            base_p, base_rr = self._score_document_retrieval(base_out, item.expected_document_title)
            ent_p, ent_rr = self._score_document_retrieval(ent_out, item.expected_document_title)

            retrieval_cases.append(
                RetrievalComparisonCase(
                    id=item.id,
                    cohort="answerable_golden",
                    tenant_id=item.tenant_id,
                    persona=item.persona,
                    query=item.question,
                    expected_document_title=item.expected_document_title,
                    baseline_precision_at_k=base_p,
                    enterprise_precision_at_k=ent_p,
                    baseline_reciprocal_rank=base_rr,
                    enterprise_reciprocal_rank=ent_rr,
                    baseline_refused=base_out.refused,
                    enterprise_refused=ent_out.refused,
                    enterprise_top_rerank_score=round(ent_out.top_rerank_score, 4),
                    baseline_latency_ms=base_out.latency_ms,
                    enterprise_latency_ms=ent_out.latency_ms,
                )
            )

        for probe in jargon:
            roles = tuple(probe.allowed_roles)
            ctx = SecurityContext(
                tenant_id=probe.tenant_id,
                allowed_roles=roles,
                scope_hash=compute_scope_hash(probe.tenant_id, roles),
            )
            base_out = await self.run_naive_dense_baseline(ctx, probe.query)
            ent_out = await self.run_enterprise_hybrid_pipeline(ctx, probe.query)
            base_p, base_rr = self._score_jargon_retrieval(
                base_out, probe.expected_document_title, probe.expected_token
            )
            ent_p, ent_rr = self._score_jargon_retrieval(
                ent_out, probe.expected_document_title, probe.expected_token
            )

            retrieval_cases.append(
                RetrievalComparisonCase(
                    id=probe.id,
                    cohort="technical_jargon",
                    tenant_id=probe.tenant_id,
                    persona=probe.persona,
                    query=probe.query,
                    expected_document_title=probe.expected_document_title,
                    expected_token=probe.expected_token,
                    baseline_precision_at_k=base_p,
                    enterprise_precision_at_k=ent_p,
                    baseline_reciprocal_rank=base_rr,
                    enterprise_reciprocal_rank=ent_rr,
                    baseline_refused=base_out.refused,
                    enterprise_refused=ent_out.refused,
                    enterprise_top_rerank_score=round(ent_out.top_rerank_score, 4),
                    baseline_latency_ms=base_out.latency_ms,
                    enterprise_latency_ms=ent_out.latency_ms,
                )
            )

        adversarial_cases: list[AdversarialComparisonCase] = []
        for adv_item in adversarial:
            roles = tuple(adv_item.allowed_roles)
            ctx = SecurityContext(
                tenant_id=adv_item.tenant_id,
                allowed_roles=roles,
                scope_hash=compute_scope_hash(adv_item.tenant_id, roles),
            )
            base_out = await self.run_naive_dense_baseline(ctx, adv_item.question)
            ent_out = await self.run_enterprise_hybrid_pipeline(ctx, adv_item.question)

            base_leaked = self._collect_leaked_terms(adv_item, base_out)
            ent_leaked = self._collect_leaked_terms(adv_item, ent_out)

            # An ungrounded response occurs whenever an out-of-scope query triggers LLM generation
            # instead of being deterministically blocked by the Refusal Gate.
            base_ungrounded = (not base_out.refused) or base_out.llm_called
            ent_ungrounded = (not ent_out.refused) or ent_out.llm_called

            adversarial_cases.append(
                AdversarialComparisonCase(
                    id=adv_item.id,
                    attack_type=adv_item.attack_type,
                    tenant_id=adv_item.tenant_id,
                    persona=adv_item.persona,
                    query=adv_item.question,
                    baseline_refused=base_out.refused,
                    baseline_llm_called=base_out.llm_called,
                    baseline_ungrounded=base_ungrounded,
                    enterprise_refused=ent_out.refused,
                    enterprise_llm_called=ent_out.llm_called,
                    enterprise_ungrounded=ent_ungrounded,
                    enterprise_top_rerank_score=round(ent_out.top_rerank_score, 4),
                    baseline_leaked_terms=base_leaked,
                    enterprise_leaked_terms=ent_leaked,
                )
            )

        ret_div = max(1, len(retrieval_cases))
        golden_cases = [c for c in retrieval_cases if c.cohort == "answerable_golden"]
        jargon_cases = [c for c in retrieval_cases if c.cohort == "technical_jargon"]

        baseline_precision = round(
            sum(c.baseline_precision_at_k for c in retrieval_cases) / ret_div, 4
        )
        enterprise_precision = round(
            sum(c.enterprise_precision_at_k for c in retrieval_cases) / ret_div, 4
        )
        answerable_golden_precision = round(
            sum(c.enterprise_precision_at_k for c in golden_cases) / max(1, len(golden_cases)),
            4,
        )
        technical_jargon_precision = round(
            sum(c.enterprise_precision_at_k for c in jargon_cases) / max(1, len(jargon_cases)),
            4,
        )

        baseline_mrr = round(sum(c.baseline_reciprocal_rank for c in retrieval_cases) / ret_div, 4)
        enterprise_mrr = round(
            sum(c.enterprise_reciprocal_rank for c in retrieval_cases) / ret_div, 4
        )
        mrr_lift_pct = compute_mrr_lift_pct(baseline_mrr, enterprise_mrr)

        adv_div = max(1, len(adversarial_cases))
        baseline_ungrounded_rate = round(
            sum(1 for c in adversarial_cases if c.baseline_ungrounded) / adv_div, 4
        )
        enterprise_ungrounded_rate = round(
            sum(1 for c in adversarial_cases if c.enterprise_ungrounded) / adv_div, 4
        )
        hallucination_reduction_pct = compute_hallucination_reduction_pct(
            baseline_ungrounded_rate, enterprise_ungrounded_rate
        )

        baseline_rbac_leakage_rate = round(
            sum(1 for c in adversarial_cases if len(c.baseline_leaked_terms) > 0) / adv_div, 4
        )
        rbac_leakage_rate = round(
            sum(1 for c in adversarial_cases if len(c.enterprise_leaked_terms) > 0) / adv_div, 4
        )

        gates_passed = {
            "enterprise_precision": enterprise_precision
            >= self.thresholds.min_enterprise_precision,
            "mrr_lift_pct": mrr_lift_pct >= self.thresholds.min_mrr_lift_pct,
            "hallucination_reduction_pct": (
                hallucination_reduction_pct >= self.thresholds.min_hallucination_reduction_pct
            ),
            "rbac_leakage_rate": rbac_leakage_rate <= self.thresholds.max_rbac_leakage_rate,
        }

        total_duration_ms = round((time.perf_counter() - start) * 1000.0, 2)
        report = ComparativeBenchmarkReport(
            generated_at=datetime.now(UTC).isoformat(),
            dataset_counts={
                "answerable_golden": len(golden),
                "technical_jargon": len(jargon),
                "retrieval_total": len(retrieval_cases),
                "adversarial_refusal": len(adversarial),
            },
            baseline_precision=baseline_precision,
            enterprise_precision=enterprise_precision,
            answerable_golden_precision=answerable_golden_precision,
            technical_jargon_precision=technical_jargon_precision,
            baseline_mrr=baseline_mrr,
            enterprise_mrr=enterprise_mrr,
            mrr_lift_pct=mrr_lift_pct,
            baseline_ungrounded_rate=baseline_ungrounded_rate,
            enterprise_ungrounded_rate=enterprise_ungrounded_rate,
            hallucination_reduction_pct=hallucination_reduction_pct,
            baseline_rbac_leakage_rate=baseline_rbac_leakage_rate,
            rbac_leakage_rate=rbac_leakage_rate,
            total_duration_ms=total_duration_ms,
            gate_thresholds=self.thresholds,
            gates_passed=gates_passed,
            all_gates_passed=all(gates_passed.values()),
            retrieval_cases=retrieval_cases,
            adversarial_cases=adversarial_cases,
        )

        if write_report_path is not None:
            self.write_report(report, write_report_path)

        return report

    @staticmethod
    def write_report(
        report: ComparativeBenchmarkReport,
        path: Path | None = None,
    ) -> Path:
        """Persist benchmark JSON report to disk (defaults to evals/reports/latest_benchmark.json)."""
        target = path or default_benchmark_report_path()
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(json.dumps(report.model_dump(mode="json"), indent=2), encoding="utf-8")
        return target


async def _run_cli(output_path: Path | None, seed: bool) -> int:
    """CLI execution wrapper: optionally seeds corpus, runs benchmark, writes report."""
    try:
        if seed:
            await run_seed()
        async with async_session_maker() as session:
            runner = ComparativeBenchmarkRunner(session=session)
            target = output_path or default_benchmark_report_path()
            report = await runner.run_benchmark(write_report_path=target)

        summary = {
            "report_path": str(target),
            "dataset_counts": report.dataset_counts,
            "baseline_precision": report.baseline_precision,
            "enterprise_precision": report.enterprise_precision,
            "baseline_mrr": report.baseline_mrr,
            "enterprise_mrr": report.enterprise_mrr,
            "mrr_lift_pct": report.mrr_lift_pct,
            "baseline_ungrounded_rate": report.baseline_ungrounded_rate,
            "enterprise_ungrounded_rate": report.enterprise_ungrounded_rate,
            "hallucination_reduction_pct": report.hallucination_reduction_pct,
            "rbac_leakage_rate": report.rbac_leakage_rate,
            "gates_passed": report.gates_passed,
            "all_gates_passed": report.all_gates_passed,
            "total_duration_ms": report.total_duration_ms,
        }
        print(json.dumps(summary, indent=2))
        return 0 if report.all_gates_passed else 1
    finally:
        await close_redis_pool()
        await async_engine.dispose()


def main(argv: list[str] | None = None) -> int:
    """Entry point for `python -m app.evals.benchmark_suite`."""
    parser = argparse.ArgumentParser(
        description="Run Comparative RAG CI Benchmark (Naive Dense vs. Enterprise Hybrid)."
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=None,
        help="Optional output path for JSON benchmark report (default: evals/reports/latest_benchmark.json).",
    )
    parser.add_argument(
        "--no-seed",
        action="store_true",
        help="Skip idempotent run_seed() before executing the benchmark suite.",
    )
    args = parser.parse_args(argv)
    return asyncio.run(_run_cli(output_path=args.output, seed=not args.no_seed))


if __name__ == "__main__":
    sys.exit(main())
