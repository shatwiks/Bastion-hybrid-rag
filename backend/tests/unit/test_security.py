from datetime import UTC, datetime, timedelta

import jwt
import pytest
from pydantic import ValidationError

from app.config import get_settings
from app.core.security import compute_scope_hash, create_access_token, decode_access_token
from app.schemas.auth import JWTPayload, SecurityContext

settings = get_settings()


def test_create_access_token_produces_valid_signed_jwt():
    data = {
        "sub": "user-123",
        "tenant_id": "acme_corp",
        "allowed_roles": ["public", "support_tier_1"],
    }
    token = create_access_token(data=data, expires_delta=timedelta(minutes=15))
    assert isinstance(token, str)

    # Decode directly using PyJWT and secret key to verify cryptographic signature
    decoded = jwt.decode(token, settings.JWT_SECRET_KEY, algorithms=[settings.ALGORITHM])
    assert decoded["sub"] == "user-123"
    assert decoded["tenant_id"] == "acme_corp"
    assert decoded["allowed_roles"] == ["public", "support_tier_1"]
    assert "exp" in decoded
    assert "iat" in decoded


def test_decode_access_token_enforces_algorithm_and_key():
    data = {
        "sub": "user-456",
        "tenant_id": "acme_corp",
        "allowed_roles": ["public"],
    }
    valid_token = create_access_token(data=data)
    payload = decode_access_token(valid_token)
    assert isinstance(payload, JWTPayload)
    assert payload.sub == "user-456"
    assert payload.tenant_id == "acme_corp"
    assert payload.allowed_roles == ["public"]

    # Reject foreign symmetric key
    foreign_token = jwt.encode(
        {
            "sub": "attacker",
            "tenant_id": "acme_corp",
            "allowed_roles": ["executive"],
            "exp": int(datetime.now(UTC).timestamp()) + 3600,
            "iat": int(datetime.now(UTC).timestamp()),
        },
        "wrong_foreign_secret_key_1234567890",
        algorithm=settings.ALGORITHM,
    )
    with pytest.raises(jwt.InvalidSignatureError):
        decode_access_token(foreign_token)

    # Reject algorithm 'none'
    none_token = jwt.encode(
        {"sub": "attacker", "tenant_id": "acme_corp", "allowed_roles": ["executive"]},
        key="",
        algorithm="none",
    )
    with pytest.raises(jwt.InvalidTokenError):
        decode_access_token(none_token)


def test_decode_access_token_raises_expired_signature_error():
    expired_data = {
        "sub": "expired-user",
        "tenant_id": "globex_corp",
        "allowed_roles": ["public"],
    }
    token = create_access_token(data=expired_data, expires_delta=timedelta(seconds=-10))
    with pytest.raises(jwt.ExpiredSignatureError):
        decode_access_token(token)


def test_compute_scope_hash_invariant_to_role_order():
    hash1 = compute_scope_hash("acme_corp", ["public", "support_tier_1"])
    hash2 = compute_scope_hash("acme_corp", ["support_tier_1", "public"])
    hash3 = compute_scope_hash("acme_corp", ["public", "support_tier_1", "public"])
    assert hash1 == hash2
    assert hash1 == hash3
    assert len(hash1) == 16


def test_compute_scope_hash_distinct_for_different_tenants():
    roles = ["public", "support_tier_1"]
    hash_acme = compute_scope_hash("acme_corp", roles)
    hash_globex = compute_scope_hash("globex_corp", roles)
    assert hash_acme != hash_globex


def test_security_context_is_frozen_and_immutable():
    ctx = SecurityContext(
        tenant_id="acme_corp",
        allowed_roles=("public", "support_tier_1"),
        scope_hash="a1b2c3d4e5f60718",
    )
    assert ctx.tenant_id == "acme_corp"
    assert ctx.allowed_roles == ("public", "support_tier_1")
    assert ctx.scope_hash == "a1b2c3d4e5f60718"

    with pytest.raises(ValidationError):
        ctx.tenant_id = "globex_corp"  # type: ignore

    with pytest.raises(ValidationError):
        ctx.allowed_roles = ("executive",)  # type: ignore
