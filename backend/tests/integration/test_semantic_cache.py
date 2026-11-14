import math
import uuid
from collections.abc import AsyncGenerator

import pytest
import redis.asyncio as aioredis

from app.core.security import compute_scope_hash
from app.redis_client import close_redis_pool, get_redis_client
from app.schemas.auth import SecurityContext
from app.schemas.cache import CachedCitation
from app.services.semantic_cache import (
    SemanticCacheService,
    compute_entity_fingerprint,
)


def _make_security_ctx(tenant_id: str, roles: tuple[str, ...]) -> SecurityContext:
    return SecurityContext(
        tenant_id=tenant_id,
        allowed_roles=roles,
        scope_hash=compute_scope_hash(tenant_id, roles),
    )


def _unit_vector(dim: int = 384, primary_idx: int = 0, secondary_weight: float = 0.0) -> list[float]:
    vec = [0.0] * dim
    vec[primary_idx] = 1.0
    if secondary_weight != 0.0:
        vec[(primary_idx + 1) % dim] = secondary_weight
    norm = math.sqrt(sum(v * v for v in vec))
    return [v / norm for v in vec]


def _sample_citation(rerank_score: float = 0.92) -> CachedCitation:
    return CachedCitation(
        chunk_id=str(uuid.uuid4()),
        document_id=str(uuid.uuid4()),
        document_title="Webhook Synchronization Runbook",
        section_header="Webhook Synchronization Runbook > Conflict Resolution",
        content="Retry webhook delivery with exponential backoff when ERR_409_CONFLICT occurs.",
        allowed_roles=["support_tier_1", "executive"],
        rerank_score=rerank_score,
    )


@pytest.fixture
async def cache_env() -> AsyncGenerator[tuple[SemanticCacheService, aioredis.Redis], None]:
    """Provide a live SemanticCacheService and clean up test keys + Redis pool on teardown."""
    redis_client = get_redis_client()
    service = SemanticCacheService(redis_client=redis_client)
    test_tenants = ("acme_corp", "globex_corp")

    for tenant in test_tenants:
        await service.invalidate_tenant(tenant)

    try:
        yield service, redis_client
    finally:
        for tenant in test_tenants:
            await service.invalidate_tenant(tenant)
        await redis_client.aclose()
        await close_redis_pool()


@pytest.mark.asyncio
async def test_semantic_cache_exact_and_paraphrased_hit_under_50ms(
    cache_env: tuple[SemanticCacheService, aioredis.Redis],
) -> None:
    """Exact and paraphrased queries (>= 0.90 similarity) in same scope hit in < 50ms."""
    service, _ = cache_env
    ctx = _make_security_ctx("acme_corp", ("support_tier_1",))
    base_vec = _unit_vector(primary_idx=0)
    # Cosine similarity with base_vec is 1 / sqrt(1 + 0.25^2) ~= 0.9701 >= 0.90
    paraphrase_vec = _unit_vector(primary_idx=0, secondary_weight=0.25)
    # Cosine similarity with base_vec is 1 / sqrt(1 + 0.80^2) ~= 0.7809 < 0.90
    distant_vec = _unit_vector(primary_idx=0, secondary_weight=0.80)

    citation = _sample_citation(0.93)
    entry_id = await service.store(
        security_ctx=ctx,
        query="What is the standard customer escalation SLA?",
        query_embedding=base_vec,
        answer_text="Tier-1 escalations have a 4-hour response SLA [chunk-1].",
        citations=[citation],
        top_rerank_score=0.93,
    )
    assert entry_id is not None

    exact_result = await service.lookup(
        security_ctx=ctx,
        query="What is the standard customer escalation SLA?",
        query_embedding=base_vec,
    )
    assert exact_result.hit is True
    assert exact_result.similarity_score == pytest.approx(1.0, abs=1e-4)
    assert exact_result.entity_fingerprint == "none"
    assert exact_result.entry is not None
    assert exact_result.entry.entry_id == entry_id
    assert exact_result.entry.citations[0].chunk_id == citation.chunk_id
    assert exact_result.latency_ms < 50.0

    paraphrase_result = await service.lookup(
        security_ctx=ctx,
        query="Tell me the response time SLA for customer escalations",
        query_embedding=paraphrase_vec,
    )
    assert paraphrase_result.hit is True
    assert paraphrase_result.similarity_score >= 0.90
    assert paraphrase_result.entry is not None
    assert paraphrase_result.entry.answer_text == (
        "Tier-1 escalations have a 4-hour response SLA [chunk-1]."
    )
    assert paraphrase_result.latency_ms < 50.0

    miss_result = await service.lookup(
        security_ctx=ctx,
        query="Completely unrelated onboarding question",
        query_embedding=distant_vec,
    )
    assert miss_result.hit is False
    assert miss_result.entry is None
    assert miss_result.similarity_score < 0.90


