"""Pagination schemas for cursor-based pagination."""

from typing import Generic, TypeVar

from pydantic import BaseModel, ConfigDict, Field, field_validator

T = TypeVar("T")


class PaginationParams(BaseModel):
    """Query parameters for cursor-based pagination."""

    limit: int = Field(
        default=20,
        ge=1,
        description="Maximum number of items to return (1-100)",
    )
    after: str | None = Field(
        default=None,
        description="Cursor for fetching items after this position",
    )
    before: str | None = Field(
        default=None,
        description="Cursor for fetching items before this position",
    )

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "limit": 20,
                "after": "aW1kOjEwMA==",
                "before": None,
            }
        }
    )

    @field_validator("limit", mode="after")
    @classmethod
    def clamp_max_limit(cls, v: int) -> int:
        """Clamp limit to maximum allowed value (ge/le already validated min)."""
        return min(v, 100)


class PaginationMeta(BaseModel):
    """Pagination metadata included in paginated responses."""

    limit: int = Field(description="Number of items requested")
    has_next: bool = Field(description="Whether more items exist after this page")
    has_previous: bool = Field(description="Whether items exist before this page")
    next_cursor: str | None = Field(
        default=None,
        description="Cursor to fetch next page (null if no more pages)",
    )
    previous_cursor: str | None = Field(
        default=None,
        description="Cursor to fetch previous page (null if at start)",
    )
    total_count: int | None = Field(
        default=None,
        description="Total number of items (may be null for performance)",
    )

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "limit": 20,
                "has_next": True,
                "has_previous": False,
                "next_cursor": "aW1kOjIw",
                "previous_cursor": None,
                "total_count": 150,
            }
        }
    )


class PaginatedResponse(BaseModel, Generic[T]):
    """Generic wrapper for paginated API responses."""

    data: list[T] = Field(description="List of items for this page")
    pagination: PaginationMeta = Field(description="Pagination metadata")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "data": [{"id": 1, "name": "Example Item"}],
                "pagination": {
                    "limit": 20,
                    "has_next": True,
                    "has_previous": False,
                    "next_cursor": "aW1kOjIw",
                    "previous_cursor": None,
                    "total_count": 150,
                },
            }
        }
    )
