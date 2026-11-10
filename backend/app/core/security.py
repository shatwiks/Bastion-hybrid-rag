import hashlib
from collections.abc import Sequence
from datetime import UTC, datetime, timedelta
from typing import Any

import jwt

from app.config import get_settings
from app.schemas.auth import JWTPayload

settings = get_settings()


def compute_scope_hash(tenant_id: str, allowed_roles: Sequence[str]) -> str:
    """Computes a deterministic canonical scope hash from tenant_id and allowed_roles.

    The hash is invariant to role ordering and deduplicates identical roles.
    Format: SHA-256('{tenant_id}:{role1,role2,...}')[:16]
    """
    sorted_roles = sorted(set(allowed_roles))
    canonical = f"{tenant_id}:{','.join(sorted_roles)}"
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()[:16]


def create_access_token(
    data: dict[str, Any],
    expires_delta: timedelta | None = None,
) -> str:
    """Creates a cryptographically signed JWT access token.

    Defaults to a 24-hour expiration window if not specified.
    """
    to_encode = data.copy()
    now = datetime.now(UTC)
    if expires_delta is not None:
        expire = now + expires_delta
    else:
        expire = now + timedelta(hours=24)

    to_encode.update(
        {
            "exp": int(expire.timestamp()),
            "iat": int(now.timestamp()),
        }
    )

    return jwt.encode(
        to_encode,
        settings.JWT_SECRET_KEY,
        algorithm=settings.ALGORITHM,
    )


def decode_access_token(token: str) -> JWTPayload:
    """Decodes and cryptographically validates a JWT access token.

    Enforces the configured algorithm whitelist and validates expiration and signatures.
    Raises jwt.ExpiredSignatureError, jwt.InvalidTokenError, or pydantic.ValidationError.
    """
    payload = jwt.decode(
        token,
        settings.JWT_SECRET_KEY,
        algorithms=[settings.ALGORITHM],
    )
    return JWTPayload(**payload)
