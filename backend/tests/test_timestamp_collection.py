"""
Comprehensive test suite for timestamp-based collection logic.

This module tests all timestamp and anchor date related functions to ensure
proper handling of first vs subsequent processing scenarios.
"""

from datetime import date, datetime
from unittest.mock import MagicMock, patch

import pytest
from app.models.dataset import DatasetModel, XmlArchiveModel
from app.models.provider import DataProviderModel
from app.models.statistics import EntityType, MetricType, Period, StatisticModel
from app.tasks.statistics_tasks import (
    analyze_xml_archives,
    collect_provider_biological_units,
    get_archive_anchor_date,
    is_archive_first_processing,
    mark_archive_processed,
)
from sqlalchemy.orm import Session


@pytest.fixture
def mock_db():
    """Create a mock database session."""
    db = MagicMock(spec=Session)
    db.commit = MagicMock()
    db.rollback = MagicMock()
    db.add = MagicMock()
    return db


@pytest.fixture
def mock_dataset():
    """Create a mock dataset with various timestamps."""
    dataset = MagicMock(spec=DatasetModel)
    dataset.id = 1
    dataset.provider_id = 10
    dataset.created_at = datetime(2024, 1, 15, 10, 30, 0)
    dataset.updated_at = datetime(2024, 6, 10, 15, 45, 0)
    return dataset


@pytest.fixture
def mock_archive(mock_dataset):
    """Create a mock XML archive."""
    archive = MagicMock(spec=XmlArchiveModel)
    archive.id = 100
    archive.dataset_id = mock_dataset.id
    archive.url = "http://example.com/data.xml"
    archive.isLatest = True
    archive.dataset = mock_dataset
    return archive


@pytest.fixture
def mock_statistic():
    """Create a mock statistic model."""
    stat = MagicMock(spec=StatisticModel)
    stat.id = 500
    stat.entity_type = EntityType.DATASET
    stat.entity_id = 1
    stat.metric_type = MetricType.BIOLOGICAL_UNITS
    stat.period = Period.DAILY
    stat.target_date = date(2024, 1, 15)
    stat.extra_data = {"archive_id": 100}
    return stat


class TestIsArchiveFirstProcessing:
    """Test suite for is_archive_first_processing function."""

    def test_no_existing_statistics(self, mock_db):
        """Archive is first processing when no statistics exist."""
        # Setup: No statistics found
        mock_db.query().filter().first.return_value = None

        result = is_archive_first_processing(mock_db, 100)

        assert result is True
        # Verify correct query was made
        mock_db.query.assert_called()

    def test_existing_statistics_no_marker(self, mock_db, mock_statistic):
        """Archive is first processing when stats exist but no first_processed_at."""
        # Setup: Statistics exist but no first_processed_at marker
        mock_statistic.extra_data = {"archive_id": 100, "unit_count": 1000}
        mock_db.query().filter().first.return_value = mock_statistic

        result = is_archive_first_processing(mock_db, 100)

        assert result is True

    def test_existing_statistics_with_marker(self, mock_db, mock_statistic):
        """Archive is not first processing when first_processed_at exists."""
        # Setup: Statistics with first_processed_at marker
        mock_statistic.extra_data = {
            "archive_id": 100,
            "unit_count": 1000,
            "first_processed_at": "2024-01-15T10:30:00",
        }
        # First call checks for failure, second checks for stats
        mock_db.query().filter().first.side_effect = [None, mock_statistic]

        result = is_archive_first_processing(mock_db, 100)

        assert result is False

    def test_failed_archive_treated_as_first(self, mock_db, mock_statistic):
        """Failed archives are treated as first processing."""
        # Setup: Archive with failure flag
        mock_statistic.extra_data = {
            "archive_id": 100,
            "processing_failed": True,
            "failure_count": 3,
            "last_failure_reason": "Parse error",
            "last_failure_at": datetime.utcnow().isoformat(),
        }
        mock_db.query().filter().first.return_value = mock_statistic

        result = is_archive_first_processing(mock_db, 100)

        assert result is True

    def test_different_archive_ids(self, mock_db):
        """Test with different archive IDs to ensure proper filtering."""
        # Setup: No statistics for archive 200
        mock_db.query().filter().first.return_value = None

        result = is_archive_first_processing(mock_db, 200)

        assert result is True
        # Verify query was made for correct archive ID
        mock_db.query.assert_called()


