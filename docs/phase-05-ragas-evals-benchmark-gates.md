# Phase 5: Two-Cohort Ragas Evaluation & Comparative Baseline-vs-Enterprise Benchmark Suite

> **Core Problem Solved:** Claiming "high retrieval precision" or "hallucination reduction" without reproducible measurements is guesswork. Phase 5 builds a golden evaluation suite spanning normal Q&A, technical jargon (`ERR_*`, `SKU-*`, `--*`), and adversarial RBAC/refusal traps—comparing a naive dense-only baseline directly against our full 6-step enterprise pipeline and failing CI if any metric regresses.

---

## 1. Commits & File Inventory

| Commit | Scope | Files Added / Modified | Purpose |
| :--- | :--- | :--- | :--- |
| `b3e786f` | Two-Cohort Golden Datasets & Ragas Runner | Added `evals/datasets/answerable_golden.json`, `evals/datasets/adversarial_refusal.json`, `backend/app/evals/__init__.py`, `backend/app/evals/ragas_runner.py`, `backend/tests/integration/test_eval_cohorts.py` | 17 answerable multi-tenant items + 14 adversarial traps + `RagasCohortEvaluator` |
| `4823399` & `6211a7c` | Comparative Benchmark & CI Regression Gates | Added `backend/app/evals/benchmark_suite.py`, `backend/tests/integration/test_benchmark_gates.py`, `evals/reports/latest_benchmark.json`; modified `backend/app/evals/__init__.py` | Naive dense baseline vs full pipeline runner (`_DENSE_BASELINE_SQL`), 11 technical jargon probes, 4 strict numeric CI gates |
| `9c27803` | Test Isolation & Report Refresh | Updated `backend/tests/integration/test_benchmark_gates.py` (`tmp_path`) & refreshed `evals/reports/latest_benchmark.json` | Prevented tests from mutating tracked JSON files while verifying the full benchmark snapshot |

---

## 2. Two-Cohort Golden Datasets

### Cohort 1: [`evals/datasets/answerable_golden.json`](../evals/datasets/answerable_golden.json) (17 Cases)
Tests positive retrieval precision, ranking quality (MRR), keyword recall, and inline `[chunk_id]` citation faithfulness across tenants (`acme_corp`, `globex_corp`), roles (`public`, `support_tier_1`, `executive`), technical identifiers (`ERR_*`, `SKU-*`, CLI flags), and natural language runbook questions.

### Cohort 2: [`evals/datasets/adversarial_refusal.json`](../evals/datasets/adversarial_refusal.json) (14 Cases)
Evaluates security and refusal behavior across 4 distinct adversarial attack vectors:
- `out_of_domain` (unrelated questions outside enterprise docs)
- `unanswerable_internal_gap` (plausible internal topics intentionally absent from the docs)
- `rbac_privilege_escalation` (e.g., `public` or `support_tier_1` user asking about confidential `executive` M&A/financial targets)
- `cross_tenant_isolation` (e.g., `acme_corp` executive asking about `globex_corp` firewall codes/acquisitions, and vice versa)

Every Cohort 2 item specifies `forbidden_terms`—if even a single forbidden substring leaks into retrieved chunks or answers, RBAC leakage (`rbac_leakage_rate`) becomes non-zero and fails the gate immediately.

---

## 3. Ragas v0.4 + Deterministic Hybrid Evaluator ([`backend/app/evals/ragas_runner.py`](../backend/app/evals/ragas_runner.py))

`RagasCohortEvaluator` executes queries through the full `RAGPipelineOrchestrator.stream_lifecycle` with `bypass_cache=True` (so every evaluation item genuinely exercises retrieval, reranking, and gating cleanly):

- **Cohort 1 Metrics:**
  - `precision_at_k` (chunk-to-expected-document precision)
  - `mrr` (Mean Reciprocal Rank: `1 / rank_of_first_relevant_chunk`)
  - `keyword_recall` (`_compute_keyword_recall` against expected terms)
  - `citation_faithfulness` (`_compute_citation_faithfulness`: validates every inline `[chunk_id]` against `retrieved_chunk_ids` and penalizes invented IDs)
  - **Optional Ragas LLM-as-a-Judge:** When an LLM API key is configured, runs throttled `SingleTurnSample` + `EvaluationDataset` scoring (`RunConfig(max_workers=2, max_retries=5, timeout=60)`) using Ragas v0.4 metrics (`ContextPrecision`, `ContextRecall`, `Faithfulness`, `AnswerRelevancy`).
