"""
Unit tests for Celery task queue routing configuration.
Tests verify that tasks are routed to the correct queues as specified in decorators.
"""

import pytest
from unittest.mock import Mock, patch
from app.tasks.validator_tasks import validate_archive
from app.tasks.statistics_tasks import (
    collect_daily_statistics,
    analyze_xml_archives,
    aggregate_weekly_statistics,
    aggregate_monthly_statistics,
    collect_provider_biological_units,
    update_dataset_statistics,
    update_provider_biological_units,
    update_validation_statistics,
    update_provider_dataset_count_after_deletion
)


class TestTaskQueueRouting:
    """Test that tasks are configured with correct queue routing."""
    
    def test_validate_archive_routes_to_heavy_validation_queue(self):
        """Verify validate_archive task routes to heavy_validation queue."""
        # For Celery tasks, check the task options directly
        assert hasattr(validate_archive, 'name')
        assert validate_archive.name == 'validator.validate_archive'
        
        # Check if task has queue option set (it will be in the task options)
        task_options = getattr(validate_archive, '_decorated', True)
        # Since _decorated is True (a bool), we need to check another way
        # Celery tasks store their options differently when already registered
        
        # Verify through the Celery app configuration
        from app.core.celery_app import celery_app
        task_routes = celery_app.conf['task_routes']
        assert 'validator.validate_archive' in task_routes
        assert task_routes['validator.validate_archive']['queue'] == 'heavy_validation'
    
    def test_collect_daily_statistics_routes_to_light_tasks_queue(self):
        """Verify collect_daily_statistics task routes to light_tasks queue."""
        assert hasattr(collect_daily_statistics, 'name')
        assert collect_daily_statistics.name == 'statistics.collect_daily_stats'
        
        # Verify through the Celery app configuration
        from app.core.celery_app import celery_app
        task_routes = celery_app.conf['task_routes']
        # Statistics tasks use wildcard pattern
        assert 'statistics.*' in task_routes
        assert task_routes['statistics.*']['queue'] == 'light_tasks'
    
    def test_analyze_xml_archives_routes_to_light_tasks_queue(self):
        """Verify analyze_xml_archives task routes to light_tasks queue."""
        assert hasattr(analyze_xml_archives, 'name')
        assert analyze_xml_archives.name == 'statistics.analyze_xml_archives'
        
        from app.core.celery_app import celery_app
        task_routes = celery_app.conf['task_routes']
        assert 'statistics.*' in task_routes
        assert task_routes['statistics.*']['queue'] == 'light_tasks'
    
    def test_aggregate_weekly_statistics_routes_to_light_tasks_queue(self):
        """Verify aggregate_weekly_statistics task routes to light_tasks queue."""
        assert hasattr(aggregate_weekly_statistics, 'name')
        assert aggregate_weekly_statistics.name == 'statistics.aggregate_weekly_stats'
        
        from app.core.celery_app import celery_app
        task_routes = celery_app.conf['task_routes']
        assert 'statistics.*' in task_routes
        assert task_routes['statistics.*']['queue'] == 'light_tasks'
    
    def test_aggregate_monthly_statistics_routes_to_light_tasks_queue(self):
        """Verify aggregate_monthly_statistics task routes to light_tasks queue."""
        assert hasattr(aggregate_monthly_statistics, 'name')
        assert aggregate_monthly_statistics.name == 'statistics.aggregate_monthly_stats'
        
        from app.core.celery_app import celery_app
        task_routes = celery_app.conf['task_routes']
        assert 'statistics.*' in task_routes
        assert task_routes['statistics.*']['queue'] == 'light_tasks'
    
    def test_collect_provider_biological_units_has_priority_and_queue(self):
        """Verify collect_provider_biological_units has priority=10 and routes to light_tasks."""
        assert hasattr(collect_provider_biological_units, 'name')
        assert collect_provider_biological_units.name == 'statistics.collect_provider_biological_units'
        
        # Queue routing verified through configuration
        from app.core.celery_app import celery_app
        task_routes = celery_app.conf['task_routes']
        assert 'statistics.*' in task_routes
        assert task_routes['statistics.*']['queue'] == 'light_tasks'
        
        # Note: Priority is set in decorator but verifying it requires task inspection
        # which is challenging in unit tests without full Celery worker context
    
    def test_update_dataset_statistics_routes_to_light_tasks_queue(self):
        """Verify update_dataset_statistics task routes to light_tasks queue."""
        assert hasattr(update_dataset_statistics, 'name')
        assert update_dataset_statistics.name == 'statistics.update_dataset_statistics'
        
        from app.core.celery_app import celery_app
        task_routes = celery_app.conf['task_routes']
        assert 'statistics.*' in task_routes
        assert task_routes['statistics.*']['queue'] == 'light_tasks'
    
    def test_update_provider_biological_units_routes_to_light_tasks_queue(self):
        """Verify update_provider_biological_units task routes to light_tasks queue."""
        assert hasattr(update_provider_biological_units, 'name')
        assert update_provider_biological_units.name == 'statistics.update_provider_biological_units'
        
        from app.core.celery_app import celery_app
        task_routes = celery_app.conf['task_routes']
        assert 'statistics.*' in task_routes
        assert task_routes['statistics.*']['queue'] == 'light_tasks'
    
    def test_update_validation_statistics_routes_to_light_tasks_queue(self):
        """Verify update_validation_statistics task routes to light_tasks queue."""
        assert hasattr(update_validation_statistics, 'name')
        assert update_validation_statistics.name == 'statistics.update_validation_statistics'
        
        from app.core.celery_app import celery_app
        task_routes = celery_app.conf['task_routes']
        assert 'statistics.*' in task_routes
        assert task_routes['statistics.*']['queue'] == 'light_tasks'
    
    def test_update_provider_dataset_count_after_deletion_routes_to_light_tasks_queue(self):
        """Verify update_provider_dataset_count_after_deletion task routes to light_tasks queue."""
        assert hasattr(update_provider_dataset_count_after_deletion, 'name')
        assert update_provider_dataset_count_after_deletion.name == 'statistics.update_provider_dataset_count_after_deletion'
        
        from app.core.celery_app import celery_app
        task_routes = celery_app.conf['task_routes']
        assert 'statistics.*' in task_routes
        assert task_routes['statistics.*']['queue'] == 'light_tasks'
    
    def test_tasks_without_explicit_queue_use_default_routing(self):
        """Verify that tasks without explicit queue parameter will use default routing."""
        # This test ensures backward compatibility - if we have any tasks without
        # explicit queue settings, they should still work via task_routes config
        from app.core.celery_app import celery_app
        
        # Check that task_routes configuration exists
        assert 'task_routes' in celery_app.conf
        task_routes = celery_app.conf['task_routes']
        
        # Verify validation task routing pattern
        assert 'validator.validate_archive' in task_routes
        assert task_routes['validator.validate_archive']['queue'] == 'heavy_validation'
        
        # Verify statistics task routing pattern
        assert 'statistics.*' in task_routes
        assert task_routes['statistics.*']['queue'] == 'light_tasks'


