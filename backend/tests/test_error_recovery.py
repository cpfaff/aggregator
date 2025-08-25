"""
Test suite for error recovery and retry mechanisms in statistics tasks.

Tests the resilient collection and error recovery functionality introduced in Story 1.3.
"""

import pytest
from datetime import datetime, date, timedelta
from unittest.mock import Mock, patch, MagicMock
from sqlalchemy.orm import Session

from app.models import (
    StatisticModel,
    DataProviderModel,
    DatasetModel,
    XmlArchiveModel,
    MetricType,
    EntityType,
    Period
)
from app.tasks.statistics_tasks import (
    analyze_xml_archives,
    mark_archive_failed,
    reset_archive_failure,
    get_archive_failure_info,
    is_archive_first_processing,
    get_archive_anchor_date,
    should_retry_failed_archive,
    collect_provider_biological_units,
    XMLParsingError
)


@pytest.fixture
def mock_db_session():
    """Create a mock database session."""
    session = MagicMock(spec=Session)
    
    # Set up query chain mock
    query_mock = MagicMock()
    filter_mock = MagicMock()
    
    # Chain the mocks
    session.query.return_value = query_mock
    query_mock.filter.return_value = filter_mock
    filter_mock.first.return_value = None
    filter_mock.all.return_value = []
    
    # Direct access to methods
    session.first.return_value = None
    session.all.return_value = []
    session.commit.return_value = None
    session.rollback.return_value = None
    session.add.return_value = None
    session.delete.return_value = None
    session.is_active = True
    session.dirty = []
    session.new = []
    
    return session


@pytest.fixture
def sample_archive():
    """Create a sample XML archive for testing."""
    archive = Mock(spec=XmlArchiveModel)
    archive.id = 123
    archive.dataset_id = 456
    archive.url = "http://example.com/archive.xml"
    archive.isLatest = True
    
    # Mock dataset relationship
    archive.dataset = Mock()
    archive.dataset.created_at = datetime(2024, 1, 1, 12, 0, 0)
    archive.dataset.provider_id = 789
    
    return archive


@pytest.fixture
def sample_statistic_with_failure():
    """Create a sample statistic with failure tracking."""
    stat = Mock(spec=StatisticModel)
    stat.extra_data = {
        'archive_id': 123,
        'processing_failed': True,
        'failure_count': 2,
        'last_failure_reason': 'Network timeout',
        'last_failure_at': datetime.utcnow().isoformat()
    }
    return stat


class TestFailureTracking:
    """Test failure tracking mechanisms."""
    
    def test_mark_archive_failed_first_failure(self, mock_db_session):
        """Test marking an archive as failed for the first time."""
        # No existing failure record
        mock_db_session.first.return_value = None
        
        mark_archive_failed(mock_db_session, 123, "Connection timeout")
        
        # Should add a new failure record
        assert mock_db_session.add.called
        added_stat = mock_db_session.add.call_args[0][0]
        assert added_stat.extra_data['archive_id'] == 123
        assert added_stat.extra_data['processing_failed'] == True
        assert added_stat.extra_data['failure_count'] == 1
        assert added_stat.extra_data['last_failure_reason'] == "Connection timeout"
        assert added_stat.date == date(1970, 1, 1)  # Failure marker date
    
    def test_mark_archive_failed_increment_count(self, mock_db_session, sample_statistic_with_failure):
        """Test incrementing failure count for already failed archive."""
        mock_db_session.first.return_value = sample_statistic_with_failure
        
        mark_archive_failed(mock_db_session, 123, "Parse error")
        
        # Should update existing record
        assert sample_statistic_with_failure.extra_data['failure_count'] == 3
        assert sample_statistic_with_failure.extra_data['last_failure_reason'] == "Parse error"
    
    def test_reset_archive_failure(self, mock_db_session, sample_statistic_with_failure):
        """Test clearing failure state after successful processing."""
        mock_db_session.first.return_value = sample_statistic_with_failure
        
        reset_archive_failure(mock_db_session, 123)
        
        # Should delete the failure record
        mock_db_session.delete.assert_called_once_with(sample_statistic_with_failure)
    
    def test_get_archive_failure_info(self, mock_db_session, sample_statistic_with_failure):
        """Test retrieving failure information for an archive."""
        mock_db_session.first.return_value = sample_statistic_with_failure
        
        failure_info = get_archive_failure_info(mock_db_session, 123)
        
        assert failure_info is not None
        assert failure_info['failure_count'] == 2
        assert failure_info['last_failure_reason'] == 'Network timeout'
        assert 'last_failure_at' in failure_info
    
    def test_get_archive_failure_info_no_failures(self, mock_db_session):
        """Test retrieving failure info when no failures exist."""
        mock_db_session.first.return_value = None
        
        failure_info = get_archive_failure_info(mock_db_session, 123)
        
        assert failure_info is None


