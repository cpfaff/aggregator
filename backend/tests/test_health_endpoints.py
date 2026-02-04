"""Tests for health check endpoints."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.api.v1.endpoints.health import health_check, readiness_check


@pytest.mark.asyncio
async def test_health_check_returns_healthy_when_db_connected():
    """Test that /health-check returns healthy status when database is connected."""
    mock_db = AsyncMock()
    mock_db.execute = AsyncMock()

    result = await health_check(db=mock_db)

    assert result["status"] == "healthy"
    assert result["database"]["status"] == "connected"
    assert "response_time_ms" in result["database"]
    assert "timestamp" in result


@pytest.mark.asyncio
async def test_health_check_returns_unhealthy_when_db_fails():
    """Test that /health-check raises 503 when database query fails."""
    from fastapi import HTTPException

    mock_db = AsyncMock()
    mock_db.execute = AsyncMock(side_effect=Exception("Connection refused"))

    with pytest.raises(HTTPException) as exc_info:
        await health_check(db=mock_db)

    assert exc_info.value.status_code == 503


@pytest.mark.asyncio
async def test_health_ready_returns_ready_when_all_deps_ok():
    """Test that /health/ready returns ready when database and Redis are both up."""
    mock_db = AsyncMock()
    mock_db.execute = AsyncMock()

    mock_redis = MagicMock()
    mock_redis.ping = MagicMock(return_value=True)
    mock_redis.close = MagicMock()

    with patch("app.api.v1.endpoints.health._get_redis_client", return_value=mock_redis):
        result = await readiness_check(db=mock_db)

    assert result.status_code == 200
    body = result.body
    import json

    data = json.loads(body)
    assert data["status"] == "ready"
    assert data["checks"]["database"]["status"] == "up"
    assert data["checks"]["redis"]["status"] == "up"


@pytest.mark.asyncio
async def test_health_ready_returns_not_ready_when_redis_fails():
    """Test that /health/ready returns 503 when Redis is down."""
    mock_db = AsyncMock()
    mock_db.execute = AsyncMock()

    mock_redis = MagicMock()
    mock_redis.ping = MagicMock(side_effect=Exception("Connection refused"))
    mock_redis.close = MagicMock()

    with patch("app.api.v1.endpoints.health._get_redis_client", return_value=mock_redis):
        result = await readiness_check(db=mock_db)

    assert result.status_code == 503
    import json

    data = json.loads(result.body)
    assert data["status"] == "not_ready"
    assert data["checks"]["redis"]["status"] == "down"
    assert data["checks"]["database"]["status"] == "up"


@pytest.mark.asyncio
async def test_health_ready_returns_not_ready_when_db_fails():
    """Test that /health/ready returns 503 when database is down."""
    mock_db = AsyncMock()
    mock_db.execute = AsyncMock(side_effect=Exception("Connection refused"))

    mock_redis = MagicMock()
    mock_redis.ping = MagicMock(return_value=True)
    mock_redis.close = MagicMock()

    with patch("app.api.v1.endpoints.health._get_redis_client", return_value=mock_redis):
        result = await readiness_check(db=mock_db)

    assert result.status_code == 503
    import json

    data = json.loads(result.body)
    assert data["status"] == "not_ready"
    assert data["checks"]["database"]["status"] == "down"
    assert data["checks"]["redis"]["status"] == "up"


@pytest.mark.asyncio
async def test_health_ready_includes_response_times():
    """Test that /health/ready includes response times for each dependency."""
    mock_db = AsyncMock()
    mock_db.execute = AsyncMock()

    mock_redis = MagicMock()
    mock_redis.ping = MagicMock(return_value=True)
    mock_redis.close = MagicMock()

    with patch("app.api.v1.endpoints.health._get_redis_client", return_value=mock_redis):
        result = await readiness_check(db=mock_db)

    import json

    data = json.loads(result.body)
    assert "response_time_ms" in data["checks"]["database"]
    assert "response_time_ms" in data["checks"]["redis"]
    assert isinstance(data["checks"]["database"]["response_time_ms"], float)
    assert isinstance(data["checks"]["redis"]["response_time_ms"], float)


@pytest.mark.asyncio
async def test_health_ready_returns_not_ready_when_both_fail():
    """Test that /health/ready returns 503 when both dependencies are down."""
    mock_db = AsyncMock()
    mock_db.execute = AsyncMock(side_effect=Exception("DB down"))

    mock_redis = MagicMock()
    mock_redis.ping = MagicMock(side_effect=Exception("Redis down"))
    mock_redis.close = MagicMock()

    with patch("app.api.v1.endpoints.health._get_redis_client", return_value=mock_redis):
        result = await readiness_check(db=mock_db)

    assert result.status_code == 503
    import json

    data = json.loads(result.body)
    assert data["status"] == "not_ready"
    assert data["checks"]["database"]["status"] == "down"
    assert data["checks"]["redis"]["status"] == "down"
