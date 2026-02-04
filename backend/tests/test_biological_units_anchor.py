"""
Test biological units anchor date logic for Story 1.2.

This test module verifies that biological units are collected using appropriate
anchor dates based on whether archives are being processed for the first time.
"""

from datetime import date, datetime
from unittest.mock import MagicMock, patch

import pytest
from app.models.dataset import DatasetModel, XmlArchiveModel
from app.models.provider import DataProviderModel
from app.models.statistics import StatisticModel
from app.tasks.statistics_tasks import (
    XMLParsingError,
    analyze_xml_archives,
    collect_provider_biological_units,
    get_archive_anchor_date,
    is_archive_first_processing,
    mark_archive_processed,
    update_provider_biological_units,
)
from sqlalchemy.orm import Session


@pytest.fixture
def mock_db():
    """Create a mock database session."""
    return MagicMock(spec=Session)


@pytest.fixture
def mock_dataset():
    """Create a mock dataset with created_at date."""
    dataset = MagicMock(spec=DatasetModel)
    dataset.id = 1
    dataset.provider_id = 1
    dataset.created_at = datetime(2024, 1, 1, 10, 0, 0)  # Jan 1, 2024
    dataset.updated_at = datetime.utcnow()
    return dataset


@pytest.fixture
def mock_archive(mock_dataset):
    """Create a mock XML archive."""
    archive = MagicMock(spec=XmlArchiveModel)
    archive.id = 100
    archive.dataset_id = 1
    archive.url = "http://example.com/archive.xml"
    archive.isLatest = True
    archive.dataset = mock_dataset
    return archive


@pytest.fixture
def mock_provider():
    """Create a mock data provider."""
    provider = MagicMock(spec=DataProviderModel)
    provider.id = 1
    provider.name = "Test Provider"
    provider.datacenter = "Test DC"
    return provider


class TestArchiveProcessingStateTracking:
    """Test archive processing state tracking helper functions."""

    def test_is_archive_first_processing_no_existing_stats(self, mock_db):
        """Test that archive is considered first processing when no stats exist."""
        mock_db.query().filter().first.return_value = None

        result = is_archive_first_processing(mock_db, 100)

        assert result is True
        mock_db.query.assert_called()

    def test_is_archive_first_processing_with_existing_stats_no_marker(self, mock_db):
        """Test that archive is considered first processing when stats exist but no first_processed_at marker."""
        mock_stat = MagicMock(spec=StatisticModel)
        mock_stat.extra_data = {"archive_id": 100, "unit_count": 500}
        mock_db.query().filter().first.return_value = mock_stat

        result = is_archive_first_processing(mock_db, 100)

        assert result is True

    def test_is_archive_first_processing_with_marker(self, mock_db):
        """Test that archive is not considered first processing when first_processed_at exists."""
        mock_stat = MagicMock(spec=StatisticModel)
        mock_stat.extra_data = {
            "archive_id": 100,
            "unit_count": 500,
            "first_processed_at": "2024-01-15T10:00:00",
        }
        # First query checks for failure, second checks for existing stats
        mock_db.query().filter().first.side_effect = [None, mock_stat]

        result = is_archive_first_processing(mock_db, 100)

        assert result is False

    def test_is_archive_first_processing_with_failure(self, mock_db):
        """Test that failed archives are treated as first processing."""
        mock_failure_stat = MagicMock(spec=StatisticModel)
        mock_failure_stat.extra_data = {
            "archive_id": 100,
            "processing_failed": True,
            "failure_count": 2,
            "last_failure_reason": "Network error",
        }
        mock_db.query().filter().first.return_value = mock_failure_stat

        result = is_archive_first_processing(mock_db, 100)

        assert result is True  # Failed archives should be treated as first processing

    def test_mark_archive_processed(self, mock_db):
        """Test marking an archive as processed adds first_processed_at."""
        mock_stat = MagicMock(spec=StatisticModel)
        mock_stat.extra_data = {"archive_id": 100}
        mock_db.query().filter().first.return_value = mock_stat

        with patch("app.tasks.statistics_tasks.flag_modified") as mock_flag:
            mark_archive_processed(mock_db, 100, 1, date.today())

            assert "first_processed_at" in mock_stat.extra_data
            mock_flag.assert_called_once_with(mock_stat, "extra_data")

    def test_get_archive_anchor_date_first_processing(self, mock_db, mock_archive):
        """Test that first processing uses dataset created_at as anchor date."""
        with patch("app.tasks.statistics_tasks.is_archive_first_processing", return_value=True):
            result = get_archive_anchor_date(mock_db, mock_archive)

            assert result == date(2024, 1, 1)  # Dataset created_at date

    def test_get_archive_anchor_date_subsequent_processing(self, mock_db, mock_archive):
        """Test that subsequent processing uses current date as anchor."""
        with patch("app.tasks.statistics_tasks.is_archive_first_processing", return_value=False):
            with patch("app.tasks.statistics_tasks.get_archive_failure_info", return_value=None):
                with patch("app.tasks.statistics_tasks.date") as mock_date:
                    mock_date.today.return_value = date(2024, 6, 15)

                    result = get_archive_anchor_date(mock_db, mock_archive)

                    assert result == date(2024, 6, 15)  # Current date

    def test_get_archive_anchor_date_with_failure(self, mock_db, mock_archive):
        """Test that failed archives use dataset created_at as anchor date."""
        with patch("app.tasks.statistics_tasks.is_archive_first_processing", return_value=True):
            with patch("app.tasks.statistics_tasks.get_archive_failure_info") as mock_failure_info:
                mock_failure_info.return_value = {
                    "failure_count": 3,
                    "last_failure_reason": "Parse error",
                }

                result = get_archive_anchor_date(mock_db, mock_archive)

                assert result == date(2024, 1, 1)  # Dataset created_at date for retry


