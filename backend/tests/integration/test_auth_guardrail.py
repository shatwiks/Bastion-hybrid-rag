from datetime import timedelta

import jwt
import pytest
from httpx import AsyncClient

from app.config import get_settings
from app.core.security import compute_scope_hash, create_access_token

settings = get_settings()


@pytest.mark.asyncio
async def test_auth_me_missing_header_returns_401(async_client: AsyncClient):
    response = await async_client.get("/api/v1/auth/me")
    assert response.status_code == 401
    assert response.json()["detail"] == "Missing Authorization header"
    assert "Bearer" in response.headers.get("www-authenticate", "")


@pytest.mark.asyncio
async def test_auth_me_invalid_scheme_returns_401(async_client: AsyncClient):
    response = await async_client.get(
        "/api/v1/auth/me",
        headers={"Authorization": "Basic dXNlcjpwYXNz"},
    )
    assert response.status_code == 401
    assert response.json()["detail"] == "Invalid authorization scheme"


@pytest.mark.asyncio
async def test_auth_me_tampered_token_returns_401(async_client: AsyncClient):
    response = await async_client.get(
        "/api/v1/auth/me",
        headers={"Authorization": "Bearer not_a_valid_jwt_token.at.all"},
    )
    assert response.status_code == 401
    assert response.json()["detail"] == "Invalid token signature or format"


@pytest.mark.asyncio
async def test_auth_me_expired_token_returns_401(async_client: AsyncClient):
    data = {
        "sub": "user-expired",
        "tenant_id": "acme_corp",
        "allowed_roles": ["public"],
    }
    expired_token = create_access_token(data=data, expires_delta=timedelta(seconds=-10))
    response = await async_client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {expired_token}"},
    )
    assert response.status_code == 401
    assert response.json()["detail"] == "Token has expired"


@pytest.mark.asyncio
async def test_auth_me_token_lacking_tenant_id_returns_403(async_client: AsyncClient):
    # Valid signature but missing tenant_id claim
    token = jwt.encode(
        {"sub": "no-tenant-user", "allowed_roles": ["public"]},
        settings.JWT_SECRET_KEY,
        algorithm=settings.ALGORITHM,
    )
    response = await async_client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 403
    assert response.json()["detail"] == "Token missing tenant_id or allowed_roles claims"


@pytest.mark.asyncio
async def test_auth_me_token_lacking_roles_returns_403(async_client: AsyncClient):
    # Valid signature but missing or empty allowed_roles claim
    token = jwt.encode(
        {"sub": "no-roles-user", "tenant_id": "acme_corp", "allowed_roles": []},
        settings.JWT_SECRET_KEY,
        algorithm=settings.ALGORITHM,
    )
    response = await async_client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 403
    assert response.json()["detail"] == "Token missing tenant_id or allowed_roles claims"


@pytest.mark.asyncio
async def test_auth_me_valid_token_returns_200_and_security_context(async_client: AsyncClient):
    data = {
        "sub": "valid-user",
        "tenant_id": "acme_corp",
        "allowed_roles": ["support_tier_1", "public"],
    }
    token = create_access_token(data=data)
    response = await async_client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["tenant_id"] == "acme_corp"
    assert sorted(body["allowed_roles"]) == ["public", "support_tier_1"]
    expected_hash = compute_scope_hash("acme_corp", ["public", "support_tier_1"])
    assert body["scope_hash"] == expected_hash