@pytest.mark.asyncio
async def test_semantic_cache_cross_tenant_isolation(
    cache_env: tuple[SemanticCacheService, aioredis.Redis],
) -> None:
    """Identical query and vector under globex_corp never hits acme_corp cached entry."""
    service, _ = cache_env
    acme_ctx = _make_security_ctx("acme_corp", ("executive",))
    globex_ctx = _make_security_ctx("globex_corp", ("executive",))
    vec = _unit_vector(primary_idx=12)

    entry_id = await service.store(
        security_ctx=acme_ctx,
        query="What was Q3 Acme revenue?",
        query_embedding=vec,
        answer_text="Acme Q3 revenue was $42M [chunk-acme].",
        citations=[_sample_citation(0.95)],
        top_rerank_score=0.95,
    )
    assert entry_id is not None

    acme_hit = await service.lookup(acme_ctx, "What was Q3 Acme revenue?", vec)
    assert acme_hit.hit is True

    globex_miss = await service.lookup(globex_ctx, "What was Q3 Acme revenue?", vec)
    assert globex_miss.hit is False
    assert globex_miss.entry is None


@pytest.mark.asyncio
async def test_semantic_cache_cross_role_isolation_within_same_tenant(
    cache_env: tuple[SemanticCacheService, aioredis.Redis],
) -> None:
    """Executive cache entries cannot leak to public role within the same tenant."""
    service, _ = cache_env
    exec_ctx = _make_security_ctx("acme_corp", ("executive",))
    public_ctx = _make_security_ctx("acme_corp", ("public",))
    vec = _unit_vector(primary_idx=25)

    await service.store(
        security_ctx=exec_ctx,
        query="Summarize confidential M&A acquisition targets",
        query_embedding=vec,
        answer_text="Target Alpha acquisition valuation is $120M [chunk-exec].",
        citations=[_sample_citation(0.91)],
        top_rerank_score=0.91,
    )

    exec_hit = await service.lookup(
        exec_ctx, "Summarize confidential M&A acquisition targets", vec
    )
    assert exec_hit.hit is True

    public_miss = await service.lookup(
        public_ctx, "Summarize confidential M&A acquisition targets", vec
    )
    assert public_miss.hit is False
    assert public_miss.entry is None


