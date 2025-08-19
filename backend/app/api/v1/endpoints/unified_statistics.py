"""
Unified statistics API endpoints with role-based access control.
Consolidates public and authenticated statistics into a single router.
"""
import logging
from datetime import datetime, date, timedelta
from typing import List, Dict, Any, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, BackgroundTasks, Response
from sqlalchemy.orm import Session

from app.db.session import get_sync_db
from app.models import MetricType, EntityType, Period
from app.models.user import UserModel
from app.schemas.statistics import (
    StatisticResponse,
    TimeSeriesResponse,
    StatisticsQuery,
    OverviewStats,
    ProviderStats,
    DatasetStats,
    QualityMetrics,
    TimeSeriesPoint,
    GrowthMetrics
)
from app.security.permissions import get_current_user_optional, get_current_user_sync, require_admin
from app.services.statistics_service import StatisticsService
from app.tasks.statistics_tasks import (
    collect_daily_statistics, 
    analyze_xml_archives, 
    collect_provider_biological_units
)

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/overview", response_model=OverviewStats, summary="Registry overview statistics")
async def get_overview(
    db: Session = Depends(get_sync_db),
    current_user: Optional[UserModel] = Depends(get_current_user_optional),
    response: Response = None
) -> OverviewStats:
    """
    Get registry overview statistics.
    - Public users: Basic registry information
    - Authenticated users: Same as public (for now)
    - Admin users: Can request detailed metrics with include_details=true
    
    Real-time data with no caching for immediate updates.
    """
    try:
        # Set no-cache headers for real-time updates
        if response:
            response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
            response.headers["Pragma"] = "no-cache"
            response.headers["Expires"] = "0"
        
        # Initialize service
        service = StatisticsService(db)
        
        # Get overview stats with role-based filtering
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
    response: Response = None
) -> QualityMetrics:
    """
    Get data quality metrics.
    - Public users: Aggregated quality metrics
    - Authenticated users: Same as public
    - Admin users: Same data (no additional sensitive info currently)
    
    Shows validation success rates and processing metrics.
    """
    try:
        if response:
            response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
            response.headers["Pragma"] = "no-cache"
            response.headers["Expires"] = "0"
        
        service = StatisticsService(db)
        metrics = service.get_quality_metrics(user=current_user, days=days)
        
        return QualityMetrics(**metrics)
        
    except Exception as e:
        logger.error(f"Error getting quality metrics: {e}")
        raise HTTPException(status_code=500, detail="Error retrieving quality metrics")


