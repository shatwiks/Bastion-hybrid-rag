import logging
import math
import re
import time
import uuid

import redis.asyncio as aioredis

from app.config import get_settings
from app.redis_client import get_redis_client
from app.schemas.auth import SecurityContext
from app.schemas.cache import (
    CachedCitation,
    SemanticCacheEntry,
    SemanticCacheLookupResult,
)
from app.services.query_rewriter import extract_technical_tokens

logger = logging.getLogger("rag_engine.semantic_cache")

_NORMALIZE_DELIMITER_RE = re.compile(r"[-_]+")


def compute_entity_fingerprint(query: str) -> str:
    """Compute a deterministic technical entity fingerprint for cache key partitioning (T-04-02).

    Extracts technical error codes (`ERR_*`), SKUs (`SKU-*`), and CLI flags (`--*`),
    normalizes delimiters to underscores in lowercase, deduplicates, and joins sorted
    tokens with `"|"` (or returns `"none"` when no technical identifiers are present).
    """
    raw_tokens = extract_technical_tokens(query)
    normalized: set[str] = set()
    for token in raw_tokens:
        cleaned = _NORMALIZE_DELIMITER_RE.sub("_", token.lower()).strip("_")
        if cleaned:
            normalized.add(cleaned)

    if not normalized:
        return "none"
    return "|".join(sorted(normalized))


def _l2_normalize(vector: list[float]) -> list[float]:
    """Return an L2-normalized copy of vector, or a zero list copy if norm is zero."""
    norm = math.sqrt(sum(x * x for x in vector))
    if norm == 0.0:
        return [0.0 for _ in vector]
    return [x / norm for x in vector]


def _cosine_similarity(vec_a: list[float], vec_b: list[float]) -> float:
    """Compute cosine similarity between two equal-length vectors, guarding zero norms."""
    if not vec_a or len(vec_a) != len(vec_b):
        return 0.0
    norm_a = math.sqrt(sum(a * a for a in vec_a))
    norm_b = math.sqrt(sum(b * b for b in vec_b))
    if norm_a == 0.0 or norm_b == 0.0:
        return 0.0
    dot = sum(a * b for a, b in zip(vec_a, vec_b, strict=True))
    sim = dot / (norm_a * norm_b)
    return max(-1.0, min(1.0, sim))


