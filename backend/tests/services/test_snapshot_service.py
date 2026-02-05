"""
Tests for SnapshotService.

Tests all statistics queries using real PostgreSQL via testcontainers.
Covers overview stats, unit counts, timelines, provider/dataset stats,
health status, and growth metrics.
"""

from datetime import date, datetime, timedelta

import pytest

from app.core.utils import utc_now
from app.models.archive_snapshot import ArchiveSnapshotModel
from app.models.dataset import DatasetModel, XmlArchiveModel
from app.models.provider import DataProviderModel
from app.models.validation import ValidationJobModel
from app.services.snapshot_service import SnapshotService


@pytest.fixture
def snapshot_service(sync_db_session):
    """Create SnapshotService instance with sync test database session."""
    return SnapshotService(sync_db_session)


@pytest.fixture
def provider(sync_db_session):
    """Create a test data provider."""
    p = DataProviderModel(
        name="Test Provider",
        shortName="TP",
        datacenter="PANGAEA",
        isDataCenter=True,
    )
    sync_db_session.add(p)
    sync_db_session.flush()
    return p


@pytest.fixture
def second_provider(sync_db_session):
    """Create a second test data provider."""
    p = DataProviderModel(
        name="Second Provider",
        shortName="SP",
        datacenter="ENA",
        isDataCenter=False,
    )
    sync_db_session.add(p)
    sync_db_session.flush()
    return p


@pytest.fixture
def dataset(sync_db_session, provider):
    """Create a test dataset."""
    ds = DatasetModel(
        title="Test Dataset",
        source="test-source",
        provider_id=provider.id,
    )
    sync_db_session.add(ds)
    sync_db_session.flush()
    return ds


@pytest.fixture
def second_dataset(sync_db_session, second_provider):
    """Create a test dataset for the second provider."""
    ds = DatasetModel(
        title="Second Dataset",
        source="test-source-2",
        provider_id=second_provider.id,
    )
    sync_db_session.add(ds)
    sync_db_session.flush()
    return ds


@pytest.fixture
def archive(sync_db_session, dataset):
    """Create a test XML archive (isLatest=True)."""
    a = XmlArchiveModel(
        dataset_id=dataset.id,
        url="http://example.com/archive.xml",
        isLatest=True,
    )
    sync_db_session.add(a)
    sync_db_session.flush()
    return a


@pytest.fixture
def old_archive(sync_db_session, dataset):
    """Create a non-latest XML archive."""
    a = XmlArchiveModel(
        dataset_id=dataset.id,
        url="http://example.com/old-archive.xml",
        isLatest=False,
    )
    sync_db_session.add(a)
    sync_db_session.flush()
    return a


@pytest.fixture
def second_archive(sync_db_session, second_dataset):
    """Create a test archive for the second provider."""
    a = XmlArchiveModel(
        dataset_id=second_dataset.id,
        url="http://example.com/archive2.xml",
        isLatest=True,
    )
    sync_db_session.add(a)
    sync_db_session.flush()
    return a


# ---------------------------------------------------------------------------
# get_overview_stats
# ---------------------------------------------------------------------------


