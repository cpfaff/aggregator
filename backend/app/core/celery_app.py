from celery import Celery
from app.core.config import settings

# Create Celery instance
celery_app = Celery(
    "fastapi_celery",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND,
    include=["app.tasks", "app.tasks.validator_tasks", "app.tasks.statistics_tasks"],  # Import task modules here
)

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
}
