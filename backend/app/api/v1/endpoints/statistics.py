"""
Statistics API endpoints for internal authenticated access.
"""
import logging
from datetime import datetime, date, timedelta
from typing import List, Dict, Any, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, BackgroundTasks, Response
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
    StatisticResponse,
    TimeSeriesResponse,
    StatisticsQuery,
    OverviewStats,
    ProviderStats,
    DatasetStats,
    QualityMetrics,
    TimeSeriesPoint
)
from app.security.permissions import require_admin, get_current_user_sync as get_current_user
from app.models.user import UserModel
from app.tasks.statistics_tasks import collect_daily_statistics, analyze_xml_archives

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/overview", response_model=OverviewStats, summary="System-wide statistics overview")
async def get_system_overview(
    db: Session = Depends(get_sync_db),
    current_user: UserModel = Depends(require_admin)
) -> OverviewStats:
    """
    Get system-wide statistics overview.
    Requires admin permissions.
    Real-time data with no caching for immediate updates.
    """
    try:
        # Get real-time counts directly from database for immediate accuracy
        
        # Use direct database queries for real-time data instead of cached statistics
        total_datasets = db.query(func.count(DatasetModel.id)).scalar()
        total_providers = db.query(func.count(DataProviderModel.id)).scalar()
        total_archives = db.query(func.count(XmlArchiveModel.id)).scalar()
        
        # Get actual data center count (providers marked as data centers)
        total_datacenters = db.query(func.count(DataProviderModel.id)).filter(
            DataProviderModel.isDataCenter == True
        ).scalar()
        
        # Get validation success rate - calculate in real-time for accuracy
        validation_success_rate = None
        thirty_days_ago = date.today() - timedelta(days=30)
        recent_jobs = db.query(ValidationJobModel).filter(
            ValidationJobModel.created_at >= thirty_days_ago
        ).all()
        
        if recent_jobs:
            total_validations = len(recent_jobs)
            successful_validations = len([job for job in recent_jobs 
                                        if job.status == 'completed' and job.valid_files == job.total_files and job.total_files > 0])
            validation_success_rate = (successful_validations / total_validations * 100) if total_validations > 0 else 0
        
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
        logger.error(f"Error getting system overview: {e}")
        raise HTTPException(status_code=500, detail="Error retrieving system statistics")


@router.get("/providers/{provider_id}", response_model=ProviderStats, summary="Provider-specific statistics")
async def get_provider_statistics(
    provider_id: int,
    db: Session = Depends(get_sync_db),
    current_user: UserModel = Depends(get_current_user)
) -> ProviderStats:
    """
    Get statistics for a specific data provider.
    Users can access their own provider statistics, admins can access any.
    """
    # Get provider details
    provider = db.query(DataProviderModel).filter(DataProviderModel.id == provider_id).first()
    if not provider:
        raise HTTPException(status_code=404, detail="Provider not found")
    
    # Check permissions - admins can access any, users can access their own providers
    if not current_user.is_global_admin:
        # Check if user has access to this provider (implement your permission logic here)
        # For now, allowing access to any provider for authenticated users
        pass
    
    try:
        # Get real-time dataset count for this provider
        dataset_count = db.query(func.count(DatasetModel.id)).filter(
            DatasetModel.provider_id == provider_id
        ).scalar()
        
        # Get XML archive count for this provider's datasets
        xml_archive_count = db.query(func.count(XmlArchiveModel.id)).join(
            DatasetModel, XmlArchiveModel.dataset_id == DatasetModel.id
        ).filter(DatasetModel.provider_id == provider_id).scalar()
        
        # Calculate validation success rate for this provider
        validation_jobs_query = db.query(ValidationJobModel).join(
            XmlArchiveModel, ValidationJobModel.archive_id == XmlArchiveModel.id
        ).join(
            DatasetModel, XmlArchiveModel.dataset_id == DatasetModel.id
        ).filter(DatasetModel.provider_id == provider_id)
        
        total_jobs = validation_jobs_query.count()
        successful_jobs = validation_jobs_query.filter(
            and_(
                ValidationJobModel.status == 'completed',
                ValidationJobModel.valid_files == ValidationJobModel.total_files,
                ValidationJobModel.total_files > 0
            )
        ).count()
        
        validation_success_rate = (successful_jobs / total_jobs * 100) if total_jobs > 0 else None
        
        # Get last activity (latest dataset update)
        last_activity = db.query(func.max(DatasetModel.updated_at)).filter(
            DatasetModel.provider_id == provider_id
        ).scalar()
        
        # Calculate activity score (based on recent dataset activity)
        activity_score = None
        if last_activity:
            days_since_activity = (datetime.utcnow() - last_activity).days
            # Simple activity score: 100 for activity today, decreasing over time
            activity_score = max(0, 100 - days_since_activity * 2)
        
        return ProviderStats(
            provider_id=provider_id,
            provider_name=provider.name,
            dataset_count=dataset_count,
            xml_archive_count=xml_archive_count,
            validation_success_rate=validation_success_rate,
            last_activity=last_activity,
            activity_score=activity_score
        )
        
    except Exception as e:
        logger.error(f"Error getting provider {provider_id} statistics: {e}")
        raise HTTPException(status_code=500, detail="Error retrieving provider statistics")


