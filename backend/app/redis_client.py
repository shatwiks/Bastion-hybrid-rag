import redis.asyncio as aioredis

from app.config import get_settings

settings = get_settings()

redis_pool: aioredis.ConnectionPool | None = None


def get_redis_pool() -> aioredis.ConnectionPool:
    global redis_pool
    if redis_pool is None:
        redis_pool = aioredis.ConnectionPool.from_url(
            settings.REDIS_URL,
            decode_responses=True,
            max_connections=20,
        )
    return redis_pool


def get_redis_client() -> aioredis.Redis:
    pool = get_redis_pool()
    return aioredis.Redis(connection_pool=pool)


async def check_redis_connection() -> bool:
    client = get_redis_client()
    try:
        response = await client.ping()
        return bool(response)
    except Exception:  # noqa: BLE001
        return False
    finally:
        await client.aclose()


async def close_redis_pool() -> None:
    global redis_pool
    if redis_pool is not None:
        await redis_pool.disconnect()
        redis_pool = None
