from celery import Celery
from app.core.config import settings
from app.core.resource_allocation import (
    get_validator_cpu_count,
    get_stats_worker_concurrency
)
import logging

logger = logging.getLogger(__name__)

# Calculate resource allocation
validator_cpus = get_validator_cpu_count(settings.VALIDATOR_CPU_PERCENT)
stats_concurrency = get_stats_worker_concurrency(
    settings.STATS_WORKER_CONCURRENCY, 
    validator_cpus
)

# Log calculated values at startup
logger.info("=" * 60)
logger.info("Celery Worker Resource Allocation")
logger.info(f"Total CPUs detected: {__import__('multiprocessing').cpu_count()}")
logger.info(f"Validator CPU allocation: {validator_cpus} CPUs ({settings.VALIDATOR_CPU_PERCENT}% requested)")
logger.info(f"Statistics worker concurrency: {stats_concurrency} (setting: {settings.STATS_WORKER_CONCURRENCY})")
logger.info("=" * 60)

# Create Celery instance
celery_app = Celery(
    "fastapi_celery",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND,
    include=["app.tasks", "app.tasks.validator_tasks", "app.tasks.statistics_tasks"],  # Import task modules here
)

# Queue definitions
celery_app.conf.task_routes = {
    # Validation tasks go to heavy_validation queue
    'validator.validate_archive': {'queue': 'heavy_validation'},
    
    # Statistics tasks go to light_tasks queue
    'statistics.*': {'queue': 'light_tasks'},
    
    # Tasks without explicit queue specification will use default queue
    # maintaining backward compatibility
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
    worker_concurrency=stats_concurrency,  # Apply calculated concurrency
    
    # Dead Letter Queue configuration
    task_reject_on_worker_lost=True,  # Reject tasks when worker is lost
    task_ignore_result=False,  # Store task results for monitoring
    result_expires=3600,  # Results expire after 1 hour to prevent memory leak
    
    # Task time limits (global defaults, can be overridden per task)
    task_time_limit=7200,  # Hard time limit of 2 hours
    task_soft_time_limit=7000,  # Soft time limit slightly less than hard limit
    
    # Dead letter queue routing for failed tasks
    task_dead_letter_queue_config={
        'max_retries_exceeded': 'dead_letter',  # Queue for tasks that exceeded max retries
        'expired': 'dead_letter',  # Queue for expired tasks
        'rejected': 'dead_letter',  # Queue for rejected tasks
    }
)

# Optional: Define custom periodic tasks
celery_app.conf.beat_schedule = {
    # Daily statistics collection - runs every day at 1 AM UTC
    "collect-daily-statistics": {
        "task": "statistics.collect_daily_stats",
        "schedule": 3600.0 * 24,  # 24 hours
        "options": {"expires": 3600}  # Task expires after 1 hour
    },
    # Weekly statistics aggregation - runs every Monday at 2 AM UTC  
    "aggregate-weekly-statistics": {
        "task": "statistics.aggregate_weekly_stats",
        "schedule": 3600.0 * 24 * 7,  # Weekly
        "options": {"expires": 7200}  # Task expires after 2 hours
    },
    # Monthly statistics aggregation - runs on 1st of each month at 3 AM UTC
    "aggregate-monthly-statistics": {
        "task": "statistics.aggregate_monthly_stats", 
        "schedule": 3600.0 * 24 * 30,  # Monthly (approximate)
        "options": {"expires": 7200}  # Task expires after 2 hours
    },
    # XML archive analysis - runs every 6 hours to process new archives
    "analyze-xml-archives": {
        "task": "statistics.analyze_xml_archives",
        "schedule": 3600.0 * 6,  # Every 6 hours
        "options": {"expires": 10800}  # Task expires after 3 hours
    },
    # Provider biological units collection - runs daily at 1:30 AM UTC (after daily stats)
    "collect-provider-biological-units": {
        "task": "statistics.collect_provider_biological_units",
        "schedule": 3600.0 * 24,  # Daily
        "options": {"expires": 3600}  # Task expires after 1 hour
    },
}
