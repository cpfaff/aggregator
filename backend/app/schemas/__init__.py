"""
Pydantic schemas for request/response validation.
Import all schemas here for easy access from other modules.
"""

from app.schemas.common import (
    PaginatedDatasets,
    PaginatedProviders,
    PaginatedResponse,
    PaginatedUsers,
    TokenResponse,
)
from app.schemas.dataset import (
    Dataset,
    LegacyDataset,
    LegacyUsefulLink,
    LegacyXmlArchive,
    UsefulLink,
    XmlArchive,
)
from app.schemas.provider import DataProvider, ProviderAssociation
from app.schemas.statistics import (
    DatasetStats,
    GrowthMetrics,
    OverviewStats,
    ProviderStats,
    QualityMetrics,
    TimeSeriesPoint,
    TimeSeriesResponse,
)
from app.schemas.user import User, UserCreate, UserPermissions, UserUpdate

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
    "GrowthMetrics",
]
