"""
Repository for dataset data access operations including cascade deletion.
"""

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import (
    DatasetModel,
    UsefulLinkModel,
    ValidationJobModel,
    XmlArchiveModel,
)
from app.models.archive_snapshot import ArchiveSnapshotModel
from app.repositories.base import BaseRepository


class DatasetRepository(BaseRepository[DatasetModel]):
    """Data access layer for dataset operations."""

    def __init__(self, db: AsyncSession):
        super().__init__(DatasetModel, db)

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
