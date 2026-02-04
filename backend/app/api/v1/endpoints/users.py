"""
User management API endpoints.

This module contains endpoints for user CRUD operations,
user permissions, and provider associations.
"""

import logging

from fastapi import APIRouter, Body, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import csrf_protect
from app.core.cache import invalidate_cache
from app.db import get_db
from app.models import UserModel
from app.schemas import (
    ProviderAssociation,
    User,
    UserCreate,
    UserPermissions,
    UserUpdate,
)
from app.security import (
    check_global_admin,
    get_current_user,
    get_password_hash,
    get_user_model,
    normalize_provider_roles,
    verify_password,
)

logger = logging.getLogger("api")

router = APIRouter()


@router.get(
    "/me/permissions",
    response_model=UserPermissions,
    summary="Get current user's permissions",
)
async def get_user_permissions(current_user: UserModel = Depends(get_current_user)):
    """
    Retrieve the permissions of the currently authenticated user.
    Returns the username, global admin status, and provider-specific roles.
    """
    provider_roles = normalize_provider_roles(current_user.provider_roles)
    return UserPermissions(
        username=current_user.username,
        is_global_admin=current_user.is_global_admin,
        provider_roles=provider_roles,
    )


@router.get("/users", response_model=list[User], summary="List all users")
async def list_users(
    current_user: UserModel = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    skip: int = Query(0, ge=0, description="Number of users to skip"),
    limit: int = Query(100, ge=1, le=1000, description="Maximum number of users to return"),
):
    """
    List all users in the system. Requires global admin privileges.

    Supports pagination with skip/limit parameters.
    """
    check_global_admin(current_user)
    result = await db.execute(select(UserModel).offset(skip).limit(limit))
    return result.scalars().all()


