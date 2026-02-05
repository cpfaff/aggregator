"""
Repository for data provider data access operations.
"""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models import DataProviderModel, DatasetModel
from app.repositories.base import BaseRepository


class ProviderRepository(BaseRepository[DataProviderModel]):
    """Data access layer for provider operations."""

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
        name: str | None = None,
        datacenter: str | None = None,
        skip: int = 0,
        limit: int = 100,
    ) -> list[DataProviderModel]:
        """
        List providers with optional filtering by user permissions.

        Args:
            allowed_provider_ids: List of provider IDs the user can access.
                                  None means user can access all providers.
            name: Optional name filter (partial match)
            datacenter: Optional datacenter filter (partial match)
            skip: Number of records to skip
            limit: Maximum records to return

        Returns:
            List of DataProviderModel instances
        """
        query = select(DataProviderModel)

        # Apply text search filters if provided
        if name:
            query = query.filter(DataProviderModel.name.ilike(f"%{name}%"))
        if datacenter:
            query = query.filter(DataProviderModel.datacenter.ilike(f"%{datacenter}%"))

        # Apply permission filtering if not a global admin
        if allowed_provider_ids is not None:
            if not allowed_provider_ids:
                return []
            query = query.filter(DataProviderModel.id.in_(allowed_provider_ids))

        # Add eager loading for related entities
        query = query.options(
            selectinload(DataProviderModel.datasets).selectinload(DatasetModel.xmlArchives),
            selectinload(DataProviderModel.datasets).selectinload(DatasetModel.usefulLinks),
        )

        # Add consistent ordering by ID
        query = query.order_by(DataProviderModel.id)

        # Execute query with pagination
        result = await self.db.execute(query.offset(skip).limit(limit))
        return list(result.scalars().all())
