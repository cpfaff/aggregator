"""
Links service for managing useful links operations.

This service extracts useful links management business logic from route handlers,
providing a clean interface for links CRUD operations.
"""

import logging

from fastapi import HTTPException
from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.cache import invalidate_cache
from app.models import DatasetModel, UsefulLinkModel
from app.repositories.links_repository import LinksRepository
from app.schemas import UsefulLink

logger = logging.getLogger(__name__)


class LinksService:
    """Service for useful links management operations."""

    def __init__(self, db: AsyncSession):
        self.db = db
        self.repo = LinksRepository(db)

    async def list_links(self, provider_id: int, dataset_id: int) -> list[UsefulLinkModel]:
        """
        List all useful links for a specific dataset.

        Args:
            provider_id: ID of the data provider
            dataset_id: ID of the dataset

        Returns:
            List of UsefulLinkModel instances

        Raises:
            HTTPException: 400 if IDs are invalid
        """
        if provider_id <= 0 or dataset_id <= 0:
            raise HTTPException(status_code=400, detail="IDs must be positive integers")

        result = await self.db.execute(
            select(UsefulLinkModel)
            .join(DatasetModel)
            .where(and_(DatasetModel.provider_id == provider_id, DatasetModel.id == dataset_id))
        )
        return list(result.scalars().all())

    async def create_link(
        self,
        provider_id: int,
        dataset_id: int,
        link_data: UsefulLink,
    ) -> UsefulLinkModel:
        """
        Create a new useful link for a dataset.

        Args:
            provider_id: ID of the data provider
            dataset_id: ID of the dataset
            link_data: Useful link data

        Returns:
            Created UsefulLinkModel

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

        # Create the link
        link_dict = link_data.model_dump(exclude={"id"}, exclude_unset=True)
        if link_dict.get("url"):
            link_dict["url"] = str(link_dict["url"])

        link_obj = UsefulLinkModel(**link_dict, dataset_id=dataset_id)
        await self.repo.create(link_obj)
        await self.repo.commit()

        # Invalidate related caches
        invalidate_cache(f"dataset:{dataset_id}")
        invalidate_cache(f"provider:{provider_id}")
        invalidate_cache("useful-links")
        invalidate_cache("providers")
        invalidate_cache("datasets")

        return link_obj
