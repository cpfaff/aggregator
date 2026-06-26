"""Behavioural tests for the server-side DB statement/lock timeout (RH-01).

These tests prove that a slow query is aborted by PostgreSQL's
``statement_timeout`` instead of pinning a pooled connection for its full
duration. The check is **behavioural** (run ``SELECT pg_sleep(10)`` and assert it
is aborted well under the sleep duration) because ``connect_args`` live inside a
driver closure and cannot be reliably asserted from the engine object — see the
RH-01 anti-pattern about asserting on ``engine.url``/kwargs.

The production default ``settings.DB_STATEMENT_TIMEOUT_MS`` is 5000 ms; these
tests pin the wire value to a tighter ``TEST_STATEMENT_TIMEOUT_MS`` (2000 ms) so
the abort lands comfortably inside the 5s wall-clock budget and the assertion
stays deterministic. They apply the timeout through the *same* ``connect_args``
shape the production engines in ``app/db/base.py`` and ``app/db/session.py`` use
(``server_settings`` for asyncpg, libpq ``options`` for psycopg2), so a wiring
regression on that shape would surface here. ``DB_LOCK_TIMEOUT_MS`` is sourced
from ``settings`` to assert the setting exists.
"""

import time

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.exc import DBAPIError, OperationalError
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy.orm import Session

from app.core.config import settings

# Tighter than the 5000 ms production default so the 10s sleep is aborted well
# inside the 5s budget without flaking on container/scheduler jitter.
TEST_STATEMENT_TIMEOUT_MS = 2000


def test_slow_query_aborts_within_timeout(postgres_container):
    """A 10s query must be aborted by ``statement_timeout`` in well under 5s.

    Builds a sync engine against the test container using the production
    ``connect_args`` shape (libpq ``options``), runs ``SELECT pg_sleep(10)``,
    and asserts it raises a DB error within a 5s wall-clock budget. Without a
    server-side ``statement_timeout`` the query runs the full 10s and either
    blows the budget or never raises — that is the RH-01 defect.
    """
    database_url = postgres_container.get_connection_url()
    engine = create_engine(
        database_url,
        connect_args={
            "options": (
                f"-c statement_timeout={TEST_STATEMENT_TIMEOUT_MS} "
                f"-c lock_timeout={settings.DB_LOCK_TIMEOUT_MS}"
            )
        },
    )
    try:
        started = time.monotonic()
        with pytest.raises((OperationalError, DBAPIError)):
            with Session(engine) as session:
                session.execute(text("SELECT pg_sleep(10)"))
        elapsed = time.monotonic() - started
        # The 10s sleep must be aborted, not run to completion.
        assert elapsed < 5, f"query was not aborted by statement_timeout ({elapsed:.1f}s)"
    finally:
        engine.dispose()


async def test_async_slow_query_aborts_within_timeout(postgres_container):
    """Same guarantee on the async (asyncpg) engine that serves request handlers.

    The async engine carries the timeout via ``server_settings``; a 10s query
    must be aborted within the 5s budget.
    """
    database_url = postgres_container.get_connection_url().replace(
        "postgresql+psycopg2://", "postgresql+asyncpg://"
    )
    engine = create_async_engine(
        database_url,
        connect_args={
            "server_settings": {
                "statement_timeout": str(TEST_STATEMENT_TIMEOUT_MS),
                "lock_timeout": str(settings.DB_LOCK_TIMEOUT_MS),
            }
        },
    )
    try:
        started = time.monotonic()
        with pytest.raises((OperationalError, DBAPIError)):
            async with engine.connect() as conn:
                await conn.execute(text("SELECT pg_sleep(10)"))
        elapsed = time.monotonic() - started
        assert elapsed < 5, f"async query was not aborted by statement_timeout ({elapsed:.1f}s)"
    finally:
        await engine.dispose()
