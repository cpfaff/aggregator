"""
Data provider management API endpoints.

This module contains endpoints for provider CRUD operations.
"""

import logging
from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import csrf_protect, provider_permission
from app.core.cache import cache_response
from app.db import get_db
from app.models import UserModel
from app.schemas import DataProvider
from app.security import check_global_admin, get_current_user
from app.services.provider_service import ProviderService

logger = logging.getLogger("api")

router = APIRouter()


@router.get("", response_model=list[DataProvider], summary="List data providers")
@cache_response(prefix="providers", ttl_seconds=300)
async def get_providers(
    current_user: Annotated[UserModel, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
    name: Annotated[str | None, Query(description="Filter by provider name")] = None,
    datacenter: Annotated[str | None, Query(description="Filter by datacenter")] = None,
    skip: Annotated[int, Query(ge=0, description="Number of items to skip")] = 0,
    limit: Annotated[
        int, Query(ge=1, le=1000, description="Maximum number of items to return")
    ] = 100,
):
    """
    List all data providers the current user has access to.

    Supports filtering by name or datacenter and pagination with skip/limit.
    """
    service = ProviderService(db)
    return await service.list_providers(
        user=current_user,
        name=name,
        datacenter=datacenter,
        skip=skip,
        limit=limit,
    )


@router.get(
    "/{provider_id}",
    response_model=DataProvider,
    summary="Get data provider by ID",
)
@cache_response(prefix="provider", ttl_seconds=300)
async def get_provider(
    provider_id: int,
    current_user: Annotated[UserModel, Depends(provider_permission("read"))],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """
    Retrieve a data provider by its ID. Requires appropriate permissions.
    - **provider_id**: Must be a positive integer
    """
    service = ProviderService(db)
    return await service.get_provider_or_404(provider_id)


@csrf_protect.validate_csrf
@router.post(
    "",
    response_model=DataProvider,
    status_code=201,
    summary="Create a new data provider",
)
async def create_provider(
    provider: DataProvider,
    current_user: Annotated[UserModel, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """
    Create a new data provider. Requires global admin privileges.
    - **datacenter**: Datacenter name
    - **shortName**: Short name of the provider
    - **name**: Full name of the provider
    - **url**: Optional provider URL
    - **biocaseUrl**: Optional BioCASe URL
    - **isDataCenter**: Optional boolean indicating if the provider is a data center (global admin only)
    - **datasets**: Optional list of datasets
    """
    check_global_admin(current_user)
    service = ProviderService(db)
    return await service.create_provider(provider, current_user)


@csrf_protect.validate_csrf
@router.put(
    "/{provider_id}",
    response_model=DataProvider,
    summary="Update data provider",
)
async def update_provider(
    provider_id: int,
    provider: DataProvider,
    current_user: Annotated[UserModel, Depends(provider_permission("write"))],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """
    Update a data provider. Requires write permissions for the provider.
    - **provider_id**: Must be a positive integer

    Note: The isDataCenter field can only be modified by global admins.
    """
    service = ProviderService(db)
    return await service.update_provider(provider_id, provider, current_user)


@csrf_protect.validate_csrf
@router.delete("/{provider_id}", status_code=204, summary="Delete data provider")
async def delete_provider(
    provider_id: int,
    current_user: Annotated[UserModel, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """
    Delete a data provider. Requires global admin privileges.
    - **provider_id**: Must be a positive integer
    """
    check_global_admin(current_user)
    service = ProviderService(db)
    await service.delete_provider(provider_id, current_user)
    return
