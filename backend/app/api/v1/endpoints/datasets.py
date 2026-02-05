"""
Dataset CRUD API endpoints.

This module contains endpoints for dataset management operations
including listing, retrieving, creating, updating, and deleting datasets.
"""

import logging
from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import csrf_protect, provider_permission
from app.core.cache import cache_response
from app.db import get_db
from app.models import UserModel
from app.schemas import Dataset
from app.services.dataset_service import DatasetService

logger = logging.getLogger("api")

router = APIRouter()


@router.get(
    "/{provider_id}/data-sets",
    response_model=list[Dataset],
    summary="List datasets for provider",
)
@cache_response(prefix="datasets", ttl_seconds=300)
async def get_datasets(
    provider_id: int,
    current_user: Annotated[UserModel, Depends(provider_permission("read"))],
    db: Annotated[AsyncSession, Depends(get_db)],
    title: Annotated[str | None, Query(description="Filter by dataset title")] = None,
    source: Annotated[str | None, Query(description="Filter by dataset source")] = None,
    skip: Annotated[int, Query(ge=0, description="Number of items to skip")] = 0,
    limit: Annotated[
        int, Query(ge=1, le=1000, description="Maximum number of items to return")
    ] = 100,
):
    """
    List all datasets for a specific data provider. Requires read permissions.
    - **provider_id**: Must be a positive integer

    Supports filtering by title or source and pagination with skip/limit.
    """
    service = DatasetService(db)
    return await service.list_datasets(
        provider_id=provider_id,
        skip=skip,
        limit=limit,
        title=title,
        source=source,
    )


@router.get(
    "/{provider_id}/data-sets/{dataset_id}",
    response_model=Dataset,
    summary="Get dataset by ID",
)
@cache_response(prefix="dataset", ttl_seconds=300)
async def get_dataset(
    provider_id: int,
    dataset_id: int,
    current_user: Annotated[UserModel, Depends(provider_permission("read"))],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """
    Retrieve a dataset by its ID for a specific provider. Requires read permissions.
    - **provider_id**: Must be a positive integer
    - **dataset_id**: Must be a positive integer
    """
    service = DatasetService(db)
    return await service.get_dataset_or_404(dataset_id, provider_id)


@csrf_protect.validate_csrf
@router.post(
    "/{provider_id}/data-sets",
    response_model=Dataset,
    status_code=201,
    summary="Create a new dataset",
)
async def create_dataset(
    provider_id: int,
    dataset: Dataset,
    current_user: Annotated[UserModel, Depends(provider_permission("write"))],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """
    Create a new dataset for a specific provider. Requires write permissions.
    - **provider_id**: Must be a positive integer
    """
    service = DatasetService(db)
    return await service.create_dataset(provider_id, dataset)


@csrf_protect.validate_csrf
@router.put(
    "/{provider_id}/data-sets/{dataset_id}",
    response_model=Dataset,
    summary="Update dataset",
)
async def update_dataset(
    provider_id: int,
    dataset_id: int,
    dataset: Dataset,
    current_user: Annotated[UserModel, Depends(provider_permission("write"))],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """
    Update a dataset for a specific provider. Requires write permissions.
    - **provider_id**: Must be a positive integer
    - **dataset_id**: Must be a positive integer
    """
    service = DatasetService(db)
    return await service.update_dataset(dataset_id, provider_id, dataset)


@csrf_protect.validate_csrf
@router.delete(
    "/{provider_id}/data-sets/{dataset_id}",
    status_code=204,
    summary="Delete dataset",
)
async def delete_dataset(
    provider_id: int,
    dataset_id: int,
    current_user: Annotated[UserModel, Depends(provider_permission("delete"))],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """
    Delete a dataset for a specific provider. Requires delete permissions.

    This performs a complete cascade deletion, removing:
    - All statistics records for the dataset
    - All validation jobs for the dataset's archives
    - All XML archives
    - All useful links
    - The dataset itself

    After deletion, provider statistics are automatically re-aggregated.

    - **provider_id**: Must be a positive integer
    - **dataset_id**: Must be a positive integer
    """
    service = DatasetService(db)
    await service.delete_dataset(dataset_id, provider_id)
    return
