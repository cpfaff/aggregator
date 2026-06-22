"""
Dataset models including XML archives and useful links.
"""

from sqlalchemy import Boolean, Column, ForeignKey, Index, Integer, String
from sqlalchemy.orm import relationship

from app.models.base import Base, TimestampMixin


class DatasetModel(Base, TimestampMixin):
    """Dataset model representing datasets provided by data providers."""

    __tablename__ = "datasets"

    id = Column(Integer, primary_key=True, index=True)
    provider_id = Column(Integer, ForeignKey("data_providers.id"))
    source = Column(String)
    title = Column(String)
    landingPageUrl = Column(String, nullable=True)
    isHarvestReady = Column(Boolean, nullable=False, default=False)

    # Relationships
    provider = relationship("DataProviderModel", back_populates="datasets")
    xmlArchives = relationship(
        "XmlArchiveModel", back_populates="dataset", cascade="all, delete-orphan"
    )
    usefulLinks = relationship(
        "UsefulLinkModel", back_populates="dataset", cascade="all, delete-orphan"
    )

    __table_args__ = (Index("idx_dataset_provider", "provider_id"),)


class XmlArchiveModel(Base):
    """XML Archive model representing XML archive files for datasets."""

    __tablename__ = "xml_archives"

    id = Column(Integer, primary_key=True, index=True)
    dataset_id = Column(Integer, ForeignKey("datasets.id"))
    url = Column(String)
    isLatest = Column(Boolean)

    # Relationships
    dataset = relationship("DatasetModel", back_populates="xmlArchives")
    validation_jobs = relationship(
        "ValidationJobModel", back_populates="archive", cascade="all, delete-orphan"
    )

    __table_args__ = (Index("idx_xml_archive_dataset", "dataset_id"),)


class UsefulLinkModel(Base):
    """Useful Link model representing useful links for datasets."""

    __tablename__ = "useful_links"

    id = Column(Integer, primary_key=True, index=True)
    dataset_id = Column(Integer, ForeignKey("datasets.id"))
    title = Column(String)
    url = Column(String)
    isLatest = Column(Boolean)

    # Relationships
    dataset = relationship("DatasetModel", back_populates="usefulLinks")

    __table_args__ = (Index("idx_useful_link_dataset", "dataset_id"),)