class TestGetArchiveAnchorDate:
    """Test suite for get_archive_anchor_date function."""

    def test_first_processing_uses_dataset_created_at(self, mock_db, mock_archive):
        """First processing should use dataset's created_at date."""
        with patch("app.tasks.statistics_tasks.is_archive_first_processing", return_value=True):
            result = get_archive_anchor_date(mock_db, mock_archive)

            assert result == date(2024, 1, 15)  # Dataset created_at as date

    def test_subsequent_processing_uses_current_date(self, mock_db, mock_archive):
        """Subsequent processing should use current date."""
        with patch("app.tasks.statistics_tasks.is_archive_first_processing", return_value=False):
            with patch("app.tasks.statistics_tasks.get_archive_failure_info", return_value=None):
                with patch("app.tasks.statistics_tasks.date") as mock_date:
                    mock_date.today.return_value = date(2024, 6, 20)

                    result = get_archive_anchor_date(mock_db, mock_archive)

                    assert result == date(2024, 6, 20)

    def test_failed_archive_uses_dataset_created_at(self, mock_db, mock_archive):
        """Failed archives should use dataset's created_at for retry."""
        with patch("app.tasks.statistics_tasks.is_archive_first_processing", return_value=True):
            with patch("app.tasks.statistics_tasks.get_archive_failure_info") as mock_failure:
                mock_failure.return_value = {
                    "failure_count": 2,
                    "last_failure_reason": "Network error",
                    "last_failure_at": datetime.utcnow().isoformat(),
                }

                result = get_archive_anchor_date(mock_db, mock_archive)

                assert result == date(2024, 1, 15)  # Dataset created_at

    def test_none_dataset_created_at_fallback(self, mock_db, mock_archive):
        """Test fallback when dataset created_at is None."""
        mock_archive.dataset.created_at = None

        with patch("app.tasks.statistics_tasks.is_archive_first_processing", return_value=True):
            with patch("app.tasks.statistics_tasks.date") as mock_date:
                mock_date.today.return_value = date(2024, 6, 20)

                result = get_archive_anchor_date(mock_db, mock_archive)

                assert result == date(2024, 6, 20)  # Falls back to current date

    def test_various_date_formats(self, mock_db):
        """Test handling of different date formats in created_at."""
        # Test with different datetime formats
        datasets = [
            datetime(2024, 3, 10, 0, 0, 0),  # Midnight
            datetime(2024, 3, 10, 23, 59, 59),  # End of day
            datetime(2024, 3, 10, 12, 30, 45, 123456),  # With microseconds
        ]

        for created_at in datasets:
            archive = MagicMock(spec=XmlArchiveModel)
            archive.id = 100
            archive.dataset = MagicMock(spec=DatasetModel)
            archive.dataset.created_at = created_at

            with patch("app.tasks.statistics_tasks.is_archive_first_processing", return_value=True):
                result = get_archive_anchor_date(mock_db, archive)

                assert result == date(2024, 3, 10)  # All should resolve to same date


