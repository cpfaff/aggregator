"""
Dataset cascade deletion service.

This module handles the complete deletion of a dataset and all its associated data,
ensuring no orphaned records remain in the database.
"""

import logging
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories.dataset_repository import DatasetRepository

logger = logging.getLogger(__name__)


class DatasetDeletionService:
    """Service for handling complete dataset deletion with cascade cleanup."""

    def __init__(self, db: AsyncSession):
        """Initialize the service with a database session."""
        self.db = db
        self.repo = DatasetRepository(db)

    async def delete_dataset_cascade(self, dataset_id: int, provider_id: int) -> dict[str, Any]:
        """
        Completely delete a dataset and all associated data.

        This function ensures all related data is removed:
        1. Archive snapshots for the dataset's archives
        2. Validation jobs for the dataset's archives
        3. XML archives belonging to the dataset
        4. Useful links belonging to the dataset
        5. The dataset record itself

        Args:
            dataset_id: ID of the dataset to delete
            provider_id: ID of the provider (for logging)

        Returns:
            Dict with deletion summary
        """
        deletion_summary = {
            "dataset_id": dataset_id,
            "provider_id": provider_id,
            "deleted_counts": {},
        }

        try:
            # 1. Get all XML archive IDs for this dataset
            archive_ids = await self.repo.get_archive_ids_for_dataset(dataset_id)

            # 2. Delete archive snapshots for these archives
            logger.info(f"Deleting snapshots for {len(archive_ids)} archives")
            snapshot_count = await self.repo.delete_snapshots_for_archives(archive_ids)
            deletion_summary["deleted_counts"]["archive_snapshots"] = snapshot_count
            logger.info(f"Deleted {snapshot_count} archive snapshots")

            # 3. Delete validation jobs for these archives
            logger.info(f"Deleting validation jobs for {len(archive_ids)} archives")
            validation_count = await self.repo.delete_validation_jobs_for_archives(archive_ids)
            deletion_summary["deleted_counts"]["validation_jobs"] = validation_count
            logger.info(f"Deleted {validation_count} validation jobs")

            # 4. Delete XML archives
            logger.info(f"Deleting XML archives for dataset {dataset_id}")
            archives_count = await self.repo.delete_archives_for_dataset(dataset_id)
            deletion_summary["deleted_counts"]["xml_archives"] = archives_count
            logger.info(f"Deleted {archives_count} XML archives")

            # 5. Delete useful links
            logger.info(f"Deleting useful links for dataset {dataset_id}")
            links_count = await self.repo.delete_links_for_dataset(dataset_id)
            deletion_summary["deleted_counts"]["useful_links"] = links_count
            logger.info(f"Deleted {links_count} useful links")

            # 6. Finally delete the dataset itself
            logger.info(f"Deleting dataset {dataset_id}")
            dataset_count = await self.repo.delete_dataset_by_id(dataset_id)
            deletion_summary["deleted_counts"]["dataset"] = dataset_count

            if dataset_count == 0:
                logger.warning(f"Dataset {dataset_id} not found or already deleted")
                deletion_summary["status"] = "not_found"
            else:
                logger.info(f"Successfully deleted dataset {dataset_id}")
                deletion_summary["status"] = "success"

            # Commit all deletions in a single transaction
            await self.repo.commit()

            return deletion_summary

        except Exception as e:
            logger.error(f"Error during cascade deletion of dataset {dataset_id}: {e}")
            await self.repo.rollback()
            raise

    async def get_dataset_dependencies(self, dataset_id: int) -> dict[str, int]:
        """
        Get counts of all dependent records for a dataset.
        Useful for showing confirmation dialog before deletion.

        Args:
            dataset_id: ID of the dataset

        Returns:
            Dict with counts of dependent records
        """
        counts = {}

        # Count XML archives
        archive_ids = await self.repo.get_archive_ids_for_dataset(dataset_id)
        counts["xml_archives"] = len(archive_ids)

        # Count archive snapshots and validation jobs
        counts["archive_snapshots"] = await self.repo.count_snapshots_for_archives(archive_ids)
        counts["validation_jobs"] = await self.repo.count_validation_jobs_for_archives(archive_ids)

        # Count useful links
        counts["useful_links"] = await self.repo.count_links_for_dataset(dataset_id)

        return counts
