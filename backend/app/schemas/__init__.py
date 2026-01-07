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
from app.schemas.statistics import (
    TimeSeriesPoint,
    TimeSeriesResponse,
    OverviewStats,
    ProviderStats,
    DatasetStats,
    QualityMetrics,
    GrowthMetrics
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
    "PaginatedUsers",
    "TimeSeriesPoint",
    "TimeSeriesResponse",
    "OverviewStats",
    "ProviderStats",
    "DatasetStats",
    "QualityMetrics",
    "GrowthMetrics"
]
