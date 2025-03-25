"""
Celery tasks for XML validation.
"""

import logging
from datetime import datetime
from typing import Dict, Any, Optional

from celery import shared_task

from app.models import ValidationJobModel, XmlArchiveModel
from app.db.session import SessionLocal
from app.tasks.validator.service import ValidatorService

logger = logging.getLogger(__name__)


@shared_task(
    bind=True,
    name="validator.validate_archive",
    max_retries=3,
    soft_time_limit=7200,  # 2 hour timeout
    retry_backoff=True,
)
def validate_archive(self, archive_id: int) -> Dict[str, Any]:
    """
    Validate an XML archive with the given ID.
    
    This task will:
    1. Fetch the archive information from the database
    2. Create a validation job record
    3. Run the validation using the validator service
    4. Update the job record with the results
    
    Args:
        archive_id: ID of the XML archive to validate
        
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
            
        # Create or update job record
        job = db.query(ValidationJobModel).filter(
            ValidationJobModel.archive_id == archive_id,
            ValidationJobModel.task_id == self.request.id
        ).first()
        
        if not job:
            job = ValidationJobModel(
                archive_id=archive_id,
                status="running",
                task_id=self.request.id
            )
            db.add(job)
        else:
            job.status = "running"
            
        db.commit()
        db.refresh(job)
        
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
        
        logger.exception(f"Error validating archive {archive_id}: {e}")
        raise
        
    finally:
        db.close()
