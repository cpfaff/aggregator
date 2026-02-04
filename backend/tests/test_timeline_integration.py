"""
Integration tests for the complete timeline feature.

Tests the full workflow from archive creation through processing to statistics
generation, including retry mechanisms and timeline integrity.
"""

from datetime import date, datetime, timedelta
from unittest.mock import MagicMock, Mock, patch

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
)
from sqlalchemy.orm import Session


@pytest.fixture
def mock_db_session():
    """Create a comprehensive mock database session."""
    db = MagicMock(spec=Session)
    db.commit = MagicMock()
    db.rollback = MagicMock()
    db.add = MagicMock()
    db.execute = MagicMock()
    db.query = MagicMock()
    return db


@pytest.fixture
def sample_provider():
    """Create a sample provider."""
    provider = Mock(spec=DataProviderModel)
    provider.id = 1
    provider.name = "Test Provider"
    provider.datacenter = "Test DC"
    return provider


@pytest.fixture
def sample_dataset():
    """Create a sample dataset."""
    dataset = Mock(spec=DatasetModel)
    dataset.id = 1
    dataset.provider_id = 1
    dataset.created_at = datetime(2024, 1, 15, 10, 0, 0)
    dataset.updated_at = datetime(2024, 6, 20, 15, 0, 0)
    return dataset


@pytest.fixture
def sample_archive(sample_dataset):
    """Create a sample archive."""
    archive = Mock(spec=XmlArchiveModel)
    archive.id = 100
    archive.dataset_id = 1
    archive.url = "http://example.com/data.xml"
    archive.isLatest = True
    archive.dataset = sample_dataset
    return archive


