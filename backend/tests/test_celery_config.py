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

        # Check that the snapshot collection task is scheduled
        expected_tasks = [
            "collect-archive-snapshots",
        ]

        for task_name in expected_tasks:
            assert task_name in beat_schedule

    def test_task_modules_included(self):
        """Test that all task modules are included in celery app configuration."""
        # Verify the include list contains the expected task modules
        include = celery_app.conf.get("include", []) or celery_app.include or []

        expected_modules = ["app.tasks", "app.tasks.validator_tasks", "app.tasks.snapshot_tasks"]
        for module in expected_modules:
            assert module in include, f"Module '{module}' not in include list: {include}"

    def test_visibility_timeout_exceeds_longest_task_limit(self):
        """Broker visibility timeout must exceed the longest task hard limit.

        validate_archive (app/tasks/validator_tasks.py) sets
        task_time_limit=7500. With task_acks_late=True, a Redis broker
        visibility_timeout below that hard limit causes a still-running
        long task to be redelivered and re-run (RH-05, REQ-CEL-1).
        """
        assert celery_app.conf.broker_transport_options.get("visibility_timeout", 3600) > 7500

    def test_default_queue_still_works(self):
        """Test that tasks without explicit routing can still use default queue."""
        routes = celery_app.conf.task_routes

        # The configuration should only have specific routes
        # Tasks not in the routes will use the default queue
        assert len(routes) == 2  # Only our two routing rules

        # Verify that we're not blocking other tasks
        assert "some.other.task" not in routes
