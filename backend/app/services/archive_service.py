"""
Archive service for managing XML archive operations.

This service extracts XML archive management business logic from route handlers,
providing a clean interface for archive CRUD operations.
"""

import logging

from fastapi import HTTPException
from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.cache import invalidate_cache
from app.models import DatasetModel, XmlArchiveModel
from app.repositories.archive_repository import ArchiveRepository
from app.schemas import XmlArchive

logger = logging.getLogger(__name__)


class ArchiveService:
    """Service for XML archive management operations."""

    def __init__(self, db: AsyncSession):
        self.db = db
        self.repo = ArchiveRepository(db)

    async def list_archives(self, provider_id: int, dataset_id: int) -> list[XmlArchiveModel]:
        """
        List all XML archives for a specific dataset.

        Args:
            provider_id: ID of the data provider
            dataset_id: ID of the dataset

        Returns:
            List of XmlArchiveModel instances

        Raises:
            HTTPException: 400 if IDs are invalid
        """
        if provider_id <= 0 or dataset_id <= 0:
            raise HTTPException(status_code=400, detail="IDs must be positive integers")

        result = await self.db.execute(
            select(XmlArchiveModel)
            .join(DatasetModel)
            .where(and_(DatasetModel.provider_id == provider_id, DatasetModel.id == dataset_id))
        )
        return list(result.scalars().all())

    async def create_archive(
        self,
        provider_id: int,
        dataset_id: int,
        archive_data: XmlArchive,
        trigger_snapshot: bool = True,
    ) -> XmlArchiveModel:
        """
        Create a new XML archive for a dataset.

        Args:
            provider_id: ID of the data provider
            dataset_id: ID of the dataset
            archive_data: XML archive data
            trigger_snapshot: Whether to trigger snapshot collection

        Returns:
            Created XmlArchiveModel

        Raises:
            HTTPException: 400 if IDs are invalid, 404 if dataset not found
        """
        if provider_id <= 0 or dataset_id <= 0:
            raise HTTPException(status_code=400, detail="IDs must be positive integers")

        # Verify dataset exists and belongs to provider
        result = await self.db.execute(
            select(DatasetModel).where(
                and_(DatasetModel.provider_id == provider_id, DatasetModel.id == dataset_id)
            )
        )
        dataset = result.scalar_one_or_none()
        if not dataset:
            raise HTTPException(status_code=404, detail="Dataset not found")

        # Create the archive
        xml_data = archive_data.model_dump(exclude={"id"}, exclude_unset=True)
        if xml_data.get("url"):
            xml_data["url"] = str(xml_data["url"])

        xml_obj = XmlArchiveModel(**xml_data, dataset_id=dataset_id)
        await self.repo.create(xml_obj)
        await self.repo.commit()

        # Invalidate related caches
        invalidate_cache(f"dataset:{dataset_id}")
        invalidate_cache(f"provider:{provider_id}")
        invalidate_cache("xml-archives")
        invalidate_cache("providers")
        invalidate_cache("datasets")

        # Trigger background tasks
        if trigger_snapshot:
            from app.tasks.snapshot_tasks import collect_single_archive_snapshot
            from app.tasks.validator_tasks import validate_archive

            validate_archive.delay(xml_obj.id)
            collect_single_archive_snapshot.delay(xml_obj.id)

        return xml_obj