class TestGetOverviewStats:
    """Tests for get_overview_stats."""

    def test_returns_counts_with_data(self, snapshot_service, provider, dataset, archive):
        """Test overview returns correct counts when data exists."""
        result = snapshot_service.get_overview_stats()

        assert result["total_datasets"] == 1
        assert result["total_providers"] == 1
        assert result["total_xml_archives"] == 1
        assert result["total_datacenters"] == 1  # provider.isDataCenter=True
        assert "last_updated" in result

    def test_returns_zeros_on_empty_db(self, snapshot_service):
        """Test overview returns zeros when database is empty."""
        result = snapshot_service.get_overview_stats()

        assert result["total_datasets"] == 0
        assert result["total_providers"] == 0
        assert result["total_xml_archives"] == 0
        assert result["total_datacenters"] == 0

    def test_counts_only_datacenters_for_datacenter_field(
        self, snapshot_service, provider, second_provider
    ):
        """Test total_datacenters only counts providers where isDataCenter=True."""
        result = snapshot_service.get_overview_stats()

        # provider.isDataCenter=True, second_provider.isDataCenter=False
        assert result["total_providers"] == 2
        assert result["total_datacenters"] == 1

    def test_validation_success_rate_with_recent_jobs(
        self, snapshot_service, sync_db_session, archive
    ):
        """Test validation_success_rate is computed from recent completed jobs."""
        # Create 2 completed jobs: 1 successful, 1 failed
        job1 = ValidationJobModel(
            archive_id=archive.id,
            status="completed",
            task_id="task-1",
            total_files=10,
            valid_files=10,
            created_at=utc_now(),
        )
        job2 = ValidationJobModel(
            archive_id=archive.id,
            status="completed",
            task_id="task-2",
            total_files=10,
            valid_files=5,
            created_at=utc_now(),
        )
        sync_db_session.add_all([job1, job2])
        sync_db_session.flush()

        result = snapshot_service.get_overview_stats()
        assert result["validation_success_rate"] == 50.0

    def test_validation_success_rate_none_when_no_jobs(self, snapshot_service, provider, dataset):
        """Test validation_success_rate is None when no completed jobs exist."""
        result = snapshot_service.get_overview_stats()
        assert result["validation_success_rate"] is None


# ---------------------------------------------------------------------------
# get_quality_metrics
# ---------------------------------------------------------------------------


class TestGetQualityMetrics:
    """Tests for get_quality_metrics."""

    def test_empty_when_no_jobs(self, snapshot_service):
        """Test returns zero metrics when no validation jobs exist."""
        result = snapshot_service.get_quality_metrics()

        assert result["total_validations"] == 0
        assert result["successful_validations"] == 0
        assert result["failed_validations"] == 0
        assert result["success_rate"] == 0
        assert result["average_processing_time"] is None

    def test_counts_successful_and_failed(self, snapshot_service, sync_db_session, archive):
        """Test correct counting of successful vs failed validations."""
        # Successful: completed + valid_files == total_files > 0
        success = ValidationJobModel(
            archive_id=archive.id,
            status="completed",
            task_id="task-ok",
            total_files=5,
            valid_files=5,
            validation_time=1.5,
            created_at=utc_now(),
        )
        # Failed: completed but valid_files < total_files
        failed = ValidationJobModel(
            archive_id=archive.id,
            status="completed",
            task_id="task-fail",
            total_files=5,
            valid_files=2,
            validation_time=2.0,
            created_at=utc_now(),
        )
        # Pending: still running, not completed
        pending = ValidationJobModel(
            archive_id=archive.id,
            status="pending",
            task_id="task-pending",
            created_at=utc_now(),
        )
        sync_db_session.add_all([success, failed, pending])
        sync_db_session.flush()

        result = snapshot_service.get_quality_metrics(days=30)

        assert result["total_validations"] == 3  # all 3 are recent
        assert result["successful_validations"] == 1
        assert result["failed_validations"] == 2  # failed + pending both non-successful
        assert result["success_rate"] == pytest.approx(33.33, abs=0.1)
        assert result["average_processing_time"] == pytest.approx(1.75)  # (1.5+2.0)/2

    def test_excludes_jobs_outside_date_range(self, snapshot_service, sync_db_session, archive):
        """Test that jobs older than the cutoff are excluded."""
        old_job = ValidationJobModel(
            archive_id=archive.id,
            status="completed",
            task_id="task-old",
            total_files=5,
            valid_files=5,
            created_at=utc_now() - timedelta(days=60),
        )
        sync_db_session.add(old_job)
        sync_db_session.flush()

        result = snapshot_service.get_quality_metrics(days=30)
        assert result["total_validations"] == 0

    def test_zero_total_files_not_counted_as_success(
        self, snapshot_service, sync_db_session, archive
    ):
        """Test that completed jobs with total_files=0 aren't counted as successful."""
        job = ValidationJobModel(
            archive_id=archive.id,
            status="completed",
            task_id="task-empty",
            total_files=0,
            valid_files=0,
            created_at=utc_now(),
        )
        sync_db_session.add(job)
        sync_db_session.flush()

        result = snapshot_service.get_quality_metrics()
        assert result["successful_validations"] == 0


