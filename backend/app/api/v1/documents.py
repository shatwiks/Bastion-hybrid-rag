from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_security_context
from app.db.models import Document, DocumentChunk
from app.db.session import get_db_session
from app.schemas.auth import SecurityContext
from app.schemas.document import (
    DocumentIngestRequest,
    DocumentIngestResponse,
    DocumentListResponse,
    DocumentSummary,
)
from app.services.ingestion import IngestionService

router = APIRouter()

AUTHORIZED_INGEST_ROLES: frozenset[str] = frozenset({"executive", "support_tier_1", "admin"})


@router.post("/ingest", response_model=DocumentIngestResponse, status_code=status.HTTP_201_CREATED)
async def ingest_document(
    req: DocumentIngestRequest,
    ctx: SecurityContext = Depends(get_security_context),  # noqa: B008
    session: AsyncSession = Depends(get_db_session),  # noqa: B008
) -> DocumentIngestResponse:
    """Ingest a Markdown document with strict pre-retrieval tenant and role RBAC validation."""
    if req.tenant_id != ctx.tenant_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=(
                f"Cross-tenant ingestion forbidden. Token tenant: '{ctx.tenant_id}', "
                f"target tenant: '{req.tenant_id}'"
            ),
        )

    if not set(ctx.allowed_roles).intersection(AUTHORIZED_INGEST_ROLES):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Caller lacks administrative ingestion role permissions.",
        )

    service = IngestionService(session=session)
    try:
        return await service.ingest_document(
            title=req.title,
            content=req.content,
            tenant_id=req.tenant_id,
            allowed_roles=req.allowed_roles,
            doc_metadata=req.doc_metadata,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        ) from exc


@router.get("/documents", response_model=DocumentListResponse)
async def list_documents(
    ctx: SecurityContext = Depends(get_security_context),  # noqa: B008
    session: AsyncSession = Depends(get_db_session),  # noqa: B008
) -> DocumentListResponse:
    """List indexed documents and chunk counts pre-filtered to the caller's tenant_id."""
    stmt = (
        select(
            Document.id,
            Document.title,
            Document.tenant_id,
            Document.doc_metadata,
            Document.created_at,
            func.count(DocumentChunk.id).label("chunks_count"),
        )
        .outerjoin(DocumentChunk, DocumentChunk.document_id == Document.id)
        .where(Document.tenant_id == ctx.tenant_id)
        .group_by(Document.id)
        .order_by(Document.created_at.desc())
    )
    result = await session.execute(stmt)
    rows = result.all()

    documents = [
        DocumentSummary(
            id=str(row.id),
            title=row.title,
            tenant_id=row.tenant_id,
            chunks_count=row.chunks_count,
            doc_metadata=row.doc_metadata,
            created_at=row.created_at,
        )
        for row in rows
    ]
    return DocumentListResponse(documents=documents, total=len(documents))