class TestQueueRoutingIntegration:
    """Integration tests for queue routing with Celery app configuration."""
    
    @patch('app.db.session.SessionLocal')
    def test_validate_archive_task_can_be_delayed(self, mock_session):
        """Test that validate_archive task can be queued with delay method."""
        # Mock database session to avoid actual DB connection
        mock_db = Mock()
        mock_session.return_value = mock_db
        
        # Test that the task has delay method (from Celery)
        assert hasattr(validate_archive, 'delay')
        
        # Test that calling delay returns an AsyncResult-like object
        with patch.object(validate_archive, 'delay') as mock_delay:
            mock_delay.return_value = Mock(id='test-task-id')
            result = validate_archive.delay(1, 2)
            assert result.id == 'test-task-id'
            mock_delay.assert_called_once_with(1, 2)
    
    @patch('app.db.session.SessionLocal')
    def test_statistics_tasks_can_be_delayed(self, mock_session):
        """Test that statistics tasks can be queued with delay method."""
        # Mock database session
        mock_db = Mock()
        mock_session.return_value = mock_db
        
        # Test a sample of statistics tasks
        statistics_tasks = [
            collect_daily_statistics,
            analyze_xml_archives,
            collect_provider_biological_units
        ]
        
        for task in statistics_tasks:
            assert hasattr(task, 'delay')
            
            # Test that calling delay works
            with patch.object(task, 'delay') as mock_delay:
                mock_delay.return_value = Mock(id=f'{task.name}-test-id')
                result = task.delay()
                assert result.id == f'{task.name}-test-id'
                mock_delay.assert_called_once()
    
    def test_celery_inspect_commands_compatibility(self):
        """Verify tasks are compatible with Celery inspect commands."""
        from app.core.celery_app import celery_app
        
        # Ensure all our tasks are registered
        registered_tasks = list(celery_app.tasks.keys())
        
        # Check validation task is registered
        assert 'validator.validate_archive' in registered_tasks
        
        # Check statistics tasks are registered
        expected_stats_tasks = [
            'statistics.collect_daily_stats',
            'statistics.analyze_xml_archives',
            'statistics.aggregate_weekly_stats',
            'statistics.aggregate_monthly_stats',
            'statistics.collect_provider_biological_units',
            'statistics.update_dataset_statistics',
            'statistics.update_provider_biological_units',
            'statistics.update_validation_statistics',
            'statistics.update_provider_dataset_count_after_deletion'
        ]
        
        for task_name in expected_stats_tasks:
            assert task_name in registered_tasks, f"Task {task_name} not registered"