"""
Common schemas used across the application.
"""

from typing import Generic, TypeVar

from pydantic import BaseModel

T = TypeVar("T")


class PaginatedResponse(BaseModel, Generic[T]):
    """Generic paginated response model"""

    items: list[T]
    total: int
    page: int
    size: int

    @classmethod
    def create(cls, items: list[T], total: int, page: int, size: int):
        """Factory method to create a paginated response"""
        return cls(items=items, total=total, page=page, size=size)


class TokenResponse(BaseModel):
    """Token response model for authentication endpoints"""

    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int


# Import other schema types to define specialized paginated responses
# These are defined here to avoid circular imports
from app.schemas.dataset import Dataset  # noqa: E402
from app.schemas.provider import DataProvider  # noqa: E402
from app.schemas.user import User  # noqa: E402

# Create paginated response models for each entity
PaginatedProviders = PaginatedResponse[DataProvider]
PaginatedDatasets = PaginatedResponse[Dataset]
PaginatedUsers = PaginatedResponse[User]
