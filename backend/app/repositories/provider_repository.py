"""
Repository for data provider data access operations.
"""

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models import DataProviderModel, DatasetModel
from app.repositories.base import BaseRepository
from app.schemas.pagination import PaginationParams
from app.utils.filtering import FilterParam
from app.utils.pagination import decode_cursor, encode_cursor
from app.utils.query_utils import apply_filters, apply_sorts
from app.utils.sorting import SortParam


class ProviderRepository(BaseRepository[DataProviderModel]):
    """Data access layer for provider operations."""

    # Field mappings for filtering and sorting
    FILTER_FIELD_MAP = {
        "name": DataProviderModel.name,
        "datacenter": DataProviderModel.datacenter,
        "is_data_center": DataProviderModel.isDataCenter,
    }

    SORT_FIELD_MAP = {
        "name": DataProviderModel.name,
        "datacenter": DataProviderModel.datacenter,
        "id": DataProviderModel.id,
    }

    def __init__(self, db: AsyncSession):
        super().__init__(DataProviderModel, db)

    async def get_by_id(self, id: int) -> DataProviderModel | None:
        """Get a provider by ID with related datasets loaded."""
        result = await self.db.execute(
            select(DataProviderModel)
            .where(DataProviderModel.id == id)
            .options(
                selectinload(DataProviderModel.datasets).selectinload(DatasetModel.xmlArchives),
                selectinload(DataProviderModel.datasets).selectinload(DatasetModel.usefulLinks),
            )
        )
        return result.scalar_one_or_none()

    async def get_by_short_name(self, short_name: str) -> DataProviderModel | None:
        """Get a provider by short name."""
        result = await self.db.execute(
            select(DataProviderModel).where(DataProviderModel.shortName == short_name)
        )
        return result.scalar_one_or_none()

    async def list_for_user(
        self,
        allowed_provider_ids: list[int] | None,
        filters: list[FilterParam] | None = None,
        sorts: list[SortParam] | None = None,
        pagination: PaginationParams | None = None,
    ) -> tuple[list[DataProviderModel], int, str | None, str | None]:
        """
        List providers with optional filtering by user permissions.

        Args:
            allowed_provider_ids: List of provider IDs the user can access.
                                  None means user can access all providers.
            filters: List of filter parameters
            sorts: List of sort parameters
            pagination: Pagination parameters (limit, after, before cursors)

        Returns:
            Tuple of (items, total_count, next_cursor, previous_cursor)
        """
        if pagination is None:
            pagination = PaginationParams()

        # Base query for filtering
        base_query = select(DataProviderModel)

        # Apply filters if provided
        if filters:
            base_query = apply_filters(base_query, filters, self.FILTER_FIELD_MAP)

        # Apply permission filtering if not a global admin
        if allowed_provider_ids is not None:
            if not allowed_provider_ids:
                return [], 0, None, None
            base_query = base_query.filter(DataProviderModel.id.in_(allowed_provider_ids))

        # Get total count
        count_query = select(func.count()).select_from(base_query.subquery())
        total_result = await self.db.execute(count_query)
        total_count = total_result.scalar() or 0

        # Add eager loading for related entities
        query = base_query.options(
            selectinload(DataProviderModel.datasets).selectinload(DatasetModel.xmlArchives),
            selectinload(DataProviderModel.datasets).selectinload(DatasetModel.usefulLinks),
        )

        # Apply cursor-based pagination
        if pagination.after:
            cursor_data = decode_cursor(pagination.after)
            if cursor_data and "id" in cursor_data:
                query = query.filter(DataProviderModel.id > cursor_data["id"])

        if pagination.before:
            cursor_data = decode_cursor(pagination.before)
            if cursor_data and "id" in cursor_data:
                query = query.filter(DataProviderModel.id < cursor_data["id"])

        # Apply sorting - custom sorts first, then ID for consistent pagination
        if sorts:
            query = apply_sorts(query, sorts, self.SORT_FIELD_MAP)
        # Always add ID as final sort for deterministic pagination
        query = query.order_by(DataProviderModel.id)

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
