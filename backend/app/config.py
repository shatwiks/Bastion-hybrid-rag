from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    PROJECT_NAME: str = "Enterprise Multi-Tenant RAG Knowledge Engine"
    VERSION: str = "1.0.0"
    ENVIRONMENT: str = "development"

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

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()
