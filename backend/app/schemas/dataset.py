"""
Dataset-related Pydantic schemas for validation and serialization.
"""
from datetime import datetime
from typing import Any, List, Optional

from pydantic import BaseModel, AnyUrl, field_validator, ConfigDict


class XmlArchive(BaseModel):
    """Schema for XML archive information."""
    id: Optional[int] = None
    url: AnyUrl
    isLatest: bool

    model_config = ConfigDict(
        from_attributes=True,
        json_encoders={AnyUrl: str},
        populate_by_name=True
    )


class UsefulLink(BaseModel):
    """Schema for useful link information."""
    id: Optional[int] = None
    title: str
    url: AnyUrl
    isLatest: bool

    @field_validator("title")
    @classmethod
    def trim_whitespace(cls, v: str) -> str:
        return v.strip()

    model_config = ConfigDict(
        from_attributes=True,
        json_encoders={AnyUrl: str},
        populate_by_name=True
    )


class Dataset(BaseModel):
    """Schema for dataset information."""
    id: Optional[int] = None
    source: str
    title: str
    landingPageUrl: Optional[AnyUrl] = None
    xmlArchives: List[XmlArchive] = []
    usefulLinks: List[UsefulLink] = []
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

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
        from_attributes=True,
        json_encoders={AnyUrl: str},
        populate_by_name=True
    )


# Legacy API compatibility schemas
class LegacyXmlArchive(BaseModel):
    """Legacy schema for XML archive information."""
    archive_id: int
    xml_archive: AnyUrl
    latest: bool

    model_config = ConfigDict(
        from_attributes=True,
        json_encoders={AnyUrl: str}
    )


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

    model_config = ConfigDict(
        from_attributes=True,
        json_encoders={AnyUrl: str}
    )


class LegacyDataset(BaseModel):
    """Legacy schema for dataset information."""
    dataset_id: int
    datasource: str
    dataset: str
    custom_landingpage: Optional[AnyUrl]
    provider_id: int
    xml_archives: List[LegacyXmlArchive]
    useful_links: List[LegacyUsefulLink]
    provider_datacenter: str
    provider_shortname: str
    provider_name: str
    provider_url: Optional[AnyUrl]
    biocase_url: Optional[AnyUrl]
    is_data_center: Optional[bool] = None

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

    model_config = ConfigDict(
        from_attributes=True,
        json_encoders={AnyUrl: str}
    )
