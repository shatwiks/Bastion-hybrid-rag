import asyncio
import logging
from collections import deque
from typing import Any

from langfuse import Langfuse

from app.config import get_settings
from app.schemas.chat import PipelineTraceRecord

logger = logging.getLogger("rag_engine.telemetry")

_STEP_OBSERVATION_TYPES: dict[str, str] = {
    "auth_guardrail": "guardrail",
    "semantic_cache": "retriever",
    "hybrid_retrieval": "retriever",
    "rerank_gate": "evaluator",
    "grounded_generation": "generation",
    "telemetry_commit": "span",
}


class TelemetryService:
    """Non-blocking 6-step pipeline trace recorder backed by Langfuse v5 and a bounded ring buffer (OBS-01)."""

    def __init__(
        self,
        max_traces: int = 200,
        public_key: str | None = None,
        secret_key: str | None = None,
        host: str | None = None,
        langfuse_client: Any | None = None,
    ) -> None:
        settings = get_settings()
        self._traces: deque[PipelineTraceRecord] = deque(maxlen=max_traces)
        self._public_key = (
            public_key if public_key is not None else settings.LANGFUSE_PUBLIC_KEY
        )
        self._secret_key = (
            secret_key if secret_key is not None else settings.LANGFUSE_SECRET_KEY
        )
        self._host = host if host is not None else settings.LANGFUSE_HOST
        self._langfuse_client: Any | None = langfuse_client
        self._background_tasks: set[asyncio.Task[None]] = set()

    @property
    def langfuse_enabled(self) -> bool:
        """Return True when external Langfuse export is active (explicit client or credentials)."""
        if self._langfuse_client is not None:
            return True
        return bool(
            self._public_key
            and self._public_key.strip()
            and self._secret_key
            and self._secret_key.strip()
        )

    def _get_langfuse_client(self) -> Any | None:
        if self._langfuse_client is not None:
            return self._langfuse_client
        if not self.langfuse_enabled:
            return None
        try:
            self._langfuse_client = Langfuse(
                public_key=self._public_key,
                secret_key=self._secret_key,
                host=self._host,
            )
            return self._langfuse_client
        except Exception as exc:  # noqa: BLE001
            logger.warning("Failed to initialize Langfuse client; using local ring buffer: %s", exc)
            return None

    def _emit_langfuse_sync(self, client: Any, trace: PipelineTraceRecord) -> None:
        """Emit root chain span and 6 child step spans via Langfuse SDK v5."""
        with client.start_as_current_observation(
            name="rag_pipeline_request",
            as_type="chain",
            input={
                "original_query": trace.original_query,
                "rewritten_query": trace.rewritten_query,
            },
            output={
                "cache_hit": trace.cache_hit,
                "refused": trace.refused,
                "refusal_reason": trace.refusal_reason,
                "llm_called": trace.llm_called,
                "citation_count": len(trace.citations),
            },
            metadata={
                "trace_id": trace.trace_id,
                "tenant_id": trace.tenant_id,
                "scope_hash": trace.scope_hash,
                "entity_fingerprint": trace.entity_fingerprint,
                "cache_similarity": trace.cache_similarity,
                "top_rerank_score": trace.top_rerank_score,
                "total_latency_ms": trace.total_latency_ms,
            },
        ):
            for step in trace.steps:
                as_type: Any = _STEP_OBSERVATION_TYPES.get(step.name, "span")
                kwargs: dict[str, Any] = {
                    "name": step.name,
                    "as_type": as_type,
                    "metadata": {
                        "step": step.step,
                        "label": step.label,
                        "status": step.status,
                        "latency_ms": step.latency_ms,
                        **step.details,
                    },
                }
                if step.name == "grounded_generation" and trace.token_usage:
                    kwargs["usage_details"] = trace.token_usage
                with client.start_as_current_observation(**kwargs):
                    pass

        flush_fn = getattr(client, "flush", None)
        if callable(flush_fn):
            flush_fn()

    async def _emit_langfuse_async(self, trace: PipelineTraceRecord) -> None:
        client = self._get_langfuse_client()
        if client is None:
            return
        try:
            await asyncio.to_thread(self._emit_langfuse_sync, client, trace)
        except Exception as exc:  # noqa: BLE001
            logger.warning("Non-blocking Langfuse trace export failed: %s", exc)

    async def record_trace(self, trace: PipelineTraceRecord) -> None:
        """Store trace in the bounded ring buffer immediately and schedule async Langfuse export."""
        self._traces.append(trace)
        if self.langfuse_enabled:
            task = asyncio.create_task(self._emit_langfuse_async(trace))
            self._background_tasks.add(task)
            task.add_done_callback(self._background_tasks.discard)

    def get_trace(self, trace_id: str) -> PipelineTraceRecord | None:
        """Retrieve a recorded trace by trace_id from the bounded ring buffer."""
        for trace in reversed(self._traces):
            if trace.trace_id == trace_id:
                return trace
        return None

    def list_traces(
        self,
        tenant_id: str | None = None,
        limit: int = 50,
    ) -> list[PipelineTraceRecord]:
        """Return recent traces (newest first), optionally filtered by tenant_id."""
        results: list[PipelineTraceRecord] = []
        for trace in reversed(self._traces):
            if tenant_id is not None and trace.tenant_id != tenant_id:
                continue
            results.append(trace)
            if len(results) >= limit:
                break
        return results

    async def flush_pending(self) -> None:
        """Await any in-flight background Langfuse export tasks (primarily for tests)."""
        if self._background_tasks:
            await asyncio.gather(*list(self._background_tasks), return_exceptions=True)


_telemetry_service: TelemetryService | None = None


def get_telemetry_service() -> TelemetryService:
    """Return the process-wide singleton TelemetryService instance."""
    global _telemetry_service
    if _telemetry_service is None:
        _telemetry_service = TelemetryService()
    return _telemetry_service
