import json
from collections.abc import AsyncGenerator
from typing import Any

import pytest
from httpx import AsyncClient

from app.db.session import async_engine
from app.redis_client import close_redis_pool
from app.scripts.seed_corpus import run_seed
from app.services.embeddings import get_embedding_service
from app.services.refusal_gate import VERIFIED_REFUSAL_MESSAGE
from app.services.reranker import get_reranker_service
from app.services.semantic_cache import SemanticCacheService

_SEED_INITIALIZED = False


@pytest.fixture(scope="module", autouse=True)
def warmup_models_once() -> None:
    """Warm up local EmbeddingService and CrossEncoderRerankerService once per module."""
    embedding_service = get_embedding_service()
    if not embedding_service.is_warmed_up:
        embedding_service.warmup()
    reranker_service = get_reranker_service()
    if not reranker_service.is_warmed_up:
        reranker_service.warmup()


@pytest.fixture
async def seeded_cache_clean_env() -> AsyncGenerator[None, None]:
    """Ensure seed corpus is populated and clear test-tenant Redis cache before/after each test."""
    global _SEED_INITIALIZED
    if not _SEED_INITIALIZED:
        await run_seed()
        _SEED_INITIALIZED = True

    cache = SemanticCacheService()
    for tenant in ("acme_corp", "globex_corp"):
        await cache.invalidate_tenant(tenant)

    try:
        yield
    finally:
        for tenant in ("acme_corp", "globex_corp"):
            await cache.invalidate_tenant(tenant)
        await close_redis_pool()
        await async_engine.dispose()


async def _mint_token(async_client: AsyncClient, tenant_id: str, persona: str) -> str:
    resp = await async_client.post(
        "/api/v1/auth/demo-token",
        json={"tenant_id": tenant_id, "persona": persona},
    )
    assert resp.status_code == 200
    return resp.json()["access_token"]


def _parse_sse_frames(raw_body: str) -> list[tuple[str, dict[str, Any]]]:
    """Parse raw `text/event-stream` text into ordered (event_name, json_payload) pairs."""
    frames: list[tuple[str, dict[str, Any]]] = []
    normalized = raw_body.replace("\r\n", "\n")
    for block in normalized.strip().split("\n\n"):
        if not block.strip():
            continue
        event_name = "message"
        data_lines: list[str] = []
        for line in block.splitlines():
            if line.startswith("event:"):
                event_name = line[len("event:") :].strip()
            elif line.startswith("data:"):
                data_lines.append(line[len("data:") :].strip())
        if data_lines:
            payload = json.loads("\n".join(data_lines))
            frames.append((event_name, payload))
    return frames


@pytest.mark.asyncio
async def test_chat_stream_requires_authentication_401(async_client: AsyncClient) -> None:
    """Missing Authorization header returns HTTP 401 before pipeline execution."""
    resp = await async_client.post(
        "/api/v1/chat/stream",
        json={"query": "How do I fix ERR_409_CONFLICT?"},
    )
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_chat_stream_grounded_answer_emits_6_steps_citations_and_trace(
    async_client: AsyncClient,
    seeded_cache_clean_env: None,
) -> None:
    """In-scope query emits all 6 step_update events, [chunk_id] tokens, citations, done, and trace."""
    support_token = await _mint_token(async_client, "acme_corp", "support_tier_1")
    globex_token = await _mint_token(async_client, "globex_corp", "executive")

    async with async_client.stream(
        "POST",
        "/api/v1/chat/stream",
        json={"query": "How do I fix ERR_409_CONFLICT?"},
        headers={"Authorization": f"Bearer {support_token}"},
    ) as resp:
        assert resp.status_code == 200
        assert resp.headers["content-type"].startswith("text/event-stream")
        body = (await resp.aread()).decode("utf-8")

    frames = _parse_sse_frames(body)
    event_names = [name for name, _ in frames]
    assert "step_update" in event_names
    assert "token" in event_names
    assert "citations" in event_names
    assert "refusal" not in event_names
    assert event_names[-1] == "done"

    step_updates = [payload for name, payload in frames if name == "step_update"]
    assert {s["step"] for s in step_updates} == {1, 2, 3, 4, 5, 6}
    final_steps = {s["step"]: s for s in step_updates}
    for step_num in range(1, 7):
        assert final_steps[step_num]["status"] == "completed"

    assert final_steps[3]["details"]["candidate_count"] > 0
    assert final_steps[4]["details"]["top_rerank_score"] >= 0.65

    tokens = [payload["delta"] for name, payload in frames if name == "token"]
    full_answer = "".join(tokens)
    citations_payload = next(payload for name, payload in frames if name == "citations")
    citations = citations_payload["citations"]
    assert 1 <= len(citations) <= 5
    assert any(f"[{c['chunk_id']}]" in full_answer for c in citations)

    done_payload = frames[-1][1]
    assert done_payload["refused"] is False
    assert done_payload["llm_called"] is True
    assert done_payload["cache_hit"] is False
    trace_id = done_payload["trace_id"]

    # Trace inspection endpoint returns 6-step record for acme_corp, rejects globex_corp with 403
    trace_resp = await async_client.get(
        f"/api/v1/chat/traces/{trace_id}",
        headers={"Authorization": f"Bearer {support_token}"},
    )
    assert trace_resp.status_code == 200
    trace_data = trace_resp.json()
    assert trace_data["trace_id"] == trace_id
    assert trace_data["tenant_id"] == "acme_corp"
    assert trace_data["cache_hit"] is False
    assert trace_data["refused"] is False
    assert trace_data["llm_called"] is True
    assert len(trace_data["steps"]) == 6

    forbidden_resp = await async_client.get(
        f"/api/v1/chat/traces/{trace_id}",
        headers={"Authorization": f"Bearer {globex_token}"},
    )
    assert forbidden_resp.status_code == 403


