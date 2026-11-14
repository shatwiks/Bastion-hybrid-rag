from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field, field_validator


class DocumentIngestRequest(BaseModel):
    """Request payload for structure-aware RBAC document ingestion."""

    title: str = Field(..., min_length=1, max_length=512, description="Unique document title per tenant")
    content: str = Field(..., min_length=1, description="Markdown or plain-text document content")
    tenant_id: str = Field(..., min_length=1, max_length=128, description="Target tenant identifier")
    allowed_roles: list[str] = Field(
        ..., min_length=1, description="List of roles authorized to retrieve this document"
    )
    doc_metadata: dict[str, Any] = Field(
        default_factory=dict, description="Optional structured metadata JSON"
    )

    @field_validator("title", "content", "tenant_id")
    @classmethod
    def _reject_blank_strings(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("Field must not be blank or whitespace-only.")
        return value

    @field_validator("allowed_roles")
    @classmethod
    def _validate_roles(cls, value: list[str]) -> list[str]:
        cleaned = [role.strip() for role in value if role and role.strip()]
        if not cleaned:
            raise ValueError("allowed_roles must contain at least one non-empty role.")
        return cleaned


class DocumentChunkSummary(BaseModel):
    """Summary metadata for a single persisted document chunk."""

    chunk_id: str = Field(..., description="Unique chunk UUID string")
    section_header: str = Field(..., description="Leaf Markdown section header for the chunk")
    character_count: int = Field(..., ge=0, description="Character length of stored chunk content")


class DocumentIngestResponse(BaseModel):
    """Response payload returned after successful transactional document ingestion."""

    document_id: str = Field(..., description="Persisted parent document UUID string")
    title: str = Field(..., description="Ingested document title")
    tenant_id: str = Field(..., description="Owning tenant identifier")
    chunks_count: int = Field(..., ge=0, description="Total number of chunks persisted")
    chunks: list[DocumentChunkSummary] = Field(..., description="Ordered list of chunk summaries")


class DocumentSummary(BaseModel):
    """Summary item returned by the tenant-scoped document listing endpoint."""

    id: str = Field(..., description="Document UUID string")
    title: str = Field(..., description="Document title")
    tenant_id: str = Field(..., description="Owning tenant identifier")
    chunks_count: int = Field(..., ge=0, description="Number of indexed chunks")
    doc_metadata: dict[str, Any] = Field(default_factory=dict, description="Document metadata JSON")
    created_at: datetime = Field(..., description="UTC timestamp when document was created")


class DocumentListResponse(BaseModel):
    """Paginated/scoped list of documents belonging to the caller's tenant."""

    documents: list[DocumentSummary] = Field(..., description="Tenant-scoped document summaries")
    total: int = Field(..., ge=0, description="Total number of documents returned")
