from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status

from app.api.deps import get_security_context
from app.core.security import compute_scope_hash, create_access_token
from app.schemas.auth import DemoTokenRequest, DemoTokenResponse, SecurityContext

router = APIRouter()
auth_router = router

PERSONA_ROLES_MAP: dict[str, list[str]] = {
    "public": ["public"],
    "support_tier_1": ["public", "support_tier_1"],
    "executive": ["public", "support_tier_1", "executive"],
}

SUPPORTED_DEMO_TENANTS: set[str] = {"acme_corp", "globex_corp"}


@router.post("/demo-token", response_model=DemoTokenResponse)
async def mint_demo_token(req: DemoTokenRequest) -> DemoTokenResponse:
    """Mints signed persona-tiered JWT tokens for demo evaluation and testing."""
    tenant_id = req.tenant_id or "acme_corp"
    if tenant_id not in SUPPORTED_DEMO_TENANTS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported demo tenant. Supported: {', '.join(sorted(SUPPORTED_DEMO_TENANTS))}",
        )

    if req.persona is not None:
        if req.persona not in PERSONA_ROLES_MAP:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Unknown persona: '{req.persona}'. Supported personas: {', '.join(sorted(PERSONA_ROLES_MAP.keys()))}",
            )
        roles = PERSONA_ROLES_MAP[req.persona]
        persona_name = req.persona
    elif req.custom_roles is not None:
        if not isinstance(req.custom_roles, list) or len(req.custom_roles) == 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="custom_roles must be a non-empty list of strings",
            )
        roles = req.custom_roles
        persona_name = "custom"
    else:
        roles = PERSONA_ROLES_MAP["public"]
        persona_name = "public"

    token_data = {
        "sub": f"demo-{tenant_id}-{persona_name}",
        "tenant_id": tenant_id,
        "allowed_roles": roles,
    }
    access_token = create_access_token(data=token_data)
    scope_hash = compute_scope_hash(tenant_id, roles)

    return DemoTokenResponse(
        access_token=access_token,
        token_type="bearer",
        tenant_id=tenant_id,
        allowed_roles=roles,
        scope_hash=scope_hash,
        expires_in=86400,
    )


@router.get("/me")
async def get_current_user_context(
    ctx: SecurityContext = Depends(get_security_context),  # noqa: B008
) -> dict[str, Any]:
    """Protected endpoint returning the verified caller SecurityContext."""
    return {
        "tenant_id": ctx.tenant_id,
        "allowed_roles": list(ctx.allowed_roles),
        "scope_hash": ctx.scope_hash,
    }
