"""Comparative CI Benchmark Gate Tests (Naive Dense Baseline vs. Enterprise Hybrid RAG)."""

from __future__ import annotations

import pytest

from app.db.session import async_engine, async_session_maker
from app.evals.benchmark_suite import (
    ComparativeBenchmarkReport,
    ComparativeBenchmarkRunner,
    compute_hallucination_reduction_pct,
    compute_mrr_lift_pct,
    default_benchmark_report_path,
)
from app.redis_client import close_redis_pool
from app.scripts.seed_corpus import run_seed
from app.services.embeddings import get_embedding_service
from app.services.reranker import get_reranker_service


@pytest.fixture(scope="module")
def warmed_models():
    """Warm up local embedding and Cross-Encoder singletons once for the test module."""
    emb = get_embedding_service()
    if not emb.is_warmed_up:
        emb.warmup()
    reranker = get_reranker_service()
    if not reranker.is_warmed_up:
        reranker.warmup()
    return emb, reranker


@pytest.fixture
async def db_session():
    """Seed multi-tenant corpus idempotently and guarantee clean async teardown."""
    await run_seed()
    try:
        async with async_session_maker() as session:
            yield session
    finally:
        await close_redis_pool()
        await async_engine.dispose()


def test_benchmark_lift_and_reduction_formulas() -> None:
    """Verify deterministic relative percentage helpers used by the CI benchmark gate."""
    assert compute_mrr_lift_pct(baseline_mrr=0.75, enterprise_mrr=0.96) == 28.0
    assert compute_mrr_lift_pct(baseline_mrr=0.0, enterprise_mrr=0.9) == 0.0
    assert compute_hallucination_reduction_pct(1.0, 0.0) == 100.0
    assert compute_hallucination_reduction_pct(0.85, 0.15) == 82.35
    assert compute_hallucination_reduction_pct(0.0, 0.0) == 0.0


async def test_comparative_benchmark_ci_gates(warmed_models, db_session, tmp_path) -> None:
    """Run live Baseline vs. Enterprise comparison and enforce all 4 production CI gates."""
    emb, reranker = warmed_models
    report_path = tmp_path / "latest_benchmark.json"
    runner = ComparativeBenchmarkRunner(
        session=db_session,
        embedding_service=emb,
        reranker_service=reranker,
    )

    report = await runner.run_benchmark(write_report_path=report_path)

    # Gate 1: >= 85% retrieval precision across in-scope NL + technical jargon queries
    assert report.enterprise_precision >= 0.85, (
        f"Enterprise retrieval precision {report.enterprise_precision} < 0.85"
    )
    # Gate 2: >= +26% MRR lift over Naive Dense-Only baseline
    assert report.mrr_lift_pct >= 26.0, (
        f"MRR lift {report.mrr_lift_pct}% < 26.0% "
        f"(baseline={report.baseline_mrr}, enterprise={report.enterprise_mrr})"
    )
    # Gate 3: >= 82% hallucination reduction on adversarial & out-of-domain queries
    assert report.hallucination_reduction_pct >= 82.0, (
        f"Hallucination reduction {report.hallucination_reduction_pct}% < 82.0% "
        f"(baseline_ungrounded={report.baseline_ungrounded_rate}, "
        f"enterprise_ungrounded={report.enterprise_ungrounded_rate})"
    )
    # Gate 4: Strictly 0.0% cross-tenant / cross-role RBAC leakage
    assert report.rbac_leakage_rate == 0.0, (
        f"RBAC leakage rate must be 0.0, got {report.rbac_leakage_rate}"
    )

    assert report.all_gates_passed is True
    assert report.gates_passed == {
        "enterprise_precision": True,
        "mrr_lift_pct": True,
        "hallucination_reduction_pct": True,
        "rbac_leakage_rate": True,
    }
    assert report_path.is_file()

    persisted = ComparativeBenchmarkReport.model_validate_json(
        report_path.read_text(encoding="utf-8")
    )
    assert persisted.enterprise_precision == report.enterprise_precision
    assert persisted.mrr_lift_pct == report.mrr_lift_pct
    assert persisted.hallucination_reduction_pct == report.hallucination_reduction_pct

    # Also verify the tracked evals/reports/latest_benchmark.json artifact validates cleanly
    tracked_report_path = default_benchmark_report_path()
    assert tracked_report_path.is_file()
    tracked_persisted = ComparativeBenchmarkReport.model_validate_json(
        tracked_report_path.read_text(encoding="utf-8")
    )
    assert tracked_persisted.all_gates_passed is True
    assert persisted.rbac_leakage_rate == 0.0
