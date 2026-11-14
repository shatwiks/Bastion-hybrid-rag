import asyncio
import logging
import uuid
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Document, DocumentChunk
from app.redis_client import get_redis_client
from app.schemas.document import DocumentChunkSummary, DocumentIngestResponse
from app.services.embeddings import EmbeddingService, get_embedding_service
from app.services.text_splitter import split_markdown_document
from app.services.token_expansion import append_search_index_tokens

logger = logging.getLogger("rag_engine.ingestion")


class IngestionService:
    """Orchestrates chunking, token expansion, dense vectorization, and transactional DB storage."""

    def __init__(
        self,
        session: AsyncSession,
        embedding_service: EmbeddingService | None = None,
    ) -> None:
        self.session = session
        self.embedding_service = embedding_service or get_embedding_service()

    async def ingest_document(
        self,
        title: str,
        content: str,
        tenant_id: str,
        allowed_roles: list[str],
        doc_metadata: dict[str, Any] | None = None,
    ) -> DocumentIngestResponse:
        """Idempotently ingest a Markdown document and invalidate tenant semantic cache."""
        # 1. Structure-aware Markdown splitting
        raw_chunks = split_markdown_document(title=title, content=content)
        if not raw_chunks:
            raise ValueError("Document content produced zero indexable chunks.")

        # 2. Ensure embedding model is warmed up (supports ASGI test transports without lifespan)
        if not self.embedding_service.is_warmed_up:
            await asyncio.to_thread(self.embedding_service.warmup)

        # 3. Assemble breadcrumb-prefixed content with plain-text search index tokens
        chunk_texts_for_embed: list[str] = []
        final_chunk_payloads: list[dict[str, str]] = []
        for chunk in raw_chunks:
            assembled = f"{chunk['breadcrumb']}\n\n{chunk['body']}"
            final_content = append_search_index_tokens(assembled)
            chunk_texts_for_embed.append(final_content)
            final_chunk_payloads.append(
                {
                    "section_header": str(chunk["section_header"])[:512],
                    "content": final_content,
                }
            )

        # 4. Compute 384-dim L2-normalized embeddings in non-blocking worker threads
        embeddings = await self.embedding_service.embed_texts(chunk_texts_for_embed)

        # 5. Idempotent replacement for existing document with same (tenant_id, title)
        existing_stmt = select(Document).where(
            Document.tenant_id == tenant_id,
            Document.title == title,
        )
        existing_result = await self.session.execute(existing_stmt)
        for existing_doc in existing_result.scalars().all():
            await self.session.delete(existing_doc)
        await self.session.flush()

        # 6. Persist parent Document and child DocumentChunks atomically
        normalized_roles = list(dict.fromkeys(allowed_roles))
        doc = Document(
            id=uuid.uuid4(),
            title=title,
            tenant_id=tenant_id,
            doc_metadata=doc_metadata or {},
        )
        self.session.add(doc)

        chunk_models: list[DocumentChunk] = []
        chunk_summaries: list[DocumentChunkSummary] = []
        for payload, emb in zip(final_chunk_payloads, embeddings, strict=True):
            chunk_id = uuid.uuid4()
            chunk_models.append(
                DocumentChunk(
                    id=chunk_id,
                    document_id=doc.id,
                    tenant_id=tenant_id,
                    section_header=payload["section_header"],
                    content=payload["content"],
                    allowed_roles=normalized_roles,
                    embedding=emb,
                )
            )
            chunk_summaries.append(
                DocumentChunkSummary(
                    chunk_id=str(chunk_id),
                    section_header=payload["section_header"],
                    character_count=len(payload["content"]),
                )
            )

        self.session.add_all(chunk_models)
        await self.session.commit()

        # 7. Invalidate tenant Redis semantic cache keys
        await self._invalidate_tenant_cache(tenant_id)

        return DocumentIngestResponse(
            document_id=str(doc.id),
            title=doc.title,
            tenant_id=doc.tenant_id,
            chunks_count=len(chunk_models),
            chunks=chunk_summaries,
        )

    async def _invalidate_tenant_cache(self, tenant_id: str) -> None:
        """Scan and delete Redis semantic cache entries scoped to tenant_id."""
        redis = get_redis_client()
        try:
            pattern = f"llm_cache:{tenant_id}:*"
            cursor = 0
            while True:
                cursor, keys = await redis.scan(cursor=cursor, match=pattern, count=100)
                if keys:
                    await redis.delete(*keys)
                if cursor == 0:
                    break
        except Exception as exc:  # noqa: BLE001
            logger.warning(
                "Redis cache invalidation skipped for tenant '%s': %s", tenant_id, exc
            )
        finally:
            await redis.aclose()
