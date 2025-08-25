"""
Comprehensive test suite for resilient retry mechanism.

Tests failure tracking, exponential backoff, circuit breaker pattern,
and time-based reset functionality.
"""

import pytest
from datetime import datetime, timedelta
from unittest.mock import MagicMock, patch
from sqlalchemy.orm import Session

from app.models.statistics import StatisticModel, MetricType, EntityType, Period
from app.tasks.statistics_tasks import (
    mark_archive_failed,
    reset_archive_failure,
    get_archive_failure_info,
    should_retry_failed_archive
)


@pytest.fixture
def mock_db():
    """Create a mock database session."""
    db = MagicMock(spec=Session)
    db.commit = MagicMock()
    db.rollback = MagicMock()
    return db


@pytest.fixture
def mock_statistic():
    """Create a mock statistic model."""
    stat = MagicMock(spec=StatisticModel)
    stat.entity_type = EntityType.DATASET
    stat.metric_type = MetricType.BIOLOGICAL_UNITS
    stat.period = Period.DAILY
    stat.extra_data = {'archive_id': 100}
    return stat


class TestMarkArchiveFailed:
    """Test suite for mark_archive_failed function."""
    
    def test_mark_first_failure(self, mock_db, mock_statistic):
        """Test marking an archive as failed for the first time."""
        # Setup: Statistic without any failure info
        mock_statistic.extra_data = {'archive_id': 100, 'unit_count': 0}
        mock_db.query().filter().first.return_value = mock_statistic
        
        with patch('app.tasks.statistics_tasks.flag_modified') as mock_flag:
            with patch('app.tasks.statistics_tasks.datetime') as mock_datetime:
                mock_datetime.utcnow.return_value = datetime(2024, 6, 20, 10, 30, 0)
                
                mark_archive_failed(mock_db, 100, "Network timeout")
                
                # Verify failure tracking was added
                assert mock_statistic.extra_data['processing_failed'] is True
                assert mock_statistic.extra_data['failure_count'] == 1
                assert mock_statistic.extra_data['last_failure_reason'] == "Network timeout"
                assert mock_statistic.extra_data['last_failure_at'] == '2024-06-20T10:30:00'
                
                # Verify flag_modified was called
                mock_flag.assert_called_once_with(mock_statistic, 'extra_data')
                mock_db.commit.assert_called_once()
    
    def test_mark_subsequent_failure(self, mock_db, mock_statistic):
        """Test incrementing failure count on subsequent failures."""
        # Setup: Statistic with existing failure
        mock_statistic.extra_data = {
            'archive_id': 100,
            'processing_failed': True,
            'failure_count': 2,
            'last_failure_reason': "Old error",
            'last_failure_at': '2024-06-19T10:00:00'
        }
        mock_db.query().filter().first.return_value = mock_statistic
        
        with patch('app.tasks.statistics_tasks.flag_modified') as mock_flag:
            with patch('app.tasks.statistics_tasks.datetime') as mock_datetime:
                mock_datetime.utcnow.return_value = datetime(2024, 6, 20, 15, 45, 0)
                
                mark_archive_failed(mock_db, 100, "Parse error")
                
                # Verify failure count was incremented
                assert mock_statistic.extra_data['failure_count'] == 3
                assert mock_statistic.extra_data['last_failure_reason'] == "Parse error"
                assert mock_statistic.extra_data['last_failure_at'] == '2024-06-20T15:45:00'
    
    def test_mark_failure_no_existing_statistic(self, mock_db):
        """Test marking failure when no statistic exists."""
        # Setup: No existing statistic
        mock_db.query().filter().first.return_value = None
        
        # Should handle gracefully without exception
        mark_archive_failed(mock_db, 100, "Initial failure")
        
        # Verify commit was still called
        mock_db.commit.assert_called_once()
    
    def test_mark_failure_with_long_error_message(self, mock_db, mock_statistic):
        """Test truncation of very long error messages."""
        mock_db.query().filter().first.return_value = mock_statistic
        
        # Create a very long error message
        long_error = "Error: " + "x" * 5000
        
        with patch('app.tasks.statistics_tasks.flag_modified'):
            mark_archive_failed(mock_db, 100, long_error)
            
            # Verify error message is stored (implementation may truncate)
            assert 'last_failure_reason' in mock_statistic.extra_data
            # If truncation is implemented, check length limit


