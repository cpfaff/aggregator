"""
Health check API endpoint.

This module contains the health check endpoint for monitoring
the API and database connection status.
"""

import logging
import time
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_db

logger = logging.getLogger("api")

router = APIRouter()


@router.get("/health-check", status_code=200, summary="Health check")
async def health_check(db: AsyncSession = Depends(get_db)):
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
            "version": "1.9.0",
            "timestamp": datetime.utcnow().isoformat(),
        }
    except Exception as e:
        logger.error(f"Health check failed: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=503,
            detail={
                "status": "unhealthy",
                "database": {"status": "disconnected", "error": str(e)},
                "timestamp": datetime.utcnow().isoformat(),
            },
        )
