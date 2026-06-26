"""
Snapshot service for querying archive snapshot data.

This service provides all statistics queries using the simplified
ArchiveSnapshot model with query-time SQL aggregation.

Glossary — the two timeline kinds (REQ-SH-LANG, discovery F-A)
-------------------------------------------------------------
The statistics surface exposes two semantically distinct "timeline" notions,
keyed on two different timestamps. They are named distinctly throughout so they
are never conflated:

* **Collection timeline** — the as-of series of biological-unit counts,
  forward-filled over ``ArchiveSnapshot.recorded_at`` (the collected-at instant).
  Produced by :meth:`get_biological_units_timeline` and the per-provider /
  multi-provider variants. Retired synonyms: "as-of timeline",
  "biological-units timeline", "snapshot timeline".
* **Registration timeline** — the cumulative series of entity (dataset /
  provider / validation) counts keyed on ``created_at`` (entity registration),
  unrelated to snapshot collection. Produced by :meth:`get_growth_metrics` and
  :meth:`get_provider_datasets_timeline` over the repository's
  ``get_entity_timeline`` primitive.

Total: ~200 lines (vs 1,085 in the old statistics_service.py)
"""

import logging
from datetime import UTC, date, datetime, timedelta
from typing import Any

from sqlalchemy.orm import Session

from app.models import DataProviderModel, DatasetModel, UserModel
from app.repositories.snapshot_repository import SnapshotRepository

logger = logging.getLogger(__name__)


