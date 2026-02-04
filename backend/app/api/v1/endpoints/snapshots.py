"""
Snapshot statistics API endpoints.

This module replaces unified_statistics.py with a simplified implementation
using the ArchiveSnapshot model.

Total: ~300 lines (vs 798 in the old unified_statistics.py)
"""

import logging
from datetime import date
from typing import Any, Dict, Optional

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query, Response
from sqlalchemy.orm import Session

from app.db.session import get_sync_db
from app.models.user import UserModel
from app.schemas.statistics import (
    DatasetStats,
    GrowthMetrics,
    OverviewStats,
    ProviderStats,
    QualityMetrics,
    TimeSeriesPoint,
    TimeSeriesResponse,
)
from app.security.permissions import get_current_user_optional, get_current_user_sync, require_admin
from app.services.snapshot_service import SnapshotService
from app.tasks.snapshot_tasks import collect_archive_snapshots

logger = logging.getLogger(__name__)

router = APIRouter()


def _no_cache_headers(response: Response) -> None:
    """Set no-cache headers for real-time data."""
    if response:
        response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
        response.headers["Pragma"] = "no-cache"
        response.headers["Expires"] = "0"


# -----------------------------------------------------------------------------
# Public Endpoints (no auth required)
# -----------------------------------------------------------------------------


@router.get("/overview", response_model=OverviewStats, summary="Registry overview statistics")
async def get_overview(
    db: Session = Depends(get_sync_db),
    current_user: Optional[UserModel] = Depends(get_current_user_optional),
    response: Response = None,
) -> OverviewStats:
    """Get registry overview statistics using live database counts."""
    try:
        _no_cache_headers(response)
        service = SnapshotService(db)
        include_sensitive = current_user and current_user.is_global_admin
        stats = service.get_overview_stats(user=current_user, include_sensitive=include_sensitive)
        return OverviewStats(**stats)
    except Exception as e:
        logger.error(f"Error getting overview: {e}")
        raise HTTPException(status_code=500, detail="Error retrieving statistics")


@router.get("/quality", response_model=QualityMetrics, summary="Data quality metrics")
async def get_quality_metrics(
    db: Session = Depends(get_sync_db),
    current_user: Optional[UserModel] = Depends(get_current_user_optional),
    days: int = Query(30, ge=1, le=90, description="Number of days to look back"),
    response: Response = None,
) -> QualityMetrics:
    """Get data quality metrics from validation jobs."""
    try:
        _no_cache_headers(response)
        service = SnapshotService(db)
        metrics = service.get_quality_metrics(user=current_user, days=days)
        return QualityMetrics(**metrics)
    except Exception as e:
        logger.error(f"Error getting quality metrics: {e}")
        raise HTTPException(status_code=500, detail="Error retrieving quality metrics")


@router.get("/timeline", response_model=GrowthMetrics, summary="Registry growth timeline")
async def get_growth_timeline(
    period: str = Query("monthly", description="Time period for aggregation"),
    months: int = Query(12, ge=1, le=60, description="Number of months to retrieve"),
    db: Session = Depends(get_sync_db),
    current_user: Optional[UserModel] = Depends(get_current_user_optional),
    response: Response = None,
) -> GrowthMetrics:
    """Get registry growth metrics over time."""
    try:
        _no_cache_headers(response)
        service = SnapshotService(db)
        growth_data = service.get_growth_metrics(period=period, months=months, user=current_user)
        return GrowthMetrics(
            datasets_timeline=[TimeSeriesPoint(**p) for p in growth_data["datasets_timeline"]],
            providers_timeline=[TimeSeriesPoint(**p) for p in growth_data["providers_timeline"]],
            validation_timeline=[TimeSeriesPoint(**p) for p in growth_data["validation_timeline"]],
        )
    except Exception as e:
        logger.error(f"Error getting growth timeline: {e}")
        raise HTTPException(status_code=500, detail="Error retrieving growth timeline")


@router.get("/providers", summary="Provider statistics")
async def get_provider_list_stats(
    limit: int = Query(20, ge=1, le=100, description="Number of top providers to show"),
    db: Session = Depends(get_sync_db),
    current_user: Optional[UserModel] = Depends(get_current_user_optional),
    response: Response = None,
) -> Dict[str, Any]:
    """Get statistics about top contributing providers."""
    try:
        _no_cache_headers(response)
        service = SnapshotService(db)
        return service.get_provider_list_stats(limit=limit, user=current_user)
    except Exception as e:
        logger.error(f"Error getting provider list stats: {e}")
        raise HTTPException(status_code=500, detail="Error retrieving provider statistics")


