from collections.abc import AsyncGenerator
from unittest.mock import MagicMock, patch

import pytest
from ragas import EvaluationDataset, SingleTurnSample
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import async_engine, async_session_maker
from app.evals import (
    RagasCohortEvaluator,
    load_adversarial_dataset,
    load_answerable_dataset,
)
from app.evals.ragas_runner import PipelineExecutionOutcome
from app.redis_client import close_redis_pool
from app.scripts.seed_corpus import run_seed
from app.services.embeddings import get_embedding_service
from app.services.reranker import get_reranker_service

_SEED_INITIALIZED = False


@pytest.fixture(scope="module", autouse=True)
def warmup_models_once() -> None:
    """Warm up local EmbeddingService and CrossEncoderRerankerService once per module."""
    emb = get_embedding_service()
    if not emb.is_warmed_up:
        emb.warmup()
    reranker = get_reranker_service()
    if not reranker.is_warmed_up:
        reranker.warmup()


@pytest.fixture
async def db_session() -> AsyncGenerator[AsyncSession, None]:
    """Ensure seed corpus is populated, yield AsyncSession, and dispose engine cleanly."""
    global _SEED_INITIALIZED
    if not _SEED_INITIALIZED:
        await run_seed()
        _SEED_INITIALIZED = True

    try:
        async with async_session_maker() as session:
            yield session
    finally:
        await close_redis_pool()
        await async_engine.dispose()


def test_eval_datasets_schema_and_cohort_separation() -> None:
    """Verify Cohort 1 (>=15) and Cohort 2 (>=12) schemas, tenants, personas, and tokens."""
    answerable = load_answerable_dataset()
    adversarial = load_adversarial_dataset()

    assert len(answerable) >= 15
    assert len(adversarial) >= 12

    assert {item.tenant_id for item in answerable} == {"acme_corp", "globex_corp"}
    assert {item.persona for item in answerable} == {"public", "support_tier_1", "executive"}

    all_questions = " ".join(item.question for item in answerable)
    for required_token in (
        "ERR_409_CONFLICT",
        "ERR_503_SERVICE_UNAVAILABLE",
        "ERR_401_SEC_REVOKED",
        "SKU-9921-A",
        "SKU-GLX-500",
        "--enable-read-replica",
    ):
        assert required_token in all_questions, f"Missing required technical token {required_token}"

    assert {item.attack_type for item in adversarial} == {
        "out_of_domain",
        "cross_role",
        "cross_tenant",
    }
    for item in adversarial:
        assert item.expected_refusal is True
        assert len(item.forbidden_terms) >= 1

    # Strict cohort separation: zero overlapping IDs
    assert not ({i.id for i in answerable} & {i.id for i in adversarial})


@pytest.mark.asyncio
async def test_ragas_single_turn_sample_and_throttled_run_config(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Verify SingleTurnSample/EvaluationDataset construction and RunConfig(max_workers=2, max_retries=5)."""
    items = load_answerable_dataset()[:2]

    async def _stub_runner(ctx, query: str) -> PipelineExecutionOutcome:
        return PipelineExecutionOutcome(
            query=query,
            tenant_id=ctx.tenant_id,
            allowed_roles=list(ctx.allowed_roles),
            answer_text="Acme Cloud Storage Mission-Critical tier provides 99.995% SLA [chunk-1].",
            retrieved_contexts=["Mission-Critical tier: 99.995% monthly uptime SLA, 18 ms P99."],
            retrieved_document_titles=[items[0].expected_document_title],
            retrieved_chunk_ids=["chunk-1"],
            candidate_document_titles=[items[0].expected_document_title],
            refused=False,
            llm_called=True,
            top_rerank_score=0.92,
            latency_ms=12.0,
        )

    evaluator = RagasCohortEvaluator(pipeline_runner=_stub_runner, use_llm_judge=False)
    assert evaluator.run_config.max_workers == 2
    assert evaluator.run_config.max_retries == 5
    assert evaluator.run_config.timeout == 60

    report, dataset = await evaluator.evaluate_answerable_cohort(items=items)
    assert isinstance(dataset, EvaluationDataset)
    assert len(dataset.samples) == 2
    assert all(isinstance(s, SingleTurnSample) for s in dataset.samples)
    assert dataset.samples[0].user_input == items[0].question
    assert dataset.samples[0].reference == items[0].reference_answer
    assert report.ragas_llm_judge_used is False

    # Verify LLM Judge branch uses throttled RunConfig when API key is configured
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test-judge-key")
    judge_evaluator = RagasCohortEvaluator(pipeline_runner=_stub_runner, use_llm_judge=True)
    fake_result = MagicMock()
    fake_result._repr_dict = {
        "context_precision": 0.95,
        "context_recall": 0.90,
        "faithfulness": 0.98,
        "answer_relevancy": 0.92,
    }
    with patch("app.evals.ragas_runner.evaluate", return_value=fake_result) as mock_eval:
        judge_report, _ = await judge_evaluator.evaluate_answerable_cohort(items=items)

    mock_eval.assert_called_once()
    call_kwargs = mock_eval.call_args.kwargs
    assert call_kwargs["run_config"].max_workers == 2
    assert call_kwargs["run_config"].max_retries == 5
    assert judge_report.ragas_llm_judge_used is True
    assert judge_report.ragas_scores["faithfulness"] == pytest.approx(0.98)


@pytest.mark.asyncio
async def test_live_two_cohort_evaluation_pipeline(db_session: AsyncSession) -> None:
    """Execute Cohort 1 & Cohort 2 against live PostgreSQL + Cross-Encoder pipeline."""
    evaluator = RagasCohortEvaluator(session=db_session, use_llm_judge=False)
    report = await evaluator.evaluate_all()

    # Cohort 1: Answerable In-Scope
    c1 = report.cohort1
    assert c1.total_cases >= 15
    assert c1.refused_cases == 0, (
        f"Expected 0 refusals on answerable cohort, got {c1.refused_cases}: "
        f"{[r.id for r in c1.case_results if r.refused]}"
    )
    assert c1.answered_cases == c1.total_cases
    assert c1.context_precision >= 0.85
    assert c1.mrr >= 0.85
    assert c1.context_recall >= 0.80
    assert c1.citation_faithfulness >= 0.95
    assert c1.answer_relevancy >= 0.65
    for case in c1.case_results:
        assert "Search Index Tokens:" not in case.answer_text

    # Cohort 2: Adversarial Refusal & RBAC Isolation
    c2 = report.cohort2
    assert c2.total_cases >= 12
    assert c2.refusal_accuracy == 1.0, (
        f"Expected 100% refusal on adversarial cohort, failed: "
        f"{[(r.id, r.top_rerank_score) for r in c2.case_results if not r.refused]}"
    )
    assert c2.llm_bypass_rate == 1.0
    assert c2.leakage_count == 0
    assert c2.leakage_rate == 0.0
    assert c2.passed_count == c2.total_cases
