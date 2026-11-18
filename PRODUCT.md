# Product

<!-- impeccable:product-schema 1 -->

## Platform

web

## Users

- **Primary (Dual-Purpose):** Internal support engineers, platform engineers, and technical evaluators / recruiters reviewing Bastion Hybrid RAG live.
- **Secondary:** Knowledge administrators uploading and managing tenant-scoped Markdown runbooks.

## Product Purpose

Bastion Hybrid RAG is an enterprise multi-tenant Hybrid Retrieval-Augmented Generation workspace that lets authenticated users query technical knowledge bases with verifiable inline source citations while letting operators and evaluators inspect every security, retrieval, reranking, caching, and refusal decision live.

## Positioning

Unlike standard RAG demos that run global vector search and filter permissions afterward in application code, Bastion enforces pre-retrieval multi-tenant RBAC inside PostgreSQL `WHERE` clauses (`tenant_id` + `allowed_roles &&` with `hnsw.iterative_scan`), fuses dense embeddings with dual-dictionary BM25/FTS via Reciprocal Rank Fusion, calibrates a local Sigmoid Cross-Encoder to deterministically short-circuit below `0.65` with zero LLM tokens spent, and scopes Redis semantic cache entries by `tenant_id`, `scope_hash`, and technical entity fingerprints.

## Operating Context

- **Scene:** Bright daytime workspace with a somewhat light, distinctive color atmosphere (explicitly avoiding generic dark-neon AI themes and sterile plain-white defaults).
- **Workflow:** Chat and verified source citations lead the workspace; the collapsible 6-Step Pipeline Telemetry Inspector sits beside the thread so evaluators and engineers can inspect latencies, cache hits/misses, query rewrites, the `0.65` confidence meter, and candidate ranks in real time.
- **Session Rhythm:** Starter scenario prompts appear cleanly in the empty state and collapse out of the way once a conversation begins so the thread owns the viewport.
- **Personas & Tenants:** Live switching across `acme_corp` and `globex_corp` and roles `public`, `support_tier_1`, and `executive`, with one-click `"Re-run Last Query Under New Role"` to prove zero-leak isolation.

## Capabilities and Constraints

- **Must Preserve:** All live FastAPI integrations (`GET /api/v1/health`, `POST /api/v1/auth/demo-token`, `POST /api/v1/chat/stream` SSE multiplexing across `step_update`/`token`/`citations`/`refusal`/`done`, `POST /api/v1/ingest`, `GET /api/v1/documents`).
- **Must Preserve:** Clickable inline `[chunk_id]` citation badges opening source inspection (`document_title`, `section_header`, `allowed_roles`, Cross-Encoder %, Dense/BM25/RRF scores, escaped chunk text), deterministic Refusal Alert notice (`LLM Called: FALSE`), `bypass_cache` toggle, HTTP 403 RBAC check on Admin Ingestion for `public` personas, and strict tenant/scope-isolated `chat_history`.
- **Security Constraint:** Zero `dangerouslySetInnerHTML`; all chunk/markdown text rendered safely.
- **Responsive Constraint:** Full usability at desktop (`1440×900`) and mobile (`390×844`) with zero horizontal overflow.

## Brand Commitments

- **Product Name:** Bastion Hybrid RAG (Enterprise Multi-Tenant Knowledge Engine).
- **User Preference:** Somewhat light ground with unique, cohesive colors — explicitly rejecting generic dark-indigo/violet AI slop.

## Evidence on Hand

- Live backend on `http://127.0.0.1:8000` (PostgreSQL 17 `pgvector`, Redis 8, local HuggingFace `BAAI/bge-small-en-v1.5` & `cross-encoder/ms-marco-MiniLM-L6-v2`).
- Measured benchmark artifact at `evals/reports/latest_benchmark.json` (100% precision, +32.59% MRR lift, 100% refusal-trap blocking, 0% RBAC leakage across 28 retrieval + 14 adversarial probes).
- Seed corpus in `seed/` across `acme_corp` and `globex_corp`.

## Product Principles

1. **Evidence over ornament:** Every visual indicator maps to a real pipeline state, score, or security scope — zero decorative badges or fake telemetry.
2. **Task-first clarity:** Chat reading and source verification lead; starter scenarios and deep candidate funnels reveal progressively when needed.
3. **Unmistakable security state:** Active tenant, role tier, and refusal/cache outcomes are legible in one glance without visual noise.
4. **Earned familiarity:** Standard, crisp web controls with consistent shapes, spacing, and keyboard focus rather than invented UI gimmicks.