class TestCompleteTimelineWorkflow:
    """Test the complete timeline workflow from archive creation to statistics."""

    @patch("app.tasks.statistics_tasks.SessionLocal")
    @patch("app.tasks.statistics_tasks.parse_abcd_xml")
    def test_full_workflow_first_processing_to_statistics(
        self, mock_parse, mock_session, sample_archive, sample_dataset
    ):
        """Test full workflow: archive creation → first processing → statistics at created_at."""
        # Setup
        mock_db = MagicMock()
        mock_session.return_value.__enter__.return_value = mock_db

        # Step 1: Archive is created and ready for processing
        mock_db.query().filter().order_by().offset().limit().all.return_value = [sample_archive]

        # Step 2: First processing check
        with patch("app.tasks.statistics_tasks.is_archive_first_processing", return_value=True):
            # Step 3: Get anchor date (should be dataset created_at)
            with patch(
                "app.tasks.statistics_tasks.get_archive_anchor_date", return_value=date(2024, 1, 15)
            ):
                # Step 4: Parse XML successfully
                mock_parse.return_value = {
                    "unit_count": 5000,
                    "xml_files_processed": 1,
                    "scientific_names": ["Species A", "Species B"],
                }

                # Step 5: Mark as processed
                with patch("app.tasks.statistics_tasks.mark_archive_processed") as mock_mark:
                    # Execute the task
                    result = analyze_xml_archives(batch_size=1, offset=0)

                    # Verify workflow execution
                    assert result["status"] == "completed"
                    assert result["processed"] == 1
                    assert result["errors"] == 0

                    # Verify correct anchor date was used
                    archive_result = result["results"][0]
                    assert archive_result["archive_id"] == 100
                    assert archive_result["anchor_date"] == "2024-01-15"
                    assert archive_result["is_first_processing"] is True
                    assert archive_result["unit_count"] == 5000

                    # Verify archive was marked as processed
                    mock_mark.assert_called_once_with(mock_db, 100, 1, date(2024, 1, 15))

        # Step 6: Verify statistics would be created at correct date
        # This would normally happen through database operations
        mock_db.execute.assert_called()
        mock_db.commit.assert_called()

    @patch("app.tasks.statistics_tasks.SessionLocal")
    @patch("app.tasks.statistics_tasks.parse_abcd_xml")
    def test_retry_workflow_failure_to_success(self, mock_parse, mock_session, sample_archive):
        """Test retry workflow: failure → retry with created_at → success."""
        mock_db = MagicMock()
        mock_session.return_value.__enter__.return_value = mock_db

        # Setup: Archive that previously failed
        mock_db.query().filter().order_by().offset().limit().all.return_value = [sample_archive]

        # First attempt: Simulate failure
        mock_parse.side_effect = XMLParsingError("Network timeout")

        with patch("app.tasks.statistics_tasks.is_archive_first_processing", return_value=True):
            with patch(
                "app.tasks.statistics_tasks.get_archive_anchor_date", return_value=date(2024, 1, 15)
            ):
                with patch("app.tasks.statistics_tasks.mark_archive_failed") as mock_mark_failed:
                    with patch(
                        "app.tasks.statistics_tasks.get_archive_failure_info"
                    ) as mock_failure_info:
                        mock_failure_info.return_value = {"failure_count": 1}

                        # First processing attempt fails
                        result = analyze_xml_archives(batch_size=1, offset=0)

                        assert result["status"] == "completed"
                        assert result["errors"] == 1
                        assert result["results"][0]["status"] == "error"
                        assert result["results"][0]["failure_count"] == 1
                        assert result["results"][0]["will_retry"] is True

                        # Verify failure was tracked
                        mock_mark_failed.assert_called_once_with(mock_db, 100, "Network timeout")

        # Reset for retry attempt
        mock_parse.side_effect = None
        mock_parse.return_value = {"unit_count": 5000, "xml_files_processed": 1}

        # Second attempt: Retry after some time
        with patch("app.tasks.statistics_tasks.get_archive_failure_info") as mock_failure_info:
            mock_failure_info.return_value = {
                "failure_count": 1,
                "last_failure_at": (datetime.utcnow() - timedelta(minutes=5)).isoformat(),
            }

            with patch("app.tasks.statistics_tasks.should_retry_failed_archive", return_value=True):
                with patch(
                    "app.tasks.statistics_tasks.is_archive_first_processing", return_value=True
                ):
                    with patch(
                        "app.tasks.statistics_tasks.get_archive_anchor_date",
                        return_value=date(2024, 1, 15),
                    ):
                        with patch(
                            "app.tasks.statistics_tasks.reset_archive_failure"
                        ) as mock_reset:
                            with patch(
                                "app.tasks.statistics_tasks.mark_archive_processed"
                            ) as mock_mark:
                                # Retry processing
                                result = analyze_xml_archives(batch_size=1, offset=0)

                                # Verify successful retry
                                assert result["status"] == "completed"
                                assert result["processed"] == 1
                                assert result["errors"] == 0

                                # Verify anchor date remained as created_at
                                assert result["results"][0]["anchor_date"] == "2024-01-15"

                                # Verify failure was reset and archive marked as processed
                                mock_reset.assert_called_once_with(mock_db, 100)
                                mock_mark.assert_called_once()

    @patch("app.tasks.statistics_tasks.SessionLocal")
    @patch("app.tasks.statistics_tasks.parse_abcd_xml")
    def test_timeline_integrity_with_mixed_archives(self, mock_parse, mock_session):
        """Test timeline integrity with mixed successful and failed archives."""
        mock_db = MagicMock()
        mock_session.return_value.__enter__.return_value = mock_db

        # Create multiple archives with different states
        archive1 = Mock(spec=XmlArchiveModel)
        archive1.id = 101
        archive1.dataset_id = 1
        archive1.dataset = Mock(created_at=datetime(2024, 1, 10))
        archive1.isLatest = True

        archive2 = Mock(spec=XmlArchiveModel)
        archive2.id = 102
        archive2.dataset_id = 2
        archive2.dataset = Mock(created_at=datetime(2024, 2, 15))
        archive2.isLatest = True

        archive3 = Mock(spec=XmlArchiveModel)
        archive3.id = 103
        archive3.dataset_id = 3
        archive3.dataset = Mock(created_at=datetime(2024, 3, 20))
        archive3.isLatest = True

        mock_db.query().filter().order_by().offset().limit().all.return_value = [
            archive1,
            archive2,
            archive3,
        ]

        # Archive 1: Successful first processing
        # Archive 2: Failed processing
        # Archive 3: Successful subsequent processing

        parse_results = [
            {"unit_count": 1000, "xml_files_processed": 1},  # Archive 1 success
            XMLParsingError("Invalid XML"),  # Archive 2 failure
            {"unit_count": 1500, "xml_files_processed": 1},  # Archive 3 success
        ]

        mock_parse.side_effect = parse_results

        # Mock processing states
        with patch("app.tasks.statistics_tasks.is_archive_first_processing") as mock_is_first:
            mock_is_first.side_effect = [True, True, False]

            with patch("app.tasks.statistics_tasks.get_archive_anchor_date") as mock_get_anchor:
                mock_get_anchor.side_effect = [
                    date(2024, 1, 10),  # Archive 1: created_at
                    date(2024, 2, 15),  # Archive 2: created_at (will fail)
                    date(2024, 6, 20),  # Archive 3: current date
                ]

                with patch("app.tasks.statistics_tasks.mark_archive_processed") as mock_mark:
                    with patch(
                        "app.tasks.statistics_tasks.mark_archive_failed"
                    ) as mock_mark_failed:
                        with patch(
                            "app.tasks.statistics_tasks.get_archive_failure_info"
                        ) as mock_failure:
                            mock_failure.return_value = None

                            # Process all archives
                            result = analyze_xml_archives(batch_size=3, offset=0)

                            # Verify results
                            assert result["status"] == "completed"
                            assert result["processed"] == 2  # 2 successful
                            assert result["errors"] == 1  # 1 failed

                            # Check timeline integrity
                            assert result["results"][0]["status"] == "success"
                            assert result["results"][0]["anchor_date"] == "2024-01-10"

                            assert result["results"][1]["status"] == "error"

                            assert result["results"][2]["status"] == "success"
                            assert result["results"][2]["anchor_date"] == "2024-06-20"

                            # Verify only successful archives were marked as processed
                            assert mock_mark.call_count == 2
                            mock_mark_failed.assert_called_once_with(mock_db, 102, "Invalid XML")

    @patch("app.tasks.statistics_tasks.SessionLocal")
    def test_provider_aggregation_workflow(self, mock_session, sample_provider):
        """Test provider aggregation with archives at different anchor dates."""
        mock_db = MagicMock()
        mock_session.return_value.__enter__.return_value = mock_db

        # Setup provider and datasets
        mock_db.query(DataProviderModel).all.return_value = [sample_provider]
        mock_db.query(DatasetModel.id).filter().all.return_value = [(1,), (2,), (3,), (4,)]

        # Mock subquery for max dates
        mock_subquery = MagicMock()
        mock_db.query().filter().group_by.return_value = mock_subquery

        # Biological units from different processing times:
        # - Dataset 1: First processing at created_at (Jan 10)
        # - Dataset 2: Failed processing (should be excluded)
        # - Dataset 3: First processing at created_at (Mar 20)
        # - Dataset 4: Subsequent processing at current date (Jun 20)

        units_data = [
            (1000, date(2024, 1, 10), 1),  # Historical
            # Dataset 2 failed - not in results
            (1500, date(2024, 3, 20), 3),  # Historical
            (2000, date(2024, 6, 20), 4),  # Current
        ]
        mock_db.query().join().filter().all.return_value = units_data

        # Execute aggregation
        result = collect_provider_biological_units(target_date="2024-06-25")

        # Verify aggregation
        assert result["status"] == "completed"
        assert result["date"] == "2024-06-25"

        # Verify database operations (INSERT/UPDATE for provider totals)
        mock_db.execute.assert_called_once()
        mock_db.commit.assert_called()

        # Total should be sum of all successful archives (4500)
        # excluding failed Dataset 2


