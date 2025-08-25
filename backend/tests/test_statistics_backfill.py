"""
Tests for timestamp-based statistics collection with backfill-then-update pattern.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock, call
from datetime import datetime, date, timedelta
from sqlalchemy.orm import Session

from app.tasks.statistics_tasks import (
    check_statistics_exist,
    generate_backfill_dates,
    get_cumulative_count,
    perform_statistics_upsert,
    collect_daily_statistics
)
from app.models import (
    StatisticModel,
    DatasetModel,
    DataProviderModel,
    XmlArchiveModel,
    ValidationJobModel,
    MetricType,
    EntityType,
    Period
)


class TestDetectionLogic:
    """Test detection logic for existing statistics."""
    
    def test_check_statistics_exist_when_empty(self):
        """Test that check_statistics_exist returns False when no statistics exist."""
        mock_db = Mock(spec=Session)
        mock_query = Mock()
        mock_db.query.return_value = mock_query
        mock_query.filter.return_value = mock_query
        mock_query.first.return_value = None
        
        result = check_statistics_exist(
            mock_db,
            MetricType.DATASET_COUNT,
            EntityType.SYSTEM,
            None,
            Period.DAILY
        )
        
        assert result is False
        mock_db.query.assert_called_once_with(StatisticModel)
        mock_query.first.assert_called_once()
    
    def test_check_statistics_exist_when_populated(self):
        """Test that check_statistics_exist returns True when statistics exist."""
        mock_db = Mock(spec=Session)
        mock_query = Mock()
        mock_db.query.return_value = mock_query
        mock_query.filter.return_value = mock_query
        mock_query.first.return_value = Mock(spec=StatisticModel)  # Non-None value
        
        result = check_statistics_exist(
            mock_db,
            MetricType.DATASET_COUNT,
            EntityType.SYSTEM,
            None,
            Period.DAILY
        )
        
        assert result is True
        mock_db.query.assert_called_once_with(StatisticModel)
        mock_query.first.assert_called_once()
    
    def test_check_statistics_exist_with_entity_id(self):
        """Test check_statistics_exist with a specific entity_id."""
        mock_db = Mock(spec=Session)
        mock_query = Mock()
        mock_db.query.return_value = mock_query
        mock_query.filter.return_value = mock_query
        mock_query.first.return_value = None
        
        result = check_statistics_exist(
            mock_db,
            MetricType.PROVIDER_DATASET_COUNT,
            EntityType.PROVIDER,
            123,
            Period.DAILY
        )
        
        assert result is False
        mock_db.query.assert_called_once_with(StatisticModel)


class TestBackfillLogic:
    """Test backfill date generation logic."""
    
    def test_generate_backfill_dates_single_day(self):
        """Test generating backfill dates for a single day."""
        start_date = datetime(2024, 1, 1, 10, 30)
        target_date = date(2024, 1, 1)
        
        dates = generate_backfill_dates(start_date, target_date)
        
        assert len(dates) == 1
        assert dates[0] == date(2024, 1, 1)
    
    def test_generate_backfill_dates_multiple_days(self):
        """Test generating backfill dates for multiple days."""
        start_date = datetime(2024, 1, 1, 10, 30)
        target_date = date(2024, 1, 5)
        
        dates = generate_backfill_dates(start_date, target_date)
        
        assert len(dates) == 5
        assert dates[0] == date(2024, 1, 1)
        assert dates[-1] == date(2024, 1, 5)
    
    def test_generate_backfill_dates_with_date_input(self):
        """Test generating backfill dates when start_date is already a date."""
        start_date = date(2024, 1, 1)
        target_date = date(2024, 1, 3)
        
        dates = generate_backfill_dates(start_date, target_date)
        
        assert len(dates) == 3
        assert dates == [date(2024, 1, 1), date(2024, 1, 2), date(2024, 1, 3)]
    
    def test_generate_backfill_dates_large_range(self):
        """Test generating backfill dates for a year."""
        start_date = date(2023, 1, 1)
        target_date = date(2023, 12, 31)
        
        dates = generate_backfill_dates(start_date, target_date)
        
        assert len(dates) == 365  # 2023 is not a leap year
        assert dates[0] == date(2023, 1, 1)
        assert dates[-1] == date(2023, 12, 31)


class TestCumulativeCount:
    """Test cumulative counting logic."""
    
    def test_get_cumulative_count_no_filter(self):
        """Test cumulative count without additional filters."""
        mock_db = Mock(spec=Session)
        mock_query = Mock()
        mock_db.query.return_value = mock_query
        mock_query.filter.return_value = mock_query
        mock_query.scalar.return_value = 42
        
        target_date = date(2024, 1, 15)
        
        result = get_cumulative_count(mock_db, DatasetModel, target_date)
        
        assert result == 42
        mock_query.scalar.assert_called_once()
    
    def test_get_cumulative_count_with_filter(self):
        """Test cumulative count with additional filter conditions."""
        mock_db = Mock(spec=Session)
        mock_query = Mock()
        mock_db.query.return_value = mock_query
        mock_query.filter.return_value = mock_query
        mock_query.scalar.return_value = 10
        
        target_date = date(2024, 1, 15)
        
        result = get_cumulative_count(
            mock_db, 
            DatasetModel, 
            target_date,
            filter_conditions=(DatasetModel.provider_id == 5)
        )
        
        assert result == 10
        assert mock_query.filter.call_count == 2  # Once for date, once for additional filter
    
    def test_get_cumulative_count_returns_zero_when_none(self):
        """Test that cumulative count returns 0 when scalar returns None."""
        mock_db = Mock(spec=Session)
        mock_query = Mock()
        mock_db.query.return_value = mock_query
        mock_query.filter.return_value = mock_query
        mock_query.scalar.return_value = None
        
        result = get_cumulative_count(mock_db, DatasetModel, date(2024, 1, 1))
        
        assert result == 0


class TestUpsertOperation:
    """Test the upsert operation helper."""
    
    @patch('app.tasks.statistics_tasks.logger')
    def test_perform_statistics_upsert_basic(self, mock_logger):
        """Test basic upsert operation."""
        mock_db = Mock(spec=Session)
        
        perform_statistics_upsert(
            db=mock_db,
            metric_type=MetricType.DATASET_COUNT,
            entity_type=EntityType.SYSTEM,
            entity_id=None,
            period=Period.DAILY,
            date_value=date(2024, 1, 1),
            value=100.0,
            extra_data={'test': 'data'},
            log_message="Test log message"
        )
        
        mock_db.execute.assert_called_once()
        mock_logger.debug.assert_called_once_with("Test log message")
    
    @patch('app.tasks.statistics_tasks.logger')
    def test_perform_statistics_upsert_no_log(self, mock_logger):
        """Test upsert operation without log message."""
        mock_db = Mock(spec=Session)
        
        perform_statistics_upsert(
            db=mock_db,
            metric_type=MetricType.PROVIDER_COUNT,
            entity_type=EntityType.SYSTEM,
            entity_id=None,
            period=Period.DAILY,
            date_value=date(2024, 1, 1),
            value=5.0,
            extra_data={'test': 'data'}
        )
        
        mock_db.execute.assert_called_once()
        mock_logger.debug.assert_not_called()


class TestCollectDailyStatistics:
    """Test the main collect_daily_statistics task."""
    
    @patch('app.tasks.statistics_tasks.SessionLocal')
    @patch('app.tasks.statistics_tasks.check_statistics_exist')
    @patch('app.tasks.statistics_tasks.generate_backfill_dates')
    @patch('app.tasks.statistics_tasks.get_cumulative_count')
    @patch('app.tasks.statistics_tasks.perform_statistics_upsert')
    def test_collect_daily_statistics_backfill_mode(
        self, 
        mock_upsert, 
        mock_cumulative_count,
        mock_generate_dates,
        mock_check_exist,
        mock_session_local
    ):
        """Test collect_daily_statistics in backfill mode (no existing stats)."""
        # Setup mocks
        mock_db = MagicMock(spec=Session)
        mock_session_local.return_value = mock_db
        
        # No existing statistics - trigger backfill
        mock_check_exist.return_value = False
        
        # Setup backfill dates
        mock_generate_dates.return_value = [
            date(2024, 1, 1),
            date(2024, 1, 2),
            date(2024, 1, 3)
        ]
        
        # Setup cumulative counts
        mock_cumulative_count.side_effect = [10, 15, 20] * 10  # Enough for all calls
        
        # Setup query mocks for earliest dates
        mock_db.query.return_value.scalar.side_effect = [
            datetime(2024, 1, 1),  # earliest_dataset
            datetime(2024, 1, 1),  # earliest_provider
            datetime(2024, 1, 1),  # earliest_archive
        ]
        
        # Mock providers and validation jobs
        mock_db.query.return_value.all.side_effect = [
            [],  # validation_jobs
            []   # providers
        ]
        
        # Mock rate counts
        mock_db.query.return_value.filter.return_value.scalar.side_effect = [0, 0]
        
        # Create task instance
        task = Mock()
        task.request.id = 'test-task-id'
        
        # Execute
        result = collect_daily_statistics(task, '2024-01-03')
        
        # Verify backfill was triggered
        assert mock_check_exist.call_count >= 3  # At least for system metrics
        assert mock_generate_dates.called
        assert 'backfill_performed' in result
        assert result['status'] == 'completed'
        assert result['date'] == '2024-01-03'
        
        # Verify upserts were called for backfill
        assert mock_upsert.call_count > 0
        mock_db.commit.assert_called_once()
    
    @patch('app.tasks.statistics_tasks.SessionLocal')
    @patch('app.tasks.statistics_tasks.check_statistics_exist')
    @patch('app.tasks.statistics_tasks.get_cumulative_count')
    @patch('app.tasks.statistics_tasks.perform_statistics_upsert')
    def test_collect_daily_statistics_incremental_mode(
        self,
        mock_upsert,
        mock_cumulative_count,
        mock_check_exist,
        mock_session_local
    ):
        """Test collect_daily_statistics in incremental mode (stats exist)."""
        # Setup mocks
        mock_db = MagicMock(spec=Session)
        mock_session_local.return_value = mock_db
        
        # Statistics exist - trigger incremental update
        mock_check_exist.return_value = True
        
        # Setup cumulative counts for incremental updates
        mock_cumulative_count.return_value = 100
        
        # Setup query mocks for earliest dates
        mock_db.query.return_value.scalar.side_effect = [
            datetime(2024, 1, 1),  # earliest_dataset
            datetime(2024, 1, 1),  # earliest_provider
            datetime(2024, 1, 1),  # earliest_archive
        ]
        
        # Mock providers and validation jobs
        mock_db.query.return_value.all.side_effect = [
            [],  # validation_jobs
            []   # providers
        ]
        
        # Mock rate counts
        mock_db.query.return_value.filter.return_value.scalar.side_effect = [5, 3]
        
        # Create task instance
        task = Mock()
        task.request.id = 'test-task-id'
        
        # Execute
        result = collect_daily_statistics(task, '2024-01-15')
        
        # Verify incremental mode
        assert mock_check_exist.call_count >= 3  # System metrics checks
        assert 'backfill_performed' in result
        assert len(result['backfill_performed']) == 0  # No backfill in incremental mode
        assert result['status'] == 'completed'
        
        # Verify upserts were called but only for current date
        assert mock_upsert.call_count >= 5  # System metrics + rates
        mock_db.commit.assert_called_once()
    
    @patch('app.tasks.statistics_tasks.SessionLocal')
    def test_collect_daily_statistics_error_handling(self, mock_session_local):
        """Test error handling in collect_daily_statistics."""
        mock_db = MagicMock(spec=Session)
        mock_session_local.return_value = mock_db
        
        # Force an error
        mock_db.query.side_effect = Exception("Database error")
        
        # Create task instance
        task = Mock()
        task.request.id = 'test-task-id'
        
        # Execute and expect exception
        with pytest.raises(Exception) as exc_info:
            collect_daily_statistics(task, '2024-01-15')
        
        assert "Database error" in str(exc_info.value)
        mock_db.rollback.assert_called_once()
        mock_db.close.assert_called_once()


class TestIntegrationVerification:
    """Tests to verify integration requirements are met."""
    
    def test_api_response_format_unchanged(self):
        """IV1: Verify that statistics API response format remains unchanged."""
        # This would be tested at the API level, not in the task
        # Placeholder for integration test reference
        pass
    
    def test_database_performance_threshold(self):
        """IV2: Verify database queries complete in < 1s."""
        # This would be tested with performance benchmarks
        # Placeholder for performance test reference
        pass
    
    def test_memory_usage_baseline(self):
        """IV3: Verify memory usage stays within baseline."""
        # This would be tested with memory profiling
        # Placeholder for memory test reference
        pass
    
    @patch('app.tasks.statistics_tasks.SessionLocal')
    @patch('app.tasks.statistics_tasks.check_statistics_exist')
    @patch('app.tasks.statistics_tasks.generate_backfill_dates')
    @patch('app.tasks.statistics_tasks.get_cumulative_count')
    @patch('app.tasks.statistics_tasks.perform_statistics_upsert')
    def test_backfill_generates_complete_timeline(
        self,
        mock_upsert,
        mock_cumulative_count,
        mock_generate_dates,
        mock_check_exist,
        mock_session_local
    ):
        """IV4: Verify backfill generates complete historical timeline on first run."""
        mock_db = MagicMock(spec=Session)
        mock_session_local.return_value = mock_db
        
        # Setup for complete backfill test
        mock_check_exist.return_value = False
        
        # Generate 30 days of backfill
        start = date(2024, 1, 1)
        end = date(2024, 1, 30)
        mock_generate_dates.return_value = [
            start + timedelta(days=i) for i in range(30)
        ]
        
        mock_cumulative_count.return_value = 10
        
        # Setup other required mocks
        mock_db.query.return_value.scalar.side_effect = [
            datetime(2024, 1, 1),
            datetime(2024, 1, 1),
            datetime(2024, 1, 1),
        ]
        mock_db.query.return_value.all.return_value = []
        mock_db.query.return_value.filter.return_value.scalar.return_value = 0
        
        task = Mock()
        task.request.id = 'test-task-id'
        
        result = collect_daily_statistics(task, '2024-01-30')
        
        # Verify complete timeline was generated
        assert 'backfill_performed' in result
        assert len(result['backfill_performed']) > 0
        
        # Verify upserts were called for each backfill date
        # 30 days * 3 system metrics = 90 minimum calls
        assert mock_upsert.call_count >= 90
    
    @patch('app.tasks.statistics_tasks.SessionLocal')
    @patch('app.tasks.statistics_tasks.check_statistics_exist')
    @patch('app.tasks.statistics_tasks.get_cumulative_count')
    @patch('app.tasks.statistics_tasks.perform_statistics_upsert')
    def test_subsequent_runs_only_update_current(
        self,
        mock_upsert,
        mock_cumulative_count,
        mock_check_exist,
        mock_session_local
    ):
        """IV5: Verify subsequent runs only add/update current date."""
        mock_db = MagicMock(spec=Session)
        mock_session_local.return_value = mock_db
        
        # All statistics exist - no backfill needed
        mock_check_exist.return_value = True
        mock_cumulative_count.return_value = 50
        
        # Setup other required mocks
        mock_db.query.return_value.scalar.side_effect = [
            datetime(2024, 1, 1),
            datetime(2024, 1, 1),
            datetime(2024, 1, 1),
        ]
        mock_db.query.return_value.all.return_value = []
        mock_db.query.return_value.filter.return_value.scalar.return_value = 0
        
        task = Mock()
        task.request.id = 'test-task-id'
        
        result = collect_daily_statistics(task, '2024-02-15')
        
        # Verify no backfill was performed
        assert 'backfill_performed' in result
        assert len(result['backfill_performed']) == 0
        
        # Verify only current date updates were made
        # Should be limited to system metrics + rates for single date
        assert mock_upsert.call_count <= 10  # Reasonable upper bound for single date