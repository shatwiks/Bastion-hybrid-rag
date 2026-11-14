from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_security_context
from app.db.session import get_db_session
from app.retrievers.postgres_hybrid import PostgresHybridRetriever
from app.schemas.auth import SecurityContext
from app.schemas.chat import ChatStreamRequest, PipelineTraceRecord
from app.services.rag_pipeline import RAGPipelineOrchestrator
from app.services.telemetry import TelemetryService, get_telemetry_service

router = APIRouter()


@router.post("/chat/stream")
async def stream_chat(
    req: ChatStreamRequest,
    ctx: SecurityContext = Depends(get_security_context),  # noqa: B008
    session: AsyncSession = Depends(get_db_session),  # noqa: B008
) -> StreamingResponse:
    """Execute the 6-Step RAG Request Lifecycle and stream multiplexed SSE frames."""
    retriever = PostgresHybridRetriever(session=session)
    orchestrator = RAGPipelineOrchestrator(retriever=retriever)
    return StreamingResponse(
        orchestrator.stream_lifecycle(security_ctx=ctx, request=req),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.get("/chat/traces/{trace_id}", response_model=PipelineTraceRecord)
async def get_chat_trace(
    trace_id: str,
    ctx: SecurityContext = Depends(get_security_context),  # noqa: B008
    telemetry: TelemetryService = Depends(get_telemetry_service),  # noqa: B008
) -> PipelineTraceRecord:
    """Retrieve a recorded 6-step pipeline trace scoped strictly to the caller's tenant_id."""
    trace = telemetry.get_trace(trace_id)
    if trace is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Trace '{trace_id}' not found",
        )
    if trace.tenant_id != ctx.tenant_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cross-tenant trace access forbidden",
        )
    return trace