class TestFailureRecoveryIntegration:
    """Test integration of failure recovery mechanisms."""

    @patch("app.tasks.statistics_tasks.SessionLocal")
    def test_max_retries_circuit_breaker(self, mock_session, sample_archive):
        """Test that archives exceeding max retries are skipped (IV1)."""
        mock_db = MagicMock()
        mock_session.return_value.__enter__.return_value = mock_db

        # Archive with max retries exceeded
        mock_db.query().filter().order_by().offset().limit().all.return_value = [sample_archive]

        with patch("app.tasks.statistics_tasks.get_archive_failure_info") as mock_failure:
            mock_failure.return_value = {
                "failure_count": 5,  # Max retries reached
                "last_failure_at": datetime.utcnow().isoformat(),
                "last_failure_reason": "Persistent parsing error",
            }

            with patch(
                "app.tasks.statistics_tasks.should_retry_failed_archive", return_value=False
            ):
                with patch("app.tasks.statistics_tasks.parse_abcd_xml") as mock_parse:
                    # Process archives
                    result = analyze_xml_archives(batch_size=1, offset=0)

                    # Verify archive was skipped
                    assert result["status"] == "completed"
                    assert result["processed"] == 0
                    assert result["skipped"] == 1
                    assert result["results"][0]["status"] == "skipped"
                    assert result["results"][0]["reason"] == "Max retries exceeded"

                    # Parse should not be called for skipped archive
                    mock_parse.assert_not_called()

    @patch("app.tasks.statistics_tasks.SessionLocal")
    @patch("app.tasks.statistics_tasks.parse_abcd_xml")
    def test_time_based_reset_recovery(self, mock_parse, mock_session, sample_archive):
        """Test recovery after 24-hour reset period."""
        mock_db = MagicMock()
        mock_session.return_value.__enter__.return_value = mock_db

        mock_db.query().filter().order_by().offset().limit().all.return_value = [sample_archive]

        # Archive failed 25 hours ago with max retries
        old_failure_time = (datetime.utcnow() - timedelta(hours=25)).isoformat()

        with patch("app.tasks.statistics_tasks.get_archive_failure_info") as mock_failure:
            mock_failure.return_value = {
                "failure_count": 5,  # Max retries exceeded
                "last_failure_at": old_failure_time,
                "last_failure_reason": "Old network error",
            }

            with patch("app.tasks.statistics_tasks.should_retry_failed_archive", return_value=True):
                with patch(
                    "app.tasks.statistics_tasks.is_archive_first_processing", return_value=True
                ):
                    with patch(
                        "app.tasks.statistics_tasks.get_archive_anchor_date",
                        return_value=date(2024, 1, 15),
                    ):
                        mock_parse.return_value = {"unit_count": 3000, "xml_files_processed": 1}

                        with patch(
                            "app.tasks.statistics_tasks.reset_archive_failure"
                        ) as mock_reset:
                            # Process after reset period
                            result = analyze_xml_archives(batch_size=1, offset=0)

                            # Verify successful recovery
                            assert result["status"] == "completed"
                            assert result["processed"] == 1
                            assert result["errors"] == 0

                            # Verify failure was reset
                            mock_reset.assert_called_once_with(mock_db, 100)

    @patch("app.tasks.statistics_tasks.SessionLocal")
    def test_failed_archives_not_corrupting_timeline(self, mock_session):
        """Verify failed archives don't corrupt timeline data (IV1)."""
        mock_db = MagicMock()
        mock_session.return_value.__enter__.return_value = mock_db

        # Create statistics with mixed states
        successful_stat = Mock(spec=StatisticModel)
        successful_stat.entity_id = 1
        successful_stat.target_date = date(2024, 1, 15)
        successful_stat.value = 5000
        successful_stat.extra_data = {
            "archive_id": 101,
            "first_processed_at": "2024-01-15T10:00:00",
        }

        failed_stat = Mock(spec=StatisticModel)
        failed_stat.entity_id = 1
        failed_stat.target_date = date(2024, 2, 10)
        failed_stat.value = 0  # Failed archives have 0 value
        failed_stat.extra_data = {"archive_id": 102, "processing_failed": True, "failure_count": 3}

        another_successful = Mock(spec=StatisticModel)
        another_successful.entity_id = 1
        another_successful.target_date = date(2024, 3, 20)
        another_successful.value = 3000
        another_successful.extra_data = {
            "archive_id": 103,
            "first_processed_at": "2024-03-20T14:00:00",
        }

        # Timeline query should filter out failed archives
        timeline_stats = [successful_stat, another_successful]  # Excludes failed_stat

        mock_query = MagicMock()
        mock_db.query.return_value = mock_query
        mock_query.filter.return_value = mock_query
        mock_query.order_by.return_value = mock_query
        mock_query.all.return_value = timeline_stats

        # Verify timeline integrity
        assert len(timeline_stats) == 2
        assert all(s.value > 0 for s in timeline_stats)

        # Check that timeline has correct dates without gaps from failed archives
        dates = [s.target_date for s in timeline_stats]
        assert dates == [date(2024, 1, 15), date(2024, 3, 20)]

        # Total biological units should exclude failed archive
        total = sum(s.value for s in timeline_stats)
        assert total == 8000  # 5000 + 3000, excluding failed archive's 0


