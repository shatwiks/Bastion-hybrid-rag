import json
import logging
import os
import re
import time
from collections.abc import Awaitable, Callable
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, Field
from ragas import EvaluationDataset, SingleTurnSample, evaluate
from ragas.metrics import AnswerRelevancy, ContextPrecision, ContextRecall, Faithfulness
from ragas.run_config import RunConfig
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.core.security import compute_scope_hash
from app.retrievers.postgres_hybrid import PostgresHybridRetriever
from app.schemas.auth import SecurityContext
from app.schemas.chat import ChatStreamRequest
from app.services.embeddings import EmbeddingService, get_embedding_service
from app.services.grounded_generator import GroundedGeneratorService
from app.services.query_rewriter import QueryRewriterService
from app.services.rag_pipeline import RAGPipelineOrchestrator
from app.services.refusal_gate import RefusalGateService
from app.services.reranker import CrossEncoderRerankerService, get_reranker_service
from app.services.semantic_cache import SemanticCacheService
from app.services.telemetry import TelemetryService

logger = logging.getLogger("rag_engine.evals.ragas_runner")

_INLINE_CITATION_RE = re.compile(r"\[([A-Za-z0-9_-]{4,})\]")


def resolve_eval_datasets_dir() -> Path:
    """Locate evals/datasets/ relative to repository root or current working directory."""
    file_path = Path(__file__).resolve()
    candidates = [
        file_path.parents[3] / "evals" / "datasets",
        file_path.parents[2] / "evals" / "datasets",
        Path.cwd() / "evals" / "datasets",
        Path.cwd().parent / "evals" / "datasets",
    ]
    for candidate in candidates:
        if candidate.is_dir():
            return candidate
    raise FileNotFoundError(f"evals/datasets directory not found from {file_path}")


class AnswerableGoldenItem(BaseModel):
    """Schema for Cohort 1 (Answerable In-Scope) golden evaluation items."""

    id: str = Field(..., min_length=1)
    tenant_id: str = Field(..., min_length=1)
    persona: Literal["public", "support_tier_1", "executive"]
    allowed_roles: list[str] = Field(..., min_length=1)
    question: str = Field(..., min_length=1)
    expected_document_title: str = Field(..., min_length=1)
    expected_keywords: list[str] = Field(default_factory=list)
    reference_answer: str = Field(..., min_length=1)


class AdversarialRefusalItem(BaseModel):
    """Schema for Cohort 2 (Adversarial Refusal & RBAC) evaluation items."""

    id: str = Field(..., min_length=1)
    tenant_id: str = Field(..., min_length=1)
    persona: Literal["public", "support_tier_1", "executive"]
    allowed_roles: list[str] = Field(..., min_length=1)
    question: str = Field(..., min_length=1)
    attack_type: Literal["out_of_domain", "cross_role", "cross_tenant"]
    expected_refusal: bool = Field(default=True)
    forbidden_terms: list[str] = Field(default_factory=list)


class PipelineExecutionOutcome(BaseModel):
    """Normalized execution output captured from a single 6-step RAG lifecycle run."""

    query: str
    tenant_id: str
    allowed_roles: list[str]
    answer_text: str = ""
    retrieved_contexts: list[str] = Field(default_factory=list)
    retrieved_document_titles: list[str] = Field(default_factory=list)
    retrieved_chunk_ids: list[str] = Field(default_factory=list)
    candidate_document_titles: list[str] = Field(default_factory=list)
    candidate_section_headers: list[str] = Field(default_factory=list)
    refused: bool = False
    refusal_reason: str | None = None
    llm_called: bool = False
    top_rerank_score: float = 0.0
    latency_ms: float = 0.0


class AnswerableCaseResult(BaseModel):
    """Per-item evaluation breakdown for Cohort 1."""

    id: str
    tenant_id: str
    persona: str
    question: str
    expected_document_title: str
    retrieved_document_titles: list[str]
    refused: bool
    llm_called: bool
    top_rerank_score: float
    precision_at_k: float
    average_precision: float
    reciprocal_rank: float
    context_recall: float
    citation_faithfulness: float
    answer_relevancy: float
    answer_text: str
    latency_ms: float


