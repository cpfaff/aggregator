"""
Base model and shared mixins for SQLAlchemy ORM models.
"""

from sqlalchemy import Column, DateTime
from sqlalchemy.orm import declarative_base

# Canonical naive-UTC "now" (REQ-SH-NOW). Imported from the dependency-free leaf
# app.core.timeutils — NOT app.core.utils — so this module (imported by every
# model) does not pull in app.core.utils -> app.models.dataset -> app.models.base
# (an import cycle). Retires the byte-identical local _utc_now duplicate.
from app.core.timeutils import utc_now

# Create base class for all models
Base = declarative_base()


class TimestampMixin:
    """Mixin class that adds created_at and updated_at timestamp fields to models."""

    created_at = Column(DateTime, default=utc_now, nullable=False)
    updated_at = Column(DateTime, default=utc_now, onupdate=utc_now, nullable=False)
