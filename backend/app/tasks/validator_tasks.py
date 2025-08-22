"""
Celery tasks for XML validation.
"""

import logging
import uuid
from datetime import datetime
from typing import Dict, Any, Optional

from celery import shared_task

from app.models import ValidationJobModel, XmlArchiveModel
from app.db.session import SessionLocal
from app.tasks.validator.service import ValidatorService
from app.core.task_base import LoggingTask

logger = logging.getLogger(__name__)


@shared_task(
    bind=True,
    base=LoggingTask,  # Use custom base class for enhanced logging
    name="validator.validate_archive",
    queue='heavy_validation',
    max_retries=3,
    soft_time_limit=7200,  # 2 hour timeout
    retry_backoff=True,
    retry_backoff_max=120,  # Maximum backoff in seconds (2 minutes)
    retry_jitter=True,  # Add randomization to prevent thundering herd
    autoretry_for=(Exception,),  # Auto-retry on all exceptions
    task_time_limit=7500,  # Hard time limit (2h 5min)
)
def validate_archive(self, archive_id: int, job_id: Optional[int] = None) -> Dict[str, Any]:
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
    
    try:
        # Get archive details from DB
        archive = db.query(XmlArchiveModel).filter(XmlArchiveModel.id == archive_id).first()
        if not archive:
            raise ValueError(f"Archive with ID {archive_id} not found")
        
        # Find existing job or create a new one if job_id not provided
        if job_id:
            job = db.query(ValidationJobModel).filter(ValidationJobModel.id == job_id).first()
            if not job:
                logger.warning(f"Job with ID {job_id} not found, creating a new one")
                job = None
                
        if not job:
            # Generate a unique task_id for this job by combining Celery task ID and a UUID
            unique_task_id = f"{self.request.id}_{str(uuid.uuid4())}"
                
            # Create job record with unique task_id
            job = ValidationJobModel(
                archive_id=archive_id,
                status="running",
                task_id=unique_task_id,
                started_at=datetime.utcnow()
            )
            db.add(job)
            db.commit()
            db.refresh(job)
        else:
            # Update existing job to running state
            job.status = "running"
            job.started_at = datetime.utcnow()
            job.task_id = self.request.id  # Update with current task ID
            db.commit()
        
        # Log the start of validation
        logger.info(f"Starting validation for archive {archive_id} (job ID: {job.id})")
        
        # Run validation
        validator_service = ValidatorService()
        final_report = validator_service.validate_archive(archive.url)
        
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
        
        # Trigger real-time validation statistics update
        from app.tasks.statistics_tasks import update_validation_statistics
        update_validation_statistics.delay(job.id, "completion")
        
        return {
            "job_id": job.id,
            "archive_id": archive_id,
            "status": "completed",
            "total_files": job.total_files,
            "valid_files": job.valid_files,
            "error_count": job.error_count,
            "validation_time": job.validation_time
        }
        
    except Exception as e:
        # Update job status to failed
        if job:
            job.status = "failed"
            job.completed_at = datetime.utcnow()
            job.results = {"error": str(e)}
            db.commit()
            
            # Trigger real-time validation statistics update even for failed jobs
            from app.tasks.statistics_tasks import update_validation_statistics
            update_validation_statistics.delay(job.id, "failure")
        
        logger.exception(f"Error validating archive {archive_id}: {e}")
        raise
        
    finally:
        db.close()
