"""
Database session management
"""

from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import NullPool
from app.core.config import settings

# Determine if we're using a connection pooler (like Render's)
# For serverless/managed PostgreSQL, use NullPool to avoid connection issues
is_production = settings.ENVIRONMENT == "production"

# Create async engine with resilience settings
engine = create_async_engine(
    settings.DATABASE_URL,
    # Use NullPool for production to avoid SSL connection issues
    poolclass=NullPool if is_production else None,
    pool_size=None if is_production else settings.DATABASE_POOL_SIZE,
    max_overflow=None if is_production else settings.DATABASE_MAX_OVERFLOW,
    # Pre-ping to check connection health before using
    pool_pre_ping=True,
    # Connection timeout
    connect_args={
        "server_settings": {"statement_timeout": "60000"},  # 60 seconds
        "command_timeout": 60,
    } if "asyncpg" in settings.DATABASE_URL else {},
    echo=settings.DEBUG,
)

# Create async session factory
AsyncSessionLocal = sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)


async def get_db() -> AsyncSession:
    """
    Dependency for getting async database sessions
    
    Yields:
        AsyncSession: Database session
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()

