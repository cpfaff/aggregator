"""
Repository for useful links data access operations.
"""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import UsefulLinkModel
from app.repositories.base import BaseRepository


class LinksRepository(BaseRepository[UsefulLinkModel]):
    """Data access layer for useful links operations."""

    def __init__(self, db: AsyncSession):
        super().__init__(UsefulLinkModel, db)

    async def list_for_dataset(self, dataset_id: int) -> list[UsefulLinkModel]:
        """List all useful links for a specific dataset."""
        result = await self.db.execute(
            select(UsefulLinkModel).where(UsefulLinkModel.dataset_id == dataset_id)
        )
        return list(result.scalars().all())
