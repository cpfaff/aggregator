"""
API endpoints for XML validation tasks.
"""

from datetime import datetime
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_filtering_params, get_pagination_params, get_sorting_params
from app.db.session import get_db
from app.models import UserModel
from app.schemas.pagination import PaginatedResponse, PaginationParams
from app.security import get_current_user
from app.services.validation_service import ValidationService
from app.utils.filtering import FilterParam
from app.utils.sorting import SortParam

router = APIRouter()

# Allowed fields for filtering and sorting validation jobs
VALIDATION_FILTER_FIELDS = ["archive_id", "status"]
VALIDATION_SORT_FIELDS = ["id", "created_at", "status"]


class ValidateRequest(BaseModel):
    """
    Request model for submitting a validation task.

    Either dataset_id or archive_id must be provided:
    - If dataset_id is provided, validates the latest archive for that dataset
    - If archive_id is provided, validates that specific archive
    - If both are provided, archive_id takes precedence
    """

    dataset_id: int | None = Field(
        None, description="ID of the dataset to validate (uses latest archive)"
    )
    archive_id: int | None = Field(None, description="ID of the XML archive to validate")
    force: bool = Field(
        False,
        description="If True, create a new validation job even if one already exists",
    )


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
    completed_at: datetime | None = None
    total_files: int | None = None
    valid_files: int | None = None
    error_count: int | None = None
    validation_time: float | None = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class DatasetValidationStatus(BaseModel):
    """
    Response model for dataset validation status.
    """

    dataset_id: int
    archive_id: int | None = None
    has_latest_archive: bool
    validation_status: str | None = None  # not_validated, pending, running, completed, failed
    validation_id: int | None = None
    last_validated_at: datetime | None = None

    # Core quality indicators (for quick access without parsing the full results)
    is_valid: bool | None = None
    quality_score: float | None = None

    # Complete validation results as JSON
    validation_results: dict[str, Any] | None = None

    model_config = ConfigDict(from_attributes=True)


@router.post("/", response_model=ValidateArchiveResponse, status_code=status.HTTP_201_CREATED)
async def create_validation_job(
    request: ValidateRequest,
    current_user: Annotated[UserModel, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """
    Start a validation job for an XML archive.

    Either dataset_id or archive_id must be provided:
    - If dataset_id is provided, validates the latest archive for that dataset
    - If archive_id is provided, validates that specific archive
    - If both are provided, archive_id takes precedence

    Args:
        request: The validation request with dataset_id and/or archive_id
        current_user: The current authenticated user
        db: Database session

    Returns:
        Information about the submitted validation job

    Raises:
        HTTPException: If neither dataset_id nor archive_id is provided
    """
    service = ValidationService(db)

    # archive_id takes precedence if provided
    if request.archive_id is not None:
        return await service.create_validation_job(request.archive_id)
    elif request.dataset_id is not None:
        return await service.validate_dataset_latest_archive(
            request.dataset_id, force=request.force
        )
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Either dataset_id or archive_id must be provided",
        )


@router.get("/{job_id}", response_model=ValidationJobResponse)
async def get_validation_job(
    job_id: int,
    current_user: Annotated[UserModel, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
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


@router.get("/", response_model=PaginatedResponse[ValidationJobResponse])
async def list_validation_jobs(
    current_user: Annotated[UserModel, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
    pagination: Annotated[PaginationParams, Depends(get_pagination_params)],
    filters: Annotated[list[FilterParam], Depends(get_filtering_params(VALIDATION_FILTER_FIELDS))],
    sorts: Annotated[list[SortParam], Depends(get_sorting_params(VALIDATION_SORT_FIELDS))],
):
    """
    List validation jobs with optional filtering.

    Supports standardized filtering with filter[field]=value or filter[field][op]=value syntax,
    sorting with sort=field:direction syntax, and cursor-based pagination.

    **Filterable fields:** archive_id, status
    **Sortable fields:** id, created_at, status
    **Filter operators:** eq, ne, gt, gte, lt, lte, like, in

    Args:
        pagination: Cursor-based pagination parameters
        filters: Filter parameters
        sorts: Sort parameters
        current_user: The current authenticated user
        db: Database session

    Returns:
        Paginated list of validation jobs
    """
    service = ValidationService(db)
    return await service.list_validation_jobs(filters=filters, sorts=sorts, pagination=pagination)


@router.get("/{job_id}/results", response_model=dict[str, Any])
async def get_validation_results(
    job_id: int,
    current_user: Annotated[UserModel, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
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
    current_user: Annotated[UserModel, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
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
