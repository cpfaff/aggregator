from celery import Celery
from app.core.config import settings

# Create Celery instance
celery_app = Celery(
    "fastapi_celery",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND,
    include=["app.tasks", "app.tasks.validator_tasks"],  # Import task modules here
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
    # Example periodic task that runs every 30 minutes
    # "example-periodic-task": {
    #     "task": "app.tasks.example.periodic_task",
    #     "schedule": 1800.0,  # 30 minutes
    # },
}
