from app.core.celery_app import celery_app


class TestCeleryConfiguration:
    """Test suite for Celery queue configuration."""

    def test_queue_routing_configuration_exists(self):
        """Test that queue routing configuration is defined."""
        assert hasattr(celery_app.conf, "task_routes")
        assert celery_app.conf.task_routes is not None

    def test_validation_queue_routing(self):
        """Test that validation tasks are routed to heavy_validation queue."""
        routes = celery_app.conf.task_routes
        assert "validator.validate_archive" in routes
        assert routes["validator.validate_archive"]["queue"] == "heavy_validation"

    def test_statistics_queue_routing(self):
        """Test that statistics tasks are routed to light_tasks queue."""
        routes = celery_app.conf.task_routes
        assert "statistics.*" in routes
        assert routes["statistics.*"]["queue"] == "light_tasks"

    def test_backward_compatibility_preserved(self):
        """Test that existing Celery configuration is preserved."""
        # Check that essential configuration is still present
        assert celery_app.conf.task_serializer == "json"
        assert celery_app.conf.accept_content == ["json"]
        assert celery_app.conf.result_serializer == "json"
        assert celery_app.conf.timezone == "UTC"
        assert celery_app.conf.enable_utc is True
        assert celery_app.conf.task_track_started is True
        assert celery_app.conf.worker_prefetch_multiplier == 1
        assert celery_app.conf.task_acks_late is True

    def test_beat_schedule_preserved(self):
        """Test that beat schedule configuration is preserved."""
        beat_schedule = celery_app.conf.beat_schedule

        # Check that all scheduled tasks are still present
        expected_tasks = [
            "collect-daily-statistics",
            "aggregate-weekly-statistics",
            "aggregate-monthly-statistics",
            "analyze-xml-archives",
            "collect-provider-biological-units",
        ]

        for task_name in expected_tasks:
            assert task_name in beat_schedule

    def test_task_modules_included(self):
        """Test that all task modules are included."""
        # Get the include configuration from Celery app
        # Note: The include list is passed during app initialization
        # We can verify the tasks are registered by checking the registry
        from celery import current_app

        # These should be registered tasks
        expected_task_prefixes = ["validator", "statistics"]
        registered_tasks = list(current_app.tasks.keys())

        for prefix in expected_task_prefixes:
            matching_tasks = [t for t in registered_tasks if t.startswith(prefix)]
            assert len(matching_tasks) > 0, f"No tasks found with prefix '{prefix}'"

    def test_default_queue_still_works(self):
        """Test that tasks without explicit routing can still use default queue."""
        routes = celery_app.conf.task_routes

        # The configuration should only have specific routes
        # Tasks not in the routes will use the default queue
        assert len(routes) == 2  # Only our two routing rules

        # Verify that we're not blocking other tasks
        assert "some.other.task" not in routes
