from typing import Any

from fastapi import APIRouter, Depends

from app.api.deps import get_security_context
from app.schemas.auth import SecurityContext

router = APIRouter()
auth_router = router


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
