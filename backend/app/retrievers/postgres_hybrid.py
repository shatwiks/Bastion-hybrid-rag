from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.retrievers.base import RetrievedChunk
from app.schemas.auth import SecurityContext

HYBRID_RRF_SQL = text("""
WITH rbac_pool AS NOT MATERIALIZED (
    SELECT
        c.id AS chunk_id,
        c.document_id,
        d.title AS document_title,
        c.section_header,
        c.content,
        c.allowed_roles,
        c.embedding,
        c.tsv_content
    FROM document_chunks c
    JOIN documents d ON d.id = c.document_id
    WHERE c.tenant_id = :tenant_id
      AND c.allowed_roles && :user_roles
),
parsed_query AS (
    SELECT
        CASE
            WHEN s_tsq IS NOT NULL AND e_tsq IS NOT NULL THEN s_tsq || e_tsq
            ELSE COALESCE(s_tsq, e_tsq)
        END AS tsq
    FROM (
        SELECT
            regexp_replace(
                NULLIF(plainto_tsquery('simple', :query_text)::text, ''),
                ' & ',
                ' | ',
                'g'
            )::tsquery AS s_tsq,
            regexp_replace(
                NULLIF(plainto_tsquery('english', :query_text)::text, ''),
                ' & ',
                ' | ',
                'g'
            )::tsquery AS e_tsq
    ) q
),
dense_candidates AS (
    SELECT
        chunk_id,
        1.0 - (embedding <=> CAST(:query_embedding AS vector)) AS dense_score,
        ROW_NUMBER() OVER (ORDER BY embedding <=> CAST(:query_embedding AS vector) ASC) AS dense_rank
    FROM rbac_pool
    ORDER BY embedding <=> CAST(:query_embedding AS vector) ASC
    LIMIT :candidate_pool_size
),
sparse_candidates AS (
    SELECT
        p.chunk_id,
        ts_rank_cd(p.tsv_content, pq.tsq) AS sparse_score,
        ROW_NUMBER() OVER (
            ORDER BY ts_rank_cd(p.tsv_content, pq.tsq) DESC
        ) AS sparse_rank
    FROM rbac_pool p
    CROSS JOIN parsed_query pq
    WHERE pq.tsq IS NOT NULL
      AND p.tsv_content @@ pq.tsq
    ORDER BY sparse_score DESC
    LIMIT :candidate_pool_size
),
rrf_fused AS (
    SELECT
        COALESCE(d.chunk_id, s.chunk_id) AS chunk_id,
        d.dense_rank,
        d.dense_score,
        s.sparse_rank,
        s.sparse_score,
        COALESCE(1.0 / (:rrf_k + d.dense_rank), 0.0) +
        COALESCE(1.0 / (:rrf_k + s.sparse_rank), 0.0) AS rrf_score
    FROM dense_candidates d
    FULL OUTER JOIN sparse_candidates s ON d.chunk_id = s.chunk_id
)
SELECT
    p.chunk_id,
    p.document_id,
    p.document_title,
    p.section_header,
    p.content,
    p.allowed_roles,
    f.dense_rank,
    f.dense_score,
    f.sparse_rank,
    f.sparse_score,
    f.rrf_score
FROM rrf_fused f
JOIN rbac_pool p ON p.chunk_id = f.chunk_id
ORDER BY f.rrf_score DESC
LIMIT :top_k;
""")


class PostgresHybridRetriever:
    """Production PostgreSQL hybrid retriever with pre-retrieval RBAC and iterative HNSW scans."""

    def __init__(
        self,
        session: AsyncSession,
        rrf_k: int = 60,
        candidate_pool_size: int = 50,
    ) -> None:
        self.session = session
        self.rrf_k = rrf_k
        self.candidate_pool_size = candidate_pool_size

    async def retrieve_hybrid(
        self,
        security_ctx: SecurityContext,
        query_text: str,
        query_embedding: list[float],
        top_k: int = 25,
    ) -> list[RetrievedChunk]:
        """Execute hybrid search enforcing pre-retrieval RBAC filtering in SQL."""
        # Enable iterative HNSW index scanning within the transaction to eliminate
        # recall collapse under selective RBAC filters (SEC-03)
        await self.session.execute(text("SET LOCAL hnsw.iterative_scan = 'relaxed_order'"))
        await self.session.execute(text("SET LOCAL hnsw.ef_search = 80"))

        result = await self.session.execute(
            HYBRID_RRF_SQL,
            {
                "tenant_id": security_ctx.tenant_id,
                "user_roles": list(security_ctx.allowed_roles),
                "query_text": query_text,
                "query_embedding": str(query_embedding),
                "candidate_pool_size": self.candidate_pool_size,
                "rrf_k": self.rrf_k,
                "top_k": top_k,
            },
        )
        rows = result.fetchall()
        return [RetrievedChunk(**dict(row._mapping)) for row in rows]
