"""
Database models package.
Import all models here for easy access from other modules.
"""

from app.models.archive_snapshot import ArchiveSnapshotModel
from app.models.base import Base, TimestampMixin
from app.models.dataset import DatasetModel, UsefulLinkModel, XmlArchiveModel
from app.models.provider import DataProviderModel
from app.models.user import UserModel
from app.models.validation import ValidationJobModel

# Export all models
__all__ = [
    "Base",
    "TimestampMixin",
    "UserModel",
    "DataProviderModel",
    "DatasetModel",
    "XmlArchiveModel",
    "UsefulLinkModel",
    "ValidationJobModel",
    "ArchiveSnapshotModel",
]
