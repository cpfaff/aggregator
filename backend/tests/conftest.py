"""Pytest configuration and fixtures for tests."""

import pytest
import pytest_asyncio
from sqlalchemy import create_engine
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import Session, sessionmaker
from testcontainers.postgres import PostgresContainer
from testcontainers.redis import RedisContainer

from app.models.base import Base


@pytest.fixture(scope="session")
def postgres_container():
    """PostgreSQL testcontainer (session-scoped for speed)."""
    with PostgresContainer("postgres:15-alpine") as postgres:
        yield postgres


@pytest.fixture(scope="session")
def redis_container():
    """Redis testcontainer (session-scoped for speed)."""
    with RedisContainer("redis:7-alpine") as redis:
        yield redis


@pytest_asyncio.fixture
async def test_engine(postgres_container):
    """Async SQLAlchemy engine with testcontainer database."""
    database_url = postgres_container.get_connection_url().replace(
        "postgresql+psycopg2://", "postgresql+asyncpg://"
    )

    engine = create_async_engine(database_url, echo=False)

    # Create all tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    yield engine

    await engine.dispose()


@pytest_asyncio.fixture
async def db_session(test_engine):
    """Clean database session for each test with proper isolation."""
    async_session = sessionmaker(
        test_engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )

    async with async_session() as session:
        yield session

    # Clear all tables after each test to ensure isolation
    async with test_engine.begin() as conn:
        for table in reversed(Base.metadata.sorted_tables):
            await conn.execute(table.delete())


@pytest.fixture
def sync_engine(postgres_container):
    """Sync SQLAlchemy engine with testcontainer database."""
    database_url = postgres_container.get_connection_url()
    engine = create_engine(database_url, echo=False)

    # Create all tables
    Base.metadata.create_all(engine)

    yield engine

    engine.dispose()


@pytest.fixture
def sync_db_session(sync_engine):
    """Clean sync database session for each test with proper isolation."""
    session = Session(sync_engine, expire_on_commit=False)

    yield session

    session.close()

    # Clear all tables after each test to ensure isolation
    with sync_engine.begin() as conn:
        for table in reversed(Base.metadata.sorted_tables):
            conn.execute(table.delete())


@pytest.fixture
def anyio_backend():
    """Configure anyio backend for pytest-asyncio."""
    return "asyncio"
