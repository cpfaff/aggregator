"""
Base model and shared mixins for SQLAlchemy ORM models.
"""

from datetime import UTC, datetime

from sqlalchemy import Column, DateTime
from sqlalchemy.orm import declarative_base

# Create base class for all models
Base = declarative_base()


def _utc_now() -> datetime:
    """Return current UTC time as timezone-naive datetime for DB compatibility."""
    return datetime.now(UTC).replace(tzinfo=None)


class TimestampMixin:
    """Mixin class that adds created_at and updated_at timestamp fields to models."""

    created_at = Column(DateTime, default=_utc_now, nullable=False)
    updated_at = Column(DateTime, default=_utc_now, onupdate=_utc_now, nullable=False)
