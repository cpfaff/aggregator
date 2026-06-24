"""
Repository for snapshot and statistics data access operations.

Uses synchronous Session (not AsyncSession) because SnapshotService
is consumed by both async endpoints and synchronous Celery tasks.
"""

from datetime import date, timedelta
from typing import Any

from sqlalchemy import and_, desc, func
from sqlalchemy.orm import Session

from app.models import (
    DataProviderModel,
    DatasetModel,
    ValidationJobModel,
    XmlArchiveModel,
)
from app.models.archive_snapshot import ArchiveSnapshotModel


class SnapshotRepository:
    """Data access layer for snapshot-based statistics queries.

    NOTE: This repository uses synchronous Session, not AsyncSession,
    because the statistics endpoints run in a sync context.
    It does not extend BaseRepository which requires AsyncSession.
    """

    def __init__(self, db: Session):
        self.db = db

    # -------------------------------------------------------------------------
    # Simple counts
    # -------------------------------------------------------------------------

    def count_datasets(self) -> int:
        return self.db.query(func.count(DatasetModel.id)).scalar() or 0

    def count_providers(self) -> int:
        return self.db.query(func.count(DataProviderModel.id)).scalar() or 0

    def count_archives(self) -> int:
        return self.db.query(func.count(XmlArchiveModel.id)).scalar() or 0

    def count_datacenters(self) -> int:
        return (
            self.db.query(func.count(DataProviderModel.id))
            .filter(DataProviderModel.isDataCenter)
            .scalar()
            or 0
        )

    # -------------------------------------------------------------------------
    # Validation queries
    # -------------------------------------------------------------------------

    def get_completed_validation_jobs(
        self, since: date, provider_id: int | None = None
    ) -> list[ValidationJobModel]:
        """Get completed validation jobs since a cutoff date, optionally for a provider."""
        query = self.db.query(ValidationJobModel).filter(
            and_(
                ValidationJobModel.created_at >= since,
                ValidationJobModel.status == "completed",
            )
        )

        if provider_id is not None:
            query = (
                query.join(XmlArchiveModel, ValidationJobModel.archive_id == XmlArchiveModel.id)
                .join(DatasetModel, XmlArchiveModel.dataset_id == DatasetModel.id)
                .filter(DatasetModel.provider_id == provider_id)
            )

        return query.all()

    def get_validation_jobs_since(self, since: date) -> list[ValidationJobModel]:
        """Get all validation jobs since a cutoff date."""
        return (
            self.db.query(ValidationJobModel).filter(ValidationJobModel.created_at >= since).all()
        )

    def count_recent_validations(self, since: date) -> int:
        """Count validation jobs since a date."""
        return (
            self.db.query(func.count(ValidationJobModel.id))
            .filter(ValidationJobModel.created_at >= since)
            .scalar()
            or 0
        )

    # -------------------------------------------------------------------------
    # Provider queries
    # -------------------------------------------------------------------------

    def get_provider_by_id(self, provider_id: int) -> DataProviderModel | None:
        return self.db.query(DataProviderModel).filter(DataProviderModel.id == provider_id).first()

    def count_datasets_for_provider(self, provider_id: int) -> int:
        return (
            self.db.query(func.count(DatasetModel.id))
            .filter(DatasetModel.provider_id == provider_id)
            .scalar()
            or 0
        )

    def count_archives_for_provider(self, provider_id: int) -> int:
        return (
            self.db.query(func.count(XmlArchiveModel.id))
            .join(DatasetModel)
            .filter(DatasetModel.provider_id == provider_id)
            .scalar()
            or 0
        )

    def get_last_dataset_for_provider(self, provider_id: int) -> DatasetModel | None:
        return (
            self.db.query(DatasetModel)
            .filter(DatasetModel.provider_id == provider_id)
            .order_by(desc(DatasetModel.updated_at))
            .first()
        )

    def get_providers(self, limit: int = 20) -> list[DataProviderModel]:
        return self.db.query(DataProviderModel).limit(limit).all()

    def get_providers_with_snapshots(self) -> list[tuple[int, str]]:
        """Get providers that have snapshot data (id, name tuples)."""
        return (
            self.db.query(DataProviderModel.id, DataProviderModel.name)
            .join(DatasetModel, DataProviderModel.id == DatasetModel.provider_id)
            .join(XmlArchiveModel, DatasetModel.id == XmlArchiveModel.dataset_id)
            .join(ArchiveSnapshotModel, XmlArchiveModel.id == ArchiveSnapshotModel.archive_id)
            .filter(XmlArchiveModel.isLatest)
            .distinct()
            .all()
        )

    def get_datacenter_stats(self) -> list[Any]:
        """Get datacenter distribution statistics."""
        return (
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

    # -------------------------------------------------------------------------
    # Dataset queries
    # -------------------------------------------------------------------------

    def get_dataset_by_id(self, dataset_id: int) -> DatasetModel | None:
        return self.db.query(DatasetModel).filter(DatasetModel.id == dataset_id).first()

    def get_latest_validation_for_dataset(self, dataset_id: int) -> ValidationJobModel | None:
        return (
            self.db.query(ValidationJobModel)
            .join(XmlArchiveModel)
            .filter(XmlArchiveModel.dataset_id == dataset_id)
            .order_by(desc(ValidationJobModel.created_at))
            .first()
        )

    def get_recent_datasets(self, since: date, limit: int = 10) -> list[DatasetModel]:
        return (
            self.db.query(DatasetModel)
            .filter(DatasetModel.created_at >= since)
            .order_by(desc(DatasetModel.created_at))
            .limit(limit)
            .all()
        )

    # -------------------------------------------------------------------------
    # Archive ID queries
    # -------------------------------------------------------------------------

    def get_latest_archive_ids_for_provider(self, provider_id: int) -> list[int]:
        """Get IDs of latest archives for a provider."""
        return [
            r[0]
            for r in self.db.query(XmlArchiveModel.id)
            .join(DatasetModel, XmlArchiveModel.dataset_id == DatasetModel.id)
            .filter(DatasetModel.provider_id == provider_id, XmlArchiveModel.isLatest)
            .all()
        ]

    # -------------------------------------------------------------------------
    # Unit count queries (from ArchiveSnapshot)
    # -------------------------------------------------------------------------

    def _latest_snapshot_subquery(
        self,
        dataset_id: int | None = None,
        provider_id: int | None = None,
        latest_only: bool = True,
    ):
        """Build subquery for latest snapshot per archive with optional filters."""
        query = self.db.query(
            ArchiveSnapshotModel.archive_id,
            func.max(ArchiveSnapshotModel.recorded_at).label("max_recorded"),
        ).join(XmlArchiveModel, ArchiveSnapshotModel.archive_id == XmlArchiveModel.id)

        if dataset_id is not None:
            query = query.filter(XmlArchiveModel.dataset_id == dataset_id)

        if provider_id is not None:
            query = query.join(DatasetModel, XmlArchiveModel.dataset_id == DatasetModel.id).filter(
                DatasetModel.provider_id == provider_id
            )

        if latest_only:
            query = query.filter(XmlArchiveModel.isLatest)

        return query.group_by(ArchiveSnapshotModel.archive_id).subquery()

    def get_unit_count(
        self,
        dataset_id: int | None = None,
        provider_id: int | None = None,
    ) -> int | None:
        """Get total unit count, optionally scoped to dataset or provider.

        Returns None when there is no matching snapshot data so callers can tell
        "unknown" apart from a genuine zero (B4); display callers coerce to 0.
        """
        subquery = self._latest_snapshot_subquery(dataset_id=dataset_id, provider_id=provider_id)

        result = (
            self.db.query(func.sum(ArchiveSnapshotModel.unit_count))
            .join(
                subquery,
                and_(
                    ArchiveSnapshotModel.archive_id == subquery.c.archive_id,
                    ArchiveSnapshotModel.recorded_at == subquery.c.max_recorded,
                ),
            )
            .scalar()
        )

        return result

    # -------------------------------------------------------------------------
    # Timeline queries
    # -------------------------------------------------------------------------

    def get_snapshot_dates(
        self,
        start_date: date | None = None,
        end_date: date | None = None,
        provider_id: int | None = None,
        limit: int = 30,
    ) -> list[date]:
        """Get distinct dates that have snapshot data."""
        query = (
            self.db.query(func.date(ArchiveSnapshotModel.recorded_at).label("date"))
            .distinct()
            .order_by(desc(func.date(ArchiveSnapshotModel.recorded_at)))
        )

        if provider_id is not None:
            query = (
                query.join(XmlArchiveModel, ArchiveSnapshotModel.archive_id == XmlArchiveModel.id)
                .join(DatasetModel, XmlArchiveModel.dataset_id == DatasetModel.id)
                .filter(DatasetModel.provider_id == provider_id)
            )

        if start_date:
            query = query.filter(ArchiveSnapshotModel.recorded_at >= start_date)
        if end_date:
            # Compare on the calendar date so same-day snapshots recorded after
            # midnight (beat runs at 02:00) are within the inclusive upper bound,
            # matching get_unit_count_for_date's day-granular semantics (B10/B5).
            query = query.filter(func.date(ArchiveSnapshotModel.recorded_at) <= end_date)

        return [r.date for r in query.limit(limit).all()]

    def get_unit_count_for_date(
        self,
        target_date: date,
        archive_ids: list[int] | None = None,
        latest_only: bool = True,
    ) -> int:
        """Get total unit count as of a specific date using forward-fill."""
        latest_per_archive = self.db.query(
            ArchiveSnapshotModel.archive_id,
            func.max(ArchiveSnapshotModel.recorded_at).label("max_recorded"),
        ).filter(func.date(ArchiveSnapshotModel.recorded_at) <= target_date)

        if archive_ids is not None:
            latest_per_archive = latest_per_archive.filter(
                ArchiveSnapshotModel.archive_id.in_(archive_ids)
            )

        latest_per_archive = latest_per_archive.group_by(ArchiveSnapshotModel.archive_id).subquery()

        query = self.db.query(func.sum(ArchiveSnapshotModel.unit_count)).join(
            latest_per_archive,
            and_(
                ArchiveSnapshotModel.archive_id == latest_per_archive.c.archive_id,
                ArchiveSnapshotModel.recorded_at == latest_per_archive.c.max_recorded,
            ),
        )

        if latest_only and archive_ids is None:
            query = query.join(
                XmlArchiveModel, ArchiveSnapshotModel.archive_id == XmlArchiveModel.id
            ).filter(XmlArchiveModel.isLatest)

        return query.scalar() or 0

    # -------------------------------------------------------------------------
    # Growth/timeline aggregation queries
    # -------------------------------------------------------------------------

    def get_entity_timeline(
        self,
        model: type,
        provider_id: int | None = None,
        period: str = "monthly",
        cutoff_date: date | None = None,
    ) -> tuple[list[Any], int]:
        """Get entity creation timeline with baseline count.

        Returns (rows, baseline_count) where rows are (period, count) tuples.
        """
        if cutoff_date is None:
            cutoff_date = date.today() - timedelta(days=360)

        date_col = model.created_at

        if period == "monthly":
            period_expr = func.date_trunc("month", date_col)
        else:
            period_expr = func.date(date_col)

        query = self.db.query(
            period_expr.label("period"),
            func.count(model.id).label("count"),
        ).filter(date_col >= cutoff_date)

        if provider_id is not None and hasattr(model, "provider_id"):
            query = query.filter(model.provider_id == provider_id)

        rows = query.group_by(period_expr).order_by(period_expr).all()

        # Baseline count
        baseline_query = self.db.query(func.count(model.id)).filter(date_col < cutoff_date)

        if provider_id is not None and hasattr(model, "provider_id"):
            baseline_query = baseline_query.filter(model.provider_id == provider_id)

        baseline = baseline_query.scalar() or 0

        return rows, baseline

    def get_validation_timeline(
        self, period: str = "monthly", cutoff_date: date | None = None
    ) -> list[Any]:
        """Get validation job count timeline (not cumulative)."""
        if cutoff_date is None:
            cutoff_date = date.today() - timedelta(days=360)

        if period == "monthly":
            period_expr = func.date_trunc("month", ValidationJobModel.created_at)
        else:
            period_expr = func.date(ValidationJobModel.created_at)

        return (
            self.db.query(
                period_expr.label("period"),
                func.count(ValidationJobModel.id).label("count"),
            )
            .filter(ValidationJobModel.created_at >= cutoff_date)
            .group_by(period_expr)
            .order_by(period_expr)
            .all()
        )
