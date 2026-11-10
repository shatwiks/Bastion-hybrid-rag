import jwt
from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import ValidationError

from app.core.security import compute_scope_hash, decode_access_token
from app.schemas.auth import SecurityContext

security_bearer = HTTPBearer(auto_error=False)


async def get_security_context(
    request: Request,
    credentials: HTTPAuthorizationCredentials | None = Depends(security_bearer),  # noqa: B008
) -> SecurityContext:
    """FastAPI dependency enforcing pre-retrieval JWT authentication and RBAC context extraction.

    Extracts an immutable SecurityContext guaranteed to contain verified tenant_id,
    allowed_roles tuple, and canonical scope_hash.
    """
    auth_header = request.headers.get("authorization")
    if not auth_header:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing Authorization header",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if credentials is None or credentials.scheme.lower() != "bearer":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authorization scheme",
            headers={"WWW-Authenticate": "Bearer"},
        )

    try:
        payload = decode_access_token(credentials.credentials)
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has expired",
            headers={"WWW-Authenticate": "Bearer"},
        )
    except (jwt.InvalidTokenError, ValidationError):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token signature or format",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if (
        not payload.tenant_id
        or not isinstance(payload.tenant_id, str)
        or not payload.allowed_roles
        or not isinstance(payload.allowed_roles, list)
        or len(payload.allowed_roles) == 0
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Token missing tenant_id or allowed_roles claims",
        )

    return SecurityContext(
        tenant_id=payload.tenant_id,
        allowed_roles=tuple(sorted(set(payload.allowed_roles))),
        scope_hash=compute_scope_hash(payload.tenant_id, payload.allowed_roles),
    )
