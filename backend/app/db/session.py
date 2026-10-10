from typing import AsyncGenerator, Dict, Any
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from app.core.config import settings
from app.db.models import Base

from sqlalchemy.pool import NullPool

engine = create_async_engine(
    settings.DATABASE_URL,
    echo=settings.DEBUG,
    future=True,
    poolclass=NullPool,
    connect_args={"command_timeout": 60.0, "ssl": False}
)

AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False
)

async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Dependency for obtaining async DB session."""
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()

async def init_db() -> None:
    """Initialize database extension (pgvector) and create missing tables."""
    # Step 1: Ensure vector extension exists
    try:
        async with engine.begin() as conn:
            await conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector;"))
    except Exception:
        pass

    # Step 2: Create all tables defined in models
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    # Step 3: Backward compatibility migration for existing artifacts tables
    try:
        async with engine.begin() as conn:
            await conn.execute(text("ALTER TABLE artifacts ADD COLUMN IF NOT EXISTS citations JSONB DEFAULT '[]'::jsonb;"))
    except Exception:
        pass

async def check_db_health() -> Dict[str, Any]:
    """Check database connection and pgvector extension availability."""
    try:
        async with AsyncSessionLocal() as session:
            result = await session.execute(text("SELECT 1;"))
            vector_check = await session.execute(text("SELECT extname FROM pg_extension WHERE extname = 'vector';"))
            has_vector = bool(vector_check.scalar_one_or_none())
            return {
                "status": "connected",
                "pgvector_extension": "installed" if has_vector else "not_installed",
                "host": settings.POSTGRES_HOST,
                "database": settings.POSTGRES_DB
            }
    except Exception as exc:
        return {
            "status": "disconnected",
            "error": str(exc),
            "host": settings.POSTGRES_HOST,
            "database": settings.POSTGRES_DB
        }
