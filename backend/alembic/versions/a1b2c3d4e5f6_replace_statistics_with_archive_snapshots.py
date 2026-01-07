"""Replace statistics table with archive_snapshots

This migration implements the statistics simplification:
- Drops the complex generic 'statistics' table
- Creates a new domain-specific 'archive_snapshots' table
- Uses true append-only storage pattern with proper FK integrity

Revision ID: a1b2c3d4e5f6
Revises: 6af81fd1122b
Create Date: 2026-01-06

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a1b2c3d4e5f6'
down_revision: Union[str, None] = '6af81fd1122b'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Drop the old statistics table and all its indexes/constraints
    op.drop_index('idx_statistics_date', table_name='statistics')
    op.drop_index('idx_statistics_entity', table_name='statistics')
    op.drop_index('idx_statistics_lookup', table_name='statistics')
    op.drop_index('idx_statistics_metric', table_name='statistics')
    op.drop_index(op.f('ix_statistics_id'), table_name='statistics')
    op.drop_table('statistics')

    # Create the new archive_snapshots table
    op.create_table(
        'archive_snapshots',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('archive_id', sa.Integer(), nullable=False),
        sa.Column('recorded_at', sa.DateTime(), nullable=False),
        sa.Column('unit_count', sa.Integer(), nullable=False, server_default='0'),
        sa.ForeignKeyConstraint(
            ['archive_id'],
            ['xml_archives.id'],
            ondelete='CASCADE'
        ),
        sa.PrimaryKeyConstraint('id')
    )

    # Create indexes for efficient queries
    op.create_index(
        op.f('ix_archive_snapshots_id'),
        'archive_snapshots',
        ['id'],
        unique=False
    )
    op.create_index(
        'idx_snapshot_archive_id',
        'archive_snapshots',
        ['archive_id'],
        unique=False
    )
    op.create_index(
        'idx_snapshot_recorded_at',
        'archive_snapshots',
        ['recorded_at'],
        unique=False
    )
    op.create_index(
        'idx_snapshot_archive_recorded',
        'archive_snapshots',
        ['archive_id', 'recorded_at'],
        unique=False
    )


def downgrade() -> None:
    # Drop the archive_snapshots table
    op.drop_index('idx_snapshot_archive_recorded', table_name='archive_snapshots')
    op.drop_index('idx_snapshot_recorded_at', table_name='archive_snapshots')
    op.drop_index('idx_snapshot_archive_id', table_name='archive_snapshots')
    op.drop_index(op.f('ix_archive_snapshots_id'), table_name='archive_snapshots')
    op.drop_table('archive_snapshots')

    # Recreate the old statistics table (for rollback capability)
    from sqlalchemy.dialects import postgresql

    op.create_table(
        'statistics',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('metric_type', sa.String(), nullable=False),
        sa.Column('entity_type', sa.String(), nullable=False),
        sa.Column('entity_id', sa.Integer(), nullable=True),
        sa.Column('period', sa.String(), nullable=False),
        sa.Column('date', sa.Date(), nullable=False),
        sa.Column('value', sa.Float(), nullable=False),
        sa.Column('extra_data', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.CheckConstraint(
            "(entity_type = 'system' AND entity_id IS NULL) OR "
            "(entity_type != 'system' AND entity_id IS NOT NULL)",
            name='entity_id_consistency'
        ),
        sa.CheckConstraint(
            "entity_type IN ('system', 'provider', 'dataset', 'datacenter')",
            name='valid_entity_type'
        ),
        sa.CheckConstraint(
            "metric_type IN ('dataset_count', 'dataset_registration_rate', "
            "'dataset_modification_rate', 'dataset_unit_count', 'provider_count', "
            "'provider_dataset_count', 'provider_activity_score', 'provider_biological_units', "
            "'validation_success_rate', 'validation_error_rate', 'validation_processing_time', "
            "'validation_job_count', 'abcd_compliance_rate', 'xml_archive_count', "
            "'system_storage_size', 'system_processing_load', 'system_api_response_time')",
            name='valid_metric_type'
        ),
        sa.CheckConstraint(
            "period IN ('daily', 'weekly', 'monthly', 'quarterly', 'yearly')",
            name='valid_period'
        ),
        sa.CheckConstraint('value >= 0', name='non_negative_value'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_statistics_date', 'statistics', ['date'], unique=False)
    op.create_index(
        'idx_statistics_entity',
        'statistics',
        ['entity_type', 'entity_id', 'date'],
        unique=False
    )
    op.create_index(
        'idx_statistics_lookup',
        'statistics',
        ['metric_type', 'entity_type', 'entity_id', 'period'],
        unique=False
    )
    op.create_index(
        'idx_statistics_metric',
        'statistics',
        ['metric_type', 'period', 'date'],
        unique=False
    )
    op.create_index(op.f('ix_statistics_id'), 'statistics', ['id'], unique=False)
