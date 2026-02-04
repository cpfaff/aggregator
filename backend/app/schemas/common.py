"""
Common schemas used across the application.
"""

from typing import Generic, List, TypeVar

from pydantic import BaseModel
from pydantic.generics import GenericModel

T = TypeVar("T")


class PaginatedResponse(GenericModel, Generic[T]):
    """Generic paginated response model"""

    items: List[T]
    total: int
    page: int
    size: int

    @classmethod
    def create(cls, items: List[T], total: int, page: int, size: int):
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
from app.schemas.dataset import Dataset
from app.schemas.provider import DataProvider
from app.schemas.user import User

# Create paginated response models for each entity
PaginatedProviders = PaginatedResponse[DataProvider]
PaginatedDatasets = PaginatedResponse[Dataset]
PaginatedUsers = PaginatedResponse[User]
