"""
User-related Pydantic schemas for validation and serialization.
"""

from datetime import datetime
from typing import Dict, Optional

from pydantic import BaseModel, ConfigDict, field_validator

from app.core.config import settings


class User(BaseModel):
    """Schema for returning user information."""

    username: str
    provider_roles: Dict[str, str]
    is_global_admin: bool = False
    last_login: Optional[datetime] = None

    @field_validator("username")
    @classmethod
    def trim_whitespace(cls, v: str) -> str:
        return v.strip()

    model_config = ConfigDict(from_attributes=True)


class UserCreate(BaseModel):
    """Schema for creating a new user."""

    username: str
    password: str
    provider_roles: Optional[Dict[str, str]] = {}
    is_global_admin: bool = False

    @field_validator("username", "password")
    @classmethod
    def trim_whitespace(cls, v: str) -> str:
        return v.strip()

    @field_validator("password")
    @classmethod
    def validate_password_strength(cls, v: str) -> str:
        min_length = settings.MIN_PASSWORD_LENGTH
        if len(v) < min_length:
            raise ValueError(f"Password must be at least {min_length} characters long")
        return v

    model_config = ConfigDict(from_attributes=True)


class UserUpdate(BaseModel):
    """Schema for updating an existing user."""

    password: Optional[str] = None
    provider_roles: Optional[Dict[str, str]] = None
    is_global_admin: Optional[bool] = None

    @field_validator("password")
    @classmethod
    def trim_whitespace(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return v
        return v.strip()

    @field_validator("password")
    @classmethod
    def validate_password_strength(cls, v: Optional[str]) -> Optional[str]:
        if v is not None:
            min_length = settings.MIN_PASSWORD_LENGTH
            if len(v) < min_length:
                raise ValueError(f"Password must be at least {min_length} characters long")
        return v

    model_config = ConfigDict(from_attributes=True)


class UserPermissions(BaseModel):
    """Schema for retrieving user permissions."""

    username: str
    is_global_admin: bool
    provider_roles: Dict[str, str]
    last_login: Optional[datetime] = None

    @field_validator("username")
    @classmethod
    def trim_whitespace(cls, v: str) -> str:
        return v.strip()

    model_config = ConfigDict(from_attributes=True)
