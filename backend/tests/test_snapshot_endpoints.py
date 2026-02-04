"""Tests for snapshot statistics API endpoints.

Tests the HTTP contract layer: correct service wiring, response models,
status codes, and error handling. Service logic is tested separately
in tests/services/test_snapshot_service.py.
"""

from datetime import datetime
from unittest.mock import MagicMock, patch

import pytest
from fastapi import HTTPException

from app.api.v1.endpoints.snapshots import (
    _no_cache_headers,
    get_biological_units_timeline,
    get_dataset_statistics,
    get_growth_timeline,
    get_multi_provider_biological_units_timeline,
    get_overview,
    get_provider_biological_units_timeline,
    get_provider_datasets_timeline,
    get_provider_list_stats,
    get_provider_statistics,
    get_quality_metrics,
    get_recent_dataset_activity,
    get_registry_health,
    trigger_snapshot_collection,
)

# ---------------------------------------------------------------------------
# Helper: _no_cache_headers
# ---------------------------------------------------------------------------


class TestNoCacheHeaders:
    """Tests for the _no_cache_headers helper."""

    def test_sets_cache_control_headers(self):
        """Test that no-cache headers are set on the response."""
        mock_response = MagicMock()
        mock_response.headers = {}
        _no_cache_headers(mock_response)

        assert mock_response.headers["Cache-Control"] == "no-cache, no-store, must-revalidate"
        assert mock_response.headers["Pragma"] == "no-cache"
        assert mock_response.headers["Expires"] == "0"

    def test_does_not_crash_when_response_is_none(self):
        """Test that passing None does not raise an error."""
        _no_cache_headers(None)  # Should not raise


# ---------------------------------------------------------------------------
# Public Endpoints
# ---------------------------------------------------------------------------


class TestGetOverview:
    """Tests for GET /overview endpoint."""

    @pytest.mark.asyncio
    @patch("app.api.v1.endpoints.snapshots.SnapshotService")
    async def test_returns_overview_stats(self, MockServiceClass):
        """Test happy path returns OverviewStats model with correct data."""
        mock_service = MagicMock()
        MockServiceClass.return_value = mock_service
        mock_service.get_overview_stats.return_value = {
            "total_datasets": 10,
            "total_providers": 5,
            "total_datacenters": 2,
            "total_xml_archives": 20,
            "validation_success_rate": 85.0,
            "last_updated": datetime(2024, 6, 1),
        }

        mock_db = MagicMock()
        mock_user = MagicMock()
        mock_user.is_global_admin = False

        result = await get_overview(db=mock_db, current_user=mock_user)

        assert result.total_datasets == 10
        assert result.total_providers == 5
        MockServiceClass.assert_called_once_with(mock_db)

    @pytest.mark.asyncio
    @patch("app.api.v1.endpoints.snapshots.SnapshotService")
    async def test_service_error_returns_500(self, MockServiceClass):
        """Test that a service exception produces HTTP 500."""
        mock_service = MagicMock()
        MockServiceClass.return_value = mock_service
        mock_service.get_overview_stats.side_effect = RuntimeError("DB down")

        with pytest.raises(HTTPException) as exc_info:
            await get_overview(db=MagicMock(), current_user=None)

        assert exc_info.value.status_code == 500

    @pytest.mark.asyncio
    @patch("app.api.v1.endpoints.snapshots.SnapshotService")
    async def test_works_with_none_response(self, MockServiceClass):
        """Test endpoint works when response parameter is None (no crash)."""
        mock_service = MagicMock()
        MockServiceClass.return_value = mock_service
        mock_service.get_overview_stats.return_value = {
            "total_datasets": 0,
            "total_providers": 0,
            "total_datacenters": 0,
            "total_xml_archives": 0,
            "validation_success_rate": None,
            "last_updated": datetime(2024, 1, 1),
        }

        result = await get_overview(db=MagicMock(), current_user=None, response=None)
        assert result.total_datasets == 0


