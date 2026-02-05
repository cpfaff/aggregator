"""
Useful Links management API endpoints.

This module contains endpoints for useful links CRUD operations.
"""

import logging
from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import csrf_protect, provider_permission
from app.core.cache import cache_response
from app.db import get_db
from app.models import UserModel
from app.schemas import UsefulLink
from app.services.links_service import LinksService

logger = logging.getLogger("api")

router = APIRouter()


@router.get(
    "/{provider_id}/data-sets/{dataset_id}/useful-links",
    response_model=list[UsefulLink],
    summary="List useful links",
)
@cache_response(prefix="useful-links", ttl_seconds=300)
async def get_useful_links(
    provider_id: int,
    dataset_id: int,
    current_user: Annotated[UserModel, Depends(provider_permission("read"))],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """
    List all useful links for a specific dataset. Requires read permissions.
    - **provider_id**: Must be a positive integer
    - **dataset_id**: Must be a positive integer
    """
    service = LinksService(db)
    return await service.list_links(provider_id, dataset_id)


@csrf_protect.validate_csrf
@router.post(
    "/{provider_id}/data-sets/{dataset_id}/useful-links",
    response_model=UsefulLink,
    status_code=201,
    summary="Create useful link",
)
async def create_useful_link(
    provider_id: int,
    dataset_id: int,
    useful_link: UsefulLink,
    current_user: Annotated[UserModel, Depends(provider_permission("write"))],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """
    Create a new useful link for a specific dataset. Requires write permissions.
    - **provider_id**: Must be a positive integer
    - **dataset_id**: Must be a positive integer
    """
    service = LinksService(db)
    return await service.create_link(provider_id, dataset_id, useful_link)
