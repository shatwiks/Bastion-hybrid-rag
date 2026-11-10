from pydantic import BaseModel, ConfigDict, Field


class SecurityContext(BaseModel):
    model_config = ConfigDict(frozen=True)

    tenant_id: str = Field(..., description="Unique tenant identifier for data isolation")
    allowed_roles: tuple[str, ...] = Field(..., description="Immutable tuple of authorized roles")
    scope_hash: str = Field(..., description="Deterministic canonical hash of tenant and roles")


class JWTPayload(BaseModel):
    model_config = ConfigDict(extra="ignore")

    sub: str = Field(default="", description="Subject identifier (e.g. user or demo identity)")
    tenant_id: str | None = Field(default=None, description="Unique tenant identifier")
    allowed_roles: list[str] | None = Field(
        default=None, description="List of authorized roles for the subject"
    )
    exp: int | None = Field(default=None, description="Expiration timestamp (unix seconds)")
    iat: int | None = Field(default=None, description="Issued-at timestamp (unix seconds)")


class DemoTokenRequest(BaseModel):
    tenant_id: str = Field(default="acme_corp", description="Target demo tenant identifier")
    persona: str | None = Field(
        default=None,
        description="Demo persona preset (public, support_tier_1, executive)",
    )
    custom_roles: list[str] | None = Field(
        default=None,
        description="Optional custom roles list if persona preset is not used",
    )


class DemoTokenResponse(BaseModel):
    access_token: str = Field(..., description="Cryptographically signed JWT bearer token")
    token_type: str = Field(default="bearer", description="Token type")
    tenant_id: str = Field(..., description="Target tenant identifier")
    allowed_roles: list[str] = Field(..., description="List of authorized roles")
    scope_hash: str = Field(..., description="Deterministic canonical scope hash")
    expires_in: int = Field(..., description="Token validity in seconds")
