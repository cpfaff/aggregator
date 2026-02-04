"""
Example tasks to demonstrate Celery integration.
These are placeholder tasks that can be replaced with real application tasks.
"""

import logging
import time
from typing import Any

from celery import shared_task

logger = logging.getLogger(__name__)


@shared_task(
    bind=True,
    name="example.process_data",
    max_retries=3,
    soft_time_limit=300,
    autoretry_for=(Exception,),
    retry_backoff=True,
)
def process_data(self, data: dict[str, Any], user_id: int | None = None) -> dict[str, Any]:
    """
    Example task that processes data.

    Args:
        data: The data to process
        user_id: Optional user ID for tracking

    Returns:
        A dictionary containing processed results
    """
    logger.info(f"Processing data for user {user_id}: {data}")

    # Simulate processing time
    time.sleep(5)

    # Example of processing logic
    result = {
        "processed": True,
        "input_size": len(data),
        "timestamp": time.time(),
        "user_id": user_id,
    }

    logger.info(f"Data processing completed for user {user_id}")
    return result


@shared_task(name="example.periodic_task")
def periodic_task() -> str:
    """
    Example periodic task that runs on a schedule defined in celery_app.py

    Returns:
        Status message
    """
    logger.info("Running periodic task")
    # Add your periodic task logic here
    return "Periodic task completed"
