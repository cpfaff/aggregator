"""
Dataset cascade deletion service.

This module handles the complete deletion of a dataset and all its associated data,
ensuring no orphaned records remain in the database.
"""

from typing import Optional, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete, and_
import logging

from app.models.dataset import DatasetModel, XmlArchiveModel, UsefulLinkModel
from app.models.validation import ValidationJobModel
from app.models.statistics import StatisticModel, EntityType, MetricType
from app.core.celery_app import celery_app

logger = logging.getLogger(__name__)


class DatasetDeletionService:
    """Service for handling complete dataset deletion with cascade cleanup."""
    
    def __init__(self, db: AsyncSession):
        """Initialize the service with a database session."""
        self.db = db
        
    async def delete_dataset_cascade(
        self, 
        dataset_id: int, 
        provider_id: int
    ) -> Dict[str, Any]:
        """
        Completely delete a dataset and all associated data.
        
        This function ensures all related data is removed:
        1. Statistics records for the dataset
        2. Validation jobs for the dataset's archives
        3. XML archives belonging to the dataset
        4. Useful links belonging to the dataset
        5. The dataset record itself
        
        After deletion, it triggers re-aggregation of provider statistics.
        
        Args:
            dataset_id: ID of the dataset to delete
            provider_id: ID of the provider (for re-aggregation)
            
        Returns:
            Dict with deletion summary
        """
        deletion_summary = {
            'dataset_id': dataset_id,
            'provider_id': provider_id,
            'deleted_counts': {}
        }
        
        try:
            # 1. Delete all statistics records for this dataset
            logger.info(f"Deleting statistics for dataset {dataset_id}")
            stats_result = await self.db.execute(
                delete(StatisticModel).where(
                    and_(
                        StatisticModel.entity_type == EntityType.DATASET,
                        StatisticModel.entity_id == dataset_id
                    )
                )
            )
            deletion_summary['deleted_counts']['statistics'] = stats_result.rowcount
            logger.info(f"Deleted {stats_result.rowcount} statistics records")
            
            # 2. Get all XML archive IDs for this dataset (needed for validation jobs)
            archive_result = await self.db.execute(
                select(XmlArchiveModel.id).where(
                    XmlArchiveModel.dataset_id == dataset_id
                )
            )
            archive_ids = [row[0] for row in archive_result.fetchall()]
            
            # 3. Delete validation jobs for these archives
            if archive_ids:
                logger.info(f"Deleting validation jobs for {len(archive_ids)} archives")
                validation_result = await self.db.execute(
                    delete(ValidationJobModel).where(
                        ValidationJobModel.archive_id.in_(archive_ids)
                    )
                )
                deletion_summary['deleted_counts']['validation_jobs'] = validation_result.rowcount
                logger.info(f"Deleted {validation_result.rowcount} validation jobs")
            else:
                deletion_summary['deleted_counts']['validation_jobs'] = 0
            
            # 4. Delete XML archives
            logger.info(f"Deleting XML archives for dataset {dataset_id}")
            archives_result = await self.db.execute(
                delete(XmlArchiveModel).where(
                    XmlArchiveModel.dataset_id == dataset_id
                )
            )
            deletion_summary['deleted_counts']['xml_archives'] = archives_result.rowcount
            logger.info(f"Deleted {archives_result.rowcount} XML archives")
            
            # 5. Delete useful links
            logger.info(f"Deleting useful links for dataset {dataset_id}")
            links_result = await self.db.execute(
                delete(UsefulLinkModel).where(
                    UsefulLinkModel.dataset_id == dataset_id
                )
            )
            deletion_summary['deleted_counts']['useful_links'] = links_result.rowcount
            logger.info(f"Deleted {links_result.rowcount} useful links")
            
            # 6. Finally delete the dataset itself
            logger.info(f"Deleting dataset {dataset_id}")
            dataset_result = await self.db.execute(
                delete(DatasetModel).where(
                    DatasetModel.id == dataset_id
                )
            )
            deletion_summary['deleted_counts']['dataset'] = dataset_result.rowcount
            
            if dataset_result.rowcount == 0:
                logger.warning(f"Dataset {dataset_id} not found or already deleted")
                deletion_summary['status'] = 'not_found'
            else:
                logger.info(f"Successfully deleted dataset {dataset_id}")
                deletion_summary['status'] = 'success'
                
                # 7. Trigger provider statistics re-aggregation
                await self._trigger_statistics_reaggregation(provider_id)
            
            # Commit all deletions in a single transaction
            await self.db.commit()
            
            return deletion_summary
            
        except Exception as e:
            logger.error(f"Error during cascade deletion of dataset {dataset_id}: {e}")
            await self.db.rollback()
            raise
    
    async def _trigger_statistics_reaggregation(self, provider_id: int):
        """
        Trigger re-aggregation of provider statistics after dataset deletion.
        
        This ensures:
        - Provider dataset counts are updated
        - Provider biological units are recalculated
        - All timelines reflect the current state
        """
        from datetime import date
        
        try:
            # Import tasks
            from app.tasks.statistics_tasks import (
                update_provider_dataset_count_after_deletion,
                collect_provider_biological_units,
                collect_daily_statistics
            )
            
            logger.info(f"Triggering statistics re-aggregation for provider {provider_id}")
            
            # 1. Update provider dataset count
            update_provider_dataset_count_after_deletion.delay(
                provider_id, 
                "dataset_deletion"
            )
            
            # 2. Re-aggregate provider biological units for today
            # This will properly sum up only existing datasets
            collect_provider_biological_units.delay(
                date.today().isoformat()
            )
            
            # 3. Also trigger general daily statistics to ensure system counts are correct
            collect_daily_statistics.delay(
                date.today().isoformat()
            )
            
            logger.info("Statistics re-aggregation tasks queued successfully")
            
        except Exception as e:
            # Log but don't fail the deletion if statistics update fails
            logger.error(f"Failed to trigger statistics re-aggregation: {e}")
    
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
        
        # Count statistics
        stats_result = await self.db.execute(
            select(StatisticModel).where(
                and_(
                    StatisticModel.entity_type == EntityType.DATASET,
                    StatisticModel.entity_id == dataset_id
                )
            )
        )
        counts['statistics'] = len(stats_result.fetchall())
        
        # Count XML archives
        archives_result = await self.db.execute(
            select(XmlArchiveModel).where(
                XmlArchiveModel.dataset_id == dataset_id
            )
        )
        archives = archives_result.fetchall()
        counts['xml_archives'] = len(archives)
        
        # Count validation jobs
        if archives:
            archive_ids = [a[0].id for a in archives]
            validation_result = await self.db.execute(
                select(ValidationJobModel).where(
                    ValidationJobModel.archive_id.in_(archive_ids)
                )
            )
            counts['validation_jobs'] = len(validation_result.fetchall())
        else:
            counts['validation_jobs'] = 0
        
        # Count useful links
        links_result = await self.db.execute(
            select(UsefulLinkModel).where(
                UsefulLinkModel.dataset_id == dataset_id
            )
        )
        counts['useful_links'] = len(links_result.fetchall())
        
        return counts