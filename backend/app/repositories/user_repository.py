"""
Repository for user data access operations.
"""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import UserModel
from app.repositories.base import BaseRepository


class UserRepository(BaseRepository[UserModel]):
    """Data access layer for user operations."""

    def __init__(self, db: AsyncSession):
        super().__init__(UserModel, db)

    async def get_by_username(self, username: str) -> UserModel | None:
        """Get a user by username."""
        result = await self.db.execute(select(UserModel).where(UserModel.username == username))
        return result.scalar_one_or_none()
