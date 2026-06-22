"""Tests for the harvest-status API endpoint.

Tests the HTTP-contract layer only: correct service wiring (db + es_gateway +
the N unit-count provider), the response model pass-through, and the int-typed
path-parameter annotation that makes FastAPI deliver the 422 for a non-int id.
All harvest-state / URN / M-of-N logic is owned by ``HarvestStatusService`` and
is tested in ``tests/test_harvest_status_service.py`` — this file adds none of it.

House idiom (mirrors ``tests/test_validator_endpoints.py``): the service is
patched at its *import site in the endpoint module* and the endpoint coroutine is
called directly with ``current_user=MagicMock()`` and a ``db=MagicMock()``. No
``TestClient`` / ``AsyncClient`` / ``dependency_overrides`` is introduced — the
house has none, and the 422-on-non-int-id contract is asserted at the signature
level (the ``dataset_id: int`` annotation), which FastAPI converts into a routed
422. Introducing a live client to chase that 422 is forbidden by the run's
AUTH-DEP TRAP directive.
"""

import inspect
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.api.v1.endpoints.harvest_status import get_dataset_harvest_status
from app.schemas.harvest_status import HarvestStatus, HarvestStatusResponse


def _make_response(**overrides) -> HarvestStatusResponse:
    """Build a real ``HarvestStatusResponse`` so equality assertions are meaningful.

    Returning a bare ``MagicMock`` would make every ``result.<field>`` a truthy
    mock and the equality assertions vacuous — the single most likely tautology
    trap in this ticket — so the stub is always a real model instance.
    """
    fields = {
        "dataset_id": 7,
        "is_harvest_ready": True,
        "harvest_status": HarvestStatus.IN_INDEX,
        "units_in_index": 5,
        "units_expected": 5,
        "last_seen_in_index_at": datetime(2026, 1, 1, tzinfo=UTC),
        "index_checked_at": datetime(2026, 1, 2, tzinfo=UTC),
    }
    fields.update(overrides)
    return HarvestStatusResponse(**fields)


