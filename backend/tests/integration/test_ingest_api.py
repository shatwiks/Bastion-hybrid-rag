import uuid
from collections.abc import AsyncGenerator

import pytest
from httpx import AsyncClient
from sqlalchemy import select, text

from app.db.models import Document, DocumentChunk
from app.db.session import async_engine, async_session_maker
from app.main import app, lifespan
from app.redis_client import get_redis_client
from app.services.embeddings import get_embedding_service


@pytest.fixture(scope="module", autouse=True)
def warmup_embeddings_once() -> None:
    """Warm up the local SentenceTransformer singleton once for integration tests."""
    get_embedding_service().warmup()


@pytest.fixture
async def created_doc_ids() -> AsyncGenerator[list[uuid.UUID], None]:
    """Track documents created during a test and remove them + dispose pools on teardown."""
    ids: list[uuid.UUID] = []
    yield ids

    if ids:
        async with async_session_maker() as session:
            for doc_id in ids:
                doc = await session.get(Document, doc_id)
                if doc is not None:
                    await session.delete(doc)
            await session.commit()

    await async_engine.dispose()


async def _mint_token(async_client: AsyncClient, tenant_id: str, persona: str) -> str:
    resp = await async_client.post(
        "/api/v1/auth/demo-token",
        json={"tenant_id": tenant_id, "persona": persona},
    )
    assert resp.status_code == 200
    return resp.json()["access_token"]


@pytest.mark.asyncio
async def test_ingest_document_and_list_documents_success(
    async_client: AsyncClient,
    created_doc_ids: list[uuid.UUID],
) -> None:
    """Minting executive token for acme_corp and ingesting returns 201 and lists accurately."""
    acme_token = await _mint_token(async_client, "acme_corp", "executive")
    globex_token = await _mint_token(async_client, "globex_corp", "executive")

    unique_title = f"Integration Test Runbook {uuid.uuid4().hex[:8]}"
    payload = {
        "title": unique_title,
        "content": (
            "# Webhook Sync\n\n"
            "Diagnostic steps for ERR_409_CONFLICT during concurrent updates.\n\n"
            "## Recovery\n\n"
            "Retry with exponential backoff."
        ),
        "tenant_id": "acme_corp",
        "allowed_roles": ["support_tier_1", "executive"],
        "doc_metadata": {"author": "qa", "env": "integration"},
    }

    ingest_resp = await async_client.post(
        "/api/v1/ingest",
        json=payload,
        headers={"Authorization": f"Bearer {acme_token}"},
    )
    assert ingest_resp.status_code == 201
    data = ingest_resp.json()
    doc_uuid = uuid.UUID(data["document_id"])
    created_doc_ids.append(doc_uuid)

    assert data["title"] == unique_title
    assert data["tenant_id"] == "acme_corp"
    assert data["chunks_count"] == 2
    assert len(data["chunks"]) == 2
    assert all(c["character_count"] > 0 for c in data["chunks"])

    # Verify PostgreSQL persisted vector(384) and dual-dictionary tsv_content
    async with async_session_maker() as session:
        chunks = (
            await session.execute(
                select(DocumentChunk).where(DocumentChunk.document_id == doc_uuid)
            )
        ).scalars().all()
        assert len(chunks) == 2
        assert all(c.embedding is not None and len(c.embedding) == 384 for c in chunks)

        fts_match = await session.execute(
            text(
                "SELECT count(*) FROM document_chunks "
                "WHERE document_id = :doc_id "
                "AND tsv_content @@ websearch_to_tsquery('simple', 'err409conflict')"
            ),
            {"doc_id": doc_uuid},
        )
        assert fts_match.scalar_one() == 1

    # Verify GET /api/v1/documents returns the document for acme_corp
    acme_list_resp = await async_client.get(
        "/api/v1/documents",
        headers={"Authorization": f"Bearer {acme_token}"},
    )
    assert acme_list_resp.status_code == 200
    acme_docs = acme_list_resp.json()["documents"]
    matched = [d for d in acme_docs if d["id"] == str(doc_uuid)]
    assert len(matched) == 1
    assert matched[0]["title"] == unique_title
    assert matched[0]["chunks_count"] == 2
    assert matched[0]["doc_metadata"] == {"author": "qa", "env": "integration"}

    # Verify strict tenant isolation: globex_corp cannot see acme_corp document
    globex_list_resp = await async_client.get(
        "/api/v1/documents",
        headers={"Authorization": f"Bearer {globex_token}"},
    )
    assert globex_list_resp.status_code == 200
    globex_docs = globex_list_resp.json()["documents"]
    assert all(d["id"] != str(doc_uuid) for d in globex_docs)


@pytest.mark.asyncio
async def test_cross_tenant_ingest_rejected_403(
    async_client: AsyncClient,
    created_doc_ids: list[uuid.UUID],
) -> None:
    """Cross-tenant ingestion attempt (acme_corp token -> globex_corp payload) returns 403."""
    acme_token = await _mint_token(async_client, "acme_corp", "executive")

    payload = {
        "title": f"Malicious Injection {uuid.uuid4().hex[:8]}",
        "content": "# Injection\n\nUnauthorized cross-tenant content.",
        "tenant_id": "globex_corp",
        "allowed_roles": ["public"],
    }
    resp = await async_client.post(
        "/api/v1/ingest",
        json=payload,
        headers={"Authorization": f"Bearer {acme_token}"},
    )
    assert resp.status_code == 403
    assert "Cross-tenant ingestion forbidden" in resp.json()["detail"]


