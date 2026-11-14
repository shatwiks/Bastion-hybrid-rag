import asyncio
import hashlib
import logging
from pathlib import Path

from sqlalchemy import func, select

from app.db.models import Document, DocumentChunk
from app.db.session import async_engine, async_session_maker
from app.services.embeddings import get_embedding_service
from app.services.ingestion import IngestionService

logger = logging.getLogger("rag_engine.seed_corpus")

ROLE_TIER_MAPPING: dict[str, list[str]] = {
    "public": ["public", "support_tier_1", "executive"],
    "support_tier_1": ["support_tier_1", "executive"],
    "executive": ["executive"],
}


def resolve_seed_dir() -> Path:
    """Locate the multi-tenant seed/ directory relative to repository or container root."""
    file_path = Path(__file__).resolve()
    candidates = [
        file_path.parents[3] / "seed",
        file_path.parents[2] / "seed",
        Path.cwd() / "seed",
        Path.cwd().parent / "seed",
    ]
    for candidate in candidates:
        if candidate.is_dir():
            return candidate
    raise FileNotFoundError(f"Seed directory not found from {file_path}")


def _compute_content_digest(content: str, allowed_roles: list[str], tier_name: str) -> str:
    """Compute a deterministic hash over file content, tier, and ACL role list."""
    payload = f"{tier_name}|{','.join(allowed_roles)}|{content}".encode()
    return hashlib.sha256(payload).hexdigest()


async def run_seed() -> None:
    """Idempotently ingest all multi-tenant Markdown seed documents into PostgreSQL."""
    embedding_service = get_embedding_service()
    if not embedding_service.is_warmed_up:
        await asyncio.to_thread(embedding_service.warmup)

    seed_dir = resolve_seed_dir()

    try:
        async with async_session_maker() as session:
            service = IngestionService(session=session, embedding_service=embedding_service)

            for tenant_dir in sorted(seed_dir.iterdir()):
                if not tenant_dir.is_dir() or tenant_dir.name == "refusal_traps":
                    continue

                tenant_id = tenant_dir.name
                for role_tier_dir in sorted(tenant_dir.iterdir()):
                    if not role_tier_dir.is_dir():
                        continue

                    tier_name = role_tier_dir.name
                    if tier_name not in ROLE_TIER_MAPPING:
                        raise ValueError(
                            f"Unsupported role tier '{tier_name}' in tenant directory '{tenant_id}'."
                        )
                    allowed_roles = ROLE_TIER_MAPPING[tier_name]

                    for md_file in sorted(role_tier_dir.glob("*.md")):
                        content = md_file.read_text(encoding="utf-8")
                        title = md_file.stem.replace("_", " ").title()
                        digest = _compute_content_digest(content, allowed_roles, tier_name)

                        existing_doc = (
                            await session.execute(
                                select(Document).where(
                                    Document.tenant_id == tenant_id,
                                    Document.title == title,
                                )
                            )
                        ).scalar_one_or_none()

                        if existing_doc is not None and (
                            existing_doc.doc_metadata.get("content_sha256") == digest
                        ):
                            chunk_count = (
                                await session.execute(
                                    select(func.count(DocumentChunk.id)).where(
                                        DocumentChunk.document_id == existing_doc.id
                                    )
                                )
                            ).scalar_one()
                            if chunk_count > 0:
                                logger.info(
                                    "Skipped unchanged seed '%s' (%s/%s) -> %d chunks.",
                                    title,
                                    tenant_id,
                                    tier_name,
                                    chunk_count,
                                )
                                continue

                        resp = await service.ingest_document(
                            title=title,
                            content=content,
                            tenant_id=tenant_id,
                            allowed_roles=allowed_roles,
                            doc_metadata={
                                "file": md_file.name,
                                "tier": tier_name,
                                "content_sha256": digest,
                            },
                        )
                        logger.info(
                            "Seeded '%s' (%s/%s) -> %d chunks.",
                            title,
                            tenant_id,
                            tier_name,
                            resp.chunks_count,
                        )
    finally:
        await async_engine.dispose()


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )
    asyncio.run(run_seed())
