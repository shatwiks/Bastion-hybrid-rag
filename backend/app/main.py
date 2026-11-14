import asyncio
import logging
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1 import api_router
from app.api.v1.auth import auth_router
from app.config import get_settings
from app.db import check_database_connection, engine
from app.redis_client import check_redis_connection, close_redis_pool
from app.services.embeddings import get_embedding_service

logger = logging.getLogger("rag_engine")
settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    logger.info("Initializing Enterprise Multi-Tenant RAG Engine...")

    # Startup connection validation
    db_ok = await check_database_connection()
    if db_ok:
        logger.info("PostgreSQL connection verified via asyncpg.")
    else:
        logger.warning("PostgreSQL connection check failed during startup.")

    redis_ok = await check_redis_connection()
    if redis_ok:
        logger.info("Redis 8 connection verified via aioredis.")
    else:
        logger.warning("Redis connection check failed during startup.")

    # Pre-warm local embedding model weights before accepting traffic
    try:
        embedding_service = get_embedding_service()
        await asyncio.to_thread(embedding_service.warmup)
        logger.info("Local EmbeddingService pre-warmed model '%s'.", embedding_service.model_name)
    except Exception as exc:  # noqa: BLE001
        logger.error("Failed to pre-warm EmbeddingService: %s", exc)

    yield

    # Graceful shutdown
    logger.info("Shutting down RAG Engine resources...")
    await close_redis_pool()
    await engine.dispose()
    logger.info("Resources cleaned up successfully.")


app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    description="Enterprise Multi-Tenant RAG Knowledge Engine API with pre-retrieval RBAC security.",
    lifespan=lifespan,
)

# CORS configuration for Next.js frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://localhost:3005",
        "http://127.0.0.1:3000",
        "http://127.0.0.1:3005",
        "*",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount API routers
app.include_router(api_router, prefix="/api/v1")
app.include_router(auth_router, prefix="/api/v1/auth", tags=["auth"])


@app.get("/")
async def root():
    return {
        "service": settings.PROJECT_NAME,
        "version": settings.VERSION,
        "docs": "/docs",
        "health": "/api/v1/health",
    }
