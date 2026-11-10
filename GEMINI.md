<!-- GSD:project-start source:PROJECT.md -->

## Project

**Enterprise Multi-Tenant RAG Knowledge Engine**

A production-grade, multi-tenant Retrieval-Augmented Generation (RAG) system built for internal support and enterprise knowledge management. It combines an Async FastAPI backend, PostgreSQL (`pgvector` + lexical BM25/FTS) with a Qdrant-ready retriever abstraction, Redis semantic caching, local HuggingFace embeddings and Cross-Encoder reranking, and an interactive Next.js chat, admin ingestion, and live telemetry inspector UI. It solves the four primary failure modes of enterprise AI: cross-tenant/role data leaks, poor retrieval accuracy on technical jargon and error codes, high latency/token costs, and LLM hallucinations.

**Core Value:** Guaranteed pre-retrieval multi-tenant RBAC isolation paired with deterministic, zero-hallucination grounded answers (or explicit refusal when confidence is below threshold).

### Constraints

- **Backend Stack**: Python Async FastAPI, SQLAlchemy/asyncpg, PostgreSQL with `pgvector` + lexical search (BM25/FTS), Redis for semantic caching.
- **Model Stack**: Configurable Cloud LLM provider (OpenAI / Gemini / Anthropic via environment variables) for query rewriting and grounded generation + local HuggingFace models (`sentence-transformers`) for dense embeddings and Cross-Encoder reranking.
- **Frontend Stack**: Next.js (App Router, TypeScript, Tailwind CSS) with interactive demo/inspector controls and admin document management.
- **Observability & Evaluation**: Langfuse SDK for asynchronous request tracing; Ragas framework for CI evaluation against a golden dataset.
- **Security**: Multi-tenant and role-based filtering must always execute inside the database query (`WHERE` clause) prior to similarity ranking and semantic cache lookup.

<!-- GSD:project-end -->

<!-- GSD:stack-start source:research/STACK.md -->

## Technology Stack

## Recommended Stack

### Core Technologies (Backend, Data Store & AI Pipeline)

| Technology | Version | Purpose | Why Recommended | Confidence |
|------------|---------|---------|-----------------|------------|
| **Python** | `3.12+` (`3.13` compatible) | Backend runtime | Optimal compatibility across PyTorch (`torch`), `sentence-transformers`, `asyncpg` C-extensions, and `ragas` evaluation dependencies. | HIGH |
| **FastAPI** | `0.162.3` | Async API & SSE streaming server | First-class `asyncio` support, dependency injection (`Depends`) for pre-retrieval JWT RBAC extraction, native `StreamingResponse` for Server-Sent Events (SSE), and automatic OpenAPI schema generation. | HIGH |
| **Uvicorn** | `0.54.0` | ASGI server (`uvicorn[standard]`) | High-throughput `uvloop` + `httptools` event loop required so concurrent SSE streams and async database/Redis I/O never block worker threads. | HIGH |
| **PostgreSQL + `pgvector`** | Postgres `17` + `pgvector 0.8+` (`pgvector/pgvector:pg17`) | Unified transactional relational, dense vector, and lexical FTS/BM25 store | Eliminates dual-write consistency bugs between a relational ACL database and an external vector store. Supports HNSW vector indexes (`vector_cosine_ops` / `halfvec_cosine_ops`), native `tsvector` + GIN indexes (`ts_rank_cd`) with `simple`/`english` configurations for exact error codes (`ERR_409_CONFLICT`), and strict SQL `WHERE` clause pre-filtering (`tenant_id = $1 AND allowed_roles && $2`). | HIGH |
| **SQLAlchemy (Async) + `asyncpg` + `pgvector`** | `sqlalchemy==2.1.8`, `asyncpg==0.32.0`, `pgvector==0.5.1` | Async ORM, connection pooling, and vector codec binding | SQLAlchemy 2.x `AsyncSession` paired with `asyncpg` delivers the highest async Postgres throughput in Python. `pgvector.sqlalchemy.Vector` and `pgvector.asyncpg.register_vector` enable native SQL expressions for cosine distance (`<=>`), HNSW index DDL, and single-roundtrip Reciprocal Rank Fusion (RRF) CTE queries. | HIGH |
| **Redis 8 + `redisvl` + `redis-py`** | Redis `8.x` (`redis:8-alpine`), `redis==8.1.0`, `redisvl==0.31.0` | Permission-scoped semantic cache & response cache | Redis 8 natively embeds the RediSearch vector query engine without separate module containers. `redisvl.extensions.cache.llm.SemanticCache` supports `filterable_fields` (`Tag("tenant_id")` and `Tag("roles_Scope")`), guaranteeing that semantic cache hits (~20ms) are mathematically scoped to identical tenant and role entitlements. | HIGH |
| **Sentence Transformers (`sentence-transformers`)** | `6.2.0` (`torch==2.15.0`) | Local dense embeddings & Cross-Encoder reranking | Industry-standard local inference library for bi-encoder embeddings and cross-encoder reranking (`CrossEncoder.rank()`). Zero per-token API cost and ~40–90ms local batch scoring over 25 candidate chunks. **Recommended models:** `BAAI/bge-small-en-v1.5` (384-dim, fast CPU/GPU) or `BAAI/bge-m3` (1024-dim, 8k context) for embeddings; `BAAI/bge-reranker-base` (superior enterprise NDCG/MRR) or `cross-encoder/ms-marco-MiniLM-L6-v2` (ultra-low-latency CPU fallback) for reranking and deterministic confidence gating (`score < 0.65`). | HIGH |
| **LiteLLM + OpenAI SDK** | `litellm==1.108.4`, `openai==3.49.0` | Cloud LLM provider abstraction (OpenAI / Gemini / Anthropic) | Satisfies the configurable Cloud LLM constraint (`LLM_MODEL=gpt-4o-mini`, `gemini/gemini-2.5-flash`, `claude-3-7-sonnet`) behind a single OpenAI-compatible async streaming interface with native Langfuse callback/OpenTelemetry support. | HIGH |
| **Qdrant Client (`qdrant-client`)** | `1.20.0` | Secondary pluggable `VectorStoreRetriever` adapter | Provides `AsyncQdrantClient` with single-stage `query_points(prefetch=[...], query=FusionQuery(fusion=Fusion.RRF), query_filter=Filter(...))` so the `Retriever` interface has a verified, production-ready Qdrant adapter alongside the primary PostgreSQL adapter. | HIGH |

