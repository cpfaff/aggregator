"""
Celery tasks for XML validation.
"""

import logging
import uuid
from datetime import datetime
from typing import Any

from celery import shared_task
from sqlalchemy.exc import OperationalError

from app.core.task_base import LoggingTask
from app.db.session import SessionLocal
from app.models import ValidationJobModel, XmlArchiveModel
from app.tasks.validator.service import ValidatorService

logger = logging.getLogger(__name__)


class PermanentTaskError(Exception):
    """A deterministic, non-retriable task failure.

    Raised for failures that are identical on every attempt (e.g. the archive
    row does not exist, or its content is malformed) so they are NOT in
    ``autoretry_for`` and never consume the retry budget or backoff window —
    only genuinely transient infrastructure errors retry. Mirrors the
    ``EsGateway`` resilience shape: one typed failure the wrapper acts on.
    """


# Transient infrastructure errors worth re-attempting: a flaky DB connection
# (OperationalError), a dropped/refused socket (ConnectionError), or a hung
# dependency (TimeoutError). Deterministic failures (PermanentTaskError) are
# excluded so a missing/malformed archive fails fast instead of retrying.
TRANSIENT_TASK_ERRORS = (OperationalError, ConnectionError, TimeoutError)


@shared_task(
    bind=True,
    base=LoggingTask,  # Use custom base class for enhanced logging
    name="validator.validate_archive",
    queue="heavy_validation",
    max_retries=3,
    soft_time_limit=7200,  # 2 hour timeout
    retry_backoff=True,
    retry_backoff_max=120,  # Maximum backoff in seconds (2 minutes)
    retry_jitter=True,  # Add randomization to prevent thundering herd
    autoretry_for=TRANSIENT_TASK_ERRORS,  # Retry only transient infra errors (RH-09)
    task_time_limit=7500,  # Hard time limit (2h 5min)
)
def validate_archive(self, archive_id: int, job_id: int | None = None) -> dict[str, Any]:
    """
    Validate an XML archive with the given ID.

    This task will:
    1. Fetch the archive information from the database
    2. Use an existing validation job record or create one if job_id not provided
    3. Run the validation using the validator service
    4. Update the job record with the results

    Queue Assignment: Routes to 'heavy_validation' queue for resource-intensive
    XML processing with thread-based worker pool optimized for I/O operations.

    Args:
        archive_id: ID of the XML archive to validate
        job_id: Optional ID of an existing validation job

    Returns:
        Dictionary with job information and summary results
    """
    db = SessionLocal()
    job = None
    job_pk: int | None = None

    try:
        # Get archive details from DB - only select the columns that exist
        archive_data = (
            db.query(
                XmlArchiveModel.id,
                XmlArchiveModel.dataset_id,
                XmlArchiveModel.url,
                XmlArchiveModel.isLatest,
            )
            .filter(XmlArchiveModel.id == archive_id)
            .first()
        )
        if not archive_data:
            # Deterministic: the archive is absent on every retry, so fail fast
            # rather than spend the retry budget re-confirming it (RH-09).
            raise PermanentTaskError(f"Archive with ID {archive_id} not found")

        # Extract archive data from tuple
        archive_id_db, dataset_id, archive_url, is_latest = archive_data

        # Find existing job or create a new one if job_id not provided
        if job_id:
            job = db.query(ValidationJobModel).filter(ValidationJobModel.id == job_id).first()
            if not job:
                logger.warning(f"Job with ID {job_id} not found, creating a new one")
                job = None

        if not job:
            # Celery autoretry re-submits the original args (no job_id) but keeps
            # the same request.id; reuse the job created by a prior attempt of
            # this task for this archive so retries don't insert duplicate rows
            # (B24). task_id is "<request.id>_<uuid>" from creation below.
            job = (
                db.query(ValidationJobModel)
                .filter(
                    ValidationJobModel.archive_id == archive_id,
                    ValidationJobModel.task_id.like(f"{self.request.id}_%"),
                )
                .order_by(ValidationJobModel.id.desc())
                .first()
            )

        if not job:
            # Generate a unique task_id for this job by combining Celery task ID and a UUID
            unique_task_id = f"{self.request.id}_{str(uuid.uuid4())}"

            # Create job record with unique task_id
            job = ValidationJobModel(
                archive_id=archive_id,
                status="running",
                task_id=unique_task_id,
                started_at=datetime.utcnow(),
            )
            db.add(job)
            db.commit()
            db.refresh(job)
        else:
            # Update existing job to running state. Keep task_id unchanged: for
            # the job_id path it already holds the Celery id, and for the retry
            # reuse path it must keep its "<request.id>_<uuid>" form so further
            # retries find it (B24).
            job.status = "running"
            job.started_at = datetime.utcnow()
            db.commit()

        # Capture the pk so the failure handler can re-fetch after a rollback.
        job_pk = job.id

        # Log the start of validation
        logger.info(f"Starting validation for archive {archive_id} (job ID: {job.id})")

        # Run validation
        validator_service = ValidatorService()
        final_report = validator_service.validate_archive(archive_url)

        # Update job with results
        job.status = "completed"
        job.completed_at = datetime.utcnow()
        job.results = final_report

        # Extract summary metrics
        if "summary" in final_report:
            summary = final_report["summary"]
            job.total_files = summary.get("total_files", 0)
            job.valid_files = summary.get("valid_files", 0)
            job.error_count = job.total_files - job.valid_files
            job.validation_time = summary.get("total_time", 0)

        db.commit()

        logger.info(f"Validation completed for archive {archive_id} (job ID: {job.id})")

        return {
            "job_id": job.id,
            "archive_id": archive_id,
            "status": "completed",
            "total_files": job.total_files,
            "valid_files": job.valid_files,
            "error_count": job.error_count,
            "validation_time": job.validation_time,
        }

    except Exception as e:
        # The failure may have poisoned the transaction (e.g. it WAS the
        # success-path commit), so roll back before recording the failure;
        # otherwise the second commit raises PendingRollbackError, masking the
        # original error and leaving the job stuck 'running' (B25). Rollback
        # expires the instance, so re-fetch by pk.
        db.rollback()
        if job_pk is not None:
            failed_job = (
                db.query(ValidationJobModel).filter(ValidationJobModel.id == job_pk).first()
            )
            if failed_job is not None:
                failed_job.status = "failed"
                failed_job.completed_at = datetime.utcnow()
                failed_job.results = {"error": str(e)}
                db.commit()

        logger.exception(f"Error validating archive {archive_id}: {e}")
        raise

    finally:
        db.close()
