"""
Router for API v1 endpoints.
"""
from fastapi import APIRouter

from app.api.v1.endpoints.tasks import router as tasks_router
from app.api.v1.endpoints.validators import router as validators_router

# Create the API v1 router
api_v1_router = APIRouter()

# Include all v1 endpoint routers
api_v1_router.include_router(tasks_router, prefix="/tasks", tags=["tasks"])
api_v1_router.include_router(validators_router, prefix="/validators", tags=["validators"])

# As you migrate existing endpoints from main.py, you can add them here
# Example:
# api_v1_router.include_router(users_router, prefix="/users", tags=["users"])
