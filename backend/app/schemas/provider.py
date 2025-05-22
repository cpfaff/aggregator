"""
Provider-related Pydantic schemas for validation and serialization.
"""
from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, AnyUrl, field_validator, ConfigDict

from app.schemas.dataset import Dataset


class DataProvider(BaseModel):
    """Schema for data provider information."""
    id: Optional[int] = None
    datacenter: str
    shortName: str
    name: str
    url: Optional[AnyUrl] = None
    biocaseUrl: Optional[AnyUrl] = None
    isDataCenter: Optional[bool] = None
    datasets: List[Dataset] = []
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    @field_validator("datacenter", "shortName", "name")
    @classmethod
    def trim_whitespace(cls, v: str) -> str:
        return v.strip()

    model_config = ConfigDict(
        from_attributes=True,
        json_encoders={AnyUrl: str},
        populate_by_name=True
    )


class ProviderAssociation(BaseModel):
    """Schema for provider role associations."""
    provider_id: int
    role: str  # Expected values: "admin" or "curator"

    @field_validator("role")
    @classmethod
    def trim_whitespace(cls, v: str) -> str:
        return v.strip()

    model_config = ConfigDict(from_attributes=True)