@pytest.mark.asyncio
async def test_chat_stream_repeat_query_hits_permission_scoped_semantic_cache(
    async_client: AsyncClient,
    seeded_cache_clean_env: None,
) -> None:
    """Repeating an identical query under the same persona hits Redis semantic cache (llm_called=False)."""
    token = await _mint_token(async_client, "acme_corp", "support_tier_1")
    query = "How do I fix ERR_409_CONFLICT?"

    # First call populates cache
    first_resp = await async_client.post(
        "/api/v1/chat/stream",
        json={"query": query},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert first_resp.status_code == 200
    first_frames = _parse_sse_frames(first_resp.text)
    first_done = first_frames[-1][1]
    assert first_done["cache_hit"] is False
    assert first_done["llm_called"] is True
    first_answer = "".join(p["delta"] for n, p in first_frames if n == "token")

    # Second call short-circuits at Step 2
    second_resp = await async_client.post(
        "/api/v1/chat/stream",
        json={"query": query},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert second_resp.status_code == 200
    second_frames = _parse_sse_frames(second_resp.text)
    second_done = second_frames[-1][1]
    assert second_done["cache_hit"] is True
    assert second_done["llm_called"] is False
    assert second_done["refused"] is False

    second_steps = {
        p["step"]: p for n, p in second_frames if n == "step_update"
    }
    assert second_steps[2]["status"] == "short_circuited"
    assert second_steps[2]["details"]["cache_hit"] is True
    assert second_steps[3]["status"] == "skipped"
    assert second_steps[4]["status"] == "skipped"
    assert second_steps[5]["status"] == "skipped"
    assert second_steps[6]["status"] == "completed"

    second_answer = "".join(p["delta"] for n, p in second_frames if n == "token")
    assert second_answer == first_answer
    assert any(n == "citations" for n, _ in second_frames)


@pytest.mark.asyncio
async def test_chat_stream_different_role_persona_does_not_hit_executive_cache(
    async_client: AsyncClient,
    seeded_cache_clean_env: None,
) -> None:
    """Public persona asking the same executive query never hits executive cache and is refused."""
    exec_token = await _mint_token(async_client, "acme_corp", "executive")
    public_token = await _mint_token(async_client, "acme_corp", "public")
    exec_query = "What is the stretch ceiling bid for Project Nimbus in Q3?"

    # 1. Executive user gets grounded answer and populates executive-scoped cache
    exec_resp = await async_client.post(
        "/api/v1/chat/stream",
        json={"query": exec_query},
        headers={"Authorization": f"Bearer {exec_token}"},
    )
    assert exec_resp.status_code == 200
    exec_frames = _parse_sse_frames(exec_resp.text)
    exec_done = exec_frames[-1][1]
    assert exec_done["cache_hit"] is False
    assert exec_done["refused"] is False
    assert exec_done["llm_called"] is True
    exec_answer = "".join(p["delta"] for n, p in exec_frames if n == "token")
    assert "Project Nimbus" in exec_answer or "$165,000,000" in exec_answer

    # 2. Public user asking identical query MUST miss executive cache and trigger RBAC refusal
    public_resp = await async_client.post(
        "/api/v1/chat/stream",
        json={"query": exec_query},
        headers={"Authorization": f"Bearer {public_token}"},
    )
    assert public_resp.status_code == 200
    public_frames = _parse_sse_frames(public_resp.text)
    public_events = [n for n, _ in public_frames]
    assert "refusal" in public_events
    assert "token" not in public_events

    public_done = public_frames[-1][1]
    assert public_done["cache_hit"] is False
    assert public_done["refused"] is True
    assert public_done["llm_called"] is False

    refusal_payload = next(p for n, p in public_frames if n == "refusal")
    assert refusal_payload["refused"] is True
    assert refusal_payload["message"] == VERIFIED_REFUSAL_MESSAGE


@pytest.mark.asyncio
async def test_chat_stream_out_of_domain_query_triggers_refusal_gate(
    async_client: AsyncClient,
    seeded_cache_clean_env: None,
) -> None:
    """Out-of-domain refusal-trap query triggers Step 4 Refusal Gate with llm_called=False."""
    token = await _mint_token(async_client, "acme_corp", "public")
    ood_query = "What are the safety protocols for stabilizing a quantum wormhole teleportation ring?"

    resp = await async_client.post(
        "/api/v1/chat/stream",
        json={"query": ood_query},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    frames = _parse_sse_frames(resp.text)
    event_names = [name for name, _ in frames]
    assert "refusal" in event_names
    assert "token" not in event_names
    assert "citations" not in event_names
    assert event_names[-1] == "done"

    steps = {p["step"]: p for n, p in frames if n == "step_update"}
    assert steps[4]["status"] == "short_circuited"
    assert steps[4]["details"]["should_refuse"] is True
    assert steps[4]["details"]["top_rerank_score"] < 0.65
    assert steps[5]["status"] == "skipped"
    assert steps[6]["status"] == "completed"

    refusal_payload = next(p for n, p in frames if n == "refusal")
    assert refusal_payload["refused"] is True
    assert refusal_payload["message"] == VERIFIED_REFUSAL_MESSAGE
    assert refusal_payload["threshold"] == pytest.approx(0.65)

    done_payload = frames[-1][1]
    assert done_payload["refused"] is True
    assert done_payload["llm_called"] is False
    assert done_payload["cache_hit"] is False
