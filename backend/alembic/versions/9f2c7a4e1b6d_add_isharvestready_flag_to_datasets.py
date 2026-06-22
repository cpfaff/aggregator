"""Add isHarvestReady flag to datasets

Gates whether a registered dataset is exposed to the harvester feed. Existing
rows are backfilled to True (stay harvested); new rows default to False (staged)
via the application layer, so the one-time server default is dropped after the
backfill.

Revision ID: 9f2c7a4e1b6d
Revises: 679a3c003046
Create Date: 2026-06-22 00:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "9f2c7a4e1b6d"
down_revision: str | None = "679a3c003046"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Add NOT NULL with a one-time server default of True so existing rows are
    # backfilled to harvest-ready in place (nothing currently harvested drops out).
    op.add_column(
        "datasets",
        sa.Column("isHarvestReady", sa.Boolean(), nullable=False, server_default=sa.true()),
    )
    # Drop the server default so new rows take the application-layer default
    # (False / staged), not a database-level True.
    op.alter_column("datasets", "isHarvestReady", server_default=None)


def downgrade() -> None:
    op.drop_column("datasets", "isHarvestReady")