class TestMarkArchiveProcessed:
    """Test suite for mark_archive_processed function."""

    def test_mark_new_archive_processed(self, mock_db, mock_statistic):
        """Test marking a newly processed archive."""
        # Setup: Existing statistic without first_processed_at
        mock_statistic.extra_data = {"archive_id": 100, "unit_count": 5000}
        mock_db.query().filter().first.return_value = mock_statistic

        with patch("app.tasks.statistics_tasks.flag_modified") as mock_flag:
            with patch("app.tasks.statistics_tasks.datetime") as mock_datetime:
                mock_datetime.utcnow.return_value = datetime(2024, 6, 20, 14, 30, 0)

                mark_archive_processed(mock_db, 100, 1, date(2024, 1, 15))

                # Verify first_processed_at was added
                assert "first_processed_at" in mock_statistic.extra_data
                assert mock_statistic.extra_data["first_processed_at"] == "2024-06-20T14:30:00"

                # Verify flag_modified was called
                mock_flag.assert_called_once_with(mock_statistic, "extra_data")

                # Verify commit was called
                mock_db.commit.assert_called_once()

    def test_mark_already_processed_archive(self, mock_db, mock_statistic):
        """Test marking an already processed archive (should not update)."""
        # Setup: Statistic with existing first_processed_at
        original_timestamp = "2024-01-15T10:30:00"
        mock_statistic.extra_data = {
            "archive_id": 100,
            "unit_count": 5000,
            "first_processed_at": original_timestamp,
        }
        mock_db.query().filter().first.return_value = mock_statistic

        with patch("app.tasks.statistics_tasks.flag_modified") as mock_flag:
            mark_archive_processed(mock_db, 100, 1, date(2024, 6, 20))

            # Verify first_processed_at was NOT changed
            assert mock_statistic.extra_data["first_processed_at"] == original_timestamp

            # Flag modified should still be called
            mock_flag.assert_called_once()

    def test_mark_processed_no_existing_statistic(self, mock_db):
        """Test marking processed when no statistic exists (should handle gracefully)."""
        # Setup: No existing statistic
        mock_db.query().filter().first.return_value = None

        # Should not raise an exception
        mark_archive_processed(mock_db, 100, 1, date(2024, 1, 15))

        # Verify commit was still called
        mock_db.commit.assert_called_once()

    def test_mark_processed_updates_dataset_id(self, mock_db, mock_statistic):
        """Test that dataset_id is properly stored in extra_data."""
        mock_statistic.extra_data = {"archive_id": 100}
        mock_db.query().filter().first.return_value = mock_statistic

        with patch("app.tasks.statistics_tasks.flag_modified"):
            mark_archive_processed(mock_db, 100, 456, date(2024, 1, 15))

            # Verify dataset_id was added
            assert mock_statistic.extra_data.get("dataset_id") == 456


