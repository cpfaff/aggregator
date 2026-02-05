"""
Repository for validation job and archive data access operations.
"""

from sqlalchemy import desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import ValidationJobModel, XmlArchiveModel
from app.repositories.base import BaseRepository
from app.schemas.pagination import PaginationParams
from app.utils.filtering import FilterParam
from app.utils.pagination import decode_cursor, encode_cursor
from app.utils.query_utils import apply_filters, apply_sorts
from app.utils.sorting import SortParam


class ValidationRepository(BaseRepository[ValidationJobModel]):
    """Data access layer for validation job operations."""

    # Field mappings for filtering and sorting
    FILTER_FIELD_MAP = {
        "archive_id": ValidationJobModel.archive_id,
        "status": ValidationJobModel.status,
    }

    SORT_FIELD_MAP = {
        "id": ValidationJobModel.id,
        "created_at": ValidationJobModel.created_at,
        "status": ValidationJobModel.status,
    }

    def __init__(self, db: AsyncSession):
        super().__init__(ValidationJobModel, db)

    async def get_archive_by_id(self, archive_id: int) -> XmlArchiveModel | None:
        """Get an XML archive by ID."""
        result = await self.db.execute(
            select(XmlArchiveModel).where(XmlArchiveModel.id == archive_id)
        )
        return result.scalar_one_or_none()

    async def list_jobs(
        self,
        filters: list[FilterParam] | None = None,
        sorts: list[SortParam] | None = None,
        pagination: PaginationParams | None = None,
    ) -> tuple[list[ValidationJobModel], int, str | None, str | None]:
        """
        List validation jobs with optional filtering and cursor-based pagination.

        Args:
            filters: List of filter parameters
            sorts: List of sort parameters
            pagination: Pagination parameters (limit, after, before cursors)

        Returns:
            Tuple of (items, total_count, next_cursor, previous_cursor)
        """
        if pagination is None:
            pagination = PaginationParams()

        # Base query for filtering
        base_query = select(ValidationJobModel)

        # Apply filters if provided
        if filters:
            base_query = apply_filters(base_query, filters, self.FILTER_FIELD_MAP)

        # Get total count
        count_query = select(func.count()).select_from(base_query.subquery())
        total_result = await self.db.execute(count_query)
        total_count = total_result.scalar() or 0

        # Start with base query
        query = base_query

        # Apply custom sorting if provided
        if sorts:
            query = apply_sorts(query, sorts, self.SORT_FIELD_MAP)

        # Order by ID descending (most recent first) as final sort
        query = query.order_by(desc(ValidationJobModel.id))

        # Apply cursor-based pagination (note: reversed direction since ordering is DESC)
        if pagination.after:
            cursor_data = decode_cursor(pagination.after)
            if cursor_data and "id" in cursor_data:
                query = query.filter(ValidationJobModel.id < cursor_data["id"])

        if pagination.before:
            cursor_data = decode_cursor(pagination.before)
            if cursor_data and "id" in cursor_data:
                query = query.filter(ValidationJobModel.id > cursor_data["id"])

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

    async def get_latest_archive_for_dataset(self, dataset_id: int) -> XmlArchiveModel | None:
        """Get the latest archive for a dataset."""
        result = await self.db.execute(
            select(XmlArchiveModel)
            .where(XmlArchiveModel.dataset_id == dataset_id)
            .where(XmlArchiveModel.isLatest.is_(True))
        )
        return result.scalars().first()

    async def get_pending_jobs_for_archive(self, archive_id: int) -> list[ValidationJobModel]:
        """Get all pending validation jobs for an archive."""
        result = await self.db.execute(
            select(ValidationJobModel)
            .where(ValidationJobModel.archive_id == archive_id)
            .where(ValidationJobModel.status == "pending")
            .order_by(desc(ValidationJobModel.created_at))
        )
        return list(result.scalars().all())

    async def find_completed_job_by_task_prefix(
        self, archive_id: int, task_id_prefix: str
    ) -> ValidationJobModel | None:
        """Find a completed validation job matching a task ID prefix."""
        result = await self.db.execute(
            select(ValidationJobModel)
            .where(ValidationJobModel.archive_id == archive_id)
            .where(ValidationJobModel.status == "completed")
            .where(ValidationJobModel.task_id.startswith(task_id_prefix))
        )
        return result.scalars().first()

    async def get_latest_non_obsolete_job(self, archive_id: int) -> ValidationJobModel | None:
        """Get the most recent non-obsolete validation job for an archive."""
        result = await self.db.execute(
            select(ValidationJobModel)
            .where(ValidationJobModel.archive_id == archive_id)
            .where(ValidationJobModel.status != "obsolete")
            .order_by(desc(ValidationJobModel.created_at))
            .limit(1)
        )
        return result.scalars().first()

    async def find_active_validation(self, archive_id: int) -> ValidationJobModel | None:
        """Find existing pending or running validation for an archive."""
        result = await self.db.execute(
            select(ValidationJobModel)
            .where(ValidationJobModel.archive_id == archive_id)
            .where(ValidationJobModel.status.in_(["pending", "running"]))
            .order_by(desc(ValidationJobModel.created_at))
            .limit(1)
        )
        return result.scalars().first()