class TestAnalyzeXmlArchivesAnchorLogic:
    """Test analyze_xml_archives with anchor date logic."""

    @patch("app.tasks.statistics_tasks.SessionLocal")
    @patch("app.tasks.statistics_tasks.parse_abcd_xml")
    def test_analyze_uses_dataset_created_at_for_first_processing(
        self, mock_parse, mock_session, mock_archive
    ):
        """Test that first-time archive processing uses dataset created_at."""
        # Setup mocks
        mock_db = MagicMock()
        mock_session.return_value = mock_db
        mock_db.query().filter().order_by().offset().limit().all.return_value = [mock_archive]
        mock_parse.return_value = {"unit_count": 1000, "xml_files_processed": 1}

        # Mock first processing check
        with patch("app.tasks.statistics_tasks.is_archive_first_processing", return_value=True):
            with patch(
                "app.tasks.statistics_tasks.get_archive_anchor_date", return_value=date(2024, 1, 1)
            ) as mock_get_anchor:
                # Execute task
                result = analyze_xml_archives(batch_size=1, offset=0)

                # Verify anchor date was retrieved
                mock_get_anchor.assert_called_once_with(mock_db, mock_archive)

                # Verify result includes correct anchor date
                assert result["status"] == "completed"
                assert result["processed"] == 1
                assert result["results"][0]["anchor_date"] == "2024-01-01"
                assert result["results"][0]["is_first_processing"] is True

    @patch("app.tasks.statistics_tasks.SessionLocal")
    @patch("app.tasks.statistics_tasks.parse_abcd_xml")
    def test_analyze_uses_current_date_for_subsequent_processing(
        self, mock_parse, mock_session, mock_archive
    ):
        """Test that subsequent archive processing uses current date."""
        # Setup mocks
        mock_db = MagicMock()
        mock_session.return_value = mock_db
        mock_db.query().filter().order_by().offset().limit().all.return_value = [mock_archive]
        mock_parse.return_value = {"unit_count": 1500, "xml_files_processed": 1}

        # Mock subsequent processing check
        with patch("app.tasks.statistics_tasks.is_archive_first_processing", return_value=False):
            with patch(
                "app.tasks.statistics_tasks.get_archive_anchor_date", return_value=date(2024, 6, 15)
            ) as mock_get_anchor:
                # Execute task
                result = analyze_xml_archives(batch_size=1, offset=0)

                # Verify anchor date was retrieved
                mock_get_anchor.assert_called_once_with(mock_db, mock_archive)

                # Verify result includes correct anchor date
                assert result["status"] == "completed"
                assert result["processed"] == 1
                assert result["results"][0]["anchor_date"] == "2024-06-15"

    @patch("app.tasks.statistics_tasks.SessionLocal")
    def test_analyze_filters_only_latest_archives(self, mock_session):
        """Test that only archives with isLatest=True are processed."""
        mock_db = MagicMock()
        mock_session.return_value = mock_db

        # Create mock query chain
        mock_query = MagicMock()
        mock_db.query.return_value = mock_query
        mock_filter = MagicMock()
        mock_query.filter.return_value = mock_filter
        mock_filter.order_by().offset().limit().all.return_value = []

        # Execute task
        analyze_xml_archives(batch_size=10, offset=0)

        # Verify filter was called with isLatest == True
        mock_query.filter.assert_called_once()
        filter_call = mock_query.filter.call_args[0][0]
        # The filter should check for isLatest == True
        assert str(filter_call).find("isLatest") != -1

    @patch("app.tasks.statistics_tasks.SessionLocal")
    @patch("app.tasks.statistics_tasks.parse_abcd_xml")
    def test_analyze_with_target_date_override(self, mock_parse, mock_session, mock_archive):
        """Test that target_date parameter overrides anchor date logic."""
        mock_db = MagicMock()
        mock_session.return_value = mock_db
        mock_db.query().filter().order_by().offset().limit().all.return_value = [mock_archive]
        mock_parse.return_value = {"unit_count": 2000, "xml_files_processed": 1}

        # Execute task with target_date
        result = analyze_xml_archives(batch_size=1, offset=0, target_date="2024-03-15")

        # Verify override date is used
        assert result["status"] == "completed"
        assert result["results"][0]["anchor_date"] == "2024-03-15"

    @patch("app.tasks.statistics_tasks.SessionLocal")
    @patch("app.tasks.statistics_tasks.parse_abcd_xml")
    def test_analyze_handles_failure_and_marks_archive(
        self, mock_parse, mock_session, mock_archive
    ):
        """Test that failures are tracked properly with failure marking."""
        mock_db = MagicMock()
        mock_session.return_value = mock_db
        mock_db.query().filter().order_by().offset().limit().all.return_value = [mock_archive]

        # Simulate parsing error
        mock_parse.side_effect = XMLParsingError("Invalid XML structure")

        with patch("app.tasks.statistics_tasks.mark_archive_failed") as mock_mark_failed:
            with patch("app.tasks.statistics_tasks.get_archive_failure_info") as mock_failure_info:
                mock_failure_info.return_value = {"failure_count": 1}

                # Execute task
                result = analyze_xml_archives(batch_size=1, offset=0)

                # Verify failure was tracked
                mock_mark_failed.assert_called_once_with(mock_db, 100, "Invalid XML structure")
                assert result["errors"] == 1
                assert result["results"][0]["status"] == "error"
                assert result["results"][0]["failure_count"] == 1
                assert result["results"][0]["will_retry"] is True

    @patch("app.tasks.statistics_tasks.SessionLocal")
    @patch("app.tasks.statistics_tasks.parse_abcd_xml")
    def test_analyze_skips_archives_exceeding_max_retries(
        self, mock_parse, mock_session, mock_archive
    ):
        """Test that archives exceeding max retries are skipped."""
        mock_db = MagicMock()
        mock_session.return_value = mock_db
        mock_db.query().filter().order_by().offset().limit().all.return_value = [mock_archive]

        with patch("app.tasks.statistics_tasks.get_archive_failure_info") as mock_failure_info:
            mock_failure_info.return_value = {
                "failure_count": 5,  # Max retries reached
                "last_failure_reason": "Persistent error",
            }

            # Execute task
            result = analyze_xml_archives(batch_size=1, offset=0)

            # Verify archive was skipped
            assert result["skipped"] == 1
            assert result["processed"] == 0
            assert result["results"][0]["status"] == "skipped"
            mock_parse.assert_not_called()  # Should not attempt to parse


