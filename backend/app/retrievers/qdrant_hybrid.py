from qdrant_client import AsyncQdrantClient, models

from app.retrievers.base import RetrievedChunk
from app.schemas.auth import SecurityContext


class QdrantHybridRetriever:
    """Secondary pluggable hybrid retriever adapter backed by Qdrant (STOR-02).

    Enforces pre-retrieval RBAC filtering via Qdrant payload filters prior to RRF fusion.
    """

    def __init__(
        self,
        client: AsyncQdrantClient,
        collection_name: str = "enterprise_rag",
    ) -> None:
        self.client = client
        self.collection_name = collection_name

    async def retrieve_hybrid(
        self,
        security_ctx: SecurityContext,
        query_text: str,
        query_embedding: list[float],
        top_k: int = 25,
    ) -> list[RetrievedChunk]:
        """Execute hybrid search on Qdrant with pre-retrieval RBAC filter and RRF fusion."""
        # Pre-retrieval RBAC filter: must match tenant_id and overlap allowed_roles
        rbac_filter = models.Filter(
            must=[
                models.FieldCondition(
                    key="tenant_id",
                    match=models.MatchValue(value=security_ctx.tenant_id),
                ),
                models.FieldCondition(
                    key="allowed_roles",
                    match=models.MatchAny(any=list(security_ctx.allowed_roles)),
                ),
            ]
        )

        response = await self.client.query_points(
            collection_name=self.collection_name,
            prefetch=[
                models.Prefetch(
                    query=query_embedding,
                    using="dense",
                    filter=rbac_filter,
                    limit=50,
                )
            ],
            query=models.FusionQuery(fusion=models.Fusion.RRF),
            limit=top_k,
        )

        points = getattr(response, "points", response)
        chunks: list[RetrievedChunk] = []

        for idx, point in enumerate(points, start=1):
            payload = getattr(point, "payload", None) or {}
            chunks.append(
                RetrievedChunk(
                    chunk_id=payload.get("chunk_id", str(point.id)),
                    document_id=payload.get("document_id", ""),
                    document_title=payload.get("document_title", ""),
                    section_header=payload.get("section_header", ""),
                    content=payload.get("content", ""),
                    allowed_roles=payload.get("allowed_roles", []),
                    dense_rank=payload.get("dense_rank", idx),
                    dense_score=payload.get("dense_score"),
                    sparse_rank=payload.get("sparse_rank"),
                    sparse_score=payload.get("sparse_score"),
                    rrf_score=float(point.score),
                    rerank_score=payload.get("rerank_score"),
                )
            )

        return chunks