class TestGetQualityMetrics:
    """Tests for GET /quality endpoint."""

    @pytest.mark.asyncio
    @patch("app.api.v1.endpoints.snapshots.SnapshotService")
    async def test_returns_quality_metrics(self, MockServiceClass):
        """Test happy path returns QualityMetrics model."""
        mock_service = MagicMock()
        MockServiceClass.return_value = mock_service
        mock_service.get_quality_metrics.return_value = {
            "total_validations": 100,
            "successful_validations": 80,
            "failed_validations": 20,
            "success_rate": 80.0,
            "abcd_compliance_rate": None,
            "average_processing_time": 1.5,
        }

        result = await get_quality_metrics(db=MagicMock(), current_user=None, days=30)

        assert result.total_validations == 100
        assert result.success_rate == 80.0

    @pytest.mark.asyncio
    @patch("app.api.v1.endpoints.snapshots.SnapshotService")
    async def test_service_error_returns_500(self, MockServiceClass):
        """Test that a service exception produces HTTP 500."""
        mock_service = MagicMock()
        MockServiceClass.return_value = mock_service
        mock_service.get_quality_metrics.side_effect = RuntimeError("fail")

        with pytest.raises(HTTPException) as exc_info:
            await get_quality_metrics(db=MagicMock(), current_user=None, days=30)

        assert exc_info.value.status_code == 500


class TestGetGrowthTimeline:
    """Tests for GET /timeline endpoint."""

    @pytest.mark.asyncio
    @patch("app.api.v1.endpoints.snapshots.SnapshotService")
    async def test_returns_growth_metrics(self, MockServiceClass):
        """Test happy path returns GrowthMetrics with timelines."""
        mock_service = MagicMock()
        MockServiceClass.return_value = mock_service
        mock_service.get_growth_metrics.return_value = {
            "datasets_timeline": [],
            "providers_timeline": [],
            "validation_timeline": [],
        }

        result = await get_growth_timeline(
            db=MagicMock(), current_user=None, period="monthly", months=12
        )

        assert result.datasets_timeline == []
        assert result.providers_timeline == []
        assert result.validation_timeline == []

    @pytest.mark.asyncio
    @patch("app.api.v1.endpoints.snapshots.SnapshotService")
    async def test_service_error_returns_500(self, MockServiceClass):
        """Test that a service exception produces HTTP 500."""
        mock_service = MagicMock()
        MockServiceClass.return_value = mock_service
        mock_service.get_growth_metrics.side_effect = RuntimeError("fail")

        with pytest.raises(HTTPException) as exc_info:
            await get_growth_timeline(
                db=MagicMock(), current_user=None, period="monthly", months=12
            )

        assert exc_info.value.status_code == 500


class TestGetProviderListStats:
    """Tests for GET /providers endpoint."""

    @pytest.mark.asyncio
    @patch("app.api.v1.endpoints.snapshots.SnapshotService")
    async def test_returns_provider_list(self, MockServiceClass):
        """Test happy path returns provider list dict."""
        mock_service = MagicMock()
        MockServiceClass.return_value = mock_service
        mock_service.get_provider_list_stats.return_value = {
            "providers": [],
            "total_count": 0,
            "datacenters": [],
        }

        result = await get_provider_list_stats(db=MagicMock(), current_user=None, limit=20)

        assert result["total_count"] == 0

    @pytest.mark.asyncio
    @patch("app.api.v1.endpoints.snapshots.SnapshotService")
    async def test_service_error_returns_500(self, MockServiceClass):
        """Test that a service exception produces HTTP 500."""
        mock_service = MagicMock()
        MockServiceClass.return_value = mock_service
        mock_service.get_provider_list_stats.side_effect = RuntimeError("fail")

        with pytest.raises(HTTPException) as exc_info:
            await get_provider_list_stats(db=MagicMock(), current_user=None, limit=20)

        assert exc_info.value.status_code == 500