### Core Technologies (Observability, Evaluation & Frontend)

| Technology | Version | Purpose | Why Recommended | Confidence |
|------------|---------|---------|-----------------|------------|
| **Langfuse Python SDK** | `5.2.0` | Production RAG observability & async trace telemetry | OpenTelemetry-backed `@observe(as_type="retriever" \| "generation" \| "guardrail" \| "span")` decorator natively wraps `async def` functions, async generators, and Starlette `StreamingResponse` without blocking the request path. Captures per-step latencies, token costs, cache hit/miss status, and Cross-Encoder confidence scores. | HIGH |
| **Ragas** | `0.4.3` | CI RAG evaluation & LLM-as-a-Judge benchmarking | Standard RAG evaluation framework using `SingleTurnSample` and `EvaluationDataset` with `ContextPrecision`, `ContextRecall`, `Faithfulness`, and `AnswerRelevancy` (`metric.ascore()`). Directly measures the target benchmarks (88% retrieval precision, +26% MRR, 82% hallucination reduction). | HIGH |
| **Next.js (App Router)** | `16.4.6` (`react==19.3.1`, `typescript==7.0.2`) | Interactive Chat, Live Telemetry Inspector & Admin UI | App Router and Web Streams API natively handle multi-event SSE streams (streaming both `[chunk_id]` grounded answer tokens and real-time 6-step pipeline telemetry payloads to the Inspector drawer). | HIGH |
| **Tailwind CSS + Lucide React** | `tailwindcss==4.3.5`, `lucide-react==1.71.0` | Styling & enterprise UI iconography | Zero-runtime CSS v4 engine and crisp technical iconography for building the split-pane chat + live 6-step Pipeline Telemetry Inspector drawer, role/tenant switcher badges, and citation cards. | HIGH |

### Supporting Libraries