# ---------------------------------------------------------------------------
# get_dataset_unit_count
# ---------------------------------------------------------------------------


class TestGetDatasetUnitCount:
    """Tests for get_dataset_unit_count."""

    def test_returns_zero_when_no_snapshots(self, snapshot_service, dataset, archive):
        """Test returns 0 when no snapshots exist for the dataset's archives."""
        result = snapshot_service.get_dataset_unit_count(dataset.id)
        assert result == 0

    def test_returns_sum_of_latest_snapshots(self, snapshot_service, sync_db_session, dataset, archive):
        """Test returns sum of unit counts from latest snapshots per archive."""
        # Older snapshot
        snap1 = ArchiveSnapshotModel(
            archive_id=archive.id,
            recorded_at=datetime(2024, 1, 1),
            unit_count=100,
        )
        # Newer snapshot (should be used)
        snap2 = ArchiveSnapshotModel(
            archive_id=archive.id,
            recorded_at=datetime(2024, 6, 1),
            unit_count=150,
        )
        sync_db_session.add_all([snap1, snap2])
        sync_db_session.flush()

        result = snapshot_service.get_dataset_unit_count(dataset.id)
        assert result == 150  # latest snapshot only

    def test_ignores_non_latest_archives(
        self, snapshot_service, sync_db_session, dataset, archive, old_archive
    ):
        """Test that archives with isLatest=False are excluded."""
        snap_latest = ArchiveSnapshotModel(
            archive_id=archive.id,
            recorded_at=datetime(2024, 6, 1),
            unit_count=100,
        )
        snap_old = ArchiveSnapshotModel(
            archive_id=old_archive.id,
            recorded_at=datetime(2024, 6, 1),
            unit_count=999,
        )
        sync_db_session.add_all([snap_latest, snap_old])
        sync_db_session.flush()

        result = snapshot_service.get_dataset_unit_count(dataset.id)
        assert result == 100  # old_archive excluded

    def test_returns_zero_for_nonexistent_dataset(self, snapshot_service):
        """Test returns 0 for a dataset_id with no matching data."""
        result = snapshot_service.get_dataset_unit_count(99999)
        assert result == 0


# ---------------------------------------------------------------------------
# get_provider_unit_count
# ---------------------------------------------------------------------------


class TestGetProviderUnitCount:
    """Tests for get_provider_unit_count."""

    def test_aggregates_across_datasets(
        self, snapshot_service, sync_db_session, provider, dataset, archive
    ):
        """Test aggregates unit counts across all datasets for a provider."""
        snap = ArchiveSnapshotModel(
            archive_id=archive.id,
            recorded_at=datetime(2024, 6, 1),
            unit_count=200,
        )
        sync_db_session.add(snap)
        sync_db_session.flush()

        result = snapshot_service.get_provider_unit_count(provider.id)
        assert result == 200

    def test_returns_zero_for_provider_without_snapshots(self, snapshot_service, provider, dataset):
        """Test returns 0 when provider's archives have no snapshots."""
        result = snapshot_service.get_provider_unit_count(provider.id)
        assert result == 0


# ---------------------------------------------------------------------------
# get_total_biological_units
# ---------------------------------------------------------------------------


class TestGetTotalBiologicalUnits:
    """Tests for get_total_biological_units."""

    def test_returns_zero_on_empty_db(self, snapshot_service):
        """Test returns 0 when no snapshots exist."""
        result = snapshot_service.get_total_biological_units()
        assert result == 0

    def test_sums_latest_snapshots_across_all_archives(
        self, snapshot_service, sync_db_session, archive, second_archive
    ):
        """Test sums latest snapshot per archive across all archives."""
        snap1 = ArchiveSnapshotModel(
            archive_id=archive.id,
            recorded_at=datetime(2024, 6, 1),
            unit_count=100,
        )
        snap2 = ArchiveSnapshotModel(
            archive_id=second_archive.id,
            recorded_at=datetime(2024, 6, 1),
            unit_count=200,
        )
        sync_db_session.add_all([snap1, snap2])
        sync_db_session.flush()

        result = snapshot_service.get_total_biological_units()
        assert result == 300


