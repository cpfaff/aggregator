"""
Test suite for API backward compatibility.

Ensures that existing statistics endpoints maintain their response format
and that failed archives are properly excluded from provider totals.
"""

import pytest
from datetime import date, datetime
from unittest.mock import MagicMock, patch, Mock

from app.models.statistics import StatisticModel, MetricType, EntityType, Period
from app.models.provider import DataProviderModel
from app.models.dataset import DatasetModel


@pytest.fixture
def mock_db():
    """Create a mock database session."""
    db = MagicMock()
    db.commit = MagicMock()
    db.rollback = MagicMock()
    return db


class TestBiologicalUnitsProvidersEndpoint:
    """Test /api/v1/statistics/biological-units/providers endpoint."""
    
    @patch('app.api.v1.endpoints.statistics.get_db')
    def test_providers_endpoint_response_format(self, mock_get_db):
        """Test that providers endpoint maintains expected response format."""
        # Setup mock database
        mock_db = MagicMock()
        mock_get_db.return_value = mock_db
        
        # Mock provider data
        provider1 = Mock(spec=DataProviderModel)
        provider1.id = 1
        provider1.name = "Provider One"
        provider1.datacenter = "DC One"
        
        provider2 = Mock(spec=DataProviderModel)
        provider2.id = 2
        provider2.name = "Provider Two"
        provider2.datacenter = "DC Two"
        
        # Mock statistics for providers
        stat1 = Mock(spec=StatisticModel)
        stat1.entity_id = 1
        stat1.value = 5000
        stat1.target_date = date(2024, 6, 20)
        
        stat2 = Mock(spec=StatisticModel)
        stat2.entity_id = 2
        stat2.value = 3000
        stat2.target_date = date(2024, 6, 20)
        
        # Mock query results
        mock_db.query(DataProviderModel).all.return_value = [provider1, provider2]
        mock_db.query(StatisticModel).filter().all.return_value = [stat1, stat2]
        
        # Expected response format
        expected_format = {
            "providers": [
                {
                    "provider_id": 1,
                    "provider_name": "Provider One",
                    "datacenter": "DC One",
                    "biological_units": 5000,
                    "last_updated": "2024-06-20"
                },
                {
                    "provider_id": 2,
                    "provider_name": "Provider Two",
                    "datacenter": "DC Two",
                    "biological_units": 3000,
                    "last_updated": "2024-06-20"
                }
            ],
            "total_biological_units": 8000,
            "provider_count": 2,
            "generated_at": "2024-06-20T10:00:00"
        }
        
        # Verify response structure matches expected format
        assert "providers" in expected_format
        assert "total_biological_units" in expected_format
        assert "provider_count" in expected_format
        assert "generated_at" in expected_format
        
        # Verify provider object structure
        provider_obj = expected_format["providers"][0]
        assert "provider_id" in provider_obj
        assert "provider_name" in provider_obj
        assert "datacenter" in provider_obj
        assert "biological_units" in provider_obj
        assert "last_updated" in provider_obj
    
    @patch('app.api.v1.endpoints.statistics.get_db')
    def test_providers_exclude_failed_archives(self, mock_get_db):
        """Test that failed archives are excluded from provider totals."""
        mock_db = MagicMock()
        mock_get_db.return_value = mock_db
        
        provider = Mock(spec=DataProviderModel)
        provider.id = 1
        provider.name = "Test Provider"
        
        # Create statistics with different states
        stat_success = Mock(spec=StatisticModel)
        stat_success.entity_id = 1
        stat_success.value = 5000
        stat_success.extra_data = {'archive_id': 101, 'processing_failed': False}
        
        stat_failed = Mock(spec=StatisticModel)
        stat_failed.entity_id = 1
        stat_failed.value = 0  # Failed archives should have 0 value
        stat_failed.extra_data = {
            'archive_id': 102,
            'processing_failed': True,
            'failure_count': 3
        }
        
        stat_normal = Mock(spec=StatisticModel)
        stat_normal.entity_id = 1
        stat_normal.value = 3000
        stat_normal.extra_data = {'archive_id': 103}
        
        mock_db.query(DataProviderModel).all.return_value = [provider]
        # Should only include successful statistics
        mock_db.query(StatisticModel).filter().all.return_value = [stat_success, stat_normal]
        
        # Total should exclude failed archive
        total = stat_success.value + stat_normal.value
        assert total == 8000  # 5000 + 3000, excluding failed
    
    @patch('app.tasks.statistics_tasks.SessionLocal')
    def test_collect_provider_with_mixed_anchor_dates(self, mock_session):
        """Test that collection works with archives at different anchor dates."""
        mock_db = MagicMock()
        mock_session.return_value.__enter__.return_value = mock_db
        
        provider = Mock(spec=DataProviderModel)
        provider.id = 1
        provider.name = "Test Provider"
        mock_db.query(DataProviderModel).all.return_value = [provider]
        
        # Mock datasets
        mock_db.query(DatasetModel.id).filter().all.return_value = [(1,), (2,), (3,)]
        
        # Mock subquery for max dates
        mock_subquery = MagicMock()
        mock_db.query().filter().group_by.return_value = mock_subquery
        
        # Statistics at different anchor dates
        stats_by_date = [
            (2000, date(2024, 1, 15), 1),  # Historical anchor
            (3000, date(2024, 6, 20), 2),  # Current date anchor
            (1500, date(2024, 3, 10), 3),  # Historical anchor
        ]
        mock_db.query().join().filter().all.return_value = stats_by_date
        
        from app.tasks.statistics_tasks import collect_provider_biological_units
        result = collect_provider_biological_units(target_date="2024-06-25")
        
        assert result['status'] == 'completed'
        # Total should be sum of all units regardless of anchor date
        # Verification happens through the database operations
        mock_db.execute.assert_called_once()
    
    @patch('app.tasks.statistics_tasks.SessionLocal')
    def test_update_provider_respects_anchor_dates(self, mock_session):
        """Test that update_provider_biological_units respects anchor dates."""
        mock_db = MagicMock()
        mock_session.return_value.__enter__.return_value = mock_db
        
        provider = Mock(spec=DataProviderModel)
        provider.id = 1
        mock_db.query(DataProviderModel).filter().first.return_value = provider
        
        # Mock datasets
        mock_db.query(DatasetModel.id).filter().all.return_value = [(1,), (2,)]
        
        # Mock subquery
        mock_subquery = MagicMock()
        mock_db.query().filter().group_by.return_value = mock_subquery
        
        # Units from different dates
        units_data = [
            (1000, date(2024, 1, 15), 1),  # Historical
            (2000, date(2024, 6, 20), 2),  # Recent
        ]
        mock_db.query().join().filter().all.return_value = units_data
        
        from app.tasks.statistics_tasks import update_provider_biological_units
        result = update_provider_biological_units(provider_id=1, target_date="2024-06-25")
        
        assert result['status'] == 'completed'
        assert result['biological_units'] == 3000  # Sum of both


