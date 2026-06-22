"""HarvestStatusService — per-dataset harvest-success assembly.

Pure backend logic: load the dataset (async) with its archives, derive the
dataset-level URN from the latest archive, short-circuit ``staged`` when the
dataset is not harvest-ready (without touching ES), ask the injected
:class:`~app.services.es_gateway.EsGateway` for presence / M / last-seen, ask the
injected N-provider for the expected unit count, and map every outcome onto the
:class:`~app.schemas.harvest_status.HarvestStatus` enum per the state table.

**No degrade/fallback.** Every state is computed per-dataset. The only soft
outcomes are the deliberate ``staged`` short-circuit and the honest ``unknown``
when the gateway itself reports ES is down. The N lookup is an injected
``Callable`` so this service never constructs the sync-session-only
``SnapshotService`` against the async session (which would raise
``MissingGreenlet`` at query time); the wiring ticket supplies the real
sync-backed callable, tests supply a stub.
"""

import logging
from collections.abc import Callable
from datetime import UTC, datetime

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.dataset import DatasetModel, XmlArchiveModel
from app.schemas.harvest_status import HarvestStatus, HarvestStatusResponse
from app.services.es_gateway import EsUnavailable, compose_dataset_urn

logger = logging.getLogger(__name__)


class HarvestStatusService:
    """Assemble the per-dataset harvest-success indicator."""

    def __init__(
        self,
        db: AsyncSession,
        es_gateway,
        unit_count_provider: Callable[[int], int | None],
    ) -> None:
        self.db = db
        self.es_gateway = es_gateway
        self.unit_count_provider = unit_count_provider

    def _derive_urn(self, dataset: DatasetModel, latest_archive: XmlArchiveModel) -> str:
        """Compose the dataset-level URN from the provider, dataset and archive ids."""
        return compose_dataset_urn(dataset.provider_id, dataset.id, latest_archive.id)

    def _pick_latest_archive(self, archives: list[XmlArchiveModel]) -> XmlArchiveModel | None:
        """Pick the latest archive, deterministically.

        Prefers rows explicitly flagged ``isLatest is True``; among multiple
        flagged rows the deterministic ``max(id)`` wins. When **no** row is
        flagged (``isLatest`` is ``False`` or the nullable ``None``), fall back to
        the ``max(id)`` across all archives. Returns ``None`` only when the
        dataset has no archives at all.
        """
        if not archives:
            return None
        flagged = [archive for archive in archives if archive.isLatest is True]
        candidates = flagged if flagged else archives
        return max(candidates, key=lambda archive: archive.id)

    async def get_harvest_status(self, dataset_id: int) -> HarvestStatusResponse:
        """Compute the harvest-success status for ``dataset_id``.

        Raises ``HTTPException(404)`` when the dataset does not exist or has no
        archive from which a URN can be derived. Returns ``staged`` (without any
        gateway call) when the dataset is not harvest-ready, ``unknown`` when the
        gateway reports ES is down, and otherwise maps M/N per the state table.
        """
        result = await self.db.execute(
            select(DatasetModel)
            .where(DatasetModel.id == dataset_id)
            .options(selectinload(DatasetModel.xmlArchives))
        )
        dataset = result.scalar_one_or_none()

        if dataset is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Dataset with ID {dataset_id} not found",
            )

        checked_at = datetime.now(UTC)

        # Staged short-circuit: do NOT touch the gateway or the N-provider.
        if not dataset.isHarvestReady:
            return HarvestStatusResponse(
                dataset_id=dataset_id,
                is_harvest_ready=False,
                harvest_status=HarvestStatus.STAGED,
                units_in_index=None,
                units_expected=None,
                last_seen_in_index_at=None,
                index_checked_at=checked_at,
            )

        latest_archive = self._pick_latest_archive(list(dataset.xmlArchives))
        if latest_archive is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"No latest XML archive found for dataset with ID {dataset_id}",
            )

        urn = self._derive_urn(dataset, latest_archive)

        try:
            count = await self.es_gateway.count_for_urn(urn)
            last_seen = await self.es_gateway.latest_datestamp_for_urn(urn)
        except EsUnavailable:
            logger.warning("ES unavailable for dataset_id=%s urn=%s", dataset_id, urn)
            return HarvestStatusResponse(
                dataset_id=dataset_id,
                is_harvest_ready=True,
                harvest_status=HarvestStatus.UNKNOWN,
                units_in_index=None,
                units_expected=None,
                last_seen_in_index_at=None,
                index_checked_at=checked_at,
            )

        present = count >= 1
        m = max(count - 1, 0)
        n = self.unit_count_provider(dataset_id)

        if not present:
            harvest_status = HarvestStatus.NOT_IN_INDEX
        elif n is not None and m < n:
            harvest_status = HarvestStatus.PARTIAL
        else:
            harvest_status = HarvestStatus.IN_INDEX

        return HarvestStatusResponse(
            dataset_id=dataset_id,
            is_harvest_ready=True,
            harvest_status=harvest_status,
            units_in_index=m,
            units_expected=n,
            last_seen_in_index_at=last_seen if present else None,
            index_checked_at=checked_at,
        )
