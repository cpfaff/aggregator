"""Tests for the public POST /validation-stats batch endpoint.

HTTP-contract layer only — the latest-archive / latest-job / projection logic is
owned by ``ValidationService.get_validation_stats_for_datasets`` and tested in
``tests/services/test_validation_service.py``. This file pins the endpoint's job:
parse each inbound ``abcdDatasetIdentifier`` URN to a dataset id, batch the DB read
once, and re-key the per-dataset summaries back onto the *identifiers* the caller
sent (so the search backend can merge by the exact term it holds).

House idiom (mirrors ``tests/test_harvest_status_endpoint.py``): the service is
patched at its import site in the endpoint module and the coroutine is called
directly — no TestClient / AsyncClient / dependency_overrides. The route mounting
is asserted through the reverse-router (``url_path_for``), which is stable across
the lazy-include behaviour of the pinned FastAPI.
"""

from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.api.v1.endpoints.validation_stats import (
    ValidationStatsRequest,
    get_validation_stats,
)
from app.api.v1.endpoints.validation_stats import (
    router as validation_stats_router,
)

URN_204 = "urn:gfbio.org:abcd:1_204_375"
URN_204_UNIT = "urn:gfbio.org:abcd:1_204_375:7"  # a unit doc of the same dataset


def _dataset_summary(**overrides) -> dict:
    """A service-shaped per-dataset summary dict (what the batch method returns)."""
    base = {
        "dataset_id": 204,
        "archive_id": 375,
        "validation_status": "completed",
        "last_validated_at": datetime(2026, 6, 20, tzinfo=UTC),
        "is_valid": False,
        "quality_score": 0.86,
        "mandatory_percentage": 95.0,
        "recommended_percentage": 70.0,
        "total_files": 12,
        "valid_files": 11,
    }
    base.update(overrides)
    return base


@pytest.mark.asyncio
@patch("app.api.v1.endpoints.validation_stats.ValidationService")
async def test_returns_summary_keyed_by_identifier(MockServiceClass):
    mock_service = MagicMock()
    MockServiceClass.return_value = mock_service
    mock_service.get_validation_stats_for_datasets = AsyncMock(
        return_value={204: _dataset_summary()}
    )

    response = await get_validation_stats(
        ValidationStatsRequest(identifiers=[URN_204]), db=MagicMock()
    )

    # Re-keyed onto the identifier the caller sent, with the headline numbers.
    assert set(response.results) == {URN_204}
    summary = response.results[URN_204]
    assert summary.identifier == URN_204
    assert summary.dataset_id == 204
    assert summary.validation_status == "completed"
    assert summary.quality_score == 0.86
    assert summary.mandatory_percentage == 95.0
    assert summary.is_valid is False
    # Delegated once, with the parsed dataset id.
    mock_service.get_validation_stats_for_datasets.assert_awaited_once_with([204])


@pytest.mark.asyncio
@patch("app.api.v1.endpoints.validation_stats.ValidationService")
async def test_skips_malformed_identifiers(MockServiceClass):
    mock_service = MagicMock()
    MockServiceClass.return_value = mock_service
    mock_service.get_validation_stats_for_datasets = AsyncMock(
        return_value={204: _dataset_summary()}
    )

    response = await get_validation_stats(
        ValidationStatsRequest(identifiers=["not-a-urn", URN_204]), db=MagicMock()
    )

    # Only the well-formed id reaches the DB and only it appears in the result.
    mock_service.get_validation_stats_for_datasets.assert_awaited_once_with([204])
    assert set(response.results) == {URN_204}


@pytest.mark.asyncio
@patch("app.api.v1.endpoints.validation_stats.ValidationService")
async def test_omits_identifiers_with_no_validation_record(MockServiceClass):
    mock_service = MagicMock()
    MockServiceClass.return_value = mock_service
    # Service knows nothing about this dataset -> empty map.
    mock_service.get_validation_stats_for_datasets = AsyncMock(return_value={})

    response = await get_validation_stats(
        ValidationStatsRequest(identifiers=[URN_204]), db=MagicMock()
    )

    assert response.results == {}


@pytest.mark.asyncio
@patch("app.api.v1.endpoints.validation_stats.ValidationService")
async def test_deduplicates_dataset_ids_but_keys_every_identifier(MockServiceClass):
    mock_service = MagicMock()
    MockServiceClass.return_value = mock_service
    mock_service.get_validation_stats_for_datasets = AsyncMock(
        return_value={204: _dataset_summary()}
    )

    # A dataset URN and one of its unit URNs both resolve to dataset 204.
    response = await get_validation_stats(
        ValidationStatsRequest(identifiers=[URN_204, URN_204_UNIT]), db=MagicMock()
    )

    # The DB is queried once for the deduplicated dataset id...
    mock_service.get_validation_stats_for_datasets.assert_awaited_once_with([204])
    # ...but BOTH identifiers are present in the response, each carrying the summary.
    assert set(response.results) == {URN_204, URN_204_UNIT}
    assert response.results[URN_204_UNIT].quality_score == 0.86


@pytest.mark.asyncio
@patch("app.api.v1.endpoints.validation_stats.ValidationService")
async def test_empty_identifiers_returns_empty(MockServiceClass):
    mock_service = MagicMock()
    MockServiceClass.return_value = mock_service
    mock_service.get_validation_stats_for_datasets = AsyncMock(return_value={})

    response = await get_validation_stats(
        ValidationStatsRequest(identifiers=[]), db=MagicMock()
    )

    assert response.results == {}


def test_router_mounts_post_route_at_expected_path():
    from starlette.routing import NoMatchFound

    from app.api.v1.router import api_v1_router

    try:
        mounted_path = api_v1_router.url_path_for("get_validation_stats")
    except NoMatchFound:
        pytest.fail("POST /validation-stats is not mounted on api_v1_router")

    assert mounted_path == "/validation-stats"
    declared_methods = {
        method
        for route in validation_stats_router.routes
        for method in getattr(route, "methods", set())
    }
    assert "POST" in declared_methods
