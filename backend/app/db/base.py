"""
Database engine setup and base configuration.
"""

from sqlalchemy.ext.asyncio import create_async_engine

from app.core.config import settings

# Database URLs for async and sync connections
DATABASE_URL = settings.DATABASE_URL
# Convert async URL to sync URL for SQLAlchemy standard engine
SYNC_DATABASE_URL = DATABASE_URL.replace("postgresql+asyncpg://", "postgresql://")


def async_connect_args() -> dict:
    """Build the asyncpg ``connect_args`` for the async production engine.

    Sets a server-side statement/lock timeout so a slow or lock-blocked query
    is aborted by PostgreSQL instead of pinning a pooled connection until the
    pool is exhausted (RH-01 / REQ-PG-1). asyncpg applies these via
    per-connection ``server_settings``. Reads the bounds from ``settings`` at
    call time so this single helper owns the wire behaviour and the
    timeout-abort test can lock the production wiring instead of re-inlining it.
    """
    return {
        "server_settings": {
            "statement_timeout": str(settings.DB_STATEMENT_TIMEOUT_MS),
            "lock_timeout": str(settings.DB_LOCK_TIMEOUT_MS),
        }
    }


# Create engine with connection pooling configured via settings.
engine = create_async_engine(
    DATABASE_URL,
    echo=False,  # Set to True for SQL query logging (development only)
    pool_size=settings.DB_POOL_SIZE,
    max_overflow=settings.DB_MAX_OVERFLOW,
    pool_recycle=settings.DB_POOL_RECYCLE,
    connect_args=async_connect_args(),
)