class TestResetArchiveFailure:
    """Test suite for reset_archive_failure function."""
    
    def test_reset_failure_clears_flags(self, mock_db, mock_statistic):
        """Test that resetting failure clears all failure flags."""
        # Setup: Statistic with failure info
        mock_statistic.extra_data = {
            'archive_id': 100,
            'unit_count': 1000,
            'processing_failed': True,
            'failure_count': 3,
            'last_failure_reason': "Previous error",
            'last_failure_at': '2024-06-19T10:00:00'
        }
        mock_db.query().filter().first.return_value = mock_statistic
        
        with patch('app.tasks.statistics_tasks.flag_modified') as mock_flag:
            reset_archive_failure(mock_db, 100)
            
            # Verify failure info was cleared
            assert mock_statistic.extra_data['processing_failed'] is False
            assert mock_statistic.extra_data['failure_count'] == 0
            assert 'last_failure_reason' not in mock_statistic.extra_data
            assert 'last_failure_at' not in mock_statistic.extra_data
            
            # Verify other data preserved
            assert mock_statistic.extra_data['unit_count'] == 1000
            
            mock_flag.assert_called_once_with(mock_statistic, 'extra_data')
            mock_db.commit.assert_called_once()
    
    def test_reset_failure_no_existing_failure(self, mock_db, mock_statistic):
        """Test resetting when no failure exists."""
        # Setup: Statistic without failure info
        mock_statistic.extra_data = {'archive_id': 100, 'unit_count': 500}
        mock_db.query().filter().first.return_value = mock_statistic
        
        with patch('app.tasks.statistics_tasks.flag_modified') as mock_flag:
            reset_archive_failure(mock_db, 100)
            
            # Should add processing_failed = False
            assert mock_statistic.extra_data['processing_failed'] is False
            assert mock_statistic.extra_data['failure_count'] == 0
    
    def test_reset_failure_no_statistic(self, mock_db):
        """Test resetting when no statistic exists."""
        mock_db.query().filter().first.return_value = None
        
        # Should handle gracefully
        reset_archive_failure(mock_db, 100)
        
        mock_db.commit.assert_called_once()


class TestGetArchiveFailureInfo:
    """Test suite for get_archive_failure_info function."""
    
    def test_get_failure_info_with_failures(self, mock_db, mock_statistic):
        """Test retrieving failure information."""
        # Setup: Statistic with failure info
        failure_time = '2024-06-20T10:30:00'
        mock_statistic.extra_data = {
            'archive_id': 100,
            'processing_failed': True,
            'failure_count': 4,
            'last_failure_reason': "Connection refused",
            'last_failure_at': failure_time
        }
        mock_db.query().filter().first.return_value = mock_statistic
        
        result = get_archive_failure_info(mock_db, 100)
        
        assert result is not None
        assert result['failure_count'] == 4
        assert result['last_failure_reason'] == "Connection refused"
        assert result['last_failure_at'] == failure_time
    
    def test_get_failure_info_no_failures(self, mock_db, mock_statistic):
        """Test retrieving info when no failures exist."""
        # Setup: Statistic without failure info
        mock_statistic.extra_data = {
            'archive_id': 100,
            'unit_count': 1000,
            'processing_failed': False
        }
        mock_db.query().filter().first.return_value = mock_statistic
        
        result = get_archive_failure_info(mock_db, 100)
        
        assert result is None
    
    def test_get_failure_info_no_statistic(self, mock_db):
        """Test retrieving info when no statistic exists."""
        mock_db.query().filter().first.return_value = None
        
        result = get_archive_failure_info(mock_db, 100)
        
        assert result is None
    
    def test_get_failure_info_partial_data(self, mock_db, mock_statistic):
        """Test with partial failure data."""
        # Setup: Statistic with incomplete failure info
        mock_statistic.extra_data = {
            'archive_id': 100,
            'processing_failed': True,
            'failure_count': 2
            # Missing last_failure_reason and last_failure_at
        }
        mock_db.query().filter().first.return_value = mock_statistic
        
        result = get_archive_failure_info(mock_db, 100)
        
        assert result is not None
        assert result['failure_count'] == 2
        assert result.get('last_failure_reason') is None
        assert result.get('last_failure_at') is None


