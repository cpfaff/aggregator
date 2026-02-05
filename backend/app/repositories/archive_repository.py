"""
Repository for XML archive data access operations.
"""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import XmlArchiveModel
from app.repositories.base import BaseRepository


class ArchiveRepository(BaseRepository[XmlArchiveModel]):
    """Data access layer for XML archive operations."""

    def __init__(self, db: AsyncSession):
        super().__init__(XmlArchiveModel, db)

    async def list_for_dataset(self, dataset_id: int) -> list[XmlArchiveModel]:
        """List all XML archives for a specific dataset."""
        result = await self.db.execute(
            select(XmlArchiveModel).where(XmlArchiveModel.dataset_id == dataset_id)
        )
        return list(result.scalars().all())
