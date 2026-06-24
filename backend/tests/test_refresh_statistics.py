"""Regression test for the snapshot-status 'Total units (latest)' figure (B20).

archive_snapshots is append-only: collect_archive_snapshots inserts a new row
per latest archive every day, even when unchanged. A flat SUM(unit_count) over
the table therefore inflates by the number of collection runs while being
labelled "(latest)". The correct figure sums only the latest snapshot per
latest archive (mirroring snapshot_repository.get_unit_count_for_date).
"""

from datetime import datetime

from sqlalchemy import text

from app.models.archive_snapshot import ArchiveSnapshotModel
from app.models.dataset import XmlArchiveModel
from app.utils.refresh_statistics import latest_total_units


def _seed(session):
    # archive 1 is the current/latest archive with 3 daily snapshots of 100.
    session.add(XmlArchiveModel(id=1, isLatest=True))
    # archive 2 is superseded (isLatest False) and must be excluded.
    session.add(XmlArchiveModel(id=2, isLatest=False))
    session.flush()
    for day in (10, 11, 12):
        session.add(
            ArchiveSnapshotModel(
                archive_id=1, unit_count=100, recorded_at=datetime(2026, 6, day, 3, 0, 0)
            )
        )
    session.add(
        ArchiveSnapshotModel(
            archive_id=2, unit_count=500, recorded_at=datetime(2026, 6, 12, 3, 0, 0)
        )
    )
    session.commit()


def test_latest_total_units_counts_latest_snapshot_per_latest_archive(sync_db_session):
    _seed(sync_db_session)

    # The old flat SUM over all snapshots is the inflated, wrong figure.
    flat_sum = sync_db_session.execute(
        text("SELECT COALESCE(SUM(unit_count), 0) FROM archive_snapshots")
    ).scalar()
    assert flat_sum == 800  # 100*3 + 500 (the buggy "(latest)" value)

    # The corrected figure: archive 1's single latest snapshot only; archive 2
    # excluded because it is not the latest archive.
    assert latest_total_units(sync_db_session) == 100
