"""
User database model.
"""

from sqlalchemy import JSON, Boolean, Column, DateTime, Integer, String

from app.models.base import Base


class UserModel(Base):
    """User model representing application users with authentication and authorization data."""

    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    provider_roles = Column(JSON, default={})
    is_global_admin = Column(Boolean, default=False)
    last_login = Column(DateTime(timezone=True), nullable=True)
