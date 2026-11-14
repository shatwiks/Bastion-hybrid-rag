from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from app.schemas.retrieval import ChatMessage
from app.services.query_rewriter import QueryRewriterService, extract_technical_tokens


def _make_llm_response(content: str) -> SimpleNamespace:
    return SimpleNamespace(
        choices=[SimpleNamespace(message=SimpleNamespace(content=content))]
    )


def test_extract_technical_tokens_captures_errors_skus_and_cli_flags() -> None:
    query = (
        "How do I fix ERR_409_CONFLICT on SKU-9921-A when passing --enable-read-replica "
        "and ERR_409_CONFLICT again?"
    )
    tokens = extract_technical_tokens(query)
    assert tokens == ["ERR_409_CONFLICT", "SKU-9921-A", "--enable-read-replica"]


@pytest.mark.asyncio
async def test_turn_1_standalone_bypasses_llm_under_5ms(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    mock_acompletion = AsyncMock()
    monkeypatch.setattr("app.services.query_rewriter.litellm.acompletion", mock_acompletion)

    service = QueryRewriterService(openai_api_key="sk-test-key")
    query = "  How do I resolve ERR_409_CONFLICT on SKU-9921-A?  "
    result = await service.rewrite(query=query, chat_history=None)

    assert result.original_query == query
    assert result.rewritten_query == "How do I resolve ERR_409_CONFLICT on SKU-9921-A?"
    assert result.was_rewritten is False
    assert result.preserved_tokens == ["ERR_409_CONFLICT", "SKU-9921-A"]
    assert result.latency_ms < 5.0
    mock_acompletion.assert_not_awaited()


@pytest.mark.asyncio
async def test_zero_prior_user_turns_bypasses_llm(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    mock_acompletion = AsyncMock()
    monkeypatch.setattr("app.services.query_rewriter.litellm.acompletion", mock_acompletion)

    service = QueryRewriterService(openai_api_key="sk-test-key")
    history = [ChatMessage(role="assistant", content="Hello! Ask me anything about Acme Cloud.")]
    result = await service.rewrite(query="What is SKU-9921-A?", chat_history=history)

    assert result.was_rewritten is False
    assert result.preserved_tokens == ["SKU-9921-A"]
    assert result.latency_ms < 5.0
    mock_acompletion.assert_not_awaited()


@pytest.mark.asyncio
async def test_multi_turn_offline_fallback_merges_prior_user_context(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)

    service = QueryRewriterService(openai_api_key="", gemini_api_key="", anthropic_api_key="")
    history = [
        ChatMessage(
            role="user",
            content="How do I troubleshoot ERR_409_CONFLICT during bucket sync?",
        ),
        ChatMessage(
            role="assistant",
            content="Inspect active leases using acme-storage-cli locks inspect.",
        ),
    ]
    result = await service.rewrite(
        query="What if it persists after releasing the lease?",
        chat_history=history,
    )

    assert result.was_rewritten is True
    assert "ERR_409_CONFLICT" in result.rewritten_query
    assert "persists after releasing the lease" in result.rewritten_query


@pytest.mark.asyncio
async def test_multi_turn_llm_rewrite_and_technical_token_guard(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # Simulate a sloppy LLM that drops all technical identifiers during rewriting
    mock_acompletion = AsyncMock(
        return_value=_make_llm_response(
            "How do I configure read replica failover when encountering the storage lock conflict?"
        )
    )
    monkeypatch.setattr("app.services.query_rewriter.litellm.acompletion", mock_acompletion)

    service = QueryRewriterService(model="gpt-4o-mini", openai_api_key="sk-test-key")
    history = [
        ChatMessage(role="user", content="Tell me about Acme storage lock contention."),
        ChatMessage(role="assistant", content="Lock contention triggers a 409 conflict."),
    ]
    query = "What about ERR_409_CONFLICT on SKU-9921-A with --enable-read-replica?"
    result = await service.rewrite(query=query, chat_history=history)

    mock_acompletion.assert_awaited_once()
    assert result.was_rewritten is True
    assert result.preserved_tokens == ["ERR_409_CONFLICT", "SKU-9921-A", "--enable-read-replica"]
    assert "ERR_409_CONFLICT" in result.rewritten_query
    assert "SKU-9921-A" in result.rewritten_query
    assert "--enable-read-replica" in result.rewritten_query


@pytest.mark.asyncio
async def test_multi_turn_llm_exception_falls_back_gracefully(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    mock_acompletion = AsyncMock(side_effect=RuntimeError("API unreachable"))
    monkeypatch.setattr("app.services.query_rewriter.litellm.acompletion", mock_acompletion)

    service = QueryRewriterService(model="gemini/gemini-2.5-flash", gemini_api_key="gm-test-key")
    history = [
        ChatMessage(role="user", content="How do I check Globex firewall SKU-GLX-500?"),
        ChatMessage(role="assistant", content="Run glx-fw-ctl cert verify."),
    ]
    result = await service.rewrite(
        query="What if ERR_401_SEC_REVOKED occurs with --enable-read-replica?",
        chat_history=history,
    )

    mock_acompletion.assert_awaited_once()
    assert result.was_rewritten is True
    assert "SKU-GLX-500" in result.rewritten_query
    assert "ERR_401_SEC_REVOKED" in result.rewritten_query
    assert "--enable-read-replica" in result.rewritten_query