# ---------------------------------------------------------------------------
# get_biological_units_timeline
# ---------------------------------------------------------------------------


class TestGetBiologicalUnitsTimeline:
    """Tests for get_biological_units_timeline."""

    def test_returns_empty_list_when_no_snapshots(self, snapshot_service):
        """Test returns empty list when no snapshot data exists."""
        result = snapshot_service.get_biological_units_timeline()
        assert result == []

    def test_returns_chronological_data_points(
        self, snapshot_service, sync_db_session, archive
    ):
        """Test returns timeline sorted chronologically."""
        snap1 = ArchiveSnapshotModel(
            archive_id=archive.id,
            recorded_at=datetime(2024, 1, 15),
            unit_count=100,
        )
        snap2 = ArchiveSnapshotModel(
            archive_id=archive.id,
            recorded_at=datetime(2024, 3, 15),
            unit_count=200,
        )
        sync_db_session.add_all([snap1, snap2])
        sync_db_session.flush()

        result = snapshot_service.get_biological_units_timeline()

        assert len(result) == 2
        # Should be chronological (earliest first)
        assert result[0]["date"] <= result[1]["date"]
        assert result[0]["value"] == 100.0
        assert result[1]["value"] == 200.0

    def test_respects_limit_parameter(self, snapshot_service, sync_db_session, archive):
        """Test that limit parameter restricts number of data points."""
        for i in range(5):
            snap = ArchiveSnapshotModel(
                archive_id=archive.id,
                recorded_at=datetime(2024, 1 + i, 15),
                unit_count=100 * (i + 1),
            )
            sync_db_session.add(snap)
        sync_db_session.flush()

        result = snapshot_service.get_biological_units_timeline(limit=2)
        assert len(result) == 2

    def test_filters_by_date_range(self, snapshot_service, sync_db_session, archive):
        """Test start_date and end_date filtering."""
        snap1 = ArchiveSnapshotModel(
            archive_id=archive.id,
            recorded_at=datetime(2024, 1, 15),
            unit_count=100,
        )
        snap2 = ArchiveSnapshotModel(
            archive_id=archive.id,
            recorded_at=datetime(2024, 6, 15),
            unit_count=200,
        )
        snap3 = ArchiveSnapshotModel(
            archive_id=archive.id,
            recorded_at=datetime(2024, 12, 15),
            unit_count=300,
        )
        sync_db_session.add_all([snap1, snap2, snap3])
        sync_db_session.flush()

        result = snapshot_service.get_biological_units_timeline(
            start_date=date(2024, 3, 1),
            end_date=date(2024, 9, 1),
        )

        assert len(result) == 1
        assert result[0]["value"] == 200.0


# ---------------------------------------------------------------------------
# get_provider_biological_units_timeline
# ---------------------------------------------------------------------------


class TestGetProviderBiologicalUnitsTimeline:
    """Tests for get_provider_biological_units_timeline."""

    def test_returns_empty_for_provider_without_snapshots(self, snapshot_service, provider):
        """Test returns empty list when provider has no snapshot data."""
        result = snapshot_service.get_provider_biological_units_timeline(provider.id)
        assert result == []

    def test_returns_only_data_for_requested_provider(
        self, snapshot_service, sync_db_session, provider, archive, second_archive
    ):
        """Test timeline only includes archives belonging to the requested provider."""
        snap1 = ArchiveSnapshotModel(
            archive_id=archive.id,
            recorded_at=datetime(2024, 6, 1),
            unit_count=100,
        )
        snap2 = ArchiveSnapshotModel(
            archive_id=second_archive.id,
            recorded_at=datetime(2024, 6, 1),
            unit_count=999,
        )
        sync_db_session.add_all([snap1, snap2])
        sync_db_session.flush()

        result = snapshot_service.get_provider_biological_units_timeline(provider.id)

        assert len(result) == 1
        assert result[0]["value"] == 100.0  # only provider's archive


# ---------------------------------------------------------------------------
# get_provider_datasets_timeline
# ---------------------------------------------------------------------------


