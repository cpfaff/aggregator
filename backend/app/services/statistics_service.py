"""
Statistics service layer for shared business logic.
Provides a unified interface for statistics operations with role-based access control.
"""
import logging
from datetime import datetime, date, timedelta
from typing import Dict, Any, Optional, List
from sqlalchemy import func, and_, desc, distinct
from sqlalchemy.orm import Session

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
from app.models.user import UserModel

logger = logging.getLogger(__name__)


class StatisticsService:
    """Service class for statistics operations with role-based data filtering."""
    
    def __init__(self, db: Session):
        """Initialize the statistics service with a database session."""
        self.db = db
    
    def get_overview_stats(
        self, 
        user: Optional[UserModel] = None,
        include_sensitive: bool = False
    ) -> Dict[str, Any]:
        """
        Get system overview statistics with role-based filtering.
        
        Args:
            user: Current user (None for public access)
            include_sensitive: Include sensitive metrics (admin only)
            
        Returns:
            Dictionary containing overview statistics
        """
        # Base statistics available to everyone
        total_datasets = self.db.query(func.count(DatasetModel.id)).scalar()
        total_providers = self.db.query(func.count(DataProviderModel.id)).scalar()
        total_archives = self.db.query(func.count(XmlArchiveModel.id)).scalar()
        
        # Get actual data center count
        total_datacenters = self.db.query(func.count(DataProviderModel.id)).filter(
            DataProviderModel.isDataCenter == True
        ).scalar()
        
        # Calculate validation success rate (last 30 days)
        validation_success_rate = self._calculate_validation_success_rate(days=30)
        
        base_stats = {
            "total_datasets": total_datasets,
            "total_providers": total_providers,
            "total_datacenters": total_datacenters or 0,
            "total_xml_archives": total_archives,
            "validation_success_rate": validation_success_rate,
            "last_updated": datetime.utcnow()
        }
        
        # Add sensitive data for authenticated admin users
        if include_sensitive and user and user.is_global_admin:
            # Add additional admin-only metrics here if needed
            base_stats["detailed_metrics"] = self._get_detailed_admin_metrics()
        
        return base_stats
    
    def get_quality_metrics(
        self,
        user: Optional[UserModel] = None,
        days: int = 30
    ) -> Dict[str, Any]:
        """
        Get data quality metrics with optional role-based filtering.
        
        Args:
            user: Current user (None for public access)
            days: Number of days to look back for metrics
            
        Returns:
            Dictionary containing quality metrics
        """
        cutoff_date = date.today() - timedelta(days=days)
        
        # Get validation job statistics
        recent_jobs = self.db.query(ValidationJobModel).filter(
            ValidationJobModel.created_at >= cutoff_date
        ).all()
        
        total_validations = len(recent_jobs)
        successful_validations = len([
            job for job in recent_jobs 
            if job.status == 'completed' and 
            job.valid_files == job.total_files and 
            job.total_files > 0
        ])
        failed_validations = total_validations - successful_validations
        
        success_rate = (successful_validations / total_validations * 100) if total_validations > 0 else 0
        
        # Get ABCD compliance rate
        abcd_compliance_rate = None
        latest_compliance_stat = self.db.query(StatisticModel).filter(
            and_(
                StatisticModel.metric_type == MetricType.ABCD_COMPLIANCE_RATE,
                StatisticModel.entity_type == EntityType.SYSTEM,
                StatisticModel.date >= cutoff_date
            )
        ).order_by(desc(StatisticModel.date)).first()
        
        if latest_compliance_stat:
            abcd_compliance_rate = latest_compliance_stat.value
        
        # Calculate average processing time
        processing_times = [
            job.validation_time for job in recent_jobs 
            if job.validation_time is not None and job.status == 'completed'
        ]
        avg_processing_time = sum(processing_times) / len(processing_times) if processing_times else None
        
        return {
            "total_validations": total_validations,
            "successful_validations": successful_validations,
            "failed_validations": failed_validations,
            "success_rate": success_rate,
            "abcd_compliance_rate": abcd_compliance_rate,
            "average_processing_time": avg_processing_time
        }
    
    def get_provider_statistics(
        self,
        provider_id: int,
        user: Optional[UserModel] = None
    ) -> Dict[str, Any]:
        """
        Get statistics for a specific provider.
        
        Args:
            provider_id: Provider ID
            user: Current user for permission checking
            
        Returns:
            Dictionary containing provider statistics
        """
        provider = self.db.query(DataProviderModel).filter(
            DataProviderModel.id == provider_id
        ).first()
        
        if not provider:
            return None
        
        # Get dataset count
        dataset_count = self.db.query(func.count(DatasetModel.id)).filter(
            DatasetModel.provider_id == provider_id
        ).scalar()
        
        # Get XML archive count
        xml_archive_count = self.db.query(func.count(XmlArchiveModel.id)).join(
            DatasetModel, XmlArchiveModel.dataset_id == DatasetModel.id
        ).filter(DatasetModel.provider_id == provider_id).scalar()
        
        # Calculate validation success rate
        validation_success_rate = self._calculate_provider_validation_rate(provider_id)
        
        # Get last activity
        last_activity = self.db.query(func.max(DatasetModel.updated_at)).filter(
            DatasetModel.provider_id == provider_id
        ).scalar()
        
        # Calculate activity score
        activity_score = None
        if last_activity:
            days_since_activity = (datetime.utcnow() - last_activity).days
            activity_score = max(0, 100 - days_since_activity * 2)
        
        return {
            "provider_id": provider_id,
            "provider_name": provider.name,
            "dataset_count": dataset_count,
            "xml_archive_count": xml_archive_count,
            "validation_success_rate": validation_success_rate,
            "last_activity": last_activity,
            "activity_score": activity_score
        }
    
    def get_dataset_statistics(
        self,
        dataset_id: int,
        user: Optional[UserModel] = None
    ) -> Dict[str, Any]:
        """
        Get statistics for a specific dataset.
        
        Args:
            dataset_id: Dataset ID
            user: Current user for permission checking
            
        Returns:
            Dictionary containing dataset statistics
        """
        dataset = self.db.query(DatasetModel).filter(
            DatasetModel.id == dataset_id
        ).first()
        
        if not dataset:
            return None
        
        # Get latest unit count
        latest_unit_stat = self.db.query(StatisticModel).filter(
            and_(
                StatisticModel.metric_type == MetricType.DATASET_UNIT_COUNT,
                StatisticModel.entity_type == EntityType.DATASET,
                StatisticModel.entity_id == dataset_id
            )
        ).order_by(desc(StatisticModel.date)).first()
        
        unit_count = int(latest_unit_stat.value) if latest_unit_stat else None
        
        # Get latest validation status
        latest_validation = self.db.query(ValidationJobModel).join(
            XmlArchiveModel, ValidationJobModel.archive_id == XmlArchiveModel.id
        ).filter(
            XmlArchiveModel.dataset_id == dataset_id
        ).order_by(desc(ValidationJobModel.created_at)).first()
        
        validation_status = latest_validation.status if latest_validation else None
        is_valid = None
        
        if latest_validation and latest_validation.status == 'completed':
            if latest_validation.results:
                import json
                try:
                    results = json.loads(latest_validation.results) if isinstance(
                        latest_validation.results, str
                    ) else latest_validation.results
                    is_valid = results.get('is_valid', False)
                except (json.JSONDecodeError, AttributeError):
                    is_valid = False
        
        return {
            "dataset_id": dataset_id,
            "dataset_title": dataset.title or "Untitled",
            "provider_id": dataset.provider_id,
            "unit_count": unit_count,
            "last_modified": dataset.updated_at,
            "validation_status": validation_status,
            "is_valid": is_valid
        }
    
    def get_time_series_data(
        self,
        metric_type: str,
        entity_type: str,
        entity_id: Optional[int] = None,
        period: str = Period.DAILY.value,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
        limit: int = 30,
        user: Optional[UserModel] = None,
        include_today: bool = True
    ) -> Dict[str, Any]:
        """
        Get time series data for a specific metric with optional filtering.
        
        Args:
            metric_type: Type of metric to retrieve
            entity_type: Type of entity 
            entity_id: Optional entity ID
            period: Time period aggregation
            start_date: Optional start date
            end_date: Optional end date
            limit: Maximum number of data points
            user: Current user for permission checking
            include_today: Whether to include today's real-time data
            
        Returns:
            Dictionary containing time series data
        """
        from sqlalchemy import desc
        today = date.today()
        
        # For system-level metrics with potential duplicate issues, use special handling
        if entity_type == EntityType.SYSTEM and entity_id is None:
            # Use a subquery to get the most recent entry for each date
            subquery = self.db.query(
                StatisticModel.date,
                func.max(StatisticModel.created_at).label('max_created')
            ).filter(
                and_(
                    StatisticModel.metric_type == metric_type,
                    StatisticModel.entity_type == entity_type,
                    StatisticModel.period == period,
                    StatisticModel.entity_id.is_(None)
                )
            )
            
            if start_date:
                subquery = subquery.filter(StatisticModel.date >= start_date)
            if end_date:
                subquery = subquery.filter(StatisticModel.date <= end_date)
                
            subquery = subquery.group_by(StatisticModel.date).subquery()
            
            # Join to get the actual values using the most recent created_at
            stats_query = self.db.query(
                StatisticModel.date,
                StatisticModel.value,
                StatisticModel.extra_data
            ).join(
                subquery,
                and_(
                    StatisticModel.date == subquery.c.date,
                    StatisticModel.created_at == subquery.c.max_created,
                    StatisticModel.metric_type == metric_type,
                    StatisticModel.entity_type == entity_type,
                    StatisticModel.period == period,
                    StatisticModel.entity_id.is_(None)
                )
            ).order_by(desc(StatisticModel.date)).limit(limit)
            
            aggregated_stats = stats_query.all()
            
            # Convert to time series points
            data_points = []
            has_today = False
            
            for stat in reversed(aggregated_stats):  # Reverse for chronological order
                if stat.date == today:
                    has_today = True
                    # Skip today's data from database - we'll add real-time data instead
                    continue
                    
                data_points.append({
                    "date": stat.date,
                    "value": float(stat.value) if stat.value is not None else 0.0,
                    "extra_data": stat.extra_data or {"records_aggregated": 1}
                })
        else:
            # Original logic for non-system metrics
            base_query = self.db.query(
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
            
            # Group by date and order
            aggregated_stats = base_query.group_by(
                StatisticModel.date
            ).order_by(desc(StatisticModel.date)).limit(limit).all()
            
            # Convert to time series points
            data_points = []
            has_today = False
            
            for stat in reversed(aggregated_stats):  # Reverse for chronological order
                if stat.date == today and self._should_include_today_data(metric_type, entity_type, entity_id):
                    has_today = True
                    # Skip today's data from database if we should include real-time data
                    continue
                    
                data_points.append({
                    "date": stat.date,
                    "value": float(stat.value) if stat.value is not None else 0.0,
                    "extra_data": {"records_aggregated": stat.count}
                })
        
        # Always add today's real-time data for metrics that need it
        if include_today and self._should_include_today_data(metric_type, entity_type, entity_id):
            today_data = self._get_today_real_time_data(metric_type, entity_type, entity_id)
            if today_data:
                # Ensure today's real-time data is added
                data_points.append(today_data)
            elif not today_data and has_today:
                # If we can't get real-time data but today was in the database,
                # calculate it directly for dataset count
                if metric_type == MetricType.DATASET_COUNT.value and entity_type == EntityType.SYSTEM.value:
                    current_count = self.db.query(func.count(DatasetModel.id)).scalar() or 0
                    data_points.append({
                        "date": today,
                        "value": float(current_count),
                        "extra_data": {
                            "records_aggregated": 1,
                            "is_current_day": True,
                            "real_time_calculation": True
                        }
                    })
        
        return {
            "metric_type": metric_type,
            "entity_type": entity_type,
            "entity_id": entity_id,
            "period": period,
            "data_points": data_points,
            "total_points": len(data_points)
        }
    
    def get_growth_metrics(
        self,
        period: str = Period.MONTHLY.value,
        months: int = 12,
        user: Optional[UserModel] = None
    ) -> Dict[str, Any]:
        """
        Get growth metrics over time.
        
        Args:
            period: Time period for aggregation
            months: Number of months to retrieve
            user: Current user for permission checking
            
        Returns:
            Dictionary containing growth timelines
        """
        end_date = date.today()
        if period == Period.MONTHLY.value:
            start_date = end_date - timedelta(days=months * 30)
        elif period == Period.WEEKLY.value:
            start_date = end_date - timedelta(weeks=months * 4)
        else:  # daily
            start_date = end_date - timedelta(days=months * 30)
        
        # Get dataset growth timeline
        datasets_timeline = self._get_timeline_data(
            MetricType.DATASET_COUNT, 
            EntityType.SYSTEM,
            period, 
            start_date, 
            end_date
        )
        
        # Get provider growth timeline
        providers_timeline = self._get_timeline_data(
            MetricType.PROVIDER_COUNT,
            EntityType.SYSTEM,
            period,
            start_date,
            end_date
        )
        
        # Get validation activity timeline
        validation_timeline = self._get_timeline_data(
            MetricType.DATASET_REGISTRATION_RATE,
            EntityType.SYSTEM,
            period,
            start_date,
            end_date,
            aggregation_func=func.sum
        )
        
        # Add today's data if needed
        self._add_today_growth_data(
            datasets_timeline,
            providers_timeline,
            validation_timeline
        )
        
        return {
            "datasets_timeline": datasets_timeline,
            "providers_timeline": providers_timeline,
            "validation_timeline": validation_timeline
        }
    
    def get_provider_list_stats(
        self,
        limit: int = 20,
        user: Optional[UserModel] = None
    ) -> Dict[str, Any]:
        """
        Get statistics about top data providers.
        
        Args:
            limit: Number of top providers to show
            user: Current user for permission checking
            
        Returns:
            Dictionary containing provider statistics
        """
        # Get provider dataset counts
        provider_stats = self.db.query(
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
            # Get most recent biological units
            bio_units_stat = self.db.query(StatisticModel.value).filter(
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
        datacenter_stats = self._get_datacenter_stats()
        
        return {
            "top_providers": providers,
            "datacenters": datacenter_stats,
            "total_providers": len(provider_stats),
            "last_updated": datetime.utcnow().isoformat()
        }
    
    def get_recent_activity(
        self,
        limit: int = 10,
        days: int = 30,
        user: Optional[UserModel] = None
    ) -> Dict[str, Any]:
        """
        Get recent dataset registration and modification activity.
        
        Args:
            limit: Number of recent activities to show
            days: Number of days to look back
            user: Current user for permission checking
            
        Returns:
            Dictionary containing recent activity data
        """
        cutoff_date = datetime.utcnow() - timedelta(days=days)
        
        # Get recent dataset registrations
        recent_datasets = self.db.query(
            DatasetModel.id,
            DatasetModel.title,
            DatasetModel.created_at,
            DatasetModel.updated_at,
            DataProviderModel.name.label('provider_name'),
            DataProviderModel.datacenter
        ).join(
            DataProviderModel, DatasetModel.provider_id == DataProviderModel.id
        ).filter(
            DatasetModel.created_at >= cutoff_date
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
        
        # Get weekly registration statistics
        weekly_registrations = self._get_weekly_registration_stats()
        
        return {
            "recent_registrations": recent_registrations,
            "weekly_activity": weekly_registrations,
            "total_recent": len(recent_registrations),
            "period_days": days,
            "last_updated": datetime.utcnow().isoformat()
        }
    
    def get_health_status(self, user: Optional[UserModel] = None) -> Dict[str, Any]:
        """
        Get registry health status metrics.
        
        Args:
            user: Current user for permission checking
            
        Returns:
            Dictionary containing health metrics
        """
        # Get basic counts
        total_datasets = self.db.query(func.count(DatasetModel.id)).scalar()
        total_providers = self.db.query(func.count(DataProviderModel.id)).scalar()
        total_archives = self.db.query(func.count(XmlArchiveModel.id)).scalar()
        
        # Get recent validation activity (last 24 hours)
        yesterday = datetime.utcnow() - timedelta(hours=24)
        recent_validations = self.db.query(func.count(ValidationJobModel.id)).filter(
            ValidationJobModel.created_at >= yesterday
        ).scalar()
        
        successful_recent = self.db.query(func.count(ValidationJobModel.id)).filter(
            and_(
                ValidationJobModel.created_at >= yesterday,
                ValidationJobModel.status == 'completed'
            )
        ).scalar()
        
        # Calculate health score
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
    
    # Private helper methods
    
    def _calculate_validation_success_rate(self, days: int = 30) -> Optional[float]:
        """Calculate validation success rate for the last N days."""
        cutoff_date = date.today() - timedelta(days=days)
        recent_jobs = self.db.query(ValidationJobModel).filter(
            ValidationJobModel.created_at >= cutoff_date
        ).all()
        
        if recent_jobs:
            total_validations = len(recent_jobs)
            successful_validations = len([
                job for job in recent_jobs 
                if job.status == 'completed' and 
                job.valid_files == job.total_files and 
                job.total_files > 0
            ])
            return (successful_validations / total_validations * 100) if total_validations > 0 else 0
        return None
    
    def _calculate_provider_validation_rate(self, provider_id: int) -> Optional[float]:
        """Calculate validation success rate for a specific provider."""
        validation_jobs_query = self.db.query(ValidationJobModel).join(
            XmlArchiveModel, ValidationJobModel.archive_id == XmlArchiveModel.id
        ).join(
            DatasetModel, XmlArchiveModel.dataset_id == DatasetModel.id
        ).filter(DatasetModel.provider_id == provider_id)
        
        total_jobs = validation_jobs_query.count()
        if total_jobs == 0:
            return None
            
        successful_jobs = validation_jobs_query.filter(
            and_(
                ValidationJobModel.status == 'completed',
                ValidationJobModel.valid_files == ValidationJobModel.total_files,
                ValidationJobModel.total_files > 0
            )
        ).count()
        
        return (successful_jobs / total_jobs * 100) if total_jobs > 0 else None
    
    def _get_detailed_admin_metrics(self) -> Dict[str, Any]:
        """Get detailed metrics only available to admins."""
        # Add any admin-specific detailed metrics here
        return {
            "system_load": self._calculate_system_load(),
            "storage_usage": self._calculate_storage_usage(),
            "api_response_times": self._get_api_response_times()
        }
    
    def _calculate_system_load(self) -> Optional[float]:
        """Calculate system processing load."""
        # Placeholder for actual system load calculation
        return None
    
    def _calculate_storage_usage(self) -> Optional[int]:
        """Calculate total storage usage."""
        # Placeholder for actual storage calculation
        return None
    
    def _get_api_response_times(self) -> Optional[Dict[str, float]]:
        """Get average API response times."""
        # Placeholder for actual API response time calculation
        return None
    
    def _get_timeline_data(
        self,
        metric_type: str,
        entity_type: str,
        period: str,
        start_date: date,
        end_date: date,
        aggregation_func=None  # Changed: default is None, will use custom logic
    ) -> List[Dict[str, Any]]:
        """Get timeline data for a specific metric.
        
        For metrics with potential duplicates (like system-level metrics with NULL entity_id),
        this method now selects the most recent value instead of using MAX aggregation.
        """
        from sqlalchemy import desc
        
        # For system-level metrics (where entity_id is NULL), we need special handling
        # due to PostgreSQL's treatment of NULL in unique constraints
        if entity_type == EntityType.SYSTEM and aggregation_func is None:
            # Use a subquery to get the most recent entry for each date
            subquery = self.db.query(
                StatisticModel.date,
                func.max(StatisticModel.created_at).label('max_created')
            ).filter(
                and_(
                    StatisticModel.metric_type == metric_type,
                    StatisticModel.entity_type == entity_type,
                    StatisticModel.period == period,
                    StatisticModel.date >= start_date,
                    StatisticModel.date <= end_date
                )
            ).group_by(StatisticModel.date).subquery()
            
            # Join to get the actual values
            stats_raw = self.db.query(
                StatisticModel.date,
                StatisticModel.value,
                StatisticModel.extra_data
            ).join(
                subquery,
                and_(
                    StatisticModel.date == subquery.c.date,
                    StatisticModel.created_at == subquery.c.max_created,
                    StatisticModel.metric_type == metric_type,
                    StatisticModel.entity_type == entity_type,
                    StatisticModel.period == period
                )
            ).order_by(StatisticModel.date).all()
            
            return [
                {
                    "date": stat.date,
                    "value": float(stat.value) if stat.value is not None else 0.0,
                    "extra_data": stat.extra_data or {"records_aggregated": 1}
                }
                for stat in stats_raw
            ]
        else:
            # For other cases, use the provided aggregation function or default to max
            if aggregation_func is None:
                aggregation_func = func.max
                
            stats_raw = self.db.query(
                StatisticModel.date,
                aggregation_func(StatisticModel.value).label('value'),
                func.count(StatisticModel.id).label('count')
            ).filter(
                and_(
                    StatisticModel.metric_type == metric_type,
                    StatisticModel.entity_type == entity_type,
                    StatisticModel.period == period,
                    StatisticModel.date >= start_date,
                    StatisticModel.date <= end_date
                )
            ).group_by(StatisticModel.date).order_by(StatisticModel.date).all()
            
            return [
                {
                    "date": stat.date,
                    "value": float(stat.value) if stat.value is not None else 0.0,
                    "extra_data": {"records_aggregated": stat.count}
                }
                for stat in stats_raw
            ]
    
    def _should_include_today_data(
        self, 
        metric_type: str, 
        entity_type: str, 
        entity_id: Optional[int]
    ) -> bool:
        """Determine if today's real-time data should be included."""
        # Include today's data for system-wide dataset count
        if (metric_type == MetricType.DATASET_COUNT.value and
            entity_type == EntityType.SYSTEM.value and
            entity_id is None):
            return True
        
        # Include today's data for provider-specific dataset count
        if (metric_type == MetricType.PROVIDER_DATASET_COUNT.value and 
            entity_type == EntityType.PROVIDER.value and
            entity_id is not None):
            return True
        
        # Include today's data for provider biological units
        if metric_type == MetricType.PROVIDER_BIOLOGICAL_UNITS.value and entity_type == EntityType.PROVIDER.value:
            return True
            
        return False
    
    def _get_today_real_time_data(
        self,
        metric_type: str,
        entity_type: str,
        entity_id: Optional[int]
    ) -> Optional[Dict[str, Any]]:
        """Get today's real-time data for a metric."""
        today = date.today()
        today_start = datetime.combine(today, datetime.min.time())
        
        if metric_type == MetricType.DATASET_COUNT.value:
            # Get today's dataset registrations
            todays_new_datasets = self.db.query(func.count(DatasetModel.id)).filter(
                DatasetModel.created_at >= today_start
            ).scalar() or 0
            
            if todays_new_datasets > 0:
                current_total = self.db.query(func.count(DatasetModel.id)).scalar() or 0
                return {
                    "date": today,
                    "value": float(current_total),
                    "extra_data": {
                        "records_aggregated": 1,
                        "is_current_day": True,
                        "new_registrations_today": todays_new_datasets
                    }
                }
        
        elif metric_type == MetricType.PROVIDER_DATASET_COUNT.value:
            # Handle provider-specific dataset count
            if entity_id is not None:
                # Check if we have today's statistics
                existing_today_stat = self.db.query(StatisticModel).filter(
                    and_(
                        StatisticModel.metric_type == metric_type,
                        StatisticModel.entity_type == entity_type,
                        StatisticModel.entity_id == entity_id,
                        StatisticModel.date == today
                    )
                ).first()
                
                if existing_today_stat:
                    return {
                        "date": today,
                        "value": float(existing_today_stat.value),
                        "extra_data": existing_today_stat.extra_data or {
                            "records_aggregated": 1,
                            "is_current_day": True
                        }
                    }
                else:
                    # Calculate real-time count
                    current_count = self.db.query(func.count(DatasetModel.id)).filter(
                        DatasetModel.provider_id == entity_id
                    ).scalar() or 0
                    
                    if current_count > 0:
                        return {
                            "date": today,
                            "value": float(current_count),
                            "extra_data": {
                                "records_aggregated": 1,
                                "is_current_day": True,
                                "real_time_calculation": True
                            }
                        }
        
        elif metric_type == MetricType.PROVIDER_BIOLOGICAL_UNITS.value:
            # For provider biological units, always calculate real-time from dataset unit counts
            # to ensure we capture any changes immediately
            
            # Determine which datasets to include
            if entity_id is not None:
                # Specific provider - get datasets for this provider
                dataset_ids = self.db.query(DatasetModel.id).filter(
                    DatasetModel.provider_id == entity_id
                ).all()
            else:
                # System-wide - get all datasets
                dataset_ids = self.db.query(DatasetModel.id).all()
            
            if not dataset_ids:
                return {
                    "date": today,
                    "value": 0.0,
                    "extra_data": {
                        "records_aggregated": 0,
                        "is_current_day": True,
                        "real_time_calculation": True,
                        "dataset_count": 0
                    }
                }
            
            dataset_id_list = [dataset_id[0] for dataset_id in dataset_ids]
            
            # Get the most recent unit count for each dataset (including today's updates)
            subquery = self.db.query(
                StatisticModel.entity_id,
                func.max(StatisticModel.date).label('max_date')
            ).filter(
                and_(
                    StatisticModel.metric_type == MetricType.DATASET_UNIT_COUNT,
                    StatisticModel.entity_type == EntityType.DATASET,
                    StatisticModel.entity_id.in_(dataset_id_list),
                    StatisticModel.date <= today
                )
            ).group_by(StatisticModel.entity_id).subquery()
            
            # Get the actual values using the max date for each dataset
            recent_unit_counts = self.db.query(
                StatisticModel.value
            ).join(
                subquery,
                and_(
                    StatisticModel.entity_id == subquery.c.entity_id,
                    StatisticModel.date == subquery.c.max_date
                )
            ).filter(
                StatisticModel.metric_type == MetricType.DATASET_UNIT_COUNT
            ).all()
            
            total_units = sum(count[0] for count in recent_unit_counts if count[0] is not None)
            
            return {
                "date": today,
                "value": float(total_units),
                "extra_data": {
                    "records_aggregated": len(recent_unit_counts),
                    "is_current_day": True,
                    "real_time_calculation": True,
                    "dataset_count": len(dataset_ids),
                    "provider_id": entity_id if entity_id else "system"
                }
            }
        
        return None
    
    def _add_today_growth_data(
        self,
        datasets_timeline: List[Dict],
        providers_timeline: List[Dict],
        validation_timeline: List[Dict]
    ) -> None:
        """Add today's data to growth timelines if applicable.
        
        Always uses real-time data for today to ensure accuracy, especially
        after dataset additions or deletions.
        """
        today = date.today()
        today_start = datetime.combine(today, datetime.min.time())
        
        # Always replace or add today's data with real-time counts
        # Remove any existing entry for today first
        datasets_timeline[:] = [point for point in datasets_timeline if point["date"] != today]
        providers_timeline[:] = [point for point in providers_timeline if point["date"] != today]
        validation_timeline[:] = [point for point in validation_timeline if point["date"] != today]
        
        # Get real-time dataset count and add to timeline
        current_total_datasets = self.db.query(func.count(DatasetModel.id)).scalar() or 0
        todays_new_datasets = self.db.query(func.count(DatasetModel.id)).filter(
            DatasetModel.created_at >= today_start
        ).scalar() or 0
        
        datasets_timeline.append({
            "date": today,
            "value": float(current_total_datasets),
            "extra_data": {
                "records_aggregated": 1,
                "is_current_day": True,
                "new_registrations_today": todays_new_datasets,
                "real_time": True
            }
        })
        
        # Get real-time provider count and add to timeline
        current_total_providers = self.db.query(func.count(DataProviderModel.id)).scalar() or 0
        providers_timeline.append({
            "date": today,
            "value": float(current_total_providers),
            "extra_data": {
                "records_aggregated": 1,
                "is_current_day": True,
                "real_time": True
            }
        })
        
        # Get today's validation activity if any
        todays_validations = self.db.query(func.count(ValidationJobModel.id)).filter(
            ValidationJobModel.created_at >= today_start
        ).scalar() or 0
        
        if todays_validations > 0:
            validation_timeline.append({
                "date": today,
                "value": float(todays_validations),
                "extra_data": {
                    "records_aggregated": 1,
                    "is_current_day": True,
                    "real_time": True
                }
            })
        
        # Sort timelines by date to maintain order
        datasets_timeline.sort(key=lambda x: x["date"])
        providers_timeline.sort(key=lambda x: x["date"])
        validation_timeline.sort(key=lambda x: x["date"])
    
    def _get_datacenter_stats(self) -> List[Dict[str, Any]]:
        """Get datacenter statistics."""
        datacenter_stats = self.db.query(
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
        
        return datacenters
    
    def _get_weekly_registration_stats(self) -> List[Dict[str, Any]]:
        """Get registration statistics for last 7 days."""
        week_ago = date.today() - timedelta(days=7)
        recent_registration_stats = self.db.query(StatisticModel).filter(
            and_(
                StatisticModel.metric_type == MetricType.DATASET_REGISTRATION_RATE,
                StatisticModel.entity_type == EntityType.SYSTEM,
                StatisticModel.period == Period.DAILY,
                StatisticModel.date >= week_ago
            )
        ).order_by(StatisticModel.date).all()
        
        return [
            {
                "date": stat.date.isoformat(),
                "count": int(stat.value)
            }
            for stat in recent_registration_stats
        ]