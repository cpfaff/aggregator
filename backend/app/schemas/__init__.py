"""
Pydantic schemas for request/response validation.
Import all schemas here for easy access from other modules.
"""

from app.schemas.user import (
    User, 
    UserCreate, 
    UserUpdate, 
    UserPermissions
)
from app.schemas.provider import (
    DataProvider,
    ProviderAssociation
)
from app.schemas.dataset import (
    Dataset,
    XmlArchive,
    UsefulLink,
    LegacyDataset,
    LegacyXmlArchive,
    LegacyUsefulLink
)
from app.schemas.common import (
    PaginatedResponse,
    TokenResponse,
    PaginatedProviders,
    PaginatedDatasets,
    PaginatedUsers
)

__all__ = [
    "User",
    "UserCreate",
    "UserUpdate", 
    "UserPermissions",
    "DataProvider",
    "ProviderAssociation",
    "Dataset",
    "XmlArchive",
    "UsefulLink",
    "LegacyDataset",
    "LegacyXmlArchive",
    "LegacyUsefulLink",
    "PaginatedResponse",
    "TokenResponse",
    "PaginatedProviders",
    "PaginatedDatasets",
    "PaginatedUsers"
]
