"""add last_login timestamp to users table

Revision ID: 679a3c003046
Revises: d3a5a08b3c0a
Create Date: 2026-01-14 13:41:58.248457

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "679a3c003046"
down_revision: str | None = "d3a5a08b3c0a"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Add last_login timestamp column to users table."""
    op.add_column("users", sa.Column("last_login", sa.DateTime(timezone=True), nullable=True))


def downgrade() -> None:
    """Remove last_login column from users table."""
    op.drop_column("users", "last_login")
