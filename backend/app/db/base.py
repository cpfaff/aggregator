"""
Database engine setup and base configuration.
"""

from sqlalchemy.ext.asyncio import create_async_engine

from app.core.config import settings

# Database URLs for async and sync connections
DATABASE_URL = settings.DATABASE_URL
# Convert async URL to sync URL for SQLAlchemy standard engine
SYNC_DATABASE_URL = DATABASE_URL.replace("postgresql+asyncpg://", "postgresql://")

# Create engine with connection pooling configured via settings
engine = create_async_engine(
    DATABASE_URL,
    echo=False,  # Set to True for SQL query logging (development only)
    pool_size=settings.DB_POOL_SIZE,
    max_overflow=settings.DB_MAX_OVERFLOW,
    pool_recycle=settings.DB_POOL_RECYCLE,
)
