import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_health_check_returns_200_ok(async_client: AsyncClient):
    """Verify that GET /api/v1/health returns 200 with healthy postgres and redis statuses."""
    response = await async_client.get("/api/v1/health")
    assert response.status_code == 200

    payload = response.json()
    assert "status" in payload
    assert "postgres" in payload
    assert "redis" in payload
    assert "version" in payload

    assert payload["status"] == "ok"
    assert payload["postgres"] == "connected"
    assert payload["redis"] == "connected"
    assert payload["version"] == "1.0.0"


@pytest.mark.asyncio
async def test_root_endpoint_returns_200(async_client: AsyncClient):
    """Verify that GET / returns 200 and points to documentation and health check."""
    response = await async_client.get("/")
    assert response.status_code == 200

    payload = response.json()
    assert payload["health"] == "/api/v1/health"
    assert "version" in payload
