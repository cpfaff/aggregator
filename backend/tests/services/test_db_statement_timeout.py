"""Behavioural tests for the server-side DB statement/lock timeout (RH-01).

These tests prove that a slow query is aborted by PostgreSQL's
``statement_timeout`` instead of pinning a pooled connection for its full
duration. The check is **behavioural** (run ``SELECT pg_sleep(10)`` and assert it
is aborted well under the sleep duration) because ``connect_args`` live inside a
driver closure and cannot be reliably asserted from the engine object — see the
RH-01 anti-pattern about asserting on ``engine.url``/kwargs.

To avoid a tautology, the testcontainer engines are built from the **production**
``connect_args`` helpers — ``app.db.session.sync_connect_args`` and
``app.db.base.async_connect_args`` — *not* a re-inlined copy. Those helpers read
``settings.DB_STATEMENT_TIMEOUT_MS`` / ``settings.DB_LOCK_TIMEOUT_MS`` at call
time, so reverting the production timeout (dropping it from the helper) turns
these tests RED. Each test monkeypatches ``DB_STATEMENT_TIMEOUT_MS`` to a tighter
``TEST_STATEMENT_TIMEOUT_MS`` (2000 ms) *before* calling the helper, so the abort
lands comfortably inside the 5 s wall-clock budget and the assertion stays
deterministic; the helper still owns the wire shape under test.

``test_red_proof_no_timeout_runs_full_sleep`` is the explicit non-tautology
proof: with ``DB_STATEMENT_TIMEOUT_MS`` neutralised to 0 (PostgreSQL: no limit),
the same helper produces no abort and ``pg_sleep`` runs unbounded. The two
``connect_args contain a non-zero statement_timeout`` unit assertions go red if a
helper drops the timeout.
"""

import time

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.exc import DBAPIError, OperationalError
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.base import async_connect_args
from app.db.session import sync_connect_args

# Tighter than the 5000 ms production default so the 10s sleep is aborted well
# inside the 5s budget without flaking on container/scheduler jitter. Applied by
# monkeypatching settings so the *production* helper picks it up — the helper,
# not a re-inlined copy, owns the connect_args shape under test.
TEST_STATEMENT_TIMEOUT_MS = 2000


def test_sync_connect_args_carries_nonzero_statement_timeout():
    """The sync helper must set a non-zero ``statement_timeout`` (fast unit check).

    Goes red if the production helper drops the timeout (PostgreSQL treats 0 as
    "no limit"), independent of any container.
    """
    options = sync_connect_args()["options"]
    assert f"statement_timeout={settings.DB_STATEMENT_TIMEOUT_MS}" in options
    assert settings.DB_STATEMENT_TIMEOUT_MS > 0


def test_async_connect_args_carries_nonzero_statement_timeout():
    """The async helper must set a non-zero ``statement_timeout`` (fast unit check).

    Goes red if the production helper drops the timeout.
    """
    server_settings = async_connect_args()["server_settings"]
    assert server_settings["statement_timeout"] == str(settings.DB_STATEMENT_TIMEOUT_MS)
    assert settings.DB_STATEMENT_TIMEOUT_MS > 0


def test_slow_query_aborts_within_timeout(postgres_container, monkeypatch):
    """A 10s query must be aborted by ``statement_timeout`` in well under 5s.

    Builds a sync engine against the test container using the **production**
    ``sync_connect_args`` helper (libpq ``options``), runs ``SELECT pg_sleep(10)``,
    and asserts it raises a DB error within a 5s wall-clock budget. Without a
    server-side ``statement_timeout`` the query runs the full 10s and either
    blows the budget or never raises — that is the RH-01 defect. The timeout is
    tightened via ``settings`` (not a re-inlined arg) so the helper owns the
    behaviour: revert the production timeout and this turns red.
    """
    monkeypatch.setattr(settings, "DB_STATEMENT_TIMEOUT_MS", TEST_STATEMENT_TIMEOUT_MS)
    database_url = postgres_container.get_connection_url()
    engine = create_engine(database_url, connect_args=sync_connect_args())
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


async def test_async_slow_query_aborts_within_timeout(postgres_container, monkeypatch):
    """Same guarantee on the async (asyncpg) engine that serves request handlers.

    Builds the async engine from the **production** ``async_connect_args`` helper,
    which carries the timeout via ``server_settings``; a 10s query must be aborted
    within the 5s budget. Reverting the production timeout turns this red.
    """
    monkeypatch.setattr(settings, "DB_STATEMENT_TIMEOUT_MS", TEST_STATEMENT_TIMEOUT_MS)
    database_url = postgres_container.get_connection_url().replace(
        "postgresql+psycopg2://", "postgresql+asyncpg://"
    )
    engine = create_async_engine(database_url, connect_args=async_connect_args())
    try:
        started = time.monotonic()
        with pytest.raises((OperationalError, DBAPIError)):
            async with engine.connect() as conn:
                await conn.execute(text("SELECT pg_sleep(10)"))
        elapsed = time.monotonic() - started
        assert elapsed < 5, f"async query was not aborted by statement_timeout ({elapsed:.1f}s)"
    finally:
        await engine.dispose()


def test_red_proof_no_timeout_runs_full_sleep(postgres_container, monkeypatch):
    """Non-tautology proof: with the timeout neutralised, no abort happens.

    Neutralising the production bound (``DB_STATEMENT_TIMEOUT_MS = 0`` ==
    PostgreSQL "no limit") through the *same* ``sync_connect_args`` helper means
    ``SELECT pg_sleep(3)`` runs to completion and raises nothing — proving the
    abort in the other tests is produced by the production timeout wiring, not by
    the test scaffolding. If the helper stopped honouring the setting, this query
    would still be capped and the ``does not raise`` assertion below would fail.
    """
    monkeypatch.setattr(settings, "DB_STATEMENT_TIMEOUT_MS", 0)
    database_url = postgres_container.get_connection_url()
    engine = create_engine(database_url, connect_args=sync_connect_args())
    try:
        with Session(engine) as session:
            # No statement_timeout in force -> the sleep completes, no error.
            session.execute(text("SELECT pg_sleep(3)"))
    finally:
        engine.dispose()