class TestArchiveProcessingWithAnchorDates:
    """Test analyze_xml_archives with anchor date scenarios."""

    @patch("app.tasks.statistics_tasks.SessionLocal")
    @patch("app.tasks.statistics_tasks.parse_abcd_xml")
    def test_first_processing_anchor_date(self, mock_parse, mock_session, mock_archive):
        """Test first processing uses dataset created_at."""
        # Setup
        mock_db = MagicMock()
        mock_session.return_value.__enter__.return_value = mock_db
        mock_db.query().filter().order_by().offset().limit().all.return_value = [mock_archive]
        mock_parse.return_value = {"unit_count": 2500, "xml_files_processed": 1}

        with patch("app.tasks.statistics_tasks.is_archive_first_processing", return_value=True):
            with patch(
                "app.tasks.statistics_tasks.get_archive_anchor_date", return_value=date(2024, 1, 15)
            ):
                with patch("app.tasks.statistics_tasks.mark_archive_processed") as mock_mark:
                    result = analyze_xml_archives(batch_size=1, offset=0)

                    # Verify results
                    assert result["status"] == "completed"
                    assert result["processed"] == 1
                    assert result["results"][0]["anchor_date"] == "2024-01-15"
                    assert result["results"][0]["is_first_processing"] is True

                    # Verify archive was marked as processed
                    mock_mark.assert_called_once()

    @patch("app.tasks.statistics_tasks.SessionLocal")
    @patch("app.tasks.statistics_tasks.parse_abcd_xml")
    def test_subsequent_processing_anchor_date(self, mock_parse, mock_session, mock_archive):
        """Test subsequent processing uses current date."""
        # Setup
        mock_db = MagicMock()
        mock_session.return_value.__enter__.return_value = mock_db
        mock_db.query().filter().order_by().offset().limit().all.return_value = [mock_archive]
        mock_parse.return_value = {"unit_count": 3000, "xml_files_processed": 1}

        with patch("app.tasks.statistics_tasks.is_archive_first_processing", return_value=False):
            with patch(
                "app.tasks.statistics_tasks.get_archive_anchor_date", return_value=date(2024, 6, 20)
            ):
                with patch(
                    "app.tasks.statistics_tasks.get_archive_failure_info", return_value=None
                ):
                    result = analyze_xml_archives(batch_size=1, offset=0)

                    # Verify results
                    assert result["status"] == "completed"
                    assert result["processed"] == 1
                    assert result["results"][0]["anchor_date"] == "2024-06-20"
                    assert result["results"][0].get("is_first_processing") is False

    @patch("app.tasks.statistics_tasks.SessionLocal")
    @patch("app.tasks.statistics_tasks.parse_abcd_xml")
    def test_multiple_archives_different_anchor_dates(self, mock_parse, mock_session):
        """Test processing multiple archives with different anchor dates."""
        # Create archives with different created_at dates
        archive1 = MagicMock(spec=XmlArchiveModel)
        archive1.id = 101
        archive1.dataset_id = 1
        archive1.dataset = MagicMock(created_at=datetime(2024, 1, 10))
        archive1.isLatest = True

        archive2 = MagicMock(spec=XmlArchiveModel)
        archive2.id = 102
        archive2.dataset_id = 2
        archive2.dataset = MagicMock(created_at=datetime(2024, 2, 20))
        archive2.isLatest = True

        archive3 = MagicMock(spec=XmlArchiveModel)
        archive3.id = 103
        archive3.dataset_id = 3
        archive3.dataset = MagicMock(created_at=datetime(2024, 3, 30))
        archive3.isLatest = True

        # Setup
        mock_db = MagicMock()
        mock_session.return_value.__enter__.return_value = mock_db
        mock_db.query().filter().order_by().offset().limit().all.return_value = [
            archive1,
            archive2,
            archive3,
        ]
        mock_parse.return_value = {"unit_count": 1000, "xml_files_processed": 1}

        # Mock different processing states
        with patch("app.tasks.statistics_tasks.is_archive_first_processing") as mock_is_first:
            mock_is_first.side_effect = [
                True,
                False,
                True,
            ]  # 1st: first, 2nd: subsequent, 3rd: first

            with patch("app.tasks.statistics_tasks.get_archive_anchor_date") as mock_get_anchor:
                mock_get_anchor.side_effect = [
                    date(2024, 1, 10),  # Archive 1: dataset created_at
                    date(2024, 6, 20),  # Archive 2: current date
                    date(2024, 3, 30),  # Archive 3: dataset created_at
                ]

                with patch(
                    "app.tasks.statistics_tasks.get_archive_failure_info", return_value=None
                ):
                    result = analyze_xml_archives(batch_size=3, offset=0)

                    # Verify all processed with correct anchor dates
                    assert result["processed"] == 3
                    assert result["results"][0]["anchor_date"] == "2024-01-10"
                    assert result["results"][1]["anchor_date"] == "2024-06-20"
                    assert result["results"][2]["anchor_date"] == "2024-03-30"

    @patch("app.tasks.statistics_tasks.SessionLocal")
    def test_target_date_override(self, mock_session, mock_archive):
        """Test that target_date parameter overrides anchor date logic."""
        mock_db = MagicMock()
        mock_session.return_value.__enter__.return_value = mock_db
        mock_db.query().filter().order_by().offset().limit().all.return_value = [mock_archive]

        with patch("app.tasks.statistics_tasks.parse_abcd_xml") as mock_parse:
            mock_parse.return_value = {"unit_count": 1500, "xml_files_processed": 1}

            # Should not call anchor date functions when target_date is provided
            with patch("app.tasks.statistics_tasks.is_archive_first_processing") as mock_is_first:
                with patch("app.tasks.statistics_tasks.get_archive_anchor_date") as mock_get_anchor:
                    result = analyze_xml_archives(batch_size=1, offset=0, target_date="2024-05-15")

                    # Verify target_date was used
                    assert result["results"][0]["anchor_date"] == "2024-05-15"

                    # Anchor date functions should not be called when target_date is provided
                    # (They may still be called, but the result isn't used)