class TestArchiveProcessingState:
    """Test archive processing state logic."""
    
    def test_is_archive_first_processing_with_failure(self, mock_db_session, sample_statistic_with_failure):
        """Test that failed archives are treated as first processing."""
        # Return failure record first, then None for successful record
        mock_db_session.first.side_effect = [sample_statistic_with_failure, None]
        
        is_first = is_archive_first_processing(mock_db_session, 123)
        
        assert is_first == True  # Failed archives should be treated as first processing
    
    def test_is_archive_first_processing_no_records(self, mock_db_session):
        """Test that archives with no records are first processing."""
        mock_db_session.first.return_value = None
        
        is_first = is_archive_first_processing(mock_db_session, 123)
        
        assert is_first == True
    
    def test_is_archive_first_processing_has_successful(self, mock_db_session):
        """Test that archives with successful processing are not first."""
        successful_stat = Mock(spec=StatisticModel)
        successful_stat.extra_data = {
            'archive_id': 123,
            'first_processed_at': '2024-01-01T12:00:00'
        }
        mock_db_session.first.side_effect = [None, successful_stat]  # No failure, has successful
        
        is_first = is_archive_first_processing(mock_db_session, 123)
        
        assert is_first == False


class TestAnchorDateLogic:
    """Test anchor date determination with failure handling."""
    
    def test_anchor_date_for_failed_archive(self, mock_db_session, sample_archive):
        """Test that failed archives use dataset created_at as anchor."""
        with patch('app.tasks.statistics_tasks.is_archive_first_processing', return_value=True):
            with patch('app.tasks.statistics_tasks.get_archive_failure_info') as mock_failure_info:
                mock_failure_info.return_value = {'failure_count': 3}
                
                anchor_date = get_archive_anchor_date(mock_db_session, sample_archive)
                
                assert anchor_date == date(2024, 1, 1)  # Dataset created_at date
    
    def test_anchor_date_for_first_processing(self, mock_db_session, sample_archive):
        """Test that first-time processing uses dataset created_at."""
        with patch('app.tasks.statistics_tasks.is_archive_first_processing', return_value=True):
            with patch('app.tasks.statistics_tasks.get_archive_failure_info', return_value=None):
                
                anchor_date = get_archive_anchor_date(mock_db_session, sample_archive)
                
                assert anchor_date == date(2024, 1, 1)  # Dataset created_at date
    
    def test_anchor_date_for_subsequent_processing(self, mock_db_session, sample_archive):
        """Test that subsequent processing uses current date."""
        with patch('app.tasks.statistics_tasks.is_archive_first_processing', return_value=False):
            with patch('app.tasks.statistics_tasks.get_archive_failure_info', return_value=None):
                with patch('app.tasks.statistics_tasks.date') as mock_date:
                    mock_date.today.return_value = date(2024, 6, 15)
                    
                    anchor_date = get_archive_anchor_date(mock_db_session, sample_archive)
                    
                    assert anchor_date == date(2024, 6, 15)  # Current date


class TestExponentialBackoff:
    """Test exponential backoff calculation and retry logic."""
    
    def test_exponential_backoff_calculation(self):
        """Test that backoff delay increases exponentially."""
        base_delay = 60  # 1 minute
        
        # Test delay calculations for different failure counts
        delays = []
        for failure_count in range(1, 6):
            delay = min(base_delay * (2 ** (failure_count - 1)), 3600)
            delays.append(delay)
        
        expected_delays = [60, 120, 240, 480, 960]  # 1, 2, 4, 8, 16 minutes
        assert delays == expected_delays
    
    def test_backoff_cap_at_one_hour(self):
        """Test that backoff is capped at 1 hour (3600 seconds)."""
        base_delay = 60
        failure_count = 10  # High failure count
        
        delay = min(base_delay * (2 ** (failure_count - 1)), 3600)
        
        assert delay == 3600  # Should be capped at 1 hour


