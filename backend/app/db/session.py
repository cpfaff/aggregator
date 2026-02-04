"""
Database session management and dependencies.
"""
from typing import AsyncGenerator, Generator

from fastapi import Depends
from sqlalchemy import create_engine
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Session, sessionmaker

from app.db.base import SYNC_DATABASE_URL, engine

# Create async session factory
async_session = sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)

# Create sync session factory for Celery tasks
sync_engine = create_engine(SYNC_DATABASE_URL)
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
