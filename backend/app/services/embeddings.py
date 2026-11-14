import asyncio
import threading

from sentence_transformers import SentenceTransformer

from app.config import get_settings


class EmbeddingService:
    """Singleton service for non-blocking local dense vector embeddings."""

    def __init__(self, model_name: str | None = None, max_concurrency: int = 4) -> None:
        settings = get_settings()
        self.model_name: str = model_name or settings.EMBEDDING_MODEL or "BAAI/bge-small-en-v1.5"
        self.max_concurrency: int = max_concurrency
        self._model: SentenceTransformer | None = None
        self._semaphore: asyncio.Semaphore = asyncio.Semaphore(max_concurrency)
        self._semaphore_loop: asyncio.AbstractEventLoop | None = None
        self._warmup_lock = threading.Lock()

    @property
    def is_warmed_up(self) -> bool:
        """Return True when the underlying SentenceTransformer weights are loaded."""
        return self._model is not None

    def _get_semaphore(self) -> asyncio.Semaphore:
        """Return a semaphore bound to the active running event loop."""
        loop = asyncio.get_running_loop()
        if self._semaphore_loop is not None and self._semaphore_loop is not loop:
            self._semaphore = asyncio.Semaphore(self.max_concurrency)
        self._semaphore_loop = loop
        return self._semaphore

    def warmup(self) -> None:
        """Synchronously load model weights and run a probe pass during startup."""
        with self._warmup_lock:
            if self._model is None:
                model = SentenceTransformer(self.model_name)
                model.encode(["warmup probe"], normalize_embeddings=True)
                self._model = model

    async def embed_texts(self, texts: list[str]) -> list[list[float]]:
        """Compute 384-dimensional L2-normalized dense embeddings in worker threads."""
        if self._model is None:
            raise RuntimeError(
                "EmbeddingService is not initialized. Call warmup() during application lifespan."
            )
        if not texts:
            return []

        semaphore = self._get_semaphore()
        async with semaphore:
            embeddings = await asyncio.to_thread(
                self._model.encode,
                texts,
                normalize_embeddings=True,
                batch_size=32,
                show_progress_bar=False,
                convert_to_numpy=True,
            )
            return embeddings.tolist()

    async def embed_query(self, query: str) -> list[float]:
        """Compute a single normalized dense embedding vector for a search query."""
        results = await self.embed_texts([query])
        return results[0]


_embedding_service: EmbeddingService | None = None


def get_embedding_service() -> EmbeddingService:
    """Return the process-wide singleton EmbeddingService instance."""
    global _embedding_service
    if _embedding_service is None:
        _embedding_service = EmbeddingService()
    return _embedding_service
