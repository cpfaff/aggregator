"""
Repository for validation job and archive data access operations.
"""

from sqlalchemy import desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import DatasetModel, ValidationJobModel, XmlArchiveModel
from app.repositories.base import BaseRepository
from app.schemas.pagination import PaginationParams
from app.utils.filtering import FilterParam
from app.utils.pagination import build_keyset_order, paginate_keyset
from app.utils.query_utils import apply_filters
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
        allowed_provider_ids: list[int] | None = None,
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

        # Scope to the user's providers (None = global admin, all). Empty list
        # means no accessible providers -> no jobs (B12).
        if allowed_provider_ids is not None:
            if not allowed_provider_ids:
                return [], 0, None, None
            base_query = (
                base_query.join(
                    XmlArchiveModel, ValidationJobModel.archive_id == XmlArchiveModel.id
                )
                .join(DatasetModel, XmlArchiveModel.dataset_id == DatasetModel.id)
                .where(DatasetModel.provider_id.in_(allowed_provider_ids))
            )

        # Apply filters if provided
        if filters:
            base_query = apply_filters(base_query, filters, self.FILTER_FIELD_MAP)

        # Get total count
        count_query = select(func.count()).select_from(base_query.subquery())
        total_result = await self.db.execute(count_query)
        total_count = total_result.scalar() or 0

        # Keyset pagination, most-recent-first by default (id descending). The
        # cursor and ORDER BY share the same (sort..., id) tuple so pages stay
        # contiguous and ``before`` returns the preceding page (B7, B8).
        order = build_keyset_order(
            sorts, self.SORT_FIELD_MAP, ValidationJobModel.id, id_ascending=False
        )
        items, next_cursor, previous_cursor = await paginate_keyset(
            self.db, base_query, order, pagination
        )

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