class TestProviderBiologicalUnitsAggregation:
    """Test provider biological units aggregation with anchor dates."""

    @patch("app.tasks.statistics_tasks.SessionLocal")
    def test_collect_aggregates_from_different_anchor_dates(self, mock_session, mock_provider):
        """Test that collection aggregates unit counts from different anchor dates."""
        mock_db = MagicMock()
        mock_session.return_value = mock_db

        # Mock provider query
        mock_db.query(DataProviderModel).all.return_value = [mock_provider]

        # Mock dataset IDs for provider
        mock_db.query(DatasetModel.id).filter().all.return_value = [(1,), (2,), (3,)]

        # Mock subquery for max dates - datasets have stats at different dates
        mock_subquery = MagicMock()
        mock_db.query().filter().group_by.return_value = mock_subquery

        # Mock unit counts from different dates
        # Dataset 1: counted at 2024-01-01 (created_at anchor)
        # Dataset 2: counted at 2024-06-01 (recent update)
        # Dataset 3: counted at 2024-01-15 (created_at anchor)
        mock_counts = [
            (500, date(2024, 1, 1), 1),  # Dataset 1
            (750, date(2024, 6, 1), 2),  # Dataset 2
            (250, date(2024, 1, 15), 3),  # Dataset 3
        ]
        mock_db.query().join().filter().all.return_value = mock_counts

        # Execute collection
        result = collect_provider_biological_units(target_date="2024-06-15")

        # Verify aggregation
        assert result["status"] == "completed"
        assert result["date"] == "2024-06-15"

        # Verify that execute was called to insert provider stats
        mock_db.execute.assert_called_once()

    @patch("app.tasks.statistics_tasks.SessionLocal")
    def test_update_provider_respects_anchor_dates(self, mock_session, mock_provider):
        """Test that provider update respects anchor dates in aggregation."""
        mock_db = MagicMock()
        mock_session.return_value = mock_db

        # Mock provider query
        mock_db.query(DataProviderModel).filter().first.return_value = mock_provider

        # Mock dataset IDs
        mock_db.query(DatasetModel.id).filter().all.return_value = [(1,), (2,)]

        # Mock subquery
        mock_subquery = MagicMock()
        mock_db.query().filter().group_by.return_value = mock_subquery

        # Mock unit counts from different anchor dates
        mock_counts = [
            (1000, date(2024, 1, 1), 1),  # Historical anchor
            (2000, date(2024, 6, 10), 2),  # Recent update
        ]
        mock_db.query().join().filter().all.return_value = mock_counts

        # Execute update
        result = update_provider_biological_units(provider_id=1, target_date="2024-06-15")

        # Verify success
        assert result["status"] == "completed"
        assert result["biological_units"] == 3000  # Sum of both counts
        assert result["date"] == "2024-06-15"


