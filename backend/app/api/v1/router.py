"""
Router for API v1 endpoints.
"""
from fastapi import APIRouter

from app.api.v1.endpoints.tasks import router as tasks_router
from app.api.v1.endpoints.validators import router as validators_router
from app.api.v1.endpoints.unified_statistics import router as unified_statistics_router
# Keep old imports for backward compatibility during migration
# from app.api.v1.endpoints.statistics import router as statistics_router
# from app.api.v1.endpoints.public_statistics import router as public_statistics_router

# Create the API v1 router
api_v1_router = APIRouter()

# Include all v1 endpoint routers
api_v1_router.include_router(tasks_router, prefix="/tasks", tags=["tasks"])
api_v1_router.include_router(validators_router, prefix="/validators", tags=["validators"])

# Use unified statistics router for both public and authenticated endpoints
# This provides backward compatibility while consolidating the code
api_v1_router.include_router(unified_statistics_router, prefix="/statistics", tags=["statistics"])
api_v1_router.include_router(unified_statistics_router, prefix="/public-statistics", tags=["public-statistics"])

# As you migrate existing endpoints from main.py, you can add them here
# Example:
# api_v1_router.include_router(users_router, prefix="/users", tags=["users"])