| Library | Version | Purpose | When to Use | Confidence |
|---------|---------|---------|-------------|------------|
| **Pydantic & Pydantic Settings** | `pydantic==2.14.3`, `pydantic-settings==2.16.2` | Schema validation & typed env configuration | Always — validates JWT claims, 6-step telemetry trace payloads, chunk metadata schemas, refusal threshold (`REFUSAL_THRESHOLD=0.65`), and LLM provider keys. | HIGH |
| **PyJWT (`PyJWT[crypto]`)** | `2.15.1` | OAuth 2.0 / JWT decoding & signature verification | Always — validates incoming Bearer tokens and extracts `tenant_id` and `allowed_roles` inside FastAPI security dependencies before any cache or DB call executes. | HIGH |
| **LangChain Text Splitters (`langchain-text-splitters`)** | `1.1.3` | Structure-aware Markdown & recursive chunking | During document ingestion — use `MarkdownHeaderTextSplitter` + `RecursiveCharacterTextSplitter` as a lightweight standalone package (without pulling in the heavy LangChain runtime) to preserve headers, code blocks, and tables with ACL metadata. | HIGH |
| **Alembic** | `1.20.1` | Database schema & index migrations | Always — manages `CREATE EXTENSION IF NOT EXISTS vector`, `chunks` table DDL, `GIN` indexes on `tsvector` and `allowed_roles`, and `HNSW` indexes on `embedding`. | HIGH |
| **Vercel AI SDK (`ai` + `@ai-sdk/react`)** | `ai==7.0.166`, `@ai-sdk/react==4.0.170` | Frontend chat stream state & custom data parts | In the Next.js chat UI — simplifies streaming text + custom data annotations (6-step telemetry states, chunk citations, refusal notices) over SSE. | MEDIUM |
| **HTTPX** | `0.28.1` | Async HTTP client & FastAPI `AsyncClient` test harness | In backend tests and health checks — drives `pytest-asyncio` integration tests against the FastAPI ASGI app. | HIGH |

### Development Tools

| Tool | Version | Purpose | Notes |
|------|---------|---------|-------|
| **uv** | `0.7+` | Python package & virtualenv manager | 10–50x faster than `pip`/`poetry` for resolving `torch` + `sentence-transformers` + `ragas`; configure CPU-only PyTorch index in `pyproject.toml` for slim Docker builds when GPU is absent. |
| **Ruff** | `0.17.4` | Python linter & formatter | Replaces Flake8, Black, and isort in a single Rust binary (`ruff check` + `ruff format`). |
| **Pytest + Pytest-Asyncio** | `pytest==9.2.0`, `pytest-asyncio==1.4.1.post1` | Async unit, RBAC isolation & CI Ragas test runner | Set `asyncio_mode = "auto"` in `pyproject.toml`. Run cross-tenant RBAC isolation tests and Ragas threshold gates in CI. |
| **Docker Compose** | `v2.30+` | Local multi-container orchestration | Runs `postgres` (`pgvector/pgvector:pg17`), `redis` (`redis:8-alpine`), `backend` (FastAPI), `frontend` (Next.js), and optional `qdrant` / `langfuse` locally. |

## Installation

# Backend: Core runtime & API (using uv)

# Backend: Database, Vector Store & Semantic Cache

# Backend: Embeddings, Reranking, Ingestion & Cloud LLM

# Backend: Observability & Evaluation

# Backend: Dev & Testing dependencies

# Frontend: Next.js App Router, Streaming UI & Styling

## Alternatives Considered

| Recommended | Alternative | When to Use Alternative |
|-------------|-------------|-------------------------|
| **PostgreSQL (`pgvector` + native `tsvector` + RRF SQL CTE)** | **PostgreSQL + ParadeDB (`pg_search` BM25)** | Use `pg_search` when deploying self-hosted ParadeDB images where Rust/Tantivy true Okapi BM25 extensions are permitted. Stick to native `tsvector` (`english` + `simple` dict for exact error codes/SKUs) + GIN index when maximum Docker/cloud portability (`pgvector/pgvector:pg17`, RDS, Neon, Supabase) is required. |
| **PostgreSQL (`pgvector`) as Primary Retriever** | **Qdrant (`qdrant-client`) as Primary Retriever** | Use the Qdrant adapter when scaling past ~10M–50M vectors where dedicated Rust HNSW memory management, quantization, and distributed sharding outweigh single-DB transactional simplicity. Our `VectorStoreRetriever` protocol supports both. |
| **`BAAI/bge-reranker-base` (Cross-Encoder)** | **`cross-encoder/ms-marco-MiniLM-L6-v2`** | Use `ms-marco-MiniLM-L6-v2` (22M params) on constrained CPU-only laptops or CI runners where <30ms reranking latency over 25 chunks is prioritized over the higher enterprise domain accuracy of `bge-reranker-base` (278M params). Support selecting either via `RERANKER_MODEL` env var. |
| **Custom Async Pipeline + `langchain-text-splitters`** | **Full LangChain / LlamaIndex Orchestration** | Use LlamaIndex or LangChain `Runnable` chains only for rapid throwaway prototypes. For an enterprise 6-step pipeline with strict pre-retrieval RBAC, permission-scoped Redis caching, a deterministic Cross-Encoder refusal gate (`< 0.65`), and per-step telemetry streaming, explicit Python async services are far easier to audit, type-check, and debug. |
| **LiteLLM (`litellm`)** | **Provider-specific SDKs (`openai`, `google-genai`, `anthropic`)** | Use direct SDKs if locked to a single vendor. LiteLLM is preferred here because `PROJECT.md` explicitly requires switching between OpenAI, Gemini, and Anthropic via environment variables. |

