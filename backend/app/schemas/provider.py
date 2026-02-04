"""
Provider-related Pydantic schemas for validation and serialization.
"""

from datetime import datetime

from pydantic import AnyUrl, BaseModel, ConfigDict, field_validator

from app.schemas.dataset import Dataset


class DataProvider(BaseModel):
    """Schema for data provider information."""

    id: int | None = None
    datacenter: str
    shortName: str
    name: str
    url: AnyUrl | None = None
    biocaseUrl: AnyUrl | None = None
    isDataCenter: bool | None = None
    datasets: list[Dataset] = []
    created_at: datetime | None = None
    updated_at: datetime | None = None

    @field_validator("datacenter", "shortName", "name")
    @classmethod
    def trim_whitespace(cls, v: str) -> str:
        return v.strip()

    model_config = ConfigDict(
        from_attributes=True, json_encoders={AnyUrl: str}, populate_by_name=True
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
