"""
API endpoints for XML validation tasks.
"""
from typing import Dict, Any, List, Optional
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks
from pydantic import BaseModel, Field, ConfigDict
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import UserModel
from app.security import get_current_user
from app.db.session import get_db
from app.services.validation_service import ValidationService

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
    service = ValidationService(db)
    return await service.create_validation_job(request.archive_id)


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
    service = ValidationService(db)
    return await service.get_validation_job(job_id)


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
    service = ValidationService(db)
    return await service.list_validation_jobs(
        archive_id=archive_id,
        status_filter=status,
        limit=limit,
        offset=offset
    )


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
    service = ValidationService(db)
    return await service.get_validation_results(job_id)


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
    service = ValidationService(db)
    result = await service.get_dataset_validation_status(dataset_id)

    # Convert dict to Pydantic model for response
    return DatasetValidationStatus(**result)


@router.post("/datasets/{dataset_id}/validate", response_model=ValidateArchiveResponse, status_code=status.HTTP_201_CREATED)
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
    service = ValidationService(db)
    return await service.validate_dataset_latest_archive(dataset_id, force=force)
