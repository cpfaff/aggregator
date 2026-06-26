"""Add functional unique index for one snapshot per archive per day

Makes snapshot insertion idempotent under acks_late redelivery (RH-06 /
REQ-CEL-3 / F-CELERY-03 / F-SNAP-03). A redelivered
``collect_single_archive_snapshot`` (crash / lost ack / visibility-timeout)
must not double-insert a snapshot for the same archive on the same calendar day.

A plain column-tuple ``UniqueConstraint("archive_id", "recorded_at")`` cannot
express this — ``recorded_at`` differs by milliseconds and never collides — so we
add a functional UNIQUE index on ``(archive_id, date(recorded_at))``.

The upgrade MUST de-duplicate existing rows (keep the latest per archive/day)
BEFORE creating the unique index, or the index build aborts on any pre-existing
duplicate.

Revision ID: c4f1a2b9d7e3
Revises: 9f2c7a4e1b6d
Create Date: 2026-06-26 00:00:00.000000

"""

from collections.abc import Sequence

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "c4f1a2b9d7e3"
down_revision: str | None = "9f2c7a4e1b6d"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # De-duplicate existing rows first: keep the latest snapshot per
    # (archive_id, calendar day), delete the rest. Without this the unique index
    # build below aborts if any archive already has two snapshots on one day.
    # "Latest" = highest recorded_at, tie-broken by highest id.
    op.execute(
        """
        DELETE FROM archive_snapshots a
        USING archive_snapshots b
        WHERE a.archive_id = b.archive_id
          AND date(a.recorded_at) = date(b.recorded_at)
          AND (
                a.recorded_at < b.recorded_at
                OR (a.recorded_at = b.recorded_at AND a.id < b.id)
          )
        """
    )

    # Functional UNIQUE index: at most one snapshot per archive per calendar day.
    op.execute(
        "CREATE UNIQUE INDEX uq_snapshot_archive_day "
        "ON archive_snapshots (archive_id, date(recorded_at))"
    )


def downgrade() -> None:
    op.drop_index("uq_snapshot_archive_day", table_name="archive_snapshots")
