"""Unit tests for HarvestStatusService.

Proves URN derivation (incl. the deterministic ``max(id)`` latest-archive
tie-break), the ``staged`` short-circuit (gateway/N never consulted), the full
state-mapping table (``partial`` / ``in_index`` / ``not_in_index`` / ``unknown``),
the N-None M-only degrade, and the 404 on a missing dataset — all against the
**real async ``db_session``** testcontainer fixture with a **mocked ``EsGateway``**
(no live ES, no ``httpx``).
"""

from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock

import pytest
import pytest_asyncio
from fastapi import HTTPException

from app.models.dataset import DatasetModel, XmlArchiveModel
from app.models.provider import DataProviderModel
from app.schemas.harvest_status import HarvestStatus, HarvestStatusResponse
from app.services.es_gateway import EsUnavailable
from app.services.harvest_status_service import HarvestStatusService


# --------------------------------------------------------------------------- #
# Seed helpers
# --------------------------------------------------------------------------- #
async def _seed_provider(db_session, provider_id: int = 1) -> DataProviderModel:
    provider = DataProviderModel(
        id=provider_id,
        datacenter="test-datacenter",
        shortName="TP",
        name="Test Provider",
    )
    db_session.add(provider)
    await db_session.flush()
    return provider


async def _seed_dataset(
    db_session,
    provider_id: int,
    dataset_id: int = 1,
    *,
    is_harvest_ready: bool = True,
) -> DatasetModel:
    dataset = DatasetModel(
        id=dataset_id,
        title="Test Dataset",
        source="test-source",
        provider_id=provider_id,
        landingPageUrl="http://example.com/landing",
        isHarvestReady=is_harvest_ready,
    )
    db_session.add(dataset)
    await db_session.flush()
    return dataset


async def _seed_archive(
    db_session,
    dataset_id: int,
    archive_id: int,
    *,
    is_latest: bool | None,
) -> XmlArchiveModel:
    archive = XmlArchiveModel(
        id=archive_id,
        dataset_id=dataset_id,
        url=f"http://example.com/archive-{archive_id}.xml",
        isLatest=is_latest,
    )
    db_session.add(archive)
    await db_session.flush()
    return archive


def _gateway(*, count: int | None = None, last_seen: datetime | None = None) -> MagicMock:
    """Build a mocked EsGateway with AsyncMock operations.

    ``count``/``last_seen`` set the success return values; tests that need an
    ES-down outcome override ``count_for_urn.side_effect`` themselves.
    """
    gateway = MagicMock()
    gateway.count_for_urn = AsyncMock(return_value=count)
    gateway.latest_datestamp_for_urn = AsyncMock(return_value=last_seen)
    return gateway


@pytest_asyncio.fixture
async def provider(db_session):
    return await _seed_provider(db_session)


# --------------------------------------------------------------------------- #
# AC-2: URN derivation — exact string
# --------------------------------------------------------------------------- #
@pytest.mark.asyncio
async def test_derive_urn_exact_string(db_session):
    await _seed_provider(db_session, provider_id=7)
    await _seed_dataset(db_session, provider_id=7, dataset_id=42)
    await _seed_archive(db_session, dataset_id=42, archive_id=99, is_latest=True)

    gateway = _gateway(count=1, last_seen=None)
    unit_count_provider = MagicMock(return_value=0)
    service = HarvestStatusService(db_session, gateway, unit_count_provider)

    await service.get_harvest_status(42)

    gateway.count_for_urn.assert_awaited_once_with("urn:gfbio.org:abcd:7_42_99")


# --------------------------------------------------------------------------- #
# AC-3: tie-break — multiple flagged latest -> max id among the flagged
# --------------------------------------------------------------------------- #
@pytest.mark.asyncio
async def test_pick_latest_multiple_flagged(db_session, provider):
    await _seed_dataset(db_session, provider_id=provider.id, dataset_id=1)
    await _seed_archive(db_session, dataset_id=1, archive_id=3, is_latest=True)
    await _seed_archive(db_session, dataset_id=1, archive_id=9, is_latest=True)
    await _seed_archive(db_session, dataset_id=1, archive_id=5, is_latest=True)

    gateway = _gateway(count=1, last_seen=None)
    service = HarvestStatusService(db_session, gateway, MagicMock(return_value=0))

    await service.get_harvest_status(1)

    urn = gateway.count_for_urn.await_args.args[0]
    assert urn.endswith("_9"), urn