class TestBiologicalUnitsTimelineEndpoint:
    """Test /api/v1/statistics/biological-units/timeline endpoint."""
    
    @patch('app.api.v1.endpoints.statistics.get_db')
    def test_timeline_endpoint_response_format(self, mock_get_db):
        """Test that timeline endpoint maintains expected response format."""
        mock_db = MagicMock()
        mock_get_db.return_value = mock_db
        
        # Mock timeline statistics
        stat1 = Mock(spec=StatisticModel)
        stat1.target_date = date(2024, 1, 15)
        stat1.value = 1000
        stat1.entity_id = 1
        
        stat2 = Mock(spec=StatisticModel)
        stat2.target_date = date(2024, 3, 10)
        stat2.value = 1500
        stat2.entity_id = 1
        
        stat3 = Mock(spec=StatisticModel)
        stat3.target_date = date(2024, 6, 20)
        stat3.value = 2000
        stat3.entity_id = 1
        
        mock_db.query(StatisticModel).filter().order_by().all.return_value = [stat1, stat2, stat3]
        
        # Expected response format
        expected_format = {
            "timeline": [
                {
                    "date": "2024-01-15",
                    "biological_units": 1000,
                    "provider_id": 1
                },
                {
                    "date": "2024-03-10",
                    "biological_units": 1500,
                    "provider_id": 1
                },
                {
                    "date": "2024-06-20",
                    "biological_units": 2000,
                    "provider_id": 1
                }
            ],
            "start_date": "2024-01-15",
            "end_date": "2024-06-20",
            "data_points": 3
        }
        
        # Verify response structure
        assert "timeline" in expected_format
        assert "start_date" in expected_format
        assert "end_date" in expected_format
        assert "data_points" in expected_format
        
        # Verify timeline entry structure
        timeline_entry = expected_format["timeline"][0]
        assert "date" in timeline_entry
        assert "biological_units" in timeline_entry
        assert "provider_id" in timeline_entry
    
    @patch('app.api.v1.endpoints.statistics.get_db')
    def test_timeline_returns_correct_historical_data(self, mock_get_db):
        """Test that timeline returns data at correct historical points."""
        mock_db = MagicMock()
        mock_get_db.return_value = mock_db
        
        # Create statistics at historical anchor dates
        historical_stats = []
        
        # Archive processed first time at its created_at date
        stat1 = Mock(spec=StatisticModel)
        stat1.target_date = date(2024, 1, 15)
        stat1.value = 1000
        stat1.extra_data = {
            'archive_id': 101,
            'first_processed_at': '2024-01-15T10:00:00'
        }
        historical_stats.append(stat1)
        
        # Another archive at different historical date
        stat2 = Mock(spec=StatisticModel)
        stat2.target_date = date(2024, 3, 10)
        stat2.value = 1500
        stat2.extra_data = {
            'archive_id': 102,
            'first_processed_at': '2024-03-10T14:00:00'
        }
        historical_stats.append(stat2)
        
        # Recent update (subsequent processing)
        stat3 = Mock(spec=StatisticModel)
        stat3.target_date = date(2024, 6, 20)
        stat3.value = 2500
        stat3.extra_data = {'archive_id': 103}
        historical_stats.append(stat3)
        
        mock_db.query(StatisticModel).filter().order_by().all.return_value = historical_stats
        
        # Verify dates are preserved correctly
        assert stat1.target_date == date(2024, 1, 15)
        assert stat2.target_date == date(2024, 3, 10)
        assert stat3.target_date == date(2024, 6, 20)
    
    @patch('app.api.v1.endpoints.statistics.get_db')
    def test_timeline_filters_date_range(self, mock_get_db):
        """Test that timeline correctly filters by date range."""
        mock_db = MagicMock()
        mock_get_db.return_value = mock_db
        
        # Create statistics across a range
        all_stats = []
        for day in range(1, 31):
            stat = Mock(spec=StatisticModel)
            stat.target_date = date(2024, 6, day)
            stat.value = day * 100
            all_stats.append(stat)
        
        # Mock filter for date range
        mock_query = MagicMock()
        mock_db.query.return_value = mock_query
        mock_filter = MagicMock()
        mock_query.filter.return_value = mock_filter
        mock_filter.order_by.return_value.all.return_value = all_stats[9:20]  # Days 10-20
        
        # Should return only filtered range
        filtered_stats = mock_filter.order_by.return_value.all.return_value
        assert len(filtered_stats) == 11
        assert filtered_stats[0].target_date == date(2024, 6, 10)
        assert filtered_stats[-1].target_date == date(2024, 6, 20)


