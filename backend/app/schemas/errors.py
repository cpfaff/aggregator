"""RFC 7807 Problem Details error response schemas."""

from datetime import UTC, datetime

from pydantic import BaseModel, Field


class ProblemDetail(BaseModel):
    """RFC 7807 Problem Details response schema.

    See: https://datatracker.ietf.org/doc/html/rfc7807
    """

    type: str = Field(
        default="about:blank",
        description="URI reference identifying the problem type",
    )
    title: str = Field(description="Short, human-readable summary of the problem")
    status: int = Field(description="HTTP status code")
    detail: str | None = Field(
        default=None, description="Human-readable explanation specific to this occurrence"
    )
    instance: str | None = Field(
        default=None, description="URI reference for this specific occurrence"
    )
    timestamp: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        description="When the error occurred (extension field)",
    )


class ValidationProblemDetail(ProblemDetail):
    """Extended problem details for validation errors with error list."""

    errors: list[dict] = Field(
        default_factory=list,
        description="List of validation errors with field and message",
    )
