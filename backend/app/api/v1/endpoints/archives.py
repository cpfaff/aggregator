"""
XML Archive management API endpoints.

This module contains endpoints for XML archive CRUD operations.
"""

import logging
from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import csrf_protect, provider_permission
from app.core.cache import cache_response
from app.db import get_db
from app.models import UserModel
from app.schemas import XmlArchive
from app.services.archive_service import ArchiveService

logger = logging.getLogger("api")

router = APIRouter()


@router.get(
    "/{provider_id}/data-sets/{dataset_id}/xml-archives",
    response_model=list[XmlArchive],
    summary="List XML archives",
)
@cache_response(prefix="xml-archives", ttl_seconds=300)
async def get_xml_archives(
    provider_id: int,
    dataset_id: int,
    current_user: Annotated[UserModel, Depends(provider_permission("read"))],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """
    List all XML archives for a specific dataset. Requires read permissions.
    - **provider_id**: Must be a positive integer
    - **dataset_id**: Must be a positive integer
    """
    service = ArchiveService(db)
    return await service.list_archives(provider_id, dataset_id)


@csrf_protect.validate_csrf
@router.post(
    "/{provider_id}/data-sets/{dataset_id}/xml-archives",
    response_model=XmlArchive,
    status_code=201,
    summary="Create XML archive",
)
async def create_xml_archive(
    provider_id: int,
    dataset_id: int,
    xml_archive: XmlArchive,
    current_user: Annotated[UserModel, Depends(provider_permission("write"))],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """
    Create a new XML archive for a specific dataset. Requires write permissions.
    - **provider_id**: Must be a positive integer
    - **dataset_id**: Must be a positive integer
    """
    service = ArchiveService(db)
    return await service.create_archive(provider_id, dataset_id, xml_archive)