class TestGetRecentDatasetActivity:
    """Tests for GET /datasets/recent endpoint."""

    @pytest.mark.asyncio
    @patch("app.api.v1.endpoints.snapshots.SnapshotService")
    async def test_returns_recent_activity(self, MockServiceClass):
        """Test happy path returns activity dict."""
        mock_service = MagicMock()
        MockServiceClass.return_value = mock_service
        mock_service.get_recent_activity.return_value = {
            "recent_datasets": [],
            "total_new_datasets": 0,
        }

        result = await get_recent_dataset_activity(
            db=MagicMock(), current_user=None, limit=10, days=30
        )

        assert result["total_new_datasets"] == 0

    @pytest.mark.asyncio
    @patch("app.api.v1.endpoints.snapshots.SnapshotService")
    async def test_service_error_returns_500(self, MockServiceClass):
        """Test that a service exception produces HTTP 500."""
        mock_service = MagicMock()
        MockServiceClass.return_value = mock_service
        mock_service.get_recent_activity.side_effect = RuntimeError("fail")

        with pytest.raises(HTTPException) as exc_info:
            await get_recent_dataset_activity(
                db=MagicMock(), current_user=None, limit=10, days=30
            )

        assert exc_info.value.status_code == 500


class TestGetRegistryHealth:
    """Tests for GET /health endpoint."""

    @pytest.mark.asyncio
    @patch("app.api.v1.endpoints.snapshots.SnapshotService")
    async def test_returns_health_status(self, MockServiceClass):
        """Test happy path returns health status dict."""
        mock_service = MagicMock()
        MockServiceClass.return_value = mock_service
        mock_service.get_health_status.return_value = {
            "health_score": 100,
            "total_datasets": 5,
            "total_archives": 10,
            "recent_validations": 3,
            "status": "healthy",
        }

        result = await get_registry_health(db=MagicMock(), current_user=None)

        assert result["status"] == "healthy"
        assert result["health_score"] == 100

    @pytest.mark.asyncio
    @patch("app.api.v1.endpoints.snapshots.SnapshotService")
    async def test_service_error_returns_500(self, MockServiceClass):
        """Test that a service exception produces HTTP 500."""
        mock_service = MagicMock()
        MockServiceClass.return_value = mock_service
        mock_service.get_health_status.side_effect = RuntimeError("fail")

        with pytest.raises(HTTPException) as exc_info:
            await get_registry_health(db=MagicMock(), current_user=None)

        assert exc_info.value.status_code == 500


# ---------------------------------------------------------------------------
# Authenticated Endpoints
# ---------------------------------------------------------------------------


class TestGetProviderStatistics:
    """Tests for GET /providers/{provider_id} endpoint."""

    @pytest.mark.asyncio
    @patch("app.api.v1.endpoints.snapshots.SnapshotService")
    async def test_returns_provider_stats(self, MockServiceClass):
        """Test happy path returns ProviderStats model."""
        mock_service = MagicMock()
        MockServiceClass.return_value = mock_service
        mock_service.get_provider_statistics.return_value = {
            "provider_id": 1,
            "provider_name": "Test Provider",
            "dataset_count": 5,
            "xml_archive_count": 10,
            "validation_success_rate": 90.0,
            "last_activity": datetime(2024, 6, 1),
            "activity_score": None,
        }

        result = await get_provider_statistics(
            provider_id=1, db=MagicMock(), current_user=MagicMock()
        )

        assert result.provider_id == 1
        assert result.provider_name == "Test Provider"

    @pytest.mark.asyncio
    @patch("app.api.v1.endpoints.snapshots.SnapshotService")
    async def test_provider_not_found_returns_404(self, MockServiceClass):
        """Test that None return from service produces 404, not 500."""
        mock_service = MagicMock()
        MockServiceClass.return_value = mock_service
        mock_service.get_provider_statistics.return_value = None

        with pytest.raises(HTTPException) as exc_info:
            await get_provider_statistics(
                provider_id=999, db=MagicMock(), current_user=MagicMock()
            )

        assert exc_info.value.status_code == 404

    @pytest.mark.asyncio
    @patch("app.api.v1.endpoints.snapshots.SnapshotService")
    async def test_service_error_returns_500(self, MockServiceClass):
        """Test that a generic exception produces 500."""
        mock_service = MagicMock()
        MockServiceClass.return_value = mock_service
        mock_service.get_provider_statistics.side_effect = RuntimeError("DB error")

        with pytest.raises(HTTPException) as exc_info:
            await get_provider_statistics(
                provider_id=1, db=MagicMock(), current_user=MagicMock()
            )

        assert exc_info.value.status_code == 500