## What NOT to Use

| Avoid | Why | Use Instead |
|-------|-----|-------------|
| **`python-jose` for JWT validation** | Abandoned maintenance history and known cryptographic vulnerabilities (CVE-2024-33663 / algorithm confusion attacks). | **`PyJWT[crypto]==2.15.1`** — actively maintained, strict algorithm enforcement. |
| **Synchronous DB / Redis drivers (`psycopg2-binary`, sync `redis.Redis`)** | Blocks FastAPI's single-threaded `asyncio` event loop during vector search and cache lookups, destroying concurrent SSE streaming throughput. | **`asyncpg==0.32.0`** with SQLAlchemy `AsyncSession` and **`redis.asyncio`** / async `RedisVL`. |
| **Running `SentenceTransformer.encode()` or `CrossEncoder.rank()` directly on the `asyncio` event loop** | PyTorch CPU/GPU forward passes are CPU-bound synchronous calls that freeze the FastAPI event loop for 30–100ms per request, stalling active token streams. | Offload local model inference via **`await asyncio.to_thread(...)`** (or a dedicated thread pool executor with pre-warmed singleton models). |
| **Post-Retrieval Python RBAC Filtering** | Fetching global `LIMIT 25` from `pgvector` and filtering `tenant_id` / `allowed_roles` in Python causes **Top-K starvation** (returns 0 results when another tenant's chunks dominate top-25) and risks cross-tenant data leaks. | **Pre-Retrieval SQL `WHERE` clause filtering** inside the `pgvector` and FTS CTEs (`WHERE tenant_id = :tenant_id AND allowed_roles && :user_roles`). |
| **Unscoped Semantic Cache Keys (Vector-only Redis lookup)** | Returning a cached answer based purely on cosine similarity (`distance < 0.10`) leaks restricted `executive` or another tenant's answers to `public` or `support_tier_1` users asking the same question. | **`RedisVL SemanticCache` with mandatory `Tag` filter expressions** (`(Tag("tenant_id") == tenant_id) & (Tag("roles_scope") == roles_key)`). |
| **monolithic `langchain` / `langchain-community` meta-packages** | Pulls 100+ transitive dependencies, causes frequent Pydantic/dependency version conflicts, and obscures the 6-step lifecycle behind opaque abstractions. | Standalone **`langchain-text-splitters==1.1.3`** strictly for Markdown/recursive chunking, with clean native Python classes for the 6-step pipeline. |

## Stack Patterns by Variant

- Configure `EMBEDDING_MODEL=BAAI/bge-small-en-v1.5` (384 dims) and `RERANKER_MODEL=cross-encoder/ms-marco-MiniLM-L6-v2` (with sigmoid normalization so scores map cleanly to `[0, 1]` against the `0.65` refusal threshold).
- Install CPU-only PyTorch wheels (`--index-url https://download.pytorch.org/whl/cpu`) to reduce Docker image size by ~2.5 GB.
- Configure `EMBEDDING_MODEL=BAAI/bge-m3` (or `BAAI/bge-base-en-v1.5`) and `RERANKER_MODEL=BAAI/bge-reranker-base` (with `activation_fn=torch.nn.Sigmoid()` in `CrossEncoder`) to maximize retrieval precision (88%+ target) and MRR (+26% target) on complex enterprise documentation.
- Combine PostgreSQL's `english` stemming configuration with the `simple` dictionary configuration (or `pg_trgm` / unstemmed tokens) inside the `tsvector` generated column (`to_tsvector('simple', content) || to_tsvector('english', content)`), because standard English stemming alone can split or normalize away underscored technical tokens.

## Version Compatibility

| Package A | Compatible With | Notes |
|-----------|-----------------|-------|
| `sqlalchemy==2.1.8` | `asyncpg==0.32.0`, `pgvector==0.5.1` | Requires connection string `postgresql+asyncpg://...` and registering the vector codec on connection checkout (`register_vector`). |
| `sentence-transformers==6.2.0` | `torch==2.15.0`, `transformers>=5.0` | `CrossEncoder` supports `activation_fn=nn.Sigmoid()` so raw logits from `ms-marco-MiniLM-L6-v2` or `bge-reranker-base` are normalized to `0.0–1.0` probabilities for the `< 0.65` deterministic refusal gate. |
| `redisvl==0.31.0` | `redis==8.1.0` + `redis:8-alpine` (or `redis/redis-stack-server`) | Requires Redis 8+ (which includes RediSearch/Vector capabilities out of the box) or `redis-stack-server` 7.4+ for `FT.CREATE` / `FT.SEARCH` tag-filtered vector queries. |
| `ragas==0.4.3` | `pydantic==2.14.3`, `litellm==1.108.4`, `openai==3.49.0` | Ragas v0.4+ uses `SingleTurnSample(user_input=..., retrieved_contexts=..., response=..., reference=...)` instead of the deprecated v0.1/v0.2 `ground_truths` list column. |
| `langfuse==5.2.0` | `fastapi==0.162.3`, `litellm==1.108.4` | Langfuse v3+/v5 `@observe()` automatically preserves `contextvars` across `async def` functions and wraps Starlette `StreamingResponse` iterators. |

## Sources

- Context7 `/pgvector/pgvector-python` — Verified `pgvector.sqlalchemy.Vector`, `HALFVEC`, HNSW index DDL (`postgresql_using='hnsw'`), and `pgvector.asyncpg.register_vector` (Confidence: HIGH)
- Context7 `/huggingface/sentence-transformers` — Verified `CrossEncoder.rank(query, passages, return_documents=True)` and `CrossEncoder.predict()` APIs (Confidence: HIGH)
- Context7 `/langfuse/langfuse-python` — Verified `@observe(name=..., as_type=...)` async decorator, `start_as_current_observation`, and Starlette `StreamingResponse` wrapping (Confidence: HIGH)
- Context7 `/vibrantlabsai/ragas` — Verified Ragas v0.4 `SingleTurnSample`, `EvaluationDataset`, `ContextPrecision`, `ContextRecall`, `Faithfulness`, and `metric.ascore()` (Confidence: HIGH)
- Context7 `/websites/deepwiki_redis_redis-vl-python` — Verified `SemanticCache` multi-tenancy with `filterable_fields` and `Tag` filter expressions (Confidence: HIGH)
- Context7 `/qdrant/qdrant-client` — Verified `query_points` with `Prefetch`, `FusionQuery(fusion=Fusion.RRF)`, and `models.Filter` (Confidence: HIGH)
- Context7 `/vercel/next.js` — Verified App Router streaming Route Handlers with `ReadableStream` and SSE (Confidence: HIGH)
- PyPI & npm Official JSON Registries (`https://pypi.org/pypi/<pkg>/json`, `https://registry.npmjs.org/<pkg>/latest`) — Verified exact current versions for all 30 packages on 2026-11-10 (Confidence: HIGH)

<!-- GSD:stack-end -->

<!-- GSD:conventions-start source:CONVENTIONS.md -->

## Conventions

Conventions not yet established. Will populate as patterns emerge during development.
<!-- GSD:conventions-end -->

<!-- GSD:architecture-start source:ARCHITECTURE.md -->

## Architecture

Architecture not yet mapped. Follow existing patterns found in the codebase.
<!-- GSD:architecture-end -->

<!-- GSD:skills-start source:skills/ -->

## Project Skills

No project skills found. Add skills to any of: `.agents/skills/`, `.agents/skills/`, `.cursor/skills/`, `.github/skills/`, or `.codex/skills/` with a `SKILL.md` index file.
<!-- GSD:skills-end -->

<!-- GSD:workflow-start source:GSD defaults -->

## GSD Workflow Enforcement

Before using Edit, Write, or other file-changing tools, start work through a GSD command so planning artifacts and execution context stay in sync.

Use these entry points:
- `/gsd-fast` for a trivial task inline, with no subagents and no PLAN.md
- `/gsd-quick` for small fixes, doc updates, and ad-hoc tasks
- `/gsd-debug` for investigation and bug fixing
- `/gsd-execute-phase` for planned phase work

Do not make direct repo edits outside a GSD workflow unless the user explicitly asks to bypass it.
<!-- GSD:workflow-end -->

<!-- GSD:profile-start -->

## Developer Profile

> Profile not yet configured. Run `/gsd-profile-user` to generate your developer profile.
> This section is managed by `generate-claude-profile` -- do not edit manually.
<!-- GSD:profile-end -->