class SnapshotService:
    """Service for snapshot-based statistics queries."""

    def __init__(self, db: Session):
        self.db = db
        self.repo = SnapshotRepository(db)

    # -------------------------------------------------------------------------
    # Overview & Counts (live database queries, not from snapshots)
    # -------------------------------------------------------------------------

    def get_overview_stats(
        self, user: UserModel | None = None, include_sensitive: bool = False
    ) -> dict[str, Any]:
        """Get system overview statistics using live counts."""
        validation_success_rate = self._calculate_validation_success_rate(days=30)

        return {
            "total_datasets": self.repo.count_datasets(),
            "total_providers": self.repo.count_providers(),
            "total_datacenters": self.repo.count_datacenters(),
            "total_xml_archives": self.repo.count_archives(),
            "validation_success_rate": validation_success_rate,
            "last_updated": datetime.now(UTC),
        }

    def get_quality_metrics(self, user: UserModel | None = None, days: int = 30) -> dict[str, Any]:
        """Get data quality metrics from validation jobs.

        Computed with bounded SQL aggregates (RH-03 / REQ-PG-2): this is a public,
        unauthenticated surface, so it must never materialize every validation-job
        row (each carrying a JSON ``results`` blob) into memory.
        """
        cutoff_date = date.today() - timedelta(days=days)

        total_validations, successful_validations, avg_processing_time = (
            self.repo.get_quality_metric_aggregates(cutoff_date)
        )

        failed_validations = total_validations - successful_validations

        success_rate = (
            (successful_validations / total_validations * 100) if total_validations > 0 else 0
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
        """Calculate validation success rate for the last N days.

        Uses bounded SQL counts (RH-03 / REQ-PG-2) rather than materializing the
        completed-job rows.
        """
        cutoff_date = date.today() - timedelta(days=days)
        completed, successful = self.repo.get_completed_validation_counts(since=cutoff_date)

        if not completed:
            return None

        return successful / completed * 100

    # -------------------------------------------------------------------------
    # Unit Count Queries (from ArchiveSnapshot)
    # -------------------------------------------------------------------------

    def get_dataset_unit_count(self, dataset_id: int) -> int | None:
        """Expected unit count for a dataset, or None when unknown (no snapshot
        data). This feeds the harvest-status N provider, which maps None to an
        honest "unknown" rather than a misleading 0 (B4)."""
        return self.repo.get_unit_count(dataset_id=dataset_id)

    def get_provider_unit_count(self, provider_id: int) -> int:
        """Get total unit count for a provider (0 when no snapshot data)."""
        return self.repo.get_unit_count(provider_id=provider_id) or 0

    def get_total_biological_units(self) -> int:
        """Get total biological units across all archives (0 when none)."""
        return self.repo.get_unit_count() or 0

    # -------------------------------------------------------------------------
    # Timeline Queries (for charts)
    # -------------------------------------------------------------------------

    def get_biological_units_timeline(
        self, start_date: date | None = None, end_date: date | None = None, limit: int = 30
    ) -> list[dict[str, Any]]:
        """
        Get the system-wide **collection timeline** of biological-unit counts.

        The collection timeline is the as-of series forward-filled over
        ``recorded_at``: for each date, uses the most recent snapshot for each
        archive up to that date. Only counts archives where isLatest=True. This is
        a collection timeline (collected-at), never a registration timeline.
        """
        dates = self.repo.get_snapshot_dates(start_date=start_date, end_date=end_date, limit=limit)

        if not dates:
            return []

        timeline = []
        for target_date in reversed(dates):
            total = self.repo.get_unit_count_for_date(target_date, latest_only=True)
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
        Only counts archives where isLatest=True.
        """
        dates = self.repo.get_snapshot_dates(
            start_date=start_date, end_date=end_date, provider_id=provider_id, limit=limit
        )

        if not dates:
            return []

        provider_archive_ids = self.repo.get_latest_archive_ids_for_provider(provider_id)

        if not provider_archive_ids:
            return []

        timeline = []
        for target_date in reversed(dates):
            total = self.repo.get_unit_count_for_date(target_date, archive_ids=provider_archive_ids)
            timeline.append({"date": target_date, "value": float(total)})

        return timeline

    def get_provider_datasets_timeline(
        self, provider_id: int, period: str = "daily", months: int = 12
    ) -> list[dict[str, Any]]:
        """Get cumulative dataset count timeline for a specific provider."""
        cutoff_date = date.today() - timedelta(days=months * 30)

        rows, baseline = self.repo.get_entity_timeline(
            DatasetModel, provider_id=provider_id, period=period, cutoff_date=cutoff_date
        )

        cumulative = baseline
        timeline = []
        for row in rows:
            if row.period:
                cumulative += row.count
                period_date = row.period.date() if period == "monthly" else row.period
                timeline.append({"date": period_date, "value": cumulative})
        return timeline

    def get_multi_provider_timeline(
        self, start_date: date | None = None, end_date: date | None = None, limit: int = 30
    ) -> dict[str, Any]:
        """
        Get biological units timeline for all providers with forward-fill.
        Only counts archives where isLatest=True.
        """
        dates = self.repo.get_snapshot_dates(start_date=start_date, end_date=end_date, limit=limit)

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

        providers = self.repo.get_providers_with_snapshots()

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
            archive_ids = self.repo.get_latest_archive_ids_for_provider(provider_id)
            provider_archives[provider_name] = archive_ids

        # For each date, calculate totals per provider using forward-fill
        data_points = []
        for target_date in reversed(dates):
            date_point = {"date": target_date.isoformat()}

            for provider_name, archive_ids in provider_archives.items():
                if not archive_ids:
                    date_point[provider_name] = 0.0
                    continue

                total = self.repo.get_unit_count_for_date(target_date, archive_ids=archive_ids)
                date_point[provider_name] = float(total)

            data_points.append(date_point)

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
        provider = self.repo.get_provider_by_id(provider_id)

        if not provider:
            return None

        validation_success_rate = self._calculate_provider_validation_rate(provider_id)

        last_dataset = self.repo.get_last_dataset_for_provider(provider_id)

        return {
            "provider_id": provider_id,
            "provider_name": provider.name,
            "dataset_count": self.repo.count_datasets_for_provider(provider_id),
            "xml_archive_count": self.repo.count_archives_for_provider(provider_id),
            "validation_success_rate": validation_success_rate,
            "last_activity": last_dataset.updated_at if last_dataset else None,
            "activity_score": None,  # No longer tracked
        }

    def _calculate_provider_validation_rate(self, provider_id: int) -> float | None:
        """Calculate validation success rate for a specific provider.

        Uses bounded SQL counts (RH-03 / REQ-PG-2) rather than materializing the
        completed-job rows.
        """
        cutoff_date = date.today() - timedelta(days=30)
        completed, successful = self.repo.get_completed_validation_counts(
            since=cutoff_date, provider_id=provider_id
        )

        if not completed:
            return None

        return successful / completed * 100

    def get_dataset_statistics(
        self, dataset_id: int, user: UserModel | None = None
    ) -> dict[str, Any] | None:
        """Get statistics for a specific dataset."""
        dataset = self.repo.get_dataset_by_id(dataset_id)

        if not dataset:
            return None

        unit_count = self.get_dataset_unit_count(dataset_id)
        latest_validation = self.repo.get_latest_validation_for_dataset(dataset_id)

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
        providers = self.repo.get_providers(limit=limit)

        provider_list = []
        for provider in providers:
            dataset_count = self.repo.count_datasets_for_provider(provider.id)
            unit_count = self.get_provider_unit_count(provider.id)

            provider_list.append(
                {
                    "provider_id": provider.id,
                    "provider_name": provider.name,
                    "dataset_count": dataset_count,
                    "biological_units": unit_count,
                }
            )

        provider_list.sort(key=lambda x: x["biological_units"], reverse=True)

        datacenter_stats = self.repo.get_datacenter_stats()
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
        recent_datasets = self.repo.get_recent_datasets(since=cutoff_date, limit=limit)

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
        total_datasets = self.repo.count_datasets()
        total_archives = self.repo.count_archives()

        cutoff = date.today() - timedelta(days=7)
        recent_validations = self.repo.count_recent_validations(since=cutoff)

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
        Get the **registration timeline** — cumulative entity growth over time.

        The registration timeline is keyed on ``created_at`` (entity registration),
        unrelated to snapshot collection; it is not a collection timeline. Returns:
        - datasets_timeline: Total datasets over time (cumulative)
        - providers_timeline: Total providers over time (cumulative)
        - validation_timeline: Validation activity per period (not cumulative)
        """
        cutoff_date = date.today() - timedelta(days=months * 30)

        # Datasets timeline
        dataset_rows, dataset_baseline = self.repo.get_entity_timeline(
            DatasetModel, period=period, cutoff_date=cutoff_date
        )
        datasets_timeline = self._build_cumulative_timeline(dataset_rows, dataset_baseline, period)

        # Providers timeline
        provider_rows, provider_baseline = self.repo.get_entity_timeline(
            DataProviderModel, period=period, cutoff_date=cutoff_date
        )
        providers_timeline = self._build_cumulative_timeline(
            provider_rows, provider_baseline, period
        )

        # Validation timeline (not cumulative)
        validation_rows = self.repo.get_validation_timeline(period=period, cutoff_date=cutoff_date)
        validation_timeline = [
            {"date": row.period.date() if period == "monthly" else row.period, "value": row.count}
            for row in validation_rows
            if row.period
        ]

        return {
            "datasets_timeline": datasets_timeline,
            "providers_timeline": providers_timeline,
            "validation_timeline": validation_timeline,
        }

    @staticmethod
    def _build_cumulative_timeline(rows: list, baseline: int, period: str) -> list[dict[str, Any]]:
        """Build a cumulative timeline from period rows and baseline count."""
        cumulative = baseline
        timeline = []
        for row in rows:
            if row.period:
                cumulative += row.count
                period_date = row.period.date() if period == "monthly" else row.period
                timeline.append({"date": period_date, "value": cumulative})
        return timeline
