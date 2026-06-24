"""
Validation service for managing XML archive validation jobs.

This service extracts validation business logic from route handlers,
providing a clean interface for validation job management.
"""

import logging
from typing import Any

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import ValidationJobModel, XmlArchiveModel
from app.repositories.validation_repository import ValidationRepository
from app.schemas.pagination import PaginatedResponse, PaginationMeta, PaginationParams
from app.tasks.validator_tasks import validate_archive
from app.utils.filtering import FilterParam
from app.utils.sorting import SortParam

logger = logging.getLogger(__name__)


class ValidationService:
    """Service for validation job operations."""

    def __init__(self, db: AsyncSession):
        self.db = db
        self.repo = ValidationRepository(db)

    async def get_archive_or_404(self, archive_id: int) -> XmlArchiveModel:
        """
        Get an archive by ID or raise 404 if not found.

        Args:
            archive_id: ID of the archive to retrieve

        Returns:
            XmlArchiveModel: The archive if found

        Raises:
            HTTPException: 404 if archive not found
        """
        archive = await self.repo.get_archive_by_id(archive_id)

        if not archive:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Archive with ID {archive_id} not found",
            )

        return archive

    async def create_validation_job(self, archive_id: int) -> dict[str, Any]:
        """
        Create a new validation job for an archive.

        Args:
            archive_id: ID of the archive to validate

        Returns:
            Dict with task_id, job_id, archive_id, and status

        Raises:
            HTTPException: If archive not found
        """
        # Verify archive exists
        await self.get_archive_or_404(archive_id)

        # Create validation job record
        job = ValidationJobModel(
            archive_id=archive_id,
            status="pending",
            task_id="pending",  # Will be updated when task starts
        )

        await self.repo.create(job)
        await self.repo.commit()

        # Submit validation task to Celery. If the broker is unreachable, .delay()
        # raises; mark the just-committed job failed so it does not linger as an
        # active 'pending' row that blocks future re-validation (B1).
        try:
            task = validate_archive.delay(archive_id, job_id=job.id)
        except Exception as exc:
            job.status = "failed"
            job.results = {"error": f"Failed to enqueue validation task: {exc}"}
            await self.repo.commit()
            raise

        # Update job with task ID
        job.task_id = task.id
        await self.repo.commit()

        return {"task_id": task.id, "job_id": job.id, "archive_id": archive_id, "status": "pending"}

    async def get_validation_job(self, job_id: int) -> ValidationJobModel:
        """
        Get a validation job by ID.

        Args:
            job_id: ID of the validation job

        Returns:
            ValidationJobModel: The validation job

        Raises:
            HTTPException: 404 if job not found
        """
        job = await self.repo.get_by_id(job_id)

        if not job:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Validation job with ID {job_id} not found",
            )

        return job

    async def list_validation_jobs(
        self,
        filters: list[FilterParam] | None = None,
        sorts: list[SortParam] | None = None,
        pagination: PaginationParams | None = None,
    ) -> PaginatedResponse:
        """
        List validation jobs with optional filtering and cursor-based pagination.

        Args:
            filters: List of filter parameters
            sorts: List of sort parameters
            pagination: Pagination parameters

        Returns:
            PaginatedResponse with validation jobs and pagination metadata
        """
        items, total_count, next_cursor, previous_cursor = await self.repo.list_jobs(
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

    async def get_validation_results(self, job_id: int) -> dict[str, Any]:
        """
        Get detailed validation results for a completed job.

        Args:
            job_id: ID of the validation job

        Returns:
            Validation results as dictionary

        Raises:
            HTTPException: If job not found, not completed, or results missing
        """
        job = await self.get_validation_job(job_id)

        if job.status != "completed":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Validation job is not completed (current status: {job.status})",
            )

        if not job.results:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Validation results not found"
            )

        return job.results

    async def cleanup_obsolete_pending_jobs(self, archive_id: int) -> None:
        """
        Mark pending validation jobs as obsolete if newer completed jobs exist.

        This handles the task ID mismatch issue where Celery workers add UUIDs
        to task IDs.

        Args:
            archive_id: Archive ID to check
        """
        pending_jobs = await self.repo.get_pending_jobs_for_archive(archive_id)

        for pending in pending_jobs:
            completed = await self.repo.find_completed_job_by_task_prefix(
                archive_id, pending.task_id
            )
            if completed:
                pending.status = "obsolete"

        await self.repo.commit()

    async def get_dataset_validation_status(self, dataset_id: int) -> dict[str, Any]:
        """
        Get validation status for a dataset's latest XML archive.

        This includes checking for obsolete pending jobs and computing
        quality metrics from validation results.

        Args:
            dataset_id: ID of the dataset

        Returns:
            Dictionary with validation status information
        """
        # Get latest archive for this dataset
        latest_archive = await self.repo.get_latest_archive_for_dataset(dataset_id)

        # Initialize response
        status_response = {
            "dataset_id": dataset_id,
            "archive_id": None,
            "has_latest_archive": latest_archive is not None,
            "validation_status": None,
            "validation_id": None,
            "last_validated_at": None,
            "is_valid": None,
            "quality_score": None,
            "validation_results": None,
        }

        # If no latest archive, return basic response
        if not latest_archive:
            return status_response

        status_response["archive_id"] = latest_archive.id

        # Cleanup obsolete pending jobs
        await self.cleanup_obsolete_pending_jobs(latest_archive.id)

        # Get latest non-obsolete validation
        latest_validation = await self.repo.get_latest_non_obsolete_job(latest_archive.id)

        # If no validation exists
        if not latest_validation:
            status_response["validation_status"] = "not_validated"
            return status_response

        # Populate validation details
        status_response["validation_id"] = latest_validation.id
        status_response["validation_status"] = latest_validation.status
        status_response["last_validated_at"] = (
            latest_validation.completed_at or latest_validation.started_at
        )

        # Include full results if completed
        if latest_validation.status == "completed" and latest_validation.results:
            status_response["validation_results"] = latest_validation.results

            # Extract convenience fields from results
            summary = latest_validation.results.get("summary")
            if summary:
                # Check if archive is fully valid
                total_files = summary.get("total_files")
                valid_files = summary.get("valid_files")
                if total_files is not None and valid_files is not None:
                    status_response["is_valid"] = total_files == valid_files

                # Extract quality score
                data_quality = summary.get("data_quality")
                if data_quality and "total_weighted_quality" in data_quality:
                    status_response["quality_score"] = data_quality["total_weighted_quality"]

        return status_response

    async def get_latest_archive_for_dataset(self, dataset_id: int) -> XmlArchiveModel:
        """
        Get the latest archive for a dataset.

        Args:
            dataset_id: ID of the dataset

        Returns:
            Latest XmlArchiveModel

        Raises:
            HTTPException: 404 if no latest archive found
        """
        archive = await self.repo.get_latest_archive_for_dataset(dataset_id)

        if not archive:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"No latest XML archive found for dataset with ID {dataset_id}",
            )

        return archive

    async def find_existing_active_validation(self, archive_id: int) -> ValidationJobModel | None:
        """
        Find existing pending or running validation for an archive.

        Args:
            archive_id: Archive ID to check

        Returns:
            ValidationJobModel if found, None otherwise
        """
        return await self.repo.find_active_validation(archive_id)

    async def validate_dataset_latest_archive(
        self, dataset_id: int, force: bool = False
    ) -> dict[str, Any]:
        """
        Start validation for the latest archive of a dataset.

        If force=False and an active validation exists, returns existing job.
        If force=True, always creates a new validation job.

        Args:
            dataset_id: ID of the dataset
            force: If True, create new job even if one exists

        Returns:
            Dictionary with validation job information

        Raises:
            HTTPException: If dataset has no latest archive
        """
        # Get latest archive
        latest_archive = await self.get_latest_archive_for_dataset(dataset_id)

        # Check for existing active validation (unless force=True)
        if not force:
            existing_validation = await self.find_existing_active_validation(latest_archive.id)

            if existing_validation:
                # Return existing job instead of creating new one
                return {
                    "task_id": existing_validation.task_id,
                    "job_id": existing_validation.id,
                    "archive_id": latest_archive.id,
                    "status": existing_validation.status,
                }

        # Create new validation job
        return await self.create_validation_job(latest_archive.id)
