"""
Repository for validation job and archive data access operations.
"""

from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import ValidationJobModel, XmlArchiveModel
from app.repositories.base import BaseRepository


class ValidationRepository(BaseRepository[ValidationJobModel]):
    """Data access layer for validation job operations."""

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
        archive_id: int | None = None,
        status_filter: str | None = None,
        limit: int = 10,
        offset: int = 0,
    ) -> list[ValidationJobModel]:
        """List validation jobs with optional filtering."""
        query = select(ValidationJobModel).order_by(desc(ValidationJobModel.created_at))

        if archive_id is not None:
            query = query.where(ValidationJobModel.archive_id == archive_id)

        if status_filter is not None:
            query = query.where(ValidationJobModel.status == status_filter)

        query = query.limit(limit).offset(offset)

        result = await self.db.execute(query)
        return list(result.scalars().all())

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