@router.get("/datasets/recent", summary="Recent dataset activity")
async def get_recent_dataset_activity(
    limit: int = Query(10, ge=1, le=50, description="Number of recent activities to show"),
    days: int = Query(30, ge=1, le=90, description="Number of days to look back"),
    db: Session = Depends(get_sync_db),
    current_user: Optional[UserModel] = Depends(get_current_user_optional),
    response: Response = None,
) -> Dict[str, Any]:
    """Get recent dataset registration activity."""
    try:
        _no_cache_headers(response)
        service = SnapshotService(db)
        return service.get_recent_activity(limit=limit, days=days, user=current_user)
    except Exception as e:
        logger.error(f"Error getting recent dataset activity: {e}")
        raise HTTPException(status_code=500, detail="Error retrieving recent activity")


@router.get("/health", summary="Registry health status")
async def get_registry_health(
    db: Session = Depends(get_sync_db),
    current_user: Optional[UserModel] = Depends(get_current_user_optional),
    response: Response = None,
) -> Dict[str, Any]:
    """Get basic health metrics of the registry system."""
    try:
        _no_cache_headers(response)
        service = SnapshotService(db)
        return service.get_health_status(user=current_user)
    except Exception as e:
        logger.error(f"Error getting registry health: {e}")
        raise HTTPException(status_code=500, detail="Error retrieving health status")


# -----------------------------------------------------------------------------
# Authenticated Endpoints
# -----------------------------------------------------------------------------


@router.get(
    "/providers/{provider_id}", response_model=ProviderStats, summary="Provider-specific statistics"
)
async def get_provider_statistics(
    provider_id: int,
    db: Session = Depends(get_sync_db),
    current_user: UserModel = Depends(get_current_user_sync),
) -> ProviderStats:
    """Get statistics for a specific data provider. Requires authentication."""
    try:
        service = SnapshotService(db)
        stats = service.get_provider_statistics(provider_id=provider_id, user=current_user)
        if not stats:
            raise HTTPException(status_code=404, detail="Provider not found")
        return ProviderStats(**stats)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting provider {provider_id} statistics: {e}")
        raise HTTPException(status_code=500, detail="Error retrieving provider statistics")


@router.get(
    "/datasets/{dataset_id}", response_model=DatasetStats, summary="Dataset-specific statistics"
)
async def get_dataset_statistics(
    dataset_id: int,
    db: Session = Depends(get_sync_db),
    current_user: UserModel = Depends(get_current_user_sync),
) -> DatasetStats:
    """Get statistics for a specific dataset. Requires authentication."""
    try:
        service = SnapshotService(db)
        stats = service.get_dataset_statistics(dataset_id=dataset_id, user=current_user)
        if not stats:
            raise HTTPException(status_code=404, detail="Dataset not found")
        return DatasetStats(**stats)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting dataset {dataset_id} statistics: {e}")
        raise HTTPException(status_code=500, detail="Error retrieving dataset statistics")


@router.get(
    "/providers/{provider_id}/datasets-timeline",
    response_model=TimeSeriesResponse,
    summary="Provider datasets timeline",
)
async def get_provider_datasets_timeline(
    provider_id: int,
    period: str = Query("monthly", description="Time period (daily or monthly)"),
    months: int = Query(12, ge=1, le=60, description="Number of months to retrieve"),
    db: Session = Depends(get_sync_db),
    current_user: UserModel = Depends(get_current_user_sync),
) -> TimeSeriesResponse:
    """Get dataset count timeline for a specific provider. Requires authentication."""
    try:
        service = SnapshotService(db)
        data_points = service.get_provider_datasets_timeline(
            provider_id=provider_id, period=period, months=months
        )

        return TimeSeriesResponse(
            metric_type="provider_dataset_count",
            entity_type="provider",
            entity_id=provider_id,
            period=period,
            data_points=[TimeSeriesPoint(**p) for p in data_points],
            total_points=len(data_points),
        )
    except Exception as e:
        logger.error(f"Error getting provider {provider_id} datasets timeline: {e}")
        raise HTTPException(status_code=500, detail="Error retrieving provider datasets timeline")


