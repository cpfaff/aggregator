"""
Provider service for managing data provider operations.

This service extracts provider management business logic from route handlers,
providing a clean interface for provider CRUD operations.
"""

import logging

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
    UserModel,
    XmlArchiveModel,
)
from app.repositories.provider_repository import ProviderRepository
from app.schemas import DataProvider
from app.schemas.pagination import PaginatedResponse, PaginationMeta, PaginationParams
from app.security import normalize_provider_roles
from app.utils.filtering import FilterParam
from app.utils.sorting import SortParam

logger = logging.getLogger(__name__)


class ProviderService:
    """Service for data provider management operations."""

    def __init__(self, db: AsyncSession):
        self.db = db
        self.repo = ProviderRepository(db)

    def _get_allowed_provider_ids(self, user: UserModel) -> list[int] | None:
        """
        Get list of provider IDs a user can access.

        Args:
            user: The user to check permissions for

        Returns:
            List of allowed provider IDs, or None if user is global admin
        """
        if user.is_global_admin:
            return None

        return [
            int(key)
            for key in normalize_provider_roles(user.provider_roles).keys()
            if key.isdigit()
        ]

    async def list_providers(
        self,
        user: UserModel,
        filters: list[FilterParam] | None = None,
        sorts: list[SortParam] | None = None,
        pagination: PaginationParams | None = None,
    ) -> PaginatedResponse:
        """
        List all providers the user has access to.

        Args:
            user: Current user
            filters: List of filter parameters
            sorts: List of sort parameters
            pagination: Pagination parameters

        Returns:
            PaginatedResponse with providers and pagination metadata
        """
        allowed_ids = self._get_allowed_provider_ids(user)
        items, total_count, next_cursor, previous_cursor = await self.repo.list_for_user(
            allowed_provider_ids=allowed_ids,
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

    async def get_provider_by_id(self, provider_id: int) -> DataProviderModel | None:
        """
        Get a provider by ID.

        Args:
            provider_id: ID of the provider

        Returns:
            DataProviderModel if found, None otherwise
        """
        return await self.repo.get_by_id(provider_id)

    async def get_provider_or_404(self, provider_id: int) -> DataProviderModel:
        """
        Get a provider by ID or raise 404.

        Args:
            provider_id: ID of the provider

        Returns:
            DataProviderModel if found

        Raises:
            HTTPException: 404 if provider not found
            HTTPException: 400 if provider_id is invalid
        """
        if provider_id <= 0:
            raise HTTPException(status_code=400, detail="Provider ID must be a positive integer")

        provider = await self.get_provider_by_id(provider_id)
        if not provider:
            raise HTTPException(status_code=404, detail="Provider not found")
        return provider

    async def create_provider(
        self, provider_data: DataProvider, user: UserModel
    ) -> DataProviderModel:
        """
        Create a new provider.

        Args:
            provider_data: Provider data from request
            user: Current user (must be global admin)

        Returns:
            Created DataProviderModel

        Raises:
            HTTPException: 403 if user is not global admin
        """
        # Prepare provider data
        data_dict = provider_data.model_dump(exclude={"datasets", "id"}, exclude_unset=True)
        if data_dict.get("url"):
            data_dict["url"] = str(data_dict["url"])
        if data_dict.get("biocaseUrl"):
            data_dict["biocaseUrl"] = str(data_dict["biocaseUrl"])

        # Create provider model
        provider_obj = DataProviderModel(**data_dict)

        # Add datasets if provided
        if provider_data.datasets:
            for dataset in provider_data.datasets:
                dataset_data = dataset.model_dump(
                    exclude={"id", "xmlArchives", "usefulLinks"}, exclude_unset=True
                )
                if dataset_data.get("landingPageUrl"):
                    dataset_data["landingPageUrl"] = (
                        str(dataset_data["landingPageUrl"])
                        if dataset_data["landingPageUrl"]
                        else None
                    )
                db_dataset = DatasetModel(**dataset_data)

                # Add XML archives
                if dataset.xmlArchives and len(dataset.xmlArchives) > 0:
                    for archive in dataset.xmlArchives:
                        db_dataset.xmlArchives.append(
                            XmlArchiveModel(url=str(archive.url), isLatest=archive.isLatest)
                        )

                # Add useful links
                if dataset.usefulLinks and len(dataset.usefulLinks) > 0:
                    for link in dataset.usefulLinks:
                        db_dataset.usefulLinks.append(
                            UsefulLinkModel(
                                title=link.title, url=str(link.url), isLatest=link.isLatest
                            )
                        )

                provider_obj.datasets.append(db_dataset)

        # Save to database
        self.db.add(provider_obj)
        await self.db.commit()
        await self.db.refresh(provider_obj)

        # Reload with relationships
        result = await self.db.execute(
            select(DataProviderModel)
            .options(
                selectinload(DataProviderModel.datasets).selectinload(DatasetModel.xmlArchives),
                selectinload(DataProviderModel.datasets).selectinload(DatasetModel.usefulLinks),
            )
            .where(DataProviderModel.id == provider_obj.id)
        )

        # Invalidate cache
        invalidate_cache("providers")

        return result.scalar_one()

    async def update_provider(
        self,
        provider_id: int,
        provider_data: DataProvider,
        user: UserModel,
    ) -> DataProviderModel:
        """
        Update a provider.

        Args:
            provider_id: ID of the provider to update
            provider_data: New provider data
            user: Current user

        Returns:
            Updated DataProviderModel

        Raises:
            HTTPException: 404 if provider not found
            HTTPException: 400 if provider_id is invalid
        """
        db_provider = await self.get_provider_or_404(provider_id)

        # Prepare update data
        data_dict = provider_data.model_dump(exclude={"datasets", "id"}, exclude_unset=True)

        # Only allow global admins to modify isDataCenter field
        if "isDataCenter" in data_dict and not user.is_global_admin:
            del data_dict["isDataCenter"]

        # Convert URLs to strings
        if data_dict.get("url"):
            data_dict["url"] = str(data_dict["url"])
        if data_dict.get("biocaseUrl"):
            data_dict["biocaseUrl"] = str(data_dict["biocaseUrl"])

        # Update provider fields
        for key, value in data_dict.items():
            setattr(db_provider, key, value)

        # Handle nested dataset updates
        async with self.db.begin_nested():
            if (
                "datasets" in provider_data.model_dump(exclude_unset=True)
                and provider_data.datasets is not None
            ):
                existing_datasets = {ds.id: ds for ds in db_provider.datasets if ds.id is not None}
                processed_dataset_ids = set()
                updated_datasets = []

                for dataset in provider_data.datasets:
                    if dataset.id is not None and dataset.id in existing_datasets:
                        # Update existing dataset
                        db_dataset = existing_datasets[dataset.id]
                        processed_dataset_ids.add(dataset.id)
                        dataset_data = dataset.model_dump(
                            exclude={"id", "xmlArchives", "usefulLinks"},
                            exclude_unset=True,
                        )
                        if "landingPageUrl" in dataset_data:
                            dataset_data["landingPageUrl"] = (
                                str(dataset_data["landingPageUrl"])
                                if dataset_data["landingPageUrl"]
                                else None
                            )
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

                        updated_datasets.append(db_dataset)
                    else:
                        # Create new dataset
                        new_dataset = DatasetModel(
                            provider_id=db_provider.id,
                            source=dataset.source,
                            title=dataset.title,
                            landingPageUrl=(
                                str(dataset.landingPageUrl) if dataset.landingPageUrl else None
                            ),
                            isHarvestReady=dataset.isHarvestReady,
                        )
                        if dataset.xmlArchives:
                            for archive in dataset.xmlArchives:
                                new_dataset.xmlArchives.append(
                                    XmlArchiveModel(url=str(archive.url), isLatest=archive.isLatest)
                                )
                        if dataset.usefulLinks:
                            for link in dataset.usefulLinks:
                                new_dataset.usefulLinks.append(
                                    UsefulLinkModel(
                                        title=link.title,
                                        url=str(link.url),
                                        isLatest=link.isLatest,
                                    )
                                )
                        updated_datasets.append(new_dataset)

                db_provider.datasets = updated_datasets

        await self.db.commit()

        # Reload with relationships
        result = await self.db.execute(
            select(DataProviderModel)
            .options(
                selectinload(DataProviderModel.datasets).selectinload(DatasetModel.xmlArchives),
                selectinload(DataProviderModel.datasets).selectinload(DatasetModel.usefulLinks),
            )
            .where(DataProviderModel.id == provider_id)
        )

        # Invalidate caches
        invalidate_cache(f"provider:{provider_id}")
        invalidate_cache("providers")

        provider_result = result.scalar_one()

        # Trigger snapshot collection for any archives to capture unit count
        if provider_data.datasets is not None:
            # Defer import to avoid circular imports
            from app.tasks.snapshot_tasks import collect_single_archive_snapshot

            for dataset in provider_result.datasets:
                for archive in dataset.xmlArchives:
                    collect_single_archive_snapshot.delay(archive.id)

        return provider_result

    async def delete_provider(self, provider_id: int, user: UserModel) -> None:
        """
        Delete a provider and all its datasets.

        Args:
            provider_id: ID of the provider to delete
            user: Current user (must be global admin)

        Raises:
            HTTPException: 400 if provider_id is invalid
        """
        if provider_id <= 0:
            raise HTTPException(status_code=400, detail="Provider ID must be a positive integer")

        result = await self.db.execute(
            select(DataProviderModel).where(DataProviderModel.id == provider_id)
        )
        provider = result.scalar_one_or_none()

        if provider:
            await self.db.delete(provider)
            await self.db.commit()

            # Invalidate caches
            invalidate_cache(f"provider:{provider_id}")
            invalidate_cache("providers")
            invalidate_cache("datasets")