@router.get("/timeline", response_model=GrowthMetrics, summary="Registry growth timeline")
async def get_growth_timeline(
    period: str = Query(Period.MONTHLY.value, description="Time period for aggregation"),
    months: int = Query(12, ge=1, le=60, description="Number of months to retrieve"),
    db: Session = Depends(get_sync_db),
    current_user: Optional[UserModel] = Depends(get_current_user_optional),
    response: Response = None
) -> GrowthMetrics:
    """
    Get registry growth metrics over time.
    Shows dataset and provider growth trends.
    Available to all users (public and authenticated).
    """
    try:
        if response:
            response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
            response.headers["Pragma"] = "no-cache"
            response.headers["Expires"] = "0"
        
        # Validate period
        try:
            Period(period)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid period. Use 'daily', 'weekly', or 'monthly'")
        
        service = StatisticsService(db)
        growth_data = service.get_growth_metrics(period=period, months=months, user=current_user)
        
        # Convert to schema format
        return GrowthMetrics(
            datasets_timeline=[TimeSeriesPoint(**p) for p in growth_data["datasets_timeline"]],
            providers_timeline=[TimeSeriesPoint(**p) for p in growth_data["providers_timeline"]],
            validation_timeline=[TimeSeriesPoint(**p) for p in growth_data["validation_timeline"]]
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting growth timeline: {e}")
        raise HTTPException(status_code=500, detail="Error retrieving growth timeline")


@router.get("/providers", summary="Provider statistics")
async def get_provider_list_stats(
    limit: int = Query(20, ge=1, le=100, description="Number of top providers to show"),
    db: Session = Depends(get_sync_db),
    current_user: Optional[UserModel] = Depends(get_current_user_optional),
    response: Response = None
) -> Dict[str, Any]:
    """
    Get statistics about data providers.
    Shows aggregated information about top contributing providers.
    Available to all users.
    """
    try:
        if response:
            response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
            response.headers["Pragma"] = "no-cache"
            response.headers["Expires"] = "0"
        
        service = StatisticsService(db)
        return service.get_provider_list_stats(limit=limit, user=current_user)
        
    except Exception as e:
        logger.error(f"Error getting provider list stats: {e}")
        raise HTTPException(status_code=500, detail="Error retrieving provider statistics")


@router.get("/providers/{provider_id}", response_model=ProviderStats, summary="Provider-specific statistics")
async def get_provider_statistics(
    provider_id: int,
    db: Session = Depends(get_sync_db),
    current_user: UserModel = Depends(get_current_user_sync)
) -> ProviderStats:
    """
    Get statistics for a specific data provider.
    Requires authentication.
    Users can access their own provider statistics, admins can access any.
    """
    try:
        service = StatisticsService(db)
        stats = service.get_provider_statistics(provider_id=provider_id, user=current_user)
        
        if not stats:
            raise HTTPException(status_code=404, detail="Provider not found")
        
        # Check permissions - admins can access any, users can access their own providers
        # TODO: Implement proper provider-level permission checking
        # For now, allowing access to any provider for authenticated users
        
        return ProviderStats(**stats)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting provider {provider_id} statistics: {e}")
        raise HTTPException(status_code=500, detail="Error retrieving provider statistics")


@router.get("/datasets/recent", summary="Recent dataset activity")
async def get_recent_dataset_activity(
    limit: int = Query(10, ge=1, le=50, description="Number of recent activities to show"),
    days: int = Query(30, ge=1, le=90, description="Number of days to look back"),
    db: Session = Depends(get_sync_db),
    current_user: Optional[UserModel] = Depends(get_current_user_optional),
    response: Response = None
) -> Dict[str, Any]:
    """
    Get recent dataset registration and modification activity.
    Available to all users.
    """
    try:
        if response:
            response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
            response.headers["Pragma"] = "no-cache"
            response.headers["Expires"] = "0"
        
        service = StatisticsService(db)
        return service.get_recent_activity(limit=limit, days=days, user=current_user)
        
    except Exception as e:
        logger.error(f"Error getting recent dataset activity: {e}")
        raise HTTPException(status_code=500, detail="Error retrieving recent activity")


@router.get("/datasets/{dataset_id}", response_model=DatasetStats, summary="Dataset-specific statistics")
async def get_dataset_statistics(
    dataset_id: int,
    db: Session = Depends(get_sync_db),
    current_user: UserModel = Depends(get_current_user_sync)
) -> DatasetStats:
    """
    Get statistics for a specific dataset.
    Requires authentication.
    """
    try:
        service = StatisticsService(db)
        stats = service.get_dataset_statistics(dataset_id=dataset_id, user=current_user)
        
        if not stats:
            raise HTTPException(status_code=404, detail="Dataset not found")
        
        return DatasetStats(**stats)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting dataset {dataset_id} statistics: {e}")
        raise HTTPException(status_code=500, detail="Error retrieving dataset statistics")


@router.get("/health", summary="Registry health status")
async def get_registry_health(
    db: Session = Depends(get_sync_db),
    current_user: Optional[UserModel] = Depends(get_current_user_optional),
    response: Response = None
) -> Dict[str, Any]:
    """
    Get basic health metrics of the registry system.
    Available to all users.
    """
    try:
        if response:
            response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
            response.headers["Pragma"] = "no-cache"
            response.headers["Expires"] = "0"
        
        service = StatisticsService(db)
        return service.get_health_status(user=current_user)
        
    except Exception as e:
        logger.error(f"Error getting registry health: {e}")
        raise HTTPException(status_code=500, detail="Error retrieving health status")


@router.get("/time-series", response_model=TimeSeriesResponse, summary="Time series data")
async def get_time_series_data(
    metric_type: str = Query(..., description="Metric type to retrieve"),
    entity_type: str = Query(..., description="Entity type"),
    entity_id: Optional[int] = Query(None, description="Entity ID (null for system-wide)"),
    period: str = Query(Period.DAILY.value, description="Time period"),
    start_date: Optional[date] = Query(None, description="Start date"),
    end_date: Optional[date] = Query(None, description="End date"),
    limit: int = Query(30, ge=1, le=365, description="Maximum data points"),
    db: Session = Depends(get_sync_db),
    current_user: Optional[UserModel] = Depends(get_current_user_optional)
) -> TimeSeriesResponse:
    """
    Get time series data for a specific metric.
    - Public users: Can access public metrics only
    - Authenticated users: Can access all metrics
    """
    try:
        # Define public metrics
        PUBLIC_METRICS = [
            MetricType.DATASET_COUNT.value,
            MetricType.PROVIDER_COUNT.value,
            MetricType.DATASET_REGISTRATION_RATE.value,
            MetricType.VALIDATION_SUCCESS_RATE.value
        ]
        
        # Check if metric requires authentication
        if metric_type not in PUBLIC_METRICS and not current_user:
            raise HTTPException(
                status_code=401, 
                detail="Authentication required for this metric"
            )
        
        # Validate enum values
        try:
            MetricType(metric_type)
            EntityType(entity_type)
            Period(period)
        except ValueError as e:
            raise HTTPException(status_code=400, detail=f"Invalid parameter: {e}")
        
        service = StatisticsService(db)
        data = service.get_time_series_data(
            metric_type=metric_type,
            entity_type=entity_type,
            entity_id=entity_id,
            period=period,
            start_date=start_date,
            end_date=end_date,
            limit=limit,
            user=current_user,
            include_today=True
        )
        
        # Convert to response format
        return TimeSeriesResponse(
            metric_type=data["metric_type"],
            entity_type=data["entity_type"],
            entity_id=data["entity_id"],
            period=data["period"],
            data_points=[TimeSeriesPoint(**p) for p in data["data_points"]],
            total_points=data["total_points"]
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting time series data: {e}")
        raise HTTPException(status_code=500, detail="Error retrieving time series data")


@router.get("/biological-units-timeline", response_model=TimeSeriesResponse, summary="Biological units timeline")
async def get_biological_units_timeline(
    period: str = Query(Period.DAILY.value, description="Time period"),
    start_date: Optional[date] = Query(None, description="Start date"),
    end_date: Optional[date] = Query(None, description="End date"),
    limit: int = Query(30, ge=1, le=365, description="Maximum data points"),
    db: Session = Depends(get_sync_db),
    current_user: UserModel = Depends(get_current_user_sync)
) -> TimeSeriesResponse:
    """
    Get system-wide biological units timeline.
    Requires authentication.
    Aggregates provider biological units for system-wide view.
    """
    try:
        # Validate period
        try:
            Period(period)
        except ValueError as e:
            raise HTTPException(status_code=400, detail=f"Invalid period: {e}")
        
        # Use the service to get time series data for biological units
        service = StatisticsService(db)
        
        # Query to aggregate biological units across all providers
        from sqlalchemy import func, and_, desc
        from app.models import StatisticModel, MetricType, EntityType
        
        base_query = db.query(
            StatisticModel.date,
            func.sum(StatisticModel.value).label('total_units')
        ).filter(
            and_(
                StatisticModel.metric_type == MetricType.PROVIDER_BIOLOGICAL_UNITS,
                StatisticModel.entity_type == EntityType.PROVIDER,
                StatisticModel.period == period
            )
        )
        
        if start_date:
            base_query = base_query.filter(StatisticModel.date >= start_date)
        if end_date:
            base_query = base_query.filter(StatisticModel.date <= end_date)
        
        # Group by date to aggregate across providers
        aggregated_stats = base_query.group_by(
            StatisticModel.date
        ).order_by(desc(StatisticModel.date)).limit(limit).all()
        
        # Convert to time series points
        data_points = []
        for stat in reversed(aggregated_stats):  # Reverse for chronological order
            data_points.append(
                TimeSeriesPoint(
                    date=stat.date,
                    value=float(stat.total_units) if stat.total_units is not None else 0.0,
                    extra_data={'aggregated_from_providers': True}
                )
            )
        
        return TimeSeriesResponse(
            metric_type=MetricType.PROVIDER_BIOLOGICAL_UNITS.value,
            entity_type=EntityType.SYSTEM.value,
            entity_id=None,
            period=period,
            data_points=data_points,
            total_points=len(data_points)
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting biological units timeline: {e}")
        raise HTTPException(status_code=500, detail="Error retrieving biological units timeline")


@router.get("/multi-provider-biological-units", response_model=Dict[str, Any], summary="Multi-provider biological units")
async def get_multi_provider_biological_units_timeline(
    period: str = Query(Period.DAILY.value, description="Time period"),
    start_date: Optional[date] = Query(None, description="Start date"),
    end_date: Optional[date] = Query(None, description="End date"),
    limit: int = Query(30, ge=1, le=365, description="Maximum data points"),
    db: Session = Depends(get_sync_db),
    current_user: UserModel = Depends(get_current_user_sync)
) -> Dict[str, Any]:
    """
    Get biological units timeline for all providers simultaneously.
    Requires authentication.
    Returns data structured for multi-line chart display.
    """
    try:
        # Validate period
        try:
            Period(period)
        except ValueError as e:
            raise HTTPException(status_code=400, detail=f"Invalid period: {e}")
        
        # Query to get biological units data for each provider
        from sqlalchemy import func, and_, desc
        from app.models import StatisticModel, DataProviderModel, MetricType, EntityType
        
        base_query = db.query(
            StatisticModel.date,
            StatisticModel.entity_id.label('provider_id'),
            func.max(StatisticModel.value).label('units')
        ).join(
            DataProviderModel, DataProviderModel.id == StatisticModel.entity_id
        ).filter(
            and_(
                StatisticModel.metric_type == MetricType.PROVIDER_BIOLOGICAL_UNITS,
                StatisticModel.entity_type == EntityType.PROVIDER,
                StatisticModel.period == period
            )
        )
        
        if start_date:
            base_query = base_query.filter(StatisticModel.date >= start_date)
        if end_date:
            base_query = base_query.filter(StatisticModel.date <= end_date)
        
        # Group by date and provider
        stats_data = base_query.group_by(
            StatisticModel.date,
            StatisticModel.entity_id
        ).order_by(desc(StatisticModel.date)).all()
        
        # Get provider names
        provider_names = dict(
            db.query(DataProviderModel.id, DataProviderModel.name).all()
        )
        
        # Transform data into multi-line chart format
        date_data = {}
        
        for stat in stats_data:
            date_str = stat.date.isoformat()
            provider_name = provider_names.get(stat.provider_id, f"Provider {stat.provider_id}")
            
            if date_str not in date_data:
                date_data[date_str] = {'date': date_str}
            
            date_data[date_str][provider_name] = float(stat.units) if stat.units is not None else 0.0
        
        # Convert to list and sort by date
        data_points = list(date_data.values())
        data_points.sort(key=lambda x: x['date'])
        data_points = data_points[-limit:] if len(data_points) > limit else data_points
        
        # Get list of all providers
        all_providers = set()
        for point in data_points:
            all_providers.update(key for key in point.keys() if key != 'date')
        
        # Ensure all data points have all provider fields
        for point in data_points:
            for provider in all_providers:
                if provider not in point:
                    point[provider] = 0.0
        
        # Get provider metadata
        provider_metadata = []
        for provider_id, provider_name in provider_names.items():
            if provider_name in all_providers:
                provider_metadata.append({
                    'id': provider_id,
                    'name': provider_name,
                    'key': provider_name
                })
        
        return {
            'metric_type': MetricType.PROVIDER_BIOLOGICAL_UNITS.value,
            'entity_type': 'multi_provider',
            'period': period,
            'data_points': data_points,
            'total_points': len(data_points),
            'providers': provider_metadata,
            'total_providers': len(provider_metadata)
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting multi-provider biological units timeline: {e}")
        raise HTTPException(status_code=500, detail="Error retrieving multi-provider biological units timeline")


@router.get("/search", response_model=List[StatisticResponse], summary="Search statistics")
async def search_statistics(
    query: StatisticsQuery = Depends(),
    db: Session = Depends(get_sync_db),
    current_user: UserModel = Depends(get_current_user_sync)
) -> List[StatisticResponse]:
    """
    Search and filter statistics with various criteria.
    Requires authentication.
    """
    try:
        # Build base query
        from app.models import StatisticModel
        base_query = db.query(StatisticModel)
        
        # Apply filters
        if query.metric_types:
            base_query = base_query.filter(StatisticModel.metric_type.in_(query.metric_types))
        
        if query.entity_types:
            base_query = base_query.filter(StatisticModel.entity_type.in_(query.entity_types))
        
        if query.entity_ids:
            base_query = base_query.filter(StatisticModel.entity_id.in_(query.entity_ids))
        
        if query.periods:
            base_query = base_query.filter(StatisticModel.period.in_(query.periods))
        
        if query.start_date:
            base_query = base_query.filter(StatisticModel.date >= query.start_date)
        
        if query.end_date:
            base_query = base_query.filter(StatisticModel.date <= query.end_date)
        
        # Apply pagination and ordering
        from sqlalchemy import desc
        statistics = base_query.order_by(
            desc(StatisticModel.date)
        ).offset(query.offset).limit(query.limit).all()
        
        return [StatisticResponse.model_validate(stat) for stat in statistics]
        
    except Exception as e:
        logger.error(f"Error searching statistics: {e}")
        raise HTTPException(status_code=500, detail="Error searching statistics")


# Admin-only trigger endpoints

@router.post("/collect", summary="Trigger statistics collection")
async def trigger_statistics_collection(
    background_tasks: BackgroundTasks,
    target_date: Optional[str] = Query(None, description="Target date (YYYY-MM-DD)"),
    current_user: UserModel = Depends(require_admin)
) -> Dict[str, Any]:
    """
    Manually trigger statistics collection.
    Requires admin permissions.
    """
    try:
        # Validate date format if provided
        if target_date:
            try:
                datetime.strptime(target_date, "%Y-%m-%d")
            except ValueError:
                raise HTTPException(status_code=400, detail="Invalid date format. Use YYYY-MM-DD")
        
        # Queue the statistics collection task
        background_tasks.add_task(collect_daily_statistics.delay, target_date)
        
        return {
            "message": "Statistics collection task has been queued",
            "target_date": target_date or "yesterday",
            "status": "queued"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error triggering statistics collection: {e}")
        raise HTTPException(status_code=500, detail="Error triggering statistics collection")


@router.post("/analyze-xml", summary="Trigger XML analysis")
async def trigger_xml_analysis(
    background_tasks: BackgroundTasks,
    batch_size: int = Query(50, ge=1, le=200, description="Batch size for processing"),
    offset: int = Query(0, ge=0, description="Starting offset"),
    current_user: UserModel = Depends(require_admin)
) -> Dict[str, Any]:
    """
    Manually trigger XML archive analysis.
    Requires admin permissions.
    """
    try:
        # Queue the XML analysis task
        background_tasks.add_task(analyze_xml_archives.delay, batch_size, offset)
        
        return {
            "message": "XML analysis task has been queued",
            "batch_size": batch_size,
            "offset": offset,
            "status": "queued"
        }
        
    except Exception as e:
        logger.error(f"Error triggering XML analysis: {e}")
        raise HTTPException(status_code=500, detail="Error triggering XML analysis")


@router.post("/collect-provider-biological-units", summary="Trigger provider biological units collection")
async def trigger_provider_biological_units_collection(
    background_tasks: BackgroundTasks,
    target_date: Optional[str] = Query(None, description="Target date (YYYY-MM-DD)"),
    current_user: UserModel = Depends(require_admin)
) -> Dict[str, Any]:
    """
    Manually trigger provider biological units collection.
    Requires admin permissions.
    """
    try:
        # Validate date format if provided
        if target_date:
            try:
                datetime.strptime(target_date, "%Y-%m-%d")
            except ValueError:
                raise HTTPException(status_code=400, detail="Invalid date format. Use YYYY-MM-DD")
        
        # Queue the task
        background_tasks.add_task(collect_provider_biological_units.delay, target_date)
        
        return {
            "message": "Provider biological units collection task has been queued",
            "target_date": target_date or "yesterday",
            "status": "queued"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error triggering provider biological units collection: {e}")
        raise HTTPException(status_code=500, detail="Error triggering provider biological units collection")