"""
Dataset service for managing dataset operations.

This service extracts dataset management business logic from route handlers,
providing a clean interface for dataset CRUD operations.
"""

import logging
from typing import Any

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.cache import invalidate_cache
from app.core.utils import apply_entity_updates
from app.models import (
    DataProviderModel,
    DatasetModel,
    UsefulLinkModel,
    XmlArchiveModel,
)
from app.repositories.dataset_repository import DatasetRepository
from app.schemas import Dataset
from app.schemas.pagination import PaginatedResponse, PaginationMeta, PaginationParams
from app.services.dataset_deletion import DatasetDeletionService
from app.utils.filtering import FilterParam
from app.utils.sorting import SortParam

logger = logging.getLogger(__name__)


class DatasetService:
    """Service for dataset management operations."""

    def __init__(self, db: AsyncSession):
        self.db = db
        self.repo = DatasetRepository(db)

    async def list_datasets(
        self,
        provider_id: int,
        filters: list[FilterParam] | None = None,
        sorts: list[SortParam] | None = None,
        pagination: PaginationParams | None = None,
    ) -> PaginatedResponse:
        """
        List datasets for a provider with pagination and filtering.

        Args:
            provider_id: ID of the data provider
            filters: List of filter parameters
            sorts: List of sort parameters
            pagination: Pagination parameters

        Returns:
            PaginatedResponse with datasets and pagination metadata

        Raises:
            HTTPException: 400 if provider_id is not positive
        """
        if provider_id <= 0:
            raise HTTPException(status_code=400, detail="Provider ID must be a positive integer")

        items, total_count, next_cursor, previous_cursor = await self.repo.list_for_provider(
            provider_id=provider_id,
            filters=filters,
            sorts=sorts,
            pagination=pagination,
        )

        limit = pagination.limit if pagination else 20
        return PaginatedResponse(
            data=items,
            pagination=PaginationMeta(
                limit=limit,
                has_next=next_cursor is not None,
                has_previous=previous_cursor is not None,
                next_cursor=next_cursor,
                previous_cursor=previous_cursor,
                total_count=total_count,
            ),
        )

    async def get_dataset_or_404(self, dataset_id: int, provider_id: int) -> DatasetModel:
        """
        Get a dataset by ID or raise 404.

        Args:
            dataset_id: ID of the dataset
            provider_id: ID of the data provider

        Returns:
            DatasetModel if found

        Raises:
            HTTPException: 400 if IDs are not positive, 404 if dataset not found
        """
        if provider_id <= 0 or dataset_id <= 0:
            raise HTTPException(status_code=400, detail="IDs must be positive integers")

        dataset = await self.repo.get_by_id_and_provider(dataset_id, provider_id)
        if not dataset:
            raise HTTPException(status_code=404, detail="Dataset not found")
        return dataset

    async def create_dataset(self, provider_id: int, dataset: Dataset) -> DatasetModel:
        """
        Create a new dataset for a provider.

        Args:
            provider_id: ID of the data provider
            dataset: Dataset schema with data to create

        Returns:
            Created DatasetModel

        Raises:
            HTTPException: 400 if provider_id is not positive, 404 if provider not found
        """
        if provider_id <= 0:
            raise HTTPException(status_code=400, detail="Provider ID must be a positive integer")

        # Verify provider exists
        result = await self.db.execute(
            select(DataProviderModel).where(DataProviderModel.id == provider_id)
        )
        provider = result.scalar_one_or_none()
        if not provider:
            raise HTTPException(status_code=404, detail="Provider not found")

        # Prepare dataset data
        dataset_data = dataset.model_dump(
            exclude={"id", "xmlArchives", "usefulLinks"}, exclude_unset=True
        )
        if dataset_data.get("landingPageUrl"):
            dataset_data["landingPageUrl"] = str(dataset_data["landingPageUrl"])

        # Create dataset object
        dataset_obj = DatasetModel(**dataset_data, provider_id=provider_id)

        # Add XML archives if provided
        if dataset.xmlArchives:
            for archive in dataset.xmlArchives:
                dataset_obj.xmlArchives.append(
                    XmlArchiveModel(url=str(archive.url), isLatest=archive.isLatest)
                )

        # Add useful links if provided
        if dataset.usefulLinks:
            for link in dataset.usefulLinks:
                dataset_obj.usefulLinks.append(
                    UsefulLinkModel(title=link.title, url=str(link.url), isLatest=link.isLatest)
                )

        self.db.add(dataset_obj)
        await self.db.commit()
        await self.db.refresh(dataset_obj)

        # Reload with relationships
        result = await self.db.execute(
            select(DatasetModel)
            .options(
                selectinload(DatasetModel.xmlArchives),
                selectinload(DatasetModel.usefulLinks),
            )
            .where(DatasetModel.id == dataset_obj.id)
        )

        # Invalidate caches
        invalidate_cache("datasets")
        invalidate_cache(f"provider:{provider_id}")
        invalidate_cache("providers")

        dataset_result = result.scalar_one()

        # Trigger snapshot collection for any archives created with this dataset
        if dataset_result.xmlArchives:
            from app.tasks.snapshot_tasks import collect_single_archive_snapshot

            for archive in dataset_result.xmlArchives:
                collect_single_archive_snapshot.delay(archive.id)

        return dataset_result

    async def update_dataset(
        self, dataset_id: int, provider_id: int, dataset: Dataset
    ) -> DatasetModel:
        """
        Update a dataset.

        Args:
            dataset_id: ID of the dataset to update
            provider_id: ID of the data provider
            dataset: Dataset schema with updated data

        Returns:
            Updated DatasetModel

        Raises:
            HTTPException: 400 if IDs are not positive, 404 if dataset not found
        """
        if provider_id <= 0 or dataset_id <= 0:
            raise HTTPException(status_code=400, detail="IDs must be positive integers")

        db_dataset = await self.repo.get_by_id_and_provider(dataset_id, provider_id)
        if not db_dataset:
            raise HTTPException(status_code=404, detail="Dataset not found")

        # Update basic fields
        dataset_data = dataset.model_dump(
            exclude={"id", "xmlArchives", "usefulLinks"}, exclude_unset=True
        )
        if dataset_data.get("landingPageUrl"):
            dataset_data["landingPageUrl"] = str(dataset_data["landingPageUrl"])

        for key, value in dataset_data.items():
            setattr(db_dataset, key, value)

        # Update XML archives
        if dataset.xmlArchives is not None:
            new_archives = await apply_entity_updates(
                self.db,
                db_dataset.xmlArchives,
                dataset.xmlArchives,
                XmlArchiveModel,
                db_dataset.id,
            )
            if new_archives:
                db_dataset.xmlArchives = new_archives

        # Update useful links
        if dataset.usefulLinks is not None:
            new_links = await apply_entity_updates(
                self.db,
                db_dataset.usefulLinks,
                dataset.usefulLinks,
                UsefulLinkModel,
                db_dataset.id,
            )
            if new_links:
                db_dataset.usefulLinks = new_links

        await self.db.commit()

        # Reload with relationships
        result = await self.db.execute(
            select(DatasetModel)
            .options(
                selectinload(DatasetModel.xmlArchives),
                selectinload(DatasetModel.usefulLinks),
            )
            .where(DatasetModel.id == dataset_id)
        )

        # Invalidate caches
        invalidate_cache(f"dataset:{dataset_id}")
        invalidate_cache("datasets")
        invalidate_cache(f"provider:{provider_id}")
        invalidate_cache("providers")

        # Trigger snapshot collection for any new archives
        dataset_result = result.scalar_one()
        if dataset.xmlArchives is not None:
            from app.tasks.snapshot_tasks import collect_single_archive_snapshot

            for archive in dataset_result.xmlArchives:
                collect_single_archive_snapshot.delay(archive.id)

        return dataset_result

    async def delete_dataset(self, dataset_id: int, provider_id: int) -> dict[str, Any]:
        """
        Delete a dataset and all associated data.

        Args:
            dataset_id: ID of the dataset to delete
            provider_id: ID of the data provider

        Returns:
            Deletion summary dictionary

        Raises:
            HTTPException: 400 if IDs are not positive, 404 if dataset not found,
                          500 if deletion fails
        """
        if provider_id <= 0 or dataset_id <= 0:
            raise HTTPException(status_code=400, detail="IDs must be positive integers")

        # Verify dataset exists and belongs to provider
        dataset_obj = await self.repo.get_by_id_and_provider(dataset_id, provider_id)
        if not dataset_obj:
            raise HTTPException(status_code=404, detail="Dataset not found")

        # Use cascade deletion service
        deletion_service = DatasetDeletionService(self.db)

        try:
            deletion_summary = await deletion_service.delete_dataset_cascade(
                dataset_id=dataset_id, provider_id=provider_id
            )

            logger.info(f"Dataset {dataset_id} cascade deletion completed: {deletion_summary}")

            # Invalidate caches
            invalidate_cache(f"dataset:{dataset_id}")
            invalidate_cache("datasets")
            invalidate_cache(f"provider:{provider_id}")
            invalidate_cache("providers")

            return {
                "message": "Dataset and all associated data deleted successfully",
                "deletion_summary": deletion_summary,
            }

        except HTTPException:
            # Preserve a meaningful status raised by the cascade (e.g. 404/409).
            raise
        except Exception as e:
            logger.error(f"Failed to delete dataset {dataset_id}: {e}")
            # Do not echo raw exception text (driver/infra detail) to the client;
            # the full error is logged above (B15 follow-up).
            raise HTTPException(
                status_code=500, detail="Failed to delete dataset"
            ) from e