@router.get("/users/{username}", response_model=User, summary="Get user by username")
async def get_user_endpoint(
    username: str,
    current_user: UserModel = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Retrieve a user by their username. Requires global admin privileges.
    """
    check_global_admin(current_user)
    user_obj = await get_user_model(username, db)
    if not user_obj:
        raise HTTPException(status_code=404, detail="User not found")
    return user_obj


@csrf_protect.validate_csrf
@router.put("/users/{username}", response_model=User, summary="Update user")
async def update_user(
    username: str,
    user: UserUpdate,
    old_password: str | None = Body(None),
    current_user: UserModel = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
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
    user_obj = await get_user_model(username, db)
    if not user_obj:
        raise HTTPException(status_code=404, detail="User not found")
    if user.password is not None:
        if current_user.username == username:
            if not old_password or not verify_password(old_password, user_obj.hashed_password):
                raise HTTPException(status_code=400, detail="Old password is incorrect")
        hashed_pw = get_password_hash(user.password)
        if hashed_pw:
            user_obj.hashed_password = hashed_pw
    if user.provider_roles is not None:
        user_obj.provider_roles = normalize_provider_roles(user.provider_roles)
    if user.is_global_admin is not None:
        user_obj.is_global_admin = user.is_global_admin
    db.add(user_obj)
    await db.commit()
    await db.refresh(user_obj)

    # Invalidate any cached data related to this user
    invalidate_cache(f"user:{username}")

    return user_obj


@csrf_protect.validate_csrf
@router.post("/users", response_model=User, status_code=201, summary="Create a new user")
async def create_user(
    user: UserCreate,
    current_user: UserModel = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Create a new user. Requires global admin privileges.
    - **username**: Unique username for the user
    - **password**: User's password
    - **provider_roles**: Optional dictionary of provider IDs to roles (e.g., {"1": "admin"})
    - **is_global_admin**: Optional boolean to set global admin status
    """
    check_global_admin(current_user)
    existing = await get_user_model(user.username, db)
    if existing:
        raise HTTPException(status_code=400, detail="Username already exists")
    hashed_pw = get_password_hash(user.password)
    provider_roles = normalize_provider_roles(user.provider_roles)
    user_obj = UserModel(
        username=user.username,
        hashed_password=hashed_pw,
        provider_roles=provider_roles,
        is_global_admin=user.is_global_admin,
    )
    db.add(user_obj)
    await db.commit()
    await db.refresh(user_obj)

    # Invalidate user list cache
    invalidate_cache("users")

    return user_obj


@csrf_protect.validate_csrf
@router.delete("/users/{username}", status_code=204, summary="Delete user")
async def delete_user(
    username: str,
    current_user: UserModel = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Delete a user by username. Requires global admin privileges.
    """
    check_global_admin(current_user)
    user_obj = await get_user_model(username, db)
    if user_obj:
        await db.delete(user_obj)
        await db.commit()

        # Invalidate user caches
        invalidate_cache("users")
        invalidate_cache(f"user:{username}")
    else:
        raise HTTPException(status_code=404, detail="User not found")
    return


# Provider Association Endpoints
@csrf_protect.validate_csrf
@router.post(
    "/users/{username}/data-providers",
    response_model=User,
    summary="Add provider association",
)
async def add_provider_association(
    username: str,
    association: ProviderAssociation,
    current_user: UserModel = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Add a provider association to a user. Requires global admin privileges.
    - **provider_id**: The ID of the provider
    - **role**: The role to assign (e.g., "admin", "curator")
    """
    check_global_admin(current_user)
    user_obj = await get_user_model(username, db)
    if not user_obj:
        raise HTTPException(status_code=404, detail="User not found")
    roles = normalize_provider_roles(user_obj.provider_roles)
    roles[str(association.provider_id)] = association.role
    user_obj.provider_roles = roles
    db.add(user_obj)
    await db.commit()
    await db.refresh(user_obj)

    # Invalidate user cache
    invalidate_cache(f"user:{username}")

    return user_obj


@csrf_protect.validate_csrf
@router.put(
    "/users/{username}/data-providers/{provider_id}",
    response_model=User,
    summary="Update provider association",
)
async def update_provider_association(
    username: str,
    provider_id: int,
    association: ProviderAssociation,
    current_user: UserModel = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Update a provider association for a user. Requires global admin privileges.
    - **provider_id**: The ID of the provider to update
    - **role**: The new role to assign
    """
    check_global_admin(current_user)
    user_obj = await get_user_model(username, db)
    if not user_obj or not (
        normalize_provider_roles(user_obj.provider_roles)
        and str(provider_id) in normalize_provider_roles(user_obj.provider_roles)
    ):
        raise HTTPException(status_code=404, detail="User or association not found")
    roles = normalize_provider_roles(user_obj.provider_roles)
    roles[str(provider_id)] = association.role
    user_obj.provider_roles = roles
    db.add(user_obj)
    await db.commit()
    await db.refresh(user_obj)

    # Invalidate user and provider caches
    invalidate_cache(f"user:{username}")
    invalidate_cache(f"provider:{provider_id}")

    return user_obj


@csrf_protect.validate_csrf
@router.delete(
    "/users/{username}/data-providers/{provider_id}",
    response_model=User,
    summary="Remove provider association",
)
async def remove_provider_association(
    username: str,
    provider_id: int,
    current_user: UserModel = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Remove a provider association from a user. Requires global admin privileges.
    - **provider_id**: The ID of the provider to remove
    """
    check_global_admin(current_user)
    user_obj = await get_user_model(username, db)
    if not user_obj or not (
        normalize_provider_roles(user_obj.provider_roles)
        and str(provider_id) in normalize_provider_roles(user_obj.provider_roles)
    ):
        raise HTTPException(status_code=404, detail="User or association not found")
    roles = normalize_provider_roles(user_obj.provider_roles)
    roles.pop(str(provider_id))
    user_obj.provider_roles = roles
    db.add(user_obj)
    await db.commit()
    await db.refresh(user_obj)

    # Invalidate user and provider caches
    invalidate_cache(f"user:{username}")
    invalidate_cache(f"provider:{provider_id}")

    return user_obj