- **Cohort 2 Metrics:**
  - `refusal_accuracy`: Fraction of adversarial items cleanly refused via the Refusal Gate.
  - `llm_bypass_rate`: Confirms `llm_called == False` on refused queries (zero wasted LLM tokens, zero hallucination surface).
  - `rbac_leakage_rate`: Scans every response and retrieved context against `forbidden_terms` (`0.0` required).

---

## 4. Comparative Benchmark: Naive Dense Baseline vs Enterprise 6-Step Pipeline ([`backend/app/evals/benchmark_suite.py`](../backend/app/evals/benchmark_suite.py))

To prove the value of hybrid RRF + token expansion + Cross-Encoder reranking + Refusal Gate quantitatively, `ComparativeBenchmarkRunner` evaluates **the exact same 28 retrieval queries** (17 Cohort 1 golden + 11 `DEFAULT_TECHNICAL_JARGON_PROBES`) and **14 Cohort 2 adversarial traps** on two systems side-by-side:

1. **Naive Baseline (`_DENSE_BASELINE_SQL`):**
   - Performs raw dense-vector cosine similarity search (`ORDER BY embedding <=> :query_vec LIMIT :top_k`) filtered by tenant/role, with **no** BM25/FTS lexical fusion, **no** Cross-Encoder reranking, and **no** `< 0.65` Refusal Gate (any top candidate passes to un-gated answer generation).
2. **Enterprise 6-Step System:**
   - Full [`RAGPipelineOrchestrator`](../backend/app/services/rag_pipeline.py) (`HYBRID_RRF_SQL` + technical token expansion + `Sigmoid`-calibrated Cross-Encoder reranking + `< 0.65` deterministic refusal gate + grounded `[chunk_id]` generation).

### Measured Benchmark Snapshot ([`evals/reports/latest_benchmark.json`](../evals/reports/latest_benchmark.json))

Every metric below is directly recorded in `evals/reports/latest_benchmark.json` and enforced by [`test_benchmark_gates.py`](../backend/tests/integration/test_benchmark_gates.py):

| Metric | Naive Dense Baseline | Enterprise 6-Step Engine | CI Gate / Result |
| :--- | :---: | :---: | :--- |
| **Retrieval Precision** (28 probes) | `0.8143` (81.43%) | **`1.0000` (100.0%)** | Gate `>= 0.88` -> **PASS** |
| **Mean Reciprocal Rank (MRR)** | `0.7542` | **`1.0000`** | **+32.59% lift** (Gate `>= +20%`) -> **PASS** |
| **Ungrounded / Hallucination Rate on Traps** | `1.0000` (100% answered ungrounded) | **`0.0000` (0% hallucinated)** | **100.0% reduction** (Gate `>= 75%`) -> **PASS** |
| **RBAC / Cross-Tenant Leakage Rate** | `0.0000` | **`0.0000`** | Gate `== 0.0` -> **PASS** |

---

## 5. How Phase 5 Was Verified
- [`backend/tests/integration/test_eval_cohorts.py`](../backend/tests/integration/test_eval_cohorts.py): Verified both Cohort 1 (17 answerable items) and Cohort 2 (14 adversarial refusal/RBAC items) load cleanly and pass all precision, citation faithfulness, refusal accuracy, and zero-leakage checks.
- [`backend/tests/integration/test_benchmark_gates.py`](../backend/tests/integration/test_benchmark_gates.py): Runs `ComparativeBenchmarkRunner` in-process and asserts all 4 numerical regression gates (`enterprise_precision >= 0.88`, `mrr_lift_pct >= 20.0`, `hallucination_reduction_pct >= 75.0`, `rbac_leakage_rate == 0.0`), writing ephemeral test reports to `tmp_path`.
