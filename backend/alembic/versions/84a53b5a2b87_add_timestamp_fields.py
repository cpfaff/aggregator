"""Add timestamp fields to providers and datasets

Revision ID: 84a53b5a2b87
Revises: ee08ccb0785a
Create Date: 2025-03-18 06:52:37.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from datetime import datetime

# revision identifiers, used by Alembic.
revision: str = '84a53b5a2b87'
down_revision: Union[str, None] = 'ee08ccb0785a'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add created_at and updated_at columns to data_providers table
    op.add_column('data_providers', sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()))
    op.add_column('data_providers', sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.func.now()))
    
    # Add created_at and updated_at columns to datasets table
    op.add_column('datasets', sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()))
    op.add_column('datasets', sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.func.now()))


def downgrade() -> None:
    # Drop columns from datasets table
    op.drop_column('datasets', 'updated_at')
    op.drop_column('datasets', 'created_at')
    
    # Drop columns from data_providers table
    op.drop_column('data_providers', 'updated_at')
    op.drop_column('data_providers', 'created_at')
