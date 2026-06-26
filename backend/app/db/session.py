"""
Database session management and dependencies.
"""

from collections.abc import AsyncGenerator, Generator

from sqlalchemy import create_engine
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import settings
from app.db.base import SYNC_DATABASE_URL, engine

# Create async session factory
async_session = sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)

# Create sync session factory for Celery tasks. connect_args sets the same
# server-side statement/lock timeout as the async engine so a slow or
# lock-blocked query in any Celery task is aborted by PostgreSQL instead of
# pinning a pooled connection (RH-01 / REQ-PG-1). psycopg2 passes these via the
# libpq ``options`` startup parameter.
sync_engine = create_engine(
    SYNC_DATABASE_URL,
    connect_args={
        "options": (
            f"-c statement_timeout={settings.DB_STATEMENT_TIMEOUT_MS} "
            f"-c lock_timeout={settings.DB_LOCK_TIMEOUT_MS}"
        )
    },
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=sync_engine)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    Dependency for database session injection.
    Yields a database session and ensures proper cleanup after use.
    """
    session = async_session()
    try:
        yield session
    finally:
        await session.close()


def get_sync_db() -> Generator[Session, None, None]:
    """
    Dependency for synchronous database session injection.
    Yields a synchronous database session and ensures proper cleanup after use.
    """
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()
