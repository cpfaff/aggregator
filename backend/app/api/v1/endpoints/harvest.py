"""
Legacy harvest API endpoint.

This module provides the legacy harvesting endpoint for external systems
to retrieve all datasets in a legacy format.
"""

import logging
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.deps import limiter
from app.core.config import settings
from app.db import get_db
from app.models import DataProviderModel, DatasetModel
from app.schemas import LegacyDataset, LegacyUsefulLink, LegacyXmlArchive

logger = logging.getLogger("api")

router = APIRouter()

# Type alias for database session dependency
DbSession = Annotated[AsyncSession, Depends(get_db)]


@router.get("/legacy-data-sets", response_model=list[LegacyDataset])
@limiter.limit(settings.HARVEST_RATE_LIMIT)
async def harvest_datasets(request: Request, db: DbSession):
    """
    Retrieve all datasets in a legacy format for harvesting purposes.

    This endpoint is used by external systems to harvest dataset information
    in a flattened format that includes provider details with each dataset.
    """
    try:
        # Query all providers with their datasets, xml archives, and useful links
        query = select(DataProviderModel).options(
            selectinload(DataProviderModel.datasets).selectinload(DatasetModel.xmlArchives),
            selectinload(DataProviderModel.datasets).selectinload(DatasetModel.usefulLinks),
        )

        result = await db.execute(query)
        providers = result.scalars().all()

        # Transform to legacy format
        legacy_datasets = []
        for provider in providers:
            sorted_datasets = sorted(provider.datasets, key=lambda ds: ds.id)
            for ds in sorted_datasets:
                # Gate the feed on harvest-ready: staged (not-ready) datasets are
                # excluded so they never reach the public index. Skipping here
                # preserves the ready subset's id ordering.
                if not ds.isHarvestReady:
                    continue

                # Convert XML archives to legacy format
                xml_archives = []
                for archive in ds.xmlArchives:
                    xml_archives.append(
                        LegacyXmlArchive(
                            archive_id=archive.id,
                            xml_archive=archive.url,
                            latest=archive.isLatest,
                        )
                    )

                # Convert useful links to legacy format
                useful_links = []
                for link in ds.usefulLinks:
                    useful_links.append(
                        LegacyUsefulLink(
                            link_id=link.id,
                            title=link.title,
                            url=link.url,
                            is_latest=link.isLatest,
                        )
                    )

                # Create legacy dataset
                legacy_dataset = LegacyDataset(
                    dataset_id=ds.id,
                    datasource=ds.source,
                    dataset=ds.title,
                    custom_landingpage=ds.landingPageUrl,
                    provider_id=provider.id,
                    xml_archives=xml_archives,
                    useful_links=useful_links,
                    provider_datacenter=provider.datacenter,
                    provider_shortname=provider.shortName,
                    provider_name=provider.name,
                    provider_url=provider.url,
                    biocase_url=provider.biocaseUrl,
                    is_data_center=provider.isDataCenter,
                )
                legacy_datasets.append(legacy_dataset)

        return legacy_datasets
    except Exception as e:
        logger.error(f"Error in harvest endpoint: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}") from e