class TestGetProviderDatasetsTimeline:
    """Tests for get_provider_datasets_timeline."""

    def test_returns_empty_for_provider_without_datasets(
        self, snapshot_service, provider
    ):
        """Test returns empty list when provider has no recent datasets."""
        result = snapshot_service.get_provider_datasets_timeline(provider.id, months=1)
        assert result == []

    def test_cumulative_count_monthly(
        self, snapshot_service, sync_db_session, provider
    ):
        """Test that monthly timeline returns cumulative dataset counts."""
        now = utc_now()
        ds1 = DatasetModel(
            title="DS1",
            source="src",
            provider_id=provider.id,
            created_at=now - timedelta(days=60),
            updated_at=now - timedelta(days=60),
        )
        ds2 = DatasetModel(
            title="DS2",
            source="src",
            provider_id=provider.id,
            created_at=now - timedelta(days=30),
            updated_at=now - timedelta(days=30),
        )
        sync_db_session.add_all([ds1, ds2])
        sync_db_session.flush()

        result = snapshot_service.get_provider_datasets_timeline(
            provider.id, period="monthly", months=6
        )

        # Should have cumulative growth
        assert len(result) >= 1
        # Last value should be 2 (total datasets)
        assert result[-1]["value"] >= 2

    def test_cumulative_count_daily(
        self, snapshot_service, sync_db_session, provider
    ):
        """Test that daily timeline returns cumulative dataset counts."""
        now = utc_now()
        ds1 = DatasetModel(
            title="DS1",
            source="src",
            provider_id=provider.id,
            created_at=now - timedelta(days=5),
            updated_at=now - timedelta(days=5),
        )
        ds2 = DatasetModel(
            title="DS2",
            source="src",
            provider_id=provider.id,
            created_at=now - timedelta(days=2),
            updated_at=now - timedelta(days=2),
        )
        sync_db_session.add_all([ds1, ds2])
        sync_db_session.flush()

        result = snapshot_service.get_provider_datasets_timeline(
            provider.id, period="daily", months=1
        )

        assert len(result) >= 1
        # Values should be cumulative (non-decreasing)
        for i in range(1, len(result)):
            assert result[i]["value"] >= result[i - 1]["value"]


# ---------------------------------------------------------------------------
# get_multi_provider_timeline
# ---------------------------------------------------------------------------


class TestGetMultiProviderTimeline:
    """Tests for get_multi_provider_timeline."""

    def test_returns_empty_structure_when_no_snapshots(self, snapshot_service):
        """Test returns correct empty structure when no data exists."""
        result = snapshot_service.get_multi_provider_timeline()

        assert result["metric_type"] == "provider_biological_units"
        assert result["data_points"] == []
        assert result["total_points"] == 0
        assert result["providers"] == []

    def test_returns_data_for_multiple_providers(
        self, snapshot_service, sync_db_session, archive, second_archive, provider, second_provider
    ):
        """Test returns timeline data keyed by provider name."""
        snap1 = ArchiveSnapshotModel(
            archive_id=archive.id,
            recorded_at=datetime(2024, 6, 1),
            unit_count=100,
        )
        snap2 = ArchiveSnapshotModel(
            archive_id=second_archive.id,
            recorded_at=datetime(2024, 6, 1),
            unit_count=200,
        )
        sync_db_session.add_all([snap1, snap2])
        sync_db_session.flush()

        result = snapshot_service.get_multi_provider_timeline()

        assert result["total_points"] >= 1
        assert result["total_providers"] == 2
        # Each data point should have a key for each provider
        dp = result["data_points"][0]
        assert provider.name in dp
        assert second_provider.name in dp


# ---------------------------------------------------------------------------
# get_provider_statistics
# ---------------------------------------------------------------------------


class TestGetProviderStatistics:
    """Tests for get_provider_statistics."""

    def test_returns_none_for_nonexistent_provider(self, snapshot_service):
        """Test returns None when provider doesn't exist."""
        result = snapshot_service.get_provider_statistics(99999)
        assert result is None

    def test_returns_stats_for_existing_provider(
        self, snapshot_service, provider, dataset, archive
    ):
        """Test returns correct statistics for an existing provider."""
        result = snapshot_service.get_provider_statistics(provider.id)

        assert result is not None
        assert result["provider_id"] == provider.id
        assert result["provider_name"] == "Test Provider"
        assert result["dataset_count"] == 1
        assert result["xml_archive_count"] == 1
        assert "validation_success_rate" in result
        assert "last_activity" in result

    def test_counts_archives_correctly(
        self, snapshot_service, sync_db_session, provider, dataset, archive, old_archive
    ):
        """Test archive count includes both latest and non-latest archives."""
        result = snapshot_service.get_provider_statistics(provider.id)

        # Both archives belong to this provider's dataset
        assert result["xml_archive_count"] == 2


