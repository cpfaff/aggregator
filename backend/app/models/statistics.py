"""
Statistics models for tracking dataset registry metrics over time.
"""
from datetime import datetime, date
from enum import Enum
from typing import Dict, Any, Optional

from sqlalchemy import Column, Integer, String, Boolean, ForeignKey, Index, Date, Float, CheckConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship

from app.models.base import Base, TimestampMixin


class MetricType(str, Enum):
    """Enumeration of metric types for statistics collection."""
    
    # Dataset metrics
    DATASET_COUNT = "dataset_count"
    DATASET_REGISTRATION_RATE = "dataset_registration_rate"
    DATASET_MODIFICATION_RATE = "dataset_modification_rate"
    DATASET_UNIT_COUNT = "dataset_unit_count"
    
    # Provider metrics
    PROVIDER_COUNT = "provider_count"
    PROVIDER_DATASET_COUNT = "provider_dataset_count"
    PROVIDER_ACTIVITY_SCORE = "provider_activity_score"
    PROVIDER_BIOLOGICAL_UNITS = "provider_biological_units"
    
    # Validation metrics
    VALIDATION_SUCCESS_RATE = "validation_success_rate"
    VALIDATION_ERROR_RATE = "validation_error_rate"
    VALIDATION_PROCESSING_TIME = "validation_processing_time"
    VALIDATION_JOB_COUNT = "validation_job_count"
    
    # Data quality metrics
    ABCD_COMPLIANCE_RATE = "abcd_compliance_rate"
    XML_ARCHIVE_COUNT = "xml_archive_count"
    
    # System metrics
    SYSTEM_STORAGE_SIZE = "system_storage_size"
    SYSTEM_PROCESSING_LOAD = "system_processing_load"
    SYSTEM_API_RESPONSE_TIME = "system_api_response_time"


class EntityType(str, Enum):
    """Enumeration of entity types that statistics can be associated with."""
    
    SYSTEM = "system"        # System-wide statistics
    PROVIDER = "provider"    # Provider-specific statistics
    DATASET = "dataset"      # Dataset-specific statistics
    DATACENTER = "datacenter" # Data center statistics


class Period(str, Enum):
    """Enumeration of time periods for statistics aggregation."""
    
    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"
    QUARTERLY = "quarterly"
    YEARLY = "yearly"


class StatisticModel(Base, TimestampMixin):
    """Statistics model for tracking various metrics over time."""
    __tablename__ = "statistics"
    
    id = Column(Integer, primary_key=True, index=True)
    
    # Metric identification
    metric_type = Column(String, nullable=False)  # From MetricType enum
    entity_type = Column(String, nullable=False)  # From EntityType enum
    entity_id = Column(Integer, nullable=True)    # References provider_id, dataset_id, etc.
    
    # Time dimension
    period = Column(String, nullable=False)       # From Period enum
    date = Column(Date, nullable=False)           # The date this statistic represents
    
    # Value and metadata
    value = Column(Float, nullable=False)         # The numeric value of the metric
    extra_data = Column(JSONB, nullable=True)    # Additional context data
    
    # Constraints
    __table_args__ = (
        # Performance indexes
        Index("idx_statistics_entity", "entity_type", "entity_id", "date"),
        Index("idx_statistics_metric", "metric_type", "period", "date"),
        Index("idx_statistics_date", "date"),
        Index("idx_statistics_lookup", "metric_type", "entity_type", "entity_id", "period"),
        
        # Validation constraints
        CheckConstraint(
            "metric_type IN ('dataset_count', 'dataset_registration_rate', 'dataset_modification_rate', "
            "'dataset_unit_count', 'provider_count', 'provider_dataset_count', 'provider_activity_score', "
            "'provider_biological_units', 'validation_success_rate', 'validation_error_rate', 'validation_processing_time', "
            "'validation_job_count', 'abcd_compliance_rate', 'xml_archive_count', "
            "'system_storage_size', 'system_processing_load', 'system_api_response_time')",
            name="valid_metric_type"
        ),
        CheckConstraint(
            "entity_type IN ('system', 'provider', 'dataset', 'datacenter')",
            name="valid_entity_type"
        ),
        CheckConstraint(
            "period IN ('daily', 'weekly', 'monthly', 'quarterly', 'yearly')",
            name="valid_period"
        ),
        CheckConstraint(
            "value >= 0",
            name="non_negative_value"
        ),
        
        # Business logic constraints
        CheckConstraint(
            "(entity_type = 'system' AND entity_id IS NULL) OR "
            "(entity_type != 'system' AND entity_id IS NOT NULL)",
            name="entity_id_consistency"
        ),
    )
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert model to dictionary representation."""
        return {
            "id": self.id,
            "metric_type": self.metric_type,
            "entity_type": self.entity_type,
            "entity_id": self.entity_id,
            "period": self.period,
            "date": self.date.isoformat() if self.date else None,
            "value": self.value,
            "extra_data": self.extra_data,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
    
    @classmethod
    def get_metric_description(cls, metric_type: str) -> Optional[str]:
        """Get human-readable description for a metric type."""
        descriptions = {
            MetricType.DATASET_COUNT: "Total number of datasets",
            MetricType.DATASET_REGISTRATION_RATE: "Rate of new dataset registrations",
            MetricType.DATASET_MODIFICATION_RATE: "Rate of dataset modifications",
            MetricType.DATASET_UNIT_COUNT: "Number of units in dataset",
            MetricType.PROVIDER_COUNT: "Total number of providers",
            MetricType.PROVIDER_DATASET_COUNT: "Number of datasets per provider",
            MetricType.PROVIDER_ACTIVITY_SCORE: "Provider activity score",
            MetricType.PROVIDER_BIOLOGICAL_UNITS: "Total biological units across all datasets per provider",
            MetricType.VALIDATION_SUCCESS_RATE: "Percentage of successful validations",
            MetricType.VALIDATION_ERROR_RATE: "Percentage of validation errors",
            MetricType.VALIDATION_PROCESSING_TIME: "Average validation processing time",
            MetricType.VALIDATION_JOB_COUNT: "Number of validation jobs",
            MetricType.ABCD_COMPLIANCE_RATE: "ABCD schema compliance rate",
            MetricType.XML_ARCHIVE_COUNT: "Number of XML archives",
            MetricType.SYSTEM_STORAGE_SIZE: "Total storage size in bytes",
            MetricType.SYSTEM_PROCESSING_LOAD: "System processing load",
            MetricType.SYSTEM_API_RESPONSE_TIME: "Average API response time",
        }
        return descriptions.get(metric_type)