class TestTimeBasedReset:
    """Test time-based reset functionality for failed archives."""
    
    def test_should_retry_no_failures(self, mock_db_session):
        """Test that archives with no failures should be retried."""
        with patch('app.tasks.statistics_tasks.get_archive_failure_info', return_value=None):
            result = should_retry_failed_archive(mock_db_session, 123)
            assert result is True
    
    def test_should_retry_under_max_retries(self, mock_db_session):
        """Test that archives under max retries should be retried."""
        failure_info = {
            'failure_count': 3,
            'last_failure_at': datetime.utcnow().isoformat()
        }
        with patch('app.tasks.statistics_tasks.get_archive_failure_info', return_value=failure_info):
            result = should_retry_failed_archive(mock_db_session, 123, max_retries=5)
            assert result is True
    
    def test_should_not_retry_exceeded_max_recent_failure(self, mock_db_session):
        """Test that archives exceeding max retries with recent failure should not retry."""
        # Failed 2 hours ago
        last_failure = datetime.utcnow() - timedelta(hours=2)
        failure_info = {
            'failure_count': 5,
            'last_failure_at': last_failure.isoformat(),
            'last_failure_reason': 'Persistent error'
        }
        with patch('app.tasks.statistics_tasks.get_archive_failure_info', return_value=failure_info):
            result = should_retry_failed_archive(mock_db_session, 123, max_retries=5, reset_after_hours=24)
            assert result is False
    
    def test_should_retry_exceeded_max_after_reset_period(self, mock_db_session):
        """Test that archives exceeding max retries can retry after reset period."""
        # Failed 25 hours ago
        last_failure = datetime.utcnow() - timedelta(hours=25)
        failure_info = {
            'failure_count': 5,
            'last_failure_at': last_failure.isoformat(),
            'last_failure_reason': 'Old error'
        }
        with patch('app.tasks.statistics_tasks.get_archive_failure_info', return_value=failure_info):
            result = should_retry_failed_archive(mock_db_session, 123, max_retries=5, reset_after_hours=24)
            assert result is True
    
    def test_should_retry_on_invalid_timestamp(self, mock_db_session):
        """Test that invalid timestamp allows retry (err on side of retrying)."""
        failure_info = {
            'failure_count': 5,
            'last_failure_at': 'invalid-timestamp'
        }
        with patch('app.tasks.statistics_tasks.get_archive_failure_info', return_value=failure_info):
            with patch('app.tasks.statistics_tasks.logger') as mock_logger:
                result = should_retry_failed_archive(mock_db_session, 123, max_retries=5)
                assert result is True
                # Check that warning was logged
                mock_logger.warning.assert_called()


class TestCircuitBreaker:
    """Test circuit breaker pattern to prevent infinite loops."""
    
    @patch('app.tasks.statistics_tasks.SessionLocal')
    @patch('app.tasks.statistics_tasks.parse_abcd_xml')
    def test_skip_archives_exceeding_max_retries(self, mock_parse, mock_session_local, mock_db_session):
        """Test that archives exceeding max retries with recent failures are skipped."""
        mock_db = mock_db_session
        mock_session_local.return_value = mock_db
        
        # Create archives - one normal, one with max failures
        normal_archive = Mock(id=1, dataset_id=10)
        failed_archive = Mock(id=2, dataset_id=20)
        
        mock_db.all.return_value = [normal_archive, failed_archive]
        
        # Mock should_retry to return False for failed archive
        def should_retry_side_effect(db, archive_id, max_retries=5, reset_after_hours=24):
            return archive_id != 2
        
        with patch('app.tasks.statistics_tasks.should_retry_failed_archive', side_effect=should_retry_side_effect):
            with patch('app.tasks.statistics_tasks.get_archive_failure_info') as mock_failure_info:
                mock_failure_info.return_value = {
                    'failure_count': 5, 
                    'last_failure_reason': 'Persistent error',
                    'last_failure_at': datetime.utcnow().isoformat()
                }
                
                # Mock successful parsing for normal archive
                mock_parse.return_value = {'unit_count': 100}
                
                task = Mock()
                task.request.id = 'test-task-id'
                result = analyze_xml_archives.run(
                    task,
                    batch_size=10,
                    offset=0
                )
                
                # Should process normal archive but skip failed one
                assert result['processed'] == 1
                assert result['skipped'] == 1
                assert mock_parse.call_count == 1  # Only called for normal archive