# ---------------------------------------------------------------------------
# get_dataset_statistics
# ---------------------------------------------------------------------------


class TestGetDatasetStatistics:
    """Tests for get_dataset_statistics."""

    def test_returns_none_for_nonexistent_dataset(self, snapshot_service):
        """Test returns None when dataset doesn't exist."""
        result = snapshot_service.get_dataset_statistics(99999)
        assert result is None

    def test_returns_stats_for_existing_dataset(
        self, snapshot_service, sync_db_session, dataset, archive
    ):
        """Test returns correct statistics for an existing dataset."""
        snap = ArchiveSnapshotModel(
            archive_id=archive.id,
            recorded_at=datetime(2024, 6, 1),
            unit_count=42,
        )
        sync_db_session.add(snap)
        sync_db_session.flush()

        result = snapshot_service.get_dataset_statistics(dataset.id)

        assert result is not None
        assert result["dataset_id"] == dataset.id
        assert result["dataset_title"] == "Test Dataset"
        assert result["unit_count"] == 42
        assert result["validation_status"] is None  # no validation jobs

    def test_includes_validation_status(
        self, snapshot_service, sync_db_session, dataset, archive
    ):
        """Test that validation status is populated from latest validation job."""
        job = ValidationJobModel(
            archive_id=archive.id,
            status="completed",
            task_id="task-1",
            total_files=10,
            valid_files=10,
            created_at=utc_now(),
        )
        sync_db_session.add(job)
        sync_db_session.flush()

        result = snapshot_service.get_dataset_statistics(dataset.id)

        assert result["validation_status"] == "completed"
        assert result["is_valid"] is True

    def test_is_valid_false_when_some_files_invalid(
        self, snapshot_service, sync_db_session, dataset, archive
    ):
        """Test is_valid is False when valid_files < total_files."""
        job = ValidationJobModel(
            archive_id=archive.id,
            status="completed",
            task_id="task-1",
            total_files=10,
            valid_files=5,
            created_at=utc_now(),
        )
        sync_db_session.add(job)
        sync_db_session.flush()

        result = snapshot_service.get_dataset_statistics(dataset.id)

        assert result["is_valid"] is False

    def test_is_valid_none_when_not_completed(
        self, snapshot_service, sync_db_session, dataset, archive
    ):
        """Test is_valid is None when validation is still pending."""
        job = ValidationJobModel(
            archive_id=archive.id,
            status="pending",
            task_id="task-1",
            created_at=utc_now(),
        )
        sync_db_session.add(job)
        sync_db_session.flush()

        result = snapshot_service.get_dataset_statistics(dataset.id)

        assert result["validation_status"] == "pending"
        assert result["is_valid"] is None


# ---------------------------------------------------------------------------
# get_provider_list_stats
# ---------------------------------------------------------------------------