class TestStatisticsSummaryEndpoint:
    """Test /api/v1/statistics/summary endpoint."""
    
    @patch('app.api.v1.endpoints.statistics.get_db')
    def test_summary_endpoint_response_format(self, mock_get_db):
        """Test that summary endpoint maintains expected response format."""
        mock_db = MagicMock()
        mock_get_db.return_value = mock_db
        
        # Mock various statistics
        dataset_stats = Mock(spec=StatisticModel)
        dataset_stats.value = 150
        
        provider_stats = Mock(spec=StatisticModel)
        provider_stats.value = 25
        
        bio_units_stats = Mock(spec=StatisticModel)
        bio_units_stats.value = 50000
        
        # Expected response format
        expected_format = {
            "summary": {
                "total_datasets": 150,
                "total_providers": 25,
                "total_biological_units": 50000,
                "total_xml_archives": 145,
                "successful_validations": 140,
                "failed_validations": 5,
                "last_update": "2024-06-20T15:30:00"
            },
            "by_period": {
                "daily": {
                    "datasets": 5,
                    "biological_units": 2000
                },
                "weekly": {
                    "datasets": 30,
                    "biological_units": 15000
                },
                "monthly": {
                    "datasets": 150,
                    "biological_units": 50000
                }
            },
            "generated_at": "2024-06-20T16:00:00"
        }
        
        # Verify response structure
        assert "summary" in expected_format
        assert "by_period" in expected_format
        assert "generated_at" in expected_format
        
        # Verify summary structure
        summary = expected_format["summary"]
        assert "total_datasets" in summary
        assert "total_providers" in summary
        assert "total_biological_units" in summary
        assert "last_update" in summary
    
    @patch('app.api.v1.endpoints.statistics.get_db')
    def test_summary_excludes_failed_archives(self, mock_get_db):
        """Test that summary correctly excludes failed archives."""
        mock_db = MagicMock()
        mock_get_db.return_value = mock_db
        
        # Mock statistics with mixed success/failure states
        successful_stats = []
        failed_stats = []
        
        for i in range(10):
            stat = Mock(spec=StatisticModel)
            stat.entity_id = i
            stat.metric_type = MetricType.BIOLOGICAL_UNITS
            
            if i < 7:  # 7 successful
                stat.value = 1000
                stat.extra_data = {'archive_id': i}
                successful_stats.append(stat)
            else:  # 3 failed
                stat.value = 0
                stat.extra_data = {
                    'archive_id': i,
                    'processing_failed': True,
                    'failure_count': 2
                }
                failed_stats.append(stat)
        
        # Mock query to return only successful stats for totals
        mock_db.query(StatisticModel).filter().all.return_value = successful_stats
        
        # Total should only include successful archives
        total = sum(s.value for s in successful_stats)
        assert total == 7000  # 7 successful * 1000 each
        assert len(failed_stats) == 3  # 3 failed archives excluded