class TestGetDatasetStatistics:
    """Tests for GET /datasets/{dataset_id} endpoint."""

    @pytest.mark.asyncio
    @patch("app.api.v1.endpoints.snapshots.SnapshotService")
    async def test_returns_dataset_stats(self, MockServiceClass):
        """Test happy path returns DatasetStats model."""
        mock_service = MagicMock()
        MockServiceClass.return_value = mock_service
        mock_service.get_dataset_statistics.return_value = {
            "dataset_id": 1,
            "dataset_title": "Test Dataset",
            "provider_id": 1,
            "unit_count": 42,
            "last_modified": datetime(2024, 6, 1),
            "validation_status": "completed",
            "is_valid": True,
        }

        result = await get_dataset_statistics(
            dataset_id=1, db=MagicMock(), current_user=MagicMock()
        )

        assert result.dataset_id == 1
        assert result.unit_count == 42

    @pytest.mark.asyncio
    @patch("app.api.v1.endpoints.snapshots.SnapshotService")
    async def test_dataset_not_found_returns_404(self, MockServiceClass):
        """Test that None return from service produces 404, not 500."""
        mock_service = MagicMock()
        MockServiceClass.return_value = mock_service
        mock_service.get_dataset_statistics.return_value = None

        with pytest.raises(HTTPException) as exc_info:
            await get_dataset_statistics(
                dataset_id=999, db=MagicMock(), current_user=MagicMock()
            )

        assert exc_info.value.status_code == 404

    @pytest.mark.asyncio
    @patch("app.api.v1.endpoints.snapshots.SnapshotService")
    async def test_service_error_returns_500(self, MockServiceClass):
        """Test that a generic exception produces 500."""
        mock_service = MagicMock()
        MockServiceClass.return_value = mock_service
        mock_service.get_dataset_statistics.side_effect = RuntimeError("fail")

        with pytest.raises(HTTPException) as exc_info:
            await get_dataset_statistics(
                dataset_id=1, db=MagicMock(), current_user=MagicMock()
            )

        assert exc_info.value.status_code == 500


class TestGetProviderDatasetsTimeline:
    """Tests for GET /providers/{provider_id}/datasets-timeline endpoint."""

    @pytest.mark.asyncio
    @patch("app.api.v1.endpoints.snapshots.SnapshotService")
    async def test_returns_timeline_response(self, MockServiceClass):
        """Test happy path returns TimeSeriesResponse model."""
        mock_service = MagicMock()
        MockServiceClass.return_value = mock_service
        mock_service.get_provider_datasets_timeline.return_value = []

        result = await get_provider_datasets_timeline(
            provider_id=1, db=MagicMock(), current_user=MagicMock()
        )

        assert result.metric_type == "provider_dataset_count"
        assert result.entity_type == "provider"
        assert result.entity_id == 1
        assert result.total_points == 0

    @pytest.mark.asyncio
    @patch("app.api.v1.endpoints.snapshots.SnapshotService")
    async def test_service_error_returns_500(self, MockServiceClass):
        """Test that a service exception produces HTTP 500."""
        mock_service = MagicMock()
        MockServiceClass.return_value = mock_service
        mock_service.get_provider_datasets_timeline.side_effect = RuntimeError("fail")

        with pytest.raises(HTTPException) as exc_info:
            await get_provider_datasets_timeline(
                provider_id=1, db=MagicMock(), current_user=MagicMock()
            )

        assert exc_info.value.status_code == 500


class TestGetProviderBiologicalUnitsTimeline:
    """Tests for GET /providers/{provider_id}/biological-units-timeline endpoint."""

    @pytest.mark.asyncio
    @patch("app.api.v1.endpoints.snapshots.SnapshotService")
    async def test_returns_timeline_response(self, MockServiceClass):
        """Test happy path returns TimeSeriesResponse model."""
        mock_service = MagicMock()
        MockServiceClass.return_value = mock_service
        mock_service.get_provider_biological_units_timeline.return_value = []

        result = await get_provider_biological_units_timeline(
            provider_id=1, db=MagicMock(), current_user=MagicMock()
        )

        assert result.metric_type == "provider_biological_units"
        assert result.entity_type == "provider"
        assert result.entity_id == 1

    @pytest.mark.asyncio
    @patch("app.api.v1.endpoints.snapshots.SnapshotService")
    async def test_service_error_returns_500(self, MockServiceClass):
        """Test that a service exception produces HTTP 500."""
        mock_service = MagicMock()
        MockServiceClass.return_value = mock_service
        mock_service.get_provider_biological_units_timeline.side_effect = RuntimeError("fail")

        with pytest.raises(HTTPException) as exc_info:
            await get_provider_biological_units_timeline(
                provider_id=1, db=MagicMock(), current_user=MagicMock()
            )

        assert exc_info.value.status_code == 500