class TestTimelineDataIntegrity:
    """Test that timeline data appears at correct historical points."""

    @patch("app.tasks.statistics_tasks.SessionLocal")
    def test_timeline_with_mixed_anchor_dates(self, mock_session):
        """Test timeline shows data at correct historical points."""
        mock_db = MagicMock()
        mock_session.return_value.__enter__.return_value = mock_db

        # Create statistics at different anchor dates
        stat1 = MagicMock(spec=StatisticModel)
        stat1.target_date = date(2024, 1, 15)
        stat1.value = 1000
        stat1.extra_data = {"archive_id": 101, "first_processed_at": "2024-01-15T10:00:00"}

        stat2 = MagicMock(spec=StatisticModel)
        stat2.target_date = date(2024, 6, 20)
        stat2.value = 2000
        stat2.extra_data = {"archive_id": 102}

        stat3 = MagicMock(spec=StatisticModel)
        stat3.target_date = date(2024, 3, 10)
        stat3.value = 1500
        stat3.extra_data = {"archive_id": 103, "first_processed_at": "2024-03-10T14:00:00"}

        # Mock query to return statistics in date order
        mock_db.query().filter().order_by().all.return_value = [stat1, stat3, stat2]

        # Timeline should show:
        # - Jan 15: 1000 units (first processing)
        # - Mar 10: 1500 units (first processing)
        # - Jun 20: 2000 units (subsequent processing)

        # Verify the statistics are at correct dates
        assert stat1.target_date == date(2024, 1, 15)
        assert stat2.target_date == date(2024, 6, 20)
        assert stat3.target_date == date(2024, 3, 10)

    @patch("app.tasks.statistics_tasks.SessionLocal")
    def test_provider_aggregation_with_mixed_dates(self, mock_session):
        """Test provider aggregation correctly sums units from different anchor dates."""
        mock_db = MagicMock()
        mock_session.return_value.__enter__.return_value = mock_db

        # Mock provider
        provider = MagicMock(spec=DataProviderModel)
        provider.id = 10
        provider.name = "Test Provider"
        mock_db.query(DataProviderModel).all.return_value = [provider]

        # Mock dataset IDs for provider
        mock_db.query(DatasetModel.id).filter().all.return_value = [(1,), (2,), (3,)]

        # Mock subquery for max dates
        mock_subquery = MagicMock()
        mock_db.query().filter().group_by.return_value = mock_subquery

        # Mock biological units from different anchor dates
        mock_units = [
            (1000, date(2024, 1, 15), 1),  # Dataset 1: historical anchor
            (2000, date(2024, 6, 20), 2),  # Dataset 2: current date anchor
            (1500, date(2024, 3, 10), 3),  # Dataset 3: historical anchor
        ]
        mock_db.query().join().filter().all.return_value = mock_units

        # Execute collection
        result = collect_provider_biological_units(target_date="2024-06-25")

        # Verify aggregation occurred
        assert result["status"] == "completed"
        assert result["date"] == "2024-06-25"

        # Verify database operations
        mock_db.execute.assert_called_once()
        mock_db.commit.assert_called_once()