class SemanticCacheService:
    """Permission-scoped Redis semantic cache with entity fingerprinting (CACHE-01, CACHE-02)."""

    def __init__(self, redis_client: aioredis.Redis | None = None) -> None:
        self._redis_client = redis_client
        self._settings = get_settings()

    def _acquire_client(self) -> tuple[aioredis.Redis, bool]:
        if self._redis_client is not None:
            return self._redis_client, False
        return get_redis_client(), True

    @staticmethod
    def _build_namespace(
        tenant_id: str,
        scope_hash: str,
        entity_fingerprint: str,
    ) -> str:
        return f"llm_cache:{tenant_id}:{scope_hash}:{entity_fingerprint}"

    async def lookup(
        self,
        security_ctx: SecurityContext,
        query: str,
        query_embedding: list[float],
        similarity_threshold: float = 0.90,
    ) -> SemanticCacheLookupResult:
        """Scan only the caller's permission-and-entity namespace for a semantic cache hit."""
        start = time.perf_counter()
        entity_fp = compute_entity_fingerprint(query)
        namespace = self._build_namespace(
            security_ctx.tenant_id,
            security_ctx.scope_hash,
            entity_fp,
        )
        pattern = f"{namespace}:*"

        client, owns_client = self._acquire_client()
        best_sim = 0.0
        best_entry: SemanticCacheEntry | None = None

        try:
            keys: list[str] = [key async for key in client.scan_iter(match=pattern, count=100)]
            if keys and query_embedding:
                raw_values = await client.mget(keys)
                normalized_query_vec = _l2_normalize(query_embedding)
                has_nonzero_query = any(v != 0.0 for v in normalized_query_vec)

                if has_nonzero_query:
                    for raw in raw_values:
                        if not raw:
                            continue
                        try:
                            entry = SemanticCacheEntry.model_validate_json(raw)
                        except Exception as exc:  # noqa: BLE001
                            logger.warning("Skipping malformed semantic cache entry: %s", exc)
                            continue

                        # Defense-in-depth verification of tenant, RBAC scope, and entity fp (T-04-01/02).
                        if (
                            entry.tenant_id != security_ctx.tenant_id
                            or entry.scope_hash != security_ctx.scope_hash
                            or entry.entity_fingerprint != entity_fp
                        ):
                            continue

                        sim = _cosine_similarity(normalized_query_vec, entry.query_embedding)
                        if best_entry is None or sim > best_sim:
                            best_sim = sim
                            best_entry = entry
        finally:
            if owns_client:
                await client.aclose()

        latency_ms = (time.perf_counter() - start) * 1000.0
        if best_entry is not None and best_sim >= similarity_threshold:
            return SemanticCacheLookupResult(
                hit=True,
                similarity_score=best_sim,
                entry=best_entry,
                latency_ms=latency_ms,
                entity_fingerprint=entity_fp,
            )

        return SemanticCacheLookupResult(
            hit=False,
            similarity_score=max(0.0, best_sim) if best_entry is not None else 0.0,
            entry=None,
            latency_ms=latency_ms,
            entity_fingerprint=entity_fp,
        )

    async def store(
        self,
        security_ctx: SecurityContext,
        query: str,
        query_embedding: list[float],
        answer_text: str,
        citations: list[CachedCitation],
        top_rerank_score: float,
        ttl_seconds: int = 3600,
    ) -> str | None:
        """Persist a verified high-confidence answer inside the caller's scoped Redis namespace.

        Refuses to cache low-confidence or refused responses below `REFUSAL_THRESHOLD`.
        Returns the created `entry_id`, or `None` when skipped by the confidence guard.
        """
        if top_rerank_score < self._settings.REFUSAL_THRESHOLD:
            logger.debug(
                "Skipping semantic cache store for tenant=%s: top_rerank_score=%.4f < %.4f",
                security_ctx.tenant_id,
                top_rerank_score,
                self._settings.REFUSAL_THRESHOLD,
            )
            return None

        if ttl_seconds <= 0:
            raise ValueError("ttl_seconds must be greater than 0")

        entity_fp = compute_entity_fingerprint(query)
        entry_id = uuid.uuid4().hex
        namespace = self._build_namespace(
            security_ctx.tenant_id,
            security_ctx.scope_hash,
            entity_fp,
        )
        redis_key = f"{namespace}:{entry_id}"

        entry = SemanticCacheEntry(
            entry_id=entry_id,
            tenant_id=security_ctx.tenant_id,
            scope_hash=security_ctx.scope_hash,
            entity_fingerprint=entity_fp,
            query_text=query,
            query_embedding=_l2_normalize(query_embedding),
            answer_text=answer_text,
            citations=citations,
            top_rerank_score=top_rerank_score,
            created_at=time.time(),
        )

        client, owns_client = self._acquire_client()
        try:
            await client.set(redis_key, entry.model_dump_json(), ex=ttl_seconds)
        finally:
            if owns_client:
                await client.aclose()

        return entry_id

    async def invalidate_tenant(self, tenant_id: str) -> int:
        """Scan and delete all Redis semantic cache keys belonging to `tenant_id`."""
        pattern = f"llm_cache:{tenant_id}:*"
        client, owns_client = self._acquire_client()
        deleted_count = 0

        try:
            batch: list[str] = []
            async for key in client.scan_iter(match=pattern, count=100):
                batch.append(key)
                if len(batch) >= 100:
                    deleted_count += int(await client.delete(*batch))
                    batch.clear()
            if batch:
                deleted_count += int(await client.delete(*batch))
        finally:
            if owns_client:
                await client.aclose()

        return deleted_count
