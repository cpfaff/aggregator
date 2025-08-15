"""
Public statistics API endpoints for external users (no authentication required).
"""
import logging
from datetime import datetime, date, timedelta
from typing import List, Dict, Any, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, Response
from fastapi.responses import JSONResponse
from sqlalchemy import func, and_, desc, distinct
from sqlalchemy.orm import Session

from app.db.session import get_sync_db
from app.models import (
    StatisticModel,
    DataProviderModel, 
    DatasetModel,
    XmlArchiveModel,
    ValidationJobModel,
    MetricType,
    EntityType,
    Period
)
from app.schemas.statistics import (
    TimeSeriesResponse,
    OverviewStats,
    QualityMetrics,
    GrowthMetrics,
    TimeSeriesPoint
)

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/overview", response_model=OverviewStats, summary="Public registry overview")
async def get_public_overview(
    db: Session = Depends(get_sync_db),
    response: Response = None
) -> OverviewStats:
    """
    Get public overview statistics of the registry.
    No authentication required - shows basic registry information.
    Real-time data with no caching for immediate updates.
    """
    try:
        # Set no-cache headers for real-time updates
        if response:
            response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
            response.headers["Pragma"] = "no-cache"
            response.headers["Expires"] = "0"
        
        # Get real-time counts directly from database for immediate accuracy
        
        # Use direct database queries for real-time data instead of cached statistics
        total_datasets = db.query(func.count(DatasetModel.id)).scalar()
        total_providers = db.query(func.count(DataProviderModel.id)).scalar()
        total_archives = db.query(func.count(XmlArchiveModel.id)).scalar()
        
        # Get actual data center count (providers marked as data centers)
        total_datacenters = db.query(func.count(DataProviderModel.id)).filter(
            DataProviderModel.isDataCenter == True
        ).scalar()
        
        # Get public validation success rate (last 30 days only for performance)
        validation_success_rate = None
        recent_validation_stat = db.query(StatisticModel).filter(
            and_(
                StatisticModel.metric_type == MetricType.VALIDATION_SUCCESS_RATE,
                StatisticModel.entity_type == EntityType.SYSTEM,
                StatisticModel.period == Period.DAILY,
                StatisticModel.date >= date.today() - timedelta(days=30)
            )
        ).order_by(desc(StatisticModel.date)).first()
        
        if recent_validation_stat:
            validation_success_rate = recent_validation_stat.value
        
        # Set last updated to current time for real-time data
        last_updated = datetime.utcnow()
        
        return OverviewStats(
            total_datasets=total_datasets,
            total_providers=total_providers,
            total_datacenters=total_datacenters or 0,
            total_xml_archives=total_archives,
            validation_success_rate=validation_success_rate,
            last_updated=last_updated
        )
        
    except Exception as e:
        logger.error(f"Error getting public overview: {e}")
        raise HTTPException(status_code=500, detail="Error retrieving registry statistics")


