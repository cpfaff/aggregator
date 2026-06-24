"""
Repository for dataset data access operations including cascade deletion.
"""

from sqlalchemy import and_, delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models import (
    DatasetModel,
    UsefulLinkModel,
    ValidationJobModel,
    XmlArchiveModel,
)
from app.models.archive_snapshot import ArchiveSnapshotModel
from app.repositories.base import BaseRepository
from app.schemas.pagination import PaginationParams
from app.utils.filtering import FilterParam
from app.utils.pagination import build_keyset_order, paginate_keyset
from app.utils.query_utils import apply_filters
from app.utils.sorting import SortParam


class DatasetRepository(BaseRepository[DatasetModel]):
    """Data access layer for dataset operations."""

    # Field mappings for filtering and sorting
    FILTER_FIELD_MAP = {
        "title": DatasetModel.title,
        "source": DatasetModel.source,
        "provider_id": DatasetModel.provider_id,
    }

    SORT_FIELD_MAP = {
        "title": DatasetModel.title,
        "source": DatasetModel.source,
        "id": DatasetModel.id,
    }

    def __init__(self, db: AsyncSession):
        super().__init__(DatasetModel, db)

    async def list_for_provider(
        self,
        provider_id: int,
        filters: list[FilterParam] | None = None,
        sorts: list[SortParam] | None = None,
        pagination: PaginationParams | None = None,
    ) -> tuple[list[DatasetModel], int, str | None, str | None]:
        """
        List datasets for a specific provider with pagination and filtering.

        Args:
            provider_id: ID of the data provider
            filters: List of filter parameters
            sorts: List of sort parameters
            pagination: Pagination parameters (limit, after, before cursors)

        Returns:
            Tuple of (items, total_count, next_cursor, previous_cursor)
        """
        if pagination is None:
            pagination = PaginationParams()

        # Base query with provider filter
        base_query = select(DatasetModel).where(DatasetModel.provider_id == provider_id)

        # Apply filters if provided
        if filters:
            base_query = apply_filters(base_query, filters, self.FILTER_FIELD_MAP)

        # Get total count
        count_query = select(func.count()).select_from(base_query.subquery())
        total_result = await self.db.execute(count_query)
        total_count = total_result.scalar() or 0

        # Keyset pagination: the cursor and ORDER BY share the same
        # (sort..., id) tuple, so pages stay contiguous under any sort and
        # ``before`` returns the preceding page (B6, B8).
        order = build_keyset_order(sorts, self.SORT_FIELD_MAP, DatasetModel.id)
        items, next_cursor, previous_cursor = await paginate_keyset(
            self.db,
            base_query,
            order,
            pagination,
            options=[
                selectinload(DatasetModel.xmlArchives),
                selectinload(DatasetModel.usefulLinks),
            ],
        )

        return items, total_count, next_cursor, previous_cursor

    async def get_by_id_and_provider(
        self, dataset_id: int, provider_id: int
    ) -> DatasetModel | None:
        """
        Get a dataset by ID ensuring it belongs to the specified provider.

        Args:
            dataset_id: ID of the dataset
            provider_id: ID of the data provider

        Returns:
            DatasetModel if found, None otherwise
        """
        result = await self.db.execute(
            select(DatasetModel)
            .where(and_(DatasetModel.id == dataset_id, DatasetModel.provider_id == provider_id))
            .options(
                selectinload(DatasetModel.xmlArchives),
                selectinload(DatasetModel.usefulLinks),
            )
        )
        return result.scalar_one_or_none()

    async def get_archive_ids_for_dataset(self, dataset_id: int) -> list[int]:
        """Get all XML archive IDs for a dataset."""
        result = await self.db.execute(
            select(XmlArchiveModel.id).where(XmlArchiveModel.dataset_id == dataset_id)
        )
        return [row[0] for row in result.fetchall()]

    async def delete_snapshots_for_archives(self, archive_ids: list[int]) -> int:
        """Delete archive snapshots for given archive IDs. Returns row count."""
        if not archive_ids:
            return 0
        result = await self.db.execute(
            delete(ArchiveSnapshotModel).where(ArchiveSnapshotModel.archive_id.in_(archive_ids))
        )
        return result.rowcount

    async def delete_validation_jobs_for_archives(self, archive_ids: list[int]) -> int:
        """Delete validation jobs for given archive IDs. Returns row count."""
        if not archive_ids:
            return 0
        result = await self.db.execute(
            delete(ValidationJobModel).where(ValidationJobModel.archive_id.in_(archive_ids))
        )
        return result.rowcount

    async def delete_archives_for_dataset(self, dataset_id: int) -> int:
        """Delete all XML archives for a dataset. Returns row count."""
        result = await self.db.execute(
            delete(XmlArchiveModel).where(XmlArchiveModel.dataset_id == dataset_id)
        )
        return result.rowcount

    async def delete_links_for_dataset(self, dataset_id: int) -> int:
        """Delete all useful links for a dataset. Returns row count."""
        result = await self.db.execute(
            delete(UsefulLinkModel).where(UsefulLinkModel.dataset_id == dataset_id)
        )
        return result.rowcount

    async def delete_dataset_by_id(self, dataset_id: int) -> int:
        """Delete a dataset by ID. Returns row count."""
        result = await self.db.execute(delete(DatasetModel).where(DatasetModel.id == dataset_id))
        return result.rowcount

    async def count_archives_for_dataset(self, dataset_id: int) -> int:
        """Count XML archives for a dataset."""
        result = await self.db.execute(
            select(XmlArchiveModel).where(XmlArchiveModel.dataset_id == dataset_id)
        )
        return len(result.fetchall())

    async def count_snapshots_for_archives(self, archive_ids: list[int]) -> int:
        """Count archive snapshots for given archive IDs."""
        if not archive_ids:
            return 0
        result = await self.db.execute(
            select(ArchiveSnapshotModel).where(ArchiveSnapshotModel.archive_id.in_(archive_ids))
        )
        return len(result.fetchall())

    async def count_validation_jobs_for_archives(self, archive_ids: list[int]) -> int:
        """Count validation jobs for given archive IDs."""
        if not archive_ids:
            return 0
        result = await self.db.execute(
            select(ValidationJobModel).where(ValidationJobModel.archive_id.in_(archive_ids))
        )
        return len(result.fetchall())

    async def count_links_for_dataset(self, dataset_id: int) -> int:
        """Count useful links for a dataset."""
        result = await self.db.execute(
            select(UsefulLinkModel).where(UsefulLinkModel.dataset_id == dataset_id)
        )
        return len(result.fetchall())
