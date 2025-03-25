"""
Main API router that combines all versioned API routers.
This router serves as the central point for organizing all API endpoints,
facilitating easy versioning and organization of the API.
"""
from fastapi import APIRouter

from app.api.v1.router import api_v1_router

# Create the main API router
api_router = APIRouter()

# Include versioned API routers
api_router.include_router(api_v1_router, prefix="/v1")

# For backward compatibility, you can also include the v1 router without prefix
# This allows existing clients to continue using the API without the /v1 prefix
# Remove this when all clients have migrated to the versioned API
# api_router.include_router(api_v1_router)