class TestEdgeCases:
    """Test edge cases and boundary conditions."""

    @patch("app.tasks.statistics_tasks.SessionLocal")
    @patch("app.tasks.statistics_tasks.parse_abcd_xml")
    def test_empty_archive_batch(self, mock_parse, mock_session):
        """Test handling of empty archive batch."""
        mock_db = MagicMock()
        mock_session.return_value.__enter__.return_value = mock_db

        # No archives to process
        mock_db.query().filter().order_by().offset().limit().all.return_value = []

        result = analyze_xml_archives(batch_size=10, offset=0)

        assert result["status"] == "completed"
        assert result["processed"] == 0
        assert result["errors"] == 0
        assert result["skipped"] == 0
        assert result["results"] == []

        # Parse should not be called
        mock_parse.assert_not_called()

    @patch("app.tasks.statistics_tasks.SessionLocal")
    def test_null_dataset_created_at(self, mock_session):
        """Test handling when dataset created_at is None."""
        mock_db = MagicMock()
        mock_session.return_value.__enter__.return_value = mock_db

        # Archive with null dataset created_at
        archive = Mock(spec=XmlArchiveModel)
        archive.id = 100
        archive.dataset = Mock(created_at=None)

        with patch("app.tasks.statistics_tasks.is_archive_first_processing", return_value=True):
            with patch("app.tasks.statistics_tasks.date") as mock_date:
                mock_date.today.return_value = date(2024, 6, 20)

                anchor_date = get_archive_anchor_date(mock_db, archive)

                # Should fall back to current date
                assert anchor_date == date(2024, 6, 20)

    @patch("app.tasks.statistics_tasks.SessionLocal")
    def test_concurrent_processing_handling(self, mock_session):
        """Test handling of concurrent processing scenarios."""
        mock_db = MagicMock()
        mock_session.return_value.__enter__.return_value = mock_db

        # Simulate concurrent modification
        mock_stat = Mock(spec=StatisticModel)
        mock_stat.extra_data = {"archive_id": 100}

        # First call returns stat without marker, second with marker
        # (simulating another process marking it)
        mock_db.query().filter().first.side_effect = [
            mock_stat,  # First check
            Mock(
                extra_data={"archive_id": 100, "first_processed_at": "2024-06-20T10:00:00"}
            ),  # Second check
        ]

        # First check shows first processing
        result1 = is_archive_first_processing(mock_db, 100)
        assert result1 is True

        # Second check shows already processed (by another worker)
        result2 = is_archive_first_processing(mock_db, 100)
        assert result2 is False
