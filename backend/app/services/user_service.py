"""
User service for managing user operations.

This service extracts user management business logic from route handlers,
providing a clean interface for user CRUD and permission management.
"""
import logging
from typing import Dict, List, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import HTTPException

from app.models import UserModel
from app.security import (
    get_user_model,
    get_password_hash,
    verify_password,
    normalize_provider_roles,
)
from app.core.cache import invalidate_cache

logger = logging.getLogger(__name__)


class UserService:
    """Service for user management operations."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def list_users(
        self,
        skip: int = 0,
        limit: int = 100
    ) -> List[UserModel]:
        """
        List all users with pagination.

        Args:
            skip: Number of users to skip
            limit: Maximum number of users to return

        Returns:
            List of UserModel instances
        """
        result = await self.db.execute(
            select(UserModel).offset(skip).limit(limit)
        )
        return list(result.scalars().all())

    async def get_user_by_username(
        self,
        username: str
    ) -> Optional[UserModel]:
        """
        Get a user by username.

        Args:
            username: Username to look up

        Returns:
            UserModel if found, None otherwise
        """
        return await get_user_model(username, self.db)

    async def get_user_or_404(
        self,
        username: str
    ) -> UserModel:
        """
        Get a user by username or raise 404.

        Args:
            username: Username to look up

        Returns:
            UserModel if found

        Raises:
            HTTPException: 404 if user not found
        """
        user = await self.get_user_by_username(username)
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        return user

    async def create_user(
        self,
        username: str,
        password: str,
        provider_roles: Optional[Dict[str, str]] = None,
        is_global_admin: bool = False
    ) -> UserModel:
        """
        Create a new user.

        Args:
            username: Unique username
            password: User's password (will be hashed)
            provider_roles: Optional dict of provider IDs to roles
            is_global_admin: Whether user is global admin

        Returns:
            Created UserModel

        Raises:
            HTTPException: 400 if username already exists
        """
        # Check if user already exists
        existing = await self.get_user_by_username(username)
        if existing:
            raise HTTPException(status_code=400, detail="Username already exists")

        # Hash password
        hashed_pw = get_password_hash(password)

        # Normalize provider roles
        normalized_roles = normalize_provider_roles(provider_roles)

        # Create user
        user = UserModel(
            username=username,
            hashed_password=hashed_pw,
            provider_roles=normalized_roles,
            is_global_admin=is_global_admin,
        )

        self.db.add(user)
        await self.db.commit()
        await self.db.refresh(user)

        # Invalidate user list cache
        invalidate_cache("users")

        return user

    async def update_user_password(
        self,
        user: UserModel,
        new_password: str,
        old_password: Optional[str] = None,
        current_username: Optional[str] = None
    ) -> UserModel:
        """
        Update a user's password.

        Args:
            user: User to update
            new_password: New password (will be hashed)
            old_password: Required if updating own password
            current_username: Username of user making the change

        Returns:
            Updated UserModel

        Raises:
            HTTPException: 400 if old password verification fails
        """
        # If updating own password, verify old password
        if current_username and current_username == user.username:
            if not old_password or not verify_password(old_password, user.hashed_password):
                raise HTTPException(status_code=400, detail="Old password is incorrect")

        # Hash and set new password
        hashed_pw = get_password_hash(new_password)
        if hashed_pw:
            user.hashed_password = hashed_pw

        return user

    async def update_user(
        self,
        username: str,
        password: Optional[str] = None,
        provider_roles: Optional[Dict[str, str]] = None,
        is_global_admin: Optional[bool] = None,
        old_password: Optional[str] = None,
        current_username: Optional[str] = None
    ) -> UserModel:
        """
        Update a user's information.

        Args:
            username: Username of user to update
            password: Optional new password
            provider_roles: Optional updated provider roles
            is_global_admin: Optional updated admin status
            old_password: Required if updating own password
            current_username: Username of user making the change

        Returns:
            Updated UserModel

        Raises:
            HTTPException: 404 if user not found, 400 if old password incorrect
        """
        user = await self.get_user_or_404(username)

        # Update password if provided
        if password is not None:
            await self.update_user_password(
                user,
                password,
                old_password,
                current_username
            )

        # Update provider roles if provided
        if provider_roles is not None:
            user.provider_roles = normalize_provider_roles(provider_roles)

        # Update admin status if provided
        if is_global_admin is not None:
            user.is_global_admin = is_global_admin

        self.db.add(user)
        await self.db.commit()
        await self.db.refresh(user)

        # Invalidate user cache
        invalidate_cache(f"user:{username}")

        return user

    async def delete_user(
        self,
        username: str
    ) -> None:
        """
        Delete a user by username.

        Args:
            username: Username of user to delete

        Raises:
            HTTPException: 404 if user not found
        """
        user = await self.get_user_or_404(username)

        await self.db.delete(user)
        await self.db.commit()

        # Invalidate caches
        invalidate_cache("users")
        invalidate_cache(f"user:{username}")

    async def add_provider_association(
        self,
        username: str,
        provider_id: int,
        role: str
    ) -> UserModel:
        """
        Add or update a provider association for a user.

        Args:
            username: Username of user
            provider_id: ID of provider
            role: Role to assign (e.g., "admin", "curator")

        Returns:
            Updated UserModel

        Raises:
            HTTPException: 404 if user not found
        """
        user = await self.get_user_or_404(username)

        # Get current roles and add/update the new one
        roles = normalize_provider_roles(user.provider_roles)
        roles[str(provider_id)] = role
        user.provider_roles = roles

        self.db.add(user)
        await self.db.commit()
        await self.db.refresh(user)

        # Invalidate user cache
        invalidate_cache(f"user:{username}")

        return user

    async def update_provider_association(
        self,
        username: str,
        provider_id: int,
        role: str
    ) -> UserModel:
        """
        Update a provider association for a user.

        Args:
            username: Username of user
            provider_id: ID of provider
            role: New role to assign

        Returns:
            Updated UserModel

        Raises:
            HTTPException: 404 if user or association not found
        """
        user = await self.get_user_or_404(username)

        # Check if association exists
        roles = normalize_provider_roles(user.provider_roles)
        if not roles or str(provider_id) not in roles:
            raise HTTPException(status_code=404, detail="User or association not found")

        # Update role
        roles[str(provider_id)] = role
        user.provider_roles = roles

        self.db.add(user)
        await self.db.commit()
        await self.db.refresh(user)

        # Invalidate caches
        invalidate_cache(f"user:{username}")
        invalidate_cache(f"provider:{provider_id}")

        return user

    async def remove_provider_association(
        self,
        username: str,
        provider_id: int
    ) -> UserModel:
        """
        Remove a provider association from a user.

        Args:
            username: Username of user
            provider_id: ID of provider to remove

        Returns:
            Updated UserModel

        Raises:
            HTTPException: 404 if user or association not found
        """
        user = await self.get_user_or_404(username)

        # Check if association exists
        roles = normalize_provider_roles(user.provider_roles)
        if not roles or str(provider_id) not in roles:
            raise HTTPException(status_code=404, detail="User or association not found")

        # Remove association
        roles.pop(str(provider_id))
        user.provider_roles = roles

        self.db.add(user)
        await self.db.commit()
        await self.db.refresh(user)

        # Invalidate caches
        invalidate_cache(f"user:{username}")
        invalidate_cache(f"provider:{provider_id}")

        return user

    def get_user_permissions(
        self,
        user: UserModel
    ) -> Dict[str, any]:
        """
        Get permissions for a user.

        Args:
            user: User to get permissions for

        Returns:
            Dictionary with username, is_global_admin, and provider_roles
        """
        return {
            "username": user.username,
            "is_global_admin": user.is_global_admin,
            "provider_roles": normalize_provider_roles(user.provider_roles),
        }
