"""
Shared API dependencies.

This module contains shared dependencies used across multiple API endpoint modules,
including rate limiting, CSRF protection, and permission checking.
"""

from typing import Annotated

from fastapi import Depends, Query, Request
from fastapi_csrf_protect import CsrfProtect
from pydantic_settings import BaseSettings
from slowapi import Limiter
from slowapi.util import get_remote_address

from app.core.config import settings
from app.models import UserModel
from app.schemas.pagination import PaginationParams
from app.security import check_provider_permission, get_current_user
from app.utils.filtering import FilterParam, parse_filter_params
from app.utils.sorting import SortParam, parse_sort_params

__all__ = [
    "limiter",
    "csrf_protect",
    "provider_permission",
    "get_pagination_params",
    "get_filtering_params",
    "get_sorting_params",
]


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
        provider_id: int, current_user: Annotated[UserModel, Depends(get_current_user)]
    ):
        check_provider_permission(provider_id, current_user, operation)
        return current_user

    return dependency


# ------------------- Pagination -------------------
def get_pagination_params(
    limit: int = Query(default=20, ge=1, le=100, description="Items per page (max 100)"),
    after: str | None = Query(default=None, description="Cursor for next page"),
    before: str | None = Query(default=None, description="Cursor for previous page"),
) -> PaginationParams:
    """FastAPI dependency for pagination query parameters."""
    return PaginationParams(limit=limit, after=after, before=before)


# ------------------- Filtering -------------------
def get_filtering_params(allowed_fields: list[str], strict: bool = True):
    """
    Dependency factory for filtering parameters.

    Args:
        allowed_fields: List of field names that can be filtered
        strict: If True, raise error for disallowed fields; if False, ignore them

    Returns:
        A dependency function that parses filter query parameters
    """

    def dependency(request: Request) -> list[FilterParam]:
        return parse_filter_params(
            dict(request.query_params),
            allowed_fields=allowed_fields,
            strict=strict,
        )

    return dependency


# ------------------- Sorting -------------------
def get_sorting_params(allowed_fields: list[str], strict: bool = True):
    """
    Dependency factory for sorting parameters.

    Args:
        allowed_fields: List of field names that can be sorted
        strict: If True, raise error for disallowed fields; if False, ignore them

    Returns:
        A dependency function that parses sort query parameter
    """

    def dependency(
        sort: str | None = Query(
            default=None, description="Sort fields (e.g., name:asc,created:desc)"
        ),
    ) -> list[SortParam]:
        return parse_sort_params(sort, allowed_fields=allowed_fields, strict=strict)

    return dependency