@router.get("/timeline", response_model=GrowthMetrics, summary="Registry growth timeline")
async def get_growth_timeline(
    period: str = Query(Period.MONTHLY.value, description="Time period for aggregation"),
    months: int = Query(12, ge=1, le=60, description="Number of months to retrieve"),
    db: Session = Depends(get_sync_db),
    response: Response = None
) -> GrowthMetrics:
    """
    Get registry growth metrics over time.
    Shows dataset and provider growth trends for public viewing.
    Real-time data with no caching for immediate updates.
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
        
        # Calculate date range
        end_date = date.today()
        if period == Period.MONTHLY.value:
            start_date = end_date - timedelta(days=months * 30)
        elif period == Period.WEEKLY.value:
            start_date = end_date - timedelta(weeks=months * 4)
        else:  # daily
            start_date = end_date - timedelta(days=months * 30)
        
        # Get dataset growth timeline - use GROUP BY aggregation for proper date handling
        dataset_stats_raw = db.query(
            StatisticModel.date,
            func.max(StatisticModel.value).label('value'),
            func.count(StatisticModel.id).label('count')
        ).filter(
            and_(
                StatisticModel.metric_type == MetricType.DATASET_COUNT,
                StatisticModel.entity_type == EntityType.SYSTEM,
                StatisticModel.period == period,
                StatisticModel.date >= start_date,
                StatisticModel.date <= end_date
            )
        ).group_by(StatisticModel.date).order_by(StatisticModel.date).all()
        
        # Get provider growth timeline - use GROUP BY aggregation for proper date handling
        provider_stats_raw = db.query(
            StatisticModel.date,
            func.max(StatisticModel.value).label('value'),
            func.count(StatisticModel.id).label('count')
        ).filter(
            and_(
                StatisticModel.metric_type == MetricType.PROVIDER_COUNT,
                StatisticModel.entity_type == EntityType.SYSTEM,
                StatisticModel.period == period,
                StatisticModel.date >= start_date,
                StatisticModel.date <= end_date
            )
        ).group_by(StatisticModel.date).order_by(StatisticModel.date).all()
        
        # Get validation activity timeline (using registration rate as proxy for activity)
        validation_stats_raw = db.query(
            StatisticModel.date,
            func.sum(StatisticModel.value).label('value'),
            func.count(StatisticModel.id).label('count')
        ).filter(
            and_(
                StatisticModel.metric_type == MetricType.DATASET_REGISTRATION_RATE,
                StatisticModel.entity_type == EntityType.SYSTEM,
                StatisticModel.period == period,
                StatisticModel.date >= start_date,
                StatisticModel.date <= end_date
            )
        ).group_by(StatisticModel.date).order_by(StatisticModel.date).all()
        
        # Convert to time series points
        datasets_timeline = [
            TimeSeriesPoint(
                date=stat.date,
                value=float(stat.value) if stat.value is not None else 0.0,
                extra_data={'records_aggregated': stat.count}
            )
            for stat in dataset_stats_raw
        ]
        
        providers_timeline = [
            TimeSeriesPoint(
                date=stat.date,
                value=float(stat.value) if stat.value is not None else 0.0,
                extra_data={'records_aggregated': stat.count}
            )
            for stat in provider_stats_raw
        ]
        
        validation_timeline = [
            TimeSeriesPoint(
                date=stat.date,
                value=float(stat.value) if stat.value is not None else 0.0,
                extra_data={'records_aggregated': stat.count}
            )
            for stat in validation_stats_raw
        ]
        
        # Add today's data if there are new dataset registrations (hybrid approach)
        today = date.today()
        today_start = datetime.combine(today, datetime.min.time())
        
        # Check if today is missing from historical data and if there are new registrations today
        has_today_data = any(point.date == today for point in datasets_timeline)
        
        if not has_today_data:
            # Get today's dataset registrations count
            todays_new_datasets = db.query(func.count(DatasetModel.id)).filter(
                DatasetModel.created_at >= today_start
            ).scalar() or 0
            
            # Only add today's data point if there are actual registrations
            if todays_new_datasets > 0:
                # Get current total dataset count for today's cumulative value
                current_total_datasets = db.query(func.count(DatasetModel.id)).scalar() or 0
                
                # Add today's data point to datasets timeline
                datasets_timeline.append(TimeSeriesPoint(
                    date=today,
                    value=float(current_total_datasets),
                    extra_data={
                        'records_aggregated': 1,
                        'is_current_day': True,
                        'new_registrations_today': todays_new_datasets
                    }
                ))
                
                # For providers timeline, add today's data if not already present
                has_today_providers = any(point.date == today for point in providers_timeline)
                if not has_today_providers:
                    current_total_providers = db.query(func.count(DataProviderModel.id)).scalar() or 0
                    providers_timeline.append(TimeSeriesPoint(
                        date=today,
                        value=float(current_total_providers),
                        extra_data={'records_aggregated': 1, 'is_current_day': True}
                    ))
                
                # For validation timeline, add today's validation activity if any
                has_today_validation = any(point.date == today for point in validation_timeline)
                if not has_today_validation:
                    todays_validations = db.query(func.count(ValidationJobModel.id)).filter(
                        ValidationJobModel.created_at >= today_start
                    ).scalar() or 0
                    
                    if todays_validations > 0:
                        validation_timeline.append(TimeSeriesPoint(
                            date=today,
                            value=float(todays_validations),
                            extra_data={
                                'records_aggregated': 1,
                                'is_current_day': True
                            }
                        ))
        
        return GrowthMetrics(
            datasets_timeline=datasets_timeline,
            providers_timeline=providers_timeline,
            validation_timeline=validation_timeline
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting growth timeline: {e}")
        raise HTTPException(status_code=500, detail="Error retrieving growth timeline")


@router.get("/quality", response_model=QualityMetrics, summary="Public data quality metrics")
async def get_public_quality_metrics(
    db: Session = Depends(get_sync_db),
    response: Response = None
) -> QualityMetrics:
    """
    Get public data quality metrics showing overall registry health.
    Limited to aggregated statistics for public consumption.
    Real-time data with no caching for immediate updates.
    """
    try:
        if response:
            response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
            response.headers["Pragma"] = "no-cache"
            response.headers["Expires"] = "0"
        
        # Get aggregated validation statistics (last 30 days for performance)
        thirty_days_ago = date.today() - timedelta(days=30)
        
        recent_jobs = db.query(ValidationJobModel).filter(
            ValidationJobModel.created_at >= thirty_days_ago
        ).all()
        
        total_validations = len(recent_jobs)
        successful_validations = len([job for job in recent_jobs 
                                    if job.status == 'completed' and job.valid_files == job.total_files and job.total_files > 0])
        failed_validations = total_validations - successful_validations
        
        success_rate = (successful_validations / total_validations * 100) if total_validations > 0 else 0
        
        # Get ABCD compliance rate from statistics
        abcd_compliance_rate = None
        latest_compliance_stat = db.query(StatisticModel).filter(
            and_(
                StatisticModel.metric_type == MetricType.ABCD_COMPLIANCE_RATE,
                StatisticModel.entity_type == EntityType.SYSTEM,
                StatisticModel.date >= thirty_days_ago
            )
        ).order_by(desc(StatisticModel.date)).first()
        
        if latest_compliance_stat:
            abcd_compliance_rate = latest_compliance_stat.value
        
        # Calculate average processing time (recent jobs only)
        processing_times = [job.validation_time for job in recent_jobs 
                          if job.validation_time is not None and job.status == 'completed']
        
        avg_processing_time = sum(processing_times) / len(processing_times) if processing_times else None
        
        return QualityMetrics(
            total_validations=total_validations,
            successful_validations=successful_validations,
            failed_validations=failed_validations,
            success_rate=success_rate,
            abcd_compliance_rate=abcd_compliance_rate,
            average_processing_time=avg_processing_time
        )
        
    except Exception as e:
        logger.error(f"Error getting public quality metrics: {e}")
        raise HTTPException(status_code=500, detail="Error retrieving quality metrics")


@router.get("/providers", summary="Public provider statistics")
async def get_public_provider_stats(
    limit: int = Query(20, ge=1, le=100, description="Number of top providers to show"),
    db: Session = Depends(get_sync_db),
    response: Response = None
) -> Dict[str, Any]:
    """
    Get public statistics about data providers.
    Shows aggregated information about top contributing providers.
    Real-time data with no caching for immediate updates.
    """
    try:
        if response:
            response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
            response.headers["Pragma"] = "no-cache"
            response.headers["Expires"] = "0"
        
        # Get provider dataset counts
        provider_stats = db.query(
            DataProviderModel.id,
            DataProviderModel.name,
            DataProviderModel.datacenter,
            func.count(DatasetModel.id).label('dataset_count')
        ).outerjoin(
            DatasetModel, DataProviderModel.id == DatasetModel.provider_id
        ).group_by(
            DataProviderModel.id, DataProviderModel.name, DataProviderModel.datacenter
        ).order_by(
            desc(func.count(DatasetModel.id))
        ).limit(limit).all()
        
        # Format response with biological units
        providers = []
        for provider_id, name, datacenter, dataset_count in provider_stats:
            # Get most recent biological units for this provider
            bio_units_stat = db.query(StatisticModel.value).filter(
                and_(
                    StatisticModel.metric_type == MetricType.PROVIDER_BIOLOGICAL_UNITS,
                    StatisticModel.entity_type == EntityType.PROVIDER,
                    StatisticModel.entity_id == provider_id
                )
            ).order_by(desc(StatisticModel.date)).first()
            
            biological_units = int(bio_units_stat[0]) if bio_units_stat and bio_units_stat[0] is not None else 0
            
            providers.append({
                "provider_id": provider_id,
                "name": name,
                "datacenter": datacenter,
                "dataset_count": dataset_count,
                "biological_units": biological_units
            })
        
        # Get datacenter statistics
        datacenter_stats = db.query(
            DataProviderModel.datacenter,
            func.count(DataProviderModel.id).label('provider_count'),
            func.count(DatasetModel.id).label('dataset_count')
        ).outerjoin(
            DatasetModel, DataProviderModel.id == DatasetModel.provider_id
        ).filter(
            DataProviderModel.datacenter.isnot(None)
        ).group_by(
            DataProviderModel.datacenter
        ).all()
        
        datacenters = []
        for datacenter, provider_count, dataset_count in datacenter_stats:
            datacenters.append({
                "datacenter": datacenter,
                "provider_count": provider_count,
                "dataset_count": dataset_count or 0
            })
        
        return {
            "top_providers": providers,
            "datacenters": datacenters,
            "total_providers": len(provider_stats),
            "last_updated": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error getting public provider stats: {e}")
        raise HTTPException(status_code=500, detail="Error retrieving provider statistics")


@router.get("/datasets/recent", summary="Recent dataset activity")
async def get_recent_dataset_activity(
    limit: int = Query(10, ge=1, le=50, description="Number of recent activities to show"),
    db: Session = Depends(get_sync_db),
    response: Response = None
) -> Dict[str, Any]:
    """
    Get recent dataset registration and modification activity.
    Shows publicly available information about registry activity.
    Real-time data with no caching for immediate updates.
    """
    try:
        if response:
            response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
            response.headers["Pragma"] = "no-cache"
            response.headers["Expires"] = "0"
        
        # Get recent dataset registrations (last 30 days)
        thirty_days_ago = datetime.utcnow() - timedelta(days=30)
        
        recent_datasets = db.query(
            DatasetModel.id,
            DatasetModel.title,
            DatasetModel.created_at,
            DatasetModel.updated_at,
            DataProviderModel.name.label('provider_name'),
            DataProviderModel.datacenter
        ).join(
            DataProviderModel, DatasetModel.provider_id == DataProviderModel.id
        ).filter(
            DatasetModel.created_at >= thirty_days_ago
        ).order_by(
            desc(DatasetModel.created_at)
        ).limit(limit).all()
        
        # Format recent registrations
        recent_registrations = []
        for dataset in recent_datasets:
            recent_registrations.append({
                "dataset_id": dataset.id,
                "title": dataset.title or "Untitled",
                "provider_name": dataset.provider_name,
                "datacenter": dataset.datacenter,
                "registered_at": dataset.created_at.isoformat(),
                "last_updated": dataset.updated_at.isoformat() if dataset.updated_at else None
            })
        
        # Get registration statistics for last 7 days
        week_ago = date.today() - timedelta(days=7)
        recent_registration_stats = db.query(StatisticModel).filter(
            and_(
                StatisticModel.metric_type == MetricType.DATASET_REGISTRATION_RATE,
                StatisticModel.entity_type == EntityType.SYSTEM,
                StatisticModel.period == Period.DAILY,
                StatisticModel.date >= week_ago
            )
        ).order_by(StatisticModel.date).all()
        
        weekly_registrations = [
            {
                "date": stat.date.isoformat(),
                "count": int(stat.value)
            }
            for stat in recent_registration_stats
        ]
        
        return {
            "recent_registrations": recent_registrations,
            "weekly_activity": weekly_registrations,
            "total_recent": len(recent_registrations),
            "period_days": 30,
            "last_updated": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error getting recent dataset activity: {e}")
        raise HTTPException(status_code=500, detail="Error retrieving recent activity")


@router.get("/health", summary="Registry health status")
async def get_registry_health(
    db: Session = Depends(get_sync_db),
    response: Response = None
) -> Dict[str, Any]:
    """
    Get basic health metrics of the registry system.
    Real-time data with no caching for immediate updates.
    """
    try:
        if response:
            response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
            response.headers["Pragma"] = "no-cache"
            response.headers["Expires"] = "0"
        
        # Get basic counts
        total_datasets = db.query(func.count(DatasetModel.id)).scalar()
        total_providers = db.query(func.count(DataProviderModel.id)).scalar()
        total_archives = db.query(func.count(XmlArchiveModel.id)).scalar()
        
        # Get recent validation activity (last 24 hours)
        yesterday = datetime.utcnow() - timedelta(hours=24)
        recent_validations = db.query(func.count(ValidationJobModel.id)).filter(
            ValidationJobModel.created_at >= yesterday
        ).scalar()
        
        successful_recent = db.query(func.count(ValidationJobModel.id)).filter(
            and_(
                ValidationJobModel.created_at >= yesterday,
                ValidationJobModel.status == 'completed'
            )
        ).scalar()
        
        # Calculate health score (0-100)
        health_score = 100
        if total_datasets == 0:
            health_score -= 30
        if total_archives == 0:
            health_score -= 20
        if recent_validations == 0:
            health_score -= 25
        elif successful_recent == 0:
            health_score -= 15
        elif successful_recent / recent_validations < 0.8:
            health_score -= 10
        
        return {
            "health_score": max(0, health_score),
            "status": "healthy" if health_score >= 80 else "warning" if health_score >= 60 else "critical",
            "metrics": {
                "total_datasets": total_datasets,
                "total_providers": total_providers,
                "total_archives": total_archives,
                "recent_validations_24h": recent_validations,
                "successful_validations_24h": successful_recent
            },
            "last_checked": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error getting registry health: {e}")
        raise HTTPException(status_code=500, detail="Error retrieving health status")


@router.get("/time-series", response_model=TimeSeriesResponse, summary="Public time series data")
async def get_public_time_series_data(
    metric_type: str = Query(..., description="Metric type to retrieve"),
    entity_type: str = Query(..., description="Entity type"),
    entity_id: Optional[int] = Query(None, description="Entity ID (null for system-wide)"),
    period: str = Query(Period.DAILY.value, description="Time period"),
    start_date: Optional[date] = Query(None, description="Start date"),
    end_date: Optional[date] = Query(None, description="End date"),
    limit: int = Query(30, ge=1, le=365, description="Maximum data points"),
    db: Session = Depends(get_sync_db),
    response: Response = None
) -> TimeSeriesResponse:
    """
    Get public time series data for a specific metric.
    
    Supported public metrics:
    - provider_biological_units: Total biological units per provider
    - dataset_count: Total number of datasets (system-wide)
    - provider_count: Total number of providers (system-wide)
    - provider_dataset_count: Number of datasets per provider
    """
    try:
        if response:
            response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
            response.headers["Pragma"] = "no-cache"
            response.headers["Expires"] = "0"
        
        # Define allowed public metrics to prevent access to sensitive data
        allowed_metrics = {
            MetricType.PROVIDER_BIOLOGICAL_UNITS.value,
            MetricType.DATASET_COUNT.value,
            MetricType.PROVIDER_COUNT.value,
            MetricType.PROVIDER_DATASET_COUNT.value,
        }
        
        if metric_type not in allowed_metrics:
            raise HTTPException(
                status_code=400, 
                detail=f"Metric type '{metric_type}' is not available for public access. "
                       f"Allowed metrics: {', '.join(allowed_metrics)}"
            )
        
        # Validate enum values
        try:
            MetricType(metric_type)
            EntityType(entity_type)
            Period(period)
        except ValueError as e:
            raise HTTPException(status_code=400, detail=f"Invalid parameter: {e}")
        
        # Build query with GROUP BY aggregation for proper date handling
        base_query = db.query(
            StatisticModel.date,
            func.max(StatisticModel.value).label('value'),
            func.count(StatisticModel.id).label('count')
        ).filter(
            and_(
                StatisticModel.metric_type == metric_type,
                StatisticModel.entity_type == entity_type,
                StatisticModel.period == period
            )
        )
        
        if entity_id is not None:
            base_query = base_query.filter(StatisticModel.entity_id == entity_id)
        else:
            base_query = base_query.filter(StatisticModel.entity_id.is_(None))
        
        if start_date:
            base_query = base_query.filter(StatisticModel.date >= start_date)
        if end_date:
            base_query = base_query.filter(StatisticModel.date <= end_date)
        
        # Group by date to aggregate and order by date descending, then limit
        stats = base_query.group_by(StatisticModel.date).order_by(desc(StatisticModel.date)).limit(limit).all()
        
        # Convert to time series points
        data_points = [
            TimeSeriesPoint(
                date=stat.date,
                value=float(stat.value) if stat.value is not None else 0.0,
                extra_data={'records_aggregated': stat.count}
            )
            for stat in reversed(stats)  # Reverse to get chronological order
        ]
        
        # For system-wide dataset count, add today's data if missing and there are new registrations
        today = date.today()
        today_start = datetime.combine(today, datetime.min.time())
        
        if (not any(point.date == today for point in data_points) and 
            metric_type == MetricType.DATASET_COUNT.value and 
            entity_type == EntityType.SYSTEM.value and 
            entity_id is None):
            
            # Get today's dataset registrations count
            todays_new_datasets = db.query(func.count(DatasetModel.id)).filter(
                DatasetModel.created_at >= today_start
            ).scalar() or 0
            
            # Only add today's data point if there are actual registrations
            if todays_new_datasets > 0:
                current_total_datasets = db.query(func.count(DatasetModel.id)).scalar() or 0
                data_points.append(TimeSeriesPoint(
                    date=today,
                    value=float(current_total_datasets),
                    extra_data={
                        'records_aggregated': 1,
                        'is_current_day': True,
                        'new_registrations_today': todays_new_datasets
                    }
                ))
        
        return TimeSeriesResponse(
            metric_type=metric_type,
            entity_type=entity_type,
            entity_id=entity_id,
            period=period,
            data_points=data_points,
            total_points=len(data_points)
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting public time series data: {e}")
        raise HTTPException(status_code=500, detail="Error retrieving public time series data")