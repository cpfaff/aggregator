"""
Dataset cascade deletion service.

This module handles the complete deletion of a dataset and all its associated data,
ensuring no orphaned records remain in the database.
"""

import logging
from typing import Any, Dict, Optional

from sqlalchemy import and_, delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.archive_snapshot import ArchiveSnapshotModel
from app.models.dataset import DatasetModel, UsefulLinkModel, XmlArchiveModel
from app.models.validation import ValidationJobModel

logger = logging.getLogger(__name__)


class DatasetDeletionService:
    """Service for handling complete dataset deletion with cascade cleanup."""

    def __init__(self, db: AsyncSession):
        """Initialize the service with a database session."""
        self.db = db

    async def delete_dataset_cascade(self, dataset_id: int, provider_id: int) -> Dict[str, Any]:
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
            archive_result = await self.db.execute(
                select(XmlArchiveModel.id).where(XmlArchiveModel.dataset_id == dataset_id)
            )
            archive_ids = [row[0] for row in archive_result.fetchall()]

            # 2. Delete archive snapshots for these archives
            if archive_ids:
                logger.info(f"Deleting snapshots for {len(archive_ids)} archives")
                snapshot_result = await self.db.execute(
                    delete(ArchiveSnapshotModel).where(
                        ArchiveSnapshotModel.archive_id.in_(archive_ids)
                    )
                )
                deletion_summary["deleted_counts"]["archive_snapshots"] = snapshot_result.rowcount
                logger.info(f"Deleted {snapshot_result.rowcount} archive snapshots")
            else:
                deletion_summary["deleted_counts"]["archive_snapshots"] = 0

            # 3. Delete validation jobs for these archives
            if archive_ids:
                logger.info(f"Deleting validation jobs for {len(archive_ids)} archives")
                validation_result = await self.db.execute(
                    delete(ValidationJobModel).where(ValidationJobModel.archive_id.in_(archive_ids))
                )
                deletion_summary["deleted_counts"]["validation_jobs"] = validation_result.rowcount
                logger.info(f"Deleted {validation_result.rowcount} validation jobs")
            else:
                deletion_summary["deleted_counts"]["validation_jobs"] = 0

            # 4. Delete XML archives
            logger.info(f"Deleting XML archives for dataset {dataset_id}")
            archives_result = await self.db.execute(
                delete(XmlArchiveModel).where(XmlArchiveModel.dataset_id == dataset_id)
            )
            deletion_summary["deleted_counts"]["xml_archives"] = archives_result.rowcount
            logger.info(f"Deleted {archives_result.rowcount} XML archives")

            # 5. Delete useful links
            logger.info(f"Deleting useful links for dataset {dataset_id}")
            links_result = await self.db.execute(
                delete(UsefulLinkModel).where(UsefulLinkModel.dataset_id == dataset_id)
            )
            deletion_summary["deleted_counts"]["useful_links"] = links_result.rowcount
            logger.info(f"Deleted {links_result.rowcount} useful links")

            # 6. Finally delete the dataset itself
            logger.info(f"Deleting dataset {dataset_id}")
            dataset_result = await self.db.execute(
                delete(DatasetModel).where(DatasetModel.id == dataset_id)
            )
            deletion_summary["deleted_counts"]["dataset"] = dataset_result.rowcount

            if dataset_result.rowcount == 0:
                logger.warning(f"Dataset {dataset_id} not found or already deleted")
                deletion_summary["status"] = "not_found"
            else:
                logger.info(f"Successfully deleted dataset {dataset_id}")
                deletion_summary["status"] = "success"

            # Commit all deletions in a single transaction
            await self.db.commit()

            return deletion_summary

        except Exception as e:
            logger.error(f"Error during cascade deletion of dataset {dataset_id}: {e}")
            await self.db.rollback()
            raise

    async def get_dataset_dependencies(self, dataset_id: int) -> Dict[str, int]:
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
        archives_result = await self.db.execute(
            select(XmlArchiveModel).where(XmlArchiveModel.dataset_id == dataset_id)
        )
        archives = archives_result.fetchall()
        counts["xml_archives"] = len(archives)

        # Count archive snapshots and validation jobs
        if archives:
            archive_ids = [a[0].id for a in archives]

            # Count snapshots
            snapshot_result = await self.db.execute(
                select(ArchiveSnapshotModel).where(ArchiveSnapshotModel.archive_id.in_(archive_ids))
            )
            counts["archive_snapshots"] = len(snapshot_result.fetchall())

            # Count validation jobs
            validation_result = await self.db.execute(
                select(ValidationJobModel).where(ValidationJobModel.archive_id.in_(archive_ids))
            )
            counts["validation_jobs"] = len(validation_result.fetchall())
        else:
            counts["archive_snapshots"] = 0
            counts["validation_jobs"] = 0

        # Count useful links
        links_result = await self.db.execute(
            select(UsefulLinkModel).where(UsefulLinkModel.dataset_id == dataset_id)
        )
        counts["useful_links"] = len(links_result.fetchall())

        return counts
