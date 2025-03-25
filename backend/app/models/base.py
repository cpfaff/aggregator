"""
Base model and shared mixins for SQLAlchemy ORM models.
"""
from datetime import datetime
from sqlalchemy import Column, DateTime
from sqlalchemy.orm import declarative_base

# Create base class for all models
Base = declarative_base()


class TimestampMixin:
    """Mixin class that adds created_at and updated_at timestamp fields to models."""
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
