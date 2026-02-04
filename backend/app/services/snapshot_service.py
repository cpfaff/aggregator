"""
Snapshot service for querying archive snapshot data.

This service provides all statistics queries using the simplified
ArchiveSnapshot model with query-time SQL aggregation.

Total: ~200 lines (vs 1,085 in the old statistics_service.py)
"""

import logging
from datetime import date, datetime, timedelta
from typing import Any

from sqlalchemy import and_, desc, func
from sqlalchemy.orm import Session

from app.models.archive_snapshot import ArchiveSnapshotModel
from app.models.dataset import DatasetModel, XmlArchiveModel
from app.models.provider import DataProviderModel
from app.models.user import UserModel
from app.models.validation import ValidationJobModel

logger = logging.getLogger(__name__)


class SnapshotService:
    """Service for snapshot-based statistics queries."""

    def __init__(self, db: Session):
        self.db = db

    # -------------------------------------------------------------------------
    # Overview & Counts (live database queries, not from snapshots)
    # -------------------------------------------------------------------------

    def get_overview_stats(
        self, user: UserModel | None = None, include_sensitive: bool = False
    ) -> dict[str, Any]:
        """Get system overview statistics using live counts."""
        total_datasets = self.db.query(func.count(DatasetModel.id)).scalar() or 0
        total_providers = self.db.query(func.count(DataProviderModel.id)).scalar() or 0
        total_archives = self.db.query(func.count(XmlArchiveModel.id)).scalar() or 0
        total_datacenters = (
            self.db.query(func.count(DataProviderModel.id))
            .filter(DataProviderModel.isDataCenter == True)
            .scalar()
            or 0
        )

        validation_success_rate = self._calculate_validation_success_rate(days=30)

        return {
            "total_datasets": total_datasets,
            "total_providers": total_providers,
            "total_datacenters": total_datacenters,
            "total_xml_archives": total_archives,
            "validation_success_rate": validation_success_rate,
            "last_updated": datetime.utcnow(),
        }

    def get_quality_metrics(
        self, user: UserModel | None = None, days: int = 30
    ) -> dict[str, Any]:
        """Get data quality metrics from validation jobs."""
        cutoff_date = date.today() - timedelta(days=days)

        recent_jobs = (
            self.db.query(ValidationJobModel)
            .filter(ValidationJobModel.created_at >= cutoff_date)
            .all()
        )

        total_validations = len(recent_jobs)
        successful_validations = len(
            [
                job
                for job in recent_jobs
                if job.status == "completed"
                and job.valid_files == job.total_files
                and job.total_files > 0
            ]
        )
        failed_validations = total_validations - successful_validations

        success_rate = (
            (successful_validations / total_validations * 100) if total_validations > 0 else 0
        )

        processing_times = [
            job.validation_time
            for job in recent_jobs
            if job.validation_time is not None and job.status == "completed"
        ]
        avg_processing_time = (
            (sum(processing_times) / len(processing_times)) if processing_times else None
        )

        return {
            "total_validations": total_validations,
            "successful_validations": successful_validations,
            "failed_validations": failed_validations,
            "success_rate": success_rate,
            "abcd_compliance_rate": None,  # No longer tracked
            "average_processing_time": avg_processing_time,
        }

    def _calculate_validation_success_rate(self, days: int = 30) -> float | None:
        """Calculate validation success rate for the last N days."""
        cutoff_date = date.today() - timedelta(days=days)

        completed_jobs = (
            self.db.query(ValidationJobModel)
            .filter(
                and_(
                    ValidationJobModel.created_at >= cutoff_date,
                    ValidationJobModel.status == "completed",
                )
            )
            .all()
        )

        if not completed_jobs:
            return None

        successful = sum(
            1
            for job in completed_jobs
            if job.valid_files == job.total_files and job.total_files > 0
        )

        return (successful / len(completed_jobs) * 100) if completed_jobs else None

    # -------------------------------------------------------------------------
    # Unit Count Queries (from ArchiveSnapshot)
    # -------------------------------------------------------------------------

    def get_dataset_unit_count(self, dataset_id: int) -> int:
        """
        Get total unit count for a dataset.

        Uses the LATEST snapshot for each archive belonging to this dataset.
        Only counts archives where isLatest=True.
        """
        # Subquery to get latest snapshot per archive for this dataset
        # Only include archives where isLatest=True
        latest_per_archive = (
            self.db.query(
                ArchiveSnapshotModel.archive_id,
                func.max(ArchiveSnapshotModel.recorded_at).label("max_recorded"),
            )
            .join(XmlArchiveModel, ArchiveSnapshotModel.archive_id == XmlArchiveModel.id)
            .filter(XmlArchiveModel.dataset_id == dataset_id, XmlArchiveModel.isLatest == True)
            .group_by(ArchiveSnapshotModel.archive_id)
            .subquery()
        )

        # Get sum of unit counts from latest snapshots
        result = (
            self.db.query(func.sum(ArchiveSnapshotModel.unit_count))
            .join(
                latest_per_archive,
                and_(
                    ArchiveSnapshotModel.archive_id == latest_per_archive.c.archive_id,
                    ArchiveSnapshotModel.recorded_at == latest_per_archive.c.max_recorded,
                ),
            )
            .scalar()
        )

        return result or 0

    def get_provider_unit_count(self, provider_id: int) -> int:
        """
        Get total unit count for a provider.

        Aggregates across all datasets owned by this provider.
        Only counts archives where isLatest=True.
        """
        # Subquery for latest snapshot per archive
        # Only include archives where isLatest=True
        latest_per_archive = (
            self.db.query(
                ArchiveSnapshotModel.archive_id,
                func.max(ArchiveSnapshotModel.recorded_at).label("max_recorded"),
            )
            .join(XmlArchiveModel, ArchiveSnapshotModel.archive_id == XmlArchiveModel.id)
            .join(DatasetModel, XmlArchiveModel.dataset_id == DatasetModel.id)
            .filter(DatasetModel.provider_id == provider_id, XmlArchiveModel.isLatest == True)
            .group_by(ArchiveSnapshotModel.archive_id)
            .subquery()
        )

        result = (
            self.db.query(func.sum(ArchiveSnapshotModel.unit_count))
            .join(
                latest_per_archive,
                and_(
                    ArchiveSnapshotModel.archive_id == latest_per_archive.c.archive_id,
                    ArchiveSnapshotModel.recorded_at == latest_per_archive.c.max_recorded,
                ),
            )
            .scalar()
        )

        return result or 0

    def get_total_biological_units(self) -> int:
        """Get total biological units across all archives (system-wide).

        Only counts archives where isLatest=True.
        """
        # Get latest snapshot per archive, only for isLatest=True archives
        latest_per_archive = (
            self.db.query(
                ArchiveSnapshotModel.archive_id,
                func.max(ArchiveSnapshotModel.recorded_at).label("max_recorded"),
            )
            .join(XmlArchiveModel, ArchiveSnapshotModel.archive_id == XmlArchiveModel.id)
            .filter(XmlArchiveModel.isLatest == True)
            .group_by(ArchiveSnapshotModel.archive_id)
            .subquery()
        )

        result = (
            self.db.query(func.sum(ArchiveSnapshotModel.unit_count))
            .join(
                latest_per_archive,
                and_(
                    ArchiveSnapshotModel.archive_id == latest_per_archive.c.archive_id,
                    ArchiveSnapshotModel.recorded_at == latest_per_archive.c.max_recorded,
                ),
            )
            .scalar()
        )

        return result or 0

    # -------------------------------------------------------------------------
    # Timeline Queries (for charts)
    # -------------------------------------------------------------------------

    def get_biological_units_timeline(
        self, start_date: date | None = None, end_date: date | None = None, limit: int = 30
    ) -> list[dict[str, Any]]:
        """
        Get system-wide biological units timeline with forward-fill.

        For each date, uses the most recent snapshot for each archive up to that date.
        This ensures the timeline shows cumulative growth and doesn't drop when
        archives temporarily fail to be collected.
        Only counts archives where isLatest=True.
        """
        # Get all distinct dates we have snapshots for
        dates_query = (
            self.db.query(func.date(ArchiveSnapshotModel.recorded_at).label("date"))
            .distinct()
            .order_by(desc(func.date(ArchiveSnapshotModel.recorded_at)))
        )

        if start_date:
            dates_query = dates_query.filter(ArchiveSnapshotModel.recorded_at >= start_date)
        if end_date:
            dates_query = dates_query.filter(ArchiveSnapshotModel.recorded_at <= end_date)

        dates = [r.date for r in dates_query.limit(limit).all()]

        if not dates:
            return []

        # For each date, calculate total using forward-fill
        timeline = []
        for target_date in reversed(dates):  # Process chronologically
            # Get the most recent snapshot for each archive up to this date
            # Subquery to get max recorded_at per archive up to target_date
            latest_per_archive = (
                self.db.query(
                    ArchiveSnapshotModel.archive_id,
                    func.max(ArchiveSnapshotModel.recorded_at).label("max_recorded"),
                )
                .filter(func.date(ArchiveSnapshotModel.recorded_at) <= target_date)
                .group_by(ArchiveSnapshotModel.archive_id)
                .subquery()
            )

            # Sum units from the latest snapshot of each archive
            total = (
                self.db.query(func.sum(ArchiveSnapshotModel.unit_count))
                .join(
                    latest_per_archive,
                    and_(
                        ArchiveSnapshotModel.archive_id == latest_per_archive.c.archive_id,
                        ArchiveSnapshotModel.recorded_at == latest_per_archive.c.max_recorded,
                    ),
                )
                .join(XmlArchiveModel, ArchiveSnapshotModel.archive_id == XmlArchiveModel.id)
                .filter(XmlArchiveModel.isLatest == True)
                .scalar()
                or 0
            )

            timeline.append({"date": target_date, "value": float(total)})

        return timeline

    def get_provider_biological_units_timeline(
        self,
        provider_id: int,
        start_date: date | None = None,
        end_date: date | None = None,
        limit: int = 30,
    ) -> list[dict[str, Any]]:
        """
        Get biological units timeline for a specific provider with forward-fill.

        For each date, uses the most recent snapshot for each archive up to that date.
        This ensures the timeline shows cumulative growth and doesn't drop when
        archives temporarily fail to be collected.
        Only counts archives where isLatest=True.
        """
        # Get all distinct dates we have snapshots for (for this provider's archives)
        dates_query = (
            self.db.query(func.date(ArchiveSnapshotModel.recorded_at).label("date"))
            .join(XmlArchiveModel, ArchiveSnapshotModel.archive_id == XmlArchiveModel.id)
            .join(DatasetModel, XmlArchiveModel.dataset_id == DatasetModel.id)
            .filter(DatasetModel.provider_id == provider_id)
            .distinct()
            .order_by(desc(func.date(ArchiveSnapshotModel.recorded_at)))
        )

        if start_date:
            dates_query = dates_query.filter(ArchiveSnapshotModel.recorded_at >= start_date)
        if end_date:
            dates_query = dates_query.filter(ArchiveSnapshotModel.recorded_at <= end_date)

        dates = [r.date for r in dates_query.limit(limit).all()]

        if not dates:
            return []

        # Get all archive IDs for this provider (that are latest)
        provider_archive_ids = [
            r[0]
            for r in self.db.query(XmlArchiveModel.id)
            .join(DatasetModel, XmlArchiveModel.dataset_id == DatasetModel.id)
            .filter(DatasetModel.provider_id == provider_id, XmlArchiveModel.isLatest == True)
            .all()
        ]

        if not provider_archive_ids:
            return []

        # For each date, calculate total using forward-fill
        timeline = []
        for target_date in reversed(dates):  # Process chronologically
            # Get the most recent snapshot for each of this provider's archives up to this date
            latest_per_archive = (
                self.db.query(
                    ArchiveSnapshotModel.archive_id,
                    func.max(ArchiveSnapshotModel.recorded_at).label("max_recorded"),
                )
                .filter(
                    ArchiveSnapshotModel.archive_id.in_(provider_archive_ids),
                    func.date(ArchiveSnapshotModel.recorded_at) <= target_date,
                )
                .group_by(ArchiveSnapshotModel.archive_id)
                .subquery()
            )

            # Sum units from the latest snapshot of each archive
            total = (
                self.db.query(func.sum(ArchiveSnapshotModel.unit_count))
                .join(
                    latest_per_archive,
                    and_(
                        ArchiveSnapshotModel.archive_id == latest_per_archive.c.archive_id,
                        ArchiveSnapshotModel.recorded_at == latest_per_archive.c.max_recorded,
                    ),
                )
                .scalar()
                or 0
            )

            timeline.append({"date": target_date, "value": float(total)})

        return timeline

    def get_provider_datasets_timeline(
        self, provider_id: int, period: str = "daily", months: int = 12
    ) -> list[dict[str, Any]]:
        """
        Get cumulative dataset count timeline for a specific provider.

        Returns timeline data showing cumulative total datasets over time.
        """
        cutoff_date = date.today() - timedelta(days=months * 30)

        if period == "monthly":
            dataset_results = (
                self.db.query(
                    func.date_trunc("month", DatasetModel.created_at).label("month"),
                    func.count(DatasetModel.id).label("count"),
                )
                .filter(
                    DatasetModel.provider_id == provider_id, DatasetModel.created_at >= cutoff_date
                )
                .group_by(func.date_trunc("month", DatasetModel.created_at))
                .order_by(func.date_trunc("month", DatasetModel.created_at))
                .all()
            )

            # Get baseline count (datasets before cutoff)
            baseline_count = (
                self.db.query(func.count(DatasetModel.id))
                .filter(
                    DatasetModel.provider_id == provider_id, DatasetModel.created_at < cutoff_date
                )
                .scalar()
                or 0
            )

            cumulative = baseline_count
            timeline = []
            for row in dataset_results:
                if row.month:
                    cumulative += row.count
                    timeline.append({"date": row.month.date(), "value": cumulative})
            return timeline
        else:
            # Daily aggregation
            dataset_results = (
                self.db.query(
                    func.date(DatasetModel.created_at).label("day"),
                    func.count(DatasetModel.id).label("count"),
                )
                .filter(
                    DatasetModel.provider_id == provider_id, DatasetModel.created_at >= cutoff_date
                )
                .group_by(func.date(DatasetModel.created_at))
                .order_by(func.date(DatasetModel.created_at))
                .all()
            )

            baseline_count = (
                self.db.query(func.count(DatasetModel.id))
                .filter(
                    DatasetModel.provider_id == provider_id, DatasetModel.created_at < cutoff_date
                )
                .scalar()
                or 0
            )

            cumulative = baseline_count
            timeline = []
            for row in dataset_results:
                if row.day:
                    cumulative += row.count
                    timeline.append({"date": row.day, "value": cumulative})
            return timeline

    def get_multi_provider_timeline(
        self, start_date: date | None = None, end_date: date | None = None, limit: int = 30
    ) -> dict[str, Any]:
        """
        Get biological units timeline for all providers with forward-fill.

        For each date, uses the most recent snapshot for each archive up to that date.
        This ensures the timeline shows cumulative growth and doesn't drop when
        archives temporarily fail to be collected.
        Only counts archives where isLatest=True.
        """
        # Get all distinct dates we have snapshots for
        dates_query = (
            self.db.query(func.date(ArchiveSnapshotModel.recorded_at).label("date"))
            .distinct()
            .order_by(desc(func.date(ArchiveSnapshotModel.recorded_at)))
        )

        if start_date:
            dates_query = dates_query.filter(ArchiveSnapshotModel.recorded_at >= start_date)
        if end_date:
            dates_query = dates_query.filter(ArchiveSnapshotModel.recorded_at <= end_date)

        dates = [r.date for r in dates_query.limit(limit).all()]

        if not dates:
            return {
                "metric_type": "provider_biological_units",
                "entity_type": "multi_provider",
                "period": "daily",
                "data_points": [],
                "total_points": 0,
                "providers": [],
                "total_providers": 0,
            }

        # Get all providers that have snapshots and their archive IDs
        providers = (
            self.db.query(DataProviderModel.id, DataProviderModel.name)
            .join(DatasetModel, DataProviderModel.id == DatasetModel.provider_id)
            .join(XmlArchiveModel, DatasetModel.id == XmlArchiveModel.dataset_id)
            .join(ArchiveSnapshotModel, XmlArchiveModel.id == ArchiveSnapshotModel.archive_id)
            .filter(XmlArchiveModel.isLatest == True)
            .distinct()
            .all()
        )

        if not providers:
            return {
                "metric_type": "provider_biological_units",
                "entity_type": "multi_provider",
                "period": "daily",
                "data_points": [],
                "total_points": 0,
                "providers": [],
                "total_providers": 0,
            }

        # Build provider archive mapping
        provider_archives = {}
        for provider_id, provider_name in providers:
            archive_ids = [
                r[0]
                for r in self.db.query(XmlArchiveModel.id)
                .join(DatasetModel, XmlArchiveModel.dataset_id == DatasetModel.id)
                .filter(DatasetModel.provider_id == provider_id, XmlArchiveModel.isLatest == True)
                .all()
            ]
            provider_archives[provider_name] = archive_ids

        # For each date, calculate totals per provider using forward-fill
        data_points = []
        for target_date in reversed(dates):  # Process chronologically
            date_point = {"date": target_date.isoformat()}

            for provider_name, archive_ids in provider_archives.items():
                if not archive_ids:
                    date_point[provider_name] = 0.0
                    continue

                # Get the most recent snapshot for each of this provider's archives up to this date
                latest_per_archive = (
                    self.db.query(
                        ArchiveSnapshotModel.archive_id,
                        func.max(ArchiveSnapshotModel.recorded_at).label("max_recorded"),
                    )
                    .filter(
                        ArchiveSnapshotModel.archive_id.in_(archive_ids),
                        func.date(ArchiveSnapshotModel.recorded_at) <= target_date,
                    )
                    .group_by(ArchiveSnapshotModel.archive_id)
                    .subquery()
                )

                # Sum units from the latest snapshot of each archive
                total = (
                    self.db.query(func.sum(ArchiveSnapshotModel.unit_count))
                    .join(
                        latest_per_archive,
                        and_(
                            ArchiveSnapshotModel.archive_id == latest_per_archive.c.archive_id,
                            ArchiveSnapshotModel.recorded_at == latest_per_archive.c.max_recorded,
                        ),
                    )
                    .scalar()
                    or 0
                )

                date_point[provider_name] = float(total)

            data_points.append(date_point)

        # Get provider metadata
        provider_metadata = [
            {"id": p_id, "name": p_name, "key": p_name} for p_id, p_name in providers
        ]

        return {
            "metric_type": "provider_biological_units",
            "entity_type": "multi_provider",
            "period": "daily",
            "data_points": data_points,
            "total_points": len(data_points),
            "providers": provider_metadata,
            "total_providers": len(provider_metadata),
        }

    # -------------------------------------------------------------------------
    # Provider & Dataset Statistics
    # -------------------------------------------------------------------------

    def get_provider_statistics(
        self, provider_id: int, user: UserModel | None = None
    ) -> dict[str, Any] | None:
        """Get statistics for a specific provider."""
        provider = (
            self.db.query(DataProviderModel).filter(DataProviderModel.id == provider_id).first()
        )

        if not provider:
            return None

        dataset_count = (
            self.db.query(func.count(DatasetModel.id))
            .filter(DatasetModel.provider_id == provider_id)
            .scalar()
            or 0
        )

        archive_count = (
            self.db.query(func.count(XmlArchiveModel.id))
            .join(DatasetModel)
            .filter(DatasetModel.provider_id == provider_id)
            .scalar()
            or 0
        )

        validation_success_rate = self._calculate_provider_validation_rate(provider_id)

        # Get last activity
        last_dataset = (
            self.db.query(DatasetModel)
            .filter(DatasetModel.provider_id == provider_id)
            .order_by(desc(DatasetModel.updated_at))
            .first()
        )

        return {
            "provider_id": provider_id,
            "provider_name": provider.name,
            "dataset_count": dataset_count,
            "xml_archive_count": archive_count,
            "validation_success_rate": validation_success_rate,
            "last_activity": last_dataset.updated_at if last_dataset else None,
            "activity_score": None,  # No longer tracked
        }

    def _calculate_provider_validation_rate(self, provider_id: int) -> float | None:
        """Calculate validation success rate for a specific provider."""
        cutoff_date = date.today() - timedelta(days=30)

        completed_jobs = (
            self.db.query(ValidationJobModel)
            .join(XmlArchiveModel, ValidationJobModel.archive_id == XmlArchiveModel.id)
            .join(DatasetModel, XmlArchiveModel.dataset_id == DatasetModel.id)
            .filter(
                and_(
                    DatasetModel.provider_id == provider_id,
                    ValidationJobModel.created_at >= cutoff_date,
                    ValidationJobModel.status == "completed",
                )
            )
            .all()
        )

        if not completed_jobs:
            return None

        successful = sum(
            1
            for job in completed_jobs
            if job.valid_files == job.total_files and job.total_files > 0
        )

        return (successful / len(completed_jobs) * 100) if completed_jobs else None

    def get_dataset_statistics(
        self, dataset_id: int, user: UserModel | None = None
    ) -> dict[str, Any] | None:
        """Get statistics for a specific dataset."""
        dataset = self.db.query(DatasetModel).filter(DatasetModel.id == dataset_id).first()

        if not dataset:
            return None

        unit_count = self.get_dataset_unit_count(dataset_id)

        # Get latest validation
        latest_validation = (
            self.db.query(ValidationJobModel)
            .join(XmlArchiveModel)
            .filter(XmlArchiveModel.dataset_id == dataset_id)
            .order_by(desc(ValidationJobModel.created_at))
            .first()
        )

        validation_status = None
        is_valid = None

        if latest_validation:
            validation_status = latest_validation.status
            is_valid = (
                (
                    latest_validation.valid_files == latest_validation.total_files
                    and latest_validation.total_files > 0
                )
                if latest_validation.status == "completed"
                else None
            )

        return {
            "dataset_id": dataset_id,
            "dataset_title": dataset.title,
            "provider_id": dataset.provider_id,
            "unit_count": unit_count,
            "last_modified": dataset.updated_at,
            "validation_status": validation_status,
            "is_valid": is_valid,
        }

    def get_provider_list_stats(
        self, limit: int = 20, user: UserModel | None = None
    ) -> dict[str, Any]:
        """Get statistics about top providers."""
        providers = self.db.query(DataProviderModel).limit(limit).all()

        provider_list = []
        for provider in providers:
            dataset_count = (
                self.db.query(func.count(DatasetModel.id))
                .filter(DatasetModel.provider_id == provider.id)
                .scalar()
                or 0
            )

            unit_count = self.get_provider_unit_count(provider.id)

            provider_list.append(
                {
                    "provider_id": provider.id,
                    "provider_name": provider.name,
                    "dataset_count": dataset_count,
                    "biological_units": unit_count,
                }
            )

        # Sort by biological units descending
        provider_list.sort(key=lambda x: x["biological_units"], reverse=True)

        # Get datacenter distribution for pie chart
        datacenter_stats = (
            self.db.query(
                DataProviderModel.datacenter,
                func.count(DatasetModel.id).label("dataset_count"),
                func.count(func.distinct(DataProviderModel.id)).label("provider_count"),
            )
            .join(DatasetModel, DatasetModel.provider_id == DataProviderModel.id)
            .filter(DataProviderModel.datacenter.isnot(None))
            .group_by(DataProviderModel.datacenter)
            .all()
        )

        datacenters = [
            {
                "datacenter": row.datacenter,
                "dataset_count": row.dataset_count,
                "provider_count": row.provider_count,
            }
            for row in datacenter_stats
        ]

        return {
            "providers": provider_list,
            "total_count": len(provider_list),
            "datacenters": datacenters,
        }

    def get_recent_activity(
        self, limit: int = 10, days: int = 30, user: UserModel | None = None
    ) -> dict[str, Any]:
        """Get recent dataset registration activity."""
        cutoff_date = date.today() - timedelta(days=days)

        recent_datasets = (
            self.db.query(DatasetModel)
            .filter(DatasetModel.created_at >= cutoff_date)
            .order_by(desc(DatasetModel.created_at))
            .limit(limit)
            .all()
        )

        return {
            "recent_datasets": [
                {
                    "id": ds.id,
                    "title": ds.title,
                    "provider_id": ds.provider_id,
                    "created_at": ds.created_at.isoformat() if ds.created_at else None,
                }
                for ds in recent_datasets
            ],
            "total_new_datasets": len(recent_datasets),
        }

    def get_health_status(self, user: UserModel | None = None) -> dict[str, Any]:
        """Get basic health metrics of the registry."""
        total_datasets = self.db.query(func.count(DatasetModel.id)).scalar() or 0
        total_archives = self.db.query(func.count(XmlArchiveModel.id)).scalar() or 0

        cutoff = date.today() - timedelta(days=7)
        recent_validations = (
            self.db.query(func.count(ValidationJobModel.id))
            .filter(ValidationJobModel.created_at >= cutoff)
            .scalar()
            or 0
        )

        # Simple health score
        health_score = 100
        if total_datasets == 0:
            health_score -= 30
        if total_archives == 0:
            health_score -= 30
        if recent_validations == 0:
            health_score -= 20

        return {
            "health_score": max(0, health_score),
            "total_datasets": total_datasets,
            "total_archives": total_archives,
            "recent_validations": recent_validations,
            "status": "healthy" if health_score >= 70 else "degraded",
        }

    def get_growth_metrics(
        self, period: str = "monthly", months: int = 12, user: UserModel | None = None
    ) -> dict[str, Any]:
        """
        Get cumulative growth metrics over time.

        Returns timeline data showing cumulative totals:
        - datasets_timeline: Total datasets over time (cumulative)
        - providers_timeline: Total providers over time (cumulative)
        - validation_timeline: Validation activity per period (not cumulative)
        """
        cutoff_date = date.today() - timedelta(days=months * 30)

        # Datasets timeline - cumulative count by creation month
        datasets_timeline = []
        if period == "monthly":
            dataset_results = (
                self.db.query(
                    func.date_trunc("month", DatasetModel.created_at).label("month"),
                    func.count(DatasetModel.id).label("count"),
                )
                .filter(DatasetModel.created_at >= cutoff_date)
                .group_by(func.date_trunc("month", DatasetModel.created_at))
                .order_by(func.date_trunc("month", DatasetModel.created_at))
                .all()
            )

            # Get count of datasets created before the cutoff for cumulative baseline
            baseline_count = (
                self.db.query(func.count(DatasetModel.id))
                .filter(DatasetModel.created_at < cutoff_date)
                .scalar()
                or 0
            )

            # Build cumulative timeline
            cumulative = baseline_count
            for row in dataset_results:
                if row.month:
                    cumulative += row.count
                    datasets_timeline.append({"date": row.month.date(), "value": cumulative})
        else:
            # Daily aggregation
            dataset_results = (
                self.db.query(
                    func.date(DatasetModel.created_at).label("day"),
                    func.count(DatasetModel.id).label("count"),
                )
                .filter(DatasetModel.created_at >= cutoff_date)
                .group_by(func.date(DatasetModel.created_at))
                .order_by(func.date(DatasetModel.created_at))
                .all()
            )

            baseline_count = (
                self.db.query(func.count(DatasetModel.id))
                .filter(DatasetModel.created_at < cutoff_date)
                .scalar()
                or 0
            )

            cumulative = baseline_count
            for row in dataset_results:
                if row.day:
                    cumulative += row.count
                    datasets_timeline.append({"date": row.day, "value": cumulative})

        # Providers timeline - cumulative count by creation month
        providers_timeline = []
        if period == "monthly":
            provider_results = (
                self.db.query(
                    func.date_trunc("month", DataProviderModel.created_at).label("month"),
                    func.count(DataProviderModel.id).label("count"),
                )
                .filter(DataProviderModel.created_at >= cutoff_date)
                .group_by(func.date_trunc("month", DataProviderModel.created_at))
                .order_by(func.date_trunc("month", DataProviderModel.created_at))
                .all()
            )

            baseline_count = (
                self.db.query(func.count(DataProviderModel.id))
                .filter(DataProviderModel.created_at < cutoff_date)
                .scalar()
                or 0
            )

            cumulative = baseline_count
            for row in provider_results:
                if row.month:
                    cumulative += row.count
                    providers_timeline.append({"date": row.month.date(), "value": cumulative})
        else:
            provider_results = (
                self.db.query(
                    func.date(DataProviderModel.created_at).label("day"),
                    func.count(DataProviderModel.id).label("count"),
                )
                .filter(DataProviderModel.created_at >= cutoff_date)
                .group_by(func.date(DataProviderModel.created_at))
                .order_by(func.date(DataProviderModel.created_at))
                .all()
            )

            baseline_count = (
                self.db.query(func.count(DataProviderModel.id))
                .filter(DataProviderModel.created_at < cutoff_date)
                .scalar()
                or 0
            )

            cumulative = baseline_count
            for row in provider_results:
                if row.day:
                    cumulative += row.count
                    providers_timeline.append({"date": row.day, "value": cumulative})

        # Validation timeline - count per period (not cumulative, shows activity)
        validation_timeline = []
        if period == "monthly":
            validation_results = (
                self.db.query(
                    func.date_trunc("month", ValidationJobModel.created_at).label("month"),
                    func.count(ValidationJobModel.id).label("count"),
                )
                .filter(ValidationJobModel.created_at >= cutoff_date)
                .group_by(func.date_trunc("month", ValidationJobModel.created_at))
                .order_by(func.date_trunc("month", ValidationJobModel.created_at))
                .all()
            )

            validation_timeline = [
                {"date": row.month.date() if row.month else None, "value": row.count}
                for row in validation_results
                if row.month
            ]
        else:
            validation_results = (
                self.db.query(
                    func.date(ValidationJobModel.created_at).label("day"),
                    func.count(ValidationJobModel.id).label("count"),
                )
                .filter(ValidationJobModel.created_at >= cutoff_date)
                .group_by(func.date(ValidationJobModel.created_at))
                .order_by(func.date(ValidationJobModel.created_at))
                .all()
            )

            validation_timeline = [
                {"date": row.day, "value": row.count} for row in validation_results if row.day
            ]

        return {
            "datasets_timeline": datasets_timeline,
            "providers_timeline": providers_timeline,
            "validation_timeline": validation_timeline,
        }