@router.get("/datasets/{dataset_id}", response_model=DatasetStats, summary="Dataset-specific statistics")
async def get_dataset_statistics(
    dataset_id: int,
    db: Session = Depends(get_sync_db),
    current_user: UserModel = Depends(get_current_user)
) -> DatasetStats:
    """
    Get statistics for a specific dataset.
    """
    # Get dataset details
    dataset = db.query(DatasetModel).filter(DatasetModel.id == dataset_id).first()
    if not dataset:
        raise HTTPException(status_code=404, detail="Dataset not found")
    
    try:
        # For real-time data, calculate unit count and citation completeness dynamically
        # Note: These may require additional logic to calculate in real-time
        # For now, we'll check the latest statistics but not rely on them exclusively
        latest_unit_stat = db.query(StatisticModel).filter(
            and_(
                StatisticModel.metric_type == MetricType.DATASET_UNIT_COUNT,
                StatisticModel.entity_type == EntityType.DATASET,
                StatisticModel.entity_id == dataset_id
            )
        ).order_by(desc(StatisticModel.date)).first()
        
        unit_count = int(latest_unit_stat.value) if latest_unit_stat else None
        
        citation_stat = db.query(StatisticModel).filter(
            and_(
                StatisticModel.metric_type == MetricType.CITATION_COMPLETENESS,
                StatisticModel.entity_type == EntityType.DATASET,
                StatisticModel.entity_id == dataset_id
            )
        ).order_by(desc(StatisticModel.date)).first()
        
        citation_completeness = citation_stat.value if citation_stat else None
        
        # Get latest validation status
        latest_validation = db.query(ValidationJobModel).join(
            XmlArchiveModel, ValidationJobModel.archive_id == XmlArchiveModel.id
        ).filter(
            XmlArchiveModel.dataset_id == dataset_id
        ).order_by(desc(ValidationJobModel.created_at)).first()
        
        validation_status = latest_validation.status if latest_validation else None
        
        return DatasetStats(
            dataset_id=dataset_id,
            dataset_title=dataset.title or "Untitled",
            provider_id=dataset.provider_id,
            unit_count=unit_count,
            last_modified=dataset.updated_at,
            validation_status=validation_status,
            citation_completeness=citation_completeness
        )
        
    except Exception as e:
        logger.error(f"Error getting dataset {dataset_id} statistics: {e}")
        raise HTTPException(status_code=500, detail="Error retrieving dataset statistics")


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
    current_user: UserModel = Depends(get_current_user)
) -> TimeSeriesResponse:
    """
    Get time series data for a specific metric.
    """
    try:
        # Validate enum values
        try:
            MetricType(metric_type)
            EntityType(entity_type)
            Period(period)
        except ValueError as e:
            raise HTTPException(status_code=400, detail=f"Invalid parameter: {e}")
        
        # Build aggregated query to prevent duplicate points per date
        from sqlalchemy import func
        
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
        aggregated_stats = base_query.group_by(StatisticModel.date).order_by(desc(StatisticModel.date)).limit(limit).all()
        
        # Convert to time series points with proper date binning
        data_points = [
            TimeSeriesPoint(
                date=stat.date,
                value=float(stat.value) if stat.value is not None else 0.0,
                extra_data={'records_aggregated': stat.count}
            )
            for stat in reversed(aggregated_stats)  # Reverse to get chronological order
        ]
        
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
        logger.error(f"Error getting time series data: {e}")
        raise HTTPException(status_code=500, detail="Error retrieving time series data")


@router.get("/quality", response_model=QualityMetrics, summary="Data quality metrics")
async def get_quality_metrics(
    db: Session = Depends(get_sync_db),
    current_user: UserModel = Depends(require_admin)
) -> QualityMetrics:
    """
    Get overall data quality metrics.
    Requires admin permissions.
    """
    try:
        # Get validation job statistics
        total_validations = db.query(func.count(ValidationJobModel.id)).scalar()
        successful_validations = db.query(func.count(ValidationJobModel.id)).filter(
            and_(
                ValidationJobModel.status == 'completed',
                ValidationJobModel.valid_files == ValidationJobModel.total_files,
                ValidationJobModel.total_files > 0
            )
        ).scalar()
        failed_validations = total_validations - successful_validations
        
        success_rate = (successful_validations / total_validations * 100) if total_validations > 0 else 0
        
        # Get ABCD compliance rate from statistics
        abcd_compliance_rate = None
        latest_compliance_stat = db.query(StatisticModel).filter(
            and_(
                StatisticModel.metric_type == MetricType.ABCD_COMPLIANCE_RATE,
                StatisticModel.entity_type == EntityType.SYSTEM
            )
        ).order_by(desc(StatisticModel.date)).first()
        
        if latest_compliance_stat:
            abcd_compliance_rate = latest_compliance_stat.value
        
        # Calculate average processing time
        avg_processing_time = db.query(func.avg(ValidationJobModel.validation_time)).filter(
            and_(
                ValidationJobModel.status == 'completed',
                ValidationJobModel.validation_time.isnot(None)
            )
        ).scalar()
        
        return QualityMetrics(
            total_validations=total_validations,
            successful_validations=successful_validations,
            failed_validations=failed_validations,
            success_rate=success_rate,
            abcd_compliance_rate=abcd_compliance_rate,
            average_processing_time=float(avg_processing_time) if avg_processing_time else None
        )
        
    except Exception as e:
        logger.error(f"Error getting quality metrics: {e}")
        raise HTTPException(status_code=500, detail="Error retrieving quality metrics")


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


@router.get("/search", response_model=List[StatisticResponse], summary="Search statistics")
async def search_statistics(
    query: StatisticsQuery = Depends(),
    db: Session = Depends(get_sync_db),
    current_user: UserModel = Depends(get_current_user)
) -> List[StatisticResponse]:
    """
    Search and filter statistics with various criteria.
    """
    try:
        # Build base query
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
        statistics = base_query.order_by(desc(StatisticModel.date)).offset(query.offset).limit(query.limit).all()
        
        return [StatisticResponse.model_validate(stat) for stat in statistics]
        
    except Exception as e:
        logger.error(f"Error searching statistics: {e}")
        raise HTTPException(status_code=500, detail="Error searching statistics")