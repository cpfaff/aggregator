"""
Data Provider model for storing information about data providers.
"""
from sqlalchemy import Column, Integer, String, Boolean
from sqlalchemy.orm import relationship

from app.models.base import Base, TimestampMixin


class DataProviderModel(Base, TimestampMixin):
    """Data provider model representing data providers in the system."""
    __tablename__ = "data_providers"
    
    id = Column(Integer, primary_key=True, index=True)
    datacenter = Column(String)
    shortName = Column(String)
    name = Column(String)
    url = Column(String, nullable=True)
    biocaseUrl = Column(String, nullable=True)
    isDataCenter = Column(Boolean, nullable=True, default=False)
    
    # Relationships
    datasets = relationship(
        "DatasetModel", back_populates="provider", cascade="all, delete-orphan"
    )
