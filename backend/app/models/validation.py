"""
Models for XML validation jobs.
"""

from typing import Any

from sqlalchemy import Column, DateTime, Float, ForeignKey, Integer, String, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship

from .base import Base, TimestampMixin


class ValidationJobModel(Base, TimestampMixin):
    """
    Model for XML validation jobs.

    Stores metadata about a validation job including status, task ID,
    and summary metrics of the validation results. The full validation
    results are stored as JSON to allow for flexible result structures.
    """

    __tablename__ = "validation_jobs"

    id = Column(Integer, primary_key=True)
    archive_id = Column(Integer, ForeignKey("xml_archives.id"))
    status = Column(String, default="pending")  # pending, running, completed, failed
    task_id = Column(String, unique=True)  # Celery task ID
    started_at = Column(DateTime, default=func.now())
    completed_at = Column(DateTime, nullable=True)

    # Summary fields for querying
    total_files = Column(Integer, nullable=True)
    valid_files = Column(Integer, nullable=True)
    error_count = Column(Integer, nullable=True)
    validation_time = Column(Float, nullable=True)

    # Full validation results as JSON
    results = Column(JSONB, nullable=True)

    # Relationships
    archive = relationship("XmlArchiveModel", back_populates="validation_jobs")

    def to_dict(self) -> dict[str, Any]:
        """
        Convert model to dictionary representation.
        """
        return {
            "id": self.id,
            "archive_id": self.archive_id,
            "status": self.status,
            "task_id": self.task_id,
            "started_at": self.started_at,
            "completed_at": self.completed_at,
            "total_files": self.total_files,
            "valid_files": self.valid_files,
            "error_count": self.error_count,
            "validation_time": self.validation_time,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }
