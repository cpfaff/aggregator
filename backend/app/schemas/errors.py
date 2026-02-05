"""RFC 7807 Problem Details error response schemas."""

from datetime import UTC, datetime

from pydantic import BaseModel, ConfigDict, Field


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

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "type": "https://api.gfbio.org/errors/not-found",
                "title": "Resource Not Found",
                "status": 404,
                "detail": "Dataset with ID 12345 does not exist.",
                "instance": "/api/v1/datasets/12345",
                "timestamp": "2026-02-05T10:30:45.123456+00:00",
            }
        }
    )


class ValidationProblemDetail(ProblemDetail):
    """Extended problem details for validation errors with error list."""

    errors: list[dict] = Field(
        default_factory=list,
        description="List of validation errors with field and message",
    )

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "type": "https://api.gfbio.org/errors/validation-error",
                "title": "Validation Error",
                "status": 422,
                "detail": "Request validation failed",
                "instance": "/api/v1/providers",
                "timestamp": "2026-02-05T10:30:45.123456+00:00",
                "errors": [
                    {
                        "field": "name",
                        "message": "Field required",
                        "type": "missing",
                    },
                    {
                        "field": "url",
                        "message": "Invalid URL format",
                        "type": "url_parsing",
                    },
                ],
            }
        }
    )
