"""Snapshot insertion must be idempotent under acks_late redelivery (RH-06).

``collect_single_archive_snapshot`` is an ``acks_late`` task: a worker crash, a
lost ack, or a broker visibility-timeout redelivery can run it a second time for
the same archive on the same calendar day. Pre-fix it unconditionally
``db.add``/``commit``s a new ``ArchiveSnapshotModel``, so a redelivery
double-inserts a duplicate snapshot row for the same archive/day
(REQ-CEL-3 / F-CELERY-03 / F-SNAP-03).

The fix adds a deterministic ``(archive_id, day)`` guard: before inserting, the
task checks for an existing snapshot for this archive recorded today and, if one
exists, short-circuits to an ``already_recorded`` status (mirroring the existing
change-detection short-circuit). A functional UNIQUE index plus an
``IntegrityError`` catch is the defense-in-depth DB guard.

These tests drive the task body directly against the Postgres testcontainer with
``SessionLocal`` patched to a per-call session factory on the shared engine
(mirroring how Celery opens a fresh session per run), and ``parse_archive_xml`` /
``check_archive_changed`` stubbed so change-detection always reports "changed":

* ``test_single_snapshot_redelivery_inserts_once`` — the stub returns
  ``etag=None, last_modified=None`` so the no-previous-metadata path reports the
  archive as *changed* on the second run; without the guard this inserts TWO
  rows. The stub MUST use ``etag=None`` — a stable ETag would hit the "unchanged"
  short-circuit and the test would pass tautologically.
* ``test_snapshot_new_day_inserts_again`` — a snapshot already recorded on a
  *different* calendar day must not block today's insert (the guard keys on the
  day, not the archive alone).
"""

from datetime import datetime, timedelta
from unittest.mock import patch

from sqlalchemy.orm import Session

from app.models.archive_snapshot import ArchiveSnapshotModel
from app.models.dataset import XmlArchiveModel
from app.tasks import snapshot_tasks
from app.tasks.snapshot_tasks import (
    ArchiveParseResult,
    HttpMetadata,
    collect_single_archive_snapshot,
)


def _seed_archive(session) -> int:
    archive = XmlArchiveModel(url="http://example.com/a.xml", isLatest=True)
    session.add(archive)
    session.commit()
    return archive.id


def _session_factory(engine):
    def make():
        return Session(engine, expire_on_commit=False)

    return make


def _changed_parse_result():
    """A parse result whose HTTP metadata has no ETag / Last-Modified.

    On the second run the latest snapshot carries these None values, so
    ``check_archive_changed`` takes the no-previous-metadata path and reports
    "changed" — exercising the genuine re-insert path (not the unchanged
    short-circuit).
    """
    return ArchiveParseResult(
        unit_count=5,
        http_metadata=HttpMetadata(etag=None, last_modified=None),
    )


def test_single_snapshot_redelivery_inserts_once(sync_engine, sync_db_session):
    """Calling the task twice for the same archive on the same day inserts ONE row.

    With ``etag=None`` the change-detection layer reports "changed" on the second
    run, so only the new ``(archive_id, day)`` guard prevents the duplicate.
    Pre-fix this asserts 2 rows (RED); post-fix exactly 1.
    """
    archive_id = _seed_archive(sync_db_session)

    with (
        patch.object(snapshot_tasks, "SessionLocal", _session_factory(sync_engine)),
        patch.object(
            snapshot_tasks,
            "parse_archive_xml",
            return_value=_changed_parse_result(),
        ),
        patch.object(
            snapshot_tasks,
            "check_archive_changed",
            return_value=(True, HttpMetadata(etag=None, last_modified=None)),
        ),
    ):
        collect_single_archive_snapshot(archive_id)
        collect_single_archive_snapshot(archive_id)  # acks_late redelivery

    rows = (
        sync_db_session.query(ArchiveSnapshotModel)
        .filter(ArchiveSnapshotModel.archive_id == archive_id)
        .all()
    )
    assert len(rows) == 1, f"redelivery inserted {len(rows)} snapshot rows, expected exactly 1"


def test_snapshot_new_day_inserts_again(sync_engine, sync_db_session):
    """A snapshot recorded on a previous day does not block today's insert.

    The guard keys on ``(archive_id, date(recorded_at))``: a row from yesterday
    must still allow a fresh row today (otherwise the daily timeline would
    flatline once an archive is ever snapshotted).
    """
    archive_id = _seed_archive(sync_db_session)

    # Seed a snapshot dated yesterday for this archive.
    yesterday_snapshot = ArchiveSnapshotModel(
        archive_id=archive_id,
        unit_count=3,
        recorded_at=datetime.utcnow() - timedelta(days=1),
    )
    sync_db_session.add(yesterday_snapshot)
    sync_db_session.commit()

    with (
        patch.object(snapshot_tasks, "SessionLocal", _session_factory(sync_engine)),
        patch.object(
            snapshot_tasks,
            "parse_archive_xml",
            return_value=_changed_parse_result(),
        ),
        patch.object(
            snapshot_tasks,
            "check_archive_changed",
            return_value=(True, HttpMetadata(etag=None, last_modified=None)),
        ),
    ):
        collect_single_archive_snapshot(archive_id)

    rows = (
        sync_db_session.query(ArchiveSnapshotModel)
        .filter(ArchiveSnapshotModel.archive_id == archive_id)
        .all()
    )
    assert len(rows) == 2, (
        f"expected 2 rows (yesterday + today), got {len(rows)} — the day guard "
        "wrongly blocked a new calendar day"
    )
