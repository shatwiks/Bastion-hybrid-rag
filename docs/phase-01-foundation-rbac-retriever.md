# Phase 1: Foundation, Pre-Retrieval RBAC Security & Pluggable Hybrid Retriever

> **Core Problem Solved:** Naive RAG prototypes retrieve top-K chunks globally and filter permissions afterward in Python—causing **Top-K starvation** (returning 0 results when restricted documents dominate top similarity scores) and risking cross-tenant data leaks. Phase 1 establishes the infrastructure, database schema, JWT security boundary, and mathematical `WHERE`-clause pre-filtering inside the database engine itself.

---

## 1. Commits & File Inventory

| Commit | Scope | Files Added / Modified | Purpose |
| :--- | :--- | :--- | :--- |
| `6247e8f` | Infrastructure & FastAPI | Added `.env.example`, `.gitignore`, `docker-compose.yml`, `backend/Dockerfile`, `backend/pyproject.toml`, `backend/README.md`, `backend/app/config.py`, `backend/app/db.py`, `backend/app/redis_client.py`, `backend/app/api/v1/health.py`, `backend/app/main.py`, `backend/tests/conftest.py`, `backend/tests/integration/test_health.py` | Async FastAPI skeleton, typed Pydantic settings, Postgres 17 + pgvector & Redis 8 Docker Compose topology, `/api/v1/health` probe |
| `6e2bbe9` | Frontend Scaffold | Added `frontend/Dockerfile`, `frontend/next.config.mjs`, `frontend/package.json`, `frontend/tsconfig.json`, `frontend/src/app/layout.tsx`, `frontend/src/app/globals.css`, `frontend/src/app/page.tsx` | Next.js 16 App Router + React 19 + Tailwind CSS v4 shell |
| `62289b3` & `6f4d06c` | Database Schema & Alembic | Added `backend/alembic.ini`, `backend/alembic/env.py`, `backend/alembic/script.py.mako`, `backend/alembic/versions/0001_initial_schema.py`, `backend/app/db/__init__.py`, `backend/app/db/models.py`, `backend/app/db/session.py`, `backend/tests/integration/test_db_schema.py` (refactored `db.py` into `db/` package) | `documents` + `document_chunks` tables, `pgvector` extension, `HNSW` vector index, `GIN` ACL & `tsvector` FTS indexes |
| `4e99a5d` & `f994582` & `109d15c` | Auth & RBAC Guardrail | Added `backend/app/core/security.py`, `backend/app/schemas/auth.py`, `backend/app/api/deps.py`, `backend/app/api/v1/auth.py`, `backend/tests/unit/test_security.py`, `backend/tests/integration/test_auth_guardrail.py`, `backend/tests/integration/test_demo_tokens.py`; modified `backend/app/main.py` | Fail-closed JWT validation, immutable `SecurityContext`, canonical `scope_hash`, `POST /api/v1/auth/demo-token`, `GET /api/v1/auth/me` |
| `3138259` & `31fbb25` & `4b624f9` | Retriever Abstraction | Added `backend/app/retrievers/__init__.py`, `backend/app/retrievers/base.py`, `backend/app/retrievers/postgres_hybrid.py`, `backend/app/retrievers/qdrant_hybrid.py`, `backend/tests/unit/test_retriever_protocol.py`, `backend/tests/integration/test_postgres_retriever_rbac.py`, `backend/tests/unit/test_qdrant_retriever.py` | Metaclass-enforced `VectorStoreRetriever` protocol, PostgreSQL hybrid RRF SQL CTE implementation, pluggable Qdrant adapter |
| `9c27803` | Quality Polish | Updated `backend/app/db/__init__.py`, `models.py`, `session.py`, `redis_client.py`, `test_db_schema.py` | Clean Ruff lint hygiene across Phase 1 modules |

---

## 2. Infrastructure & Typed Configuration

### Docker Topology ([`docker-compose.yml`](../docker-compose.yml))
The local stack runs 4 coordinated containers:
1. **`postgres` (`pgvector/pgvector:pg17`)**: Host port `5437` mapped to container `5432`, backed by persistent volume `postgres_data`. Runs PostgreSQL 17 with native `pgvector` extension support.
2. **`redis` (`redis:8-alpine`)**: Port `6379`. Acts as the permission-scoped semantic cache store.
3. **`backend`**: FastAPI + Uvicorn ASGI server on port `8000`.
4. **`frontend`**: Next.js App Router UI on host port `3005` mapped to container `3000`, pointed at `NEXT_PUBLIC_API_URL: http://localhost:8000`.

