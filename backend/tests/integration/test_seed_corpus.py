import json
from collections.abc import AsyncGenerator

import pytest
from sqlalchemy import func, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Document, DocumentChunk
from app.db.session import async_engine, async_session_maker
from app.scripts.seed_corpus import resolve_seed_dir, run_seed

EXPECTED_SEED_TITLES = {
    "acme_corp": {
        "Cloud Storage Overview": ["public", "support_tier_1", "executive"],
        "Storage Troubleshooting Guide": ["support_tier_1", "executive"],
        "Hardware Inventory Skus": ["support_tier_1", "executive"],
        "Q3 Financial Expansion Plan": ["executive"],
    },
    "globex_corp": {
        "Cybersecurity Suite Intro": ["public", "support_tier_1", "executive"],
        "Firewall Error Codes": ["support_tier_1", "executive"],
        "Appliance Skus": ["support_tier_1", "executive"],
        "Acquisition Targets Q4": ["executive"],
    },
}


@pytest.fixture
async def db_session() -> AsyncGenerator[AsyncSession, None]:
    """Yield an async session and dispose engine connections cleanly on teardown."""
    async with async_session_maker() as session:
        yield session
    await async_engine.dispose()


def test_seed_corpus_assets_and_refusal_traps_exist() -> None:
    """Verify 8 Markdown seed files and curated refusal trap fixtures exist on disk."""
    seed_dir = resolve_seed_dir()
    md_files = sorted(seed_dir.glob("*/*/*.md"))
    assert len(md_files) == 8

    traps_path = seed_dir / "refusal_traps" / "topics_inventory.json"
    assert traps_path.is_file()
    traps_data = json.loads(traps_path.read_text(encoding="utf-8"))
    assert len(traps_data["refusal_topics"]) >= 5


@pytest.mark.asyncio
async def test_seed_corpus_execution_rbac_fts_and_idempotency(
    db_session: AsyncSession,
) -> None:
    """Run seed_corpus twice and verify counts, IDs, RBAC tiers, isolation, and FTS."""
    await run_seed()

    # 1. Verify both tenants have all 4 seeded documents and strictly matching RBAC tiers
    seeded_doc_ids: dict[tuple[str, str], object] = {}
    seeded_chunk_counts: dict[str, int] = {}

    for tenant_id, expected_docs in EXPECTED_SEED_TITLES.items():
        docs = (
            await db_session.execute(
                select(Document).where(
                    Document.tenant_id == tenant_id,
                    Document.title.in_(list(expected_docs.keys())),
                )
            )
        ).scalars().all()
        assert len(docs) == len(expected_docs)

        total_chunks = 0
        for doc in docs:
            seeded_doc_ids[(tenant_id, doc.title)] = doc.id
            chunks = (
                await db_session.execute(
                    select(DocumentChunk).where(DocumentChunk.document_id == doc.id)
                )
            ).scalars().all()
            assert len(chunks) >= 1
            total_chunks += len(chunks)

            expected_roles = expected_docs[doc.title]
            for chunk in chunks:
                assert chunk.tenant_id == tenant_id
                assert chunk.allowed_roles == expected_roles
                assert chunk.embedding is not None
                assert len(chunk.embedding) == 384

        seeded_chunk_counts[tenant_id] = total_chunks
        assert total_chunks >= 4

    # 2. Verify cross-tenant isolation in stored documents and chunks
    acme_globex_overlap = (
        await db_session.execute(
            select(func.count(Document.id)).where(
                Document.tenant_id == "acme_corp",
                Document.title.in_(list(EXPECTED_SEED_TITLES["globex_corp"].keys())),
            )
        )
    ).scalar_one()
    assert acme_globex_overlap == 0

    globex_acme_overlap = (
        await db_session.execute(
            select(func.count(Document.id)).where(
                Document.tenant_id == "globex_corp",
                Document.title.in_(list(EXPECTED_SEED_TITLES["acme_corp"].keys())),
            )
        )
    ).scalar_one()
    assert globex_acme_overlap == 0

    # 3. Verify PostgreSQL dual-dictionary FTS matching on concatenated/delimited tokens
    fts_checks = [
        ("acme_corp", "err409conflict"),
        ("acme_corp", "sku9921a"),
        ("globex_corp", "err401secrevoked"),
        ("globex_corp", "skuglx500"),
        ("globex_corp", "enablereadreplica"),
    ]
    for tenant_id, token in fts_checks:
        fts_query = text(
            "SELECT count(*) FROM document_chunks "
            "WHERE tenant_id = :tenant_id "
            "AND tsv_content @@ websearch_to_tsquery('simple', :token)"
        )
        match_count = (
            await db_session.execute(fts_query, {"tenant_id": tenant_id, "token": token})
        ).scalar_one()
        assert match_count >= 1, f"Expected FTS match for '{token}' under '{tenant_id}'"

    # Verify cross-tenant FTS isolation (acme_corp must not match globex_corp token)
    cross_tenant_match = (
        await db_session.execute(
            text(
                "SELECT count(*) FROM document_chunks "
                "WHERE tenant_id = 'acme_corp' "
                "AND tsv_content @@ websearch_to_tsquery('simple', 'err401secrevoked')"
            )
        )
    ).scalar_one()
    assert cross_tenant_match == 0

    # 4. Verify idempotency: running run_seed() again keeps IDs and counts unchanged
    await run_seed()

    for tenant_id, expected_docs in EXPECTED_SEED_TITLES.items():
        docs_rerun = (
            await db_session.execute(
                select(Document).where(
                    Document.tenant_id == tenant_id,
                    Document.title.in_(list(expected_docs.keys())),
                )
            )
        ).scalars().all()
        assert len(docs_rerun) == len(expected_docs)

        rerun_chunk_total = 0
        for doc in docs_rerun:
            assert seeded_doc_ids[(tenant_id, doc.title)] == doc.id
            chunk_count = (
                await db_session.execute(
                    select(func.count(DocumentChunk.id)).where(
                        DocumentChunk.document_id == doc.id
                    )
                )
            ).scalar_one()
            rerun_chunk_total += chunk_count

        assert rerun_chunk_total == seeded_chunk_counts[tenant_id]
