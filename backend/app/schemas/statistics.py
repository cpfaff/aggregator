"""
Statistics schemas for API request/response validation.
"""
from datetime import datetime
from datetime import date as date_type
from typing import Optional, List, Dict, Any, Union
from enum import Enum

from pydantic import BaseModel, Field, validator, ConfigDict

from app.models.statistics import MetricType, EntityType, Period


class StatisticBase(BaseModel):
    """Base schema for statistics."""
    metric_type: str = Field(..., description="Type of metric being recorded")
    entity_type: str = Field(..., description="Type of entity this statistic relates to")
    entity_id: Optional[int] = Field(None, description="ID of the specific entity (null for system-wide metrics)")
    period: str = Field(..., description="Time period aggregation")
    date: date_type = Field(..., description="Date this statistic represents")
    value: float = Field(..., ge=0, description="Numeric value of the metric")
    extra_data: Optional[Dict[str, Any]] = Field(None, description="Additional context data")
    
    @validator('metric_type')
    def validate_metric_type(cls, v):
        """Validate metric_type against enum values."""
        valid_types = [e.value for e in MetricType]
        if v not in valid_types:
            raise ValueError(f'metric_type must be one of: {", ".join(valid_types)}')
        return v
    
    @validator('entity_type')
    def validate_entity_type(cls, v):
        """Validate entity_type against enum values."""
        valid_types = [e.value for e in EntityType]
        if v not in valid_types:
            raise ValueError(f'entity_type must be one of: {", ".join(valid_types)}')
        return v
    
    @validator('period')
    def validate_period(cls, v):
        """Validate period against enum values."""
        valid_periods = [e.value for e in Period]
        if v not in valid_periods:
            raise ValueError(f'period must be one of: {", ".join(valid_periods)}')
        return v
    
    @validator('entity_id')
    def validate_entity_id_consistency(cls, v, values):
        """Validate entity_id consistency with entity_type."""
        entity_type = values.get('entity_type')
        if entity_type == EntityType.SYSTEM and v is not None:
            raise ValueError('entity_id must be null for system-wide metrics')
        if entity_type != EntityType.SYSTEM and v is None:
            raise ValueError('entity_id is required for non-system metrics')
        return v


class StatisticCreate(StatisticBase):
    """Schema for creating statistics."""
    pass


class StatisticUpdate(BaseModel):
    """Schema for updating statistics."""
    value: Optional[float] = Field(None, ge=0, description="Updated numeric value")
    extra_data: Optional[Dict[str, Any]] = Field(None, description="Updated context data")


class StatisticResponse(StatisticBase):
    """Schema for statistic responses."""
    id: int = Field(..., description="Unique identifier")
    created_at: datetime = Field(..., description="When this statistic was recorded")
    updated_at: datetime = Field(..., description="When this statistic was last updated")
    
    model_config = ConfigDict(from_attributes=True)


class TimeSeriesPoint(BaseModel):
    """Single point in a time series."""
    date: date_type = Field(..., description="Date of the data point")
    value: float = Field(..., description="Value at this date")
    extra_data: Optional[Dict[str, Any]] = Field(None, description="Additional context")


class TimeSeriesResponse(BaseModel):
    """Response for time series data."""
    metric_type: str = Field(..., description="Type of metric")
    entity_type: str = Field(..., description="Type of entity")
    entity_id: Optional[int] = Field(None, description="Entity ID if applicable")
    period: str = Field(..., description="Time period aggregation")
    data_points: List[TimeSeriesPoint] = Field(..., description="Time series data points")
    total_points: int = Field(..., description="Total number of data points")


class StatisticsQuery(BaseModel):
    """Query parameters for statistics endpoints."""
    metric_types: Optional[List[str]] = Field(None, description="Filter by metric types")
    entity_types: Optional[List[str]] = Field(None, description="Filter by entity types")
    entity_ids: Optional[List[int]] = Field(None, description="Filter by entity IDs")
    periods: Optional[List[str]] = Field(None, description="Filter by periods")
    start_date: Optional[date_type] = Field(None, description="Start date for date range filter")
    end_date: Optional[date_type] = Field(None, description="End date for date range filter")
    limit: Optional[int] = Field(100, ge=1, le=1000, description="Maximum results")
    offset: Optional[int] = Field(0, ge=0, description="Results offset for pagination")