# --------------------------------------------------------------------------- #
# AC-4: tie-break — zero flagged (incl. a None row) -> max id across all
# --------------------------------------------------------------------------- #
@pytest.mark.asyncio
async def test_pick_latest_zero_flagged(db_session, provider):
    await _seed_dataset(db_session, provider_id=provider.id, dataset_id=1)
    await _seed_archive(db_session, dataset_id=1, archive_id=4, is_latest=False)
    await _seed_archive(db_session, dataset_id=1, archive_id=11, is_latest=False)
    await _seed_archive(db_session, dataset_id=1, archive_id=7, is_latest=None)

    gateway = _gateway(count=1, last_seen=None)
    service = HarvestStatusService(db_session, gateway, MagicMock(return_value=0))

    await service.get_harvest_status(1)

    urn = gateway.count_for_urn.await_args.args[0]
    assert urn.endswith("_11"), urn


# --------------------------------------------------------------------------- #
# AC-5: staged short-circuit — gateway NOT awaited, N NOT called
# --------------------------------------------------------------------------- #
@pytest.mark.asyncio
async def test_staged_short_circuits_without_gateway(db_session, provider):
    await _seed_dataset(db_session, provider_id=provider.id, dataset_id=1, is_harvest_ready=False)
    await _seed_archive(db_session, dataset_id=1, archive_id=1, is_latest=True)

    gateway = _gateway(count=1, last_seen=datetime.now(UTC))
    unit_count_provider = MagicMock(return_value=5)
    service = HarvestStatusService(db_session, gateway, unit_count_provider)

    result = await service.get_harvest_status(1)

    assert result.harvest_status == HarvestStatus.STAGED
    assert result.units_in_index is None
    assert result.units_expected is None
    assert result.last_seen_in_index_at is None
    assert result.is_harvest_ready is False
    assert result.index_checked_at.tzinfo is not None
    gateway.count_for_urn.assert_not_awaited()
    gateway.latest_datestamp_for_urn.assert_not_awaited()
    unit_count_provider.assert_not_called()


# --------------------------------------------------------------------------- #
# AC-6: partial — present and M < N
# --------------------------------------------------------------------------- #
@pytest.mark.asyncio
async def test_state_partial_when_m_less_than_n(db_session, provider):
    await _seed_dataset(db_session, provider_id=provider.id, dataset_id=1)
    await _seed_archive(db_session, dataset_id=1, archive_id=1, is_latest=True)

    last_seen = datetime(2026, 6, 1, 12, 0, tzinfo=UTC)
    gateway = _gateway(count=4, last_seen=last_seen)  # M = 3
    unit_count_provider = MagicMock(return_value=5)  # N = 5
    service = HarvestStatusService(db_session, gateway, unit_count_provider)

    result = await service.get_harvest_status(1)

    assert result.harvest_status == HarvestStatus.PARTIAL
    assert result.units_in_index == 3
    assert result.units_expected == 5
    assert result.last_seen_in_index_at == last_seen
    assert result.index_checked_at.tzinfo is not None


# --------------------------------------------------------------------------- #
# AC-7: in_index — M >= N (proves >=, not ==)
# --------------------------------------------------------------------------- #
@pytest.mark.asyncio
async def test_state_in_index_when_m_ge_n(db_session, provider):
    await _seed_dataset(db_session, provider_id=provider.id, dataset_id=1)
    await _seed_archive(db_session, dataset_id=1, archive_id=1, is_latest=True)

    # M == N
    gateway = _gateway(count=6, last_seen=None)  # M = 5
    unit_count_provider = MagicMock(return_value=5)  # N = 5
    service = HarvestStatusService(db_session, gateway, unit_count_provider)

    result = await service.get_harvest_status(1)
    assert result.harvest_status == HarvestStatus.IN_INDEX
    assert result.units_in_index == 5
    assert result.units_expected == 5

    # M > N -> still in_index (over-count must not wrap to partial)
    gateway_over = _gateway(count=7, last_seen=None)  # M = 6
    service_over = HarvestStatusService(db_session, gateway_over, MagicMock(return_value=5))
    result_over = await service_over.get_harvest_status(1)
    assert result_over.harvest_status == HarvestStatus.IN_INDEX
    assert result_over.units_in_index == 6
    assert result_over.units_expected == 5