class Cohort1Report(BaseModel):
    """Aggregate Cohort 1 metrics (deterministic IR/groundedness + optional Ragas LLM judge)."""

    total_cases: int
    answered_cases: int
    refused_cases: int
    retrieval_precision_at_k: float
    context_precision: float
    mrr: float
    context_recall: float
    citation_faithfulness: float
    answer_relevancy: float
    ragas_llm_judge_used: bool = False
    ragas_scores: dict[str, float] = Field(default_factory=dict)
    case_results: list[AnswerableCaseResult] = Field(default_factory=list)


class AdversarialCaseResult(BaseModel):
    """Per-item evaluation breakdown for Cohort 2."""

    id: str
    attack_type: Literal["out_of_domain", "cross_role", "cross_tenant"]
    tenant_id: str
    persona: str
    question: str
    refused: bool
    llm_called: bool
    top_rerank_score: float
    refusal_reason: str | None = None
    leaked_terms: list[str] = Field(default_factory=list)
    passed: bool
    latency_ms: float


class Cohort2Report(BaseModel):
    """Aggregate Cohort 2 metrics (deterministic refusal accuracy & zero-leakage verification)."""

    total_cases: int
    refused_count: int
    passed_count: int
    refusal_accuracy: float
    llm_bypass_rate: float
    leakage_count: int
    leakage_rate: float
    breakdown_by_attack_type: dict[str, dict[str, float | int]] = Field(default_factory=dict)
    case_results: list[AdversarialCaseResult] = Field(default_factory=list)


class TwoCohortEvaluationReport(BaseModel):
    """Combined two-cohort evaluation output produced by RagasCohortEvaluator."""

    cohort1: Cohort1Report
    cohort2: Cohort2Report
    total_duration_ms: float
    run_config: dict[str, int]


def load_answerable_dataset(path: Path | None = None) -> list[AnswerableGoldenItem]:
    """Load and validate Cohort 1 (answerable_golden.json) items."""
    dataset_path = path or (resolve_eval_datasets_dir() / "answerable_golden.json")
    raw = json.loads(dataset_path.read_text(encoding="utf-8"))
    items = raw.get("items", raw) if isinstance(raw, dict) else raw
    return [AnswerableGoldenItem.model_validate(item) for item in items]


def load_adversarial_dataset(path: Path | None = None) -> list[AdversarialRefusalItem]:
    """Load and validate Cohort 2 (adversarial_refusal.json) items."""
    dataset_path = path or (resolve_eval_datasets_dir() / "adversarial_refusal.json")
    raw = json.loads(dataset_path.read_text(encoding="utf-8"))
    items = raw.get("items", raw) if isinstance(raw, dict) else raw
    return [AdversarialRefusalItem.model_validate(item) for item in items]


def _parse_sse_frames(raw_frames: list[str]) -> list[tuple[str, dict[str, Any]]]:
    """Parse SSE text frames emitted by RAGPipelineOrchestrator.stream_lifecycle."""
    parsed: list[tuple[str, dict[str, Any]]] = []
    for frame in raw_frames:
        event_name = "message"
        data_lines: list[str] = []
        for line in frame.strip().splitlines():
            if line.startswith("event:"):
                event_name = line[len("event:") :].strip()
            elif line.startswith("data:"):
                data_lines.append(line[len("data:") :].strip())
        if data_lines:
            parsed.append((event_name, json.loads("\n".join(data_lines))))
    return parsed


def _compute_average_precision(is_relevant_flags: list[bool]) -> float:
    """Compute Average Precision (AP) over an ordered ranked list of retrieved chunks."""
    if not is_relevant_flags:
        return 0.0
    hits = 0
    precision_sum = 0.0
    for idx, rel in enumerate(is_relevant_flags, start=1):
        if rel:
            hits += 1
            precision_sum += hits / idx
    if hits == 0:
        return 0.0
    return precision_sum / hits


def _compute_keyword_recall(keywords: list[str], haystack: str) -> float:
    """Compute fraction of expected technical/domain keywords present in text."""
    if not keywords:
        return 1.0
    lowered = haystack.lower()
    matched = sum(1 for kw in keywords if kw.lower() in lowered)
    return matched / len(keywords)