class OverviewStats(BaseModel):
    """Overview statistics response."""
    total_datasets: int = Field(..., description="Total number of datasets")
    total_providers: int = Field(..., description="Total number of providers")
    total_datacenters: int = Field(..., description="Total number of data centers")
    total_xml_archives: int = Field(..., description="Total XML archives")
    validation_success_rate: Optional[float] = Field(None, description="Overall validation success rate")
    last_updated: datetime = Field(..., description="When these stats were last updated")


class ProviderStats(BaseModel):
    """Provider-specific statistics."""
    provider_id: int = Field(..., description="Provider ID")
    provider_name: str = Field(..., description="Provider name")
    dataset_count: int = Field(..., description="Number of datasets")
    xml_archive_count: int = Field(..., description="Number of XML archives")
    validation_success_rate: Optional[float] = Field(None, description="Validation success rate")
    last_activity: Optional[datetime] = Field(None, description="Last activity timestamp")
    activity_score: Optional[float] = Field(None, description="Provider activity score")


class DatasetStats(BaseModel):
    """Dataset-specific statistics."""
    dataset_id: int = Field(..., description="Dataset ID")
    dataset_title: str = Field(..., description="Dataset title")
    provider_id: int = Field(..., description="Provider ID")
    unit_count: Optional[int] = Field(None, description="Number of units in dataset")
    last_modified: Optional[datetime] = Field(None, description="Last modification timestamp")
    validation_status: Optional[str] = Field(None, description="Latest validation status")
    is_valid: Optional[bool] = Field(None, description="Whether the latest validation passed")
    citation_completeness: Optional[float] = Field(None, description="Citation completeness score (deprecated, always None)")


class QualityMetrics(BaseModel):
    """Data quality metrics."""
    total_validations: int = Field(..., description="Total validation jobs run")
    successful_validations: int = Field(..., description="Successful validations")
    failed_validations: int = Field(..., description="Failed validations")
    success_rate: float = Field(..., description="Overall success rate percentage")
    abcd_compliance_rate: Optional[float] = Field(None, description="ABCD schema compliance rate")
    average_processing_time: Optional[float] = Field(None, description="Average processing time in seconds")


class GrowthMetrics(BaseModel):
    """Growth metrics over time."""
    datasets_timeline: List[TimeSeriesPoint] = Field(..., description="Dataset growth over time")
    providers_timeline: List[TimeSeriesPoint] = Field(..., description="Provider growth over time")
    validation_timeline: List[TimeSeriesPoint] = Field(..., description="Validation activity over time")


# Metric type descriptions for API documentation
METRIC_DESCRIPTIONS = {
    MetricType.DATASET_COUNT: "Total number of datasets in the system",
    MetricType.DATASET_REGISTRATION_RATE: "Rate of new dataset registrations per period",
    MetricType.DATASET_MODIFICATION_RATE: "Rate of dataset modifications per period",
    MetricType.DATASET_UNIT_COUNT: "Number of units (specimens, observations) in a dataset",
    MetricType.PROVIDER_COUNT: "Total number of data providers",
    MetricType.PROVIDER_DATASET_COUNT: "Number of datasets per provider",
    MetricType.PROVIDER_ACTIVITY_SCORE: "Activity score based on provider engagement",
    MetricType.PROVIDER_BIOLOGICAL_UNITS: "Total biological units across all datasets per provider",
    MetricType.VALIDATION_SUCCESS_RATE: "Percentage of successful validation jobs",
    MetricType.VALIDATION_ERROR_RATE: "Percentage of failed validation jobs",
    MetricType.VALIDATION_PROCESSING_TIME: "Average time to complete validation jobs",
    MetricType.VALIDATION_JOB_COUNT: "Total number of validation jobs",
    MetricType.ABCD_COMPLIANCE_RATE: "Percentage of XML files compliant with ABCD schema",
    MetricType.XML_ARCHIVE_COUNT: "Total number of XML archive files",
    MetricType.SYSTEM_STORAGE_SIZE: "Total storage used by the system",
    MetricType.SYSTEM_PROCESSING_LOAD: "System processing load metrics",
    MetricType.SYSTEM_API_RESPONSE_TIME: "Average API response time",
}