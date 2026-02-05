"""
Repository for user data access operations.
"""

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import UserModel
from app.repositories.base import BaseRepository
from app.schemas.pagination import PaginationParams
from app.utils.filtering import FilterParam
from app.utils.pagination import decode_cursor, encode_cursor
from app.utils.query_utils import apply_filters, apply_sorts
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

        # Continue with base query
        query = base_query

        # Apply cursor-based pagination
        if pagination.after:
            cursor_data = decode_cursor(pagination.after)
            if cursor_data and "id" in cursor_data:
                query = query.filter(UserModel.id > cursor_data["id"])

        if pagination.before:
            cursor_data = decode_cursor(pagination.before)
            if cursor_data and "id" in cursor_data:
                query = query.filter(UserModel.id < cursor_data["id"])

        # Apply sorting - custom sorts first, then ID for consistent pagination
        if sorts:
            query = apply_sorts(query, sorts, self.SORT_FIELD_MAP)
        # Always add ID as final sort for deterministic pagination
        query = query.order_by(UserModel.id)

        # Fetch one extra to check if there are more items
        result = await self.db.execute(query.limit(pagination.limit + 1))
        items = list(result.scalars().all())

        # Determine if there are more items
        has_next = len(items) > pagination.limit
        if has_next:
            items = items[: pagination.limit]

        # Generate cursors
        next_cursor = None
        previous_cursor = None

        if items:
            if has_next:
                next_cursor = encode_cursor({"id": items[-1].id})
            if pagination.after:
                previous_cursor = encode_cursor({"id": items[0].id})

        return items, total_count, next_cursor, previous_cursor