class TestGetDatasetHarvestStatus:
    """Tests for GET /datasets/{dataset_id}/harvest-status endpoint."""

    @pytest.mark.asyncio
    @patch("app.api.v1.endpoints.harvest_status.EsGateway")
    @patch("app.api.v1.endpoints.harvest_status.SnapshotService")
    @patch("app.api.v1.endpoints.harvest_status.HarvestStatusService")
    async def test_returns_response_model_and_delegates(
        self, MockServiceClass, MockSnapshotService, MockEsGateway
    ):
        """Happy path: returns the service's HarvestStatusResponse and delegates by id."""
        mock_service = MagicMock()
        MockServiceClass.return_value = mock_service
        mock_service.get_harvest_status = AsyncMock(return_value=_make_response())

        # N provider source: SnapshotService(sync_db).get_dataset_unit_count(...) -> 5
        MockSnapshotService.return_value.get_dataset_unit_count.return_value = 5

        result = await get_dataset_harvest_status(
            dataset_id=7,
            current_user=MagicMock(),
            db=MagicMock(),
            sync_db=MagicMock(),
        )

        # Assert concrete values (not `is not None`) — would catch a wrong id,
        # a dropped await, or returning the mock class instead of the result.
        assert result.dataset_id == 7
        assert result.harvest_status == HarvestStatus.IN_INDEX
        assert result.units_in_index == 5
        assert result.units_expected == 5
        assert result.is_harvest_ready is True
        mock_service.get_harvest_status.assert_awaited_once_with(7)

    @pytest.mark.asyncio
    @patch("app.api.v1.endpoints.harvest_status.EsGateway")
    @patch("app.api.v1.endpoints.harvest_status.SnapshotService")
    @patch("app.api.v1.endpoints.harvest_status.HarvestStatusService")
    async def test_service_constructed_with_db_gateway_and_n_provider(
        self, MockServiceClass, MockSnapshotService, MockEsGateway
    ):
        """Service receives the async session, an EsGateway, and a callable N-provider.

        Mirrors ``ValidationService(db)`` but the frozen T-7.1 ctor is
        ``HarvestStatusService(db, es_gateway, unit_count_provider)`` — so this
        test pins all three positional args. The N-provider must be a callable
        that, when invoked with the dataset id, yields the snapshot unit count
        (the await/blocking fetch happens in the endpoint, never in the sync
        callable — that avoids the MissingGreenlet trap).
        """
        mock_service = MagicMock()
        MockServiceClass.return_value = mock_service
        mock_service.get_harvest_status = AsyncMock(return_value=_make_response())

        MockSnapshotService.return_value.get_dataset_unit_count.return_value = 5
        gateway_instance = MockEsGateway.return_value

        db = MagicMock()
        sync_db = MagicMock()
        await get_dataset_harvest_status(
            dataset_id=7, current_user=MagicMock(), db=db, sync_db=sync_db
        )

        # Frozen T-7.1 positional ctor: (db, es_gateway, unit_count_provider).
        ctor_args, _ctor_kwargs = MockServiceClass.call_args
        assert ctor_args[0] is db
        # The injected gateway is the default-settings EsGateway instance.
        assert ctor_args[1] is gateway_instance
        # The N-provider is a callable returning the snapshot unit count (5),
        # regardless of which dataset id the service passes it.
        provider = ctor_args[2]
        assert callable(provider)
        assert provider(7) == 5
        # The blocking unit-count query was done against the SYNC session, not the
        # async one — wiring N async-safely.
        MockSnapshotService.assert_called_once_with(sync_db)
        MockSnapshotService.return_value.get_dataset_unit_count.assert_called_once_with(7)
        # Delegated to the service exactly once with the path id.
        mock_service.get_harvest_status.assert_awaited_once_with(7)

    @pytest.mark.asyncio
    @patch("app.api.v1.endpoints.harvest_status.EsGateway")
    @patch("app.api.v1.endpoints.harvest_status.SnapshotService")
    @patch("app.api.v1.endpoints.harvest_status.HarvestStatusService")
    async def test_staged_passes_through_untouched(
        self, MockServiceClass, MockSnapshotService, MockEsGateway
    ):
        """Staged result passes through verbatim — endpoint adds no short-circuit."""
        mock_service = MagicMock()
        MockServiceClass.return_value = mock_service
        mock_service.get_harvest_status = AsyncMock(
            return_value=_make_response(
                harvest_status=HarvestStatus.STAGED,
                is_harvest_ready=False,
                units_in_index=None,
                units_expected=None,
                last_seen_in_index_at=None,
            )
        )
        MockSnapshotService.return_value.get_dataset_unit_count.return_value = 0

        result = await get_dataset_harvest_status(
            dataset_id=3, current_user=MagicMock(), db=MagicMock(), sync_db=MagicMock()
        )

        assert result.harvest_status == HarvestStatus.STAGED
        assert result.is_harvest_ready is False
        assert result.units_in_index is None
        assert result.units_expected is None

    @pytest.mark.asyncio
    @patch("app.api.v1.endpoints.harvest_status.EsGateway")
    @patch("app.api.v1.endpoints.harvest_status.SnapshotService")
    @patch("app.api.v1.endpoints.harvest_status.HarvestStatusService")
    async def test_unknown_es_down_returns_200_body_not_exception(
        self, MockServiceClass, MockSnapshotService, MockEsGateway
    ):
        """ES-down maps to a normal ``unknown`` body — never a raised error."""
        mock_service = MagicMock()
        MockServiceClass.return_value = mock_service
        mock_service.get_harvest_status = AsyncMock(
            return_value=_make_response(
                harvest_status=HarvestStatus.UNKNOWN,
                units_in_index=None,
                units_expected=None,
                last_seen_in_index_at=None,
            )
        )
        MockSnapshotService.return_value.get_dataset_unit_count.return_value = 0

        result = await get_dataset_harvest_status(
            dataset_id=7, current_user=MagicMock(), db=MagicMock(), sync_db=MagicMock()
        )

        assert result.harvest_status == HarvestStatus.UNKNOWN

    def test_dataset_id_is_int_typed_for_framework_422(self):
        """422-on-non-int-id is a FRAMEWORK behavior delivered by the int annotation.

        A direct coroutine call bypasses FastAPI path coercion, so the int
        contract is asserted at the signature level: FastAPI guarantees a 422 for
        a non-int path segment from this annotation. Introducing an
        ``AsyncClient`` / ``dependency_overrides`` / ``TestClient`` to chase a
        live 422 is forbidden by the house convention (AUTH-DEP TRAP).
        """
        sig = inspect.signature(get_dataset_harvest_status)
        assert sig.parameters["dataset_id"].annotation is int

    def test_router_mounts_get_route_at_expected_path(self):
        """The v1 router exposes GET /datasets/{dataset_id}/harvest-status."""
        from app.api.v1.router import api_v1_router

        assert any(
            getattr(r, "path", None) == "/datasets/{dataset_id}/harvest-status"
            and "GET" in getattr(r, "methods", set())
            for r in api_v1_router.routes
        )
