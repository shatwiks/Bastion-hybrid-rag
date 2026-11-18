import os
from dataclasses import dataclass
from typing import Any, Literal

from app.config import Settings, get_settings

LLMProviderName = Literal["openai", "gemini", "anthropic", "ollama", "offline"]


@dataclass(frozen=True)
class ResolvedLLMTarget:
    """Resolved LiteLLM call target across Cloud APIs, local Ollama, and offline fallback."""

    enabled: bool
    provider: LLMProviderName
    model: str
    api_key: str | None = None
    api_base: str | None = None

    def acompletion_kwargs(self) -> dict[str, Any]:
        """Build provider-specific keyword arguments for litellm.acompletion."""
        kwargs: dict[str, Any] = {"model": self.model}
        if self.api_key:
            kwargs["api_key"] = self.api_key
        if self.api_base:
            kwargs["api_base"] = self.api_base
        return kwargs


def _pick_setting(explicit: str | None, env_var: str, default: str | None) -> str | None:
    """Resolve an optional string config checking explicit override, env, then Settings."""
    raw = explicit if explicit is not None else (os.environ.get(env_var) or default)
    if raw is None:
        return None
    cleaned = raw.strip()
    return cleaned or None


def resolve_llm_target(
    model: str,
    *,
    openai_api_key: str | None = None,
    gemini_api_key: str | None = None,
    anthropic_api_key: str | None = None,
    ollama_api_base: str | None = None,
    ollama_api_key: str | None = None,
    settings: Settings | None = None,
) -> ResolvedLLMTarget:
    """Resolve Cloud LLM or local Ollama connection details for LiteLLM."""
    cfg = settings or get_settings()
    model_lower = model.strip().lower()

    if model_lower.startswith(("ollama/", "ollama_chat/")):
        resolved_base = _pick_setting(ollama_api_base, "OLLAMA_API_BASE", cfg.OLLAMA_API_BASE)
        if not resolved_base:
            return ResolvedLLMTarget(enabled=False, provider="offline", model=model)
        resolved_key = _pick_setting(ollama_api_key, "OLLAMA_API_KEY", cfg.OLLAMA_API_KEY)
        return ResolvedLLMTarget(
            enabled=True,
            provider="ollama",
            model=model.strip(),
            api_key=resolved_key,
            api_base=resolved_base.rstrip("/"),
        )

    if "gemini" in model_lower:
        key = _pick_setting(gemini_api_key, "GEMINI_API_KEY", cfg.GEMINI_API_KEY)
        return ResolvedLLMTarget(
            enabled=bool(key),
            provider="gemini" if key else "offline",
            model=model,
            api_key=key,
        )

    if "claude" in model_lower or "anthropic" in model_lower:
        key = _pick_setting(anthropic_api_key, "ANTHROPIC_API_KEY", cfg.ANTHROPIC_API_KEY)
        return ResolvedLLMTarget(
            enabled=bool(key),
            provider="anthropic" if key else "offline",
            model=model,
            api_key=key,
        )

    key = _pick_setting(openai_api_key, "OPENAI_API_KEY", cfg.OPENAI_API_KEY)
    return ResolvedLLMTarget(
        enabled=bool(key),
        provider="openai" if key else "offline",
        model=model,
        api_key=key,
    )
