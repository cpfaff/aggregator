"""
Statistics schemas for API request/response validation.

Simplified schemas for the snapshot-based statistics system.
"""

from datetime import date as date_type
from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


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


class OverviewStats(BaseModel):
    """Overview statistics response."""

    total_datasets: int = Field(..., description="Total number of datasets")
    total_providers: int = Field(..., description="Total number of providers")
    total_datacenters: int = Field(..., description="Total number of data centers")
    total_xml_archives: int = Field(..., description="Total XML archives")
    validation_success_rate: Optional[float] = Field(
        None, description="Overall validation success rate"
    )
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


class QualityMetrics(BaseModel):
    """Data quality metrics."""

    total_validations: int = Field(..., description="Total validation jobs run")
    successful_validations: int = Field(..., description="Successful validations")
    failed_validations: int = Field(..., description="Failed validations")
    success_rate: float = Field(..., description="Overall success rate percentage")
    abcd_compliance_rate: Optional[float] = Field(None, description="ABCD schema compliance rate")
    average_processing_time: Optional[float] = Field(
        None, description="Average processing time in seconds"
    )


class GrowthMetrics(BaseModel):
    """Growth metrics over time."""

    datasets_timeline: List[TimeSeriesPoint] = Field(..., description="Dataset growth over time")
    providers_timeline: List[TimeSeriesPoint] = Field(..., description="Provider growth over time")
    validation_timeline: List[TimeSeriesPoint] = Field(
        ..., description="Validation activity over time"
    )
