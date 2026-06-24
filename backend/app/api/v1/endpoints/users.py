"""
User management API endpoints.

This module contains endpoints for user CRUD operations,
user permissions, and provider associations.
"""

import logging
from typing import Annotated

from fastapi import APIRouter, Body, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import (
    get_filtering_params,
    get_pagination_params,
    get_sorting_params,
)
from app.db import get_db
from app.models import UserModel
from app.schemas import (
    PaginatedResponse,
    ProviderAssociation,
    User,
    UserCreate,
    UserPermissions,
    UserUpdate,
)
from app.schemas.pagination import PaginationParams
from app.security import check_global_admin, get_current_user
from app.services.user_service import UserService
from app.utils.filtering import FilterParam
from app.utils.sorting import SortParam

logger = logging.getLogger("api")

router = APIRouter()

# Allowed fields for filtering and sorting users
USER_FILTER_FIELDS = ["username", "is_global_admin"]
USER_SORT_FIELDS = ["username", "id"]


@router.get(
    "/me/permissions",
    response_model=UserPermissions,
    summary="Get current user's permissions",
)
async def get_user_permissions(
    current_user: Annotated[UserModel, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """
    Retrieve the permissions of the currently authenticated user.
    Returns the username, global admin status, and provider-specific roles.
    """
    service = UserService(db)
    permissions = service.get_user_permissions(current_user)
    return UserPermissions(**permissions)


@router.get("/users", response_model=PaginatedResponse[User], summary="List all users")
async def list_users(
    current_user: Annotated[UserModel, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
    pagination: Annotated[PaginationParams, Depends(get_pagination_params)],
    filters: Annotated[list[FilterParam], Depends(get_filtering_params(USER_FILTER_FIELDS))],
    sorts: Annotated[list[SortParam], Depends(get_sorting_params(USER_SORT_FIELDS))],
):
    """
    List all users in the system. Requires global admin privileges.

    Supports standardized filtering with filter[field]=value or filter[field][op]=value syntax,
    sorting with sort=field:direction syntax, and cursor-based pagination.

    **Filterable fields:** username, is_global_admin
    **Sortable fields:** username, id
    **Filter operators:** eq, ne, gt, gte, lt, lte, like, in
    """
    check_global_admin(current_user)
    service = UserService(db)
    return await service.list_users(filters=filters, sorts=sorts, pagination=pagination)


@router.get("/users/{username}", response_model=User, summary="Get user by username")
async def get_user_endpoint(
    username: str,
    current_user: Annotated[UserModel, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """
    Retrieve a user by their username. Requires global admin privileges.
    """
    check_global_admin(current_user)
    service = UserService(db)
    return await service.get_user_or_404(username)


@router.put("/users/{username}", response_model=User, summary="Update user")
async def update_user(
    username: str,
    user: UserUpdate,
    current_user: Annotated[UserModel, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
    old_password: Annotated[str | None, Body()] = None,
):
    """
    Update a user's information. Requires global admin privileges.
    If updating own password, provide `old_password` for verification.
    - **username**: The username of the user to update
    - **password**: Optional new password
    - **provider_roles**: Optional updated provider roles
    - **is_global_admin**: Optional updated global admin status
    - **old_password**: Required if updating own password
    """
    check_global_admin(current_user)
    service = UserService(db)
    return await service.update_user(
        username=username,
        password=user.password,
        provider_roles=user.provider_roles,
        is_global_admin=user.is_global_admin,
        old_password=old_password,
        current_username=current_user.username,
    )


@router.post("/users", response_model=User, status_code=201, summary="Create a new user")
async def create_user(
    user: UserCreate,
    current_user: Annotated[UserModel, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """
    Create a new user. Requires global admin privileges.
    - **username**: Unique username for the user
    - **password**: User's password
    - **provider_roles**: Optional dictionary of provider IDs to roles (e.g., {"1": "admin"})
    - **is_global_admin**: Optional boolean to set global admin status
    """
    check_global_admin(current_user)
    service = UserService(db)
    return await service.create_user(
        username=user.username,
        password=user.password,
        provider_roles=user.provider_roles,
        is_global_admin=user.is_global_admin,
    )


@router.delete("/users/{username}", status_code=204, summary="Delete user")
async def delete_user(
    username: str,
    current_user: Annotated[UserModel, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """
    Delete a user by username. Requires global admin privileges.
    """
    check_global_admin(current_user)
    service = UserService(db)
    await service.delete_user(username)
    return


# Provider Association Endpoints
@router.post(
    "/users/{username}/data-providers",
    response_model=User,
    summary="Add provider association",
)
async def add_provider_association(
    username: str,
    association: ProviderAssociation,
    current_user: Annotated[UserModel, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """
    Add a provider association to a user. Requires global admin privileges.
    - **provider_id**: The ID of the provider
    - **role**: The role to assign (e.g., "admin", "curator")
    """
    check_global_admin(current_user)
    service = UserService(db)
    return await service.add_provider_association(
        username=username, provider_id=association.provider_id, role=association.role
    )


@router.put(
    "/users/{username}/data-providers/{provider_id}",
    response_model=User,
    summary="Update provider association",
)
async def update_provider_association(
    username: str,
    provider_id: int,
    association: ProviderAssociation,
    current_user: Annotated[UserModel, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """
    Update a provider association for a user. Requires global admin privileges.
    - **provider_id**: The ID of the provider to update
    - **role**: The new role to assign
    """
    check_global_admin(current_user)
    service = UserService(db)
    return await service.update_provider_association(
        username=username, provider_id=provider_id, role=association.role
    )


@router.delete(
    "/users/{username}/data-providers/{provider_id}",
    response_model=User,
    summary="Remove provider association",
)
async def remove_provider_association(
    username: str,
    provider_id: int,
    current_user: Annotated[UserModel, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """
    Remove a provider association from a user. Requires global admin privileges.
    - **provider_id**: The ID of the provider to remove
    """
    check_global_admin(current_user)
    service = UserService(db)
    return await service.remove_provider_association(username=username, provider_id=provider_id)
