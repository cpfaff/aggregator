"""Add HTTP change detection fields to archive_snapshots

This migration adds fields to store HTTP ETag and Last-Modified headers
from archive downloads, enabling change detection to skip unchanged archives.

Revision ID: d3a5a08b3c0a
Revises: a1b2c3d4e5f6
Create Date: 2026-01-12

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'd3a5a08b3c0a'
down_revision: Union[str, None] = 'a1b2c3d4e5f6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add columns for HTTP change detection
    # These store the ETag and Last-Modified headers from the last download
    # to enable skipping unchanged archives on subsequent runs
    op.add_column(
        'archive_snapshots',
        sa.Column('http_etag', sa.String(), nullable=True)
    )
    op.add_column(
        'archive_snapshots',
        sa.Column('http_last_modified', sa.String(), nullable=True)
    )


def downgrade() -> None:
    op.drop_column('archive_snapshots', 'http_last_modified')
    op.drop_column('archive_snapshots', 'http_etag')
