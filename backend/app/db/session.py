from collections.abc import AsyncGenerator
from typing import Any

from pgvector import Vector
from pgvector.asyncpg import register_vector
from sqlalchemy import event, text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.config import get_settings

settings = get_settings()

async_engine = create_async_engine(
    settings.DATABASE_URL,
    echo=False,
    pool_pre_ping=True,
    pool_size=10,
    max_overflow=20,
)


@event.listens_for(async_engine.sync_engine, "connect")
def register_pgvector_codecs(dbapi_connection: Any, connection_record: Any) -> None:
    """Register pgvector type codecs on every asyncpg connection.

    Registers binary codecs for vector, halfvec, and sparsevec via pgvector.asyncpg.register_vector,
    and extends the vector encoder so both native Vector/lists and SQLAlchemy-bound string values
    serialize without codec mismatch errors.
    """
    async def init_codecs(conn: Any) -> None:
        await register_vector(conn)
        await conn.set_type_codec(
            "vector",
            schema="public",
            encoder=lambda v: (
                v if isinstance(v, Vector)
                else Vector.from_text(v) if isinstance(v, str)
                else Vector(v)
            ).to_binary(),
            decoder=Vector.from_binary,
            format="binary",
        )

    dbapi_connection.run_async(init_codecs)


async_session_maker = async_sessionmaker(
    bind=async_engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)


async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    """Dependency that yields an async database session and ensures clean rollback on exception."""
    async with async_session_maker() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise


# Backward-compatible aliases for existing health check & lifespan hooks
get_db = get_db_session
engine = async_engine


async def check_database_connection() -> bool:
    """Verify database connectivity for readiness/liveness health endpoints."""
    try:
        async with async_engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
            return True
    except Exception:  # noqa: BLE001
        return False