@pytest.mark.asyncio
async def test_semantic_cache_entity_fingerprint_prevents_error_code_and_flag_collisions(
    cache_env: tuple[SemanticCacheService, aioredis.Redis],
) -> None:
    """Distinct error codes, SKUs, and CLI flags never collide even with identical vectors."""
    service, _ = cache_env
    ctx = _make_security_ctx("acme_corp", ("support_tier_1",))
    shared_vec = _unit_vector(primary_idx=40)

    # 1. Error codes: ERR_409_CONFLICT vs ERR_503_SERVICE_UNAVAILABLE
    await service.store(
        security_ctx=ctx,
        query="How do I resolve ERR_409_CONFLICT?",
        query_embedding=shared_vec,
        answer_text="Resolve ERR_409_CONFLICT by incrementing the idempotency version [c1].",
        citations=[_sample_citation(0.94)],
        top_rerank_score=0.94,
    )

    err409_hit = await service.lookup(ctx, "How do I resolve ERR_409_CONFLICT?", shared_vec)
    assert err409_hit.hit is True
    assert err409_hit.entity_fingerprint == "err_409_conflict"

    err409_hyphen_hit = await service.lookup(
        ctx, "How do I resolve err-409-conflict?", shared_vec
    )
    assert err409_hyphen_hit.hit is True
    assert err409_hyphen_hit.entity_fingerprint == "err_409_conflict"

    err503_miss = await service.lookup(
        ctx, "How do I resolve ERR_503_SERVICE_UNAVAILABLE?", shared_vec
    )
    assert err503_miss.hit is False
    assert err503_miss.entity_fingerprint == "err_503_service_unavailable"
    assert err503_miss.entry is None

    # 2. CLI flags: --enable-read-replica vs --force-reconcile
    await service.store(
        security_ctx=ctx,
        query="What does --enable-read-replica do during sync?",
        query_embedding=shared_vec,
        answer_text="The --enable-read-replica flag routes reads to replicas [c2].",
        citations=[_sample_citation(0.90)],
        top_rerank_score=0.90,
    )

    replica_hit = await service.lookup(
        ctx, "What does --enable-read-replica do during sync?", shared_vec
    )
    assert replica_hit.hit is True
    assert replica_hit.entity_fingerprint == "enable_read_replica"

    reconcile_miss = await service.lookup(
        ctx, "What does --force-reconcile do during sync?", shared_vec
    )
    assert reconcile_miss.hit is False
    assert reconcile_miss.entity_fingerprint == "force_reconcile"
    assert reconcile_miss.entry is None

    # 3. Multi-token deterministic sorting
    assert (
        compute_entity_fingerprint("Fix ERR_409_CONFLICT for SKU-9921-A")
        == "err_409_conflict|sku_9921_a"
    )


@pytest.mark.asyncio
async def test_semantic_cache_confidence_guard_and_tenant_invalidation(
    cache_env: tuple[SemanticCacheService, aioredis.Redis],
) -> None:
    """Low-confidence answers (< 0.65) are never cached, and invalidate_tenant wipes only target tenant."""
    service, redis_client = cache_env
    acme_exec = _make_security_ctx("acme_corp", ("executive",))
    acme_public = _make_security_ctx("acme_corp", ("public",))
    globex_exec = _make_security_ctx("globex_corp", ("executive",))

    vec_a = _unit_vector(primary_idx=60)
    vec_b = _unit_vector(primary_idx=61)

    # Below REFUSAL_THRESHOLD (0.65) -> must NOT cache
    skipped_id = await service.store(
        security_ctx=acme_exec,
        query="Unanswerable low-confidence question",
        query_embedding=vec_a,
        answer_text="Should never be stored",
        citations=[],
        top_rerank_score=0.64,
    )
    assert skipped_id is None
    low_conf_lookup = await service.lookup(
        acme_exec, "Unanswerable low-confidence question", vec_a
    )
    assert low_conf_lookup.hit is False

    # Store high-confidence entries across multiple roles for acme_corp + one for globex_corp
    await service.store(
        security_ctx=acme_exec,
        query="Acme executive policy",
        query_embedding=vec_a,
        answer_text="Acme executive policy answer [c1].",
        citations=[_sample_citation(0.88)],
        top_rerank_score=0.88,
    )
    await service.store(
        security_ctx=acme_public,
        query="Acme public FAQ for ERR_409_CONFLICT",
        query_embedding=vec_b,
        answer_text="Acme public FAQ answer [c2].",
        citations=[_sample_citation(0.82)],
        top_rerank_score=0.82,
    )
    await service.store(
        security_ctx=globex_exec,
        query="Globex executive policy",
        query_embedding=vec_a,
        answer_text="Globex executive policy answer [c3].",
        citations=[_sample_citation(0.91)],
        top_rerank_score=0.91,
    )

    deleted = await service.invalidate_tenant("acme_corp")
    assert deleted == 2

    acme_keys = [key async for key in redis_client.scan_iter(match="llm_cache:acme_corp:*")]
    assert acme_keys == []

    assert (await service.lookup(acme_exec, "Acme executive policy", vec_a)).hit is False
    assert (
        await service.lookup(acme_public, "Acme public FAQ for ERR_409_CONFLICT", vec_b)
    ).hit is False

    globex_hit = await service.lookup(globex_exec, "Globex executive policy", vec_a)
    assert globex_hit.hit is True
    assert globex_hit.entry is not None
    assert globex_hit.entry.answer_text == "Globex executive policy answer [c3]."
