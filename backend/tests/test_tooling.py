"""Test new tooling setup (Poetry, Ruff, Testcontainers)."""

import pytest
from testcontainers.postgres import PostgresContainer
from testcontainers.redis import RedisContainer


def test_poetry_dependencies_installed():
    """Verify Poetry installed all required dependencies with correct versions."""
    import fastapi
    import sqlalchemy
    from sqlalchemy import __version__ as sa_version

    # Verify SQLAlchemy 2.0+ (requirement for async)
    major_version = int(sa_version.split(".")[0])
    assert major_version >= 2, f"SQLAlchemy {sa_version} < 2.0"

    # Verify core dependencies importable
    import pytest
    import pydantic
    import celery

    # Note: ruff is command-line tool, not importable Python package


@pytest.mark.asyncio
async def test_postgres_testcontainer():
    """Verify PostgreSQL testcontainer starts and accepts connections."""
    with PostgresContainer("postgres:15-alpine") as postgres:
        conn_url = postgres.get_connection_url()
        assert "postgresql" in conn_url
        assert postgres.get_container_host_ip()

        # Verify actual connection works
        from sqlalchemy import create_engine, text

        engine = create_engine(conn_url)
        with engine.connect() as conn:
            result = conn.execute(text("SELECT 1"))
            assert result.scalar() == 1


def test_redis_testcontainer():
    """Verify Redis testcontainer starts and accepts connections."""
    with RedisContainer("redis:7-alpine") as redis:
        assert redis.get_container_host_ip()
        port = redis.get_exposed_port(6379)
        assert port

        # Verify actual connection works
        import redis as redis_client

        client = redis_client.Redis(host=redis.get_container_host_ip(), port=int(port))
        assert client.ping() == True


def test_ruff_format_check_passes_on_formatted_file():
    """Verify Ruff format check works and returns correct exit codes."""
    import subprocess
    import tempfile
    import os

    # Create known-formatted Python file with proper Ruff formatting
    with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
        # Write properly formatted code (double quotes, proper spacing)
        f.write('"""Test module."""\n\n\ndef hello() -> str:\n    return "world"\n')
        temp_file = f.name

    try:
        result = subprocess.run(
            ["poetry", "run", "ruff", "format", "--check", temp_file],
            capture_output=True,
            text=True,
        )
        # Should pass on properly formatted file
        assert result.returncode == 0, f"Formatted file failed check: {result.stderr}"
    finally:
        os.unlink(temp_file)


def test_ruff_lint_runs_without_crash():
    """Verify Ruff linting runs without crashing (exit code 0 or 1, not 2+)."""
    import subprocess

    result = subprocess.run(
        ["poetry", "run", "ruff", "check", "app/main.py"],
        capture_output=True,
        text=True,
        cwd="/home/ctpfaff/Claude/development/search.gfbio.org/aggregator/.worktrees/production-readiness/backend",
    )
    # Exit codes: 0 = clean, 1 = violations found, 2+ = error/crash
    assert result.returncode in [0, 1], f"Ruff crashed: {result.stderr}"
