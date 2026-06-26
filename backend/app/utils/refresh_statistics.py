#!/usr/bin/env python3
"""
Management command to trigger archive snapshot collection.
Can be run as: python -m app.utils.refresh_statistics
"""

import argparse
import sys

from sqlalchemy import func, select, text

# Add the app directory to path
sys.path.insert(0, "/app")

from app.core.utils import utc_now  # noqa: E402
from app.db.session import SessionLocal  # noqa: E402
from app.models.archive_snapshot import ArchiveSnapshotModel  # noqa: E402
from app.models.dataset import XmlArchiveModel  # noqa: E402
from app.tasks.snapshot_tasks import collect_archive_snapshots  # noqa: E402


def latest_total_units(db) -> int:
    """Sum unit_count of only the latest snapshot per latest archive (B20).

    archive_snapshots is append-only (one new row per archive per daily run,
    even when unchanged), so a flat SUM(unit_count) inflates the total by the
    number of collection runs. Mirror the authoritative
    snapshot_repository.get_unit_count_for_date(latest_only=True): take
    max(recorded_at) per archive_id and restrict to isLatest archives.
    """
    latest = (
        select(
            ArchiveSnapshotModel.archive_id.label("archive_id"),
            func.max(ArchiveSnapshotModel.recorded_at).label("max_recorded"),
        )
        .group_by(ArchiveSnapshotModel.archive_id)
        .subquery()
    )
    stmt = (
        select(func.coalesce(func.sum(ArchiveSnapshotModel.unit_count), 0))
        .select_from(ArchiveSnapshotModel)
        .join(
            latest,
            (ArchiveSnapshotModel.archive_id == latest.c.archive_id)
            & (ArchiveSnapshotModel.recorded_at == latest.c.max_recorded),
        )
        .join(XmlArchiveModel, XmlArchiveModel.id == ArchiveSnapshotModel.archive_id)
        .where(XmlArchiveModel.isLatest.is_(True))
    )
    return int(db.execute(stmt).scalar_one())


def queue_snapshot_collection():
    """Queue archive snapshot collection."""
    print("\nQueueing archive snapshot collection...")
    task = collect_archive_snapshots.delay()
    print(f"  Task ID: {task.id}")
    return task.id


def check_snapshot_status():
    """Check current snapshot status."""
    db = SessionLocal()
    try:
        # Overall snapshot statistics
        result = db.execute(
            text("""
            SELECT
                COUNT(*) as total_snapshots,
                COUNT(DISTINCT archive_id) as unique_archives,
                MIN(recorded_at) as earliest_snapshot,
                MAX(recorded_at) as latest_snapshot
            FROM archive_snapshots
        """)
        )

        print("\nCurrent Snapshot Status:")
        print("-" * 60)
        row = result.fetchone()
        if row:
            print(f"Total snapshots: {row.total_snapshots}")
            print(f"Unique archives: {row.unique_archives}")
            print(f"Earliest: {row.earliest_snapshot}")
            print(f"Latest: {row.latest_snapshot}")
            # Sum only the latest snapshot per latest archive, not every row.
            print(f"Total units (latest): {latest_total_units(db)}")

        # Archive coverage
        coverage_result = db.execute(
            text("""
            SELECT
                COUNT(DISTINCT xa.id) as total_archives,
                COUNT(DISTINCT CASE WHEN s.archive_id IS NOT NULL THEN xa.id END) as with_snapshots,
                COUNT(DISTINCT CASE WHEN s.archive_id IS NULL THEN xa.id END) as without_snapshots
            FROM xml_archives xa
            LEFT JOIN archive_snapshots s ON s.archive_id = xa.id
            WHERE xa."isLatest" = true
        """)
        )

        row = coverage_result.fetchone()
        if row and row.total_archives > 0:
            print("\nArchive Coverage:")
            print(f"  Total latest archives: {row.total_archives}")
            print(
                f"  With snapshots: {row.with_snapshots} ({row.with_snapshots * 100 // row.total_archives}%)"
            )
            print(
                f"  Without snapshots: {row.without_snapshots} ({row.without_snapshots * 100 // row.total_archives}%)"
            )

    finally:
        db.close()


def main():
    parser = argparse.ArgumentParser(description="Refresh archive snapshots")
    parser.add_argument("--collect", action="store_true", help="Collect archive snapshots")
    parser.add_argument("--status", action="store_true", help="Show snapshot status")

    args = parser.parse_args()

    # If no specific flags, show status
    if not any([args.collect, args.status]):
        args.status = True

    print(f"Snapshot Refresh Tool (UTC) - {utc_now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)

    if args.status:
        check_snapshot_status()

    tasks = []

    if args.collect:
        print("\n📊 Queueing Archive Snapshot Collection...")
        task_id = queue_snapshot_collection()
        tasks.append(task_id)

    if tasks:
        print(f"\n✓ Queued {len(tasks)} total tasks")
        print("\nMonitor progress with:")
        print('  docker logs -f searchgfbioorg-celery_worker-1 | grep "Snapshot"')
        print("\nCheck results with:")
        print("  python -m app.utils.refresh_statistics --status")

    return 0


if __name__ == "__main__":
    sys.exit(main())
