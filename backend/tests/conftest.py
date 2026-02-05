"""Pytest configuration and fixtures for tests."""

import pytest
import pytest_asyncio
from sqlalchemy import create_engine
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import Session, sessionmaker
from testcontainers.core.container import DockerContainer
from testcontainers.core.wait_strategies import ExecWaitStrategy
from testcontainers.postgres import PostgresContainer

from app.models.base import Base


@pytest.fixture(scope="session")
def postgres_container():
    """PostgreSQL testcontainer (session-scoped for speed)."""
    with PostgresContainer("postgres:15-alpine") as postgres:
        yield postgres


@pytest.fixture(scope="session")
def redis_container():
    """Redis testcontainer using modern wait strategy (session-scoped for speed).

    Uses DockerContainer with ExecWaitStrategy instead of deprecated RedisContainer
    to avoid the @wait_container_is_ready deprecation warning.
    """
    redis = DockerContainer("redis:7-alpine")
    redis.with_exposed_ports(6379)
    redis.waiting_for(ExecWaitStrategy(["redis-cli", "ping"]))
    with redis:
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
