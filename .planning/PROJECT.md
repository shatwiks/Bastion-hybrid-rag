# Enterprise Multi-Tenant RAG Knowledge Engine

## What This Is

A production-grade, multi-tenant Retrieval-Augmented Generation (RAG) system built for internal support and enterprise knowledge management. It combines an Async FastAPI backend, PostgreSQL (`pgvector` + lexical BM25/FTS) with a Qdrant-ready retriever abstraction, Redis semantic caching, local HuggingFace embeddings and Cross-Encoder reranking, and an interactive Next.js chat, admin ingestion, and live telemetry inspector UI. It solves the four primary failure modes of enterprise AI: cross-tenant/role data leaks, poor retrieval accuracy on technical jargon and error codes, high latency/token costs, and LLM hallucinations.

## Core Value

Guaranteed pre-retrieval multi-tenant RBAC isolation paired with deterministic, zero-hallucination grounded answers (or explicit refusal when confidence is below threshold).

## Requirements

### Validated

(None yet — ship to validate)

### Active

- [ ] **OAuth 2.0 / JWT Authentication & Pre-Retrieval RBAC Isolation**: Validate JWT claims (`tenant_id`, `allowed_roles`) in Async FastAPI and enforce strict SQL/vector `WHERE` filtering inside PostgreSQL (`pgvector`) during search so unauthorized chunks are mathematically invisible.
- [ ] **Pluggable Retriever Architecture**: Implement PostgreSQL (`pgvector` + full-text/BM25 lexical search) as the unified primary store behind a clean `VectorStoreRetriever` interface with a Qdrant-ready adapter.
- [ ] **Structure-Aware Document Ingestion Pipeline**: Chunk documents by Markdown headers, paragraphs, tables, and structural boundaries while attaching tenant and role ACL metadata.
- [ ] **Query Rewriting & Multi-Stage Hybrid Retrieval**: Rewrite conversational/follow-up queries into standalone search queries, execute parallel dense vector search and lexical BM25 keyword search (handling exact error codes like `ERR_409_CONFLICT`, SKUs, and symbols), and fuse top candidate chunks (~20–25).
- [ ] **Local Cross-Encoder Reranking & Deterministic Refusal Gate**: Score candidate chunks simultaneously using a local HuggingFace Cross-Encoder reranker; short-circuit and return a deterministic refusal message without calling the LLM if the top chunk confidence falls below threshold (e.g., `< 0.65`).
- [ ] **Permission-Scoped Redis Semantic & Response Caching**: Embed incoming queries and check Redis for mathematically similar questions scoped to the same `tenant_id` and `allowed_roles`, returning hits in ~20ms.
- [ ] **Grounded Streaming Generation with Inline Citations**: Inject top 3–5 reranked chunks into a strict system prompt requiring factual grounding and inline `[chunk_id]` citations, streamed to the client.
- [ ] **Langfuse Production Observability & Ragas CI Evaluation Suite**: Trace all 6 lifecycle steps asynchronously to Langfuse (latency, token usage, cache hit/miss, reranker scores) and provide a reproducible Ragas + LLM-as-a-Judge evaluation suite with a golden dataset benchmarking retrieval precision (target ~88%), MRR improvement (+26%), and hallucination reduction (82%).
- [ ] **Interactive Next.js Demo, Inspector & Admin UI**: Provide a Next.js frontend featuring grounded streaming chat with source citations, a live Tenant/Role switcher (`tenant_id`, `support_tier_1`, `executive`, `public`), a real-time 6-step Pipeline Telemetry Inspector drawer, an Admin document ingestion interface, and pre-seeded multi-tenant enterprise documentation.

### Out of Scope

- **Unfiltered Post-Retrieval RBAC**: Filtering chunks in Python after retrieving top-K from the database — causes zero-result starvation for lower-privilege roles and risks application-layer data leaks.
- **Unbounded Open-Domain Chat**: Allowing the LLM to answer from general pre-training knowledge when internal docs lack coverage — creates legal and support liabilities.
- **Heavy Multi-Node Distributed Cluster Setup Required for Local Dev**: The full stack (Postgres `pgvector`, Redis, FastAPI, Next.js, optional Qdrant/Langfuse) must be runnable locally via Docker Compose.