class TestGetProviderListStats:
    """Tests for get_provider_list_stats."""

    def test_returns_empty_when_no_providers(self, snapshot_service):
        """Test returns empty list when no providers exist."""
        result = snapshot_service.get_provider_list_stats()

        assert result["providers"] == []
        assert result["total_count"] == 0

    def test_returns_providers_sorted_by_units_descending(
        self, snapshot_service, sync_db_session, provider, second_provider, archive, second_archive
    ):
        """Test providers are sorted by biological units descending."""
        snap1 = ArchiveSnapshotModel(
            archive_id=archive.id,
            recorded_at=datetime(2024, 6, 1),
            unit_count=50,
        )
        snap2 = ArchiveSnapshotModel(
            archive_id=second_archive.id,
            recorded_at=datetime(2024, 6, 1),
            unit_count=200,
        )
        sync_db_session.add_all([snap1, snap2])
        sync_db_session.flush()

        result = snapshot_service.get_provider_list_stats()

        providers = result["providers"]
        assert len(providers) == 2
        # Second provider has more units, should be first
        assert providers[0]["biological_units"] >= providers[1]["biological_units"]
        assert providers[0]["provider_name"] == "Second Provider"

    def test_includes_datacenter_distribution(
        self, snapshot_service, sync_db_session, provider, second_provider, dataset, second_dataset
    ):
        """Test includes datacenter stats with dataset counts."""
        result = snapshot_service.get_provider_list_stats()

        assert "datacenters" in result
        # Both providers have datacenters and datasets
        assert len(result["datacenters"]) == 2

    def test_respects_limit_parameter(
        self, snapshot_service, sync_db_session
    ):
        """Test that limit restricts the number of providers returned."""
        # Create 3 providers
        for i in range(3):
            p = DataProviderModel(name=f"Provider {i}", shortName=f"P{i}", datacenter="DC")
            sync_db_session.add(p)
        sync_db_session.flush()

        result = snapshot_service.get_provider_list_stats(limit=2)
        assert len(result["providers"]) == 2


# ---------------------------------------------------------------------------
# get_recent_activity
# ---------------------------------------------------------------------------


class TestGetRecentActivity:
    """Tests for get_recent_activity."""

    def test_returns_empty_when_no_recent_datasets(self, snapshot_service):
        """Test returns empty list when no datasets created recently."""
        result = snapshot_service.get_recent_activity()

        assert result["recent_datasets"] == []
        assert result["total_new_datasets"] == 0

    def test_returns_recent_datasets_with_details(
        self, snapshot_service, sync_db_session, provider
    ):
        """Test returns recently created datasets with correct fields."""
        ds = DatasetModel(
            title="Recent DS",
            source="src",
            provider_id=provider.id,
            created_at=utc_now(),
            updated_at=utc_now(),
        )
        sync_db_session.add(ds)
        sync_db_session.flush()

        result = snapshot_service.get_recent_activity(days=30)

        assert result["total_new_datasets"] == 1
        assert result["recent_datasets"][0]["title"] == "Recent DS"

    def test_excludes_datasets_outside_date_range(
        self, snapshot_service, sync_db_session, provider
    ):
        """Test datasets older than cutoff are excluded."""
        old_ds = DatasetModel(
            title="Old DS",
            source="src",
            provider_id=provider.id,
            created_at=utc_now() - timedelta(days=60),
            updated_at=utc_now() - timedelta(days=60),
        )
        sync_db_session.add(old_ds)
        sync_db_session.flush()

        result = snapshot_service.get_recent_activity(days=30)
        assert result["total_new_datasets"] == 0

    def test_respects_limit_parameter(
        self, snapshot_service, sync_db_session, provider
    ):
        """Test that limit restricts the number of datasets returned."""
        now = utc_now()
        for i in range(5):
            ds = DatasetModel(
                title=f"DS {i}",
                source="src",
                provider_id=provider.id,
                created_at=now - timedelta(days=i),
                updated_at=now - timedelta(days=i),
            )
            sync_db_session.add(ds)
        sync_db_session.flush()

        result = snapshot_service.get_recent_activity(limit=2, days=30)
        assert result["total_new_datasets"] == 2


# ---------------------------------------------------------------------------
# get_health_status
# ---------------------------------------------------------------------------