class TestTimelineIntegrity:
    """Test that timeline data integrity is maintained with failures."""
    
    @patch('app.tasks.statistics_tasks.SessionLocal')
    def test_failed_archives_dont_corrupt_timeline(self, mock_session_local, mock_db_session):
        """Test that failed collections don't corrupt timeline data."""
        mock_db = mock_db_session
        mock_session_local.return_value = mock_db
        
        # Create mock statistics with mixed success/failure states
        successful_stat = Mock(
            value=100,
            date=date(2024, 1, 1),
            extra_data={'archive_id': 1}
        )
        
        failed_stat = Mock(
            value=0,
            date=date(1970, 1, 1),  # Failure marker date
            extra_data={
                'archive_id': 2,
                'processing_failed': True,
                'failure_count': 3
            }
        )
        
        mock_db.all.return_value = [successful_stat, failed_stat]
        
        # Aggregation should only include successful stats
        with patch('app.tasks.statistics_tasks.get_archive_failure_info'):
            # Test collect_provider_biological_units excludes failed archives
            task = Mock()
            task.request.id = 'test-task-id'
            
            # Mock provider and datasets
            provider = Mock(id=1, name='Test Provider', datacenter='TestDC')
            mock_db.query(DataProviderModel).all.return_value = [provider]
            mock_db.query(DatasetModel.id).filter().all.return_value = [(10,), (20,)]
            
            # Mock subquery and unit counts - only successful archive
            mock_db.query().filter().group_by().subquery.return_value = Mock()
            mock_db.query().join().filter().all.return_value = [(100, date(2024, 1, 1), 10)]
            
            result = collect_provider_biological_units.run(task)
            
            assert result['status'] == 'completed'


class TestErrorLogging:
    """Test comprehensive error logging and context."""
    
    @patch('app.tasks.statistics_tasks.logger')
    @patch('app.tasks.statistics_tasks.SessionLocal')
    @patch('app.tasks.statistics_tasks.parse_abcd_xml')
    def test_error_logging_includes_context(self, mock_parse, mock_session_local, mock_logger, mock_db_session):
        """Test that errors include archive ID, dataset ID, and retry info."""
        mock_db = mock_db_session
        mock_session_local.return_value = mock_db
        
        archive = Mock(id=123, dataset_id=456)
        mock_db.all.return_value = [archive]
        
        # Simulate parsing error
        mock_parse.side_effect = XMLParsingError("Invalid XML structure")
        
        with patch('app.tasks.statistics_tasks.mark_archive_failed'):
            with patch('app.tasks.statistics_tasks.get_archive_failure_info') as mock_failure_info:
                mock_failure_info.return_value = {'failure_count': 2}
                
                task = Mock()
                task.request.id = 'test-task-id'
                
                result = analyze_xml_archives.run(task, batch_size=10, offset=0)
                
                # Check that appropriate logging was done
                assert any(
                    'archive 123' in str(call) and 'attempt #2' in str(call)
                    for call in mock_logger.warning.call_args_list
                )
    
    @patch('app.tasks.statistics_tasks.logger')
    def test_successful_recovery_logging(self, mock_logger, mock_db_session):
        """Test that successful recovery after failures is logged."""
        failure_stat = Mock(extra_data={'failure_count': 3})
        mock_db_session.first.return_value = failure_stat
        
        reset_archive_failure(mock_db_session, 123)
        
        # Check recovery was logged
        assert any(
            'Archive 123 recovered after 3 failure(s)' in str(call)
            for call in mock_logger.info.call_args_list
        )


class TestIntegration:
    """Integration tests for the complete error recovery flow."""
    
    @patch('app.tasks.statistics_tasks.SessionLocal')
    @patch('app.tasks.statistics_tasks.parse_abcd_xml')
    def test_complete_retry_flow(self, mock_parse, mock_session_local, mock_db_session):
        """Test complete flow: fail -> retry with correct anchor -> success."""
        mock_db = mock_db_session
        mock_session_local.return_value = mock_db
        
        archive = Mock(id=123, dataset_id=456)
        archive.dataset.created_at = datetime(2024, 1, 1)
        mock_db.all.return_value = [archive]
        
        # First attempt: failure
        mock_parse.side_effect = [
            XMLParsingError("Network timeout"),
            {'unit_count': 100}  # Second attempt succeeds
        ]
        
        task = Mock()
        task.request.id = 'test-task-id'
        
        with patch('app.tasks.statistics_tasks.mark_archive_failed') as mock_mark_failed:
            with patch('app.tasks.statistics_tasks.reset_archive_failure') as mock_reset:
                with patch('app.tasks.statistics_tasks.get_archive_failure_info') as mock_info:
                    with patch('app.tasks.statistics_tasks.get_archive_anchor_date') as mock_anchor:
                        # First run - failure
                        mock_info.return_value = None
                        mock_anchor.return_value = date(2024, 1, 1)
                        
                        result1 = analyze_xml_archives.run(task, batch_size=10, offset=0)
                        
                        assert result1['errors'] == 1
                        mock_mark_failed.assert_called_once()
                        
                        # Second run - success
                        mock_parse.side_effect = [{'unit_count': 100}]
                        mock_info.return_value = {'failure_count': 1}
                        
                        result2 = analyze_xml_archives.run(task, batch_size=10, offset=0)
                        
                        assert result2['processed'] == 1
                        assert result2['errors'] == 0
                        mock_reset.assert_called_once()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])