@router.get(
    "/providers/{provider_id}/biological-units-timeline",
    response_model=TimeSeriesResponse,
    summary="Provider biological units timeline",
)
async def get_provider_biological_units_timeline(
    provider_id: int,
    period: str = Query("daily", description="Time period"),
    start_date: Optional[date] = Query(None, description="Start date"),
    end_date: Optional[date] = Query(None, description="End date"),
    limit: int = Query(30, ge=1, le=365, description="Maximum data points"),
    db: Session = Depends(get_sync_db),
    current_user: UserModel = Depends(get_current_user_sync),
) -> TimeSeriesResponse:
    """Get biological units timeline for a specific provider. Requires authentication."""
    try:
        service = SnapshotService(db)
        data_points = service.get_provider_biological_units_timeline(
            provider_id=provider_id, start_date=start_date, end_date=end_date, limit=limit
        )

        return TimeSeriesResponse(
            metric_type="provider_biological_units",
            entity_type="provider",
            entity_id=provider_id,
            period=period,
            data_points=[TimeSeriesPoint(**p) for p in data_points],
            total_points=len(data_points),
        )
    except Exception as e:
        logger.error(f"Error getting provider {provider_id} biological units timeline: {e}")
        raise HTTPException(
            status_code=500, detail="Error retrieving provider biological units timeline"
        )


@router.get(
    "/biological-units-timeline",
    response_model=TimeSeriesResponse,
    summary="Biological units timeline",
)
async def get_biological_units_timeline(
    period: str = Query("daily", description="Time period"),
    start_date: Optional[date] = Query(None, description="Start date"),
    end_date: Optional[date] = Query(None, description="End date"),
    limit: int = Query(30, ge=1, le=365, description="Maximum data points"),
    db: Session = Depends(get_sync_db),
    current_user: UserModel = Depends(get_current_user_sync),
) -> TimeSeriesResponse:
    """Get system-wide biological units timeline. Requires authentication."""
    try:
        service = SnapshotService(db)
        data_points = service.get_biological_units_timeline(
            start_date=start_date, end_date=end_date, limit=limit
        )

        return TimeSeriesResponse(
            metric_type="provider_biological_units",
            entity_type="system",
            entity_id=None,
            period=period,
            data_points=[TimeSeriesPoint(**p) for p in data_points],
            total_points=len(data_points),
        )
    except Exception as e:
        logger.error(f"Error getting biological units timeline: {e}")
        raise HTTPException(status_code=500, detail="Error retrieving biological units timeline")


@router.get(
    "/multi-provider-biological-units",
    response_model=Dict[str, Any],
    summary="Multi-provider biological units",
)
async def get_multi_provider_biological_units_timeline(
    period: str = Query("daily", description="Time period"),
    start_date: Optional[date] = Query(None, description="Start date"),
    end_date: Optional[date] = Query(None, description="End date"),
    limit: int = Query(30, ge=1, le=365, description="Maximum data points"),
    db: Session = Depends(get_sync_db),
    current_user: UserModel = Depends(get_current_user_sync),
) -> Dict[str, Any]:
    """Get biological units timeline for all providers. Requires authentication."""
    try:
        service = SnapshotService(db)
        return service.get_multi_provider_timeline(
            start_date=start_date, end_date=end_date, limit=limit
        )
    except Exception as e:
        logger.error(f"Error getting multi-provider biological units timeline: {e}")
        raise HTTPException(
            status_code=500, detail="Error retrieving multi-provider biological units timeline"
        )


# -----------------------------------------------------------------------------
# Admin-only Endpoints
# -----------------------------------------------------------------------------


@router.post("/collect", summary="Trigger snapshot collection")
async def trigger_snapshot_collection(
    background_tasks: BackgroundTasks, current_user: UserModel = Depends(require_admin)
) -> Dict[str, Any]:
    """
    Manually trigger archive snapshot collection.
    Requires admin permissions.
    """
    try:
        background_tasks.add_task(collect_archive_snapshots.delay)
        return {"message": "Snapshot collection task has been queued", "status": "queued"}
    except Exception as e:
        logger.error(f"Error triggering snapshot collection: {e}")
        raise HTTPException(status_code=500, detail="Error triggering snapshot collection")
