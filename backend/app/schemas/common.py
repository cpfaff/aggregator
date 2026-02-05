"""
Common schemas used across the application.
"""

from pydantic import BaseModel


class TokenResponse(BaseModel):
    """Token response model for authentication endpoints"""

    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int