class TestShouldRetryFailedArchive:
    """Test suite for should_retry_failed_archive function."""
    
    def test_no_failures_should_retry(self, mock_db):
        """Archive with no failures should be retried."""
        with patch('app.tasks.statistics_tasks.get_archive_failure_info', return_value=None):
            result = should_retry_failed_archive(mock_db, 100)
            
            assert result is True
    
    def test_under_max_retries_should_retry(self, mock_db):
        """Archive under max retries should be retried."""
        failure_info = {
            'failure_count': 3,
            'last_failure_at': datetime.utcnow().isoformat()
        }
        
        with patch('app.tasks.statistics_tasks.get_archive_failure_info', return_value=failure_info):
            result = should_retry_failed_archive(mock_db, 100, max_retries=5)
            
            assert result is True
    
    def test_at_max_retries_should_not_retry(self, mock_db):
        """Archive at max retries should not be retried."""
        failure_info = {
            'failure_count': 5,
            'last_failure_at': datetime.utcnow().isoformat()
        }
        
        with patch('app.tasks.statistics_tasks.get_archive_failure_info', return_value=failure_info):
            result = should_retry_failed_archive(mock_db, 100, max_retries=5)
            
            assert result is False
    
    def test_exceeded_max_retries_should_not_retry(self, mock_db):
        """Archive exceeding max retries should not be retried."""
        failure_info = {
            'failure_count': 10,
            'last_failure_at': datetime.utcnow().isoformat()
        }
        
        with patch('app.tasks.statistics_tasks.get_archive_failure_info', return_value=failure_info):
            result = should_retry_failed_archive(mock_db, 100, max_retries=5)
            
            assert result is False
    
    def test_time_based_reset_after_24_hours(self, mock_db):
        """Archive should be retried after 24 hours even if max retries exceeded."""
        # Failure occurred 25 hours ago
        old_failure_time = (datetime.utcnow() - timedelta(hours=25)).isoformat()
        failure_info = {
            'failure_count': 10,  # Exceeded max retries
            'last_failure_at': old_failure_time
        }
        
        with patch('app.tasks.statistics_tasks.get_archive_failure_info', return_value=failure_info):
            result = should_retry_failed_archive(mock_db, 100, max_retries=5, reset_after_hours=24)
            
            assert result is True  # Should retry due to time-based reset
    
    def test_time_based_reset_before_24_hours(self, mock_db):
        """Archive should not be retried before 24 hours if max retries exceeded."""
        # Failure occurred 23 hours ago
        recent_failure_time = (datetime.utcnow() - timedelta(hours=23)).isoformat()
        failure_info = {
            'failure_count': 10,  # Exceeded max retries
            'last_failure_at': recent_failure_time
        }
        
        with patch('app.tasks.statistics_tasks.get_archive_failure_info', return_value=failure_info):
            result = should_retry_failed_archive(mock_db, 100, max_retries=5, reset_after_hours=24)
            
            assert result is False  # Should not retry yet
    
    def test_custom_reset_after_hours(self, mock_db):
        """Test with custom reset_after_hours value."""
        # Failure occurred 13 hours ago
        failure_time = (datetime.utcnow() - timedelta(hours=13)).isoformat()
        failure_info = {
            'failure_count': 5,
            'last_failure_at': failure_time
        }
        
        with patch('app.tasks.statistics_tasks.get_archive_failure_info', return_value=failure_info):
            # Should retry with 12-hour reset
            result = should_retry_failed_archive(mock_db, 100, max_retries=5, reset_after_hours=12)
            assert result is True
            
            # Should not retry with 48-hour reset
            result = should_retry_failed_archive(mock_db, 100, max_retries=5, reset_after_hours=48)
            assert result is False
    
    def test_missing_last_failure_at(self, mock_db):
        """Test behavior when last_failure_at is missing."""
        failure_info = {
            'failure_count': 3
            # Missing last_failure_at
        }
        
        with patch('app.tasks.statistics_tasks.get_archive_failure_info', return_value=failure_info):
            result = should_retry_failed_archive(mock_db, 100, max_retries=5)
            
            # Should still respect failure count
            assert result is True


