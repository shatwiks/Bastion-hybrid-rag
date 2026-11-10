import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "tenant_id,persona,expected_roles",
    [
        ("acme_corp", "public", ["public"]),
        ("acme_corp", "support_tier_1", ["public", "support_tier_1"]),
        ("acme_corp", "executive", ["public", "support_tier_1", "executive"]),
        ("globex_corp", "public", ["public"]),
        ("globex_corp", "support_tier_1", ["public", "support_tier_1"]),
        ("globex_corp", "executive", ["public", "support_tier_1", "executive"]),
    ],
)
async def test_mint_standard_persona_tokens(
    async_client: AsyncClient,
    tenant_id: str,
    persona: str,
    expected_roles: list[str],
):
    # 1. Mint demo token
    payload = {
        "tenant_id": tenant_id,
        "persona": persona,
    }
    response = await async_client.post("/api/v1/auth/demo-token", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"
    assert data["tenant_id"] == tenant_id
    assert sorted(data["allowed_roles"]) == sorted(expected_roles)
    assert len(data["scope_hash"]) == 16
    assert data["expires_in"] == 86400

    token = data["access_token"]

    # 2. Authenticate against GET /api/v1/auth/me
    auth_response = await async_client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert auth_response.status_code == 200
    me_data = auth_response.json()
    assert me_data["tenant_id"] == tenant_id
    assert sorted(me_data["allowed_roles"]) == sorted(expected_roles)
    assert me_data["scope_hash"] == data["scope_hash"]


@pytest.mark.asyncio
async def test_mint_custom_roles_token(async_client: AsyncClient):
    payload = {
        "tenant_id": "acme_corp",
        "custom_roles": ["auditor", "security_lead"],
    }
    response = await async_client.post("/api/v1/auth/demo-token", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["tenant_id"] == "acme_corp"
    assert sorted(data["allowed_roles"]) == ["auditor", "security_lead"]

    # Verify against /me
    auth_response = await async_client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {data['access_token']}"},
    )
    assert auth_response.status_code == 200
    me_data = auth_response.json()
    assert me_data["tenant_id"] == "acme_corp"
    assert sorted(me_data["allowed_roles"]) == ["auditor", "security_lead"]


@pytest.mark.asyncio
async def test_mint_demo_token_default_is_public_acme(async_client: AsyncClient):
    # Empty body defaults to public acme_corp
    response = await async_client.post("/api/v1/auth/demo-token", json={})
    assert response.status_code == 200
    data = response.json()
    assert data["tenant_id"] == "acme_corp"
    assert data["allowed_roles"] == ["public"]


@pytest.mark.asyncio
async def test_mint_demo_token_unknown_persona_returns_400(async_client: AsyncClient):
    payload = {
        "tenant_id": "acme_corp",
        "persona": "super_admin_does_not_exist",
    }
    response = await async_client.post("/api/v1/auth/demo-token", json=payload)
    assert response.status_code == 400
    assert "Unknown persona" in response.json()["detail"]


@pytest.mark.asyncio
async def test_mint_demo_token_unsupported_tenant_returns_400(async_client: AsyncClient):
    payload = {
        "tenant_id": "malicious_corp",
        "persona": "public",
    }
    response = await async_client.post("/api/v1/auth/demo-token", json=payload)
    assert response.status_code == 400
    assert "Unsupported demo tenant" in response.json()["detail"]
