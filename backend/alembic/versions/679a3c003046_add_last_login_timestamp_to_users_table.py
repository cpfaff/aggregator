"""add last_login timestamp to users table

Revision ID: 679a3c003046
Revises: d3a5a08b3c0a
Create Date: 2026-01-14 13:41:58.248457

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '679a3c003046'
down_revision: Union[str, None] = 'd3a5a08b3c0a'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add last_login timestamp column to users table."""
    op.add_column('users', sa.Column('last_login', sa.DateTime(timezone=True), nullable=True))


def downgrade() -> None:
    """Remove last_login column from users table."""
    op.drop_column('users', 'last_login')
