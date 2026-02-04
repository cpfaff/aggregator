"""
API endpoints for XML validation tasks.
"""

from datetime import datetime
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.models import UserModel, ValidationJobModel, XmlArchiveModel
from app.security import get_current_user
from app.tasks.validator_tasks import validate_archive

router = APIRouter()


class ValidateArchiveRequest(BaseModel):
    """
    Request model for submitting an archive validation task.
    """

    archive_id: int = Field(..., description="ID of the XML archive to validate")


class ValidateArchiveResponse(BaseModel):
    """
    Response model for an archive validation job.
    """

    task_id: str
    job_id: int
    archive_id: int
    status: str


class ValidationJobResponse(BaseModel):
    """
    Response model for validation job details.
    """

    id: int
    archive_id: int
    status: str
    task_id: str
    started_at: datetime
    completed_at: Optional[datetime] = None
    total_files: Optional[int] = None
    valid_files: Optional[int] = None
    error_count: Optional[int] = None
    validation_time: Optional[float] = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class DatasetValidationStatus(BaseModel):
    """
    Response model for dataset validation status.
    """

    dataset_id: int
    archive_id: Optional[int] = None
    has_latest_archive: bool
    validation_status: Optional[str] = None  # not_validated, pending, running, completed, failed
    validation_id: Optional[int] = None
    last_validated_at: Optional[datetime] = None

    # Core quality indicators (for quick access without parsing the full results)
    is_valid: Optional[bool] = None
    quality_score: Optional[float] = None

    # Complete validation results as JSON
    validation_results: Optional[Dict[str, Any]] = None

    model_config = ConfigDict(from_attributes=True)


@router.post("/", response_model=ValidateArchiveResponse, status_code=status.HTTP_201_CREATED)
async def create_validation_job(
    request: ValidateArchiveRequest,
    current_user: UserModel = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Start a validation job for an XML archive.

    Args:
        request: The validation request with archive ID
        current_user: The current authenticated user
        db: Database session

    Returns:
        Information about the submitted validation job
    """
    # Check if the archive exists
    result = await db.execute(
        select(XmlArchiveModel).where(XmlArchiveModel.id == request.archive_id)
    )
    archive = result.scalar_one_or_none()

    if not archive:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Archive with ID {request.archive_id} not found",
        )

    # Create a validation job record
    job = ValidationJobModel(
        archive_id=request.archive_id,
        status="pending",
        task_id="pending",  # Will be updated when the task starts
    )

    db.add(job)
    await db.commit()
    await db.refresh(job)

    # Submit the validation task
    task = validate_archive.delay(request.archive_id, job_id=job.id)

    # Update the job with the task ID
    job.task_id = task.id
    await db.commit()

    return {
        "task_id": task.id,
        "job_id": job.id,
        "archive_id": request.archive_id,
        "status": "pending",
    }


@router.get("/{job_id}", response_model=ValidationJobResponse)
async def get_validation_job(
    job_id: int,
    current_user: UserModel = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Get details of a validation job.

    Args:
        job_id: ID of the validation job
        current_user: The current authenticated user
        db: Database session

    Returns:
        Details of the validation job
    """
    result = await db.execute(select(ValidationJobModel).where(ValidationJobModel.id == job_id))
    job = result.scalar_one_or_none()

    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Validation job with ID {job_id} not found",
        )

    return job


@router.get("/", response_model=List[ValidationJobResponse])
async def list_validation_jobs(
    archive_id: Optional[int] = None,
    status: Optional[str] = None,
    limit: int = 10,
    offset: int = 0,
    current_user: UserModel = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    List validation jobs with optional filtering.

    Args:
        archive_id: Optional filter by archive ID
        status: Optional filter by status
        limit: Maximum number of jobs to return
        offset: Offset for pagination
        current_user: The current authenticated user
        db: Database session

    Returns:
        List of validation jobs
    """
    query = select(ValidationJobModel).order_by(desc(ValidationJobModel.created_at))

    # Apply filters if provided
    if archive_id is not None:
        query = query.where(ValidationJobModel.archive_id == archive_id)

    if status is not None:
        query = query.where(ValidationJobModel.status == status)

    # Apply pagination
    query = query.limit(limit).offset(offset)

    result = await db.execute(query)
    jobs = result.scalars().all()

    return jobs


@router.get("/{job_id}/results", response_model=Dict[str, Any])
async def get_validation_results(
    job_id: int,
    current_user: UserModel = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Get detailed results of a validation job.

    Args:
        job_id: ID of the validation job
        current_user: The current authenticated user
        db: Database session

    Returns:
        Complete validation results
    """
    result = await db.execute(select(ValidationJobModel).where(ValidationJobModel.id == job_id))
    job = result.scalar_one_or_none()

    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Validation job with ID {job_id} not found",
        )

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


