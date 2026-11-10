from fastapi import APIRouter
from pydantic import BaseModel

from app.config import get_settings
from app.db import check_database_connection
from app.redis_client import check_redis_connection

router = APIRouter()
settings = get_settings()


class HealthResponse(BaseModel):
    status: str
    postgres: str
    redis: str
    version: str


@router.get("/health", response_model=HealthResponse)
async def health_check() -> HealthResponse:
    postgres_ok = await check_database_connection()
    redis_ok = await check_redis_connection()

    postgres_status = "connected" if postgres_ok else "disconnected"
    redis_status = "connected" if redis_ok else "disconnected"

    overall_status = "ok" if (postgres_ok and redis_ok) else "degraded"

    return HealthResponse(
        status=overall_status,
        postgres=postgres_status,
        redis=redis_status,
        version=settings.VERSION,
    )
