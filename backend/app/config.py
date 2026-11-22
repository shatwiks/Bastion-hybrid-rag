from functools import lru_cache
from typing import List, Union

from pydantic import field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    PROJECT_NAME: str = "Enterprise Multi-Tenant RAG Knowledge Engine"
    VERSION: str = "1.0.0"
    ENVIRONMENT: str = "development"
    ENABLE_DOCS: bool = True

    # CORS (no wildcard '*' permitted in production)
    CORS_ORIGINS: Union[List[str], str] = [
        "http://localhost:3000",
        "http://localhost:3005",
        "http://127.0.0.1:3000",
        "http://127.0.0.1:3005",
    ]

    # Ports
    BACKEND_PORT: int = 8000
    FRONTEND_PORT: int = 3005
    POSTGRES_PORT: int = 5437
    REDIS_PORT: int = 6379

    # Database
    POSTGRES_USER: str = "postgres"
    POSTGRES_PASSWORD: str = "postgres"
    POSTGRES_DB: str = "rag_engine"
    DATABASE_URL: str = "postgresql+asyncpg://postgres:postgres@localhost:5437/rag_engine"

    # Redis
    REDIS_URL: str = "redis://localhost:6379/0"

    # Security & Auth
    JWT_SECRET_KEY: str = "enterprise_super_secret_jwt_signing_key_replace_in_prod_32chars"
    ALGORITHM: str = "HS256"

    # RAG & Models
    REFUSAL_THRESHOLD: float = 0.65
    EMBEDDING_MODEL: str = "BAAI/bge-small-en-v1.5"
    RERANKER_MODEL: str = "cross-encoder/ms-marco-MiniLM-L6-v2"

    # LLM & Observability
    LLM_MODEL: str = "gpt-4o-mini"
    OPENAI_API_KEY: str | None = None
    GEMINI_API_KEY: str | None = None
    ANTHROPIC_API_KEY: str | None = None
    OLLAMA_API_BASE: str = "http://localhost:11434"
    OLLAMA_API_KEY: str | None = None
    LANGFUSE_PUBLIC_KEY: str | None = None
    LANGFUSE_SECRET_KEY: str | None = None
    LANGFUSE_HOST: str = "https://cloud.langfuse.com"

    @field_validator("CORS_ORIGINS", mode="before")
    @classmethod
    def parse_cors_origins(cls, v: Union[str, List[str]]) -> List[str]:
        if isinstance(v, str):
            return [o.strip().rstrip("/") for o in v.split(",") if o.strip()]
        return [str(o).strip().rstrip("/") for o in v if str(o).strip()]

    @model_validator(mode="after")
    def validate_production_security(self) -> "Settings":
        if (self.ENVIRONMENT or "").lower() == "production":
            default_secret = "enterprise_super_secret_jwt_signing_key_replace_in_prod_32chars"
            if not self.JWT_SECRET_KEY or self.JWT_SECRET_KEY == default_secret or len(self.JWT_SECRET_KEY) < 32:
                raise ValueError("CRITICAL SECURITY VIOLATION: Default or weak JWT_SECRET_KEY detected in production.")
            if "*" in self.CORS_ORIGINS:
                raise ValueError("CRITICAL SECURITY VIOLATION: Wildcard '*' CORS origin is forbidden in production.")
        return self

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()