@router.get("/datasets/{dataset_id}/validation-status", response_model=DatasetValidationStatus)
async def get_dataset_validation_status(
    dataset_id: int,
    current_user: UserModel = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Get the validation status for a dataset's latest XML archive.

    Args:
        dataset_id: The ID of the dataset
        current_user: The current authenticated user
        db: Database session

    Returns:
        Status information about the latest validation for the dataset
    """
    # Get the latest archive for this dataset
    latest_archive_result = await db.execute(
        select(XmlArchiveModel)
        .where(XmlArchiveModel.dataset_id == dataset_id)
        .where(XmlArchiveModel.isLatest == True)
    )
    latest_archive = latest_archive_result.scalars().first()

    # Initialize the response
    status_response = DatasetValidationStatus(
        dataset_id=dataset_id, has_latest_archive=latest_archive is not None
    )

    # If no latest archive exists, return the basic response
    if not latest_archive:
        return status_response

    # Set archive ID in response
    status_response.archive_id = latest_archive.id

    # First, check for any 'pending' jobs that might be completed in Celery but not in our DB
    # This handles the task ID mismatch issue where the worker adds a UUID to the task ID
    pending_validation_result = await db.execute(
        select(ValidationJobModel)
        .where(ValidationJobModel.archive_id == latest_archive.id)
        .where(ValidationJobModel.status == "pending")
        .order_by(desc(ValidationJobModel.created_at))
    )
    pending_validations = pending_validation_result.scalars().all()

    # If there are pending validations, check if newer completed validations exist with similar task IDs
    for pending in pending_validations:
        # Look for completed validation with a task ID starting with the pending task ID
        completed_result = await db.execute(
            select(ValidationJobModel)
            .where(ValidationJobModel.archive_id == latest_archive.id)
            .where(ValidationJobModel.status == "completed")
            .where(ValidationJobModel.task_id.startswith(pending.task_id))
        )
        completed = completed_result.scalars().first()

        # If we found a matching completed job, the pending one is obsolete
        if completed:
            # Mark pending validation as 'obsolete'
            pending.status = "obsolete"
            await db.commit()

    # Get the latest validation for this archive (excluding obsolete ones)
    latest_validation_result = await db.execute(
        select(ValidationJobModel)
        .where(ValidationJobModel.archive_id == latest_archive.id)
        .where(ValidationJobModel.status != "obsolete")
        .order_by(desc(ValidationJobModel.created_at))
        .limit(1)
    )
    latest_validation = latest_validation_result.scalars().first()

    # If no validation exists, return with archive info only
    if not latest_validation:
        status_response.validation_status = "not_validated"
        return status_response

    # Populate validation details
    status_response.validation_id = latest_validation.id
    status_response.validation_status = latest_validation.status
    status_response.last_validated_at = (
        latest_validation.completed_at or latest_validation.started_at
    )

    # Include full validation results if available and validation is completed
    if latest_validation.status == "completed" and latest_validation.results:
        status_response.validation_results = latest_validation.results

        # Set convenience fields based on the results
        if latest_validation.results.get("summary"):
            summary = latest_validation.results["summary"]

            # Check if the archive is valid (all files valid)
            if "total_files" in summary and "valid_files" in summary:
                status_response.is_valid = summary["total_files"] == summary["valid_files"]

            # Include the quality score if available
            if "data_quality" in summary and "total_weighted_quality" in summary["data_quality"]:
                status_response.quality_score = summary["data_quality"]["total_weighted_quality"]

    return status_response


@router.post(
    "/datasets/{dataset_id}/validate",
    response_model=ValidateArchiveResponse,
    status_code=status.HTTP_201_CREATED,
)
async def validate_dataset_latest_archive(
    dataset_id: int,
    force: bool = False,  # New parameter to force validation regardless of status
    current_user: UserModel = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Start a validation job for the latest XML archive of a dataset.

    Args:
        dataset_id: The ID of the dataset
        force: If True, will create a new validation job even if one already exists
        current_user: The current authenticated user
        db: Database session

    Returns:
        Information about the submitted validation job
    """
    # Find the latest archive for this dataset
    latest_archive_result = await db.execute(
        select(XmlArchiveModel)
        .where(XmlArchiveModel.dataset_id == dataset_id)
        .where(XmlArchiveModel.isLatest == True)
    )
    latest_archive = latest_archive_result.scalars().first()

    if not latest_archive:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No latest XML archive found for dataset with ID {dataset_id}",
        )

    # If force is True, don't bother checking existing validations
    if not force:
        # Check if there's already a pending or running validation for this archive
        existing_validation_result = await db.execute(
            select(ValidationJobModel)
            .where(ValidationJobModel.archive_id == latest_archive.id)
            .where(ValidationJobModel.status.in_(["pending", "running"]))
            .order_by(desc(ValidationJobModel.created_at))
            .limit(1)
        )
        existing_validation = existing_validation_result.scalars().first()

        if existing_validation:
            # Return the existing validation job instead of creating a new one
            return ValidateArchiveResponse(
                task_id=existing_validation.task_id,
                job_id=existing_validation.id,
                archive_id=latest_archive.id,
                status=existing_validation.status,
            )

    # Create a new validation request
    validation_request = ValidateArchiveRequest(archive_id=latest_archive.id)

    # Use the existing create_validation_job logic
    return await create_validation_job(validation_request, current_user, db)
