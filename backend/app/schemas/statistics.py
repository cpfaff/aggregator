"""
Statistics schemas for API request/response validation.

Simplified schemas for the snapshot-based statistics system.
"""

from datetime import date as date_type
from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class TimeSeriesPoint(BaseModel):
    """Single point in a time series."""

    date: date_type = Field(..., description="Date of the data point")
    value: float = Field(..., description="Value at this date")
    extra_data: dict[str, Any] | None = Field(None, description="Additional context")


class TimeSeriesResponse(BaseModel):
    """Response for time series data."""

    metric_type: str = Field(..., description="Type of metric")
    entity_type: str = Field(..., description="Type of entity")
    entity_id: int | None = Field(None, description="Entity ID if applicable")
    period: str = Field(..., description="Time period aggregation")
    data_points: list[TimeSeriesPoint] = Field(..., description="Time series data points")
    total_points: int = Field(..., description="Total number of data points")


class OverviewStats(BaseModel):
    """Overview statistics response."""

    total_datasets: int = Field(..., description="Total number of datasets")
    total_providers: int = Field(..., description="Total number of providers")
    total_datacenters: int = Field(..., description="Total number of data centers")
    total_xml_archives: int = Field(..., description="Total XML archives")
    validation_success_rate: float | None = Field(
        None, description="Overall validation success rate"
    )
    last_updated: datetime = Field(..., description="When these stats were last updated")


class ProviderStats(BaseModel):
    """Provider-specific statistics."""

    provider_id: int = Field(..., description="Provider ID")
    provider_name: str = Field(..., description="Provider name")
    dataset_count: int = Field(..., description="Number of datasets")
    xml_archive_count: int = Field(..., description="Number of XML archives")
    validation_success_rate: float | None = Field(None, description="Validation success rate")
    last_activity: datetime | None = Field(None, description="Last activity timestamp")
    activity_score: float | None = Field(
        None,
        deprecated=True,
        description="Deprecated (REQ-SH-DEAD-2): no longer tracked, always null. "
        "Retained for response-shape stability; do not rely on this field.",
    )


class DatasetStats(BaseModel):
    """Dataset-specific statistics."""

    dataset_id: int = Field(..., description="Dataset ID")
    dataset_title: str = Field(..., description="Dataset title")
    provider_id: int = Field(..., description="Provider ID")
    unit_count: int | None = Field(None, description="Number of units in dataset")
    last_modified: datetime | None = Field(None, description="Last modification timestamp")
    validation_status: str | None = Field(None, description="Latest validation status")
    is_valid: bool | None = Field(None, description="Whether the latest validation passed")


class QualityMetrics(BaseModel):
    """Data quality metrics."""

    total_validations: int = Field(..., description="Total validation jobs run")
    successful_validations: int = Field(..., description="Successful validations")
    failed_validations: int = Field(..., description="Failed validations")
    success_rate: float = Field(..., description="Overall success rate percentage")
    abcd_compliance_rate: float | None = Field(
        None,
        deprecated=True,
        description="Deprecated (REQ-SH-DEAD-2): no longer tracked, always null. "
        "Retained for response-shape stability; do not rely on this field.",
    )
    average_processing_time: float | None = Field(
        None, description="Average processing time in seconds"
    )


class GrowthMetrics(BaseModel):
    """Growth metrics over time."""

    datasets_timeline: list[TimeSeriesPoint] = Field(..., description="Dataset growth over time")
    providers_timeline: list[TimeSeriesPoint] = Field(..., description="Provider growth over time")
    validation_timeline: list[TimeSeriesPoint] = Field(
        ..., description="Validation activity over time"
    )


class ProviderRef(BaseModel):
    """Reference to a provider that appears as a series in a multi-provider timeline."""

    id: int = Field(..., description="Provider ID")
    name: str = Field(..., description="Provider name")
    key: str = Field(..., description="Key used for this provider in the wide-row series points")


class MultiProviderTimelineResponse(BaseModel):
    """Multi-provider collection timeline (REQ-SH-TL-1/2).

    A *wide-row* payload: each ``series`` element is one date with a float per
    provider, ``{"date": "<iso date>", "<provider key>": <units>, ...}``. The key is
    deliberately ``series`` (not ``data_points``) because these points are not
    ``TimeSeriesPoint`` elements — keeping the ``data_points`` key for one element
    type across the API (F-L).
    """

    metric_type: str = Field(..., description="Type of metric")
    entity_type: str = Field(..., description="Type of entity")
    period: str = Field(..., description="Time period aggregation")
    series: list[dict[str, Any]] = Field(
        ..., description="Wide-row points: one date with a unit count per provider"
    )
    total_points: int = Field(..., description="Number of series points")
    providers: list[ProviderRef] = Field(..., description="Providers present as series")
    total_providers: int = Field(..., description="Number of providers")
