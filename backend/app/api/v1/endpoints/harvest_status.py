"""API endpoint for the per-dataset harvest-success indicator.

Thin HTTP-contract layer over :class:`~app.services.harvest_status_service.HarvestStatusService`
(built in T-7.1, which owns the state-mapping / URN / M-of-N logic). This module
adds no business logic: it wires the service's three frozen constructor
dependencies and delegates by ``dataset_id``.

**Wiring N async-safely.** ``HarvestStatusService`` takes an injected
``unit_count_provider`` because the snapshot unit-count path is *sync-session
only* (``SnapshotService`` runs blocking ``Session`` queries; constructing it
against the async session would raise ``MissingGreenlet`` at query time). So this
async handler fetches the expected unit count **N** here — off the event loop, via
the sync ``Session`` injected as ``sync_db`` and run in the threadpool — then
passes a constant closure ``lambda _dataset_id: n`` to the service. The await /
blocking fetch happens in the endpoint; the sync callable the service invokes
never touches the DB or the loop.
"""

from typing import Annotated

from fastapi import APIRouter, Depends
from fastapi.concurrency import run_in_threadpool
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Session

from app.db.session import get_db, get_sync_db
from app.models import UserModel
from app.schemas.harvest_status import HarvestStatusResponse
from app.security import get_current_user
from app.services.es_gateway import EsGateway
from app.services.harvest_status_service import HarvestStatusService
from app.services.snapshot_service import SnapshotService

router = APIRouter()


@router.get("/{dataset_id}/harvest-status", response_model=HarvestStatusResponse)
async def get_dataset_harvest_status(
    dataset_id: int,
    current_user: Annotated[UserModel, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
    sync_db: Annotated[Session, Depends(get_sync_db)],
) -> HarvestStatusResponse:
    """Return the per-dataset harvest-success status.

    Auth is enforced by ``Depends(get_current_user)``; ``current_user`` is unused
    in the body but must stay in the signature for that wiring. The expected unit
    count (N) is fetched off the event loop via the sync session, then frozen into
    a constant closure handed to the service.
    """
    expected_units = await run_in_threadpool(
        SnapshotService(sync_db).get_dataset_unit_count, dataset_id
    )
    service = HarvestStatusService(
        db,
        EsGateway(),
        lambda _dataset_id: expected_units,
    )
    return await service.get_harvest_status(dataset_id)