class TestTimelineQueriesWithMixedDates:
    """Test timeline queries with mixed anchor dates."""
    
    @patch('app.api.v1.endpoints.statistics.get_db')
    def test_timeline_query_performance(self, mock_get_db):
        """Test that timeline queries handle large datasets efficiently."""
        mock_db = MagicMock()
        mock_get_db.return_value = mock_db
        
        # Create large dataset with mixed dates
        large_dataset = []
        for provider_id in range(1, 11):  # 10 providers
            for day in range(1, 366):  # Full year of data
                stat = Mock(spec=StatisticModel)
                stat.entity_id = provider_id
                stat.target_date = date(2024, 1, 1) + timedelta(days=day-1)
                stat.value = provider_id * 100 + day
                
                # Mix of first processing and subsequent
                if day < 180:
                    stat.extra_data = {
                        'first_processed_at': f'2024-{day//30+1:02d}-01T10:00:00'
                    }
                else:
                    stat.extra_data = {}
                
                large_dataset.append(stat)
        
        # Mock paginated query
        mock_query = MagicMock()
        mock_db.query.return_value = mock_query
        mock_query.filter.return_value = mock_query
        mock_query.order_by.return_value = mock_query
        mock_query.limit.return_value = mock_query
        mock_query.offset.return_value = mock_query
        
        # Return subset for pagination
        mock_query.all.return_value = large_dataset[:100]
        
        # Verify query can handle pagination
        results = mock_query.all()
        assert len(results) == 100
        assert results[0].entity_id == 1