def _compute_citation_faithfulness(
    answer_text: str,
    retrieved_chunk_ids: list[str],
    refused: bool,
) -> float:
    """Measure deterministic citation adherence: non-empty answer + valid inline [chunk_id]s."""
    if refused or not answer_text.strip():
        return 0.0
    if not retrieved_chunk_ids:
        return 0.0

    cited_ids = _INLINE_CITATION_RE.findall(answer_text)
    if not cited_ids:
        return 0.0

    valid_ids = set(retrieved_chunk_ids)
    valid_cited = [cid for cid in cited_ids if cid in valid_ids]
    if not valid_cited:
        return 0.0

    # Penalize any hallucinated citation IDs not in retrieved_chunk_ids
    precision_ratio = len(valid_cited) / len(cited_ids)
    return round(precision_ratio, 4)


def _find_leaked_terms(forbidden_terms: list[str], text_blobs: list[str]) -> list[str]:
    """Return any forbidden term appearing (case-insensitive) in response or contexts."""
    if not forbidden_terms:
        return []
    combined = "\n".join(text_blobs).lower()
    return [term for term in forbidden_terms if term.lower() in combined]


class RagasCohortEvaluator:
    """Two-cohort evaluator combining throttled Ragas v0.4 and deterministic IR/RBAC checks."""

    def __init__(
        self,
        session: AsyncSession | None = None,
        orchestrator: RAGPipelineOrchestrator | None = None,
        pipeline_runner: Callable[[SecurityContext, str], Awaitable[PipelineExecutionOutcome]]
        | None = None,
        embedding_service: EmbeddingService | None = None,
        reranker_service: CrossEncoderRerankerService | None = None,
        use_llm_judge: bool | None = None,
        run_config: RunConfig | None = None,
    ) -> None:
        self.session = session
        self.embedding_service = embedding_service or get_embedding_service()
        self.reranker_service = reranker_service or get_reranker_service()
        self._orchestrator = orchestrator
        self._pipeline_runner = pipeline_runner
        self._use_llm_judge = use_llm_judge
        self.run_config = run_config or RunConfig(
            max_workers=2,
            max_retries=5,
            timeout=60,
        )

    def _has_llm_judge_key(self) -> bool:
        """Return True when a supported Cloud LLM API key is configured for Ragas judging."""
        if self._use_llm_judge is False:
            return False
        settings = get_settings()
        candidates = (
            os.environ.get("OPENAI_API_KEY") or settings.OPENAI_API_KEY,
            os.environ.get("GEMINI_API_KEY") or settings.GEMINI_API_KEY,
            os.environ.get("ANTHROPIC_API_KEY") or settings.ANTHROPIC_API_KEY,
        )
        has_key = any(bool(k and k.strip()) for k in candidates)
        if self._use_llm_judge is True:
            return has_key
        return has_key

    def _get_or_create_orchestrator(self) -> RAGPipelineOrchestrator:
        """Build an offline-safe, cache-isolated RAGPipelineOrchestrator bound to AsyncSession."""
        if self._orchestrator is not None:
            return self._orchestrator
        if self.session is None:
            raise RuntimeError(
                "RagasCohortEvaluator requires either session, orchestrator, or pipeline_runner."
            )

        retriever = PostgresHybridRetriever(session=self.session, candidate_pool_size=50)
        query_rewriter = QueryRewriterService(
            openai_api_key="",
            gemini_api_key="",
            anthropic_api_key="",
        )
        semantic_cache = SemanticCacheService()
        refusal_gate = RefusalGateService(reranker=self.reranker_service)
        grounded_generator = GroundedGeneratorService()
        telemetry = TelemetryService(max_traces=200, public_key="", secret_key="")

        self._orchestrator = RAGPipelineOrchestrator(
            retriever=retriever,
            semantic_cache=semantic_cache,
            embedding_service=self.embedding_service,
            query_rewriter=query_rewriter,
            refusal_gate=refusal_gate,
            grounded_generator=grounded_generator,
            telemetry=telemetry,
        )
        return self._orchestrator

    async def _warmup_local_models(self) -> None:
        """Warm up local bi-encoder and cross-encoder singletons once before batch evaluation."""
        if not self.embedding_service.is_warmed_up:
            self.embedding_service.warmup()
        if not self.reranker_service.is_warmed_up:
            self.reranker_service.warmup()

    async def _execute_query(
        self,
        security_ctx: SecurityContext,
        query: str,
    ) -> PipelineExecutionOutcome:
        """Run a single query through the 6-step RAG lifecycle with bypass_cache=True."""
        if self._pipeline_runner is not None:
            return await self._pipeline_runner(security_ctx, query)

        await self._warmup_local_models()
        orchestrator = self._get_or_create_orchestrator()
        start = time.perf_counter()

        raw_frames: list[str] = []
        async for frame in orchestrator.stream_lifecycle(
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
                elif payload.get("step") == 4 and "top_rerank_score" in payload.get(
                    "details", {}
                ):
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
            candidate_document_titles=[
                str(c.get("document_title", "")) for c in step3_candidates
            ],
            candidate_section_headers=[
                str(c.get("section_header", "")) for c in step3_candidates
            ],
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
    def build_single_turn_sample(
        item: AnswerableGoldenItem,
        outcome: PipelineExecutionOutcome,
    ) -> SingleTurnSample:
        """Build a Ragas v0.4 SingleTurnSample from an answerable item and pipeline output."""
        return SingleTurnSample(
            user_input=item.question,
            retrieved_contexts=outcome.retrieved_contexts,
            response=outcome.answer_text,
            reference=item.reference_answer,
        )

    @classmethod
    def build_ragas_dataset(
        cls,
        pairs: list[tuple[AnswerableGoldenItem, PipelineExecutionOutcome]],
    ) -> EvaluationDataset:
        """Build a Ragas v0.4 EvaluationDataset over Cohort 1 samples."""
        samples = [cls.build_single_turn_sample(item, outcome) for item, outcome in pairs]
        return EvaluationDataset(samples=samples)

    def _run_ragas_llm_judge(self, dataset: EvaluationDataset) -> dict[str, float]:
        """Run throttled Ragas v0.4 LLM-as-a-Judge metrics when API credentials are present."""
        metrics = [
            ContextPrecision(),
            ContextRecall(),
            Faithfulness(),
            AnswerRelevancy(),
        ]
        result = evaluate(
            dataset=dataset,
            metrics=metrics,
            run_config=self.run_config,
            show_progress=False,
        )
        scores_dict = getattr(result, "_repr_dict", None) or {}
        if not scores_dict and hasattr(result, "to_pandas"):
            df = result.to_pandas()
            numeric_cols = df.select_dtypes(include="number").columns
            scores_dict = {col: float(df[col].mean()) for col in numeric_cols}
        return {k: round(float(v), 4) for k, v in scores_dict.items()}

    async def _compute_answer_relevancy(
        self,
        item: AnswerableGoldenItem,
        answer_text: str,
        refused: bool,
    ) -> float:
        """Compute deterministic answer relevancy using local embeddings + keyword coverage."""
        if refused or not answer_text.strip():
            return 0.0
        clean_answer = _INLINE_CITATION_RE.sub("", answer_text).strip()
        kw_score = _compute_keyword_recall(item.expected_keywords, clean_answer)
        if self.embedding_service.is_warmed_up and clean_answer:
            vecs = await self.embedding_service.embed_texts(
                [clean_answer, item.reference_answer, item.question]
            )
            ans_vec, ref_vec, q_vec = vecs[0], vecs[1], vecs[2]
            ref_sim = max(0.0, min(1.0, sum(a * b for a, b in zip(ans_vec, ref_vec, strict=True))))
            q_sim = max(0.0, min(1.0, sum(a * b for a, b in zip(ans_vec, q_vec, strict=True))))
            semantic_score = 0.6 * ref_sim + 0.4 * q_sim
            return round(0.6 * semantic_score + 0.4 * kw_score, 4)
        return round(kw_score, 4)

    async def evaluate_answerable_cohort(
        self,
        items: list[AnswerableGoldenItem] | None = None,
    ) -> tuple[Cohort1Report, EvaluationDataset]:
        """Evaluate Cohort 1 (Answerable In-Scope) with Ragas samples and deterministic IR."""
        dataset_items = items if items is not None else load_answerable_dataset()
        sample_pairs: list[tuple[AnswerableGoldenItem, PipelineExecutionOutcome]] = []
        case_results: list[AnswerableCaseResult] = []

        for item in dataset_items:
            roles = tuple(item.allowed_roles)
            ctx = SecurityContext(
                tenant_id=item.tenant_id,
                allowed_roles=roles,
                scope_hash=compute_scope_hash(item.tenant_id, roles),
            )
            outcome = await self._execute_query(ctx, item.question)
            sample_pairs.append((item, outcome))

            # Ranked document relevance across selected citations (fallback to Step 3 candidates)
            ranked_titles = (
                outcome.retrieved_document_titles
                if outcome.retrieved_document_titles
                else outcome.candidate_document_titles
            )
            rel_flags = [title == item.expected_document_title for title in ranked_titles]
            precision_at_k = (
                sum(1 for rel in rel_flags if rel) / len(rel_flags) if rel_flags else 0.0
            )
            avg_precision = _compute_average_precision(rel_flags)
            reciprocal_rank = next(
                (1.0 / idx for idx, rel in enumerate(rel_flags, start=1) if rel),
                0.0,
            )

            combined_contexts = "\n".join(outcome.retrieved_contexts)
            context_recall = _compute_keyword_recall(item.expected_keywords, combined_contexts)
            citation_faithfulness = _compute_citation_faithfulness(
                answer_text=outcome.answer_text,
                retrieved_chunk_ids=outcome.retrieved_chunk_ids,
                refused=outcome.refused,
            )
            answer_relevancy = await self._compute_answer_relevancy(
                item=item,
                answer_text=outcome.answer_text,
                refused=outcome.refused,
            )

            case_results.append(
                AnswerableCaseResult(
                    id=item.id,
                    tenant_id=item.tenant_id,
                    persona=item.persona,
                    question=item.question,
                    expected_document_title=item.expected_document_title,
                    retrieved_document_titles=outcome.retrieved_document_titles,
                    refused=outcome.refused,
                    llm_called=outcome.llm_called,
                    top_rerank_score=round(outcome.top_rerank_score, 4),
                    precision_at_k=round(precision_at_k, 4),
                    average_precision=round(avg_precision, 4),
                    reciprocal_rank=round(reciprocal_rank, 4),
                    context_recall=round(context_recall, 4),
                    citation_faithfulness=round(citation_faithfulness, 4),
                    answer_relevancy=round(answer_relevancy, 4),
                    answer_text=outcome.answer_text,
                    latency_ms=outcome.latency_ms,
                )
            )

        ragas_dataset = self.build_ragas_dataset(sample_pairs)
        ragas_llm_judge_used = False
        ragas_scores: dict[str, float] = {}
        if self._has_llm_judge_key() and len(ragas_dataset.samples) > 0:
            try:
                ragas_scores = self._run_ragas_llm_judge(ragas_dataset)
                ragas_llm_judge_used = True
            except Exception as exc:  # noqa: BLE001
                logger.warning("Ragas LLM Judge execution failed; using deterministic IR: %s", exc)

        total = len(case_results)
        divisor = max(1, total)
        refused_cases = sum(1 for r in case_results if r.refused)
        answered_cases = total - refused_cases

        report = Cohort1Report(
            total_cases=total,
            answered_cases=answered_cases,
            refused_cases=refused_cases,
            retrieval_precision_at_k=round(
                sum(r.precision_at_k for r in case_results) / divisor, 4
            ),
            context_precision=round(
                sum(r.average_precision for r in case_results) / divisor, 4
            ),
            mrr=round(sum(r.reciprocal_rank for r in case_results) / divisor, 4),
            context_recall=round(sum(r.context_recall for r in case_results) / divisor, 4),
            citation_faithfulness=round(
                sum(r.citation_faithfulness for r in case_results) / divisor, 4
            ),
            answer_relevancy=round(sum(r.answer_relevancy for r in case_results) / divisor, 4),
            ragas_llm_judge_used=ragas_llm_judge_used,
            ragas_scores=ragas_scores,
            case_results=case_results,
        )
        return report, ragas_dataset

    async def evaluate_adversarial_cohort(
        self,
        items: list[AdversarialRefusalItem] | None = None,
    ) -> Cohort2Report:
        """Evaluate Cohort 2 (Adversarial Refusal & RBAC) on refusal accuracy & 0.0 leakage."""
        dataset_items = items if items is not None else load_adversarial_dataset()
        case_results: list[AdversarialCaseResult] = []
        attack_buckets: dict[str, dict[str, int]] = {}

        for item in dataset_items:
            roles = tuple(item.allowed_roles)
            ctx = SecurityContext(
                tenant_id=item.tenant_id,
                allowed_roles=roles,
                scope_hash=compute_scope_hash(item.tenant_id, roles),
            )
            outcome = await self._execute_query(ctx, item.question)

            text_blobs = [outcome.answer_text, *outcome.retrieved_contexts]
            if item.attack_type in {"cross_role", "cross_tenant"}:
                text_blobs.extend(outcome.candidate_document_titles)
                text_blobs.extend(outcome.candidate_section_headers)
            leaked_terms = _find_leaked_terms(item.forbidden_terms, text_blobs)

            passed = (
                outcome.refused is item.expected_refusal
                and outcome.llm_called is False
                and len(leaked_terms) == 0
            )
            case_results.append(
                AdversarialCaseResult(
                    id=item.id,
                    attack_type=item.attack_type,
                    tenant_id=item.tenant_id,
                    persona=item.persona,
                    question=item.question,
                    refused=outcome.refused,
                    llm_called=outcome.llm_called,
                    top_rerank_score=round(outcome.top_rerank_score, 4),
                    refusal_reason=outcome.refusal_reason,
                    leaked_terms=leaked_terms,
                    passed=passed,
                    latency_ms=outcome.latency_ms,
                )
            )

            bucket = attack_buckets.setdefault(
                item.attack_type, {"total": 0, "passed": 0, "leaked": 0}
            )
            bucket["total"] += 1
            if passed:
                bucket["passed"] += 1
            if leaked_terms:
                bucket["leaked"] += 1

        total = len(case_results)
        divisor = max(1, total)
        refused_count = sum(1 for r in case_results if r.refused)
        passed_count = sum(1 for r in case_results if r.passed)
        llm_bypass_count = sum(1 for r in case_results if not r.llm_called)
        leakage_count = sum(1 for r in case_results if len(r.leaked_terms) > 0)

        breakdown: dict[str, dict[str, float | int]] = {}
        for attack_type, counts in attack_buckets.items():
            b_total = max(1, counts["total"])
            breakdown[attack_type] = {
                "total": counts["total"],
                "passed": counts["passed"],
                "pass_rate": round(counts["passed"] / b_total, 4),
                "leakage_rate": round(counts["leaked"] / b_total, 4),
            }

        return Cohort2Report(
            total_cases=total,
            refused_count=refused_count,
            passed_count=passed_count,
            refusal_accuracy=round(refused_count / divisor, 4),
            llm_bypass_rate=round(llm_bypass_count / divisor, 4),
            leakage_count=leakage_count,
            leakage_rate=round(leakage_count / divisor, 4),
            breakdown_by_attack_type=breakdown,
            case_results=case_results,
        )

    async def evaluate_all(
        self,
        answerable_items: list[AnswerableGoldenItem] | None = None,
        adversarial_items: list[AdversarialRefusalItem] | None = None,
    ) -> TwoCohortEvaluationReport:
        """Execute both Cohort 1 and Cohort 2 evaluations and return a combined report."""
        start = time.perf_counter()
        cohort1_report, _ = await self.evaluate_answerable_cohort(items=answerable_items)
        cohort2_report = await self.evaluate_adversarial_cohort(items=adversarial_items)
        total_duration_ms = round((time.perf_counter() - start) * 1000.0, 2)

        return TwoCohortEvaluationReport(
            cohort1=cohort1_report,
            cohort2=cohort2_report,
            total_duration_ms=total_duration_ms,
            run_config={
                "max_workers": int(self.run_config.max_workers),
                "max_retries": int(self.run_config.max_retries),
                "timeout": int(self.run_config.timeout),
            },
        )
