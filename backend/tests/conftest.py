from collections.abc import AsyncGenerator

import pytest
from httpx import ASGITransport, AsyncClient

from app.db.session import async_engine
from app.main import app
from app.redis_client import close_redis_pool


@pytest.fixture
async def async_client() -> AsyncGenerator[AsyncClient, None]:
    """Yield an async ASGI test client and dispose DB/Redis pools before loop teardown."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client
    await close_redis_pool()
    await async_engine.dispose()
