import asyncio
import logging
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.v1 import api_router
from app.api.v1.auth import auth_router
from app.config import get_settings
from app.db import check_database_connection, engine
from app.redis_client import check_redis_connection, close_redis_pool
from app.services.embeddings import get_embedding_service
from app.services.reranker import get_reranker_service

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

    # Pre-warm local Cross-Encoder reranker model weights before accepting traffic
    try:
        reranker_service = get_reranker_service()
        await asyncio.to_thread(reranker_service.warmup)
        logger.info(
            "Local CrossEncoderRerankerService pre-warmed model '%s'.",
            reranker_service.model_name,
        )
    except Exception as exc:  # noqa: BLE001
        logger.error("Failed to pre-warm CrossEncoderRerankerService: %s", exc)

    yield

    # Graceful shutdown
    logger.info("Shutting down RAG Engine resources...")
    await close_redis_pool()
    await engine.dispose()
    logger.info("Resources cleaned up successfully.")


_is_prod = settings.ENVIRONMENT.lower() == "production"
_docs_enabled = settings.ENABLE_DOCS and not _is_prod

app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    description="Enterprise Multi-Tenant RAG Knowledge Engine API with pre-retrieval RBAC security.",
    docs_url="/docs" if _docs_enabled else None,
    redoc_url="/redoc" if _docs_enabled else None,
    openapi_url="/openapi.json" if _docs_enabled else None,
    lifespan=lifespan,
)


@app.middleware("http")
async def security_headers_middleware(request: Request, call_next):
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
    if _is_prod:
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains; preload"
    return response


@app.exception_handler(Exception)
async def sanitized_exception_handler(request: Request, exc: Exception):
    logger.error("Unhandled exception on %s %s: %s", request.method, request.url.path, type(exc).__name__)
    return JSONResponse(status_code=500, content={"detail": "Internal server error."})


# Strict CORS configuration (never allow wildcard '*' with credentials)
_cors_origins = settings.CORS_ORIGINS if isinstance(settings.CORS_ORIGINS, list) else [settings.CORS_ORIGINS]
app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins,
    allow_credentials="*" not in _cors_origins,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "X-Request-ID", "Accept"],
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