class TestGetHealthStatus:
    """Tests for get_health_status."""

    def test_healthy_when_data_exists(
        self, snapshot_service, sync_db_session, dataset, archive
    ):
        """Test health status is healthy when datasets, archives, and validations exist."""
        job = ValidationJobModel(
            archive_id=archive.id,
            status="completed",
            task_id="task-1",
            created_at=utc_now(),
        )
        sync_db_session.add(job)
        sync_db_session.flush()

        result = snapshot_service.get_health_status()

        assert result["status"] == "healthy"
        assert result["health_score"] == 100

    def test_degraded_when_empty_db(self, snapshot_service):
        """Test health status is degraded when database is empty."""
        result = snapshot_service.get_health_status()

        assert result["status"] == "degraded"
        # No datasets (-30), no archives (-30), no validations (-20)
        assert result["health_score"] == 20

    def test_degraded_when_no_recent_validations(
        self, snapshot_service, dataset, archive
    ):
        """Test health degrades when no recent validations exist."""
        result = snapshot_service.get_health_status()

        assert result["health_score"] == 80  # -20 for no recent validations

    def test_returns_correct_counts(
        self, snapshot_service, sync_db_session, dataset, archive
    ):
        """Test health status includes correct count metrics."""
        result = snapshot_service.get_health_status()

        assert result["total_datasets"] == 1
        assert result["total_archives"] == 1
        assert result["recent_validations"] == 0


# ---------------------------------------------------------------------------
# get_growth_metrics
# ---------------------------------------------------------------------------


class TestGetGrowthMetrics:
    """Tests for get_growth_metrics."""

    def test_returns_empty_timelines_on_empty_db(self, snapshot_service):
        """Test returns empty timelines when no data exists."""
        result = snapshot_service.get_growth_metrics()

        assert result["datasets_timeline"] == []
        assert result["providers_timeline"] == []
        assert result["validation_timeline"] == []

    def test_monthly_cumulative_datasets(
        self, snapshot_service, sync_db_session, provider
    ):
        """Test monthly dataset timeline shows cumulative growth."""
        now = utc_now()
        ds1 = DatasetModel(
            title="DS1",
            source="src",
            provider_id=provider.id,
            created_at=now - timedelta(days=60),
            updated_at=now - timedelta(days=60),
        )
        ds2 = DatasetModel(
            title="DS2",
            source="src",
            provider_id=provider.id,
            created_at=now - timedelta(days=30),
            updated_at=now - timedelta(days=30),
        )
        sync_db_session.add_all([ds1, ds2])
        sync_db_session.flush()

        result = snapshot_service.get_growth_metrics(period="monthly", months=6)

        tl = result["datasets_timeline"]
        assert len(tl) >= 1
        # Values should be cumulative (non-decreasing)
        for i in range(1, len(tl)):
            assert tl[i]["value"] >= tl[i - 1]["value"]

    def test_daily_cumulative_datasets(
        self, snapshot_service, sync_db_session, provider
    ):
        """Test daily dataset timeline shows cumulative growth."""
        now = utc_now()
        ds1 = DatasetModel(
            title="DS1",
            source="src",
            provider_id=provider.id,
            created_at=now - timedelta(days=5),
            updated_at=now - timedelta(days=5),
        )
        ds2 = DatasetModel(
            title="DS2",
            source="src",
            provider_id=provider.id,
            created_at=now - timedelta(days=2),
            updated_at=now - timedelta(days=2),
        )
        sync_db_session.add_all([ds1, ds2])
        sync_db_session.flush()

        result = snapshot_service.get_growth_metrics(period="daily", months=1)

        tl = result["datasets_timeline"]
        assert len(tl) >= 1
        for i in range(1, len(tl)):
            assert tl[i]["value"] >= tl[i - 1]["value"]

    def test_validation_timeline_not_cumulative(
        self, snapshot_service, sync_db_session, archive
    ):
        """Test validation timeline shows per-period counts, not cumulative."""
        now = utc_now()
        # Create jobs on different days
        j1 = ValidationJobModel(
            archive_id=archive.id,
            status="completed",
            task_id="task-1",
            created_at=now - timedelta(days=5),
        )
        j2 = ValidationJobModel(
            archive_id=archive.id,
            status="completed",
            task_id="task-2",
            created_at=now - timedelta(days=5),
        )
        j3 = ValidationJobModel(
            archive_id=archive.id,
            status="completed",
            task_id="task-3",
            created_at=now - timedelta(days=2),
        )
        sync_db_session.add_all([j1, j2, j3])
        sync_db_session.flush()

        result = snapshot_service.get_growth_metrics(period="daily", months=1)

        tl = result["validation_timeline"]
        assert len(tl) >= 1
        # Should have per-day counts (2 on one day, 1 on another)
        values = [p["value"] for p in tl]
        assert 2 in values
        assert 1 in values
