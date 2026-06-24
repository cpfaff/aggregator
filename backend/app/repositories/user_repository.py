"""
Repository for user data access operations.
"""

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import UserModel
from app.repositories.base import BaseRepository
from app.schemas.pagination import PaginationParams
from app.utils.filtering import FilterParam
from app.utils.pagination import build_keyset_order, paginate_keyset
from app.utils.query_utils import apply_filters
from app.utils.sorting import SortParam


class UserRepository(BaseRepository[UserModel]):
    """Data access layer for user operations."""

    # Field mappings for filtering and sorting
    FILTER_FIELD_MAP = {
        "username": UserModel.username,
        "is_global_admin": UserModel.is_global_admin,
    }

    SORT_FIELD_MAP = {
        "username": UserModel.username,
        "id": UserModel.id,
    }

    def __init__(self, db: AsyncSession):
        super().__init__(UserModel, db)

    async def get_by_username(self, username: str) -> UserModel | None:
        """Get a user by username."""
        result = await self.db.execute(select(UserModel).where(UserModel.username == username))
        return result.scalar_one_or_none()

    async def list_paginated(
        self,
        filters: list[FilterParam] | None = None,
        sorts: list[SortParam] | None = None,
        pagination: PaginationParams | None = None,
    ) -> tuple[list[UserModel], int, str | None, str | None]:
        """
        List users with cursor-based pagination.

        Args:
            filters: List of filter parameters
            sorts: List of sort parameters
            pagination: Pagination parameters (limit, after, before cursors)

        Returns:
            Tuple of (items, total_count, next_cursor, previous_cursor)
        """
        if pagination is None:
            pagination = PaginationParams()

        # Build base query
        base_query = select(UserModel)

        # Apply filters if provided
        if filters:
            base_query = apply_filters(base_query, filters, self.FILTER_FIELD_MAP)

        # Get total count
        count_query = select(func.count()).select_from(base_query.subquery())
        total_result = await self.db.execute(count_query)
        total_count = total_result.scalar() or 0

        # Keyset pagination keyed on the same (sort..., id) tuple as ORDER BY
        # (B6, B8).
        order = build_keyset_order(sorts, self.SORT_FIELD_MAP, UserModel.id)
        items, next_cursor, previous_cursor = await paginate_keyset(
            self.db, base_query, order, pagination
        )

        return items, total_count, next_cursor, previous_cursor