@pytest.mark.asyncio
async def test_unauthorized_role_ingest_rejected_403(
    async_client: AsyncClient,
    created_doc_ids: list[uuid.UUID],
) -> None:
    """Public persona lacking administrative role rights receives HTTP 403 Forbidden."""
    public_token = await _mint_token(async_client, "acme_corp", "public")

    payload = {
        "title": f"Public Upload Attempt {uuid.uuid4().hex[:8]}",
        "content": "# Unauthorized\n\nPublic role cannot ingest documents.",
        "tenant_id": "acme_corp",
        "allowed_roles": ["public"],
    }
    resp = await async_client.post(
        "/api/v1/ingest",
        json=payload,
        headers={"Authorization": f"Bearer {public_token}"},
    )
    assert resp.status_code == 403
    assert "administrative ingestion role" in resp.json()["detail"]


@pytest.mark.asyncio
async def test_reingest_same_title_replaces_idempotently(
    async_client: AsyncClient,
    created_doc_ids: list[uuid.UUID],
) -> None:
    """Re-ingesting a document with identical (tenant_id, title) replaces the prior version."""
    token = await _mint_token(async_client, "acme_corp", "support_tier_1")
    shared_title = f"Idempotent Runbook {uuid.uuid4().hex[:8]}"

    first_payload = {
        "title": shared_title,
        "content": "# Version 1\n\nInitial single-section content.",
        "tenant_id": "acme_corp",
        "allowed_roles": ["support_tier_1"],
    }
    resp1 = await async_client.post(
        "/api/v1/ingest",
        json=first_payload,
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp1.status_code == 201
    first_id = uuid.UUID(resp1.json()["document_id"])
    created_doc_ids.append(first_id)

    second_payload = {
        "title": shared_title,
        "content": (
            "# Version 2 Overview\n\nUpdated overview.\n\n"
            "## Troubleshooting\n\nUpdated troubleshooting for SKU-9921-A."
        ),
        "tenant_id": "acme_corp",
        "allowed_roles": ["support_tier_1", "executive"],
    }
    resp2 = await async_client.post(
        "/api/v1/ingest",
        json=second_payload,
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp2.status_code == 201
    second_data = resp2.json()
    second_id = uuid.UUID(second_data["document_id"])
    created_doc_ids.append(second_id)

    assert second_id != first_id
    assert second_data["chunks_count"] == 2

    # Ensure only the latest version exists in PostgreSQL for (acme_corp, shared_title)
    async with async_session_maker() as session:
        docs = (
            await session.execute(
                select(Document).where(
                    Document.tenant_id == "acme_corp",
                    Document.title == shared_title,
                )
            )
        ).scalars().all()
        assert len(docs) == 1
        assert docs[0].id == second_id


@pytest.mark.asyncio
async def test_ingest_invalidates_target_tenant_redis_cache(
    async_client: AsyncClient,
    created_doc_ids: list[uuid.UUID],
) -> None:
    """Document ingestion invalidates llm_cache:{tenant_id}:* keys while preserving other tenants."""
    redis = get_redis_client()
    acme_key = f"llm_cache:acme_corp:test_{uuid.uuid4().hex[:8]}"
    globex_key = f"llm_cache:globex_corp:test_{uuid.uuid4().hex[:8]}"

    try:
        await redis.set(acme_key, "stale-acme-answer")
        await redis.set(globex_key, "valid-globex-answer")

        token = await _mint_token(async_client, "acme_corp", "executive")
        payload = {
            "title": f"Cache Invalidation Doc {uuid.uuid4().hex[:8]}",
            "content": "# Cache Test\n\nTrigger cache invalidation on acme_corp.",
            "tenant_id": "acme_corp",
            "allowed_roles": ["executive"],
        }
        resp = await async_client.post(
            "/api/v1/ingest",
            json=payload,
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 201
        created_doc_ids.append(uuid.UUID(resp.json()["document_id"]))

        assert await redis.get(acme_key) is None
        assert await redis.get(globex_key) == "valid-globex-answer"
    finally:
        await redis.delete(acme_key, globex_key)
        await redis.aclose()


@pytest.mark.asyncio
async def test_ingest_and_list_require_authentication_401(async_client: AsyncClient) -> None:
    """Missing Authorization headers are rejected with HTTP 401 on ingest and list endpoints."""
    ingest_resp = await async_client.post(
        "/api/v1/ingest",
        json={
            "title": "Unauthenticated",
            "content": "# No Auth\n\nBody.",
            "tenant_id": "acme_corp",
            "allowed_roles": ["public"],
        },
    )
    assert ingest_resp.status_code == 401

    list_resp = await async_client.get("/api/v1/documents")
    assert list_resp.status_code == 401


@pytest.mark.asyncio
async def test_lifespan_prewarms_embedding_service(
    created_doc_ids: list[uuid.UUID],
) -> None:
    """Application lifespan startup hook ensures EmbeddingService is pre-warmed."""
    async with lifespan(app):
        assert get_embedding_service().is_warmed_up is True

