import logging

from celery import Celery

from app.core.config import settings
from app.core.resource_allocation import get_stats_worker_concurrency, get_validator_cpu_count

logger = logging.getLogger(__name__)

# Calculate resource allocation
validator_cpus = get_validator_cpu_count(settings.VALIDATOR_CPU_PERCENT)
stats_concurrency = get_stats_worker_concurrency(settings.STATS_WORKER_CONCURRENCY, validator_cpus)

# Log calculated values at startup
logger.info("=" * 60)
logger.info("Celery Worker Resource Allocation")
logger.info(f"Total CPUs detected: {__import__('multiprocessing').cpu_count()}")
logger.info(
    f"Validator CPU allocation: {validator_cpus} CPUs ({settings.VALIDATOR_CPU_PERCENT}% requested)"
)
logger.info(
    f"Statistics worker concurrency: {stats_concurrency} (setting: {settings.STATS_WORKER_CONCURRENCY})"
)
logger.info("=" * 60)

# Create Celery instance
celery_app = Celery(
    "fastapi_celery",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND,
    include=["app.tasks", "app.tasks.validator_tasks", "app.tasks.snapshot_tasks"],
)

# Queue definitions
celery_app.conf.task_routes = {
    # Validation tasks go to heavy_validation queue
    "validator.validate_archive": {"queue": "heavy_validation"},
    # Tasks without explicit queue specification will use default queue
    # maintaining backward compatibility.
    #
    # NOTE: there is intentionally NO "statistics.*" route here (REQ-SH-DEAD-1 / F-F).
    # It was dead config left from the removed statistics_tasks module — no task uses
    # a "statistics." namespace. The real snapshot tasks are
    # snapshots.collect_archive_snapshots / .collect_single_archive_snapshot, already
    # pinned to light_tasks at the @shared_task decorator.
}

# Optional configuration
celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    worker_prefetch_multiplier=1,  # Good practice for fairness in task processing
    task_acks_late=True,  # Only acknowledge tasks after they are completed
    # Broker visibility timeout MUST exceed the longest task hard limit, else a
    # still-running long task is redelivered and re-run. validate_archive's
    # task_time_limit is 7500s; 8100 keeps a margin above it. Keep these in sync.
    broker_transport_options={"visibility_timeout": 8100},
    worker_concurrency=stats_concurrency,  # Apply calculated concurrency
    task_reject_on_worker_lost=True,  # Reject tasks when worker is lost
    task_ignore_result=False,  # Store task results for monitoring
    result_expires=3600,  # Results expire after 1 hour to prevent memory leak
    # Task time limits (global defaults, can be overridden per task)
    task_time_limit=7200,  # Hard time limit of 2 hours
    task_soft_time_limit=7000,  # Soft time limit slightly less than hard limit
    # Note: there is intentionally NO `task_dead_letter_queue_config` here. That
    # key is not a real Celery setting — it was stored inertly and did nothing
    # (RH-07 / REQ-CEL-2b). The durable dead-letter sink is implemented in
    # app/core/task_base.py: LoggingTask.on_failure persists the give-up payload
    # to the `failed_tasks` table, and task_base.redrive re-submits it.
)

# Periodic tasks schedule - simplified to single snapshot collection
from celery.schedules import crontab  # noqa: E402

celery_app.conf.beat_schedule = {
    # Archive snapshot collection - runs daily at 2:00 AM to capture unit counts
    # This single task replaces all the complex statistics tasks
    "collect-archive-snapshots": {
        "task": "snapshots.collect_archive_snapshots",
        "schedule": crontab(hour=2, minute=0),  # Daily at 2:00 AM
        "options": {"expires": 10800},  # Task expires after 3 hours
    },
}
