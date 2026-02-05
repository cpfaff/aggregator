"""
Common schemas used across the application.
"""

from pydantic import BaseModel, ConfigDict, Field


class TokenResponse(BaseModel):
    """Token response model for authentication endpoints."""

    access_token: str = Field(description="JWT access token for API authentication")
    refresh_token: str = Field(description="Token used to obtain new access tokens")
    token_type: str = Field(default="bearer", description="Token type (always 'bearer')")
    expires_in: int = Field(description="Access token expiration time in seconds")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxIiwiZXhwIjoxNzM4NzU2MjQ1fQ.example",
                "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxIiwiZXhwIjoxNzM5MzYxMDQ1fQ.example",
                "token_type": "bearer",
                "expires_in": 3600,
            }
        }
    )


class CSRFTokenResponse(BaseModel):
    """CSRF token response for form submissions."""

    csrf_token: str = Field(description="CSRF token for form submissions")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {"csrf_token": "abc123def456ghi789jkl012mno345pqr678stu901vwx234yz"}
        }
    )