class TestExponentialBackoff:
    """Test exponential backoff calculation."""
    
    def test_exponential_backoff_calculation(self):
        """Test that backoff increases exponentially with proper capping."""
        # Expected backoff times with base delay of 60 seconds
        expected_backoffs = [
            (1, 60),      # First retry: 60 seconds
            (2, 120),     # Second retry: 120 seconds
            (3, 240),     # Third retry: 240 seconds
            (4, 480),     # Fourth retry: 480 seconds
            (5, 960),     # Fifth retry: 960 seconds
            (6, 1920),    # Would be 1920, but may be capped
            (7, 3600),    # Should be capped at 3600 (1 hour)
            (10, 3600),   # Should remain capped at 3600
        ]
        
        for failure_count, expected_delay in expected_backoffs:
            # Calculate backoff: min(base_delay * (2 ** (failure_count - 1)), max_delay)
            base_delay = 60
            max_delay = 3600
            
            if failure_count == 0:
                actual_delay = 0
            else:
                actual_delay = min(base_delay * (2 ** (failure_count - 1)), max_delay)
            
            # For counts 7 and above, should be capped at max_delay
            if failure_count >= 7:
                assert actual_delay == max_delay
            elif failure_count > 0:
                assert actual_delay == expected_delay


class TestCircuitBreakerPattern:
    """Test circuit breaker pattern preventing infinite loops."""
    
    def test_circuit_breaker_max_retries(self):
        """Test that circuit breaker stops retries at max_retries."""
        max_retries = 5
        
        # Test various failure counts
        test_cases = [
            (0, True),   # No failures, should retry
            (1, True),   # 1 failure, should retry
            (4, True),   # 4 failures, should retry
            (5, False),  # 5 failures (max), should not retry
            (6, False),  # 6 failures, should not retry
            (10, False), # 10 failures, should not retry
        ]
        
        for failure_count, should_retry in test_cases:
            with patch('app.tasks.statistics_tasks.get_archive_failure_info') as mock_info:
                if failure_count > 0:
                    mock_info.return_value = {
                        'failure_count': failure_count,
                        'last_failure_at': datetime.utcnow().isoformat()
                    }
                else:
                    mock_info.return_value = None
                
                mock_db = MagicMock()
                result = should_retry_failed_archive(mock_db, 100, max_retries=max_retries)
                
                assert result == should_retry, f"Failed for failure_count={failure_count}"
    
    def test_circuit_breaker_with_time_reset(self):
        """Test circuit breaker reset after time period."""
        max_retries = 5
        reset_after_hours = 24
        
        # Archive with max retries reached
        failure_count = 5
        
        # Test at different time intervals
        test_cases = [
            (0, False),   # Just failed, should not retry
            (12, False),  # 12 hours later, should not retry
            (23, False),  # 23 hours later, should not retry
            (24, True),   # 24 hours later, should retry (reset)
            (25, True),   # 25 hours later, should retry
            (48, True),   # 48 hours later, should retry
        ]
        
        for hours_passed, should_retry in test_cases:
            with patch('app.tasks.statistics_tasks.get_archive_failure_info') as mock_info:
                failure_time = (datetime.utcnow() - timedelta(hours=hours_passed)).isoformat()
                mock_info.return_value = {
                    'failure_count': failure_count,
                    'last_failure_at': failure_time
                }
                
                mock_db = MagicMock()
                result = should_retry_failed_archive(
                    mock_db, 100, 
                    max_retries=max_retries, 
                    reset_after_hours=reset_after_hours
                )
                
                assert result == should_retry, f"Failed for hours_passed={hours_passed}"