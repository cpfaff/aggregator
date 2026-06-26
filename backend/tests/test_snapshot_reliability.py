"""REQ-SH-REL: the nightly-collection reliability guarantees, locked as named tests.

The append-only collection core is the subsystem's proven strength (discovery §1).
This file pins the guarantees that the harmonization must not regress, naming each
to its requirement. Three of the six already have dedicated tests at their seam,
referenced here; this file adds the three that lacked a named test:

* REQ-SH-REL-1 (same-day -> at most one) — tests/test_snapshot_idempotency.py
* REQ-SH-REL-2 (byte-budget abort)       — tests/test_snapshot_archive_bound.py
* REQ-SH-REL-3 (fail-fast partial ZIP)   — tests/test_snapshot_zip_partial.py
* REQ-SH-REL-4 (concurrent insert -> already_recorded)  — here
* REQ-SH-REL-5 (batch remainder persists)               — here
* REQ-SH-REL-6 (deterministic same-day order)           — here

REL-4/5 drive the task body against the Postgres testcontainer with ``SessionLocal``
patched to a per-call session factory (mirroring how Celery opens a fresh session),
and simulate a *concurrent* worker by committing the conflicting row through a second
session between the task's app-level check and its own insert — the only way to
reach the DB unique-index fallback, since the app-level check otherwise short-circuits.
"""

from datetime import date

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models.archive_snapshot import ArchiveSnapshotModel
from app.models.dataset import XmlArchiveModel
from app.tasks import snapshot_tasks
from app.tasks.snapshot_tasks import (
    ArchiveParseResult,
    HttpMetadata,
    collect_archive_snapshots,
    collect_single_archive_snapshot,
)


def _seed_archive(session, url="http://example.com/a.xml") -> int:
    archive = XmlArchiveModel(url=url, isLatest=True)
    session.add(archive)
    session.commit()
    return archive.id


def _session_factory(engine):
    def make():
        return Session(engine, expire_on_commit=False)

    return make


def _today_count(session, archive_id) -> int:
    return (
        session.query(func.count(ArchiveSnapshotModel.id))
        .filter(
            ArchiveSnapshotModel.archive_id == archive_id,
            func.date(ArchiveSnapshotModel.recorded_at) == date.today(),
        )
        .scalar()
    )


# ---------------------------------------------------------------------------
# REQ-SH-REL-4 — concurrent same archive/day insert -> already_recorded
# ---------------------------------------------------------------------------


def test_concurrent_same_day_insert_treated_as_already_recorded(sync_engine, sync_db_session):
    """REQ-SH-REL-4: when a concurrent worker wins the archive/day race after this
    task's app-level check passed but before its insert commits, the unique-index
    IntegrityError is treated as already-recorded (no error, no duplicate)."""
    archive_id = _seed_archive(sync_db_session)

    def _parse_then_race(url):
        # A concurrent worker inserts today's snapshot for this archive *after* the
        # task's app-level existence check has already passed (no row then).
        other = Session(sync_engine, expire_on_commit=False)
        try:
            other.add(ArchiveSnapshotModel(archive_id=archive_id, unit_count=7))
            other.commit()
        finally:
            other.close()
        return ArchiveParseResult(
            unit_count=5, http_metadata=HttpMetadata(etag=None, last_modified=None)
        )

    from unittest.mock import patch

    with (
        patch.object(snapshot_tasks, "SessionLocal", _session_factory(sync_engine)),
        patch.object(snapshot_tasks, "parse_archive_xml", side_effect=_parse_then_race),
        patch.object(
            snapshot_tasks,
            "check_archive_changed",
            return_value=(True, HttpMetadata(etag=None, last_modified=None)),
        ),
    ):
        result = collect_single_archive_snapshot(archive_id)

    assert result["status"] == "already_recorded"
    rows = (
        sync_db_session.query(ArchiveSnapshotModel)
        .filter(ArchiveSnapshotModel.archive_id == archive_id)
        .all()
    )
    assert len(rows) == 1, f"unique-index race left {len(rows)} rows, expected exactly 1"


# ---------------------------------------------------------------------------
# REQ-SH-REL-5 — a rejected duplicate in a batch does not lose the rest
# ---------------------------------------------------------------------------


def test_batch_duplicate_conflict_persists_remaining_snapshots(sync_engine, sync_db_session):
    """REQ-SH-REL-5: if one archive's snapshot conflicts on the batch commit, the
    per-row fallback still persists every other (non-conflicting) archive's snapshot."""
    from datetime import timedelta

    from app.core.utils import utc_now

    archive_a = XmlArchiveModel(url="http://example.com/a.xml", isLatest=True)
    archive_b = XmlArchiveModel(url="http://example.com/b.xml", isLatest=True)
    sync_db_session.add_all([archive_a, archive_b])
    sync_db_session.commit()
    a_id, b_id = archive_a.id, archive_b.id

    # Both archives have a snapshot from yesterday, so the unchanged path has a
    # previous unit_count to reuse (prev_unit_count is not None) and neither is
    # excluded as "already done today".
    yesterday = utc_now() - timedelta(days=1)
    sync_db_session.add_all(
        [
            ArchiveSnapshotModel(archive_id=a_id, unit_count=10, recorded_at=yesterday),
            ArchiveSnapshotModel(archive_id=b_id, unit_count=20, recorded_at=yesterday),
        ]
    )
    sync_db_session.commit()

    state = {"raced": False}

    def _unchanged_but_race(url, previous_etag=None, previous_last_modified=None):
        # On the first archive checked, a concurrent worker commits today's row for
        # archive A, so the batch commit will conflict on A and fall back to per-row.
        if not state["raced"]:
            state["raced"] = True
            other = Session(sync_engine, expire_on_commit=False)
            try:
                other.add(ArchiveSnapshotModel(archive_id=a_id, unit_count=99))
                other.commit()
            finally:
                other.close()
        return (False, HttpMetadata(etag=previous_etag, last_modified=previous_last_modified))

    from unittest.mock import patch

    with (
        patch.object(snapshot_tasks, "SessionLocal", _session_factory(sync_engine)),
        patch.object(snapshot_tasks, "check_archive_changed", side_effect=_unchanged_but_race),
    ):
        collect_archive_snapshots()

    # Archive B (non-conflicting) still got today's snapshot via the per-row retry.
    assert _today_count(sync_db_session, b_id) == 1, "remaining batch snapshot was lost"
    # Archive A has exactly the one concurrent row for today (no duplicate).
    assert _today_count(sync_db_session, a_id) == 1


# ---------------------------------------------------------------------------
# REQ-SH-REL-6 — deterministic same-day existence-check ordering
# ---------------------------------------------------------------------------


def test_same_day_check_orders_by_recorded_at_then_id_desc(sync_db_session):
    """REQ-SH-REL-6: the same-day existence check selects its row ordered by
    recorded_at descending, then id descending (F-M: align with the change-detection
    query and the dedup migration's keep-rule)."""
    query = snapshot_tasks._today_snapshot_query(
        sync_db_session, archive_id=1, today=date(2024, 1, 1)
    )
    sql = str(query.statement.compile(compile_kwargs={"literal_binds": True})).lower()

    order_clause = sql[sql.index("order by") :]
    assert "recorded_at desc" in order_clause
    assert "id desc" in order_clause
    assert order_clause.index("recorded_at desc") < order_clause.index("id desc"), (
        "same-day check must order by recorded_at DESC before id DESC"
    )
