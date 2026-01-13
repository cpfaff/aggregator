"""
Shared API dependencies.

This module contains shared dependencies used across multiple API endpoint modules,
including rate limiting, CSRF protection, and permission checking.
"""
from fastapi import Depends
from pydantic_settings import BaseSettings
from slowapi import Limiter
from slowapi.util import get_remote_address
from fastapi_csrf_protect import CsrfProtect

from app.core.config import settings
from app.models import UserModel
from app.security import check_provider_permission, get_current_user

__all__ = ["limiter", "csrf_protect", "provider_permission"]


# ------------------- Rate Limiting -------------------
# Initialize rate limiter with IP address as the key
limiter = Limiter(key_func=get_remote_address)


# ------------------- CSRF Protection -------------------
class CsrfSettings(BaseSettings):
    """CSRF protection configuration."""
    secret_key: str = settings.SECRET_KEY
    cookie_samesite: str = "lax"
    cookie_secure: bool = False  # Set to True in production with HTTPS


@CsrfProtect.load_config
def get_csrf_config():
    """Load CSRF configuration."""
    return CsrfSettings()


csrf_protect = CsrfProtect()


# ------------------- Permission Dependencies -------------------
def provider_permission(operation: str = "read"):
    """
    Dependency factory for provider permission checking.

    Args:
        operation: The operation type to check ("read", "write", "delete")

    Returns:
        A dependency function that checks if the current user has permission
        for the specified operation on a provider.
    """
    async def dependency(
        provider_id: int, current_user: UserModel = Depends(get_current_user)
    ):
        check_provider_permission(provider_id, current_user, operation)
        return current_user

    return dependency