class TestTimelineIntegration:
    """Test that biological units appear at correct points on timeline (IV1)."""

    @patch("app.tasks.statistics_tasks.SessionLocal")
    @patch("app.tasks.statistics_tasks.parse_abcd_xml")
    def test_biological_units_timeline_with_historical_anchors(self, mock_parse, mock_session):
        """Test that units appear at correct historical points on timeline."""
        mock_db = MagicMock()
        mock_session.return_value = mock_db

        # Create archives with different created_at dates
        archive1 = MagicMock(spec=XmlArchiveModel)
        archive1.id = 1
        archive1.dataset_id = 1
        archive1.isLatest = True
        archive1.dataset = MagicMock(created_at=datetime(2024, 1, 1))

        archive2 = MagicMock(spec=XmlArchiveModel)
        archive2.id = 2
        archive2.dataset_id = 2
        archive2.isLatest = True
        archive2.dataset = MagicMock(created_at=datetime(2024, 2, 15))

        mock_db.query().filter().order_by().offset().limit().all.return_value = [archive1, archive2]
        mock_parse.return_value = {"unit_count": 1000, "xml_files_processed": 1}

        # Mock first processing for both
        with patch("app.tasks.statistics_tasks.is_archive_first_processing", return_value=True):
            with patch(
                "backend.app.tasks.statistics_tasks.get_archive_anchor_date"
            ) as mock_get_anchor:
                # Return different anchor dates based on archive
                mock_get_anchor.side_effect = [date(2024, 1, 1), date(2024, 2, 15)]

                # Execute
                result = analyze_xml_archives(batch_size=2, offset=0)

                # Verify each archive got its correct historical anchor
                assert result["results"][0]["anchor_date"] == "2024-01-01"
                assert result["results"][1]["anchor_date"] == "2024-02-15"


class TestProcessingStateResilience:
    """Test that processing state persists across runs (IV3)."""

    @patch("app.tasks.statistics_tasks.SessionLocal")
    def test_processing_state_persists_in_extra_data(self, mock_session):
        """Test that first_processed_at persists in extra_data field."""
        mock_db = MagicMock()
        mock_session.return_value = mock_db

        # Create a statistic with first_processed_at
        mock_stat = MagicMock(spec=StatisticModel)
        mock_stat.extra_data = {"archive_id": 100, "first_processed_at": "2024-01-15T10:00:00"}

        mock_db.query().filter().first.return_value = mock_stat

        # Check if first processing
        result = is_archive_first_processing(mock_db, 100)

        # Should return False since first_processed_at exists
        assert result is False

        # Verify state was read from extra_data
        assert mock_stat.extra_data["first_processed_at"] == "2024-01-15T10:00:00"