### Environment Configuration ([`backend/app/config.py`](../backend/app/config.py))
`Settings(BaseSettings)` (cached via `@lru_cache` in `get_settings()`) loads configuration from `.env`:
- **Database & Cache:** `DATABASE_URL` (`postgresql+asyncpg://postgres:postgres@localhost:5437/rag_engine`), `REDIS_URL` (`redis://localhost:6379/0`).
- **Security:** `JWT_SECRET_KEY`, `ALGORITHM = "HS256"`.
- **Models & Gate:** `REFUSAL_THRESHOLD = 0.65`, `EMBEDDING_MODEL = "BAAI/bge-small-en-v1.5"`, `RERANKER_MODEL = "cross-encoder/ms-marco-MiniLM-L6-v2"`.
- **Multi-Provider LLM & Telemetry:** `LLM_MODEL = "gpt-4o-mini"`, `OPENAI_API_KEY`, `GEMINI_API_KEY`, `ANTHROPIC_API_KEY`, `LANGFUSE_PUBLIC_KEY`, `LANGFUSE_SECRET_KEY`, `LANGFUSE_HOST`.

### Health Probe ([`backend/app/api/v1/health.py`](../backend/app/api/v1/health.py))
`GET /api/v1/health` executes `check_database_connection()` and `check_redis_connection()` concurrently-in-await and returns `HealthResponse(status="ok" | "degraded", postgres=..., redis=..., version=settings.VERSION)`.

---

## 3. Unified Relational + Vector + Lexical Schema

Migration [`backend/alembic/versions/0001_initial_schema.py`](../backend/alembic/versions/0001_initial_schema.py) and ORM definitions in [`backend/app/db/models.py`](../backend/app/db/models.py) unify transactional ACL metadata, dense embeddings, and lexical full-text search inside a single PostgreSQL database—eliminating dual-write drift between an external vector store and an ACL database.

```sql
-- Simplified conceptual view of 0001_initial_schema.py
CREATE EXTENSION IF NOT EXISTS vector;

documents (
    id           UUID PRIMARY KEY,
    title        VARCHAR,
    tenant_id    VARCHAR,
    doc_metadata JSONB,
    created_at   TIMESTAMPTZ
)

document_chunks (
    id             UUID PRIMARY KEY,
    document_id    UUID REFERENCES documents(id) ON DELETE CASCADE,
    tenant_id      VARCHAR,
    section_header VARCHAR,
    content        TEXT,
    allowed_roles  TEXT[],
    embedding      VECTOR(384),
    tsv_content    TSVECTOR GENERATED ALWAYS AS (
                       to_tsvector('simple', content) || to_tsvector('english', content)
                   ) STORED
)
```

### Why Three Specialized Indexes?
1. **`GIN(allowed_roles)` + `tenant_id` B-tree:** Makes pre-retrieval array overlap (`allowed_roles && :user_roles`) and tenant equality checks sub-millisecond before vector distance calculations run.
2. **`HNSW` on `embedding` (`vector_cosine_ops`, `m=16`, `ef_construction=64`):** Enables fast approximate nearest-neighbor search over 384-dimensional normalized vectors.
3. **`GIN(tsv_content)` with dual `simple` + `english` dictionaries:** Standard English stemming (`english`) matches natural prose forms (*"troubleshooting"* -> *"troubleshoot"*), while `simple` preserves verbatim tokens without stemming—ensuring error codes (`ERR_409_CONFLICT`), SKUs (`SKU-9921-A`), and CLI flags remain exact-matchable.

---

## 4. JWT Authentication & Immutable `SecurityContext`

### Cryptographic Scope & Token Verification ([`backend/app/core/security.py`](../backend/app/core/security.py))
Every security context computes a canonical deterministic hash:
- `compute_scope_hash(tenant_id, allowed_roles)`: Sorts and deduplicates roles (`sorted_comma_roles`) and computes `SHA-256("{tenant_id}:{sorted_comma_roles}")[:16]`.
- `create_access_token(...)`: Signs JWTs using `settings.JWT_SECRET_KEY` and strict `settings.ALGORITHM` (24-hour default TTL).
- `decode_access_token(...)`: Decodes with explicit `algorithms=[settings.ALGORITHM]`, rejecting unsigned or algorithm-confused tokens (`PyJWT[crypto]`, intentionally avoiding `python-jose`).

### Fail-Closed Request Dependency ([`backend/app/api/deps.py`](../backend/app/api/deps.py))
`get_security_context` uses `HTTPBearer(auto_error=False)` and fails closed at every boundary:
- Missing header or non-Bearer scheme -> `401 Unauthorized`
- Expired or signature-invalid JWT -> `401 Unauthorized`
- Missing `tenant_id` or empty `allowed_roles` -> `403 Forbidden`
- On success -> returns a frozen Pydantic [`SecurityContext`](../backend/app/schemas/auth.py) (`tenant_id`, immutable `tuple[str, ...] allowed_roles`, `scope_hash`).

### Demo Persona Minter ([`backend/app/api/v1/auth.py`](../backend/app/api/v1/auth.py))
To support instant multi-tenant and role-escalation testing in the UI and evaluation harness:
- `SUPPORTED_DEMO_TENANTS = {"acme_corp", "globex_corp"}`
- `PERSONA_ROLES_MAP`:
  - `"public"` -> `["public"]`
  - `"support_tier_1"` -> `["public", "support_tier_1"]`
  - `"executive"` -> `["public", "support_tier_1", "executive"]`
