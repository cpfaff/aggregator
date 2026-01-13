"""
Router for API v1 endpoints.
"""
from fastapi import APIRouter

from app.api.v1.endpoints.auth import router as auth_router
from app.api.v1.endpoints.health import router as health_router
from app.api.v1.endpoints.tasks import router as tasks_router
from app.api.v1.endpoints.validators import router as validators_router
from app.api.v1.endpoints.snapshots import router as snapshots_router

# Create the API v1 router
api_v1_router = APIRouter()

# Auth and health endpoints (no prefix - maintains existing URL paths)
api_v1_router.include_router(auth_router, tags=["authentication"])
api_v1_router.include_router(health_router, tags=["health"])

# Domain-specific endpoint routers with prefixes
api_v1_router.include_router(tasks_router, prefix="/tasks", tags=["tasks"])
api_v1_router.include_router(validators_router, prefix="/validators", tags=["validators"])

# Use snapshot-based statistics router for both public and authenticated endpoints
api_v1_router.include_router(snapshots_router, prefix="/statistics", tags=["statistics"])