## Context

- **The 6-Step Request Lifecycle**:
  1. **Auth & Guardrail**: Next.js sends query + JWT to Async FastAPI, which validates `tenant_id` and `allowed_roles`.
  2. **Semantic Cache Check**: Query is embedded and checked against Redis (scoped to `tenant_id` + `allowed_roles`); cache hits return immediately (~20ms).
  3. **Hybrid Retrieval**: Cache misses trigger query rewriting and parallel dense vector + BM25 lexical search against PostgreSQL (`pgvector`), strictly filtered by RBAC metadata in the `WHERE` clause.
  4. **Reranking & Confidence Gate**: Top ~20–25 candidate chunks are scored by a local HuggingFace Cross-Encoder; if max score `< 0.65` (configurable threshold), the deterministic Refusal Gate short-circuits LLM generation.
  5. **Grounded Generation**: High-confidence top 3–5 chunks are injected into a strict system prompt instructing the LLM to answer only from context and cite chunk IDs.
  6. **Telemetry & Cache Write**: Response streams back to the user, writes to Redis semantic cache, and logs the full trace asynchronously to Langfuse.
- **Target Benchmark Metrics**:
  - **88% retrieval precision** from structure-aware chunking + hybrid retrieval + cross-encoder reranking.
  - **+26% Mean Reciprocal Rank (MRR)** improvement over naive dense-only vector search.
  - **82% reduction in hallucinations** driven by the deterministic confidence refusal gate and strict citation prompting.

## Constraints

- **Backend Stack**: Python Async FastAPI, SQLAlchemy/asyncpg, PostgreSQL with `pgvector` + lexical search (BM25/FTS), Redis for semantic caching.
- **Model Stack**: Configurable Cloud LLM provider (OpenAI / Gemini / Anthropic via environment variables) for query rewriting and grounded generation + local HuggingFace models (`sentence-transformers`) for dense embeddings and Cross-Encoder reranking.
- **Frontend Stack**: Next.js (App Router, TypeScript, Tailwind CSS) with interactive demo/inspector controls and admin document management.
- **Observability & Evaluation**: Langfuse SDK for asynchronous request tracing; Ragas framework for CI evaluation against a golden dataset.
- **Security**: Multi-tenant and role-based filtering must always execute inside the database query (`WHERE` clause) prior to similarity ranking and semantic cache lookup.

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| PostgreSQL (`pgvector` + BM25/FTS) primary with clean `Retriever` interface (Qdrant-ready adapter) | Keeps relational metadata, RBAC ACLs, dense vectors, and lexical search unified in one transactional store while supporting Qdrant swap-in as discussed in interviews | — Pending |
| Cloud LLM (OpenAI/Gemini/Anthropic via env config) + local HuggingFace embeddings & Cross-Encoder | Fast, zero-per-token-cost local embeddings and cross-encoder reranking over 25 chunks, paired with high-capability cloud LLMs for generation and Ragas judging | — Pending |
| Pre-retrieval SQL `WHERE` clause RBAC + permission-scoped Redis cache keys | Prevents unauthorized data exposure and eliminates top-K starvation when admin documents dominate similarity rankings | — Pending |
| Deterministic Refusal Gate before LLM call (`score < threshold`) | Eliminates LLM guessing on unsupported topics and saves LLM token cost and latency | — Pending |
| Interactive Next.js Demo & Inspector UI with pre-seeded multi-tenant dataset | Makes the 6-step architecture, RBAC isolation, cache hits, hybrid retrieval, and refusal gate immediately demonstrable in live interviews | — Pending |

## Evolution

This document evolves at phase transitions and milestone boundaries.

**After each phase transition** (via `/gsd-transition`):
1. Requirements invalidated? → Move to Out of Scope with reason
2. Requirements validated? → Move to Validated with phase reference
3. New requirements emerged? → Add to Active
4. Decisions to log? → Add to Key Decisions
5. "What This Is" still accurate? → Update if drifted

**After each milestone** (via `/gsd-complete-milestone`):
1. Full review of all sections
2. Core Value check — still the right priority?
3. Audit Out of Scope — reasons still valid?
4. Update Context with current state

---
*Last updated: 2026-11-10 after initialization*