# --------------------------------------------------------------------------- #
# AC-8: in_index — N unknown degrades cleanly (M-only)
# --------------------------------------------------------------------------- #
@pytest.mark.asyncio
async def test_state_in_index_when_n_none(db_session, provider):
    await _seed_dataset(db_session, provider_id=provider.id, dataset_id=1)
    await _seed_archive(db_session, dataset_id=1, archive_id=1, is_latest=True)

    gateway = _gateway(count=3, last_seen=None)  # M = 2
    unit_count_provider = MagicMock(return_value=None)  # N unknown
    service = HarvestStatusService(db_session, gateway, unit_count_provider)

    result = await service.get_harvest_status(1)

    assert result.harvest_status == HarvestStatus.IN_INDEX
    assert result.units_in_index == 2
    assert result.units_expected is None


# --------------------------------------------------------------------------- #
# AC-9: not_in_index — harvest-ready, absent (count == 0, M == 0)
# --------------------------------------------------------------------------- #
@pytest.mark.asyncio
async def test_state_not_in_index_when_ready_and_absent(db_session, provider):
    await _seed_dataset(db_session, provider_id=provider.id, dataset_id=1)
    await _seed_archive(db_session, dataset_id=1, archive_id=1, is_latest=True)

    gateway = _gateway(count=0, last_seen=None)  # present False, M = 0
    unit_count_provider = MagicMock(return_value=5)  # N = 5 (echoed)
    service = HarvestStatusService(db_session, gateway, unit_count_provider)

    result = await service.get_harvest_status(1)

    assert result.harvest_status == HarvestStatus.NOT_IN_INDEX
    assert result.units_in_index == 0
    assert result.last_seen_in_index_at is None


# --------------------------------------------------------------------------- #
# AC-10: unknown — ES down, N not consulted
# --------------------------------------------------------------------------- #
@pytest.mark.asyncio
async def test_state_unknown_when_gateway_down(db_session, provider):
    await _seed_dataset(db_session, provider_id=provider.id, dataset_id=1)
    await _seed_archive(db_session, dataset_id=1, archive_id=1, is_latest=True)

    gateway = MagicMock()
    gateway.count_for_urn = AsyncMock(side_effect=EsUnavailable("ES down"))
    gateway.latest_datestamp_for_urn = AsyncMock(side_effect=EsUnavailable("ES down"))
    unit_count_provider = MagicMock(return_value=5)
    service = HarvestStatusService(db_session, gateway, unit_count_provider)

    result = await service.get_harvest_status(1)

    assert result.harvest_status == HarvestStatus.UNKNOWN
    assert result.units_in_index is None
    assert result.units_expected is None
    assert result.last_seen_in_index_at is None
    unit_count_provider.assert_not_called()


# --------------------------------------------------------------------------- #
# AC-11: dataset not found -> 404, gateway not awaited
# --------------------------------------------------------------------------- #
@pytest.mark.asyncio
async def test_get_harvest_status_unknown_dataset(db_session):
    gateway = _gateway(count=1, last_seen=None)
    service = HarvestStatusService(db_session, gateway, MagicMock(return_value=0))

    with pytest.raises(HTTPException) as exc_info:
        await service.get_harvest_status(999)

    assert exc_info.value.status_code == 404
    gateway.count_for_urn.assert_not_awaited()


# --------------------------------------------------------------------------- #
# Edge: harvest-ready dataset with NO archives -> 404 (URN underivable),
# distinct from the ES-down unknown path.
# --------------------------------------------------------------------------- #
@pytest.mark.asyncio
async def test_get_harvest_status_no_archive_raises_404(db_session, provider):
    await _seed_dataset(db_session, provider_id=provider.id, dataset_id=1)

    gateway = _gateway(count=1, last_seen=None)
    service = HarvestStatusService(db_session, gateway, MagicMock(return_value=0))

    with pytest.raises(HTTPException) as exc_info:
        await service.get_harvest_status(1)

    assert exc_info.value.status_code == 404
    gateway.count_for_urn.assert_not_awaited()


# --------------------------------------------------------------------------- #
# AC-13: response model is snake_case Pydantic v2 with from_attributes
# --------------------------------------------------------------------------- #
def test_response_model_snake_case_and_from_attributes():
    expected_fields = {
        "dataset_id",
        "is_harvest_ready",
        "harvest_status",
        "units_in_index",
        "units_expected",
        "last_seen_in_index_at",
        "index_checked_at",
    }
    assert set(HarvestStatusResponse.model_fields) == expected_fields

    source = MagicMock(
        dataset_id=1,
        is_harvest_ready=True,
        harvest_status=HarvestStatus.PARTIAL,
        units_in_index=3,
        units_expected=5,
        last_seen_in_index_at=None,
        index_checked_at=datetime.now(UTC),
    )
    model = HarvestStatusResponse.model_validate(source)
    assert model.harvest_status == "partial"
    assert HarvestStatus.PARTIAL == "partial"
