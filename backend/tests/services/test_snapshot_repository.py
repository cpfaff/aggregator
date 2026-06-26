"""REQ-SH-AGG: one latest-snapshot-per-archive primitive; coherent totals + empty case.

Discovery F-C: the "max(recorded_at) per archive, restrict to isLatest, SUM(unit_count)"
computation was re-implemented four times (repo ``_latest_snapshot_subquery``, the
inline subquery in ``get_unit_count_for_date``, the management tool's
``latest_total_units``, and the nightly task's metadata lookup). F-D: two of those
disagreed on the empty case (None vs 0).

These tests pin the consolidation at the snapshot-repository seam:

* AGG-1 — the latest-snapshot-per-archive selection is one shared primitive (the
  "max(recorded_at) per archive" idiom is defined exactly once across the subsystem).
* AGG-2 — for identical data, the point total (latest snapshot per archive) equals
  the latest-date collection-timeline total (forward-filled), i.e. the two paths
  cannot drift.
* AGG-3 — each unit-count read declares its empty case: ``get_unit_count`` returns
  None ("unknown"); ``get_unit_count_for_date`` returns 0 ("zero"). The split is
  deliberate and preserved.
"""

from datetime import date, datetime
from pathlib import Path

from app.models.archive_snapshot import ArchiveSnapshotModel
from app.models.dataset import DatasetModel, XmlArchiveModel
from app.models.provider import DataProviderModel
from app.repositories.snapshot_repository import SnapshotRepository

_BACKEND = Path(__file__).resolve().parents[2]


def _seed_two_latest_archives(session):
    """Two isLatest archives under one provider/dataset; return (archive_a, archive_b)."""
    provider = DataProviderModel(name="Prov", shortName="PR", datacenter="DC")
    session.add(provider)
    session.flush()
    dataset = DatasetModel(title="DS", source="src", provider_id=provider.id)
    session.add(dataset)
    session.flush()
    a = XmlArchiveModel(dataset_id=dataset.id, url="http://example.com/a.xml", isLatest=True)
    b = XmlArchiveModel(dataset_id=dataset.id, url="http://example.com/b.xml", isLatest=True)
    session.add_all([a, b])
    session.flush()
    return a, b


# ---------------------------------------------------------------------------
# AGG-1 — single shared primitive
# ---------------------------------------------------------------------------


def test_latest_snapshot_per_archive_primitive_exists():
    """REQ-SH-AGG-1: there is a single named latest-snapshot-per-archive primitive."""
    assert callable(getattr(SnapshotRepository, "latest_snapshot_per_archive", None))


def test_max_recorded_per_archive_idiom_defined_once():
    """REQ-SH-AGG-1: the 'max(recorded_at) per archive' selection is written once.

    Counts the idiom across the three modules that previously each re-derived it.
    Exactly one definition (the repository primitive) must remain; the management
    tool and the nightly task compose it rather than rebuild it.
    """
    idiom = "func.max(ArchiveSnapshotModel.recorded_at)"
    files = [
        "app/repositories/snapshot_repository.py",
        "app/utils/refresh_statistics.py",
        "app/tasks/snapshot_tasks.py",
    ]
    counts = {rel: (_BACKEND / rel).read_text().count(idiom) for rel in files}
    total = sum(counts.values())
    assert total == 1, f"latest-per-archive idiom defined {total} times, expected 1: {counts}"


# ---------------------------------------------------------------------------
# AGG-2 — point total == latest-date collection-timeline total
# ---------------------------------------------------------------------------


def test_point_total_equals_latest_date_timeline_total_simple(sync_db_session):
    """REQ-SH-AGG-2: with a snapshot for every archive on the latest date, the point
    total equals the latest-date collection-timeline total."""
    a, b = _seed_two_latest_archives(sync_db_session)
    sync_db_session.add_all(
        [
            ArchiveSnapshotModel(archive_id=a.id, recorded_at=datetime(2024, 1, 1), unit_count=100),
            ArchiveSnapshotModel(archive_id=a.id, recorded_at=datetime(2024, 2, 1), unit_count=150),
            ArchiveSnapshotModel(archive_id=b.id, recorded_at=datetime(2024, 1, 1), unit_count=200),
            ArchiveSnapshotModel(archive_id=b.id, recorded_at=datetime(2024, 2, 1), unit_count=250),
        ]
    )
    sync_db_session.flush()
    repo = SnapshotRepository(sync_db_session)

    point_total = repo.get_unit_count()
    latest_date = max(repo.get_snapshot_dates())
    timeline_total = repo.get_unit_count_for_date(latest_date, latest_only=True)

    assert point_total == 400
    assert timeline_total == point_total


def test_point_total_equals_latest_date_timeline_total_with_forward_fill(sync_db_session):
    """REQ-SH-AGG-2: when one archive has no snapshot on the latest date, forward-fill
    makes the latest-date timeline total still equal the point total — the crux that
    keeps the two arithmetic paths from drifting."""
    a, b = _seed_two_latest_archives(sync_db_session)
    sync_db_session.add_all(
        [
            # archive a: only an older snapshot (must be forward-filled to the latest date)
            ArchiveSnapshotModel(archive_id=a.id, recorded_at=datetime(2024, 1, 1), unit_count=100),
            # archive b: snapshots on both dates
            ArchiveSnapshotModel(archive_id=b.id, recorded_at=datetime(2024, 1, 1), unit_count=200),
            ArchiveSnapshotModel(archive_id=b.id, recorded_at=datetime(2024, 2, 1), unit_count=250),
        ]
    )
    sync_db_session.flush()
    repo = SnapshotRepository(sync_db_session)

    point_total = repo.get_unit_count()  # a:100 (latest) + b:250 (latest) = 350
    latest_date = max(repo.get_snapshot_dates())  # 2024-02-01
    timeline_total = repo.get_unit_count_for_date(latest_date, latest_only=True)

    assert point_total == 350
    assert timeline_total == point_total


# ---------------------------------------------------------------------------
# AGG-3 — explicit empty-case contract (unknown vs zero)
# ---------------------------------------------------------------------------


def test_get_unit_count_empty_is_unknown_none(sync_db_session):
    """REQ-SH-AGG-3: get_unit_count returns None on no data — 'unknown', so callers
    can tell it apart from a genuine zero (B4)."""
    repo = SnapshotRepository(sync_db_session)
    assert repo.get_unit_count() is None
    assert repo.get_unit_count(dataset_id=999) is None
    assert repo.get_unit_count(provider_id=999) is None


def test_get_unit_count_for_date_empty_is_zero(sync_db_session):
    """REQ-SH-AGG-3: get_unit_count_for_date returns 0 on no data — 'zero', the
    deliberately-different empty-case contract for the as-of timeline read."""
    repo = SnapshotRepository(sync_db_session)
    assert repo.get_unit_count_for_date(date(2024, 6, 1)) == 0
