"""
Router for API v1 endpoints.
"""

from fastapi import APIRouter

from app.api.v1.endpoints.archives import router as archives_router
from app.api.v1.endpoints.auth import router as auth_router
from app.api.v1.endpoints.datasets import router as datasets_router
from app.api.v1.endpoints.harvest import router as harvest_router
from app.api.v1.endpoints.harvest_status import router as harvest_status_router
from app.api.v1.endpoints.health import router as health_router
from app.api.v1.endpoints.links import router as links_router
from app.api.v1.endpoints.providers import router as providers_router
from app.api.v1.endpoints.snapshots import router as snapshots_router
from app.api.v1.endpoints.tasks import router as tasks_router
from app.api.v1.endpoints.users import router as users_router
from app.api.v1.endpoints.validation_stats import router as validation_stats_router
from app.api.v1.endpoints.validators import router as validators_router

# Create the API v1 router
api_v1_router = APIRouter()

# Auth, health, user, and harvest endpoints (no prefix - maintains existing URL paths)
api_v1_router.include_router(auth_router, tags=["authentication"])
api_v1_router.include_router(harvest_router, tags=["harvest"])
api_v1_router.include_router(health_router, tags=["health"])
api_v1_router.include_router(users_router, tags=["users"])

# Public, read-only batch validation summary for the search interface (no prefix:
# sits next to the harvest feed as a server-to-server contract).
api_v1_router.include_router(validation_stats_router, tags=["validation-stats"])

# Domain-specific endpoint routers with prefixes
api_v1_router.include_router(tasks_router, prefix="/tasks", tags=["tasks"])
api_v1_router.include_router(validators_router, prefix="/validators", tags=["validators"])
api_v1_router.include_router(harvest_status_router, prefix="/datasets", tags=["harvest-status"])

# Use snapshot-based statistics router for both public and authenticated endpoints
api_v1_router.include_router(snapshots_router, prefix="/statistics", tags=["statistics"])

# Data provider routers (main provider endpoints and sub-resources)
api_v1_router.include_router(providers_router, prefix="/data-providers", tags=["data-providers"])
api_v1_router.include_router(archives_router, prefix="/data-providers", tags=["xml-archives"])
api_v1_router.include_router(links_router, prefix="/data-providers", tags=["useful-links"])
api_v1_router.include_router(datasets_router, prefix="/data-providers", tags=["datasets"])
