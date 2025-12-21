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

# Build engine kwargs based on environment
engine_kwargs = {
    "echo": settings.DEBUG,
}

# Add asyncpg-specific connection args
if "asyncpg" in settings.DATABASE_URL:
    engine_kwargs["connect_args"] = {
        "server_settings": {"statement_timeout": "60000"},  # 60 seconds
        "command_timeout": 60,
    }

if is_production:
    # Use NullPool for production - no pool_size/max_overflow allowed
    engine_kwargs["poolclass"] = NullPool
else:
    # Use connection pooling for development
    engine_kwargs["pool_size"] = settings.DATABASE_POOL_SIZE
    engine_kwargs["max_overflow"] = settings.DATABASE_MAX_OVERFLOW
    engine_kwargs["pool_pre_ping"] = True

# Create async engine
engine = create_async_engine(settings.DATABASE_URL, **engine_kwargs)

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

