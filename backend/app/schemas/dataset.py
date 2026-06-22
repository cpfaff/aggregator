"""
Dataset-related Pydantic schemas for validation and serialization.
"""

from datetime import datetime
from typing import Any

from pydantic import AnyUrl, BaseModel, ConfigDict, field_validator


class XmlArchive(BaseModel):
    """Schema for XML archive information."""

    id: int | None = None
    url: AnyUrl
    isLatest: bool

    model_config = ConfigDict(
        from_attributes=True, json_encoders={AnyUrl: str}, populate_by_name=True
    )


class UsefulLink(BaseModel):
    """Schema for useful link information."""

    id: int | None = None
    title: str
    url: AnyUrl
    isLatest: bool

    @field_validator("title")
    @classmethod
    def trim_whitespace(cls, v: str) -> str:
        return v.strip()

    model_config = ConfigDict(
        from_attributes=True, json_encoders={AnyUrl: str}, populate_by_name=True
    )


class Dataset(BaseModel):
    """Schema for dataset information."""

    id: int | None = None
    source: str
    title: str
    landingPageUrl: AnyUrl | None = None
    xmlArchives: list[XmlArchive] = []
    usefulLinks: list[UsefulLink] = []
    isHarvestReady: bool = False
    created_at: datetime | None = None
    updated_at: datetime | None = None

    @field_validator("source", "title")
    @classmethod
    def trim_whitespace(cls, v: str) -> str:
        return v.strip()

    @field_validator("landingPageUrl", mode="before")
    @classmethod
    def empty_str_to_none(cls, v: Any) -> Any:
        if v == "":
            return None
        return v

    def model_dump(self, *args, **kwargs):
        data = super().model_dump(*args, **kwargs)
        if not data.get("xmlArchives"):
            data.pop("xmlArchives", None)
        if not data.get("usefulLinks"):
            data.pop("usefulLinks", None)
        return data

    model_config = ConfigDict(
        from_attributes=True, json_encoders={AnyUrl: str}, populate_by_name=True
    )


# Legacy API compatibility schemas
class LegacyXmlArchive(BaseModel):
    """Legacy schema for XML archive information."""

    archive_id: int
    xml_archive: AnyUrl
    latest: bool

    model_config = ConfigDict(from_attributes=True, json_encoders={AnyUrl: str})


class LegacyUsefulLink(BaseModel):
    """Legacy schema for useful link information."""

    link_id: int
    title: str
    url: AnyUrl
    is_latest: bool

    @field_validator("title")
    @classmethod
    def trim_whitespace(cls, v: str) -> str:
        return v.strip()

    model_config = ConfigDict(from_attributes=True, json_encoders={AnyUrl: str})


class LegacyDataset(BaseModel):
    """Legacy schema for dataset information."""

    dataset_id: int
    datasource: str
    dataset: str
    custom_landingpage: AnyUrl | None
    provider_id: int
    xml_archives: list[LegacyXmlArchive]
    useful_links: list[LegacyUsefulLink]
    provider_datacenter: str
    provider_shortname: str
    provider_name: str
    provider_url: AnyUrl | None
    biocase_url: AnyUrl | None
    is_data_center: bool | None = None

    @field_validator(
        "datasource",
        "dataset",
        "provider_datacenter",
        "provider_shortname",
        "provider_name",
    )
    @classmethod
    def trim_whitespace(cls, v: str) -> str:
        return v.strip()

    model_config = ConfigDict(from_attributes=True, json_encoders={AnyUrl: str})