- `POST /api/v1/auth/demo-token` mints a signed JWT for the requested tenant/persona (or custom roles); `GET /api/v1/auth/me` inspects the active verified claims.

---

## 5. Metaclass-Enforced Pluggable Retriever & Hybrid RRF SQL

### Enforcing RBAC at the Type-System Level ([`backend/app/retrievers/base.py`](../backend/app/retrievers/base.py))
Any retriever adapter implementing `VectorStoreRetriever` is checked at class-definition time by `_VectorStoreRetrieverMeta`:
- It inspects the signature of `retrieve_hybrid(...)` and **raises `TypeError` if the first operational parameter is not `security_ctx`**. This makes it structurally impossible for a future backend developer to add a retriever adapter that forgets RBAC context.
- Returns frozen `RetrievedChunk` models (chunk ID, document metadata, content, dense/sparse ranks, `rrf_score`, optional `rerank_score`).
- Custom exceptions: `RetrieverError` (redacts database credentials in `to_dict()`) and `RBACSecurityViolation`.

### Single-Roundtrip Pre-Filtered Hybrid RRF ([`backend/app/retrievers/postgres_hybrid.py`](../backend/app/retrievers/postgres_hybrid.py))
`PostgresHybridRetriever.retrieve_hybrid(security_ctx, ...)` executes `HYBRID_RRF_SQL` inside PostgreSQL in one network roundtrip:

```mermaid
flowchart TD
    Q["User Query + SecurityContext"] --> CTE0["CTE 1: rbac_pool AS NOT MATERIALIZED<br/>WHERE tenant_id = :tenant_id<br/>AND allowed_roles && :user_roles"]
    CTE0 --> D["CTE 2: dense_candidates<br/>ORDER BY embedding <=> :query_vec<br/>LIMIT 50"]
    CTE0 --> S["CTE 3: sparse_candidates<br/>tsv_content @@ (simple OR english tsquery)<br/>LIMIT 50"]
    D --> J["FULL OUTER JOIN on chunk_id"]
    S --> J
    J --> RRF["RRF Score:<br/>COALESCE(1 / (60 + dense_rank), 0)<br/>+ COALESCE(1 / (60 + sparse_rank), 0)"]
    RRF --> OUT["Top K RetrievedChunks<br/>(zero unauthorized chunks ever scanned or ranked)"]
```

Key implementation details observed in `postgres_hybrid.py`:
- **Iterative HNSW Scanning:** Sets `LOCAL hnsw.iterative_scan = 'relaxed_order'` and `hnsw.ef_search = 80` on the transaction so filtered HNSW graph traversal continues exploring neighbors when restrictive roles filter out dense clusters—preventing sparse/empty recall for `public` users when `executive` chunks sit nearby in vector space.
- **`AS NOT MATERIALIZED` Fence:** Ensures PostgreSQL's planner pushes `tenant_id = :tenant_id AND allowed_roles && :user_roles` directly into index scans before ranking.
- **OR-Combined Lexical `tsquery`:** Uses dual `plainto_tsquery('simple', ...)` and `plainto_tsquery('english', ...)`, converting `' & '` to `' | '` (wrapped in `NULLIF`) so a query containing multiple conversational words plus an exact code doesn't fail just because one conversational word isn't in the chunk.
- **Pluggable Qdrant Alternative ([`backend/app/retrievers/qdrant_hybrid.py`](../backend/app/retrievers/qdrant_hybrid.py)):** Implements the exact same `VectorStoreRetriever` protocol using `AsyncQdrantClient.query_points(prefetch=[...], query=FusionQuery(fusion=Fusion.RRF), query_filter=models.Filter(must=[tenant_id, allowed_roles]))`, ready for multi-million vector deployments.

---

## 6. How Phase 1 Was Verified
- [`backend/tests/integration/test_health.py`](../backend/tests/integration/test_health.py): Verified Postgres + Redis health reporting.
- [`backend/tests/integration/test_db_schema.py`](../backend/tests/integration/test_db_schema.py): Verified `vector` extension, `documents` & `document_chunks` tables, HNSW & GIN indexes.
- [`backend/tests/unit/test_security.py`](../backend/tests/unit/test_security.py), [`test_auth_guardrail.py`](../backend/tests/integration/test_auth_guardrail.py), [`test_demo_tokens.py`](../backend/tests/integration/test_demo_tokens.py): Verified canonical `scope_hash`, `401` on invalid/missing JWTs, `403` on missing `tenant_id`/`allowed_roles`, and demo token minting.
- [`backend/tests/unit/test_retriever_protocol.py`](../backend/tests/unit/test_retriever_protocol.py), [`test_postgres_retriever_rbac.py`](../backend/tests/integration/test_postgres_retriever_rbac.py), [`test_qdrant_retriever.py`](../backend/tests/unit/test_qdrant_retriever.py): Verified metaclass RBAC enforcement, zero Top-K starvation when high-similarity restricted chunks exist, strict cross-tenant isolation, and Qdrant RRF filter parity.