class TestGetBiologicalUnitsTimeline:
    """Tests for GET /biological-units-timeline endpoint."""

    @pytest.mark.asyncio
    @patch("app.api.v1.endpoints.snapshots.SnapshotService")
    async def test_returns_system_timeline(self, MockServiceClass):
        """Test happy path returns system-wide TimeSeriesResponse."""
        mock_service = MagicMock()
        MockServiceClass.return_value = mock_service
        mock_service.get_biological_units_timeline.return_value = []

        result = await get_biological_units_timeline(
            db=MagicMock(), current_user=MagicMock()
        )

        assert result.entity_type == "system"
        assert result.entity_id is None
        assert result.total_points == 0

    @pytest.mark.asyncio
    @patch("app.api.v1.endpoints.snapshots.SnapshotService")
    async def test_service_error_returns_500(self, MockServiceClass):
        """Test that a service exception produces HTTP 500."""
        mock_service = MagicMock()
        MockServiceClass.return_value = mock_service
        mock_service.get_biological_units_timeline.side_effect = RuntimeError("fail")

        with pytest.raises(HTTPException) as exc_info:
            await get_biological_units_timeline(
                db=MagicMock(), current_user=MagicMock()
            )

        assert exc_info.value.status_code == 500


class TestGetMultiProviderBiologicalUnitsTimeline:
    """Tests for GET /multi-provider-biological-units endpoint."""

    @pytest.mark.asyncio
    @patch("app.api.v1.endpoints.snapshots.SnapshotService")
    async def test_returns_multi_provider_data(self, MockServiceClass):
        """Test happy path returns multi-provider dict."""
        mock_service = MagicMock()
        MockServiceClass.return_value = mock_service
        mock_service.get_multi_provider_timeline.return_value = {
            "metric_type": "provider_biological_units",
            "data_points": [],
            "total_points": 0,
            "providers": [],
            "total_providers": 0,
        }

        result = await get_multi_provider_biological_units_timeline(
            db=MagicMock(), current_user=MagicMock()
        )

        assert result["total_points"] == 0

    @pytest.mark.asyncio
    @patch("app.api.v1.endpoints.snapshots.SnapshotService")
    async def test_service_error_returns_500(self, MockServiceClass):
        """Test that a service exception produces HTTP 500."""
        mock_service = MagicMock()
        MockServiceClass.return_value = mock_service
        mock_service.get_multi_provider_timeline.side_effect = RuntimeError("fail")

        with pytest.raises(HTTPException) as exc_info:
            await get_multi_provider_biological_units_timeline(
                db=MagicMock(), current_user=MagicMock()
            )

        assert exc_info.value.status_code == 500


# ---------------------------------------------------------------------------
# Admin Endpoints
# ---------------------------------------------------------------------------


class TestTriggerSnapshotCollection:
    """Tests for POST /collect endpoint."""

    @pytest.mark.asyncio
    async def test_returns_queued_message(self):
        """Test happy path returns queued status message."""
        mock_background = MagicMock()

        result = await trigger_snapshot_collection(
            background_tasks=mock_background, current_user=MagicMock()
        )

        assert result["status"] == "queued"
        mock_background.add_task.assert_called_once()

    @pytest.mark.asyncio
    async def test_background_task_error_returns_500(self):
        """Test that an error adding background task produces 500."""
        mock_background = MagicMock()
        mock_background.add_task.side_effect = RuntimeError("Celery down")

        with pytest.raises(HTTPException) as exc_info:
            await trigger_snapshot_collection(
                background_tasks=mock_background, current_user=MagicMock()
            )

        assert exc_info.value.status_code == 500
