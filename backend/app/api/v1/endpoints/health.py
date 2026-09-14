"""
Health check API endpoints.

This module contains health check endpoints for monitoring
the API, database connection, and dependency status.
"""

import logging
import time
from datetime import UTC, datetime
from typing import Annotated

import redis
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import JSONResponse
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.db import get_db

logger = logging.getLogger("api")

router = APIRouter()


def _get_redis_client() -> redis.Redis:
    """Create a Redis client for health checks."""
    return redis.Redis.from_url(settings.redis_url, socket_connect_timeout=5)


@router.get("/health", status_code=200, summary="Health check")
async def health_check(db: Annotated[AsyncSession, Depends(get_db)]):
    """
    Check the health of the API and database connection.
    Returns a JSON object with the status and database connection state.
    """
    try:
        # Time the database query
        start_time = time.time()
        await db.execute(text("SELECT 1"))
        db_response_time = time.time() - start_time

        # Return enhanced health check information
        return {
            "status": "healthy",
            "database": {
                "status": "connected",
                "response_time_ms": round(db_response_time * 1000, 2),
            },
            "version": "2.4.0",
            "timestamp": datetime.now(UTC).isoformat(),
        }
    except Exception as e:
        logger.error(f"Health check failed: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=503,
            detail={
                "status": "unhealthy",
                "database": {"status": "disconnected", "error": str(e)},
                "timestamp": datetime.now(UTC).isoformat(),
            },
        ) from e


@router.get("/health/live", status_code=200, summary="Liveness check")
async def liveness_check():
    """
    Basic liveness check - returns 200 if the service is running.

    This endpoint is used by container orchestrators (like Kubernetes)
    to determine if the service should be restarted.
    """
    return {"status": "alive"}


@router.get("/health/ready", status_code=200, summary="Readiness check")
async def readiness_check(db: Annotated[AsyncSession, Depends(get_db)]) -> JSONResponse:
    """
    Check readiness of all critical dependencies.

    Verifies database and Redis connectivity with response times.
    Returns 200 if all dependencies are healthy, 503 if any are down.
    """
    checks = {}
    all_healthy = True

    # Check database
    try:
        start_time = time.time()
        await db.execute(text("SELECT 1"))
        db_response_time = time.time() - start_time
        checks["database"] = {
            "status": "up",
            "response_time_ms": round(db_response_time * 1000, 2),
        }
    except Exception as e:
        all_healthy = False
        logger.error(f"Readiness check: database failed: {e}")
        checks["database"] = {"status": "down"}

    # Check Redis
    redis_client = None
    try:
        redis_client = _get_redis_client()
        start_time = time.time()
        redis_client.ping()
        redis_response_time = time.time() - start_time
        checks["redis"] = {
            "status": "up",
            "response_time_ms": round(redis_response_time * 1000, 2),
        }
    except Exception as e:
        all_healthy = False
        logger.error(f"Readiness check: Redis failed: {e}")
        checks["redis"] = {"status": "down"}
    finally:
        if redis_client:
            redis_client.close()

    status = "ready" if all_healthy else "not_ready"
    status_code = 200 if all_healthy else 503

    return JSONResponse(
        status_code=status_code,
        content={
            "status": status,
            "checks": checks,
            "timestamp": datetime.now(UTC).isoformat(),
        },
    )
